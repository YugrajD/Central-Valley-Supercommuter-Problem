"""Travel-time matrix -> the one number: jobs reachable within the cutoff, per origin tract."""

import pandas as pd


def jobs_reachable(
    ttm: pd.DataFrame,
    job_counts: pd.DataFrame,
    cutoff_min: int = 60,
) -> pd.Series:
    """Count jobs reachable within `cutoff_min` from each origin tract.

    ttm: columns [from_id, to_id, travel_time] (minutes; NaN = unreachable),
         as returned by r5py's TravelTimeMatrix.
    job_counts: columns [work_tract, jobs].

    Returns a Series indexed by origin tract GEOID. Origins present in the
    matrix but with nothing reachable get 0, not NaN — "stranded" is a value.
    """
    reachable = ttm[ttm["travel_time"].notna() & (ttm["travel_time"] <= cutoff_min)]
    merged = reachable.merge(job_counts, left_on="to_id", right_on="work_tract", how="left")
    per_origin = merged.groupby("from_id")["jobs"].sum()

    all_origins = pd.Index(ttm["from_id"].unique(), name="geoid")
    return per_origin.reindex(all_origins, fill_value=0).rename("jobs_reachable").astype("int64")
