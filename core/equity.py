"""Equity weighting. Weights are ALWAYS caller-supplied (UI sliders) — never hardcoded.

The weighted score answers: "which tracts matter most, given what the user says
matters?" A tract scores high when it has high need on the dimensions the user
weighted up. Multiplying by accessibility gain (the diff) then ranks where a
scenario helps the people who need it most.
"""

import pandas as pd

# Layers the UI exposes. Direction: +1 = more of this means more need,
# -1 = less of this means more need (income).
LAYER_DIRECTION = {
    "supercommuter_share": 1,
    "long_commute_share": 1,
    "renter_share": 1,
    "transit_share": 1,
    "median_income": -1,
    "median_rent": -1,
}


def _normalize(s: pd.Series) -> pd.Series:
    """Min-max to [0, 1]; constant or all-NaN layers become 0 (no signal)."""
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or hi == lo:
        return pd.Series(0.0, index=s.index)
    return ((s - lo) / (hi - lo)).fillna(0.0)


def need_index(equity_layers: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Weighted composite need per tract, in [0, 1].

    equity_layers: indexed by tract GEOID, columns from LAYER_DIRECTION.
    weights: layer name -> weight (any nonnegative scale; normalized here).
    Unknown layer names are rejected loudly rather than silently ignored.
    """
    unknown = set(weights) - set(LAYER_DIRECTION)
    if unknown:
        raise KeyError(f"unknown equity layers: {sorted(unknown)}")

    total = sum(weights.values())
    if total <= 0:
        return pd.Series(0.0, index=equity_layers.index, name="need")

    acc = pd.Series(0.0, index=equity_layers.index)
    for layer, w in weights.items():
        norm = _normalize(equity_layers[layer])
        if LAYER_DIRECTION[layer] < 0:
            norm = 1.0 - norm
        acc += (w / total) * norm
    return acc.rename("need")


def weighted_score(
    access: pd.Series,
    equity_layers: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """access (jobs reachable, or diff delta) x composite need -> equity-weighted score.

    Aligned on tract GEOID index. With all-zero weights this degrades to raw access.
    """
    need = need_index(equity_layers, weights)
    if (need == 0).all():
        return access.rename("weighted_score").astype(float)
    return (access * need.reindex(access.index).fillna(0.0)).rename("weighted_score")
