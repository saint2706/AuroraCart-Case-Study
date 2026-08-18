"""Render the executive-story chart set to PNG.

    python tools/build_figures.py

Writes ``deliverables/figures/*.png`` at 2x scale for projection. Every figure
is built from :mod:`auroracart.analysis`, so a chart on a slide cannot disagree
with the dashboard or the notebook. Chart styling comes from
:mod:`auroracart.viz_theme` — the same palette and mark specs the dashboard
uses, so the deck and the live app read as one system.

Each figure carries its finding in the title rather than a neutral label
("Growth accelerated; profit did not" beats "Revenue and margin by year"), so a
reader who sees only the slide still gets the point.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from auroracart import analysis as A
from auroracart.data_prep import CATEGORY_ORDER, SEGMENT_ORDER, load_data
from auroracart.paths import FIGURES_DIR
from auroracart.viz_theme import (
    CATEGORICAL,
    DIVERGING_BLUE_RED,
    INK,
    SEQUENTIAL_BLUE,
    STATUS,
    SURFACE,
    finalize,
    style_bars,
    style_line,
)

# Slide-shaped: wide enough for a 16:9 content area, tall enough to keep axis
# labels legible when the deck is projected.
WIDTH, HEIGHT, SCALE = 1400, 600, 2

# Semantic roles, held constant across the deck and the dashboard so hue itself
# carries meaning: revenue reads blue, profit green. Both are documented palette
# slots — never eyeballed values.
C_REVENUE = CATEGORICAL[0]
C_PROFIT = CATEGORICAL[5]


def _save(fig: go.Figure, name: str) -> str:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.write_image(path, width=WIDTH, height=HEIGHT, scale=SCALE)
    return str(path.relative_to(FIGURES_DIR.parents[1]))


def _note(fig: go.Figure, text: str) -> None:
    """A one-line source/denominator note under the plot.

    Every chart states what is in its denominator, because the whole case turns
    on aggregation choices and a chart that hides them invites the reader to
    assume the convenient one.
    """
    fig.add_annotation(
        text=text, xref="paper", yref="paper", x=0, y=-0.155, showarrow=False,
        xanchor="left", yanchor="top", font=dict(size=11, color=INK["muted"]),
    )
    fig.update_layout(margin=dict(b=110))


# --------------------------------------------------------------------------- figures


def fig_growth_vs_margin(df) -> go.Figure:
    """Revenue above, margin below, on one shared time axis — the case's central tension.

    Two stacked panels rather than one dual-axis chart: a secondary axis lets the
    reader read a crossing as meaningful when the two scales are arbitrary, and
    this is precisely the chart the audience will stare at longest.
    """
    years = A.annual_summary(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        row_heights=[0.56, 0.44])
    fig.add_bar(
        x=years.index, y=years["Revenue"] / 1e6,
        marker=dict(color=C_REVENUE, cornerradius=4),
        text=[f"₹{v / 1e6:,.1f}M" for v in years["Revenue"]],
        textposition="outside", textfont=dict(color=INK["secondary"]),
        hovertemplate="<b>₹%{y:,.1f}M</b> net revenue<br>%{x}<extra></extra>",
        showlegend=False, row=1, col=1,
    )
    fig.add_scatter(
        x=years.index, y=years["Margin_Pct"],
        mode="lines+markers+text", line=dict(color=STATUS["critical"], width=2),
        marker=dict(size=11, line=dict(width=2, color=SURFACE)),
        text=[f"{v:.1f}%" for v in years["Margin_Pct"]], textposition="top center",
        textfont=dict(color=INK["secondary"], size=13),
        hovertemplate="<b>%{y:.1f}%</b> margin<br>%{x}<extra></extra>",
        showlegend=False, row=2, col=1,
    )
    # Status red is a reserved token, so it never travels alone: the panel says in
    # words what the colour is claiming.
    fig.add_annotation(text="▼ margin, below the 9% watch band", xref="paper", yref="paper",
                       x=1, y=0.30, xanchor="right", showarrow=False,
                       font=dict(color=STATUS["critical"], size=12))
    growth = years["Revenue"].iloc[-1] / years["Revenue"].iloc[0] * 100 - 100
    drop = years["Margin_Pct"].iloc[0] - years["Margin_Pct"].iloc[-1]
    fig.update_layout(
        title=f"Revenue grew {growth:.0f}%. Margin fell {drop:.1f} points.",
        bargap=0.55,
    )
    fig.update_xaxes(tickmode="array", tickvals=list(years.index), showgrid=False, row=2, col=1)
    fig.update_yaxes(title_text="Net revenue (₹M)",
                     range=[0, years["Revenue"].max() / 1e6 * 1.22], row=1, col=1)
    fig.update_yaxes(title_text="Profit margin (%)",
                     range=[0, years["Margin_Pct"].max() * 1.35], row=2, col=1)
    _note(fig, "Net revenue and margin exclude cancelled orders (zero recognised revenue). "
               "Margin = total profit ÷ total net revenue, not the average of order-level margins.")
    return finalize(fig, HEIGHT)


def fig_accelerate_split(df) -> go.Figure:
    """Per-month revenue and profit either side of Accelerate 2.0.

    Per-month rather than totals: the two windows are 18 months each here, but
    stating the normalisation is what stops the comparison being questioned.
    """
    era = A.accelerate_comparison(df)
    labels = list(era.index)
    fig = go.Figure()
    for name, column, color in [("Net revenue per month", "Revenue_Per_Month", C_REVENUE),
                                ("Profit per month", "Profit_Per_Month", C_PROFIT)]:
        values = era[column] / 1e6
        fig.add_bar(x=labels, y=values, name=name, marker=dict(color=color, cornerradius=4),
                    text=[f"₹{v:,.2f}M" for v in values], textposition="outside",
                    textfont=dict(color=INK["secondary"]),
                    hovertemplate="<b>₹%{y:,.2f}M</b> per month<br>%{x}<extra></extra>")
    revenue_growth = era["Revenue_Per_Month"].iloc[1] / era["Revenue_Per_Month"].iloc[0] * 100 - 100
    profit_growth = era["Profit_Per_Month"].iloc[1] / era["Profit_Per_Month"].iloc[0] * 100 - 100
    fig.update_layout(
        title=f"Accelerate 2.0 bought revenue, not profit: +{revenue_growth:.0f}% revenue "
              f"per month, +{profit_growth:.0f}% profit",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="₹ millions per month",
                   range=[0, (era["Revenue_Per_Month"] / 1e6).max() * 1.3]),
        bargap=0.45, bargroupgap=0.12,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=100),
    )
    _note(fig, f"18 months either side of July 2024. Margin {era['Margin_Pct'].iloc[0]:.1f}% → "
               f"{era['Margin_Pct'].iloc[1]:.1f}%; average discount "
               f"{era['Avg_Discount_Pct'].iloc[0]:.1f}% → {era['Avg_Discount_Pct'].iloc[1]:.1f}%.")
    return finalize(fig, HEIGHT)


def fig_margin_decomposition(df) -> go.Figure:
    """Waterfall: did we grow into a worse mix, or did what we already sold get worse?"""
    d = A.decompose_margin_change(df)
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[f"{d.base_year} margin", "Category mix shift", "Margin within categories",
           "Interaction", f"{d.final_year} margin"],
        y=[d.base_margin, d.mix_effect, d.rate_effect, d.interaction, d.final_margin],
        text=[f"{d.base_margin:.1f}%", f"{d.mix_effect:+.1f} pts", f"{d.rate_effect:+.1f} pts",
              f"{d.interaction:+.1f} pts", f"{d.final_margin:.1f}%"],
        textposition="outside", textfont=dict(color=INK["secondary"]),
        connector=dict(line=dict(color=INK["axis"], width=1)),
        # Blue/red diverging poles rather than green/red: green↔red measures ΔE 4.1
        # under deuteranopia, i.e. one colour to ~5% of male readers.
        increasing=dict(marker=dict(color=SEQUENTIAL_BLUE[4])),
        decreasing=dict(marker=dict(color=STATUS["critical"])),
        totals=dict(marker=dict(color=CATEGORICAL[0])),
        hovertemplate="<b>%{y:.2f}</b><br>%{x}<extra></extra>",
    ))
    fig.update_layout(
        title=f"{d.rate_share_pct:.0f}% of the margin decline is erosion inside categories — "
              "not a shift in what we sell",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="Profit margin (%)", range=[0, d.base_margin * 1.35]),
        showlegend=False,
    )
    _note(fig, "Mix effect re-weights base-year category margins with the final-year revenue mix; "
               "the rate effect holds the mix fixed. Residual interaction shown rather than absorbed.")
    return finalize(fig, HEIGHT)


def fig_category_margin(df) -> go.Figure:
    """Margin by category, with each bar carrying its share of revenue."""
    categories = A.group_economics(df, "Category").reindex(CATEGORY_ORDER).dropna(how="all")
    categories = categories.sort_values("Margin_Pct")
    fig = go.Figure(go.Bar(
        x=categories["Margin_Pct"], y=list(categories.index), orientation="h",
        marker=dict(color=categories["Margin_Pct"], colorscale=DIVERGING_BLUE_RED, cmid=0,
                    cornerradius=4),
        text=[f"{m:+.1f}%  ({s:.0f}% of revenue)"
              for m, s in zip(categories["Margin_Pct"], categories["Revenue_Share_Pct"])],
        textposition="outside", textfont=dict(color=INK["secondary"]),
        hovertemplate="<b>%{x:+.1f}%</b> margin<br>%{y}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=INK["axis"], line_width=1)
    span = categories["Margin_Pct"].max() - categories["Margin_Pct"].min()
    fig.update_layout(
        title="Half of revenue sits in the one category that loses money",
        xaxis=dict(title="Profit margin (%)",
                   range=[categories["Margin_Pct"].min() - span * 0.18,
                          categories["Margin_Pct"].max() + span * 0.45]),
        yaxis=dict(title=None, showgrid=False),
        showlegend=False, margin=dict(l=215),
    )
    _note(fig, "Valid-revenue orders only. Average discount is within 0.3 points across all five "
               "categories — the gap is not a discounting gap.")
    return finalize(fig, HEIGHT)


def fig_cost_structure(df) -> go.Figure:
    """Where each rupee of net revenue goes, by category — the *why* behind the margin bar."""
    costs = A.cost_structure(df).reindex(CATEGORY_ORDER).dropna(how="all")
    components = [
        ("Product_Cost_Pct", "Merchandise cost", CATEGORICAL[0]),
        ("Delivery_Cost_Pct", "Delivery", CATEGORICAL[1]),
        ("Marketing_Cost_Pct", "Marketing", CATEGORICAL[2]),
        ("Operating_Cost_Pct", "Operating", CATEGORICAL[3]),
    ]
    fig = go.Figure()
    for column, label, color in components:
        fig.add_bar(y=list(costs.index), x=costs[column], name=label, orientation="h",
                    # A 2px surface-coloured line is the gap between stacked fills —
                    # segments are separated by the surface, never by a drawn border.
                    marker=dict(color=color, line=dict(width=2, color=SURFACE)),
                    # Only label a segment wide enough to hold the text — a clipped
                    # in-segment label is worse than none, and the value stays in the
                    # hover and in the dashboard's table twin either way.
                    text=[f"{v:.0f}%" if v >= 4 else "" for v in costs[column]],
                    textposition="inside", insidetextanchor="middle",
                    textfont=dict(color=SURFACE, size=11), constraintext="inside",
                    hovertemplate="<b>%{x:.1f}%</b> of net revenue<br>%{y} · " + label + "<extra></extra>")
    fig.add_vline(x=100, line_dash="dash", line_width=1, line_color=INK["primary"],
                  annotation_text="break-even", annotation_position="top",
                  annotation_font=dict(color=INK["secondary"], size=12))
    electronics_product = costs.loc["Electronics", "Product_Cost_Pct"]
    fig.update_layout(
        barmode="stack", bargap=0.42,
        title=f"Electronics merchandise alone costs {electronics_product:.0f}% of what the order earns",
        xaxis=dict(title="Share of net revenue (%)", range=[0, 118]),
        yaxis=dict(title=None, showgrid=False),
        # traceorder="normal" keeps the legend in stack order; Plotly reverses it on
        # horizontal stacks by default, which reads as a different chart.
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, traceorder="normal"),
        margin=dict(l=215, t=100),
    )
    _note(fig, "Costs as recorded in the dataset. Anything the stack pushes past 100% is a loss on "
               "that category. Marketing and delivery are near-identical across categories.")
    return finalize(fig, HEIGHT)


def fig_discount_tolerance(df) -> go.Figure:
    """How much discount each half of the business can absorb before it stops earning."""
    banded = A.discount_band_margin(df, split="Category")
    banded["Side"] = banded["Category"].astype(str).where(
        banded["Category"].astype(str) == "Electronics", "Rest of business")
    side = (banded.groupby(["Side", "Discount_Band"], observed=True)[["Revenue", "Profit"]].sum()
            .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100).reset_index())

    fig = go.Figure()
    for name, color in [("Rest of business", CATEGORICAL[0]), ("Electronics", CATEGORICAL[1])]:
        series = side[side["Side"] == name].set_index("Discount_Band").reindex(A.DISCOUNT_BAND_LABELS)
        fig.add_scatter(x=A.DISCOUNT_BAND_LABELS, y=series["Margin_Pct"], name=name,
                        mode="lines+markers", line=dict(color=color, width=2),
                        marker=dict(size=10, line=dict(width=2, color=SURFACE)),
                        hovertemplate="<b>%{y:.1f}%</b> margin at %{x} discount<extra></extra>")
        fig.add_annotation(x=A.DISCOUNT_BAND_LABELS[-1], y=series["Margin_Pct"].iloc[-1],
                           text=f"  {name}: {series['Margin_Pct'].iloc[-1]:.0f}%", showarrow=False,
                           xanchor="left", font=dict(color=INK["secondary"], size=12))
    fig.add_hline(y=0, line_dash="dot", line_width=1, line_color=INK["axis"],
                  annotation_text="break-even", annotation_position="bottom left",
                  annotation_font=dict(color=INK["muted"], size=11))
    style_line(fig)
    fig.update_layout(
        title="One discount policy, two different businesses: Electronics stops earning above 10% off",
        xaxis=dict(title="Discount applied to the order", showgrid=False),
        yaxis=dict(title="Profit margin (%)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(r=190, t=100),
    )
    _note(fig, "Bands are order-level discount percentage. Read as tolerance, not as a causal "
               "response curve — deeper-discounted orders also differ in what they contain.")
    return finalize(fig, HEIGHT)


def fig_driver_ranking(df) -> go.Figure:
    """Which lens on the business actually separates profitable from unprofitable."""
    drivers = A.driver_ranking(df).sort_values("Weighted_SD_pp")
    labels = drivers["Dimension"].str.replace("_", " ")
    fig = go.Figure(go.Bar(
        x=drivers["Weighted_SD_pp"], y=labels, orientation="h",
        marker=dict(color=C_REVENUE, cornerradius=4),
        text=[f"{v:.1f} pts" for v in drivers["Weighted_SD_pp"]],
        textposition="outside", textfont=dict(color=INK["secondary"]),
        customdata=drivers[["Profit_Gap_Mn"]],
        hovertemplate="<b>%{x:.1f} pts</b> spread<br>%{y}<br>₹%{customdata[0]:.1f}M profit gap<extra></extra>",
    ))
    style_bars(fig, horizontal=True)
    fig.update_layout(
        title="Product mix explains profitability. Geography and fulfilment barely move it.",
        xaxis=dict(title="Revenue-weighted spread in category margin (percentage points)",
                   range=[0, drivers["Weighted_SD_pp"].max() * 1.22]),
        yaxis=dict(title=None, showgrid=False),
        showlegend=False, margin=dict(l=215),
    )
    _note(fig, "Spread = sqrt(Σ wᵍ (marginᵍ − company margin)²), weighted by each group's revenue "
               "share, so a small extreme group cannot outrank a dimension that splits the business.")
    return finalize(fig, HEIGHT)


def fig_misleading_pair(df) -> go.Figure:
    """The Question 4 pair, side by side, so the reversal is visible in one glance."""
    confound = A.segment_margin_confound(df).reindex(SEGMENT_ORDER).dropna(how="all")
    segments = list(confound.index)

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.12,
        subplot_titles=("Exhibit A — “Premium is our worst segment”",
                        "Exhibit B — the same orders, split by what was in them"),
    )
    fig.add_bar(x=segments, y=confound["Margin_Pooled"], name="Pooled margin",
                marker=dict(color=INK["muted"], cornerradius=4),
                text=[f"{v:.1f}%" for v in confound["Margin_Pooled"]], textposition="outside",
                textfont=dict(color=INK["secondary"]),
                hovertemplate="<b>%{y:.1f}%</b> pooled margin<br>%{x}<extra></extra>",
                row=1, col=1)
    fig.add_bar(x=segments, y=confound["Margin_Ex_Electronics"], name="Everything except Electronics",
                marker=dict(color=CATEGORICAL[0], cornerradius=4),
                hovertemplate="<b>%{y:.1f}%</b><br>%{x} · non-Electronics orders<extra></extra>",
                row=1, col=2)
    fig.add_bar(x=segments, y=confound["Margin_In_Electronics"], name="Electronics orders",
                marker=dict(color=CATEGORICAL[1], cornerradius=4),
                hovertemplate="<b>%{y:.1f}%</b><br>%{x} · Electronics orders<extra></extra>",
                row=1, col=2)
    fig.add_hline(y=0, line_color=INK["axis"], line_width=1, row=1, col=2)

    premium_share = confound.loc["Premium", "Electronics_Share_Pct"]
    fig.update_layout(
        title="Same data, opposite conclusion — and only one of these is actionable",
        barmode="group", bargap=0.4, bargroupgap=0.1,
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0.52),
        showlegend=True,
    )
    fig.update_yaxes(title_text="Profit margin (%)",
                     range=[0, confound["Margin_Pooled"].max() * 1.35], row=1, col=1)
    fig.update_yaxes(title_text="Profit margin (%)", row=1, col=2)
    fig.update_xaxes(showgrid=False)
    for annotation in fig.layout.annotations[:2]:
        annotation.font = dict(size=13, color=INK["secondary"])
    _note(fig, f"Premium's pooled margin is low because {premium_share:.0f}% of its revenue is "
               "Electronics — the loss-making category — not because Premium customers are unprofitable.")
    finalize(fig, HEIGHT)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.06, x=0.5, xanchor="center"),
                      margin=dict(t=110, b=140))
    return fig


def fig_on_time_monthly(df) -> go.Figure:
    """The pooled on-time average against the monthly series it conceals."""
    monthly = A.monthly_operations(df).reset_index()
    pooled = df["On_Time_Flag"].mean() * 100
    fig = go.Figure()
    fig.add_scatter(x=monthly["Order_YearMonth"], y=monthly["On_Time_Pct"],
                    mode="lines+markers", name="On-time rate by month",
                    line=dict(color=C_REVENUE, width=2),
                    marker=dict(size=8, line=dict(width=2, color=SURFACE)),
                    hovertemplate="<b>%{y:.1f}%</b> on time<br>%{x|%b %Y}<extra></extra>")
    fig.add_hline(y=pooled, line_dash="dot", line_width=1, line_color=INK["axis"],
                  annotation_text=f"the number on the summary table: {pooled:.0f}%",
                  annotation_position="bottom right",
                  annotation_font=dict(color=INK["muted"], size=11))
    # Kaleido serialises the figure spec through orjson, which has no encoder for
    # a pandas Timestamp — date shapes have to go in as ISO strings.
    for _, row in monthly[monthly["Is_Peak"]].iterrows():
        fig.add_vrect(x0=row["Order_YearMonth"].isoformat(),
                      x1=(row["Order_YearMonth"] + pd.offsets.MonthEnd(1)).isoformat(),
                      fillcolor=STATUS["critical"], opacity=0.07, line_width=0, layer="below")
    fig.add_vline(x=A.LOGISTICS_START.isoformat(), line_dash="dash", line_width=1, line_color=INK["muted"],
                  annotation_text="new logistics contract", annotation_position="top left",
                  annotation_font=dict(color=INK["secondary"], size=12))
    style_line(fig)
    fig.update_layout(
        title="The delivery investment worked — and every festive peak still breaks it",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="On-time rate (%)", range=[0, 100]),
        showlegend=False,
    )
    _note(fig, "All orders, including cancellations. Shaded bands are October–November. "
               "The company-wide average pools a step change and a recurring collapse into one number.")
    return finalize(fig, HEIGHT)


def fig_channel_economics(df) -> go.Figure:
    """Channel margin before and after Accelerate 2.0 — a dumbbell, so the move is the mark."""
    channels = A.channel_economics_by_era(df).sort_values("Margin_After")
    fig = go.Figure()
    for name, row in channels.iterrows():
        fig.add_scatter(x=[row["Margin_Before"], row["Margin_After"]], y=[name, name],
                        mode="lines", line=dict(color=INK["axis"], width=2),
                        showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=channels["Margin_Before"], y=list(channels.index), mode="markers",
                    name="Before Accelerate 2.0",
                    marker=dict(size=13, color=CATEGORICAL[0], line=dict(width=2, color=SURFACE)),
                    hovertemplate="<b>%{x:.1f}%</b> margin before<br>%{y}<extra></extra>")
    fig.add_scatter(x=channels["Margin_After"], y=list(channels.index), mode="markers",
                    name="After Accelerate 2.0",
                    marker=dict(size=13, color=CATEGORICAL[1], line=dict(width=2, color=SURFACE)),
                    hovertemplate="<b>%{x:.1f}%</b> margin after<br>%{y}<extra></extra>")
    fig.update_layout(
        title="Every channel lost margin — the paid ones lost the most and cost the most to run",
        xaxis=dict(title="Profit margin (%)", range=[0, channels["Margin_Before"].max() * 1.15]),
        yaxis=dict(title=None, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=215, t=100),
    )
    _note(fig, "Marketing cost as a share of the revenue it earned: "
               + ", ".join(f"{name} {row['Marketing_Pct_After']:.1f}%"
                           for name, row in channels.iterrows()) + ".")
    return finalize(fig, HEIGHT)


# --------------------------------------------------------------------------- driver

FIGURES = {
    "01_growth_vs_margin": fig_growth_vs_margin,
    "02_accelerate_split": fig_accelerate_split,
    "03_margin_decomposition": fig_margin_decomposition,
    "04_category_margin": fig_category_margin,
    "05_cost_structure": fig_cost_structure,
    "06_discount_tolerance": fig_discount_tolerance,
    "07_driver_ranking": fig_driver_ranking,
    "08_misleading_pair": fig_misleading_pair,
    "09_on_time_monthly": fig_on_time_monthly,
    "10_channel_economics": fig_channel_economics,
}


def build_all() -> list[str]:
    df = load_data()
    written = []
    for name, builder in FIGURES.items():
        written.append(_save(builder(df), name))
        print(f"  wrote {written[-1]}")
    return written


if __name__ == "__main__":
    print(f"Rendering {len(FIGURES)} figures to {FIGURES_DIR} …")
    build_all()
    print("done.")
