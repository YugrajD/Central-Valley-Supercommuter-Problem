# Methodology & assumptions

Every number this tool shows depends on choices listed here. They are surfaced
deliberately — "isn't this just your opinion as a map?" deserves a checkable
answer.

## The measure

**Bay Area jobs reachable within 60 minutes** (also computed at 45/75/90) from
each San Joaquin County census tract, by scheduled public transit, for a
departure between **6:30 and 7:30 AM on a representative Wednesday**
(2026-07-08). Travel time is the median over that window (R5, Conveyal's
routing engine, via r5py — we never write routing math).

## Access model (the assumption that matters most)

- **First mile:** walk **or drive to the boarding station (park-and-ride)** —
  matching observed ACE commuter behavior. Walk-only access makes every exurban
  tract unreachable (tract centroids sit 60–90+ minutes' walk from stations)
  and the tool degenerates to a map of zeros.
- **Last mile:** walk only. If you can't walk to the job from the alighting
  stop, the job doesn't count.
- Origins/destinations are tract **representative points** — block-level detail
  is smoothed; small tracts fare better than sprawling ones.

## Data

| Data | Source | Vintage | Caveats |
|---|---|---|---|
| Jobs by work tract | LODES8 WAC (C000) | 2022 | primary jobs; DP noise at block level (we aggregate to tract); lags ACS |
| Home→work flows | LODES8 OD, SJ home → 5 Bay counties | 2022 | 90,772 commuters; same caveats |
| Equity layers | ACS 5-year via data.census.gov | 2019–2023 | tract medians suppressed in a few tracts |
| Schedules | GTFS: ACE (MobilityData mirror), SJ RTD | mid-2026 service | no BART/Caltrain/VTA — see below |
| Streets/walk | OSM (Geofabrik NorCal, clipped) | July 2026 | routable ways only |

**Feed coverage:** only ACE + SJ RTD are loaded, so destination-side transit
transfers (BART, VTA) don't exist in the model. Jobs are counted only where the
**alighting station's walkshed** reaches them. That biases *against* reachability
— treat absolute counts as floors; deltas between scenarios are the reliable
signal.

**Remote work:** LODES barely sees it. The ACS worked-from-home share ships as
its own equity layer instead of pretending the flows capture it.

## The headline finding (baseline)

With walk-only access, **zero** Bay Area jobs are reachable within 90 minutes
from every SJ tract. Even with park-and-ride access, reachability under 60
minutes is confined to tracts near stations on the western county edge. That
asymmetry — 90k people commute out daily, transit serves almost none of them
inside an hour — is the problem the scenarios probe.

## Equity weighting

`weighted_score = access × need`, where need is a min-max-normalized composite
of the layers the **user** weights (super-commuter share, long commutes, renter
share, transit share, low income, low rent). Weights are never hardcoded; the
sliders are the argument.
