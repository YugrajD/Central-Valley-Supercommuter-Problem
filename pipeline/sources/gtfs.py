"""GTFS feeds: ACE (commuter rail over the Altamont) + San Joaquin RTD (local bus).

ACE's producer feed sits behind a 511.org API key, so we pull MobilityData's
hosted latest copy (feed mdb-2684). RTD publishes a direct zip. Feeds are kept
as raw zips on disk — that's the format r5py consumes — plus a summary table
in the repository for provenance.
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

FEEDS = {
    "ace": "https://files.mobilitydatabase.org/mdb-2684/latest.zip",
    "sjrtd": "https://sanjoaquinrtd.com/RTD-GTFS/RTD-GTFS.zip",
}

GTFS_DIR = RAW_DIR / "gtfs"

REQUIRED_FILES = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}


def _read_txt(zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
    # some feeds nest files under a directory inside the zip
    match = next((n for n in zf.namelist() if n.endswith(name)), None)
    if match is None:
        raise FileNotFoundError(f"{name} missing from feed")
    return pd.read_csv(io.BytesIO(zf.read(match)), dtype=str)


def _validate(path: Path, feed_id: str) -> dict:
    with zipfile.ZipFile(path) as zf:
        names = {n.rsplit("/", 1)[-1] for n in zf.namelist()}
        missing = REQUIRED_FILES - names
        if missing:
            raise ValueError(f"{feed_id}: feed missing required files: {missing}")
        routes = _read_txt(zf, "routes.txt")
        stops = _read_txt(zf, "stops.txt")
        trips = _read_txt(zf, "trips.txt")

        # service window from calendar and/or calendar_dates
        dates: list[str] = []
        if "calendar.txt" in names:
            cal = _read_txt(zf, "calendar.txt")
            dates += list(cal["start_date"]) + list(cal["end_date"])
        if "calendar_dates.txt" in names:
            cd = _read_txt(zf, "calendar_dates.txt")
            dates += list(cd["date"])

    return {
        "feed": feed_id,
        "path": str(path),
        "n_routes": len(routes),
        "n_stops": len(stops),
        "n_trips": len(trips),
        "service_start": min(dates) if dates else None,
        "service_end": max(dates) if dates else None,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }


def fetch_gtfs() -> pd.DataFrame:
    """Download + validate all feeds. Returns one summary row per feed."""
    GTFS_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for feed_id, url in FEEDS.items():
        dest = GTFS_DIR / f"{feed_id}.gtfs.zip"
        if not dest.exists():
            resp = requests.get(url, timeout=300)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        summaries.append(_validate(dest, feed_id))
    return pd.DataFrame(summaries)


def gtfs_paths() -> list[Path]:
    """Paths handed to r5py's TransportNetwork."""
    return sorted(GTFS_DIR.glob("*.gtfs.zip"))
