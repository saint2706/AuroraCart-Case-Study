"""Browser-environment detection and responsive figure adaptation.

The dashboard adapts on two independent layers, and the split matters:

* **CSS media queries** (``assets/style.css``) own everything the browser can
  decide on its own — grid stacking, type scale, tap-target sizing, scrollable
  tabs. These work with JavaScript disabled and never flash.
* **This module** owns everything the browser *can't* express in CSS because it
  lives inside a server-rendered Plotly figure: axis margins, tick-label
  truncation, title wrapping, drag/scroll behaviour on touch, table page size.

``assets/environment.js`` measures the real browser and pushes a profile dict
into the ``env-store``; :func:`profile_from_store` turns that dict into a
:class:`ViewProfile`, and the tab renderers ask the profile what to do. If
JavaScript never reports in, the profile falls back to :data:`DEFAULT_PROFILE`
(``known=False``) — a desktop-shaped view whose CSS layer still stacks correctly
on a phone, so the dashboard degrades rather than breaks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import plotly.graph_objects as go

from auroracart.viz_theme import INK

# Bootstrap 5 grid tiers, in the order the JS resolves them. Keep this table and
# the TIERS table in assets/environment.js identical — they are one contract.
TIERS: tuple[tuple[str, int], ...] = (
    ("xxl", 1400),
    ("xl", 1200),
    ("lg", 992),
    ("md", 768),
    ("sm", 576),
    ("xs", 0),
)

_TIER_NAMES = tuple(name for name, _ in TIERS)
_NARROW_TIERS = frozenset({"xs", "sm"})
_COMPACT_TIERS = frozenset({"xs", "sm", "md"})


def tier_for_width(width: int) -> str:
    """Resolve a viewport width in CSS pixels to a Bootstrap tier name."""
    for name, floor in TIERS:
        if width >= floor:
            return name
    return "xs"


@dataclass(frozen=True)
class ViewProfile:
    """What the server knows about the browser currently looking at the page.

    Every field has a defensible default so a missing, partial or hostile
    payload can never raise — the store is populated by client-side JavaScript,
    which means it is untrusted input like any other request body.
    """

    tier: str = "lg"
    width: int = 1440
    height: int = 900
    orientation: str = "landscape"
    touch: bool = False
    coarse: bool = False
    hover: bool = True
    dpr: float = 1.0
    reduced_motion: bool = False
    platform: str = "unknown"   # ios | android | mac | windows | linux | unknown
    browser: str = "unknown"    # chrome | safari | firefox | edge | opera | samsung
    engine: str = "unknown"     # blink | webkit | gecko
    standalone: bool = False
    supports: dict[str, bool] = field(default_factory=dict)
    known: bool = False         # True once the browser has actually reported in

    # ---------------------------------------------------------------- shape

    @property
    def is_narrow(self) -> bool:
        """Phone-width: one chart per row, truncated tick labels, tight margins."""
        return self.tier in _NARROW_TIERS

    @property
    def is_compact(self) -> bool:
        """Phone or tablet: charts still go full-width, chrome still shrinks."""
        return self.tier in _COMPACT_TIERS

    @property
    def is_phone(self) -> bool:
        return self.tier == "xs" or (self.tier == "sm" and self.coarse)

    @property
    def is_touch_primary(self) -> bool:
        """No usable hover — so nothing may be gated behind a hover interaction."""
        return self.coarse or (self.touch and not self.hover)

    # ------------------------------------------------------------- controls

    @property
    def table_page_size(self) -> int:
        return 5 if self.is_narrow else 10

    @property
    def date_months_shown(self) -> int:
        return 1 if self.is_compact else 2

    @property
    def chart_columns(self) -> int:
        return 1 if self.is_compact else 2

    def chart_height(self, base: int) -> int:
        """Chart height for this viewport.

        On a phone each chart owns the full width, so it can afford to be a
        little shorter than the desktop two-up tile; on a landscape phone the
        viewport itself is short, so shrink harder and let the page scroll less.
        """
        if self.tier == "xs":
            return max(250, base - (60 if self.orientation == "landscape" else 20))
        if self.tier == "sm":
            return max(260, base - 10)
        return base

    # ------------------------------------------------------------- helpers

    def describe(self) -> str:
        """One-line, human-readable summary — shown in the footer diagnostics."""
        if not self.known:
            return "viewport: not reported (using CSS breakpoints only)"
        pointer = "touch" if self.is_touch_primary else "mouse"
        return (
            f"viewport: {self.width}×{self.height} · {self.tier} · {self.orientation} · "
            f"{pointer} · {self.browser}/{self.engine} on {self.platform}"
        )


DEFAULT_PROFILE = ViewProfile()


def _as_bool(value: Any, default: bool = False) -> bool:
    return bool(value) if isinstance(value, (bool, int, float)) else default


def _as_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(float(value))))
    except (TypeError, ValueError):
        return default


def _as_choice(value: Any, allowed: tuple[str, ...] | frozenset[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def profile_from_store(data: Any) -> ViewProfile:
    """Build a :class:`ViewProfile` from whatever the client-side store holds.

    Anything unrecognised falls back to the corresponding default field, so a
    stale, truncated or tampered payload degrades to the desktop profile instead
    of raising inside a callback.
    """
    if not isinstance(data, dict):
        return DEFAULT_PROFILE

    width = _as_int(data.get("width"), DEFAULT_PROFILE.width, 240, 8000)
    height = _as_int(data.get("height"), DEFAULT_PROFILE.height, 240, 8000)
    # Trust the measured width over a self-reported tier: they can only disagree
    # if the JS table has drifted from TIERS above, and the width is the truth.
    tier = tier_for_width(width)

    supports = data.get("supports")
    supports = {str(k): bool(v) for k, v in supports.items()} if isinstance(supports, dict) else {}

    return ViewProfile(
        tier=tier,
        width=width,
        height=height,
        orientation=_as_choice(data.get("orientation"), ("portrait", "landscape"),
                               "portrait" if height >= width else "landscape"),
        touch=_as_bool(data.get("touch")),
        coarse=_as_bool(data.get("coarse")),
        hover=_as_bool(data.get("hover"), default=True),
        dpr=max(0.5, min(6.0, float(data.get("dpr") or 1.0))) if _is_number(data.get("dpr")) else 1.0,
        reduced_motion=_as_bool(data.get("reduced_motion")),
        platform=_as_choice(data.get("platform"),
                            ("ios", "android", "mac", "windows", "linux", "unknown"), "unknown"),
        browser=_as_choice(data.get("browser"),
                           ("chrome", "safari", "firefox", "edge", "opera", "samsung", "unknown"),
                           "unknown"),
        engine=_as_choice(data.get("engine"), ("blink", "webkit", "gecko", "unknown"), "unknown"),
        standalone=_as_bool(data.get("standalone")),
        supports=supports,
        known=True,
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# --------------------------------------------------------------------- figures

# Desktop margins are set per-chart in dashboard.py (some need 170px of room for
# category labels). On a 360px-wide phone that would leave the plot ~190px, so
# narrow viewports drop to a small fixed margin and let Plotly's `automargin`
# grow it back only as far as the (truncated) tick labels actually need.
_NARROW_MARGIN = dict(l=6, r=26, t=54, b=38)
_NARROW_TITLE_WRAP = 30
_NARROW_TICK_CHARS = 14      # horizontal bars: truncate the category axis
_NARROW_TICK_WRAP = 10       # vertical bars: wrap the category axis onto 2 lines


def _wrap_title(text: str, width: int) -> str:
    """Insert <br> at word boundaries so a long title wraps instead of clipping."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "<br>".join(lines)


