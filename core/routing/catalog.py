"""Canned scenarios — the demo set. Each builds its modified feed list once and
caches it; build_baseline-style precompute then stores the resulting access table.

IDs are stable API contract; the frontend toggle lists these.
"""

from dataclasses import dataclass
from pathlib import Path

from core.routing.scenarios import NewRoute, add_infill_stop, add_route, multiply_frequency
from pipeline.sources.gtfs import GTFS_DIR, gtfs_paths


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str


CATALOG = [
    Scenario(
        "manteca_ace",
        "Downtown Manteca ACE station",
        "Infill ACE station in downtown Manteca, between Stockton and Lathrop. "
        "Westbound AM trips stop there; times interpolated between neighbors.",
    ),
    Scenario(
        "valley_link",
        "Valley Link: Tracy to Dublin BART",
        "New rail shuttle from downtown Tracy via Mountain House to the "
        "Dublin/Pleasanton BART station, every 30 minutes in the AM peak.",
    ),
    Scenario(
        "ace_double",
        "ACE runs twice as often",
        "Every ACE trip duplicated 35 minutes later — halves the effective wait "
        "in the departure window without new infrastructure.",
    ),
]


def _ace_feed() -> Path:
    return GTFS_DIR / "ace.gtfs.zip"


def build_scenario_feeds(scenario_id: str) -> list[Path]:
    """Return the full GTFS feed list for a scenario (base feeds with the ACE
    feed swapped/augmented). Cached zips are rebuilt only if missing."""
    base = gtfs_paths()

    if scenario_id == "manteca_ace":
        modified = add_infill_stop(
            _ace_feed(),
            "manteca_ace",
            stop_id="MAN",
            stop_name="Downtown Manteca Station",
            lat=37.7980,
            lon=-121.2160,
            after_stop_id="SKT",  # westbound: Stockton -> Manteca -> Lathrop
        )
        return [modified if p.name == "ace.gtfs.zip" else p for p in base]

    if scenario_id == "valley_link":
        vlink = add_route(
            _ace_feed(),
            "valley_link",
            NewRoute(
                route_id="VLINK",
                route_name="Valley Link",
                route_type="2",
                stops=[
                    ("VL_TRC", "Tracy Valley Link", 37.7397, -121.4252, 0),
                    ("VL_MH", "Mountain House", 37.7663, -121.5449, 8),
                    ("VL_GRN", "Greenville/Livermore", 37.6987, -121.6982, 20),
                    ("VL_ISB", "Isabel/Livermore", 37.6996, -121.8121, 27),
                    ("VL_DUB", "Dublin/Pleasanton BART", 37.7017, -121.8994, 35),
                ],
                departures=["05:00", "05:30", "06:00", "06:30", "07:00", "07:30",
                            "08:00", "08:30", "09:00"],
            ),
        )
        return [*base, vlink]

    if scenario_id == "ace_double":
        modified = multiply_frequency(_ace_feed(), "ace_double", route_id="ACE",
                                      factor=2, offset_min=35)
        return [modified if p.name == "ace.gtfs.zip" else p for p in base]

    raise KeyError(f"unknown scenario: {scenario_id}")
