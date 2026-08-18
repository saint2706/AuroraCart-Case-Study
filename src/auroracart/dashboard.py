"""AuroraCart at a Crossroads — interactive profitability & operations dashboard.

Run locally:      python app.py                  (http://127.0.0.1:8050)
Run for prod:     gunicorn app:server

Layout: a global filter bar (date range, region, category, segment, fulfillment
mode) drives four tabs — Executive Overview, Profitability Deep-Dive, Customers,
and Operations & Delivery — each answering a different slice of "what should
AuroraCart do next, and what evidence supports it."

Every chart below is built against the dataviz skill's checklist: the color job
(categorical/sequential/ordinal/diverging/status) matches what the data actually
is, marks are thin with rounded bar ends and >=8px ringed line markers, bars carry
direct value-at-tip labels, hover tooltips lead with the value, and each tab keeps
a plain-table twin so nothing is gated behind a hover.

Responsive behaviour is split across three layers, deliberately:

* ``assets/style.css`` — CSS media queries own the page layout, type scale and
  tap targets. This layer works with JavaScript disabled.
* ``assets/environment.js`` — measures the live browser (viewport tier, pointer
  type, engine, feature support) and reports it into ``env-store``.
* ``responsive.py`` — turns that report into a :class:`ViewProfile` that the tab
  renderers below consult for the things CSS cannot reach: Plotly axis margins,
  tick-label truncation, drag behaviour on touch, table page size.
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

from auroracart import analysis as A
from auroracart.data_prep import (
    CATEGORY_ORDER,
    FULFILLMENT_ORDER,
    LOYALTY_ORDER,
    PROMOTION_ORDER,
    REGION_ORDER,
    SEGMENT_ORDER,
    load_data,
)
from auroracart.responsive import (
    CHART_COL,
    ViewProfile,
    graph_config,
    profile_from_store,
    responsive_figure,
)
from auroracart.viz_theme import (
    CATEGORICAL,
    DIVERGING_BLUE_RED,
    INK,
    ORDINAL_BLUE_4,
    STATUS,
    SURFACE,
    finalize,
    money_hover,
    money_hover_h,
    pct_hover,
    pct_hover_h,
    style_bars,
    style_line,
    wash_area,
)

# Semantic color roles, held constant across every chart so hue itself carries
# meaning dashboard-wide: revenue/volume always reads blue, cost/spend always
# orange, a genuinely profitable metric green — never assigned per-chart on looks.
C_REVENUE = CATEGORICAL[0]  # blue
C_COST = CATEGORICAL[1]  # orange
C_PROFIT = CATEGORICAL[5]  # green
C_FRICTION = CATEGORICAL[6]  # violet — returns/friction, deliberately not status-red

# Short codes for the promotion scatter's point labels at phone width, where the
# full names collide. The full names stay in the hover and in the table below.
PROMO_SHORT_LABEL = {
    "No Promotion": "None",
    "Category Offer": "Category",
    "Member Offer": "Member",
    "Festival Sale": "Festival",
    "Flash Deal": "Flash",
}

# --------------------------------------------------------------------------- data
DF = load_data()
MIN_DATE = DF["Order_Date"].min()
MAX_DATE = DF["Order_Date"].max()

_BASELINE_VALID = DF[DF["Is_Valid_Revenue"]]
BASELINE_MARGIN = _BASELINE_VALID["Profit"].sum() / _BASELINE_VALID["Net_Revenue"].sum() * 100
BASELINE_ON_TIME = DF["On_Time_Flag"].mean() * 100

# --------------------------------------------------------------------------- helpers


def format_inr(value: float) -> str:
    if pd.isna(value):
        return "—"
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:,.2f} L"
    return f"₹{value:,.0f}"


def rate_status(
    value: float, good_max: float, warn_max: float, lower_is_better: bool = True
) -> str:
    """Map a rate to a fixed status band.

    ``lower_is_better=False`` flips the direction (e.g. on-time %).
    """
    if not lower_is_better:
        return (
            STATUS["good"]
            if value >= good_max
            else STATUS["warning"]
            if value >= warn_max
            else STATUS["critical"]
        )
    return (
        STATUS["good"]
        if value <= good_max
        else STATUS["warning"]
        if value <= warn_max
        else STATUS["critical"]
    )


def stat_card(
    label: str,
    value: str,
    accent: str = CATEGORICAL[0],
    sub: str | None = None,
    delta: float | None = None,
    delta_good_if_up: bool = True,
    delta_suffix: str = " pts",
) -> dbc.Card:
    delta_el = html.Div(sub or " ", className="stat-sub")
    if delta is not None:
        up = delta > 0
        good = (up == delta_good_if_up) if delta != 0 else True
        arrow = "▲" if up else ("▼" if delta < 0 else "●")
        color = STATUS["good"] if good else STATUS["critical"]
        delta_el = html.Div(
            f"{arrow} {abs(delta):.1f}{delta_suffix} vs full period",
            className="stat-delta",
            style={"color": color},
        )
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="stat-label"),
                html.Div(value, className="stat-value"),
                delta_el,
            ]
        ),
        className="stat-card",
        style={"borderTop": f"3px solid {accent}"},
    )


def empty_state() -> dbc.Alert:
    return dbc.Alert(
        "No orders match the current filters. Try widening the date range or clearing a filter.",
        color="warning",
        className="mt-3",
    )


def apply_filters(
    df: pd.DataFrame, start_date, end_date, regions, categories, segments, fulfillment
) -> pd.DataFrame:
    mask = (df["Order_Date"] >= pd.to_datetime(start_date)) & (
        df["Order_Date"] <= pd.to_datetime(end_date)
    )
    if regions:
        mask &= df["Region"].isin(regions)
    if categories:
        mask &= df["Category"].isin(categories)
    if segments:
        mask &= df["Customer_Segment"].isin(segments)
    if fulfillment:
        mask &= df["Fulfillment_Mode"].isin(fulfillment)
    return df.loc[mask]


def graph(fig, view: ViewProfile) -> dcc.Graph:
    """Wrap a finished figure for the current viewport.

    ``responsive=True`` lets Plotly re-fit the chart in the browser on rotation
    or a window drag without a server round-trip; :func:`responsive_figure`
    handles the parts that must be decided server-side (margins, tick labels,
    drag behaviour on touch).

    Sizing is handed entirely to the container: the computed height goes on the
    wrapper (which style.css frames with `content-box`, so the border and padding
    add *around* it) and ``layout.height`` is cleared. Leaving both set makes
    Plotly draw an SVG at the full height inside a shorter padded content box,
    which clips the x-axis title off the bottom of every chart; clearing both
    makes it fall back to its own 450px default.
    """
    fig = responsive_figure(fig, view)
    height = int(fig.layout.height or 340)
    fig.update_layout(height=None, width=None, autosize=True)
    # Height only — style.css owns the width, because it has to subtract the
    # frame that its `content-box` sizing adds around the plot.
    return dcc.Graph(
        figure=fig,
        config=graph_config(view),
        responsive=True,
        style={"height": f"{height}px"},
    )


def table_view(df: pd.DataFrame, columns: list[str], title: str, view: ViewProfile) -> html.Div:
    """A plain data table beneath the charts — the WCAG-clean twin of every chart above it.

    On a phone this is also where the full text lives for anything the chart had
    to shorten (truncated category ticks), so nothing is lost to small screens.
    """
    return html.Div(
        [
            html.Div(title, className="table-title"),
            dash_table.DataTable(
                data=df[columns].round(2).to_dict("records"),
                columns=[{"name": c.replace("_", " "), "id": c} for c in columns],
                # Wide tables scroll inside their own box; the page itself never
                # scrolls sideways (see body overflow-x in style.css).
                style_table={"overflowX": "auto", "WebkitOverflowScrolling": "touch"},
                style_cell={
                    "fontFamily": "system-ui, sans-serif",
                    "fontSize": 12 if view.is_narrow else 13,
                    "padding": "8px 10px" if view.is_touch_primary else "6px 10px",
                    "backgroundColor": SURFACE,
                    "color": INK["primary"],
                    "border": "none",
                    "borderBottom": f"1px solid {INK['grid']}",
                    "fontVariantNumeric": "tabular-nums",
                    "minWidth": "72px",
                    "maxWidth": "200px",
                    "whiteSpace": "normal",
                },
                style_header={
                    "fontWeight": 600,
                    "backgroundColor": SURFACE,
                    "color": INK["secondary"],
                    "borderBottom": f"2px solid {INK['axis']}",
                },
                page_size=view.table_page_size,
            ),
        ],
        className="table-wrap",
    )


def status_legend(*items: tuple[str, str]) -> html.Div:
    """Icon+label caption for a status-colored chart — status color is never hue-alone."""
    chips = []
    for color, label in items:
        chips.append(
            html.Span(
                [html.Span(className="legend-dot", style={"background": color}), label],
                className="legend-chip",
            )
        )
    return html.Div(chips, className="status-legend")


def _outside_label_range(series: pd.Series, pad: float = 0.22) -> list[float]:
    lo, hi = min(0, series.min()), series.max()
    span = hi - lo
    return [lo - span * pad if lo < 0 else 0, hi + span * pad]


def _mark_event(fig, months: pd.Series, when: pd.Timestamp, label: str) -> None:
    """Annotate a dated intervention on a time series, if it falls inside the view.

    Silently does nothing when the filtered date range excludes the event, so a
    filtered chart never carries a marker pointing off its own axis.
    """
    if months.empty or not (months.min() <= when <= months.max()):
        return
    fig.add_vline(
        x=when.isoformat(),
        line_dash="dash",
        line_width=1,
        line_color=INK["muted"],
        annotation_text=label,
        annotation_position="top left",
        annotation_font=dict(color=INK["muted"], size=11),
    )


def _legend_placement(view: ViewProfile) -> dict:
    """Where a legend can sit without colliding with a wrapped title.

    Above the plot on wide screens (closest to the series it names); below it on
    narrow ones, where ``responsive_figure`` wraps the title onto a second line
    and reclaims the space the legend was using.
    """
    if view.is_narrow:
        return dict(
            legend=dict(orientation="h", yanchor="top", y=-0.28, x=0, title=None), margin=dict(b=90)
        )
    return dict(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None))


def recommendation_card(
    rank: int, title: str, evidence: str, benefit: str, risk: str, ask: str, accent: str
) -> dbc.Card:
    """One prioritised recommendation, in the four parts Question 5 asks for.

    Rank is shown as a numeral rather than implied by position, because the cards
    reflow into a single column on a phone and reading order is the only cue left.
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(f"Priority {rank}", className="stat-label"),
                html.H3(title, className="rec-title"),
                html.Dl(
                    [
                        html.Dt("Evidence"),
                        html.Dd(evidence),
                        html.Dt("Expected benefit"),
                        html.Dd(benefit),
                        html.Dt("Principal risk"),
                        html.Dd(risk),
                        html.Dt("Before we act, we need"),
                        html.Dd(ask),
                    ],
                    className="rec-list",
                ),
            ]
        ),
        className="stat-card rec-card",
        style={"borderTop": f"3px solid {accent}"},
    )