def _truncate(label: str, limit: int) -> str:
    return label if len(label) <= limit else label[: limit - 1].rstrip() + "…"


def _title_text(fig: go.Figure) -> str | None:
    title = fig.layout.title.text if fig.layout.title else None
    return title if isinstance(title, str) and title else None


def responsive_figure(fig: go.Figure, view: ViewProfile, base_height: int | None = None) -> go.Figure:
    """Re-fit a finished figure to the reported viewport. Mutates and returns it.

    Called once per chart, immediately before it is handed to ``dcc.Graph`` —
    every chart keeps its desktop definition in one place and this is the only
    thing that knows about small screens.
    """
    height = view.chart_height(base_height if base_height is not None else (fig.layout.height or 340))

    # Touch devices: a drag inside the plot must scroll the page, not pan the
    # axes. Without this a chart becomes a scroll trap the user has to swipe
    # around, which is the single worst mobile failure mode for Plotly.
    if view.is_touch_primary:
        fig.update_layout(dragmode=False)
        fig.update_layout(hoverlabel=dict(font=dict(size=13)))

    # `automargin` is safe at every width and is what keeps rotated or long tick
    # labels from being clipped on narrow screens.
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)

    if not view.is_narrow:
        fig.update_layout(height=height)
        return fig

    title = _title_text(fig)
    wrapped = _wrap_title(title, _NARROW_TITLE_WRAP) if title else None
    title_lines = wrapped.count("<br>") + 1 if wrapped else 1

    margin = dict(_NARROW_MARGIN)
    margin["t"] = 44 + 18 * title_lines
    height += 18 * (title_lines - 1)

    if wrapped:
        fig.update_layout(title=dict(text=wrapped, font=dict(size=14)))

    fig.update_layout(
        height=height,
        margin=margin,
        font=dict(size=11),
        xaxis=dict(tickfont=dict(size=10), title_font=dict(size=11)),
        yaxis=dict(tickfont=dict(size=10), title_font=dict(size=11)),
        # A horizontal legend above the plot wraps instead of stealing plot width.
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=10)),
    )

    # Value-at-tip labels stay (they are the accessible read of the bar) but
    # shrink so they don't collide at phone width.
    fig.update_traces(textfont=dict(size=10), selector=dict(type="bar"))
    fig.update_traces(textfont=dict(size=10), selector=dict(type="scatter"))

    for annotation in fig.layout.annotations:
        current = annotation.font.size or 12
        annotation.font.size = min(current, 10)

    _fit_category_ticks(fig)
    _pad_outside_labels(fig)
    return fig


