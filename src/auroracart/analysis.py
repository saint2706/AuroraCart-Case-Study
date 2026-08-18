"""Case-question metrics, computed once and shared by every deliverable.

The notebook, the dashboard, the figure builder and the slide deck all import
from here, so a number quoted on a slide is the same number the dashboard draws
and the same number the notebook printed. Nothing in this module plots.

Two conventions run through all of it, and both are deliberate:

**Margin is always ``sum(profit) / sum(revenue)``, never ``mean(Profit_Margin)``.**
Averaging an order-level ratio weights a ₹400 lipstick order the same as a
₹90,000 smartphone order, which is exactly how a technically-correct metric
produces a wrong managerial answer. Every margin below is revenue-weighted.

**Revenue analysis excludes cancelled orders; operations analysis does not.**
Cancelled orders recognise zero net revenue by construction, so leaving them in
a margin denominator silently dilutes it. They stay in the denominator for
cancellation, complaint and on-time rates, where they are the subject.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- events

ACCELERATE_START = pd.Timestamp("2024-07-01")
"""Accelerate 2.0 — the growth program launched in July 2024 (case §3)."""

LOGISTICS_START = pd.Timestamp("2025-01-01")
"""The last-mile logistics contract restructured in January 2025 (case §3)."""

PEAK_MONTHS = (10, 11)
"""October–November festive peak, where delivery performance collapses every year."""

# Dimensions offered to the driver ranking. Ordered roughly product -> commercial
# -> customer -> geography so the output table reads as a narrative.
DRIVER_DIMENSIONS: tuple[str, ...] = (
    "Subcategory",
    "Category",
    "Price_Band",
    "Brand_Tier",
    "Promotion_Type",
    "Coupon_Used",
    "Acquisition_Channel",
    "Customer_Segment",
    "Loyalty_Status",
    "Membership_Type",
    "New_vs_Returning",
    "Fulfillment_Mode",
    "Urban_Tier",
    "Region",
    "State",
)

# --------------------------------------------------------------------------- core


def valid_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Orders that recognise revenue — i.e. everything not cancelled."""
    return df[df["Is_Valid_Revenue"]]


def margin_pct(df: pd.DataFrame) -> float:
    """Revenue-weighted contribution margin, in percentage points."""
    revenue = df["Net_Revenue"].sum()
    return float(df["Profit"].sum() / revenue * 100) if revenue else float("nan")


def group_economics(
    df: pd.DataFrame, dim: str | list[str], *, sort_by: str = "Revenue", ascending: bool = False
) -> pd.DataFrame:
    """Revenue, profit, revenue-weighted margin and discount depth for one cut.

    Operates on valid-revenue orders only; ``dim`` may be a single column or a
    list for a crosstab-style cut.
    """
    valid = valid_revenue(df)
    grouped = valid.groupby(dim, observed=True).agg(
        Orders=("Order_ID", "size"),
        Revenue=("Net_Revenue", "sum"),
        Profit=("Profit", "sum"),
        Avg_Discount=("Discount_Percentage", "mean"),
        AOV=("Net_Revenue", "mean"),
    )
    grouped = grouped[grouped["Revenue"] > 0]
    grouped["Margin_Pct"] = grouped["Profit"] / grouped["Revenue"] * 100
    grouped["Revenue_Share_Pct"] = grouped["Revenue"] / valid["Net_Revenue"].sum() * 100
    return grouped.sort_values(sort_by, ascending=ascending)


def annual_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue, profit and margin by calendar year — the Context slide's numbers."""
    valid = valid_revenue(df)
    by_year = valid.groupby(valid["Order_Date"].dt.year).agg(
        Orders=("Order_ID", "size"),
        Revenue=("Net_Revenue", "sum"),
        Profit=("Profit", "sum"),
        Avg_Discount=("Discount_Percentage", "mean"),
    )
    by_year["Margin_Pct"] = by_year["Profit"] / by_year["Revenue"] * 100
    by_year.index.name = "Year"
    return by_year


# --------------------------------------------------------------------------- Q2: growth vs value


