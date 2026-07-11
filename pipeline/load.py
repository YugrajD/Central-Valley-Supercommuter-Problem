"""Run the ETL: fetch each source and persist it through the repository layer.

Usage:
    python -m pipeline.load             # everything
    python -m pipeline.load tracts acs  # just those steps

Steps are idempotent — raw downloads are cached in data/raw, tables are
overwritten in the store. OSM is the slow one (1.1 GB download + clip).
"""

import argparse
import sys

from repositories.base import Repository, get_repository


def load_tracts(repo: Repository) -> str:
    from pipeline.sources.tracts import fetch_tracts

    sj, bay = fetch_tracts()
    repo.save_geo("sj_tracts", sj)
    repo.save_geo("bay_tracts", bay)
    return f"sj_tracts: {len(sj)} tracts, bay_tracts: {len(bay)} tracts"


def load_acs(repo: Repository) -> str:
    from pipeline.sources.acs import fetch_acs

    acs = fetch_acs()
    repo.save_table("acs_equity", acs)
    return f"acs_equity: {len(acs)} tracts"


def load_lodes(repo: Repository) -> str:
    from pipeline.sources.lodes import fetch_bay_jobs, fetch_od_flows

    jobs = fetch_bay_jobs()
    repo.save_table("bay_jobs", jobs)
    od = fetch_od_flows()
    repo.save_table("od_flows", od)
    return (
        f"bay_jobs: {len(jobs)} work tracts ({jobs['jobs'].sum():,} jobs), "
        f"od_flows: {len(od)} SJ->Bay tract pairs ({od['jobs'].sum():,} commuters)"
    )


def load_gtfs(repo: Repository) -> str:
    from pipeline.sources.gtfs import fetch_gtfs

    feeds = fetch_gtfs()
    repo.save_table("gtfs_feeds", feeds)
    return "\n".join(
        f"{r.feed}: {r.n_routes} routes, {r.n_stops} stops, {r.n_trips} trips, "
        f"service {r.service_start}-{r.service_end}"
        for r in feeds.itertuples()
    )


def load_osm(repo: Repository) -> str:
    import pandas as pd

    from pipeline.sources.osm import fetch_osm

    pbf = fetch_osm()
    size_mb = pbf.stat().st_size / 1e6
    repo.save_table(
        "osm_meta", pd.DataFrame([{"path": str(pbf), "size_mb": round(size_mb, 1)}])
    )
    return f"study_area.osm.pbf: {size_mb:.0f} MB"


STEPS = {
    "tracts": load_tracts,
    "acs": load_acs,
    "lodes": load_lodes,
    "gtfs": load_gtfs,
    "osm": load_osm,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("steps", nargs="*", choices=[*STEPS, []], default=list(STEPS))
    args = parser.parse_args()

    repo = get_repository()
    failed = []
    for name in args.steps or list(STEPS):
        print(f"=== {name} ===", flush=True)
        try:
            print(STEPS[name](repo), flush=True)
        except Exception as e:  # keep going; report at the end
            failed.append(name)
            print(f"FAILED: {type(e).__name__}: {e}", flush=True)
    if failed:
        print(f"\nfailed steps: {', '.join(failed)}")
        return 1
    print("\nall steps loaded. store contents:", ", ".join(repo.list_tables()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