def _pad_outside_labels(fig: go.Figure) -> None:
    """Give value-at-tip bar labels room to render at phone width.

    Each chart sizes its value axis with ~20-30% headroom for its outside
    labels, which is proportional and so holds at any width. What does not hold
    is the *pixel* width of the label itself: at 300px the same 22% of a much
    smaller data area no longer covers "₹66.2M", and `automargin` does not help
    because it accounts for tick labels, not trace text. So widen the headroom.
    """
    for horizontal in (True, False):
        has_outside = any(
            trace.type == "bar"
            and (getattr(trace, "orientation", None) == "h") == horizontal
            and trace.textposition == "outside"
            for trace in fig.data
        )
        if not has_outside:
            continue
        axis = fig.layout.xaxis if horizontal else fig.layout.yaxis
        bounds = axis.range
        if not bounds or bounds[1] is None or bounds[0] is None:
            continue
        low, high = float(bounds[0]), float(bounds[1])
        axis.range = [low, high + (high - low) * 0.12]


def _wrap_tick(label: str, width: int, max_lines: int = 2) -> str:
    """Break a category label across at most `max_lines` lines at word boundaries."""
    lines = _wrap_title(label, width).split("<br>")
    if len(lines) <= max_lines:
        return "<br>".join(lines)
    head, tail = lines[: max_lines - 1], " ".join(lines[max_lines - 1:])
    return "<br>".join(head + [_truncate(tail, width + 4)])


def _bar_categories(fig: go.Figure, horizontal: bool) -> list[str]:
    """Distinct string category values across every bar trace of one orientation."""
    categories: list[str] = []
    for trace in fig.data:
        if trace.type != "bar":
            continue
        is_h = getattr(trace, "orientation", None) == "h"
        if is_h != horizontal:
            continue
        # `trace.x`/`trace.y` come back as numpy arrays, so test against None
        # explicitly — an array has no unambiguous truth value.
        values = trace.y if horizontal else trace.x
        if values is None:
            continue
        for value in values:
            if isinstance(value, str) and value not in categories:
                categories.append(value)
    return categories


def _fit_category_ticks(fig: go.Figure) -> None:
    """Make long category labels fit a phone-width plot.

    Horizontal bars get truncated labels (the axis is the left margin, and every
    character there is stolen from the bars). Vertical bars get wrapped labels
    instead — upright text over two lines reads far better on a touch screen
    than rotated text, and costs only height, which a scrolling page has.

    Only the axis *display* changes: hovertemplates and the plain-table twin
    beneath every chart still carry the full category name.
    """
    horizontal = _bar_categories(fig, horizontal=True)
    if horizontal and any(len(c) > _NARROW_TICK_CHARS for c in horizontal):
        fig.update_yaxes(
            tickmode="array",
            tickvals=horizontal,
            ticktext=[_truncate(c, _NARROW_TICK_CHARS) for c in horizontal],
            tickfont=dict(size=10, color=INK["secondary"]),
        )

    vertical = _bar_categories(fig, horizontal=False)
    if vertical and any(len(c) > _NARROW_TICK_WRAP for c in vertical):
        fig.update_xaxes(
            tickmode="array",
            tickvals=vertical,
            ticktext=[_wrap_tick(c, _NARROW_TICK_WRAP) for c in vertical],
            tickfont=dict(size=10, color=INK["secondary"]),
        )


def graph_config(view: ViewProfile) -> dict[str, Any]:
    """Plotly config tuned for the pointer type actually in use."""
    config: dict[str, Any] = {
        "displayModeBar": False,
        "displaylogo": False,
        "responsive": True,
        "showTips": False,
        # Never hijack the page's scroll gesture, on any device.
        "scrollZoom": False,
    }
    if view.is_touch_primary:
        # Double-tap is the browser's zoom gesture on touch; leave it alone.
        config["doubleClick"] = False
    return config


# Bootstrap column spec for a two-up chart row. Charts stay full-width right up
# to `lg` — a 380px-wide chart on a tablet is worse than a full-width one.
CHART_COL = {"xs": 12, "lg": 6}

__all__ = [
    "CHART_COL",
    "TIERS",
    "ViewProfile",
    "DEFAULT_PROFILE",
    "graph_config",
    "profile_from_store",
    "responsive_figure",
    "tier_for_width",
]
