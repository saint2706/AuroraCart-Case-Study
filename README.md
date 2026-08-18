# AuroraCart at a Crossroads

**From dashboard to decision.** A profitability and operations diagnostic for the
*Storytelling Using Data Visualization* case study: an EDA notebook, a five-page
interactive Dash dashboard in a dark theme, and a decision-oriented executive
story.

The board asked how AuroraCart should allocate growth investment over the next
twelve months. This repository answers that question, shows the evidence, and
says what the evidence cannot support.

---

## The answer in one paragraph

Revenue nearly doubled between 2023 and 2025 (₹29.3M to ₹58.0M) while margin fell
from 12.4% to 7.1%. **Ninety-two percent of that decline is margin erosion inside
categories AuroraCart already sold, not a shift in what it sells.** It is
concentrated almost entirely in Electronics, which is half of revenue at −4.9%
margin because merchandise alone costs 94% of what those orders recognise.
Meanwhile one company-wide discount policy is being applied to two businesses
with completely different tolerance for it: Electronics turns loss-making above
a 10% discount, while the rest of the business still earns double digits at 25%
off. The delivery function everyone assumed was broken is the one thing that
measurably improved.

Three actions follow, in priority order. They are in
**[docs/recommendations.md](docs/recommendations.md)**.

---

## Start here

| If you want… | Go to |
| --- | --- |
| The 10-minute story | [`deliverables/AuroraCart_Executive_Story.pptx`](deliverables/): 17 dark slides, timed speaker notes |
| The interactive dashboard | `python app.py` → <http://127.0.0.1:8050> ([deploy it](docs/deployment.md)) |
| The three recommendations | [docs/recommendations.md](docs/recommendations.md) |
| The five mandatory questions | [docs/mandatory-questions.md](docs/mandatory-questions.md) |
| How the numbers were defined | [docs/methodology.md](docs/methodology.md) |
| Coverage against the assignment | [docs/case-brief.md](docs/case-brief.md) |
| The full analysis, worked | [`notebooks/AuroraCart_EDA.ipynb`](notebooks/AuroraCart_EDA.ipynb), pre-executed |

---

## Repository layout

```text
.
├── app.py                     WSGI entrypoint: `gunicorn app:server`, `python app.py`
├── pyproject.toml             Package metadata; the dependency source of truth
├── render.yaml, Procfile      Free-tier deployment config
│
├── data/raw/                  The case dataset, as supplied
├── notebooks/                 The EDA: data-quality audit through to findings
│
├── src/auroracart/
│   ├── paths.py               Every filesystem location, resolved once
│   ├── data_prep.py           The one cleaning + feature-engineering pipeline
│   ├── analysis.py            Case-question metrics: drivers, event windows, decompositions
│   ├── viz_theme.py           Shared dark Plotly palette and mark specs
│   ├── responsive.py          Browser profile → figure adaptation
│   ├── dashboard.py           Deliverable A: the five-page Dash app
│   └── assets/                CSS + JS the dashboard auto-loads
│
├── tools/
│   ├── build_figures.py       Renders the deck's charts to PNG
│   └── build_deck.py          Builds the .pptx from those charts and computed facts
│
├── deliverables/              Deliverable B: the deck and its figures
├── docs/                      The written deliverables (see the table above)
└── tests/                     Cleaning contract, metrics, every dashboard tab
```

**The thing worth knowing about the structure:** the notebook, the dashboard,
the deck and the docs all import from `src/auroracart/`. A number quoted on a
slide is computed by the same function the dashboard draws and the notebook
printed, so the three artifacts cannot drift apart. `tools/build_deck.py` does
not contain a single typed-in figure; it reads `analysis.headline_facts()`.

---

## The evidence behind the answer

**Context.** ₹130.8M net revenue and ₹11.6M contribution across 14,970 orders and
6,778 customers, January 2023 to December 2025. Revenue grew 98%; margin went
12.4% → 8.9% → 7.1%.

