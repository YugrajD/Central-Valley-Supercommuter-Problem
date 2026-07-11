"""Scenario = a modified GTFS feed. R5 then routes over the modified network —
we never touch routing math, only the schedule inputs.

Three modification primitives cover the canned scenarios:
- add_infill_stop: new station on an existing route, times interpolated
  between its neighbors ("Downtown Manteca ACE station")
- add_route: brand-new route + stops + trips ("Valley Link Tracy->Dublin")
- multiply_frequency: clone every trip of a route with time offsets
  ("ACE runs twice as often")

Each returns the path of a new GTFS zip in cache/scenarios/, leaving the
original feed untouched.
"""

import io
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache" / "scenarios"


# ---------------------------------------------------------------- helpers


def _read(zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
    match = next((n for n in zf.namelist() if n.endswith(name)), None)
    if match is None:
        raise FileNotFoundError(f"{name} not in feed")
    return pd.read_csv(io.BytesIO(zf.read(match)), dtype=str)


def _write_feed(src: Path, out: Path, replacements: dict[str, pd.DataFrame]) -> Path:
    """Copy the feed, swapping in modified tables."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        seen = set()
        for name in zin.namelist():
            base = name.rsplit("/", 1)[-1]
            if base in replacements:
                zout.writestr(base, replacements[base].to_csv(index=False))
                seen.add(base)
            else:
                zout.writestr(base, zin.read(name))
        for base, df in replacements.items():
            if base not in seen:  # net-new table
                zout.writestr(base, df.to_csv(index=False))
    return out


def _to_seconds(hms: str) -> int:
    h, m, s = (int(x) for x in hms.split(":"))
    return h * 3600 + m * 60 + s


def _to_hms(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


# ---------------------------------------------------------------- primitives


def add_infill_stop(
    feed: Path,
    out_name: str,
    stop_id: str,
    stop_name: str,
    lat: float,
    lon: float,
    after_stop_id: str,
    dwell_s: int = 60,
) -> Path:
    """Insert a new station immediately after `after_stop_id` on every trip that
    serves it. Arrival time is interpolated between the neighboring stops."""
    out = CACHE_DIR / f"{out_name}.gtfs.zip"
    with zipfile.ZipFile(feed) as zf:
        stops = _read(zf, "stops.txt")
        st = _read(zf, "stop_times.txt")

    stops = pd.concat(
        [stops, pd.DataFrame([{"stop_id": stop_id, "stop_name": stop_name,
                               "stop_lat": str(lat), "stop_lon": str(lon)}])],
        ignore_index=True,
    )

    st["stop_sequence"] = st["stop_sequence"].astype(int)
    st = st.sort_values(["trip_id", "stop_sequence"], ignore_index=True)

    new_rows = []
    for trip_id, grp in st.groupby("trip_id"):
        idx = grp.index[grp["stop_id"] == after_stop_id]
        if len(idx) == 0:
            continue
        i = idx[0]
        pos = grp.index.get_loc(i)
        if pos + 1 >= len(grp):
            continue  # after_stop is the last stop; nothing to interpolate toward
        prev_row, next_row = grp.iloc[pos], grp.iloc[pos + 1]
        t_prev = _to_seconds(prev_row["departure_time"])
        t_next = _to_seconds(next_row["arrival_time"])
        t_mid = (t_prev + t_next) // 2
        new_rows.append(
            {
                **{c: "" for c in st.columns},
                "trip_id": trip_id,
                "stop_id": stop_id,
                "arrival_time": _to_hms(t_mid),
                "departure_time": _to_hms(min(t_mid + dwell_s, t_next)),
                # fractional sequence, re-ranked below
                "stop_sequence": prev_row["stop_sequence"] + 0.5,
            }
        )
    if not new_rows:
        raise ValueError(f"no trips serve {after_stop_id}")

    st = pd.concat([st, pd.DataFrame(new_rows)], ignore_index=True)
    st = st.sort_values(["trip_id", "stop_sequence"], ignore_index=True)
    st["stop_sequence"] = st.groupby("trip_id").cumcount() + 1

    return _write_feed(feed, out, {"stops.txt": stops, "stop_times.txt": st})


def multiply_frequency(feed: Path, out_name: str, route_id: str, factor: int = 2,
                       offset_min: int = 30) -> Path:
    """Clone each trip of `route_id` (factor-1) times, shifted by offset_min each."""
    out = CACHE_DIR / f"{out_name}.gtfs.zip"
    with zipfile.ZipFile(feed) as zf:
        trips = _read(zf, "trips.txt")
        st = _read(zf, "stop_times.txt")

    targets = trips[trips["route_id"] == route_id]
    if targets.empty:
        raise ValueError(f"route {route_id} not found")

    new_trips, new_st = [trips], [st]
    for k in range(1, factor):
        shift = k * offset_min * 60
        t = targets.copy()
        t["trip_id"] = t["trip_id"] + f"_x{k}"
        new_trips.append(t)
        s = st[st["trip_id"].isin(targets["trip_id"])].copy()
        s["trip_id"] = s["trip_id"] + f"_x{k}"
        for col in ("arrival_time", "departure_time"):
            s[col] = s[col].map(lambda v: _to_hms(_to_seconds(v) + shift))
        new_st.append(s)

    return _write_feed(
        feed, out,
        {"trips.txt": pd.concat(new_trips, ignore_index=True),
         "stop_times.txt": pd.concat(new_st, ignore_index=True)},
    )


@dataclass
class NewRoute:
    """A brand-new service, e.g. a feeder shuttle or Valley Link."""

    route_id: str
    route_name: str
    route_type: str  # GTFS: 2=rail, 3=bus
    # ordered (stop_id, name, lat, lon, minutes_from_start)
    stops: list[tuple[str, str, float, float, int]]
    # departure times from the first stop, "HH:MM" strings
    departures: list[str] = field(default_factory=list)
    service_id: str = "EVERYDAY"


def add_route(base_feed: Path, out_name: str, route: NewRoute) -> Path:
    """Write a standalone GTFS zip for the new service (r5py takes a list of
    feeds, so a new service is cleanest as its own feed). base_feed supplies
    the calendar date span."""
    out = CACHE_DIR / f"{out_name}.gtfs.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(base_feed) as zf:
        try:
            cal = _read(zf, "calendar.txt")
            start, end = cal["start_date"].min(), cal["end_date"].max()
        except FileNotFoundError:
            cd = _read(zf, "calendar_dates.txt")
            start, end = cd["date"].min(), cd["date"].max()

    agency = pd.DataFrame([{
        "agency_id": "ALTAMONT_SCENARIO", "agency_name": "ALTAMONT scenario service",
        "agency_url": "https://example.org", "agency_timezone": "America/Los_Angeles",
    }])
    routes = pd.DataFrame([{
        "route_id": route.route_id, "agency_id": "ALTAMONT_SCENARIO",
        "route_short_name": route.route_name, "route_long_name": route.route_name,
        "route_type": route.route_type,
    }])
    calendar = pd.DataFrame([{
        "service_id": route.service_id, "monday": "1", "tuesday": "1", "wednesday": "1",
        "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0",
        "start_date": start, "end_date": end,
    }])
    stops = pd.DataFrame(
        [{"stop_id": sid, "stop_name": name, "stop_lat": str(lat), "stop_lon": str(lon)}
         for sid, name, lat, lon, _ in route.stops]
    )

    trips_rows, st_rows = [], []
    for i, dep in enumerate(route.departures):
        trip_id = f"{route.route_id}_t{i}"
        trips_rows.append({"route_id": route.route_id, "service_id": route.service_id,
                           "trip_id": trip_id})
        t0 = _to_seconds(dep + ":00")
        for seq, (sid, _, _, _, offset_min) in enumerate(route.stops, start=1):
            t = t0 + offset_min * 60
            st_rows.append({
                "trip_id": trip_id, "arrival_time": _to_hms(t), "departure_time": _to_hms(t),
                "stop_id": sid, "stop_sequence": str(seq),
            })

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, df in {
            "agency.txt": agency, "routes.txt": routes, "calendar.txt": calendar,
            "stops.txt": stops, "trips.txt": pd.DataFrame(trips_rows),
            "stop_times.txt": pd.DataFrame(st_rows),
        }.items():
            zout.writestr(name, df.to_csv(index=False))
    return out
