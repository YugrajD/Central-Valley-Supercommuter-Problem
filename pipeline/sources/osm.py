"""OSM street/walk network for the study corridor.

Source: Geofabrik NorCal extract (~1.1 GB, downloaded once, cached in data/raw).
Geofabrik has no San-Joaquin-sized sub-extract and no osmium-tool binary exists
for Windows, so we clip in Python (pyosmium) to a corridor bounding box:
San Joaquin County plus the East Bay / Tri-Valley / South Bay destination side.

The clip keeps only ways tagged highway / railway / public_transport (what R5
routes over) and the nodes they reference. Relations are dropped — turn
restrictions affect car routing, not the transit+walk modes we use.

Output: data/raw/study_area.osm.pbf — the file handed to r5py.
"""

from pathlib import Path

import numpy as np
import requests

from pipeline.config import RAW_DIR

NORCAL_URL = "https://download.geofabrik.de/north-america/us/california/norcal-latest.osm.pbf"
NORCAL_PBF = RAW_DIR / "norcal-latest.osm.pbf"
STUDY_PBF = RAW_DIR / "study_area.osm.pbf"

# Corridor bbox: all of SJ County + Alameda/Tri-Valley/South Bay (ACE + BART
# destination side). SF/San Mateo are excluded — without their local feeds
# they're not transit-reachable inside the cutoff anyway.
MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = -122.35, 37.15, -120.85, 38.35

ROUTABLE_KEYS = ("highway", "railway", "public_transport")


def download_norcal(force: bool = False) -> Path:
    """Stream-download the Geofabrik extract (skipped if already present)."""
    if NORCAL_PBF.exists() and not force:
        return NORCAL_PBF
    NORCAL_PBF.parent.mkdir(parents=True, exist_ok=True)
    tmp = NORCAL_PBF.with_suffix(".part")
    with requests.get(NORCAL_URL, stream=True, timeout=1200) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 22):
                f.write(chunk)
    tmp.replace(NORCAL_PBF)
    return NORCAL_PBF


def _in_bbox(lon: float, lat: float) -> bool:
    return MIN_LON <= lon <= MAX_LON and MIN_LAT <= lat <= MAX_LAT


def clip_study_area(force: bool = False) -> Path:
    """Four sequential scans of the NorCal file (PBF requires nodes-then-ways order):

    1. nodes  -> ids inside the bbox
    2. ways   -> routable ways touching a bbox node; collect all their node refs
    3. nodes  -> write every referenced node
    4. ways   -> write the kept ways
    """
    import osmium

    if STUDY_PBF.exists() and not force:
        return STUDY_PBF

    src = str(download_norcal())

    # pass 1: bbox node ids
    ids = []
    for node in osmium.FileProcessor(src, osmium.osm.NODE):
        loc = node.location
        if loc.valid() and _in_bbox(loc.lon, loc.lat):
            ids.append(node.id)
    bbox_ids = np.sort(np.array(ids, dtype=np.int64))
    del ids

    def _contains(sorted_arr: np.ndarray, values: np.ndarray) -> np.ndarray:
        pos = np.searchsorted(sorted_arr, values)
        pos[pos == len(sorted_arr)] = 0
        return sorted_arr[pos] == values

    # pass 2: routable ways with >=1 node in bbox
    kept_way_ids = []
    needed_refs = []
    for way in osmium.FileProcessor(src, osmium.osm.WAY).with_filter(
        osmium.filter.KeyFilter(*ROUTABLE_KEYS)
    ):
        refs = np.array([n.ref for n in way.nodes], dtype=np.int64)
        if _contains(bbox_ids, refs).any():
            kept_way_ids.append(way.id)
            needed_refs.append(refs)
    way_ids = np.sort(np.array(kept_way_ids, dtype=np.int64))
    needed = np.unique(np.concatenate(needed_refs)) if needed_refs else np.array([], dtype=np.int64)
    del bbox_ids, kept_way_ids, needed_refs

    # passes 3+4: write nodes then ways. bisect (C-implemented) keeps the
    # per-object membership test cheap across ~100M nodes.
    from bisect import bisect_left

    def _has(sorted_arr: np.ndarray, value: int) -> bool:
        pos = bisect_left(sorted_arr, value)
        return pos < len(sorted_arr) and sorted_arr[pos] == value

    tmp = STUDY_PBF.with_suffix(".part.pbf")
    tmp.unlink(missing_ok=True)
    writer = osmium.SimpleWriter(str(tmp))
    try:
        for node in osmium.FileProcessor(src, osmium.osm.NODE):
            if _has(needed, node.id):
                writer.add_node(node)
        for way in osmium.FileProcessor(src, osmium.osm.WAY).with_filter(
            osmium.filter.KeyFilter(*ROUTABLE_KEYS)
        ):
            if _has(way_ids, way.id):
                writer.add_way(way)
    finally:
        writer.close()
    tmp.replace(STUDY_PBF)
    return STUDY_PBF


def fetch_osm(force: bool = False) -> Path:
    """Download + clip; returns the study-area PBF path for r5py."""
    return clip_study_area(force=force)
