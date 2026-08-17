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

DIVERGING_BLUE_RED = [
    [0.0, "#0d366b"], [0.25, "#3987e5"], [0.5, "#f0efec"], [0.75, "#eb8483"], [1.0, "#8a2323"],
]

STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7"}
SURFACE = "#fcfcfb"

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