**Tension.** Accelerate 2.0 (July 2024) grew revenue per month by 77% and
contribution per month by 14%. Average discount went 11.0% → 14.9%.

**Evidence, drilled down:**

1. **The decline is rate erosion, not mix.** Holding the 2023 category mix
   constant, 2025 margin would still be 7.6%. Mix explains −0.4 points of a −5.3
   point fall; within-category erosion explains −4.7.
2. **Electronics is the whole story.** 50.6% of revenue at −4.9% margin;
   Smartphones alone are 31.2% of company revenue at −9.1%, losing ₹3.70M.
   Merchandise cost is 94.1% of net revenue there, against 54-67% elsewhere.
   Discount depth is within 0.3 points across all five categories, so this is a
   cost problem, not a promotion problem.
3. **Discount tolerance is category-specific.** Electronics crosses into loss
   between a 10% and 15% discount; the rest of the business earns 10.5% even
   above 25%. Flash Deals (24.1% average discount, 10.0% of revenue) are the only
   promotion type at a negative margin.
4. **Product mix outranks every other lens by ~20×.** Ranked by revenue-weighted
   spread in margin: subcategory 15.1 points, category 14.2, price band 13.2,
   against region 0.8 and fulfilment mode 0.6. The leadership meeting was arguing
   about the wrong variables.
5. **The "Premium segment problem" is a mix artifact.** Premium's 2.9% pooled
   margin becomes 21.9% outside Electronics, which is ordinary. 65.9% of its
   revenue is Electronics. Any comparison here that does not control for category
   is a category-mix comparison in disguise.
6. **Delivery improved and nobody noticed.** The January 2025 logistics contract
   took on-time delivery 34.4% → 55.0%, complaints 10.1% → 6.9%, ratings 4.15 →
   4.27, for ~₹45 more per order. The 43% company-wide on-time figure that makes
   delivery look broken is the average of a success and a recurring
   October-November collapse, and describes neither.

**What this cannot conclude:** returns are not netted out of `Net_Revenue`, so
every margin is an upper bound; there is no SKU-level cost detail, so we can
prove Electronics loses money but not whether the fix is procurement or pricing;
the delivery-to-rating link is a credible association, not causation; and
order-level data has no lifetime view, which is the main reason the acquisition
recommendation ranks third. Full statement in
[docs/reflection.md](docs/reflection.md).

---

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Dashboard only:
pip install -r requirements.txt
python app.py                      # http://127.0.0.1:8050

# Everything: notebook, tests, and the deliverable build chain
pip install -r requirements-dev.txt
jupyter notebook notebooks/AuroraCart_EDA.ipynb
pytest
```

Rebuilding the deck after a data or analysis change:

```bash
python tools/build_figures.py      # -> deliverables/figures/*.png
python tools/build_deck.py         # -> deliverables/AuroraCart_Executive_Story.pptx
```

Both are pure functions of the dataset, so rerunning them with new data produces
a deck whose numbers and prose match it.

---

## Design and engineering notes

The whole system is dark: a `#0d0d0d` page, `#1a1a19` chart surfaces, and an
eight-hue palette stepped for that surface and validated against it. The deck's
slides use the same surfaces, so the charts blend into them seamlessly.

- **[docs/visual-design.md](docs/visual-design.md)**: the form heuristic, the
  colour-by-job rules, the validator output for the dark palette (including two
  hard colourblindness failures the validator caught in earlier passes that
  inspection did not), mark specs, and the anti-patterns each chart was checked
  against.
- **[docs/responsive-design.md](docs/responsive-design.md)**: the three-layer
  approach that makes the dashboard genuinely usable on a phone, verified across
  emulated devices down to a 320px viewport.
- **[docs/deployment.md](docs/deployment.md)**: free hosting on Render, and why
  not the alternatives.

---

*The case and its dataset are fictional and synthetic, designed for classroom
use. The rupee figures describe that fiction; the method is what transfers.*