# --------------------------------------------------------------------------- tab renderers


def render_overview(dff: pd.DataFrame, view: ViewProfile) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]
    revenue = valid["Net_Revenue"].sum()
    profit = valid["Profit"].sum()
    margin = (profit / revenue * 100) if revenue else float("nan")
    aov = (revenue / len(valid)) if len(valid) else float("nan")
    on_time = dff["On_Time_Flag"].mean() * 100
    is_filtered = len(dff) < len(DF)

    # 2-up on phones, 3-up on tablets, 6-up on desktop — the KPI strip stays one
    # readable block instead of six full-width cards the user has to scroll past.
    kpi_col = {"xs": 6, "sm": 4, "lg": 2}
    cards = dbc.Row(
        [
            dbc.Col(stat_card("Net Revenue", format_inr(revenue), C_REVENUE), **kpi_col),
            dbc.Col(stat_card("Profit", format_inr(profit), C_PROFIT), **kpi_col),
            dbc.Col(
                stat_card(
                    "Profit Margin",
                    f"{margin:.1f}%",
                    rate_status(margin, 12, 9, lower_is_better=False),
                    delta=(margin - BASELINE_MARGIN) if is_filtered else None,
                ),
                **kpi_col,
            ),
            dbc.Col(stat_card("Orders", f"{len(dff):,}", CATEGORICAL[3]), **kpi_col),
            dbc.Col(stat_card("Avg Order Value", format_inr(aov), CATEGORICAL[4]), **kpi_col),
            dbc.Col(
                stat_card(
                    "On-Time Delivery",
                    f"{on_time:.1f}%",
                    rate_status(on_time, 75, 50, lower_is_better=False),
                    delta=(on_time - BASELINE_ON_TIME) if is_filtered else None,
                    delta_good_if_up=True,
                    delta_suffix=" pts",
                ),
                **kpi_col,
            ),
        ],
        className="g-3 mb-3",
    )

    monthly = (
        valid.groupby("Order_YearMonth")
        .agg(Net_Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Net_Revenue"] * 100)
        .reset_index()
    )

    # --- Monthly Net Revenue: single-series trend -> sequential blue, ~18% wash + 2px line.
    fig_rev = px.area(
        monthly,
        x="Order_YearMonth",
        y="Net_Revenue",
        title="Monthly Net Revenue",
        color_discrete_sequence=[C_REVENUE],
    )
    wash_area(fig_rev, C_REVENUE)
    fig_rev.update_traces(hovertemplate="<b>₹%{y:,.0f}</b><br>%{x|%b %Y}<extra></extra>")
    last = monthly.iloc[-1]
    fig_rev.add_annotation(
        x=last["Order_YearMonth"],
        y=last["Net_Revenue"],
        text=f"₹{last['Net_Revenue'] / 1e6:.1f}M",
        showarrow=False,
        yshift=16,
        xanchor="right",
        font=dict(color=INK["secondary"], size=12),
    )
    fig_rev.update_layout(xaxis_title=None, yaxis_title="Net Revenue (₹)", margin=dict(r=45))
    finalize(fig_rev, height=320)

    # --- Monthly Margin: the headline concern -> emphasis (status critical), end-labeled.
    fig_margin = px.line(
        monthly,
        x="Order_YearMonth",
        y="Margin_Pct",
        title="Monthly Profit Margin (%)",
        markers=True,
        color_discrete_sequence=[STATUS["critical"]],
    )
    style_line(fig_margin)
    fig_margin.update_traces(hovertemplate="<b>%{y:.1f}%</b><br>%{x|%b %Y}<extra></extra>")
    fig_margin.add_hline(
        y=margin,
        line_dash="dot",
        line_width=1,
        line_color=INK["axis"],
        annotation_text="period average",
        annotation_font_color=INK["muted"],
        annotation_position="top left",
    )
    # The case names two dated interventions; a margin trend without them invites
    # the audience to invent their own explanation for the break.
    _mark_event(fig_margin, monthly["Order_YearMonth"], A.ACCELERATE_START, "Accelerate 2.0")
    trend = "▼" if monthly["Margin_Pct"].iloc[-1] < monthly["Margin_Pct"].iloc[0] else "▲"
    fig_margin.add_annotation(
        x=last["Order_YearMonth"],
        y=monthly["Margin_Pct"].iloc[-1],
        text=f"{trend} {monthly['Margin_Pct'].iloc[-1]:.1f}%",
        showarrow=False,
        yshift=16,
        xanchor="right",
        font=dict(color=STATUS["critical"], size=12),
    )
    fig_margin.update_layout(xaxis_title=None, yaxis_title="Margin (%)", margin=dict(r=45))
    finalize(fig_margin, height=320)

    # --- Revenue by Category: magnitude on a nominal axis -> one flat hue, value at tip.
    cat_rev = (
        valid.groupby("Category", observed=True)["Net_Revenue"]
        .sum()
        .reindex(CATEGORY_ORDER)
        .dropna()
        .sort_values()
        .reset_index()
    )
    cat_rev["Label"] = cat_rev["Net_Revenue"].apply(lambda v: f"₹{v / 1e6:,.1f}M")
    fig_cat = px.bar(
        cat_rev,
        x="Net_Revenue",
        y="Category",
        orientation="h",
        title="Revenue by Category",
        color_discrete_sequence=[C_REVENUE],
        text="Label",
    )
    fig_cat.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=money_hover_h("Category"),
    )
    style_bars(fig_cat, horizontal=True)
    fig_cat.update_layout(
        xaxis_title="Net Revenue (₹)",
        yaxis_title=None,
        margin=dict(l=170, r=60),
        xaxis=dict(range=[0, cat_rev["Net_Revenue"].max() * 1.22]),
    )
    finalize(fig_cat, height=320)

    # --- Revenue by Region: same job, same hue (consistency = the point).
    reg_rev = (
        valid.groupby("Region", observed=True)["Net_Revenue"]
        .sum()
        .reindex(REGION_ORDER)
        .dropna()
        .reset_index()
    )
    reg_rev["Label"] = reg_rev["Net_Revenue"].apply(lambda v: f"₹{v / 1e6:,.1f}M")
    fig_reg = px.bar(
        reg_rev,
        x="Region",
        y="Net_Revenue",
        title="Revenue by Region",
        color_discrete_sequence=[C_REVENUE],
        text="Label",
    )
    fig_reg.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=money_hover_h("Region"),
    )
    style_bars(fig_reg)
    fig_reg.update_layout(
        xaxis_title=None,
        yaxis_title="Net Revenue (₹)",
        yaxis=dict(range=[0, reg_rev["Net_Revenue"].max() * 1.2]),
    )
    finalize(fig_reg, height=320)

    story = dbc.Alert(
        [
            html.B("The story: "),
            "Revenue is growing, but margin is not keeping pace. In this filtered view it "
            "stands at ",
            html.B(f"{margin:.1f}%"),
            ". Use the Profitability tab to see which categories and promotions are driving "
            "that down.",
        ],
        color="light",
        className="story-callout",
    )

    yearly_tbl = (
        valid.assign(Year=valid["Order_Date"].dt.year)
        .groupby("Year")
        .agg(
            Net_Revenue=("Net_Revenue", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order_ID", "count"),
        )
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Net_Revenue"] * 100)
        .reset_index()
    )

    return html.Div(
        [
            cards,
            story,
            dbc.Row(
                [
                    dbc.Col(graph(fig_rev, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_margin, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(graph(fig_cat, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_reg, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3 mt-1",
            ),
            table_view(
                yearly_tbl,
                ["Year", "Net_Revenue", "Profit", "Margin_Pct", "Orders"],
                "Year-over-year revenue & margin (filtered selection)",
                view,
            ),
        ]
    )


def render_profitability(dff: pd.DataFrame, view: ViewProfile) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]

    # --- Margin by Category: crosses zero -> diverging (blue = profitable, red = loss-making).
    cat = (
        valid.groupby("Category", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(CATEGORY_ORDER)
        .dropna()
        .sort_values("Margin_Pct")
        .reset_index()
    )
    cat["Label"] = cat["Margin_Pct"].apply(lambda v: f"{v:+.1f}%")
    fig_cat = px.bar(
        cat,
        x="Margin_Pct",
        y="Category",
        orientation="h",
        title="Profit Margin by Category",
        color="Margin_Pct",
        color_continuous_scale=DIVERGING_BLUE_RED,
        color_continuous_midpoint=0,
        text="Label",
    )
    fig_cat.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=pct_hover_h("Category"),
    )
    fig_cat.add_vline(x=0, line_color=INK["axis"], line_width=1)
    style_bars(fig_cat, horizontal=True)
    fig_cat.update_layout(
        xaxis_title="Profit Margin (%)",
        yaxis_title=None,
        coloraxis_showscale=False,
        margin=dict(l=170, r=60),
        xaxis=dict(range=_outside_label_range(cat["Margin_Pct"])),
    )
    finalize(fig_cat, height=340)

    # --- Discount vs Margin by Promotion: 5 named points -> diverging-by-margin (not 5 categorical
    # hues, which fails the all-pairs CVD gate for scatter forms); identity carried by direct
    # labels.
    promo = (
        valid.groupby("Promotion_Type", observed=True)
        .agg(
            Revenue=("Net_Revenue", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order_ID", "count"),
            Avg_Discount=("Discount_Percentage", "mean"),
        )
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(PROMOTION_ORDER)
        .dropna()
        .reset_index()
    )
    # At phone width the full promotion names collide into illegibility, so the
    # points carry short codes and the table below the chart carries the full
    # names alongside every number the scatter encodes.
    promo["Point_Label"] = (
        promo["Promotion_Type"].map(PROMO_SHORT_LABEL)
        if view.is_narrow
        else promo["Promotion_Type"]
    )
    fig_promo = px.scatter(
        promo,
        x="Avg_Discount",
        y="Margin_Pct",
        size="Revenue",
        text="Point_Label",
        color="Margin_Pct",
        color_continuous_scale=DIVERGING_BLUE_RED,
        color_continuous_midpoint=0,
        title="Discount Depth vs Margin by Promotion",
        size_max=32 if view.is_narrow else 46,
        custom_data=["Promotion_Type"],
    )
    fig_promo.update_traces(
        marker=dict(sizemin=12 if view.is_narrow else 16, line=dict(width=2, color=SURFACE)),
        # Hover reads the full promotion name even when the point label is short.
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Margin: %{y:.1f}%<br>"
            "Avg discount: %{x:.1f}%<br>Revenue: ₹%{marker.size:,.0f}<extra></extra>"
        ),
    )
    fig_promo.add_hline(
        y=0,
        line_dash="dot",
        line_color=INK["axis"],
        line_width=1,
        annotation_text="break-even",
        annotation_font_color=INK["muted"],
        annotation_position="top left",
    )
    # A single trace now (color is the continuous margin value, not a per-category split), so
    # per-point label placement is a LIST aligned to row order — not a per-trace assignment.
    label_pos = {
        "No Promotion": "top center",
        "Category Offer": "top center",
        "Member Offer": "bottom center",
        "Festival Sale": "top center",
        "Flash Deal": "bottom center",
    }
    fig_promo.data[0].textposition = [label_pos[p] for p in promo["Promotion_Type"]]
    fig_promo.data[0].textfont = dict(color=INK["primary"], size=10 if view.is_narrow else 12)
    # More vertical breathing room on a phone so the short codes clear their points.
    y_pad = max(
        (promo["Margin_Pct"].max() - promo["Margin_Pct"].min())
        * (0.38 if view.is_narrow else 0.25),
        2,
    )
    fig_promo.update_layout(
        xaxis_title="Average Discount (%)",
        yaxis_title="Profit Margin (%)",
        showlegend=False,
        coloraxis_showscale=False,
        yaxis=dict(range=[promo["Margin_Pct"].min() - y_pad, promo["Margin_Pct"].max() + y_pad]),
    )
    finalize(fig_promo, height=340)

    seg = (
        valid.groupby("Customer_Segment", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(
            Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100,
            AOV=lambda d: d["Revenue"] / d["Orders"],
        )
        .reindex(SEGMENT_ORDER)
        .dropna()
        .reset_index()
    )
    seg["AOV_Label"] = seg["AOV"].apply(lambda v: f"₹{v:,.0f}")
    seg["Margin_Label"] = seg["Margin_Pct"].apply(lambda v: f"{v:.1f}%")

    # --- Segment AOV: nominal category, magnitude -> flat blue (revenue-family), value at tip.
    fig_seg = px.bar(
        seg,
        x="Customer_Segment",
        y="AOV",
        title="Customer Segment: Average Order Value",
        color_discrete_sequence=[C_REVENUE],
        text="AOV_Label",
    )
    fig_seg.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=money_hover("Segment"),
    )
    style_bars(fig_seg)
    fig_seg.update_layout(
        xaxis_title=None,
        yaxis_title="AOV (₹)",
        showlegend=False,
        yaxis=dict(range=[0, seg["AOV"].max() * 1.2]),
    )
    finalize(fig_seg, height=320)

    # --- Segment Margin: same nominal axis -> flat green (profit-family), NOT a value ramp
    # (ramping color by the same value the bar height already shows double-encodes on a
    # category with no natural order — the anti-pattern this palette explicitly forbids).
    fig_seg_margin = px.bar(
        seg,
        x="Customer_Segment",
        y="Margin_Pct",
        title="Customer Segment: Profit Margin",
        color_discrete_sequence=[C_PROFIT],
        text="Margin_Label",
    )
    fig_seg_margin.update_traces(
        textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Segment")
    )
    style_bars(fig_seg_margin)
    fig_seg_margin.update_layout(
        xaxis_title=None,
        yaxis_title="Margin (%)",
        showlegend=False,
        yaxis=dict(range=[0, seg["Margin_Pct"].max() * 1.25]),
    )
    finalize(fig_seg_margin, height=320)

    tables = [
        table_view(
            cat.assign(
                Revenue=lambda d: d["Revenue"].round(0), Profit=lambda d: d["Profit"].round(0)
            ),
            ["Category", "Revenue", "Profit", "Orders", "Margin_Pct"],
            "Category profitability (filtered selection, worst margin first)",
            view,
        )
    ]
    if view.is_narrow:
        # The promotion scatter's point labels are abbreviated at this width, so
        # ship the full names and figures as a table rather than lose them.
        tables.append(
            table_view(
                promo.assign(Revenue=lambda d: d["Revenue"].round(0)),
                ["Promotion_Type", "Avg_Discount", "Margin_Pct", "Revenue", "Orders"],
                "Promotion economics (full names for the chart above)",
                view,
            )
        )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(graph(fig_cat, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_promo, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(graph(fig_seg, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_seg_margin, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3 mt-1",
            ),
            *tables,
        ]
    )


def render_customers(dff: pd.DataFrame, view: ViewProfile) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]

    # --- New vs Returning: 2-series identity -> first two fixed slots in order (validated
    # adjacent pair, both clear the light-surface contrast floor without needing relief).
    nvr = (
        valid.groupby("New_vs_Returning")
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(["New", "Returning"])
        .reset_index()
    )
    nvr["Label"] = nvr["Margin_Pct"].apply(lambda v: f"{v:.1f}%")
    fig_nvr = px.bar(
        nvr,
        x="New_vs_Returning",
        y="Margin_Pct",
        title="Profit Margin: New vs Returning",
        color="New_vs_Returning",
        color_discrete_sequence=[CATEGORICAL[0], CATEGORICAL[1]],
        text="Label",
        category_orders={"New_vs_Returning": ["New", "Returning"]},
    )
    fig_nvr.update_traces(
        textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Customer")
    )
    style_bars(fig_nvr)
    fig_nvr.update_layout(
        xaxis_title=None,
        yaxis_title="Margin (%)",
        showlegend=False,
        yaxis=dict(range=[0, nvr["Margin_Pct"].max() * 1.25]),
    )
    finalize(fig_nvr, height=320)

    # --- Loyalty Status: New -> Champion is a genuine progression -> ordinal ramp, not a flat
    # color (this is the one axis in the dashboard where a lightness ramp is the correct job).
    loyalty = (
        valid.groupby("Loyalty_Status", observed=True)["Order_ID"]
        .count()
        .reindex(LOYALTY_ORDER)
        .dropna()
        .reset_index(name="Orders")
    )
    loyalty["Label"] = loyalty["Orders"].apply(lambda v: f"{v:,}")
    fig_loy = px.bar(
        loyalty,
        x="Loyalty_Status",
        y="Orders",
        title="Orders by Loyalty Status (New → Champion)",
        color="Loyalty_Status",
        color_discrete_sequence=ORDINAL_BLUE_4,
        category_orders={"Loyalty_Status": LOYALTY_ORDER},
        text="Label",
    )
    fig_loy.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate="<b>%{y:,}</b> orders<br>%{x}<extra></extra>",
    )
    style_bars(fig_loy)
    fig_loy.update_layout(
        xaxis_title=None,
        yaxis_title="Orders",
        showlegend=False,
        yaxis=dict(range=[0, loyalty["Orders"].max() * 1.2]),
    )
    finalize(fig_loy, height=320)

    # --- Marketing cost as % of revenue: nominal category -> flat orange (cost-family hue).
    chan = (
        valid.groupby("Acquisition_Channel")
        .agg(
            Revenue=("Net_Revenue", "sum"),
            Orders=("Order_ID", "count"),
            Marketing_Cost=("Marketing_Cost", "sum"),
        )
        .assign(Marketing_Pct=lambda d: d["Marketing_Cost"] / d["Revenue"] * 100)
        .sort_values("Marketing_Pct")
        .reset_index()
    )
    chan["Label"] = chan["Marketing_Pct"].apply(lambda v: f"{v:.1f}%")
    fig_chan = px.bar(
        chan,
        x="Marketing_Pct",
        y="Acquisition_Channel",
        orientation="h",
        title="Marketing Cost as % of Revenue, by Channel",
        color_discrete_sequence=[C_COST],
        text="Label",
    )
    fig_chan.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=pct_hover_h("Channel"),
    )
    style_bars(fig_chan, horizontal=True)
    fig_chan.update_layout(
        xaxis_title="Marketing Cost / Revenue (%)",
        yaxis_title=None,
        margin=dict(l=150, r=50),
        xaxis=dict(range=[0, chan["Marketing_Pct"].max() * 1.25]),
    )
    finalize(fig_chan, height=340)

    # --- Rating distribution: single continuous series -> sequential blue, thin bins.
    fig_rating = px.histogram(
        valid.dropna(subset=["Customer_Rating"]),
        x="Customer_Rating",
        nbins=10,
        title="Customer Rating Distribution",
        color_discrete_sequence=[C_REVENUE],
    )
    fig_rating.update_traces(
        marker=dict(cornerradius=2),
        hovertemplate="<b>%{y:,}</b> orders<br>rating %{x}<extra></extra>",
    )
    fig_rating.update_layout(
        xaxis_title="Rating", yaxis_title="Orders", bargap=0.12, showlegend=False
    )
    finalize(fig_rating, height=340)

    chan_tbl = table_view(
        chan.assign(
            Revenue=lambda d: d["Revenue"].round(0),
            Marketing_Cost=lambda d: d["Marketing_Cost"].round(0),
        ),
        ["Acquisition_Channel", "Revenue", "Orders", "Marketing_Cost", "Marketing_Pct"],
        "Acquisition channel economics (filtered selection)",
        view,
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(graph(fig_nvr, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_loy, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(graph(fig_chan, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_rating, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3 mt-1",
            ),
            chan_tbl,
        ]
    )


def render_operations(dff: pd.DataFrame, view: ViewProfile) -> html.Div:
    if dff.empty:
        return empty_state()

    # --- On-Time Rate: nominal fulfillment modes, but color carries a genuine fixed-threshold
    # STATE (critical/warning/good), not rank -> status tokens, paired with a caption (never
    # hue-alone) since status color always ships with an icon + label.
    ops = (
        dff.groupby("Fulfillment_Mode", observed=True)
        .agg(
            On_Time_Rate=("On_Time_Flag", "mean"),
            Orders=("Order_ID", "count"),
            Avg_Rating=("Customer_Rating", "mean"),
        )
        .assign(On_Time_Rate=lambda d: d["On_Time_Rate"] * 100)
        .reindex(FULFILLMENT_ORDER)
        .dropna()
        .reset_index()
    )
    ops["Status_Color"] = ops["On_Time_Rate"].apply(
        lambda v: rate_status(v, 75, 50, lower_is_better=False)
    )
    ops["Label"] = ops["On_Time_Rate"].apply(lambda v: f"{v:.0f}%")
    fig_ops = go.Figure(
        go.Bar(
            x=ops["Fulfillment_Mode"],
            y=ops["On_Time_Rate"],
            marker=dict(color=ops["Status_Color"], cornerradius=4),
            text=ops["Label"],
            textposition="outside",
            textfont=dict(color=INK["secondary"]),
            hovertemplate="<b>%{y:.1f}%</b> on time<br>%{x}<extra></extra>",
        )
    )
    fig_ops.add_hline(y=100, line_dash="dot", line_width=1, line_color=INK["grid"])
    fig_ops.add_hline(
        y=75,
        line_dash="dot",
        line_width=1,
        line_color=STATUS["good"],
        annotation_text="target 75%",
        annotation_font_color=STATUS["good"],
        annotation_position="top right",
    )
    fig_ops.update_layout(
        title="On-Time Delivery Rate by Fulfillment Mode",
        xaxis_title=None,
        yaxis_title="On-Time Rate (%)",
        yaxis=dict(range=[0, 118]),
        bargap=0.38,
        showlegend=False,
    )
    finalize(fig_ops, height=340)
    ops_legend = status_legend(
        (STATUS["critical"], "Below 50%"), (STATUS["warning"], "50-75%"), (STATUS["good"], "75%+")
    )

    # --- Complaint rate: exactly 2 states, both genuinely good/bad -> canonical status use.
    complaint = dff.groupby("On_Time_Flag")["Complaint_Flag"].mean() * 100
    complaint_df = pd.DataFrame(
        {
            "Delivery": ["✓ On Time", "✕ Late"],
            "Complaint_Rate": [complaint.get(True, 0), complaint.get(False, 0)],
        }
    )
    complaint_df["Label"] = complaint_df["Complaint_Rate"].apply(lambda v: f"{v:.1f}%")
    fig_complaint = px.bar(
        complaint_df,
        x="Delivery",
        y="Complaint_Rate",
        title="Complaint Rate: On-Time vs Late",
        color="Delivery",
        color_discrete_map={"✓ On Time": STATUS["good"], "✕ Late": STATUS["critical"]},
        text="Label",
    )
    fig_complaint.update_traces(
        textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Delivery")
    )
    style_bars(fig_complaint)
    fig_complaint.update_layout(
        xaxis_title=None,
        yaxis_title="Complaint Rate (%)",
        showlegend=False,
        yaxis=dict(range=[0, complaint_df["Complaint_Rate"].max() * 1.3]),
    )
    finalize(fig_complaint, height=340)

    # --- Return rate by category: nominal magnitude -> flat violet (friction-family, distinct
    # from the reserved status-red so it never impersonates a status chip).
    ret = (
        (
            dff.groupby("Category", observed=True)["Return_Flag"]
            .mean()
            .reindex(CATEGORY_ORDER)
            .dropna()
            * 100
        )
        .sort_values()
        .reset_index(name="Return_Rate")
    )
    ret["Label"] = ret["Return_Rate"].apply(lambda v: f"{v:.1f}%")
    fig_ret = px.bar(
        ret,
        x="Return_Rate",
        y="Category",
        orientation="h",
        title="Return Rate by Category",
        color_discrete_sequence=[C_FRICTION],
        text="Label",
    )
    fig_ret.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate=pct_hover_h("Category"),
    )
    style_bars(fig_ret, horizontal=True)
    fig_ret.update_layout(
        xaxis_title="Return Rate (%)",
        yaxis_title=None,
        margin=dict(l=170, r=60),
        xaxis=dict(range=[0, ret["Return_Rate"].max() * 1.3]),
    )
    finalize(fig_ret, height=320)

    # --- Monthly on-time rate. The bar chart above pools three years and lands near
    # 43% in every mode, which reads as "delivery is uniformly broken". The monthly
    # series says something quite different: a step change when the January 2025
    # contract started, and a collapse every October–November. Both facts are
    # invisible in the pooled average, so this chart carries the shading and the
    # event marker that make them unmissable.
    monthly_ops = A.monthly_operations(dff).reset_index()
    fig_ontime = px.line(
        monthly_ops,
        x="Order_YearMonth",
        y="On_Time_Pct",
        markers=True,
        title="On-Time Rate by Month: the average hides two stories",
        color_discrete_sequence=[C_REVENUE],
    )
    style_line(fig_ontime)
    fig_ontime.update_traces(hovertemplate="<b>%{y:.1f}%</b> on time<br>%{x|%b %Y}<extra></extra>")
    for _, row in monthly_ops[monthly_ops["Is_Peak"]].iterrows():
        month_start = row["Order_YearMonth"]
        fig_ontime.add_vrect(
            x0=month_start.isoformat(),
            x1=(month_start + pd.offsets.MonthEnd(1)).isoformat(),
            fillcolor=STATUS["critical"],
            opacity=0.07,
            line_width=0,
            layer="below",
        )
    _mark_event(
        fig_ontime, monthly_ops["Order_YearMonth"], A.LOGISTICS_START, "New logistics contract"
    )
    fig_ontime.update_layout(
        xaxis_title=None,
        yaxis_title="On-Time Rate (%)",
        yaxis=dict(range=[0, 100]),
        margin=dict(r=45),
    )
    finalize(fig_ontime, height=320)
    ontime_legend = status_legend((STATUS["critical"], "Shaded: Oct-Nov festive peak"))

    kpi_col = {"xs": 6, "md": 3}
    cards = dbc.Row(
        [
            dbc.Col(
                stat_card(
                    "On-Time Rate",
                    f"{dff['On_Time_Flag'].mean() * 100:.1f}%",
                    rate_status(dff["On_Time_Flag"].mean() * 100, 75, 50, lower_is_better=False),
                ),
                **kpi_col,
            ),
            dbc.Col(
                stat_card(
                    "Return Rate",
                    f"{dff['Return_Flag'].mean() * 100:.1f}%",
                    rate_status(dff["Return_Flag"].mean() * 100, 5, 10),
                ),
                **kpi_col,
            ),
            dbc.Col(
                stat_card(
                    "Cancellation Rate",
                    f"{dff['Cancellation_Flag'].mean() * 100:.1f}%",
                    rate_status(dff["Cancellation_Flag"].mean() * 100, 2, 5),
                ),
                **kpi_col,
            ),
            dbc.Col(
                stat_card(
                    "Complaint Rate",
                    f"{dff['Complaint_Flag'].mean() * 100:.1f}%",
                    rate_status(dff["Complaint_Flag"].mean() * 100, 5, 10),
                ),
                **kpi_col,
            ),
        ],
        className="g-3 mb-3",
    )

    ops_tbl = table_view(
        ops.round(1),
        ["Fulfillment_Mode", "Orders", "On_Time_Rate", "Avg_Rating"],
        "Fulfillment performance (filtered selection)",
        view,
    )

    return html.Div(
        [
            cards,
            dbc.Row(
                [
                    dbc.Col(
                        [graph(fig_ops, view), ops_legend], **CHART_COL, className="chart-cell"
                    ),
                    dbc.Col(graph(fig_complaint, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3",
            ),
            dbc.Row(
                [
                    dbc.Col(graph(fig_ret, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(
                        [graph(fig_ontime, view), ontime_legend],
                        **CHART_COL,
                        className="chart-cell",
                    ),
                ],
                className="g-3 mt-1",
            ),
            ops_tbl,
        ]
    )


def render_decision(dff: pd.DataFrame, view: ViewProfile) -> html.Div:
    """The page the case asks for last: what management should actually do.

    Every chart here exists to defend one of the three recommendations, and the
    two exhibits at the bottom are the pooled-versus-split pair — the view that
    would have sent leadership after the wrong problem, next to the one that
    corrects it.
    """
    if dff.empty:
        return empty_state()

    # --- Which lens actually splits profitability? Nominal dimensions, magnitude
    # on one axis -> one flat hue; the ordering IS the finding, so the bars are
    # sorted and the two the leadership team argued about are called out by name.
    drivers = A.driver_ranking(dff).sort_values("Weighted_SD_pp")
    drivers["Label"] = drivers["Weighted_SD_pp"].apply(lambda v: f"{v:.1f}")
    drivers["Dimension_Label"] = drivers["Dimension"].str.replace("_", " ")
    fig_drivers = px.bar(
        drivers,
        x="Weighted_SD_pp",
        y="Dimension_Label",
        orientation="h",
        title="What actually splits profitability",
        color_discrete_sequence=[C_REVENUE],
        text="Label",
        custom_data=["Profit_Gap_Mn", "Levels"],
    )
    fig_drivers.update_traces(
        textposition="outside",
        textfont_color=INK["secondary"],
        hovertemplate="<b>%{x:.1f} pts</b> revenue-weighted spread<br>%{y}<br>"
        "%{customdata[1]} levels · ₹%{customdata[0]:.1f}M profit gap<extra></extra>",
    )
    style_bars(fig_drivers, horizontal=True)
    fig_drivers.update_layout(
        xaxis_title="Revenue-weighted spread in margin (percentage points)",
        yaxis_title=None,
        margin=dict(l=160, r=60),
        xaxis=dict(range=[0, drivers["Weighted_SD_pp"].max() * 1.25]),
    )
    finalize(fig_drivers, height=430)

    # --- How much discount each part of the business can absorb. Two series with
    # opposite conclusions -> the first two fixed categorical slots, direct-labelled
    # at the line ends rather than via a legend the eye has to shuttle to.
    banded = A.discount_band_margin(dff, split="Category")
    banded["Side"] = (
        banded["Category"]
        .astype(str)
        .where(banded["Category"].astype(str) == "Electronics", "Rest of business")
    )
    side = (
        banded.groupby(["Side", "Discount_Band"], observed=True)[["Revenue", "Profit"]]
        .sum()
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reset_index()
    )
    fig_bands = px.line(
        side,
        x="Discount_Band",
        y="Margin_Pct",
        color="Side",
        markers=True,
        title="Margin by discount depth: the ceiling is category-specific",
        color_discrete_sequence=[CATEGORICAL[0], CATEGORICAL[1]],
        category_orders={
            "Discount_Band": A.DISCOUNT_BAND_LABELS,
            "Side": ["Rest of business", "Electronics"],
        },
    )
    style_line(fig_bands)
    fig_bands.update_traces(hovertemplate="<b>%{y:.1f}%</b> margin<br>%{x} discount<extra></extra>")
    fig_bands.add_hline(
        y=0,
        line_dash="dot",
        line_width=1,
        line_color=INK["axis"],
        annotation_text="break-even",
        annotation_font_color=INK["muted"],
        annotation_position="bottom left",
    )
    fig_bands.update_layout(
        xaxis_title="Discount applied", yaxis_title="Profit Margin (%)", **_legend_placement(view)
    )
    finalize(fig_bands, height=430)

    # --- The Question 4 pair. Same segments, same orders, two encodings: pooled
    # (a segment problem) and split by Electronics (a product-mix problem).
    confound = A.segment_margin_confound(dff).reindex(SEGMENT_ORDER).dropna(how="all").reset_index()
    confound["Label"] = confound["Margin_Pooled"].apply(lambda v: f"{v:.1f}%")
    # Deliberately grey: this is the view being rejected, and giving it an identity
    # hue would collide with the two series that Exhibit B uses to correct it.
    fig_pooled = px.bar(
        confound,
        x="Customer_Segment",
        y="Margin_Pooled",
        title="Exhibit A: margin by segment (pooled)",
        color_discrete_sequence=[INK["muted"]],
        text="Label",
    )
    fig_pooled.update_traces(
        textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Segment")
    )
    style_bars(fig_pooled)
    fig_pooled.update_layout(
        xaxis_title=None,
        yaxis_title="Margin (%)",
        showlegend=False,
        yaxis=dict(range=[0, confound["Margin_Pooled"].max() * 1.3]),
    )
    finalize(fig_pooled, height=360)

    split = confound.melt(
        id_vars="Customer_Segment",
        value_vars=["Margin_In_Electronics", "Margin_Ex_Electronics"],
        var_name="Basket",
        value_name="Margin_Pct",
    )
    split["Basket"] = split["Basket"].map(
        {"Margin_In_Electronics": "Electronics orders", "Margin_Ex_Electronics": "Everything else"}
    )
    fig_split = px.bar(
        split,
        x="Customer_Segment",
        y="Margin_Pct",
        color="Basket",
        barmode="group",
        title="Exhibit B: the same segments, split by what they bought",
        color_discrete_sequence=[CATEGORICAL[0], CATEGORICAL[1]],
        category_orders={"Basket": ["Everything else", "Electronics orders"]},
    )
    fig_split.update_traces(
        hovertemplate="<b>%{y:.1f}%</b> margin<br>%{x} · %{fullData.name}<extra></extra>"
    )
    style_bars(fig_split)
    fig_split.add_hline(y=0, line_color=INK["axis"], line_width=1)
    fig_split.update_layout(xaxis_title=None, yaxis_title="Margin (%)", **_legend_placement(view))
    finalize(fig_split, height=360)

    reading = dbc.Alert(
        [
            html.B("How to read the pair: "),
            "Exhibit A is accurate and would send us after the Premium segment. Exhibit B "
            "shows Premium's margin is ordinary once you separate Electronics from everything "
            "else. It simply buys Electronics more than any other segment does. The problem "
            "is the product, not the customer, and only the split view says so.",
        ],
        color="light",
        className="story-callout",
    )

    cards = dbc.Row(
        [
            dbc.Col(
                recommendation_card(
                    1,
                    "Re-cost and re-price Electronics before scaling it",
                    "Electronics is half of revenue at a negative margin, and merchandise "
                    "cost alone eats 94% of what those orders recognise. Smartphones account "
                    "for most of it.",
                    "Bringing Electronics to break-even recovers the largest single pool of "
                    "lost contribution in the dataset without touching demand elsewhere.",
                    "Electronics drives traffic and basket-building; repricing it may cost "
                    "volume and the attached sales that come with it.",
                    "SKU-level cost and competitor price data. The dataset cannot say whether "
                    "this is a procurement problem or a pricing one.",
                    STATUS["critical"],
                ),
                md=4,
            ),
            dbc.Col(
                recommendation_card(
                    2,
                    "Set a category-aware discount ceiling; retire Flash Deals",
                    "Discount depth is uniform across categories but tolerance is not: the "
                    "rest of the business still earns double digits at 25% off, Electronics "
                    "turns loss-making above 10%. Flash Deals are the only promotion with a "
                    "negative margin.",
                    "Recovers margin on promoted orders with a rule that can be enforced in "
                    "the pricing system next quarter, not a strategic bet.",
                    "Promotion is partly defensive; withdrawing Flash Deals may shift volume "
                    "to competitors or simply move it to other discounts.",
                    "Promotion-level incrementality: the dataset shows what promoted orders "
                    "earned, not what would have happened without the promotion.",
                    STATUS["serious"],
                ),
                md=4,
            ),
            dbc.Col(
                recommendation_card(
                    3,
                    "Underwrite acquisition on contribution, not revenue",
                    "Under Accelerate 2.0 revenue per month rose far faster than profit per "
                    "month, and the paid channels' margins fell furthest while spending the "
                    "largest share of the revenue they generate.",
                    "Reallocating spend toward the channels that held their margin protects "
                    "growth while stopping the purchase of revenue at near-zero contribution.",
                    "Paid channels may be seeding customers whose value shows up later; "
                    "order-level data cannot see a lifetime.",
                    "Cohort retention and repeat-purchase value by acquisition channel.",
                    STATUS["warning"],
                ),
                md=4,
            ),
        ],
        className="g-3 mb-3",
    )

    stakes = A.group_economics(dff, "Category").reset_index()
    stakes_tbl = table_view(
        stakes.assign(
            Revenue=lambda d: d["Revenue"].round(0), Profit=lambda d: d["Profit"].round(0)
        ),
        ["Category", "Revenue", "Profit", "Margin_Pct", "Avg_Discount", "Revenue_Share_Pct"],
        "Profit at stake by category (filtered selection)",
        view,
    )

    return html.Div(
        [
            dbc.Alert(
                [
                    html.B("Three actions, in priority order. "),
                    "Each is sized by the contribution it puts at stake, and each names the "
                    "one piece of information we would want before committing. "
                    "Recommendations were framed on the full Jan 2023 to Dec 2025 period; "
                    "the charts below follow your filters.",
                ],
                color="light",
                className="story-callout",
            ),
            cards,
            dbc.Row(
                [
                    dbc.Col(graph(fig_drivers, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_bands, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3",
            ),
            reading,
            dbc.Row(
                [
                    dbc.Col(graph(fig_pooled, view), **CHART_COL, className="chart-cell"),
                    dbc.Col(graph(fig_split, view), **CHART_COL, className="chart-cell"),
                ],
                className="g-3 mt-1",
            ),
            stakes_tbl,
        ]
    )


RENDERERS = {
    "overview": render_overview,
    "profitability": render_profitability,
    "customers": render_customers,
    "operations": render_operations,
    "decision": render_decision,
}

# --------------------------------------------------------------------------- app

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="AuroraCart Diagnostic Dashboard",
    suppress_callback_exceptions=True,
    meta_tags=[
        # Without this, mobile browsers render at a ~980px virtual width and
        # scale the whole page down — the single most common reason a Dash app
        # looks "broken" on a phone. `viewport-fit=cover` lets the layout reach
        # under a notch, which style.css then pads back with safe-area insets.
        {"name": "viewport", "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
        # No `maximum-scale` / `user-scalable=no`: pinch-zoom stays available.
        # Suppressing it would fail WCAG 2.1 SC 1.4.4 (Resize Text).
        {
            "name": "description",
            "content": "AuroraCart profitability & operations diagnostic: revenue, margin, "
            "customers and delivery performance, Jan 2023 to Dec 2025.",
        },
        {"name": "theme-color", "content": "#0d0d0d"},
        {"name": "color-scheme", "content": "dark"},
        {"name": "mobile-web-app-capable", "content": "yes"},
        {"name": "apple-mobile-web-app-capable", "content": "yes"},
        {"name": "apple-mobile-web-app-status-bar-style", "content": "black-translucent"},
        {"name": "apple-mobile-web-app-title", "content": "AuroraCart"},
        # Stops iOS Safari turning order counts and dates into blue "call" links.
        {"name": "format-detection", "content": "telephone=no"},
    ],
)
server = app.server  # exposed for gunicorn via the root `app.py`: `gunicorn app:server`

# Dash renders its scripts at the end of <body>, which would leave the first
# paint un-stamped. This inline snippet applies a provisional viewport class in
# <head> so the page never flashes a desktop-shaped layout on a phone;
# assets/environment.js then takes over and replaces these with the full set.
app.index_string = """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script>
        (function () {
          try {
            var d = document.documentElement;
            var w = window.innerWidth || d.clientWidth || 1024;
            var h = window.innerHeight || d.clientHeight || 768;
            d.classList.add("env-" + (w >= 1400 ? "xxl" : w >= 1200 ? "xl" : w >= 992 ? "lg"
                                    : w >= 768 ? "md" : w >= 576 ? "sm" : "xs"));
            if (w < 768) d.classList.add("env-narrow");
            if (w < 992) d.classList.add("env-compact");
            if ((navigator.maxTouchPoints || 0) > 0 || "ontouchstart" in window) {
              d.classList.add("env-touch");
            }
            d.style.setProperty("--vh", (h / 100) + "px");
          } catch (e) { /* CSS media queries still lay the page out correctly */ }
        })();
        </script>
    </head>
    <body>
        <noscript>
          <div style="margin:12px;padding:12px;border:1px solid #383835;border-radius:10px;
                      font-family:system-ui,sans-serif;font-size:13px;background:#1a1a19;color:#c3c2b7">
            This dashboard needs JavaScript for its charts and filters. The layout below is
            still responsive, but the interactive views will not load.
          </div>
        </noscript>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

# Column spans per tier. At `lg` all six controls share one row (3+2+2+2+2+1);
# at `md` they fold into two rows of twelve (6+3+3 / 3+3+6); on a phone the date
# range and Reset take a full row each and the four dropdowns pair up two-across.
_FILTER_WIDE = {"xs": 12, "md": 6, "lg": 3}
_FILTER_NARROW = {"xs": 6, "md": 3, "lg": 2}
_FILTER_RESET = {"xs": 12, "md": 6, "lg": 1}

filter_bar = dbc.Row(
    [
        dbc.Col(
            [
                html.Label("Date Range", className="filter-label"),
                dcc.DatePickerRange(
                    id="date-range",
                    min_date_allowed=MIN_DATE,
                    max_date_allowed=MAX_DATE,
                    start_date=MIN_DATE,
                    end_date=MAX_DATE,
                    display_format="MMM YYYY",
                    className="filter-control",
                    # Overridden per-viewport by `adapt_date_picker` below: one month
                    # and a full-screen calendar on a phone, two months inline on a
                    # desktop. A two-month inline calendar does not fit under 500px.
                    number_of_months_shown=2,
                ),
            ],
            **_FILTER_WIDE,
            className="filter-col",
        ),
        dbc.Col(
            [
                html.Label("Region", className="filter-label"),
                dcc.Dropdown(
                    id="region-filter", options=REGION_ORDER, multi=True, placeholder="All regions"
                ),
            ],
            **_FILTER_NARROW,
            className="filter-col",
        ),
        dbc.Col(
            [
                html.Label("Category", className="filter-label"),
                dcc.Dropdown(
                    id="category-filter",
                    options=CATEGORY_ORDER,
                    multi=True,
                    placeholder="All categories",
                ),
            ],
            **_FILTER_NARROW,
            className="filter-col",
        ),
        dbc.Col(
            [
                html.Label("Customer Segment", className="filter-label"),
                dcc.Dropdown(
                    id="segment-filter",
                    options=SEGMENT_ORDER,
                    multi=True,
                    placeholder="All segments",
                ),
            ],
            **_FILTER_NARROW,
            className="filter-col",
        ),
        dbc.Col(
            [
                html.Label("Fulfillment Mode", className="filter-label"),
                dcc.Dropdown(
                    id="fulfillment-filter",
                    options=FULFILLMENT_ORDER,
                    multi=True,
                    placeholder="All modes",
                ),
            ],
            **_FILTER_NARROW,
            className="filter-col",
        ),
        dbc.Col(
            [
                # The spacer label only exists to align Reset with the controls on the
                # single-row desktop layout; on smaller tiers it would be dead space.
                html.Label(" ", className="filter-label d-none d-lg-block"),
                dbc.Button("Reset", id="reset-btn", color="light", className="w-100 reset-btn"),
            ],
            **_FILTER_RESET,
            className="filter-col",
        ),
    ],
    className="g-2 filter-bar",
)

# On a phone the filter panel is ~3 rows tall — worth having, but not worth
# scrolling past on every visit. The toggle is CSS-hidden from `md` up, and the
# panel starts open so nothing is ever hidden without the user asking.
filter_panel = html.Div(
    [
        dbc.Button(id="filter-toggle", color="light", className="filter-toggle", n_clicks=0),
        dbc.Collapse(filter_bar, id="filter-collapse", is_open=True),
    ]
)

app.layout = dbc.Container(
    [
        # Populated by assets/environment.js — see the module docstring. Nothing
        # breaks if it stays empty; the server just uses its default profile.
        dcc.Store(id="env-store", storage_type="memory"),
        html.Div(
            [
                html.Div("AC", className="brand-mark"),
                html.Div(
                    [
                        html.H1("AuroraCart at a Crossroads", className="page-title"),
                        html.P(
                            "Revenue is growing. Is value? A profitability & operations "
                            "diagnostic, Jan 2023 to Dec 2025.",
                            className="page-subtitle",
                        ),
                    ]
                ),
            ],
            className="header",
        ),
        filter_panel,
        dcc.Tabs(
            id="tabs",
            value="overview",
            className="app-tabs",
            children=[
                dcc.Tab(label="Executive Overview", value="overview"),
                dcc.Tab(label="Profitability Deep-Dive", value="profitability"),
                dcc.Tab(label="Customers", value="customers"),
                dcc.Tab(label="Operations & Delivery", value="operations"),
                dcc.Tab(label="Decision", value="decision"),
            ],
        ),
        dcc.Loading(
            html.Div(id="tab-content", className="tab-content"), type="circle", color=CATEGORICAL[0]
        ),
        html.Footer(
            [
                html.Div(
                    "Synthetic case-study dataset (AuroraCart at a Crossroads). "
                    "Cancelled orders are excluded from revenue/margin figures; returns are not "
                    "netted out of Net_Revenue. See the EDA notebook and README for full "
                    "methodology and limitations."
                ),
                html.Div(id="env-readout", className="env-readout"),
            ],
            className="footer",
        ),
    ],
    fluid=True,
    className="app-container",
)


# Seeds env-store on page load. assets/environment.js keeps it current
# afterwards by calling dash_clientside.set_props on resize/rotation, so this
# fires exactly once. The `id` prop is a stable Input that never changes — the
# standard way to run a clientside callback at startup.
app.clientside_callback(
    """
    function (_) {
        if (window.auroracartEnv && window.auroracartEnv.profile) {
            return window.auroracartEnv.profile();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("env-store", "data"),
    Input("env-store", "id"),
)


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("region-filter", "value"),
    Input("category-filter", "value"),
    Input("segment-filter", "value"),
    Input("fulfillment-filter", "value"),
    Input("env-store", "data"),
)
def update_tab(tab, start_date, end_date, regions, categories, segments, fulfillment, env):
    dff = apply_filters(DF, start_date, end_date, regions, categories, segments, fulfillment)
    return RENDERERS[tab](dff, profile_from_store(env))


@app.callback(
    Output("date-range", "number_of_months_shown"),
    Output("date-range", "with_full_screen_portal"),
    Input("env-store", "data"),
)
def adapt_date_picker(env):
    """Give the date picker a phone-shaped calendar.

    An inline two-month calendar is ~600px wide and gets clipped by the viewport
    on any phone. Below `md` it drops to a single month presented in a
    full-screen portal, which is both readable and thumb-reachable.
    """
    view = profile_from_store(env)
    return view.date_months_shown, view.is_narrow


@app.callback(
    Output("env-readout", "children"),
    Input("env-store", "data"),
)
def show_environment(env):
    """Surface what the app detected — useful when a layout looks wrong on an
    unfamiliar device and someone needs to report what it actually saw."""
    return profile_from_store(env).describe()


@app.callback(
    Output("filter-collapse", "is_open"),
    Output("filter-toggle", "children"),
    Input("filter-toggle", "n_clicks"),
    Input("region-filter", "value"),
    Input("category-filter", "value"),
    Input("segment-filter", "value"),
    Input("fulfillment-filter", "value"),
)
def toggle_filters(n_clicks, regions, categories, segments, fulfillment):
    """Collapse the filter panel on small screens, and label the toggle with how
    many filters are active — so a collapsed panel never hides a live filter."""
    is_open = (n_clicks or 0) % 2 == 0
    active = sum(len(values) for values in (regions, categories, segments, fulfillment) if values)
    suffix = f" · {active} active" if active else ""
    return is_open, f"{'Hide' if is_open else 'Show'} filters{suffix}"


@app.callback(
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Output("region-filter", "value"),
    Output("category-filter", "value"),
    Output("segment-filter", "value"),
    Output("fulfillment-filter", "value"),
    Input("reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    return MIN_DATE, MAX_DATE, None, None, None, None


def main() -> None:
    """Run the development server (``python app.py`` / ``auroracart-dashboard``)."""
    app.run(debug=True)


if __name__ == "__main__":
    main()
