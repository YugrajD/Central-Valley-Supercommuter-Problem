"""Precompute the baseline: travel-time matrix on today's network + jobs-reachable
per SJ tract. Slow (R5 graph build), run offline; the API serves the cached result.

Usage: python -m pipeline.build_baseline
"""

import datetime as dt
import sys

import pandas as pd

from core.accessibility import jobs_reachable
from core.routing.engine import build_network, travel_time_matrix
from pipeline.config import DEPARTURE
from pipeline.sources.gtfs import gtfs_paths
from pipeline.sources.osm import STUDY_PBF
from repositories.base import get_repository

CUTOFFS_MIN = [45, 60, 75, 90]


def centroids(gdf: pd.DataFrame) -> pd.DataFrame:
    """Tract GeoDataFrame -> r5py-shaped origins/destinations (id + point)."""
    out = gdf[["geoid", "geometry"]].copy()
    # representative_point always falls inside the polygon (centroids of odd
    # shapes can land in a river or outside entirely)
    out["geometry"] = out.geometry.representative_point()
    return out.rename(columns={"geoid": "id"})


def main() -> int:
    repo = get_repository()

    sj = repo.load_geo("sj_tracts")
    bay = repo.load_geo("bay_tracts")
    bay_jobs = repo.load_table("bay_jobs")

    origins = centroids(sj)
    # destination = Bay tracts that actually contain jobs
    with_jobs = bay[bay["geoid"].isin(bay_jobs["work_tract"])]
    destinations = centroids(with_jobs)
    print(f"{len(origins)} origins x {len(destinations)} destinations", flush=True)

    if not STUDY_PBF.exists():
        print(f"missing {STUDY_PBF} — run: python -m pipeline.load osm")
        return 1

    print("building R5 network (first run caches next to the PBF)...", flush=True)
    network = build_network(STUDY_PBF, gtfs_paths())

    departure = dt.datetime.strptime(DEPARTURE, "%Y-%m-%d %H:%M")
    print(f"computing travel-time matrix, departure {departure}...", flush=True)
    ttm = travel_time_matrix(network, origins, destinations, departure, max_time_min=120)
    repo.save_table("baseline_ttm", ttm)

    access = pd.DataFrame(
        {f"jobs_{c}min": jobs_reachable(ttm, bay_jobs, cutoff_min=c) for c in CUTOFFS_MIN}
    )
    access.index.name = "geoid"
    repo.save_table("baseline_access", access.reset_index())

    reach60 = access["jobs_60min"]
    print(
        f"baseline done. jobs in 60min — median {reach60.median():,.0f}, "
        f"max {reach60.max():,.0f}, stranded tracts (0 jobs): {(reach60 == 0).sum()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
