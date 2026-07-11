"""Shared pipeline constants: geography, vintages, paths."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

STATE_FIPS = "06"  # California

# Home side: San Joaquin County
SJ_COUNTY_FIPS = "077"

# Work side: the five Bay Area counties from the brief (CLAUDE.md §5)
BAY_COUNTY_FIPS = {
    "001": "Alameda",
    "013": "Contra Costa",
    "075": "San Francisco",
    "081": "San Mateo",
    "085": "Santa Clara",
}

# Dataset vintages. LODES lags ACS by design — note this in the methodology page.
ACS_YEAR = 2023          # ACS 5-year, 2019–2023
LODES_VERSION = "LODES8"
LODES_YEAR = 2022
TIGER_YEAR = 2023

# Fixed representative departure for all travel-time matrices (CLAUDE.md §9):
# a mid-week morning inside the ACE westbound commute window.
DEPARTURE = "2026-07-08 06:30"  # Wednesday, 6:30 AM