@dataclass(frozen=True)
class MixDecomposition:
    """How much of a margin change is *mix* versus *within-group rate*.

    ``mix_effect`` re-weights the base year's group margins with the later
    year's revenue mix; ``rate_effect`` holds the mix fixed and lets the group
    margins move. They sum to the total change up to a small interaction
    residual, which is reported rather than hidden.
    """

    base_year: int
    final_year: int
    base_margin: float
    final_margin: float
    mix_effect: float
    rate_effect: float
    interaction: float

    @property
    def total_change(self) -> float:
        return self.final_margin - self.base_margin

    @property
    def rate_share_pct(self) -> float:
        """Share of the total change attributable to within-group rate erosion."""
        return abs(self.rate_effect) / (abs(self.mix_effect) + abs(self.rate_effect)) * 100


def decompose_margin_change(
    df: pd.DataFrame,
    dim: str = "Category",
    base_year: int | None = None,
    final_year: int | None = None,
) -> MixDecomposition:
    """Split a margin change into product-mix shift vs within-group erosion.

    This is the analytical core of Question 2. "We grew into a worse mix" and
    "the things we already sold got less profitable" imply completely different
    managerial responses, and only a decomposition tells them apart.
    """
    valid = valid_revenue(df).copy()
    valid["Year"] = valid["Order_Date"].dt.year
    years = sorted(valid["Year"].unique())
    base_year = int(base_year if base_year is not None else years[0])
    final_year = int(final_year if final_year is not None else years[-1])

    grouped = valid.groupby(["Year", dim], observed=True).agg(
        Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum")
    )
    revenue = grouped["Revenue"].unstack(fill_value=0.0)
    rate = (grouped["Profit"] / grouped["Revenue"] * 100).unstack()

    weight_base = revenue.loc[base_year] / revenue.loc[base_year].sum()
    weight_final = revenue.loc[final_year] / revenue.loc[final_year].sum()
    rate_base = rate.loc[base_year].fillna(0.0)
    rate_final = rate.loc[final_year].fillna(0.0)

    base_margin = float((weight_base * rate_base).sum())
    final_margin = float((weight_final * rate_final).sum())
    mix_effect = float(((weight_final - weight_base) * rate_base).sum())
    rate_effect = float((weight_base * (rate_final - rate_base)).sum())
    interaction = (final_margin - base_margin) - mix_effect - rate_effect

    return MixDecomposition(
        base_year,
        final_year,
        base_margin,
        final_margin,
        mix_effect,
        rate_effect,
        float(interaction),
    )


def era_comparison(
    df: pd.DataFrame, boundary: pd.Timestamp, labels: tuple[str, str]
) -> pd.DataFrame:
    """Before/after a dated intervention, on the measures that intervention touches.

    Rates that describe operations (on-time, complaints, cancellations) use every
    order; the revenue and margin rows use valid-revenue orders only. Per-month
    figures normalise for unequal window lengths — without them, a longer window
    always looks bigger.
    """
    before, after = labels
    era = pd.Series(
        np.where(df["Order_Date"] < boundary, before, after), index=df.index, name="Era"
    )
    ops = df.groupby(era, observed=True)
    valid = valid_revenue(df)
    valid_era = era.loc[valid.index]
    rev = valid.groupby(valid_era, observed=True)

    months = valid.groupby(valid_era, observed=True)["Order_YearMonth"].nunique()
    out = pd.DataFrame(
        {
            "Orders": ops.size(),
            "Months_Observed": months,
            "Revenue": rev["Net_Revenue"].sum(),
            "Profit": rev["Profit"].sum(),
            "Revenue_Per_Month": rev["Net_Revenue"].sum() / months,
            "Profit_Per_Month": rev["Profit"].sum() / months,
            "Orders_Per_Month": rev.size() / months,
            "Margin_Pct": rev["Profit"].sum() / rev["Net_Revenue"].sum() * 100,
            "Avg_Discount_Pct": rev["Discount_Percentage"].mean(),
            "AOV": rev["Net_Revenue"].mean(),
            "Marketing_Pct_of_Revenue": rev["Marketing_Cost"].sum()
            / rev["Net_Revenue"].sum()
            * 100,
            "Delivery_Cost_Per_Order": ops["Delivery_Cost"].mean(),
            "On_Time_Pct": ops["On_Time_Flag"].mean() * 100,
            "Delivery_Delay_Days": ops["Delivery_Delay_Days"].mean(),
            "Avg_Rating": ops["Customer_Rating"].mean(),
            "Complaint_Pct": ops["Complaint_Flag"].mean() * 100,
            "Return_Pct": ops["Return_Flag"].mean() * 100,
            "New_Customer_Share_Pct": ops["New_vs_Returning"].apply(
                lambda s: (s == "New").mean() * 100
            ),
        }
    )
    return out.reindex([before, after])


