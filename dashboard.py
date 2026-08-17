"""AuroraCart at a Crossroads — interactive profitability & operations dashboard.

Run locally:      python dashboard.py            (http://127.0.0.1:8050)
Run for prod:      gunicorn dashboard:server

Layout: a global filter bar (date range, region, category, segment, fulfillment
mode) drives four tabs — Executive Overview, Profitability Deep-Dive, Customers,
and Operations & Delivery — each answering a different slice of "what should
AuroraCart do next, and what evidence supports it."
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
from viz_theme import CATEGORICAL, INK, SEQUENTIAL_BLUE, STATUS, SURFACE, finalize

# --------------------------------------------------------------------------- data
DF = load_data()
MIN_DATE = DF["Order_Date"].min()
MAX_DATE = DF["Order_Date"].max()

# --------------------------------------------------------------------------- helpers


def format_inr(value: float) -> str:
    if pd.isna(value):
        return "—"
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:,.2f} L"
    return f"₹{value:,.0f}"


def stat_card(label: str, value: str, accent: str = CATEGORICAL[0], sub: str | None = None) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="stat-label"),
                html.Div(value, className="stat-value"),
                html.Div(sub or " ", className="stat-sub"),
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
    """A plain data table beneath the charts, per the 'a table view exists' rule."""
    return html.Div(
        [
            html.Div(title, className="table-title"),
            dash_table.DataTable(
                data=df[columns].round(2).to_dict("records"),
                columns=[{"name": c.replace("_", " "), "id": c} for c in columns],
                style_table={"overflowX": "auto"},
                style_cell={"fontFamily": "system-ui, sans-serif", "fontSize": 13, "padding": "6px 10px",
                            "backgroundColor": SURFACE, "color": INK["primary"], "border": "none",
                            "borderBottom": f"1px solid {INK['grid']}"},
                style_header={"fontWeight": 600, "backgroundColor": SURFACE, "color": INK["secondary"],
                              "borderBottom": f"2px solid {INK['axis']}"},
                page_size=10,
            ),
        ],
        className="table-wrap",
    )


# --------------------------------------------------------------------------- tab renderers


def render_overview(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]
    revenue = valid["Net_Revenue"].sum()
    profit = valid["Profit"].sum()
    margin = (profit / revenue * 100) if revenue else float("nan")
    aov = (revenue / len(valid)) if len(valid) else float("nan")

    cards = dbc.Row(
        [
            dbc.Col(stat_card("Net Revenue", format_inr(revenue), CATEGORICAL[0]), md=2),
            dbc.Col(stat_card("Profit", format_inr(profit), CATEGORICAL[2]), md=2),
            dbc.Col(stat_card("Profit Margin", f"{margin:.1f}%",
                               STATUS["critical"] if margin < 10 else STATUS["good"]), md=2),
            dbc.Col(stat_card("Orders", f"{len(dff):,}", CATEGORICAL[3]), md=2),
            dbc.Col(stat_card("Avg Order Value", format_inr(aov), CATEGORICAL[4]), md=2),
            dbc.Col(stat_card("On-Time Delivery", f"{dff['On_Time_Flag'].mean() * 100:.1f}%",
                               STATUS["warning"]), md=2),
        ],
        className="g-3 mb-3",
    )

    monthly = (
        valid.groupby("Order_YearMonth")
        .agg(Net_Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Net_Revenue"] * 100)
        .reset_index()
    )

    fig_rev = px.area(monthly, x="Order_YearMonth", y="Net_Revenue", title="Monthly Net Revenue",
                       color_discrete_sequence=[CATEGORICAL[0]])
    fig_rev.update_traces(line=dict(width=2))
    fig_rev.update_layout(xaxis_title=None, yaxis_title="Net Revenue (₹)")
    finalize(fig_rev, height=320)

    fig_margin = px.line(monthly, x="Order_YearMonth", y="Margin_Pct", title="Monthly Profit Margin (%)",
                          markers=True, color_discrete_sequence=[STATUS["critical"]])
    fig_margin.add_hline(y=margin, line_dash="dot", line_color=INK["axis"],
                          annotation_text="period average", annotation_font_color=INK["muted"])
    fig_margin.update_layout(xaxis_title=None, yaxis_title="Margin (%)")
    finalize(fig_margin, height=320)

    cat_rev = (
        valid.groupby("Category", observed=True)["Net_Revenue"].sum().reindex(CATEGORY_ORDER).dropna()
        .sort_values()
    )
    fig_cat = px.bar(cat_rev.reset_index(), x="Net_Revenue", y="Category", orientation="h",
                      title="Revenue by Category", color_discrete_sequence=[CATEGORICAL[0]])
    fig_cat.update_layout(xaxis_title="Net Revenue (₹)", yaxis_title=None, margin=dict(l=160))
    finalize(fig_cat, height=320)

    reg_rev = valid.groupby("Region", observed=True)["Net_Revenue"].sum().reindex(REGION_ORDER).dropna()
    fig_reg = px.bar(reg_rev.reset_index(), x="Region", y="Net_Revenue", title="Revenue by Region",
                      color_discrete_sequence=[CATEGORICAL[1]])
    fig_reg.update_layout(xaxis_title=None, yaxis_title="Net Revenue (₹)")
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

    return html.Div([
        cards,
        story,
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_rev, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_margin, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_cat, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_reg, config={"displayModeBar": False}), md=6)], className="g-3 mt-1"),
    ])


def render_profitability(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()
    valid = dff[dff["Is_Valid_Revenue"]]

    cat = (
        valid.groupby("Category", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(CATEGORY_ORDER).dropna()
    )
    fig_cat = px.bar(cat.reset_index().sort_values("Margin_Pct"), x="Margin_Pct", y="Category", orientation="h",
                      title="Profit Margin by Category", color="Margin_Pct",
                      color_continuous_scale=[STATUS["critical"], INK["grid"], STATUS["good"]],
                      color_continuous_midpoint=0)
    fig_cat.add_vline(x=0, line_color=INK["axis"])
    fig_cat.update_layout(xaxis_title="Profit Margin (%)", yaxis_title=None, coloraxis_showscale=False,
                           margin=dict(l=160))
    finalize(fig_cat, height=340)

    promo = (
        valid.groupby("Promotion_Type", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"),
             Avg_Discount=("Discount_Percentage", "mean"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
        .reindex(PROMOTION_ORDER).dropna()
    )
    fig_promo = px.scatter(promo.reset_index(), x="Avg_Discount", y="Margin_Pct", size="Revenue",
                            text="Promotion_Type", color="Promotion_Type", color_discrete_sequence=CATEGORICAL,
                            title="Discount Depth vs Margin by Promotion")
    fig_promo.add_hline(y=0, line_dash="dot", line_color=INK["axis"])
    # Alternate label position per promotion so adjacent points (Category/Member Offer) don't collide.
    label_pos = {"No Promotion": "top center", "Category Offer": "top center", "Member Offer": "bottom center",
                 "Festival Sale": "top center", "Flash Deal": "top center"}
    for trace in fig_promo.data:
        trace.textposition = label_pos.get(trace.name, "top center")
    y_pad = (promo["Margin_Pct"].max() - promo["Margin_Pct"].min()) * 0.25
    fig_promo.update_layout(
        xaxis_title="Average Discount (%)", yaxis_title="Profit Margin (%)", showlegend=False,
        yaxis=dict(range=[promo["Margin_Pct"].min() - y_pad, promo["Margin_Pct"].max() + y_pad]),
    )
    finalize(fig_promo, height=340)

    seg = (
        valid.groupby("Customer_Segment", observed=True)
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100, AOV=lambda d: d["Revenue"] / d["Orders"])
        .reindex(SEGMENT_ORDER).dropna()
    )
    fig_seg = go.Figure()
    fig_seg.add_bar(x=seg.index, y=seg["AOV"], name="Avg Order Value (₹)", marker_color=CATEGORICAL[0])
    fig_seg.update_layout(title="Customer Segment — Average Order Value", xaxis_title=None,
                           yaxis_title="AOV (₹)", showlegend=False)
    finalize(fig_seg, height=320)

    fig_seg_margin = px.bar(seg.reset_index(), x="Customer_Segment", y="Margin_Pct",
                             title="Customer Segment — Profit Margin", color="Margin_Pct",
                             color_continuous_scale=SEQUENTIAL_BLUE)
    fig_seg_margin.update_layout(xaxis_title=None, yaxis_title="Margin (%)", coloraxis_showscale=False)
    finalize(fig_seg_margin, height=320)

    tbl = table_view(
        cat.reset_index().assign(Revenue=lambda d: d["Revenue"].round(0), Profit=lambda d: d["Profit"].round(0)),
        ["Category", "Revenue", "Profit", "Orders", "Margin_Pct"],
        "Category profitability (filtered selection)",
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

    nvr = (
        valid.groupby("New_vs_Returning")
        .agg(Revenue=("Net_Revenue", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "count"))
        .assign(Margin_Pct=lambda d: d["Profit"] / d["Revenue"] * 100)
    )
    fig_nvr = px.bar(nvr.reset_index(), x="New_vs_Returning", y="Margin_Pct", title="Margin: New vs Returning",
                      color="New_vs_Returning", color_discrete_sequence=[CATEGORICAL[3], CATEGORICAL[2]])
    fig_nvr.update_layout(xaxis_title=None, yaxis_title="Margin (%)", showlegend=False)
    finalize(fig_nvr, height=320)

    loyalty = valid.groupby("Loyalty_Status", observed=True)["Order_ID"].count().reindex(LOYALTY_ORDER).dropna()
    fig_loy = px.bar(loyalty.reset_index(name="Orders"), x="Loyalty_Status", y="Orders",
                      title="Orders by Loyalty Status", color_discrete_sequence=[CATEGORICAL[0]])
    fig_loy.update_layout(xaxis_title=None, yaxis_title="Orders")
    finalize(fig_loy, height=320)

    chan = (
        valid.groupby("Acquisition_Channel")
        .agg(Revenue=("Net_Revenue", "sum"), Marketing_Cost=("Marketing_Cost", "sum"))
        .assign(Marketing_Pct=lambda d: d["Marketing_Cost"] / d["Revenue"] * 100)
        .sort_values("Marketing_Pct", ascending=True)
    )
    fig_chan = px.bar(chan.reset_index(), x="Marketing_Pct", y="Acquisition_Channel", orientation="h",
                       title="Marketing Cost as % of Revenue, by Channel", color_discrete_sequence=[CATEGORICAL[1]])
    fig_chan.update_layout(xaxis_title="Marketing Cost / Revenue (%)", yaxis_title=None, margin=dict(l=150))
    finalize(fig_chan, height=340)

    fig_rating = px.histogram(valid.dropna(subset=["Customer_Rating"]), x="Customer_Rating", nbins=10,
                               title="Customer Rating Distribution", color_discrete_sequence=[CATEGORICAL[0]])
    fig_rating.update_layout(xaxis_title="Rating", yaxis_title="Orders", bargap=0.1)
    finalize(fig_rating, height=340)

    return html.Div([
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_nvr, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_loy, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_chan, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_rating, config={"displayModeBar": False}), md=6)],
                className="g-3 mt-1"),
    ])


def render_operations(dff: pd.DataFrame) -> html.Div:
    if dff.empty:
        return empty_state()

    ops = dff.groupby("Fulfillment_Mode", observed=True).agg(
        On_Time_Rate=("On_Time_Flag", "mean"), Orders=("Order_ID", "count"),
    ).assign(On_Time_Rate=lambda d: d["On_Time_Rate"] * 100).reindex(FULFILLMENT_ORDER).dropna()
    fig_ops = px.bar(ops.reset_index(), x="Fulfillment_Mode", y="On_Time_Rate",
                      title="On-Time Delivery Rate by Fulfillment Mode", color_discrete_sequence=[STATUS["warning"]])
    fig_ops.add_hline(y=100, line_dash="dot", line_color=INK["grid"])
    fig_ops.update_layout(xaxis_title=None, yaxis_title="On-Time Rate (%)", yaxis=dict(range=[0, 100]))
    finalize(fig_ops, height=320)

    complaint = dff.groupby("On_Time_Flag")["Complaint_Flag"].mean() * 100
    complaint_df = pd.DataFrame({
        "Delivery": ["On Time", "Late"],
        "Complaint_Rate": [complaint.get(True, 0), complaint.get(False, 0)],
    })
    fig_complaint = px.bar(complaint_df, x="Delivery", y="Complaint_Rate", title="Complaint Rate: On-Time vs Late",
                            color="Delivery", color_discrete_map={"On Time": STATUS["good"], "Late": STATUS["critical"]})
    fig_complaint.update_layout(xaxis_title=None, yaxis_title="Complaint Rate (%)", showlegend=False)
    finalize(fig_complaint, height=320)

    ret = dff.groupby("Category", observed=True)["Return_Flag"].mean().reindex(CATEGORY_ORDER).dropna() * 100
    fig_ret = px.bar(ret.reset_index(name="Return_Rate"), x="Return_Rate", y="Category", orientation="h",
                      title="Return Rate by Category", color_discrete_sequence=[CATEGORICAL[4]])
    fig_ret.update_layout(xaxis_title="Return Rate (%)", yaxis_title=None, margin=dict(l=160))
    finalize(fig_ret, height=320)

    fig_delay = px.histogram(dff.dropna(subset=["Delivery_Delay_Days"]), x="Delivery_Delay_Days", nbins=30,
                              title="Delivery Delay Distribution (days)", color_discrete_sequence=[CATEGORICAL[0]])
    fig_delay.update_layout(xaxis_title="Delay (days)", yaxis_title="Orders", bargap=0.05)
    finalize(fig_delay, height=320)

    cards = dbc.Row([
        dbc.Col(stat_card("On-Time Rate", f"{dff['On_Time_Flag'].mean() * 100:.1f}%", STATUS["warning"]), md=3),
        dbc.Col(stat_card("Return Rate", f"{dff['Return_Flag'].mean() * 100:.1f}%", CATEGORICAL[4]), md=3),
        dbc.Col(stat_card("Cancellation Rate", f"{dff['Cancellation_Flag'].mean() * 100:.1f}%", STATUS["critical"]), md=3),
        dbc.Col(stat_card("Complaint Rate", f"{dff['Complaint_Flag'].mean() * 100:.1f}%", STATUS["critical"]), md=3),
    ], className="g-3 mb-3")

    return html.Div([
        cards,
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_ops, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_complaint, config={"displayModeBar": False}), md=6)], className="g-3"),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_ret, config={"displayModeBar": False}), md=6),
                 dbc.Col(dcc.Graph(figure=fig_delay, config={"displayModeBar": False}), md=6)],
                className="g-3 mt-1"),
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
            html.Label(" ", className="filter-label"),
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
