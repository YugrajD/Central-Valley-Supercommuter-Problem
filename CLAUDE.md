# ALTAMONT — Project Spec / Build Brief

> **Local-dev deviation from this spec:** no Docker on this machine. Storage goes
> through the `repositories/` interface as specified, with a file-backed
> (GeoParquet) implementation as the local default; the PostGIS implementation
> slots in unchanged when a Postgres server is available. Everything else follows
> this brief.

> A public, interactive map that lets anyone test a proposed transit change in
> San Joaquin County — a new ACE station, an added feeder bus — and instantly
> see how many more Bay Area jobs it puts within reach for stranded commuters,
> weighted by who needs it most.

This file is the source of truth for the build. Read it fully before writing code.

---

## 0. Framing guardrails (read first — these prevent the two classic mistakes)

**How to describe this project:**
> "A public-facing transit-equity scenario tool built *on* Conveyal's R5 routing
> engine (via r5py) — aimed at a question and audience Conveyal isn't for:
> letting ordinary residents test what a proposed transit change would do for
> job access, with the equity assumptions exposed as controls instead of hidden."

**Never describe it as:**
- ❌ "An open-source Conveyal" — R5 *is* Conveyal's engine; we call it, we don't rebuild it. This is an overclaim.
- ❌ "A lakehouse / big-data platform" — the data is county-scale and lives in Postgres. Reaching for warehouse tooling here is over-engineering.
- ❌ A general travel-demand simulator — we do **transit accessibility** (routing over GTFS+OSM), NOT road traffic assignment / congestion modeling.

**The one rule of build-vs-borrow:** the routing math (travel time from everywhere
to everywhere, given a schedule) is **borrowed** from R5. Everything else — pipeline,
scenarios, the before/after diff, the equity overlay, the UI — is **built**. Do not
write custom routing or graph traversal.

---

## 1. The core concept

One number drives the whole tool: **jobs reachable in 60 minutes** from a given
neighborhood (census tract), by transit + walking, using real schedules.

The tool does four things with that number:

1. **Baseline** — compute it for every SJ County tract on today's network. Map it (red = stranded, green = connected).
2. **What-if** — toggle a proposed network change (new station / new route). Recompute the same number under the modified network.
3. **Diff** — subtract before from after. The delta per tract is the headline output ("+40,000 jobs for these 3 tracts").
4. **Equity overlay** — weight/filter by who lives where (income, renter/multifamily share, super-commuter share). If the tracts that gain most are the disadvantaged ones, that's the argument. If not, that's a finding too.

The equity weights are **user-adjustable controls**, not hardcoded — this transparency is a core feature, not a nice-to-have.

---

## 2. Architecture (data flow)

```
LODES + ACS + GTFS + OSM
        │  (Python ETL pipeline)
        ▼
   PostgreSQL + PostGIS  ──(via data-access layer)──┐
        │                                            │
        ▼                                            │
   r5py / R5 engine  ──travel-time matrix──►  accessibility scores
        │                                            │
        ▼                                            ▼
   FastAPI  ──GeoJSON (baseline, scenarios, diff)──► Next.js + MapLibre frontend
```

- **Baseline is precomputed and cached.** R5 graph builds are not instant.
- **Scenarios:** ship a handful of *canned* scenarios (precomputed) for a snappy demo, plus a live `/scenario` path for custom ones.
- **All DB access goes through a data-access layer** (`repositories/`) so business logic never touches SQL directly — this keeps a future Snowflake swap contained (see §8).

---

## 3. Tech stack

| Layer | Technology |
|---|---|
| Routing engine (borrow) | **r5py** (Python wrapper for Conveyal R5) |
| ETL / data | Python: **pandas, geopandas, census/cenpy, gtfs_kit, osmnx** |
| Storage | **PostgreSQL + PostGIS**, behind a data-access layer |
| Backend | **FastAPI + Uvicorn** |
| Frontend | **Next.js + React + MapLibre GL JS** (open-source, no token) |
| GIS companion track | **ArcGIS Pro** (suitability/Network Analyst), **ArcGIS Online StoryMap** |
| Deploy | **Cloud Run** (API), **Vercel** (frontend), **Cloud SQL or Supabase** (Postgres) |
| Documented for scale, NOT deployed | **Snowflake + dbt** (see §8) |