def accelerate_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Before/after Accelerate 2.0 (July 2024)."""
    return era_comparison(df, ACCELERATE_START, ("Before Accelerate 2.0", "After Accelerate 2.0"))


def logistics_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Before/after the January 2025 logistics restructure."""
    return era_comparison(df, LOGISTICS_START, ("Before new contract", "After new contract"))


# --------------------------------------------------------------------------- Q3: hidden drivers


def driver_ranking(
    df: pd.DataFrame, dimensions: tuple[str, ...] = DRIVER_DIMENSIONS
) -> pd.DataFrame:
    """Rank candidate explanations of profitability by how much they actually split it.

    "Performance" here is contribution margin (revenue-weighted). For each
    dimension we report:

    ``Weighted_SD_pp``
        Revenue-weighted standard deviation of group margin around the company
        margin — ``sqrt(sum(w_g * (m_g - m)^2))``. This is the headline rank.
        Weighting by revenue is what stops a tiny, wild group from outranking a
        dimension that splits half the business.
    ``Margin_Range_pp``
        Best group margin minus worst — intuitive, but easily inflated by a
        thin group, which is why it does not drive the ranking.
    ``Profit_Gap_Mn``
        Rupees (millions) of contribution that below-average groups would add if
        each merely reached the company margin. This converts spread into money
        and is what makes the ranking actionable rather than statistical.
    """
    valid = valid_revenue(df)
    company_margin = margin_pct(valid)

    rows = []
    for dim in dimensions:
        if dim not in valid.columns:
            continue
        grouped = valid.groupby(dim, observed=True).agg(
            Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum")
        )
        grouped = grouped[grouped["Revenue"] > 0]
        if len(grouped) < 2:
            continue
        group_margin = grouped["Profit"] / grouped["Revenue"] * 100
        weight = grouped["Revenue"] / grouped["Revenue"].sum()
        # Shortfall only — groups already above the company margin contribute 0,
        # so this is "profit forgone", not a net of winners against losers.
        shortfall_pp = (company_margin - group_margin).clip(lower=0)
        rows.append(
            {
                "Dimension": dim,
                "Levels": len(grouped),
                "Worst_Margin_pp": group_margin.min(),
                "Best_Margin_pp": group_margin.max(),
                "Margin_Range_pp": group_margin.max() - group_margin.min(),
                "Weighted_SD_pp": float(
                    np.sqrt((weight * (group_margin - company_margin) ** 2).sum())
                ),
                "Profit_Gap_Mn": float((shortfall_pp / 100 * grouped["Revenue"]).sum() / 1e6),
            }
        )

    ranking = pd.DataFrame(rows).sort_values("Weighted_SD_pp", ascending=False)
    return ranking.reset_index(drop=True)


def cost_structure(df: pd.DataFrame, dim: str = "Category") -> pd.DataFrame:
    """Each cost component as a share of net revenue — *why* a group's margin is what it is.

    A margin chart says Electronics loses money; this says the merchandise
    itself costs 94% of what the order recognises, which points at pricing and
    procurement rather than at marketing or delivery.
    """
    valid = valid_revenue(df)
    grouped = valid.groupby(dim, observed=True).agg(
        Revenue=("Net_Revenue", "sum"),
        Product_Cost=("Product_Cost", "sum"),
        Delivery_Cost=("Delivery_Cost", "sum"),
        Marketing_Cost=("Marketing_Cost", "sum"),
        Operating_Cost=("Operating_Cost", "sum"),
        Profit=("Profit", "sum"),
    )
    out = pd.DataFrame(index=grouped.index)
    for component in ["Product_Cost", "Delivery_Cost", "Marketing_Cost", "Operating_Cost"]:
        out[f"{component}_Pct"] = grouped[component] / grouped["Revenue"] * 100
    out["Margin_Pct"] = grouped["Profit"] / grouped["Revenue"] * 100
    out["Revenue"] = grouped["Revenue"]
    return out.sort_values("Margin_Pct")


