# Build plan — stages and steps

Adapted from CLAUDE.md §7 for this machine: **no Docker**; storage is a
file-backed (GeoParquet) repository by default, PostGIS implementation kept
behind the same interface. One commit per step.

## Stage 0 — Scaffold
1. Repo structure, pyproject, .gitignore, docs, spec copied in
2. Python venv + FastAPI `GET /health` running
3. Next.js scaffold in `web/`, map prototype ported to `components/Map.tsx`

**Done when:** API healthcheck responds; frontend shows the map.

## Stage 1 — Data pipeline
1. Tract geometries (TIGER cartographic boundaries, SJ County)
2. `sources/acs.py` — ACS 5-yr: B08303 (90+ min super-commuters), B08301 mode/WFH, B19013 income, B25064 rent
3. `sources/lodes.py` — LODES8 CA OD (home ∈ SJ, work ∈ 5 Bay counties) + WAC job counts by destination
4. `sources/gtfs.py` — ACE + SJ RTD feeds, validated
5. `sources/osm.py` — Geofabrik extract clipped to SJ + Altamont corridor
6. `repositories/` layer + `load.py`; run the pipeline end-to-end

**Done when:** all datasets queryable through the repository layer.

## Stage 2 — Baseline accessibility (first demo)
1. Portable JDK 21 (Java 8 on this machine won't run R5); r5py installed
2. `core/routing/engine.py` — build_network, travel_time_matrix (fixed weekday AM departure, documented)
3. `pipeline/build_baseline.py` — tract-to-tract matrix → cached
4. `core/accessibility.py` — jobs reachable in 60 min per tract
5. `GET /baseline` GeoJSON; frontend choropleth replaces placeholder circles

**Done when:** the red/green baseline map renders from real data.

## Stage 3 — Scenario + diff (MVP)
1. `core/routing/scenarios.py` — scenario = modified GTFS, recompute
2. `core/diff.py` — per-tract delta
3. Canned scenarios (Manteca ACE station, feeder bus, frequency bump), precomputed
4. `GET /scenarios` + `POST /scenario`
5. UI: scenario toggle, diverging diff choropleth, headline delta panel

**Done when:** toggling a scenario shows before/after delta.

## Stage 4 — Equity overlay
1. `core/equity.py` — weighted_score(access, layers, weights) — weights always inputs
2. Equity layers wired into `/baseline` payload
3. EquitySliders — reweighting happens client-side, live
4. "Who gains most" ranking tied to active scenario

**Done when:** sliders change the ranking live.

## Stage 5 — Polish + deploy
Cloud Run (API) + Vercel (web) + Supabase (Postgres impl of the repository
interface). Methodology page surfacing all assumptions. README + screenshots.

## Stage 6 — ArcGIS companion (parallel)
Suitability analysis (ArcGIS Pro) + StoryMap. Independent deliverable.

---

**Critical path:** 0 → 1 → 2 → 3. **Riskiest step:** 2.1–2.2 (r5py + JDK on
Windows) — spike early with a toy network before the full pipeline data lands.
