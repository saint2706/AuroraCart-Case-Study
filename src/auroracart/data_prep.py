"""Shared data loading, cleaning and feature-engineering for the AuroraCart case study.

Both the EDA notebook and the dashboard import `load_data()` from this module so the
two artifacts never drift apart on what "clean" means.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from auroracart.paths import RAW_DATA_PATH

RAW_PATH = RAW_DATA_PATH

# Free-text values that mean the same thing but were typed inconsistently at source.
_CATEGORY_FIX = {
    "Home & kitchen": "Home & Kitchen",
    "Beauty and Personal Care": "Beauty & Personal Care",
}
_CHANNEL_FIX = {
    "organic search": "Organic Search",
    "Paid social": "Paid Social",
}

CATEGORY_ORDER = [
    "Electronics",
    "Home & Kitchen",
    "Fashion",
    "Sports & Fitness",
    "Beauty & Personal Care",
]
REGION_ORDER = ["North", "South", "East", "West", "Central"]
FULFILLMENT_ORDER = ["Express Delivery", "Standard Delivery", "Store Pickup"]
PROMOTION_ORDER = ["No Promotion", "Category Offer", "Member Offer", "Festival Sale", "Flash Deal"]
SEGMENT_ORDER = ["Premium", "Family", "Value Seeker", "Occasional"]
LOYALTY_ORDER = ["New", "Developing", "Loyal", "Champion"]


def load_data(raw_path: Path | str = RAW_PATH) -> pd.DataFrame:
    """Load the raw AuroraCart export and return an analysis-ready DataFrame.

    Cleaning steps applied (see the EDA notebook for the audit that justified each one):
      1. Drop exact duplicate rows (order re-submitted into the export twice).
      2. Standardize inconsistent category / acquisition-channel spelling & casing.
      3. Parse Order_Date and derive calendar helper columns.
      4. Recode structurally-missing categoricals into an explicit label rather than NaN
         (e.g. no promotion applied, no paid membership).
      5. Leave *numerically* missing fields (rating, margin, recency) as NaN — they are
         genuinely unknown/inapplicable, not something to impute, and every aggregation
         below uses skipna semantics.
      6. Engineer the KPI columns the dashboard and notebook both plot.
    """
    df = pd.read_csv(raw_path)

    df = df.drop_duplicates()

    df["Category"] = df["Category"].replace(_CATEGORY_FIX)
    df["Acquisition_Channel"] = df["Acquisition_Channel"].replace(_CHANNEL_FIX)

    df["Order_Date"] = pd.to_datetime(df["Order_Date"])
    df["Order_YearMonth"] = df["Order_Date"].dt.to_period("M").dt.to_timestamp()
    df["Order_Month_Label"] = df["Order_Date"].dt.strftime("%b %Y")

    df["Promotion_Type"] = df["Promotion_Type"].fillna("No Promotion")
    df["Membership_Type"] = df["Membership_Type"].fillna("No Membership")
    df["Age_Group"] = df["Age_Group"].fillna("Unknown")

    for col in ["Weekend_Flag", "Coupon_Used", "On_Time_Flag", "Return_Flag",
                "Cancellation_Flag", "Complaint_Flag"]:
        df[col] = df[col].map({"Yes": True, "No": False}).astype(bool)

    # A cancelled order carries Net_Revenue = 0 by construction (confirmed 1:1 in the
    # source data) and should be excluded from revenue/margin analysis, but kept for
    # operations/cancellation-rate analysis.
    df["Is_Valid_Revenue"] = ~df["Cancellation_Flag"]

    df["Net_Margin_Pct"] = np.where(
        df["Net_Revenue"] > 0, df["Profit"] / df["Net_Revenue"] * 100, np.nan
    )

    df["Category"] = pd.Categorical(df["Category"], categories=CATEGORY_ORDER, ordered=True)
    df["Region"] = pd.Categorical(df["Region"], categories=REGION_ORDER, ordered=True)
    df["Fulfillment_Mode"] = pd.Categorical(
        df["Fulfillment_Mode"], categories=FULFILLMENT_ORDER, ordered=True
    )
    df["Promotion_Type"] = pd.Categorical(
        df["Promotion_Type"], categories=PROMOTION_ORDER, ordered=True
    )
    df["Customer_Segment"] = pd.Categorical(
        df["Customer_Segment"], categories=SEGMENT_ORDER, ordered=True
    )
    df["Loyalty_Status"] = pd.Categorical(
        df["Loyalty_Status"], categories=LOYALTY_ORDER, ordered=True
    )

    return df


def kpi_summary(df: pd.DataFrame) -> dict:
    """Headline KPIs computed over valid (non-cancelled) orders, for the overview tab."""
    valid = df[df["Is_Valid_Revenue"]]
    n_orders = len(df)
    n_valid = len(valid)
    revenue = valid["Net_Revenue"].sum()
    profit = valid["Profit"].sum()
    return {
        "orders": n_orders,
        "net_revenue": revenue,
        "profit": profit,
        "margin_pct": (profit / revenue * 100) if revenue else np.nan,
        "aov": (revenue / n_valid) if n_valid else np.nan,
        "avg_rating": valid["Customer_Rating"].mean(),
        "on_time_rate": df["On_Time_Flag"].mean() * 100,
        "return_rate": df["Return_Flag"].mean() * 100,
        "cancellation_rate": df["Cancellation_Flag"].mean() * 100,
        "complaint_rate": df["Complaint_Flag"].mean() * 100,
        "customers": df["Customer_ID"].nunique(),
    }


if __name__ == "__main__":
    data = load_data()
    print(f"Loaded {len(data):,} rows x {data.shape[1]} columns after cleaning")
    print(kpi_summary(data))