DISCOUNT_BANDS = [-0.01, 5, 10, 15, 20, 25, 100]
DISCOUNT_BAND_LABELS = ["0–5%", "5–10%", "10–15%", "15–20%", "20–25%", "25%+"]


def discount_band_margin(df: pd.DataFrame, split: str | None = None) -> pd.DataFrame:
    """Margin by discount depth — the evidence behind a category-aware discount ceiling.

    Pass ``split="Category"`` (or any column) to see how much discount each group
    can absorb before it stops making money. The break-even point differs by tens
    of points between categories, which is the whole argument against a single
    company-wide discount policy.
    """
    valid = valid_revenue(df).copy()
    valid["Discount_Band"] = pd.cut(
        valid["Discount_Percentage"], DISCOUNT_BANDS, labels=DISCOUNT_BAND_LABELS
    )
    keys = ["Discount_Band"] if split is None else [split, "Discount_Band"]
    grouped = valid.groupby(keys, observed=True).agg(
        Orders=("Order_ID", "size"), Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum")
    )
    grouped["Margin_Pct"] = grouped["Profit"] / grouped["Revenue"] * 100
    return grouped.reset_index()


def breakeven_discount(df: pd.DataFrame, dim: str = "Category") -> pd.DataFrame:
    """Highest discount band each group still clears break-even in.

    Reported as a band, not a precise point, because a band is what the data
    supports — an order-level regression would imply a false precision here.
    """
    banded = discount_band_margin(df, split=dim)
    rows = []
    for name, group in banded.groupby(dim, observed=True):
        profitable = group[group["Margin_Pct"] > 0]
        rows.append(
            {
                dim: name,
                "Last_Profitable_Band": profitable["Discount_Band"].iloc[-1]
                if len(profitable)
                else "none",
                "First_Loss_Band": (
                    group[group["Margin_Pct"] <= 0]["Discount_Band"].iloc[0]
                    if (group["Margin_Pct"] <= 0).any()
                    else "none observed"
                ),
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Q4: the misleading pair


def segment_margin_confound(
    df: pd.DataFrame, confounder: str = "Category", confound_level: str = "Electronics"
) -> pd.DataFrame:
    """The Premium-segment paradox, and its resolution.

    Pooled across categories, Premium looks like the company's worst segment.
    Split by whether the order is Electronics, Premium's margin is ordinary —
    it simply buys two thirds Electronics. Same data, opposite managerial
    conclusion: this is the Question 4 pair.
    """
    valid = valid_revenue(df)
    inside = valid[valid[confounder] == confound_level]
    outside = valid[valid[confounder] != confound_level]

    def by_segment(frame: pd.DataFrame, label: str) -> pd.Series:
        grouped = frame.groupby("Customer_Segment", observed=True).agg(
            Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum")
        )
        return (grouped["Profit"] / grouped["Revenue"] * 100).rename(label)

    mix = valid.pivot_table(
        index="Customer_Segment",
        columns=confounder,
        values="Net_Revenue",
        aggfunc="sum",
        observed=True,
    )
    share = (mix[confound_level] / mix.sum(axis=1) * 100).rename(f"{confound_level}_Share_Pct")

    return pd.concat(
        [
            by_segment(valid, "Margin_Pooled"),
            by_segment(inside, f"Margin_In_{confound_level}"),
            by_segment(outside, f"Margin_Ex_{confound_level}"),
            share,
        ],
        axis=1,
    )


# --------------------------------------------------------------------------- operations


def monthly_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly delivery and experience series, flagged for peak months.

    The company-wide on-time average (~43%) is the single most misleading number
    in this dataset: it pools a genuine step change in January 2025 with a
    festive-season collapse that recurs every October–November.
    """
    monthly = df.groupby("Order_YearMonth").agg(
        Orders=("Order_ID", "size"),
        On_Time_Pct=("On_Time_Flag", "mean"),
        Delay_Days=("Delivery_Delay_Days", "mean"),
        Complaint_Pct=("Complaint_Flag", "mean"),
        Avg_Rating=("Customer_Rating", "mean"),
        Delivery_Cost=("Delivery_Cost", "mean"),
    )
    monthly["On_Time_Pct"] *= 100
    monthly["Complaint_Pct"] *= 100
    monthly["Is_Peak"] = monthly.index.month.isin(PEAK_MONTHS)
    monthly["Post_Logistics"] = monthly.index >= LOGISTICS_START
    return monthly


def peak_season_gap(df: pd.DataFrame) -> pd.DataFrame:
    """On-time attainment in the Oct–Nov peak versus the rest of the year, by year."""
    monthly = monthly_operations(df)
    frame = monthly.assign(
        Year=monthly.index.year, Window=np.where(monthly["Is_Peak"], "Oct–Nov peak", "Rest of year")
    )
    weighted = frame.groupby(["Year", "Window"], observed=True).apply(
        lambda g: np.average(g["On_Time_Pct"], weights=g["Orders"]), include_groups=False
    )
    return weighted.unstack().assign(Gap_pp=lambda d: d["Rest of year"] - d["Oct–Nov peak"])


def channel_economics(df: pd.DataFrame) -> pd.DataFrame:
    """Acquisition-channel contribution, with marketing cost as a share of the revenue it earned."""
    valid = valid_revenue(df)
    grouped = valid.groupby("Acquisition_Channel", observed=True).agg(
        Orders=("Order_ID", "size"),
        Revenue=("Net_Revenue", "sum"),
        Profit=("Profit", "sum"),
        Marketing_Cost=("Marketing_Cost", "sum"),
    )
    grouped["Margin_Pct"] = grouped["Profit"] / grouped["Revenue"] * 100
    grouped["Marketing_Pct_of_Revenue"] = grouped["Marketing_Cost"] / grouped["Revenue"] * 100
    grouped["Revenue_Share_Pct"] = grouped["Revenue"] / valid["Net_Revenue"].sum() * 100
    return grouped.sort_values("Margin_Pct")


def channel_economics_by_era(df: pd.DataFrame) -> pd.DataFrame:
    """Channel margin before and after Accelerate 2.0 — did the extra spend still pay?"""
    valid = valid_revenue(df).copy()
    valid["Era"] = np.where(valid["Order_Date"] < ACCELERATE_START, "Before", "After")
    grouped = valid.groupby(["Acquisition_Channel", "Era"], observed=True).agg(
        Revenue=("Net_Revenue", "sum"),
        Profit=("Profit", "sum"),
        Marketing_Cost=("Marketing_Cost", "sum"),
    )
    margin = (grouped["Profit"] / grouped["Revenue"] * 100).unstack()
    spend = (grouped["Marketing_Cost"] / grouped["Revenue"] * 100).unstack()
    out = pd.DataFrame(
        {
            "Margin_Before": margin["Before"],
            "Margin_After": margin["After"],
            "Margin_Change_pp": margin["After"] - margin["Before"],
            "Marketing_Pct_Before": spend["Before"],
            "Marketing_Pct_After": spend["After"],
        }
    )
    return out.sort_values("Margin_After")


# --------------------------------------------------------------------------- headline numbers


def headline_facts(df: pd.DataFrame) -> dict[str, float]:
    """Every number quoted in the deck and the docs, computed in one place.

    Anything that appears on a slide should be pulled from here rather than
    retyped, so the story cannot drift from the data.
    """
    valid = valid_revenue(df)
    years = annual_summary(df)
    accelerate = accelerate_comparison(df)
    logistics = logistics_comparison(df)
    decomposition = decompose_margin_change(df)
    categories = group_economics(df, "Category")
    subcategories = group_economics(df, "Subcategory")
    promotions = group_economics(df, "Promotion_Type")
    segments = segment_margin_confound(df)
    drivers = driver_ranking(df)
    peak = peak_season_gap(df)

    first_year, last_year = int(years.index[0]), int(years.index[-1])
    electronics = categories.loc["Electronics"]
    smartphones = subcategories.loc["Smartphones"]
    flash = promotions.loc["Flash Deal"]
    none_promo = promotions.loc["No Promotion"]

    return {
        "orders": float(len(df)),
        "customers": float(df["Customer_ID"].nunique()),
        "revenue_total": float(valid["Net_Revenue"].sum()),
        "profit_total": float(valid["Profit"].sum()),
        "margin_total": margin_pct(valid),
        "revenue_first_year": float(years.loc[first_year, "Revenue"]),
        "revenue_last_year": float(years.loc[last_year, "Revenue"]),
        "revenue_growth_pct": float(
            years.loc[last_year, "Revenue"] / years.loc[first_year, "Revenue"] * 100 - 100
        ),
        "margin_first_year": float(years.loc[first_year, "Margin_Pct"]),
        "margin_last_year": float(years.loc[last_year, "Margin_Pct"]),
        "margin_drop_pp": float(
            years.loc[first_year, "Margin_Pct"] - years.loc[last_year, "Margin_Pct"]
        ),
        "mix_effect_pp": decomposition.mix_effect,
        "rate_effect_pp": decomposition.rate_effect,
        "rate_share_pct": decomposition.rate_share_pct,
        "accelerate_revenue_per_month_growth_pct": float(
            accelerate["Revenue_Per_Month"].iloc[1] / accelerate["Revenue_Per_Month"].iloc[0] * 100
            - 100
        ),
        "accelerate_profit_per_month_growth_pct": float(
            accelerate["Profit_Per_Month"].iloc[1] / accelerate["Profit_Per_Month"].iloc[0] * 100
            - 100
        ),
        "accelerate_margin_before": float(accelerate["Margin_Pct"].iloc[0]),
        "accelerate_margin_after": float(accelerate["Margin_Pct"].iloc[1]),
        "accelerate_discount_before": float(accelerate["Avg_Discount_Pct"].iloc[0]),
        "accelerate_discount_after": float(accelerate["Avg_Discount_Pct"].iloc[1]),
        "accelerate_new_share_before": float(accelerate["New_Customer_Share_Pct"].iloc[0]),
        "accelerate_new_share_after": float(accelerate["New_Customer_Share_Pct"].iloc[1]),
        "electronics_revenue_share": float(electronics["Revenue_Share_Pct"]),
        "electronics_margin": float(electronics["Margin_Pct"]),
        "electronics_profit": float(electronics["Profit"]),
        "electronics_product_cost_pct": float(
            cost_structure(df).loc["Electronics", "Product_Cost_Pct"]
        ),
        "smartphones_revenue_share": float(smartphones["Revenue_Share_Pct"]),
        "smartphones_margin": float(smartphones["Margin_Pct"]),
        "smartphones_profit": float(smartphones["Profit"]),
        "flash_margin": float(flash["Margin_Pct"]),
        "flash_discount": float(flash["Avg_Discount"]),
        "flash_revenue_share": float(flash["Revenue_Share_Pct"]),
        "no_promo_margin": float(none_promo["Margin_Pct"]),
        "no_promo_revenue_share": float(none_promo["Revenue_Share_Pct"]),
        "premium_margin_pooled": float(segments.loc["Premium", "Margin_Pooled"]),
        "premium_margin_ex_electronics": float(segments.loc["Premium", "Margin_Ex_Electronics"]),
        "premium_electronics_share": float(segments.loc["Premium", "Electronics_Share_Pct"]),
        "top_driver": drivers.iloc[0]["Dimension"],
        "top_driver_sd_pp": float(drivers.iloc[0]["Weighted_SD_pp"]),
        "geography_sd_pp": float(drivers.set_index("Dimension").loc["Region", "Weighted_SD_pp"]),
        "on_time_before_contract": float(logistics["On_Time_Pct"].iloc[0]),
        "on_time_after_contract": float(logistics["On_Time_Pct"].iloc[1]),
        "complaint_before_contract": float(logistics["Complaint_Pct"].iloc[0]),
        "complaint_after_contract": float(logistics["Complaint_Pct"].iloc[1]),
        "delivery_cost_before_contract": float(logistics["Delivery_Cost_Per_Order"].iloc[0]),
        "delivery_cost_after_contract": float(logistics["Delivery_Cost_Per_Order"].iloc[1]),
        "peak_gap_last_year_pp": float(peak.loc[last_year, "Gap_pp"]),
        "peak_on_time_last_year": float(peak.loc[last_year, "Oct–Nov peak"]),
    }
