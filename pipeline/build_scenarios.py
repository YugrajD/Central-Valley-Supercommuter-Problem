"""Precompute canned scenarios: for each, build the modified network, recompute
the travel-time matrix, and cache the per-tract access table.

Usage: python -m pipeline.build_scenarios [scenario_id ...]
Requires the baseline inputs (tracts, bay_jobs, OSM study area, GTFS feeds).
"""

import datetime as dt
import sys

import pandas as pd

from core.accessibility import jobs_reachable
from core.routing.catalog import CATALOG, build_scenario_feeds
from core.routing.engine import build_network, travel_time_matrix
from pipeline.build_baseline import CUTOFFS_MIN, centroids
from pipeline.config import DEPARTURE
from pipeline.sources.osm import STUDY_PBF
from repositories.base import get_repository


def build_one(scenario_id: str) -> None:
    repo = get_repository()
    sj = repo.load_geo("sj_tracts")
    bay = repo.load_geo("bay_tracts")
    bay_jobs = repo.load_table("bay_jobs")

    origins = centroids(sj)
    destinations = centroids(bay[bay["geoid"].isin(bay_jobs["work_tract"])])

    print(f"[{scenario_id}] building network...", flush=True)
    network = build_network(STUDY_PBF, build_scenario_feeds(scenario_id))

    departure = dt.datetime.strptime(DEPARTURE, "%Y-%m-%d %H:%M")
    print(f"[{scenario_id}] travel-time matrix...", flush=True)
    ttm = travel_time_matrix(network, origins, destinations, departure, max_time_min=120)

    access = pd.DataFrame(
        {f"jobs_{c}min": jobs_reachable(ttm, bay_jobs, cutoff_min=c) for c in CUTOFFS_MIN}
    )
    access.index.name = "geoid"
    repo.save_table(f"scenario_access_{scenario_id}", access.reset_index())
    print(f"[{scenario_id}] done. median jobs in 60min: "
          f"{access['jobs_60min'].median():,.0f}", flush=True)


def main() -> int:
    ids = sys.argv[1:] or [s.id for s in CATALOG]
    for scenario_id in ids:
        build_one(scenario_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
