"""ACS 5-year tract-level equity layers for San Joaquin County.

The classic api.census.gov endpoint now requires an API key, so this pulls from
data.census.gov's own table API (keyless, same published estimates). One request
per table, merged on tract GEOID.

Variables (CLAUDE.md §5):
- B08303: travel time to work — 90+ min bucket → super-commuter share
- B08301: means of transportation — transit share, worked-from-home share
- B19013: median household income
- B25064: median gross rent
- B25003: tenure — renter share
"""

import pandas as pd
import requests

from pipeline.config import ACS_YEAR, SJ_COUNTY_FIPS, STATE_FIPS

API = "https://data.census.gov/api/access/data/table"

# table -> {variable: output column}
TABLES = {
    "B08303": {
        "B08303_001E": "tt_total",    # workers who commute (travel-time universe)
        "B08303_012E": "tt_60_89",    # 60–89 min
        "B08303_013E": "tt_90_plus",  # 90+ min
    },
    "B08301": {
        "B08301_001E": "mode_total",
        "B08301_010E": "mode_transit",  # public transportation (excl. taxicab)
        "B08301_021E": "mode_wfh",      # worked from home
    },
    "B19013": {"B19013_001E": "median_income"},
    "B25064": {"B25064_001E": "median_rent"},
    "B25003": {
        "B25003_001E": "tenure_total",
        "B25003_003E": "tenure_renter",
    },
}


def _fetch_table(table: str, columns: dict[str, str]) -> pd.DataFrame:
    resp = requests.get(
        API,
        params={
            "id": f"ACSDT5Y{ACS_YEAR}.{table}",
            # all tracts (1400000) within the county
            "g": f"050XX00US{STATE_FIPS}{SJ_COUNTY_FIPS}$1400000",
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()["response"]["data"]
    df = pd.DataFrame(data[1:], columns=data[0])
    df["geoid"] = df["GEO_ID"].str.split("US").str[-1]
    keep = df[["geoid", *columns]].rename(columns=columns)
    for col in columns.values():
        keep[col] = pd.to_numeric(keep[col], errors="coerce")
        # negative values are suppression sentinels (-666666666 etc.), never data
        keep.loc[keep[col] < 0, col] = pd.NA
    return keep


def fetch_acs() -> pd.DataFrame:
    """One row per SJ County tract: GEOID + raw counts + derived equity shares."""
    df: pd.DataFrame | None = None
    for table, columns in TABLES.items():
        part = _fetch_table(table, columns)
        df = part if df is None else df.merge(part, on="geoid", how="outer")
    assert df is not None

    # Derived shares; guard against zero-worker tracts
    tt = df["tt_total"].replace(0, pd.NA)
    mt = df["mode_total"].replace(0, pd.NA)
    tn = df["tenure_total"].replace(0, pd.NA)
    as_float = lambda s: pd.to_numeric(s, errors="coerce").astype(float)  # noqa: E731
    df["supercommuter_share"] = as_float(df["tt_90_plus"] / tt)
    df["long_commute_share"] = as_float((df["tt_60_89"] + df["tt_90_plus"]) / tt)
    df["transit_share"] = as_float(df["mode_transit"] / mt)
    df["wfh_share"] = as_float(df["mode_wfh"] / mt)
    df["renter_share"] = as_float(df["tenure_renter"] / tn)

    return df[
        ["geoid", "median_income", "median_rent", "supercommuter_share",
         "long_commute_share", "transit_share", "wfh_share", "renter_share",
         "tt_total", "mode_total", "tenure_total"]
    ]
