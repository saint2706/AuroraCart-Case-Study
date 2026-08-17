"""Shared Plotly theme for the AuroraCart notebook + dashboard.

A single validated palette (see the dataviz skill's palette reference) is defined
once here so every chart in both artifacts reads as one visual system.
"""

import plotly.graph_objects as go
import plotly.io as pio

# Fixed-order categorical palette (colorblind-validated). Assign by entity identity,
# never by rank, and never cycle past what's needed.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Low (negative/loss) -> red, high (positive/profit) -> blue: with color_continuous_midpoint=0,
# Plotly maps values below the midpoint to the scale's low end and above it to the high end, so
# the stop order below is what actually determines which pole reads as "bad" vs "good" — red must
# sit at 0.0, blue at 1.0, or a profitable category renders red and a loss-making one renders blue.
DIVERGING_BLUE_RED = [
    [0.0, "#8a2323"], [0.25, "#eb8483"], [0.5, "#f0efec"], [0.75, "#3987e5"], [1.0, "#0d366b"],
]

# 4-step ordinal ramp (New -> Champion): monotone lightness, light end still clears 2:1 on the
# light surface (step 250), for encoding a genuinely ORDERED category — never use this on a
# nominal one (that's the "value-ramp on nominal categories" anti-pattern; nominal = flat slot-1).
ORDINAL_BLUE_4 = ["#86b6ef", "#5598e7", "#2a78d6", "#184f95"]

STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7"}
SURFACE = "#fcfcfb"

# Fixed mark specs (marks-and-anatomy.md) applied uniformly so no chart free-hands its own.
BAR_CORNER_RADIUS = 4
LINE_WIDTH = 2
MARKER_SIZE = 9
MARKER_RING = dict(width=2, color=SURFACE)
BARGAP = 0.38

FONT_FAMILY = "system-ui, -apple-system, Segoe UI, sans-serif"

_template = go.layout.Template()
_template.layout = go.Layout(
    colorway=CATEGORICAL,
    font=dict(family=FONT_FAMILY, color=INK["primary"], size=13),
    title=dict(font=dict(size=17, color=INK["primary"]), x=0.02, xanchor="left"),
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    xaxis=dict(
        gridcolor=INK["grid"], zerolinecolor=INK["axis"], linecolor=INK["axis"],
        tickfont=dict(color=INK["muted"]), title_font=dict(color=INK["secondary"]),
    ),
    yaxis=dict(
        gridcolor=INK["grid"], zerolinecolor=INK["axis"], linecolor=INK["axis"],
        tickfont=dict(color=INK["muted"]), title_font=dict(color=INK["secondary"]),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK["secondary"])),
    margin=dict(l=60, r=30, t=60, b=50),
    hoverlabel=dict(bgcolor=SURFACE, font=dict(family=FONT_FAMILY, color=INK["primary"])),
)
pio.templates["auroracart"] = _template
pio.templates.default = "auroracart"


def finalize(fig: go.Figure, height: int = 420) -> go.Figure:
    """Apply consistent sizing/legend placement. Call on every chart before display."""
    fig.update_layout(
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def style_bars(fig: go.Figure, horizontal: bool = False) -> go.Figure:
    """Apply the fixed bar mark spec: 4px rounded data-ends, capped thickness, breathing room."""
    fig.update_traces(marker=dict(cornerradius=BAR_CORNER_RADIUS), selector=dict(type="bar"))
    fig.update_layout(bargap=BARGAP, bargroupgap=0.12)
    axis = fig.update_yaxes if horizontal else fig.update_xaxes
    axis(showgrid=False)  # the category axis never needs gridlines; only the value axis does
    return fig


def style_line(fig: go.Figure, with_markers: bool = True) -> go.Figure:
    """Apply the fixed line/marker mark spec: 2px round-joined line, >=8px ringed markers."""
    marker = dict(size=MARKER_SIZE, line=MARKER_RING) if with_markers else dict(size=0)
    fig.update_traces(
        line=dict(width=LINE_WIDTH, shape="linear"),
        marker=marker,
        selector=dict(type="scatter"),
    )
    return fig


def wash_area(fig: go.Figure, hex_color: str) -> go.Figure:
    """Area fill as a ~10% wash with a solid 2px line on top, never a saturated block."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    fig.update_traces(
        line=dict(width=LINE_WIDTH, color=hex_color),
        fillcolor=f"rgba({r},{g},{b},0.12)",
        selector=dict(type="scatter"),
    )
    return fig


def money_hover(name: str, extra: str = "") -> str:
    return f"<b>₹%{{y:,.0f}}</b><br>{name}: %{{x}}{extra}<extra></extra>"


def money_hover_h(name: str, extra: str = "") -> str:
    return f"<b>₹%{{x:,.0f}}</b><br>{name}: %{{y}}{extra}<extra></extra>"


def pct_hover(name: str, extra: str = "") -> str:
    return f"<b>%{{y:.1f}}%</b><br>{name}: %{{x}}{extra}<extra></extra>"


def pct_hover_h(name: str, extra: str = "") -> str:
    return f"<b>%{{x:.1f}}%</b><br>{name}: %{{y}}{extra}<extra></extra>"
