# Phones, tablets and browsers

The dashboard is built to be used on a phone, not merely to survive on one. It
was verified end-to-end on emulated iPhone SE / 14 Pro, Pixel 7, Galaxy S9+,
iPad Mini (portrait and landscape), a 320px-wide viewport, and desktop, every
tab on each, with no horizontal page scroll, no clipped chart text, and no tap
target under 44px.

Adaptation happens in three layers, which is worth knowing before changing any
of it:

1. **CSS media queries** (`src/auroracart/assets/style.css`) own the page
   layout: grid stacking, type scale, tap targets, the collapsible filter panel.
   This layer works with JavaScript disabled.
2. **Browser detection** (`src/auroracart/assets/environment.js`) measures what a
   media query cannot express (pointer type, browser engine, `dvh`/`clamp`/
   safe-area support, standalone home-screen mode), stamps it on `<html>` as
   `env-*` classes, then reports it into a `dcc.Store`.
3. **Figure adaptation** (`src/auroracart/responsive.py`) consumes that report
   for the things locked inside a server-rendered Plotly figure: axis margins,
   tick-label truncation and wrapping, title wrapping, histogram bin counts, and
   table page size.

What that buys on a small screen:

- Charts go one-up below `lg`; category labels are truncated (horizontal bars)
  or wrapped over two lines (vertical bars), with the full text always present
  in the hover and in the plain-table twin beneath.
- **Dragging a chart scrolls the page** instead of panning the axes. Plotly's
  drag mode is switched off wherever the primary pointer is coarse, because
  axis-panning on touch is the single worst Dash-on-mobile failure mode.
- The date picker drops to a one-month, full-screen calendar; a two-month
  inline calendar is ~600px wide and gets clipped by any phone viewport.
- Filters collapse behind a toggle that reports how many are active, so a
  collapsed panel never hides a live filter.
- The five-tab strip scrolls horizontally from `sm` up and stacks into
  full-width rows below it, so no tab label is ever ellipsed.
- Tables that really are wider than their box say so and scroll in place.
- Pinch-zoom is deliberately left enabled (no `maximum-scale`), per WCAG 2.1
  SC 1.4.4.

Detection is progressive enhancement throughout: if the JavaScript never reports
in, `responsive.py` falls back to a desktop profile and the CSS layer still lays
the page out correctly. The footer prints what was actually detected, which is
the first thing to check if a layout looks wrong on an unfamiliar device.
