"""The cleaning contract the notebook and the dashboard both depend on."""

import pandas as pd
import pytest

from auroracart.data_prep import CATEGORY_ORDER, kpi_summary, load_data
from auroracart.paths import RAW_DATA_PATH


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load_data()


def test_raw_data_is_where_paths_says_it_is():
    assert RAW_DATA_PATH.exists(), f"missing dataset at {RAW_DATA_PATH}"


def test_duplicates_are_dropped(df):
    raw = pd.read_csv(RAW_DATA_PATH)
    assert raw.duplicated().any(), "fixture should still contain the seeded duplicates"
    assert not df.duplicated().any()


def test_category_labels_are_standardised(df):
    assert set(df["Category"].cat.categories) == set(CATEGORY_ORDER)
    assert "Home & kitchen" not in df["Category"].astype(str).unique()


def test_acquisition_channel_labels_are_standardised(df):
    channels = set(df["Acquisition_Channel"].unique())
    assert "organic search" not in channels
    assert "Paid social" not in channels


def test_cancelled_orders_are_flagged_not_dropped(df):
    """Cancelled orders leave the revenue denominator but stay in operations rates."""
    cancelled = df[df["Cancellation_Flag"]]
    assert len(cancelled) > 0
    assert not cancelled["Is_Valid_Revenue"].any()
    assert (cancelled["Net_Revenue"] == 0).all()


def test_ratings_are_left_missing_rather_than_imputed(df):
    assert df["Customer_Rating"].isna().any()
    assert df["Customer_Rating"].dropna().between(1.0, 5.0).all()


def test_kpi_margin_is_revenue_weighted(df):
    kpis = kpi_summary(df)
    valid = df[df["Is_Valid_Revenue"]]
    expected = valid["Profit"].sum() / valid["Net_Revenue"].sum() * 100
    assert kpis["margin_pct"] == pytest.approx(expected)
    # And it is *not* the mean of the order-level ratio — the trap this guards.
    assert kpis["margin_pct"] != pytest.approx(valid["Profit_Margin"].mean(), rel=1e-3)
