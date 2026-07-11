"""Census tract geometries (TIGER cartographic boundaries, 500k resolution).

Two tract layers:
- sj_tracts: San Joaquin County (origin side — where the score is computed)
- bay_tracts: the five Bay Area work counties (destination side — job locations)
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

from pipeline.config import BAY_COUNTY_FIPS, RAW_DIR, SJ_COUNTY_FIPS, STATE_FIPS, TIGER_YEAR

CB_URL = (
    f"https://www2.census.gov/geo/tiger/GENZ{TIGER_YEAR}/shp/"
    f"cb_{TIGER_YEAR}_{STATE_FIPS}_tract_500k.zip"
)


def _download_ca_tracts() -> gpd.GeoDataFrame:
    dest = RAW_DIR / f"cb_{TIGER_YEAR}_{STATE_FIPS}_tract_500k.zip"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(CB_URL, timeout=120)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return gpd.read_file(dest)


def fetch_tracts() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Returns (sj_tracts, bay_tracts), both EPSG:4326 with GEOID + geometry."""
    ca = _download_ca_tracts().to_crs(4326)
    keep = ["GEOID", "NAMELSAD", "COUNTYFP", "ALAND", "geometry"]
    ca = ca[keep].rename(columns={"NAMELSAD": "name", "COUNTYFP": "county_fips", "ALAND": "aland"})
    ca.columns = [c.lower() for c in ca.columns]

    sj = ca[ca["county_fips"] == SJ_COUNTY_FIPS].reset_index(drop=True)
    bay = ca[ca["county_fips"].isin(BAY_COUNTY_FIPS)].reset_index(drop=True)
    return sj, bay