**Deliberately excluded (and why):** Spark/lakehouse (data fits in Postgres),
custom routing code (use r5py), a separate ML model (this is routing+aggregation,
not prediction).

---

## 4. Repo structure

```
altamont/
├── CLAUDE.md                    # this file
├── README.md                    # public-facing project description
├── docker-compose.yml           # postgres+postgis for local dev
├── pipeline/                    # ETL — repeatable scripts, NOT notebooks
│   ├── sources/
│   │   ├── lodes.py             # SJ home → Bay work OD flows
│   │   ├── acs.py               # travel time, mode, WFH, income, rent
│   │   ├── gtfs.py              # ACE + SJ RTD feeds
│   │   └── osm.py               # street/walk network extract
│   ├── load.py                  # → PostGIS
│   └── build_baseline.py        # r5py: compute baseline accessibility matrix
├── core/
│   ├── routing/
│   │   ├── engine.py            # thin r5py wrapper (build graph, travel-time matrix)
│   │   └── scenarios.py         # apply a network modification, recompute
│   ├── accessibility.py         # matrix → jobs-reachable-in-60min per tract
│   ├── equity.py                # weighting/overlay logic (weights are inputs)
│   └── diff.py                  # baseline vs scenario delta
├── repositories/                # data-access layer (swappable storage)
│   ├── base.py                  # interface
│   └── postgres.py              # PostGIS implementation
├── api/                         # FastAPI
│   ├── main.py
│   └── routes/
│       ├── baseline.py          # GET tract scores as GeoJSON
│       ├── scenarios.py         # GET canned scenarios
│       └── scenario.py          # POST modified network → diff
├── web/                         # Next.js
│   └── src/
│       ├── components/Map.tsx           # MapLibre choropleth
│       ├── components/ScenarioPanel.tsx # toggles
│       ├── components/EquitySliders.tsx # adjustable weights
│       └── components/DiffPanel.tsx     # before/after breakdown
└── docs/
    └── scaling-to-statewide.md  # the Snowflake plan (see §8)
```

---

## 5. Data sources (concrete)

- **LODES** (LEHD Origin-Destination, latest LODES8 vintage): CA "main" OD file. Keep pairs where **home block ∈ San Joaquin County** and **work block ∈ Bay Area** (Santa Clara, Alameda, San Francisco, San Mateo, Contra Costa). Aggregate home → tract. Note the multi-year lag in the writeup.
- **ACS 5-year** (Census API): `B08303` travel time (use 90+ min bucket for super-commuter share), `B08301` mode, worked-from-home, `B19013` median income, `B25064` median rent. Tract level, SJ County.
- **GTFS:** ACE + San Joaquin RTD feeds (gtfs.ca.gov / transit.land / Mobility Database). Optionally Bay Area feeds for the destination side.
- **OSM:** street + pedestrian network for SJ County + relevant Bay corridors (osmnx or a Geofabrik NorCal extract).
- **Job destinations:** LODES workplace-area characteristics (WAC) for Bay Area job counts by block, aggregated to destination tracts.

---

## 6. Key interfaces

**`core/routing/engine.py`**
- `build_network(osm_path, gtfs_paths) -> TransportNetwork`
- `travel_time_matrix(network, origins, destinations, departure, max_time=60) -> DataFrame`

**`core/routing/scenarios.py`**
- `apply_scenario(base_network, scenario) -> TransportNetwork` — scenario = added station(s)/route(s) as modified GTFS.

**`core/accessibility.py`**
- `jobs_reachable(ttm, job_counts, cutoff_min=60) -> Series` (per origin tract)

**`core/equity.py`**
- `weighted_score(access, equity_layers, weights: dict) -> Series` — weights supplied at call time, never hardcoded.

