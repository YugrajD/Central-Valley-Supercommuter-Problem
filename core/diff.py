"""Baseline vs scenario — the headline number."""

import pandas as pd


def diff(baseline_access: pd.Series, scenario_access: pd.Series) -> pd.DataFrame:
    """Per-tract delta. Indexed by tract GEOID.

    Columns: baseline, scenario, delta, pct_change (NaN where baseline is 0 —
    a tract going from 0 to anything is an infinite improvement; the UI shows
    the absolute delta there instead).
    """
    out = pd.DataFrame(
        {
            "baseline": baseline_access,
            "scenario": scenario_access.reindex(baseline_access.index),
        }
    )
    out["delta"] = out["scenario"] - out["baseline"]
    base = out["baseline"].where(out["baseline"] > 0)
    out["pct_change"] = out["delta"] / base
    return out


def headline(d: pd.DataFrame, top_n: int = 5) -> dict:
    """Summary for the diff panel: total delta, tracts improved, biggest winners."""
    gainers = d[d["delta"] > 0].sort_values("delta", ascending=False)
    return {
        "total_delta": int(d["delta"].sum()),
        "tracts_improved": int((d["delta"] > 0).sum()),
        "tracts_worsened": int((d["delta"] < 0).sum()),
        "top_gainers": [
            {"geoid": geoid, "delta": int(row["delta"]), "baseline": int(row["baseline"])}
            for geoid, row in gainers.head(top_n).iterrows()
        ],
    }
