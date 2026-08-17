"""AuroraCart at a Crossroads — interactive profitability & operations dashboard.

Run locally:      python dashboard.py            (http://127.0.0.1:8050)
Run for prod:      gunicorn dashboard:server

Layout: a global filter bar (date range, region, category, segment, fulfillment
mode) drives four tabs — Executive Overview, Profitability Deep-Dive, Customers,
and Operations & Delivery — each answering a different slice of "what should
AuroraCart do next, and what evidence supports it."

Every chart below is built against the dataviz skill's checklist: the color job
(categorical/sequential/ordinal/diverging/status) matches what the data actually
is, marks are thin with rounded bar ends and >=8px ringed line markers, bars carry
direct value-at-tip labels, hover tooltips lead with the value, and each tab keeps
a plain-table twin so nothing is gated behind a hover.
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

from data_prep import (
    CATEGORY_ORDER,
    FULFILLMENT_ORDER,
    LOYALTY_ORDER,
    PROMOTION_ORDER,
    REGION_ORDER,
    SEGMENT_ORDER,
    load_data,
)
from viz_theme import (
    CATEGORICAL,
    DIVERGING_BLUE_RED,
    INK,
    ORDINAL_BLUE_4,
    SEQUENTIAL_BLUE,
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
C_REVENUE = CATEGORICAL[0]      # blue
C_COST = CATEGORICAL[1]         # orange
C_PROFIT = CATEGORICAL[5]       # green
C_FRICTION = CATEGORICAL[6]     # violet — returns/friction, deliberately not status-red

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


def rate_status(value: float, good_max: float, warn_max: float, lower_is_better: bool = True) -> str:
    """Map a rate to a fixed status band. lower_is_better=False flips the direction (e.g. on-time %)."""
    if not lower_is_better:
        return STATUS["good"] if value >= good_max else STATUS["warning"] if value >= warn_max else STATUS["critical"]
    return STATUS["good"] if value <= good_max else STATUS["warning"] if value <= warn_max else STATUS["critical"]


def stat_card(label: str, value: str, accent: str = CATEGORICAL[0], sub: str | None = None,
              delta: float | None = None, delta_good_if_up: bool = True, delta_suffix: str = " pts") -> dbc.Card:
    delta_el = html.Div(sub or " ", className="stat-sub")
    if delta is not None:
        up = delta > 0
        good = (up == delta_good_if_up) if delta != 0 else True
        arrow = "▲" if up else ("▼" if delta < 0 else "●")
        color = STATUS["good"] if good else STATUS["critical"]
        delta_el = html.Div(
            f"{arrow} {abs(delta):.1f}{delta_suffix} vs full period",
            className="stat-delta", style={"color": color},
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


def apply_filters(df: pd.DataFrame, start_date, end_date, regions, categories, segments, fulfillment) -> pd.DataFrame:
    mask = (df["Order_Date"] >= pd.to_datetime(start_date)) & (df["Order_Date"] <= pd.to_datetime(end_date))
    if regions:
        mask &= df["Region"].isin(regions)
    if categories:
        mask &= df["Category"].isin(categories)
    if segments:
        mask &= df["Customer_Segment"].isin(segments)
    if fulfillment:
        mask &= df["Fulfillment_Mode"].isin(fulfillment)
    return df.loc[mask]


def table_view(df: pd.DataFrame, columns: list[str], title: str) -> html.Div:
    """A plain data table beneath the charts — the WCAG-clean twin of every chart above it."""
    return html.Div(
        [
            html.Div(title, className="table-title"),
            dash_table.DataTable(
                data=df[columns].round(2).to_dict("records"),
                columns=[{"name": c.replace("_", " "), "id": c} for c in columns],
                style_table={"overflowX": "auto"},
                style_cell={"fontFamily": "system-ui, sans-serif", "fontSize": 13, "padding": "6px 10px",
                            "backgroundColor": SURFACE, "color": INK["primary"], "border": "none",
                            "borderBottom": f"1px solid {INK['grid']}", "fontVariantNumeric": "tabular-nums"},
                style_header={"fontWeight": 600, "backgroundColor": SURFACE, "color": INK["secondary"],
                              "borderBottom": f"2px solid {INK['axis']}"},
                page_size=10,
            ),
        ],
        className="table-wrap",
    )


def status_legend(*items: tuple[str, str]) -> html.Div:
    """Icon+label caption for a status-colored chart — status color is never hue-alone."""
    chips = []
    for color, label in items:
        chips.append(html.Span([html.Span(className="legend-dot", style={"background": color}), label],
                                className="legend-chip"))
    return html.Div(chips, className="status-legend")


def _outside_label_range(series: pd.Series, pad: float = 0.22) -> list[float]:
    lo, hi = min(0, series.min()), series.max()
    span = hi - lo
    return [lo - span * pad if lo < 0 else 0, hi + span * pad]


# --------------------------------------------------------------------------- tab renderers


def render_overview(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]
    revenue = valid["Net_Revenue"].sum()
    profit = valid["Profit"].sum()
    margin = (profit / revenue * 100) if revenue else float("nan")
    aov = (revenue / len(valid)) if len(valid) else float("nan")
    on_time = dff["On_Time_Flag"].mean() * 100
    is_filtered = len(dff) < len(DF)

    cards = dbc.Row(
        [
            dbc.Col(stat_card("Net Revenue", format_inr(revenue), C_REVENUE), md=2),
            dbc.Col(stat_card("Profit", format_inr(profit), C_PROFIT), md=2),
            dbc.Col(stat_card("Profit Margin", f"{margin:.1f}%",
                               rate_status(margin, 12, 9, lower_is_better=False),
                               delta=(margin - BASELINE_MARGIN) if is_filtered else None), md=2),
            dbc.Col(stat_card("Orders", f"{len(dff):,}", CATEGORICAL[3]), md=2),
            dbc.Col(stat_card("Avg Order Value", format_inr(aov), CATEGORICAL[4]), md=2),
            dbc.Col(stat_card("On-Time Delivery", f"{on_time:.1f}%",
                               rate_status(on_time, 75, 50, lower_is_better=False),
                               delta=(on_time - BASELINE_ON_TIME) if is_filtered else None,
                               delta_good_if_up=True, delta_suffix=" pts"), md=2),
        ],
        className="g-3 mb-3",
    )

    monthly = (
        valid.groupby("Order_YearMonth")
        .agg(Net_Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Net_Revenue"] * 100)
        .reset_index()
    )

    # --- Monthly Net Revenue: single-series trend -> sequential blue, ~10% wash + 2px line.
    fig_rev = px.area(monthly, x="Order_YearMonth", y="Net_Revenue", title="Monthly Net Revenue",
                       color_discrete_sequence=[C_REVENUE])
    wash_area(fig_rev, C_REVENUE)
    fig_rev.update_traces(hovertemplate="<b>₹%{y:,.0f}</b><br>%{x|%b %Y}<extra></extra>")
    last = monthly.iloc[-1]
    fig_rev.add_annotation(x=last["Order_YearMonth"], y=last["Net_Revenue"],
                            text=f"₹{last['Net_Revenue'] / 1e6:.1f}M", showarrow=False, yshift=16,
                            xanchor="right", font=dict(color=INK["secondary"], size=12))
    fig_rev.update_layout(xaxis_title=None, yaxis_title="Net Revenue (₹)", margin=dict(r=45))
    finalize(fig_rev, height=320)

    # --- Monthly Margin: the headline concern -> emphasis (status critical), end-labeled.
    fig_margin = px.line(monthly, x="Order_YearMonth", y="Margin_Pct", title="Monthly Profit Margin (%)",
                          markers=True, color_discrete_sequence=[STATUS["critical"]])
    style_line(fig_margin)
    fig_margin.update_traces(hovertemplate="<b>%{y:.1f}%</b><br>%{x|%b %Y}<extra></extra>")
    fig_margin.add_hline(y=margin, line_dash="dot", line_width=1, line_color=INK["axis"],
                          annotation_text="period average", annotation_font_color=INK["muted"],
                          annotation_position="top left")
    trend = "▼" if monthly["Margin_Pct"].iloc[-1] < monthly["Margin_Pct"].iloc[0] else "▲"
    fig_margin.add_annotation(x=last["Order_YearMonth"], y=monthly["Margin_Pct"].iloc[-1],
                               text=f"{trend} {monthly['Margin_Pct'].iloc[-1]:.1f}%", showarrow=False, yshift=16,
                               xanchor="right", font=dict(color=STATUS["critical"], size=12))
    fig_margin.update_layout(xaxis_title=None, yaxis_title="Margin (%)", margin=dict(r=45))
    finalize(fig_margin, height=320)

    # --- Revenue by Category: magnitude on a nominal axis -> one flat hue, value at tip.
    cat_rev = (
        valid.groupby("Category", observed=True)["Net_Revenue"].sum().reindex(CATEGORY_ORDER).dropna()
        .sort_values().reset_index()
    )
    cat_rev["Label"] = cat_rev["Net_Revenue"].apply(lambda v: f"₹{v / 1e6:,.1f}M")
    fig_cat = px.bar(cat_rev, x="Net_Revenue", y="Category", orientation="h", title="Revenue by Category",
                      color_discrete_sequence=[C_REVENUE], text="Label")
    fig_cat.update_traces(textposition="outside", textfont_color=INK["secondary"],
                           hovertemplate=money_hover_h("Category"))
    style_bars(fig_cat, horizontal=True)
    fig_cat.update_layout(xaxis_title="Net Revenue (₹)", yaxis_title=None, margin=dict(l=170, r=60),
                           xaxis=dict(range=[0, cat_rev["Net_Revenue"].max() * 1.22]))
    finalize(fig_cat, height=320)

    # --- Revenue by Region: same job, same hue (consistency = the point).
    reg_rev = valid.groupby("Region", observed=True)["Net_Revenue"].sum().reindex(REGION_ORDER).dropna().reset_index()
    reg_rev["Label"] = reg_rev["Net_Revenue"].apply(lambda v: f"₹{v / 1e6:,.1f}M")
    fig_reg = px.bar(reg_rev, x="Region", y="Net_Revenue", title="Revenue by Region",
                      color_discrete_sequence=[C_REVENUE], text="Label")
    fig_reg.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=money_hover_h("Region"))
    style_bars(fig_reg)
    fig_reg.update_layout(xaxis_title=None, yaxis_title="Net Revenue (₹)",
                           yaxis=dict(range=[0, reg_rev["Net_Revenue"].max() * 1.2]))
    finalize(fig_reg, height=320)

    story = dbc.Alert(
        [
            html.B("The story: "),
            "Revenue is growing, but margin is not keeping pace — and in this filtered view it stands at ",
            html.B(f"{margin:.1f}%"),
            ". Use the Profitability tab to see which categories and promotions are driving that down.",
        ],
        color="light", className="story-callout",
    )

    yearly_tbl = (
        valid.assign(Year=valid["Order_Date"].dt.year)
        .groupby("Year").agg(Net_Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Net_Revenue"] * 100)
        .reset_index()
    )

    return html.Div([
        cards,
        story,
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_rev, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_margin, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_cat, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_reg, config={"displayModeBar": False}), md=6)], className="g-3 mt-1"),
        table_view(yearly_tbl, ["Year", "Net_Revenue", "Profit", "Margin_Pct", "Orders"],
                   "Year-over-year revenue & margin (filtered selection)"),
    ])


def render_profitability(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]

    # --- Margin by Category: crosses zero -> diverging (blue = profitable, red = loss-making).
    cat = (
        valid.groupby("Category", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(CATEGORY_ORDER).dropna().sort_values("Margin_Pct").reset_index()
    )
    cat["Label"] = cat["Margin_Pct"].apply(lambda v: f"{v:+.1f}%")
    fig_cat = px.bar(cat, x="Margin_Pct", y="Category", orientation="h", title="Profit Margin by Category",
                      color="Margin_Pct", color_continuous_scale=DIVERGING_BLUE_RED, color_continuous_midpoint=0,
                      text="Label")
    fig_cat.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover_h("Category"))
    fig_cat.add_vline(x=0, line_color=INK["axis"], line_width=1)
    style_bars(fig_cat, horizontal=True)
    fig_cat.update_layout(xaxis_title="Profit Margin (%)", yaxis_title=None, coloraxis_showscale=False,
                           margin=dict(l=170, r=60), xaxis=dict(range=_outside_label_range(cat["Margin_Pct"])))
    finalize(fig_cat, height=340)

    # --- Discount vs Margin by Promotion: 5 named points -> diverging-by-margin (not 5 categorical
    # hues, which fails the all-pairs CVD gate for scatter forms); identity carried by direct labels.
    promo = (
        valid.groupby("Promotion_Type", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"),
             Avg_Discount=("Discount_Percentage", "mean"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(PROMOTION_ORDER).dropna().reset_index()
    )
    fig_promo = px.scatter(promo, x="Avg_Discount", y="Margin_Pct", size="Revenue", text="Promotion_Type",
                            color="Margin_Pct", color_continuous_scale=DIVERGING_BLUE_RED, color_continuous_midpoint=0,
                            title="Discount Depth vs Margin by Promotion", size_max=46)
    fig_promo.update_traces(
        marker=dict(sizemin=16, line=dict(width=2, color=SURFACE)),
        hovertemplate="<b>%{text}</b><br>Margin: %{y:.1f}%<br>Avg discount: %{x:.1f}%<br>Revenue: ₹%{marker.size:,.0f}<extra></extra>",
    )
    fig_promo.add_hline(y=0, line_dash="dot", line_color=INK["axis"], line_width=1,
                         annotation_text="break-even", annotation_font_color=INK["muted"],
                         annotation_position="top left")
    # A single trace now (color is the continuous margin value, not a per-category split), so
    # per-point label placement is a LIST aligned to row order — not a per-trace assignment.
    label_pos = {"No Promotion": "top center", "Category Offer": "top center", "Member Offer": "bottom center",
                 "Festival Sale": "top center", "Flash Deal": "bottom center"}
    fig_promo.data[0].textposition = [label_pos[p] for p in promo["Promotion_Type"]]
    fig_promo.data[0].textfont = dict(color=INK["primary"], size=12)
    y_pad = max((promo["Margin_Pct"].max() - promo["Margin_Pct"].min()) * 0.25, 2)
    fig_promo.update_layout(
        xaxis_title="Average Discount (%)", yaxis_title="Profit Margin (%)", showlegend=False,
        coloraxis_showscale=False,
        yaxis=dict(range=[promo["Margin_Pct"].min() - y_pad, promo["Margin_Pct"].max() + y_pad]),
    )
    finalize(fig_promo, height=340)

    seg = (
        valid.groupby("Customer_Segment", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100, AOV=lambda d: d["Revenue"] / d["Orders"])
        .reindex(SEGMENT_ORDER).dropna().reset_index()
    )
    seg["AOV_Label"] = seg["AOV"].apply(lambda v: f"₹{v:,.0f}")
    seg["Margin_Label"] = seg["Margin_Pct"].apply(lambda v: f"{v:.1f}%")

    # --- Segment AOV: nominal category, magnitude -> flat blue (revenue-family), value at tip.
    fig_seg = px.bar(seg, x="Customer_Segment", y="AOV", title="Customer Segment — Average Order Value",
                      color_discrete_sequence=[C_REVENUE], text="AOV_Label")
    fig_seg.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=money_hover("Segment"))
    style_bars(fig_seg)
    fig_seg.update_layout(xaxis_title=None, yaxis_title="AOV (₹)", showlegend=False,
                           yaxis=dict(range=[0, seg["AOV"].max() * 1.2]))
    finalize(fig_seg, height=320)

    # --- Segment Margin: same nominal axis -> flat green (profit-family), NOT a value ramp
    # (ramping color by the same value the bar height already shows double-encodes on a
    # category with no natural order — the anti-pattern this palette explicitly forbids).
    fig_seg_margin = px.bar(seg, x="Customer_Segment", y="Margin_Pct", title="Customer Segment — Profit Margin",
                             color_discrete_sequence=[C_PROFIT], text="Margin_Label")
    fig_seg_margin.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Segment"))
    style_bars(fig_seg_margin)
    fig_seg_margin.update_layout(xaxis_title=None, yaxis_title="Margin (%)", showlegend=False,
                                  yaxis=dict(range=[0, seg["Margin_Pct"].max() * 1.25]))
    finalize(fig_seg_margin, height=320)

    tbl = table_view(
        cat.assign(Revenue=lambda d: d["Revenue"].round(0), Profit=lambda d: d["Profit"].round(0)),
        ["Category", "Revenue", "Profit", "Orders", "Margin_Pct"],
        "Category profitability (filtered selection, worst margin first)",
    )

    return html.Div([
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_cat, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_promo, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_seg, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_seg_margin, config={"displayModeBar": False}), md=6)],
                className="g-3 mt-1"),
        tbl,
    ])


def render_customers(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]

    # --- New vs Returning: 2-series identity -> first two fixed slots in order (validated
    # adjacent pair, both clear the light-surface contrast floor without needing relief).
    nvr = (
        valid.groupby("New_vs_Returning")
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(["New", "Returning"]).reset_index()
    )
    nvr["Label"] = nvr["Margin_Pct"].apply(lambda v: f"{v:.1f}%")
    fig_nvr = px.bar(nvr, x="New_vs_Returning", y="Margin_Pct", title="Profit Margin: New vs Returning",
                      color="New_vs_Returning", color_discrete_sequence=[CATEGORICAL[0], CATEGORICAL[1]],
                      text="Label", category_orders={"New_vs_Returning": ["New", "Returning"]})
    fig_nvr.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Customer"))
    style_bars(fig_nvr)
    fig_nvr.update_layout(xaxis_title=None, yaxis_title="Margin (%)", showlegend=False,
                           yaxis=dict(range=[0, nvr["Margin_Pct"].max() * 1.25]))
    finalize(fig_nvr, height=320)

    # --- Loyalty Status: New -> Champion is a genuine progression -> ordinal ramp, not a flat
    # color (this is the one axis in the dashboard where a lightness ramp is the correct job).
    loyalty = (valid.groupby("Loyalty_Status", observed=True)["Order_ID"].count()
               .reindex(LOYALTY_ORDER).dropna().reset_index(name="Orders"))
    loyalty["Label"] = loyalty["Orders"].apply(lambda v: f"{v:,}")
    fig_loy = px.bar(loyalty, x="Loyalty_Status", y="Orders", title="Orders by Loyalty Status (New → Champion)",
                      color="Loyalty_Status", color_discrete_sequence=ORDINAL_BLUE_4,
                      category_orders={"Loyalty_Status": LOYALTY_ORDER}, text="Label")
    fig_loy.update_traces(textposition="outside", textfont_color=INK["secondary"],
                           hovertemplate="<b>%{y:,}</b> orders<br>%{x}<extra></extra>")
    style_bars(fig_loy)
    fig_loy.update_layout(xaxis_title=None, yaxis_title="Orders", showlegend=False,
                           yaxis=dict(range=[0, loyalty["Orders"].max() * 1.2]))
    finalize(fig_loy, height=320)

    # --- Marketing cost as % of revenue: nominal category -> flat orange (cost-family hue).
    chan = (
        valid.groupby("Acquisition_Channel")
        .agg(Revenue=("Net_Revenue", "sum"), Orders=("Order_ID", "count"), Marketing_Cost=("Marketing_Cost", "sum"))
        .assign(Marketing_Pct=lambda d: d["Marketing_Cost"] / d["Revenue"] * 100)
        .sort_values("Marketing_Pct").reset_index()
    )
    chan["Label"] = chan["Marketing_Pct"].apply(lambda v: f"{v:.1f}%")
    fig_chan = px.bar(chan, x="Marketing_Pct", y="Acquisition_Channel", orientation="h",
                       title="Marketing Cost as % of Revenue, by Channel", color_discrete_sequence=[C_COST],
                       text="Label")
    fig_chan.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover_h("Channel"))
    style_bars(fig_chan, horizontal=True)
    fig_chan.update_layout(xaxis_title="Marketing Cost / Revenue (%)", yaxis_title=None, margin=dict(l=150, r=50),
                            xaxis=dict(range=[0, chan["Marketing_Pct"].max() * 1.25]))
    finalize(fig_chan, height=340)

    # --- Rating distribution: single continuous series -> sequential blue, thin bins.
    fig_rating = px.histogram(valid.dropna(subset=["Customer_Rating"]), x="Customer_Rating", nbins=10,
                               title="Customer Rating Distribution", color_discrete_sequence=[C_REVENUE])
    fig_rating.update_traces(marker=dict(cornerradius=2), hovertemplate="<b>%{y:,}</b> orders<br>rating %{x}<extra></extra>")
    fig_rating.update_layout(xaxis_title="Rating", yaxis_title="Orders", bargap=0.12, showlegend=False)
    finalize(fig_rating, height=340)

    chan_tbl = table_view(
        chan.assign(Revenue=lambda d: d["Revenue"].round(0), Marketing_Cost=lambda d: d["Marketing_Cost"].round(0)),
        ["Acquisition_Channel", "Revenue", "Orders", "Marketing_Cost", "Marketing_Pct"],
        "Acquisition channel economics (filtered selection)",
    )

    return html.Div([
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_nvr, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_loy, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_chan, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_rating, config={"displayModeBar": False}), md=6)],
                className="g-3 mt-1"),
        chan_tbl,
    ])


def render_operations(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()

    # --- On-Time Rate: nominal fulfillment modes, but color carries a genuine fixed-threshold
    # STATE (critical/warning/good), not rank -> status tokens, paired with a caption (never
    # hue-alone) since status color always ships with an icon + label.
    ops = (dff.groupby("Fulfillment_Mode", observed=True)
           .agg(On_Time_Rate=("On_Time_Flag", "mean"), Orders=("Order_ID", "count"), Avg_Rating=("Customer_Rating", "mean"))
           .assign(On_Time_Rate=lambda d: d["On_Time_Rate"] * 100)
           .reindex(FULFILLMENT_ORDER).dropna().reset_index())
    ops["Status_Color"] = ops["On_Time_Rate"].apply(lambda v: rate_status(v, 75, 50, lower_is_better=False))
    ops["Label"] = ops["On_Time_Rate"].apply(lambda v: f"{v:.0f}%")
    fig_ops = go.Figure(go.Bar(
        x=ops["Fulfillment_Mode"], y=ops["On_Time_Rate"], marker=dict(color=ops["Status_Color"], cornerradius=4),
        text=ops["Label"], textposition="outside", textfont=dict(color=INK["secondary"]),
        hovertemplate="<b>%{y:.1f}%</b> on time<br>%{x}<extra></extra>",
    ))
    fig_ops.add_hline(y=100, line_dash="dot", line_width=1, line_color=INK["grid"])
    fig_ops.add_hline(y=75, line_dash="dot", line_width=1, line_color=STATUS["good"],
                       annotation_text="target 75%", annotation_font_color=STATUS["good"], annotation_position="top right")
    fig_ops.update_layout(title="On-Time Delivery Rate by Fulfillment Mode", xaxis_title=None,
                           yaxis_title="On-Time Rate (%)", yaxis=dict(range=[0, 118]), bargap=0.38, showlegend=False)
    finalize(fig_ops, height=340)
    ops_legend = status_legend((STATUS["critical"], "Below 50%"), (STATUS["warning"], "50–75%"), (STATUS["good"], "75%+"))

    # --- Complaint rate: exactly 2 states, both genuinely good/bad -> canonical status use.
    complaint = dff.groupby("On_Time_Flag")["Complaint_Flag"].mean() * 100
    complaint_df = pd.DataFrame({
        "Delivery": ["✓ On Time", "✕ Late"],
        "Complaint_Rate": [complaint.get(True, 0), complaint.get(False, 0)],
    })
    complaint_df["Label"] = complaint_df["Complaint_Rate"].apply(lambda v: f"{v:.1f}%")
    fig_complaint = px.bar(complaint_df, x="Delivery", y="Complaint_Rate", title="Complaint Rate: On-Time vs Late",
                            color="Delivery", color_discrete_map={"✓ On Time": STATUS["good"], "✕ Late": STATUS["critical"]},
                            text="Label")
    fig_complaint.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover("Delivery"))
    style_bars(fig_complaint)
    fig_complaint.update_layout(xaxis_title=None, yaxis_title="Complaint Rate (%)", showlegend=False,
                                 yaxis=dict(range=[0, complaint_df["Complaint_Rate"].max() * 1.3]))
    finalize(fig_complaint, height=340)

    # --- Return rate by category: nominal magnitude -> flat violet (friction-family, distinct
    # from the reserved status-red so it never impersonates a status chip).
    ret = (dff.groupby("Category", observed=True)["Return_Flag"].mean().reindex(CATEGORY_ORDER).dropna() * 100
           ).sort_values().reset_index(name="Return_Rate")
    ret["Label"] = ret["Return_Rate"].apply(lambda v: f"{v:.1f}%")
    fig_ret = px.bar(ret, x="Return_Rate", y="Category", orientation="h", title="Return Rate by Category",
                      color_discrete_sequence=[C_FRICTION], text="Label")
    fig_ret.update_traces(textposition="outside", textfont_color=INK["secondary"], hovertemplate=pct_hover_h("Category"))
    style_bars(fig_ret, horizontal=True)
    fig_ret.update_layout(xaxis_title="Return Rate (%)", yaxis_title=None, margin=dict(l=170, r=60),
                           xaxis=dict(range=[0, ret["Return_Rate"].max() * 1.3]))
    finalize(fig_ret, height=320)

    # --- Delivery delay distribution: single continuous series -> flat orange (friction/cost family).
    fig_delay = px.histogram(dff.dropna(subset=["Delivery_Delay_Days"]), x="Delivery_Delay_Days", nbins=30,
                              title="Delivery Delay Distribution (days)", color_discrete_sequence=[C_COST])
    fig_delay.update_traces(marker=dict(cornerradius=2), hovertemplate="<b>%{y:,}</b> orders<br>~%{x:.1f} days late<extra></extra>")
    fig_delay.update_layout(xaxis_title="Delay (days)", yaxis_title="Orders", bargap=0.08, showlegend=False)
    finalize(fig_delay, height=320)

    cards = dbc.Row([
        dbc.Col(stat_card("On-Time Rate", f"{dff['On_Time_Flag'].mean() * 100:.1f}%",
                           rate_status(dff['On_Time_Flag'].mean() * 100, 75, 50, lower_is_better=False)), md=3),
        dbc.Col(stat_card("Return Rate", f"{dff['Return_Flag'].mean() * 100:.1f}%",
                           rate_status(dff['Return_Flag'].mean() * 100, 5, 10)), md=3),
        dbc.Col(stat_card("Cancellation Rate", f"{dff['Cancellation_Flag'].mean() * 100:.1f}%",
                           rate_status(dff['Cancellation_Flag'].mean() * 100, 2, 5)), md=3),
        dbc.Col(stat_card("Complaint Rate", f"{dff['Complaint_Flag'].mean() * 100:.1f}%",
                           rate_status(dff['Complaint_Flag'].mean() * 100, 5, 10)), md=3),
    ], className="g-3 mb-3")

    ops_tbl = table_view(
        ops.round(1), ["Fulfillment_Mode", "Orders", "On_Time_Rate", "Avg_Rating"],
        "Fulfillment performance (filtered selection)",
    )

    return html.Div([
        cards,
        dbc.Row([dbc.Col([dcc.Graph(figure=fig_ops, config={"displayModeBar": False}), ops_legend], md=6),
                 dbc.Col(dcc.Graph(figure=fig_complaint, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_ret, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_delay, config={"displayModeBar": False}), md=6)],
                className="g-3 mt-1"),
        ops_tbl,
    ])


RENDERERS = {
    "overview": render_overview,
    "profitability": render_profitability,
    "customers": render_customers,
    "operations": render_operations,
}

# --------------------------------------------------------------------------- app

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="AuroraCart Diagnostic Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server  # exposed for gunicorn: `gunicorn dashboard:server`

filter_bar = dbc.Row(
    [
        dbc.Col([
            html.Label("Date Range", className="filter-label"),
            dcc.DatePickerRange(
                id="date-range", min_date_allowed=MIN_DATE, max_date_allowed=MAX_DATE,
                start_date=MIN_DATE, end_date=MAX_DATE, display_format="MMM YYYY",
                className="filter-control",
            ),
        ], md=3),
        dbc.Col([
            html.Label("Region", className="filter-label"),
            dcc.Dropdown(id="region-filter", options=REGION_ORDER, multi=True, placeholder="All regions"),
        ], md=2),
        dbc.Col([
            html.Label("Category", className="filter-label"),
            dcc.Dropdown(id="category-filter", options=CATEGORY_ORDER, multi=True, placeholder="All categories"),
        ], md=2),
        dbc.Col([
            html.Label("Customer Segment", className="filter-label"),
            dcc.Dropdown(id="segment-filter", options=SEGMENT_ORDER, multi=True, placeholder="All segments"),
        ], md=2),
        dbc.Col([
            html.Label("Fulfillment Mode", className="filter-label"),
            dcc.Dropdown(id="fulfillment-filter", options=FULFILLMENT_ORDER, multi=True, placeholder="All modes"),
        ], md=2),
        dbc.Col([
            html.Label(" ", className="filter-label"),
            dbc.Button("Reset", id="reset-btn", color="light", className="w-100 reset-btn"),
        ], md=1),
    ],
    className="g-2 filter-bar",
)

app.layout = dbc.Container(
    [
        html.Div(
            [
                html.Div("AC", className="brand-mark"),
                html.Div([
                    html.H1("AuroraCart at a Crossroads", className="page-title"),
                    html.P("Revenue is growing — is value? A profitability & operations diagnostic, "
                           "Jan 2023 – Dec 2025.", className="page-subtitle"),
                ]),
            ],
            className="header",
        ),
        filter_bar,
        dcc.Tabs(
            id="tabs", value="overview", className="app-tabs",
            children=[
                dcc.Tab(label="Executive Overview", value="overview"),
                dcc.Tab(label="Profitability Deep-Dive", value="profitability"),
                dcc.Tab(label="Customers", value="customers"),
                dcc.Tab(label="Operations & Delivery", value="operations"),
            ],
        ),
        dcc.Loading(html.Div(id="tab-content", className="tab-content"), type="circle", color=CATEGORICAL[0]),
        html.Footer(
            "Synthetic case-study dataset (AuroraCart at a Crossroads). "
            "Cancelled orders are excluded from revenue/margin figures; returns are not "
            "netted out of Net_Revenue. See the EDA notebook and README for full methodology and limitations.",
            className="footer",
        ),
    ],
    fluid=True,
    className="app-container",
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
)
def update_tab(tab, start_date, end_date, regions, categories, segments, fulfillment):
    dff = apply_filters(DF, start_date, end_date, regions, categories, segments, fulfillment)
    return RENDERERS[tab](dff)


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


if __name__ == "__main__":
    app.run(debug=True)
