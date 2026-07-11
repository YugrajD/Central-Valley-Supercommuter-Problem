# ALTAMONT — The Central Valley Super-Commuter Problem

A public, interactive map that lets anyone test a proposed transit change in
San Joaquin County — a new ACE station, an added feeder bus — and instantly see
how many more Bay Area jobs it puts within reach for stranded commuters,
weighted by who needs it most.

Built **on** Conveyal's R5 routing engine (via [r5py](https://r5py.readthedocs.io/)) —
the routing math is borrowed; the pipeline, scenarios, before/after diff, equity
overlay, and UI are built here.

**One number drives the tool:** jobs reachable in 60 minutes by transit + walking
from each census tract, using real schedules.

1. **Baseline** — compute it for every SJ County tract on today's network
2. **What-if** — toggle a proposed change, recompute
3. **Diff** — the delta per tract is the headline ("+40,000 jobs for these tracts")
4. **Equity overlay** — user-adjustable weights for income, renter share, super-commuter share

## Repo layout

| Path | What |
|---|---|
| `pipeline/` | ETL: LODES, ACS, GTFS, OSM → storage |
| `core/` | routing wrapper (r5py), accessibility, equity, diff |
| `repositories/` | data-access layer (file-backed default, PostGIS impl) |
| `api/` | FastAPI backend |
| `web/` | Next.js + MapLibre frontend |
| `prototype/` | single-file map prototype (open `map.html` directly) |
| `docs/` | plan, methodology, scaling notes |

## Quick start

```powershell
# API
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\uvicorn api.main:app --reload   # http://localhost:8000/health

# Frontend
cd web && npm install && npm run dev           # http://localhost:3000
```

See [CLAUDE.md](CLAUDE.md) for the full build brief and [docs/plan.md](docs/plan.md)
for the staged plan.
