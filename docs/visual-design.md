# Visual design — how every chart here was built

The case brief (§17) judges a visualization by "how accurately and efficiently it
communicates the intended comparison", and warns that an attractive chart is not
automatically a useful one. This is the record of the construction rules the
dashboard and the deck both follow, and of the checks that were actually run
rather than eyeballed.

The procedure is: **pick the form from the data's job → assign colour by the job
the colour does → validate the palette with a script → apply mark specs → add the
interaction layer → accessibility pass → render it and look at it.** Colour comes
last, deliberately.

---

## 1. Form follows the job

| The chart's job | Form used | Where |
|---|---|---|
| Magnitude on a nominal axis | Horizontal bar, sorted, value at tip | Revenue by category, driver ranking |
| Polarity around a baseline | Diverging-coloured bar with a zero rule | Margin by category |
| Change over time | Line with markers; area for a single revenue series | Monthly revenue, margin, on-time |
| Decomposition of a change | Waterfall | Margin mix-vs-rate |
| Composition of a total | Stacked horizontal bar with a break-even rule | Cost structure by category |
| Before/after on one measure | Dumbbell | Channel margin either side of Accelerate 2.0 |
| Two variables plus magnitude | Bubble scatter, direct-labelled | Discount depth vs margin by promotion |
| A single headline number | Stat tile, not a chart | The KPI strip |

Two forms were rejected on purpose. **A pie for category revenue share** — the
comparison is between close values, which a pie cannot support; it is a bar.
**A dual-axis revenue-and-margin chart** — the crossing point of two arbitrary
scales invents a relationship that is not in the data, so the deck's opening
chart is two stacked panels sharing one time axis instead.

---

## 2. Colour by job, not by taste

Five distinct colour jobs appear, and each has one rule:

| Job | Encoding | Example |
|---|---|---|
| **Categorical** (identity) | Fixed hue order, assigned in sequence, never cycled | Before/after series; Electronics vs rest |
| **Ordinal** (position in a sequence) | One hue, monotone lightness | Loyalty status New → Champion |
| **Sequential** (magnitude) | One hue, light → dark | Revenue-family fills |
| **Diverging** (polarity) | Two opposed hues + neutral midpoint | Margin crossing zero |
| **Status** (state) | Reserved tokens, always with an icon or label | On-time bands, complaint rate |

Semantic roles are held constant everywhere so hue itself carries meaning across
the whole system: **revenue reads blue, cost orange, profit green, friction
violet** — never reassigned per chart on looks. Colour follows the entity, so
filtering a series out never repaints the survivors.

The rule broken most often in practice, and avoided here: **a value-ramp on
nominal categories**. Colouring bars darker-where-bigger on categories with no
natural order double-encodes bar length as hue and spends the identity channel
on information the chart already shows. Nominal categories get one flat hue;
only genuinely ordered ones (loyalty status) get a ramp.

---

## 3. The palette was validated, not eyeballed

The eight-slot categorical palette in
[`src/auroracart/viz_theme.py`](../src/auroracart/viz_theme.py) was run through
the palette validator against the light chart surface `#fcfcfb`:

```
Palette (light, surface #fcfcfb, categorical): 8 slots
  [PASS] Lightness band      all 8 inside L 0.43–0.77
  [PASS] Chroma floor        all 8 >= 0.1
  [PASS] CVD separation      worst adjacent #eda100↔#1baf7a ΔE 9.1 (protan)
  [PASS] Normal-vision floor worst adjacent #e87ba4↔#eda100 ΔE 19.6
  [WARN] Contrast vs surface below 3:1 for 3 slots — relief required
```

The contrast WARN is not dismissable; it obliges a relief channel. Every chart
here ships one: direct value labels on the marks, and a plain-table twin beneath
every chart group in the dashboard.

**Two hard failures the validator caught, and what changed:**

1. **The waterfall's green/red gain-loss pair** measured ΔE 4.1 under
   deuteranopia — effectively one colour for ~5% of male readers. Replaced with
   the diverging blue/red poles (ΔE 20.4 protan, 30.8 normal).
2. **The cost stack's pink segment next to its orange one** measured ΔE 12.9
   under *normal* vision, below the 15 floor — a pair full-colour readers
   struggle with, which secondary encoding does not excuse. Replaced with the
   palette's first four slots in fixed order (worst adjacent pair ΔE 22.9
   normal, 9.1 protan).

Both were invisible to inspection and would have shipped without the script.

---

## 4. Mark specifications, applied uniformly

Held constant so no chart free-hands its own: 4px rounded bar ends anchored to
the baseline, 2px lines, ≥8px markers with a 2px surface ring, a 2px surface gap
between stacked segments (the surface separates fills — never a drawn border),
recessive hairline gridlines one shade off the surface, and generous bar gaps.

Labelling is selective, not universal. A number on every point is chaos; the
labelled ones are the value at a bar tip, the endpoint of a line, and the
extreme. Everything else lives in the axis, the hover, and the table twin.

Dashes are reserved for meaning: a dashed vertical rule marks a dated
intervention (Accelerate 2.0, the logistics contract), a dashed horizontal rule
marks a threshold (break-even, the on-time target). Gridlines are never dashed.

Text wears text tokens — values, labels and legends stay in primary, secondary
or muted ink, and the coloured mark beside them carries the identity. Series
colour is never used for the text describing it.

Titles state the finding rather than naming the axes: *"Half of revenue sits in
the one category that loses money"*, not *"Margin by category"*. A reader who
sees only the slide still gets the point.

---

## 5. Interaction, and where it is *not* used

One filter row scopes every page — date range, region, category, segment,
fulfilment mode — never per-chart filters inside a card. Hover tooltips lead with
the value and carry the full label even when the axis had to shorten it.

Tooltips enhance and never gate: every value is also reachable from a direct
label or the table twin, which is what makes the dashboard usable with a keyboard
and on a phone where hover does not exist.

On touch devices Plotly's drag-to-pan is switched off entirely, so dragging a
chart scrolls the page instead of panning the axes — the single worst
Dash-on-mobile failure mode. The full layering is documented in
[responsive-design.md](responsive-design.md).

---

## 6. Accessibility pass

- **Identity is never colour-alone.** Two or more series always carry a legend;
  up to four are also direct-labelled. Status colours always ship with an icon or
  a caption chip, never hue by itself.
- **Every chart has a table twin.** Each dashboard page ends with a plain
  `DataTable` carrying the numbers behind the charts above it — the WCAG-clean
  equivalent, and on a phone the place where any truncated category label still
  appears in full.
- **Pinch-zoom stays enabled** (no `maximum-scale`), per WCAG 2.1 SC 1.4.4.
- **Tap targets are ≥44px**, verified across emulated phones and tablets.
- **The palette is fixed light-surface** and declares `color-scheme: light`, so
  Chrome for Android's auto-dark cannot re-render it into an unvalidated inverted
  palette the validator never saw.

---

## 7. Rendered and inspected

The validator checks colour, not layout. Every deck figure was rendered to PNG
and inspected for label collisions, clipped in-segment labels, legends landing on
titles, and notes running off the canvas — several of which were found and fixed
that way, including in-segment labels being squeezed into unreadable slivers on
the narrowest cost-stack segments (now suppressed below a width threshold, with
the value kept in the hover and the table).
