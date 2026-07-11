"""GET /baseline — SJ tract geometry + baseline accessibility + equity layers, as GeoJSON."""

import json
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from repositories.base import get_repository

router = APIRouter()

EQUITY_COLS = [
    "median_income", "median_rent", "supercommuter_share", "long_commute_share",
    "transit_share", "wfh_share", "renter_share",
]


@lru_cache(maxsize=1)
def _baseline_geojson() -> str:
    """Join tracts + ACS + (if computed) baseline access; cache the serialized result."""
    repo = get_repository()
    if not repo.exists("sj_tracts"):
        raise HTTPException(503, "pipeline has not run: sj_tracts missing")

    tracts = repo.load_geo("sj_tracts")
    if repo.exists("acs_equity"):
        acs = repo.load_table("acs_equity")[["geoid", *EQUITY_COLS]]
        tracts = tracts.merge(acs, on="geoid", how="left")
    if repo.exists("baseline_access"):
        access = repo.load_table("baseline_access")
        tracts = tracts.merge(access, on="geoid", how="left")

    # NaN -> null happens inside to_json; round floats to keep the payload lean
    for col in tracts.columns:
        if tracts[col].dtype == "float64":
            tracts[col] = tracts[col].round(4)
    return tracts.to_json(na="null")


@router.get("/baseline")
def baseline() -> dict:
    return json.loads(_baseline_geojson())


def invalidate_cache() -> None:
    """Called if the pipeline reruns while the API is up."""
    _baseline_geojson.cache_clear()
