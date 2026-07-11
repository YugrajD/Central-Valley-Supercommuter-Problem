"""LODES8 (LEHD) — the actual home→work flows and job locations.

Two products:
- OD "main" file: job counts by (home block, work block) pair. We keep
  home ∈ SJ County, work ∈ the five Bay counties, aggregated to tract pairs.
- WAC file: total jobs by work block, aggregated to Bay Area work tracts —
  this is the "reachable jobs" mass for the accessibility score.

Known caveats (surface in methodology): primary jobs only (JT00 = all jobs,
S000 = all segments), DP noise at block level (we aggregate to tract),
multi-year lag vs ACS, no remote-work signal (ACS wfh_share covers that).
"""

import gzip
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import BAY_COUNTY_FIPS, LODES_VERSION, LODES_YEAR, RAW_DIR, SJ_COUNTY_FIPS, STATE_FIPS

BASE = f"https://lehd.ces.census.gov/data/lodes/{LODES_VERSION}/ca"
OD_URL = f"{BASE}/od/ca_od_main_JT00_{LODES_YEAR}.csv.gz"
WAC_URL = f"{BASE}/wac/ca_wac_S000_JT00_{LODES_YEAR}.csv.gz"

SJ_PREFIX = STATE_FIPS + SJ_COUNTY_FIPS                      # "06077"
BAY_PREFIXES = tuple(STATE_FIPS + c for c in BAY_COUNTY_FIPS)  # ("06001", ...)


def _download(url: str) -> Path:
    dest = RAW_DIR / url.rsplit("/", 1)[-1]
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=600) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
    return dest


def fetch_od_flows() -> pd.DataFrame:
    """Tract-level OD: home tract (SJ) → work tract (Bay), total jobs per pair.

    The statewide block-pair file is ~15M rows; stream it in chunks and keep
    only SJ-home → Bay-work pairs.
    """
    path = _download(OD_URL)
    keep_frames = []
    with gzip.open(path, "rt") as f:
        for chunk in pd.read_csv(
            f,
            usecols=["w_geocode", "h_geocode", "S000"],
            dtype={"w_geocode": str, "h_geocode": str, "S000": "int32"},
            chunksize=1_000_000,
        ):
            mask = chunk["h_geocode"].str.startswith(SJ_PREFIX) & chunk[
                "w_geocode"
            ].str.startswith(BAY_PREFIXES)
            if mask.any():
                keep_frames.append(chunk[mask])

    od = pd.concat(keep_frames, ignore_index=True)
    # block GEOID (15 digits) → tract GEOID (first 11)
    od["home_tract"] = od["h_geocode"].str[:11]
    od["work_tract"] = od["w_geocode"].str[:11]
    return (
        od.groupby(["home_tract", "work_tract"], as_index=False)["S000"]
        .sum()
        .rename(columns={"S000": "jobs"})
    )


def fetch_bay_jobs() -> pd.DataFrame:
    """Total jobs per Bay Area work tract (WAC C000), the accessibility mass."""
    path = _download(WAC_URL)
    with gzip.open(path, "rt") as f:
        wac = pd.read_csv(
            f, usecols=["w_geocode", "C000"], dtype={"w_geocode": str, "C000": "int32"}
        )
    wac = wac[wac["w_geocode"].str.startswith(BAY_PREFIXES)]
    wac["work_tract"] = wac["w_geocode"].str[:11]
    return (
        wac.groupby("work_tract", as_index=False)["C000"]
        .sum()
        .rename(columns={"C000": "jobs"})
    )
