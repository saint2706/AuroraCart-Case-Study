"""Guards on the numbers the deck and the docs quote.

These are not regression snapshots of the whole analysis — they pin the handful
of claims a reader could check against the dataset, plus the arithmetic
properties that would silently corrupt every downstream number if they broke.
"""

import pandas as pd
import pytest

from auroracart import analysis as A
from auroracart.data_prep import load_data


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load_data()


@pytest.fixture(scope="module")
def facts(df) -> dict:
    return A.headline_facts(df)


def test_margin_excludes_cancelled_orders(df):
    """Cancelled orders in the denominator would dilute margin toward zero."""
    with_cancelled = df["Profit"].sum() / df["Net_Revenue"].sum() * 100
    assert A.margin_pct(A.valid_revenue(df)) == pytest.approx(with_cancelled, rel=0.05)
    assert A.margin_pct(A.valid_revenue(df)) > with_cancelled


def test_decomposition_adds_up(df):
    """mix + rate + interaction must reconstruct the observed margin change."""
    d = A.decompose_margin_change(df)
    assert d.mix_effect + d.rate_effect + d.interaction == pytest.approx(d.total_change, abs=1e-9)


def test_margin_decline_is_mostly_within_category(facts):
    """Question 2's core claim: this is rate erosion, not a mix shift."""
    assert facts["rate_share_pct"] > 85
    assert abs(facts["rate_effect_pp"]) > abs(facts["mix_effect_pp"]) * 5


def test_growth_outpaced_profit_after_accelerate(facts):
    assert facts["accelerate_revenue_per_month_growth_pct"] > 50
    assert facts["accelerate_profit_per_month_growth_pct"] < 25
    assert facts["accelerate_margin_after"] < facts["accelerate_margin_before"]


def test_product_mix_outranks_geography(df):
    """Question 3's conclusion, stated as an ordering rather than a value."""
    ranking = A.driver_ranking(df).set_index("Dimension")
    assert ranking.index[0] in {"Subcategory", "Category", "Price_Band"}
    assert ranking.loc["Category", "Weighted_SD_pp"] > ranking.loc["Region", "Weighted_SD_pp"] * 10
    assert (
        ranking.loc["Category", "Weighted_SD_pp"]
        > ranking.loc["Fulfillment_Mode", "Weighted_SD_pp"] * 10
    )


def test_premium_paradox_is_a_category_mix_artifact(facts):
    """Question 4: pooled and split views must disagree, or there is no lesson."""
    assert facts["premium_margin_pooled"] < 5
    assert facts["premium_margin_ex_electronics"] > 20
    assert facts["premium_electronics_share"] > 60


def test_electronics_is_a_cost_problem_not_a_discount_problem(df, facts):
    """Electronics discounts sit at the company norm; its cost ratio does not."""
    assert facts["electronics_product_cost_pct"] > 90
    discounts = A.group_economics(df, "Category")["Avg_Discount"]
    assert discounts.max() - discounts.min() < 1.0


def test_discount_tolerance_differs_by_category(df):
    """The argument against a single company-wide discount ceiling."""
    breakeven = A.breakeven_discount(df).set_index("Category")
    assert breakeven.loc["Electronics", "First_Loss_Band"] == "10–15%"
    assert breakeven.loc["Fashion", "First_Loss_Band"] == "none observed"


def test_logistics_contract_improved_service(facts):
    assert facts["on_time_after_contract"] > facts["on_time_before_contract"] + 15
    assert facts["complaint_after_contract"] < facts["complaint_before_contract"]
    assert facts["delivery_cost_after_contract"] > facts["delivery_cost_before_contract"]


def test_peak_season_gap_persists_every_year(df):
    peak = A.peak_season_gap(df)
    assert (peak["Gap_pp"] > 15).all(), "Oct–Nov collapse should show in every year"


def test_group_economics_shares_sum_to_100(df):
    assert A.group_economics(df, "Category")["Revenue_Share_Pct"].sum() == pytest.approx(100.0)
