"""Scenario primitives, exercised against the real ACE feed (skipped if the
pipeline hasn't downloaded it yet)."""

import io
import zipfile

import pandas as pd
import pytest

from core.routing.scenarios import add_infill_stop, multiply_frequency
from pipeline.sources.gtfs import GTFS_DIR

ACE = GTFS_DIR / "ace.gtfs.zip"

pytestmark = pytest.mark.skipif(not ACE.exists(), reason="ACE feed not downloaded")


def read(path, name) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        match = next(n for n in zf.namelist() if n.endswith(name))
        return pd.read_csv(io.BytesIO(zf.read(match)), dtype=str)


def test_infill_stop_added_and_times_monotonic(tmp_path):
    out = add_infill_stop(
        ACE, "test_manteca", stop_id="MAN", stop_name="Downtown Manteca",
        lat=37.798, lon=-121.216, after_stop_id="SKT",
    )
    stops = read(out, "stops.txt")
    assert "MAN" in set(stops["stop_id"])

    st = read(out, "stop_times.txt")
    st["stop_sequence"] = st["stop_sequence"].astype(int)
    served = st[st["stop_id"] == "MAN"]["trip_id"]
    assert len(served) > 0  # westbound trips got the stop

    def secs(v):
        h, m, s = map(int, v.split(":"))
        return h * 3600 + m * 60 + s

    for trip_id in served:
        times = (
            st[st["trip_id"] == trip_id]
            .sort_values("stop_sequence")["arrival_time"]
            .map(secs)
            .tolist()
        )
        assert times == sorted(times), f"non-monotonic times on {trip_id}"


def test_frequency_doubling_doubles_trips():
    out = multiply_frequency(ACE, "test_double", route_id="ACE", factor=2, offset_min=35)
    base_trips = read(ACE, "trips.txt")
    new_trips = read(out, "trips.txt")
    assert len(new_trips) == 2 * len(base_trips)

    st = read(out, "stop_times.txt")
    orig = st[st["trip_id"] == base_trips["trip_id"].iloc[0]]
    clone = st[st["trip_id"] == base_trips["trip_id"].iloc[0] + "_x1"]
    assert len(orig) == len(clone)


def test_catalog_builds_all(tmp_path):
    from core.routing.catalog import CATALOG, build_scenario_feeds

    for sc in CATALOG:
        feeds = build_scenario_feeds(sc.id)
        assert all(p.exists() for p in feeds), sc.id
