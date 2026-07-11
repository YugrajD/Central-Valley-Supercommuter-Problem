"""GET /scenarios — the canned catalog. POST /scenario — a scenario's per-tract diff.

Canned scenarios are served from precomputed cache (never invoke R5 per request);
the live custom path exists for completeness but is explicitly slow.
"""

import json
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.diff import diff, headline
from core.routing.catalog import CATALOG
from repositories.base import get_repository

router = APIRouter()


@router.get("/scenarios")
def scenarios() -> list[dict]:
    repo = get_repository()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "computed": repo.exists(f"scenario_access_{s.id}"),
        }
        for s in CATALOG
    ]


class ScenarioRequest(BaseModel):
    scenario_id: str
    cutoff_min: int = 60


@lru_cache(maxsize=16)
def _diff_payload(scenario_id: str, cutoff_min: int) -> str:
    repo = get_repository()
    col = f"jobs_{cutoff_min}min"

    if not repo.exists("baseline_access"):
        raise HTTPException(503, "baseline not computed yet: run pipeline/build_baseline.py")
    if not repo.exists(f"scenario_access_{scenario_id}"):
        known = {s.id for s in CATALOG}
        if scenario_id not in known:
            raise HTTPException(404, f"unknown scenario {scenario_id!r}")
        raise HTTPException(
            503, f"scenario {scenario_id!r} not precomputed: run pipeline/build_scenarios.py"
        )

    base = repo.load_table("baseline_access").set_index("geoid")[col]
    scen = repo.load_table(f"scenario_access_{scenario_id}").set_index("geoid")[col]
    d = diff(base, scen)

    tracts = repo.load_geo("sj_tracts").merge(
        d.reset_index(), on="geoid", how="left"
    )
    return json.dumps(
        {
            "scenario_id": scenario_id,
            "cutoff_min": cutoff_min,
            "headline": headline(d),
            "geojson": json.loads(tracts.to_json(na="null")),
        }
    )


@router.post("/scenario")
def scenario(req: ScenarioRequest) -> dict:
    return json.loads(_diff_payload(req.scenario_id, req.cutoff_min))