**`core/diff.py`**
- `diff(baseline_access, scenario_access) -> DataFrame` (delta per tract)

**API**
- `GET /baseline` → GeoJSON: tract geometry + baseline jobs-reachable + equity layers
- `GET /scenarios` → list of canned scenarios
- `POST /scenario` → body: scenario def + equity weights → GeoJSON diff. **Serve canned scenarios from cache; only invoke R5 for custom ones.**

---

## 7. Build phases (each ships something demoable — do them in order)

**Phase 0 — Scaffold.** Repo structure, docker-compose Postgres+PostGIS, empty modules, CI lint. *Done when: `docker compose up` gives a working DB and the FastAPI healthcheck responds.*

**Phase 1 — Data pipeline.** Implement `pipeline/sources/*` and `load.py`. *Done when: LODES/ACS/GTFS/OSM are loaded into PostGIS and queryable via the repository layer.*

**Phase 2 — Baseline accessibility.** `build_baseline.py` using r5py → jobs-reachable per tract, cached. `GET /baseline`. Frontend choropleth. *Done when: the map shows the red/green baseline. THIS IS ALREADY A DEMO.*

**Phase 3 — Scenario + diff (MVP).** `scenarios.py`, `diff.py`, canned scenarios (incl. "Manteca ACE station opens"), `GET /scenarios` + `POST /scenario`, scenario toggle + diff panel in UI. *Done when: toggling a scenario shows the before/after delta. THIS IS THE MVP.*

**Phase 4 — Equity overlay.** `equity.py`, equity layers in `/baseline`, adjustable weight sliders driving recompute. *Done when: sliders change the weighted ranking live.*

**Phase 5 — Polish + deploy.** Cloud Run + Vercel + Supabase/Cloud SQL, loading states, methodology writeup, README. *Done when: it's live at a public URL.*

**Phase 6 (companion, parallel) — ArcGIS track.** Candidate-site suitability in ArcGIS Pro (parcels ≥ ~2 acres near top-decile tracts, within ~800m of an interchange, non-residential). Publish baseline findings as an ArcGIS Online StoryMap. *This is a separate deliverable beside the app, not a dependency of it.*

Ship Phases 1–3 and you have a portfolio piece. Phases 4–6 make it stand out.

---

## 8. Scaling to statewide (documented, NOT built now)

Today: county-scale, on Postgres, because that fits and never strains. Do **not**
deploy Snowflake for this project — it targets a bottleneck we don't have (our
expensive path is R5 recompute, which a warehouse doesn't help).

Architect for a contained future swap: all storage access goes through
`repositories/base.py`. If this grew to all 58 CA counties + multi-year ACS +
statewide GTFS, a Snowflake implementation of that interface (plus dbt transforms)
would slot in without touching business logic. Full plan lives in
`docs/scaling-to-statewide.md`. A real Snowflake deployment belongs in a *separate*
statewide project where the data volume genuinely earns it.

---

## 9. Engineering constraints / gotchas

- **R5 needs RAM** to hold the network graph — size the Cloud Run instance, or precompute baseline offline and serve cached results; the public app mostly reads cache and only calls R5 for live custom scenarios.
- **Precompute + cache the baseline** and all canned scenarios; don't recompute per request.
- **Departure time matters** — accessibility depends on the schedule snapshot; pick a fixed representative weekday AM departure and state it.
- **Be transparent about assumptions** (cutoff, what counts as a reachable job, walk speed, equity weights). Surfacing them in the UI is the answer to "isn't this just your opinion as a map?"
- **LODES quirks:** primary-jobs-only, differential-privacy noise at fine geography, multi-year lag, weak on remote work — add an ACS worked-from-home layer so the model accounts for WFH rather than ignoring it.

---

## 10. Non-goals

- No road-traffic simulation / congestion modeling / dynamic assignment.
- No custom routing engine.
- No predictive ML model.
- Not a general planner tool — it's public-facing, opinionated, single-question, single-region.
