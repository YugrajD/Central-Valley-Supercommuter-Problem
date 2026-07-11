"""Thin wrapper around r5py. Borrowed math stops here — nothing above this file
touches R5, nothing in this file computes routes itself.

R5 needs Java 21. This machine's system Java is 1.8, so a portable Temurin JDK
lives in jdk/ (gitignored); point JAVA_HOME there before importing r5py —
`configure_java()` handles it.
"""

import datetime as dt
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def configure_java() -> None:
    """Set JAVA_HOME to the bundled JDK 21 if the environment doesn't have one."""
    bundled = sorted(REPO_ROOT.glob("jdk/jdk-21*"))
    if bundled and "21" not in os.environ.get("JAVA_HOME", ""):
        os.environ["JAVA_HOME"] = str(bundled[-1])
        os.environ["PATH"] = str(bundled[-1] / "bin") + os.pathsep + os.environ["PATH"]


def build_network(osm_path: Path, gtfs_paths: list[Path]):
    """Build (or load from R5's cache next to the PBF) the routable network."""
    configure_java()
    from r5py import TransportNetwork

    return TransportNetwork(str(osm_path), [str(p) for p in gtfs_paths])


def travel_time_matrix(
    network,
    origins: gpd.GeoDataFrame,
    destinations: gpd.GeoDataFrame,
    departure: dt.datetime,
    max_time_min: int = 120,
) -> pd.DataFrame:
    """Transit+walk travel times, long format [from_id, to_id, travel_time] (minutes).

    origins/destinations: GeoDataFrames with an `id` column and point geometry
    (tract centroids). NaN travel_time = unreachable within max_time_min.
    The departure is fixed and documented (pipeline.config.DEPARTURE) so every
    matrix answers the same question about the same schedule snapshot.
    """
    configure_java()
    from r5py import TravelTimeMatrix, TransportMode

    ttm = TravelTimeMatrix(
        network,
        origins=origins,
        destinations=destinations,
        departure=departure,
        departure_time_window=dt.timedelta(minutes=60),  # spread over the AM peak
        transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
        max_time=dt.timedelta(minutes=max_time_min),
    )
    return pd.DataFrame(ttm).rename(columns={"from_id": "from_id", "to_id": "to_id"})
