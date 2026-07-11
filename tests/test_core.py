"""Unit tests for the pure-logic core: accessibility, equity, diff."""

import pandas as pd
import pytest

from core.accessibility import jobs_reachable
from core.diff import diff, headline
from core.equity import need_index, weighted_score


def make_ttm() -> pd.DataFrame:
    # two origins: A reaches t1 (30min) and t2 (59min); B reaches nothing in 60
    return pd.DataFrame(
        {
            "from_id": ["A", "A", "A", "B", "B", "B"],
            "to_id": ["t1", "t2", "t3", "t1", "t2", "t3"],
            "travel_time": [30.0, 59.0, 75.0, 90.0, None, 120.0],
        }
    )


JOBS = pd.DataFrame({"work_tract": ["t1", "t2", "t3"], "jobs": [1000, 500, 9999]})


class TestJobsReachable:
    def test_counts_within_cutoff(self):
        result = jobs_reachable(make_ttm(), JOBS, cutoff_min=60)
        assert result["A"] == 1500  # t1 + t2, not t3

    def test_stranded_origin_gets_zero_not_nan(self):
        result = jobs_reachable(make_ttm(), JOBS, cutoff_min=60)
        assert result["B"] == 0

    def test_cutoff_respected(self):
        result = jobs_reachable(make_ttm(), JOBS, cutoff_min=90)
        assert result["A"] == 1500 + 9999
        assert result["B"] == 1000


LAYERS = pd.DataFrame(
    {
        "supercommuter_share": [0.30, 0.10, 0.00],
        "median_income": [40_000, 80_000, 160_000],
        "renter_share": [0.8, 0.4, 0.1],
        "long_commute_share": [0.5, 0.2, 0.1],
        "transit_share": [0.1, 0.05, 0.01],
        "median_rent": [900, 1500, 2500],
    },
    index=pd.Index(["poor_far", "mid", "rich_close"], name="geoid"),
)


class TestEquity:
    def test_need_ranks_disadvantage_first(self):
        need = need_index(LAYERS, {"supercommuter_share": 1, "median_income": 1})
        assert need["poor_far"] > need["mid"] > need["rich_close"]

    def test_income_direction_inverted(self):
        need = need_index(LAYERS, {"median_income": 1})
        assert need["poor_far"] == 1.0 and need["rich_close"] == 0.0

    def test_zero_weights_degrade_to_raw_access(self):
        access = pd.Series([100, 200, 300], index=LAYERS.index)
        score = weighted_score(access, LAYERS, {})
        pd.testing.assert_series_equal(
            score, access.astype(float), check_names=False
        )

    def test_unknown_layer_rejected(self):
        with pytest.raises(KeyError):
            need_index(LAYERS, {"not_a_layer": 1})

    def test_weights_shift_ranking(self):
        access = pd.Series([10, 10, 10], index=LAYERS.index)
        by_income = weighted_score(access, LAYERS, {"median_income": 1})
        assert by_income.idxmax() == "poor_far"


class TestDiff:
    def test_delta(self):
        base = pd.Series([100, 0], index=pd.Index(["A", "B"], name="geoid"))
        scen = pd.Series([150, 40], index=pd.Index(["A", "B"], name="geoid"))
        d = diff(base, scen)
        assert d.loc["A", "delta"] == 50
        assert d.loc["B", "delta"] == 40
        assert d.loc["A", "pct_change"] == 0.5
        assert pd.isna(d.loc["B", "pct_change"])  # from zero: no pct, absolute only

    def test_headline(self):
        base = pd.Series([100, 0, 50], index=pd.Index(["A", "B", "C"], name="geoid"))
        scen = pd.Series([150, 40, 30], index=pd.Index(["A", "B", "C"], name="geoid"))
        h = headline(diff(base, scen))
        assert h["total_delta"] == 50 + 40 - 20
        assert h["tracts_improved"] == 2
        assert h["tracts_worsened"] == 1
        assert h["top_gainers"][0]["geoid"] == "A"
