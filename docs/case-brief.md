# Case brief: where each requirement is answered

A map from the assignment document (*Storytelling Using Data Visualization —
AuroraCart at a Crossroads*) to the artifact that answers it, so a reader can
check coverage without reading everything.

## Expected deliverables (§15)

| | Deliverable | Where |
|---|---|---|
| **A** | Interactive dashboard | [`src/auroracart/dashboard.py`](../src/auroracart/dashboard.py): 5 pages, global filters. Run with `python app.py`, or see [deployment.md](deployment.md) for the hosted link. |
| **B** | Executive story, 7-10 minutes | [`deliverables/AuroraCart_Executive_Story.pptx`](../deliverables/AuroraCart_Executive_Story.pptx): 17 slides with timed speaker notes. Source: [`tools/build_deck.py`](../tools/build_deck.py). |
| **C** | Executive recommendations (max 3, prioritised) | [recommendations.md](recommendations.md), and the dashboard's **Decision** tab. |
| **D** | Analytical reflection | [reflection.md](reflection.md) |

## Five mandatory questions (§13) and the bonus (§14)

| Question | Where |
|---|---|
| 1. Executive diagnosis (≤ 5 primary visuals) | [mandatory-questions.md §Q1](mandatory-questions.md#question-1-executive-diagnosis) |
| 2. Growth versus value (multi-measure, ≥ 2 levels of segmentation) | [§Q2](mandatory-questions.md#question-2-growth-versus-value) |
| 3. Hidden drivers (define "performance", justify, support visually) | [§Q3](mandatory-questions.md#question-3-hidden-drivers) |
| 4. The misleading dashboard | [§Q4](mandatory-questions.md#question-4-the-misleading-dashboard) |
| 5. Decision recommendation (evidence / benefit / risk / one more thing) | [§Q5](mandatory-questions.md#question-5-decision-recommendation) and [recommendations.md](recommendations.md) |
| Bonus: three additional variables | [§Bonus](mandatory-questions.md#bonus-challenge-the-three-variables-we-would-request) |

## Analytical brief (§7)

| The brief asks us to explain | Answered in |
|---|---|
| What is happening in the business | Deck slides 3-5; dashboard **Executive Overview** |
| Where the most important differences occur | Deck slides 7-9; dashboard **Profitability Deep-Dive**; [Q3 driver ranking](mandatory-questions.md#question-3-hidden-drivers) |
| What factors appear associated with those differences | [Q3](mandatory-questions.md#question-3-hidden-drivers): product mix dominates; geography and fulfilment do not |
| Why the patterns matter to management | Deck slides 11-14; [recommendations.md](recommendations.md) |
| What cannot be concluded | [methodology.md §What the analysis does not claim](methodology.md#what-the-analysis-does-not-claim); [reflection.md](reflection.md); deck slide 17 |
| What management should consider doing next | [recommendations.md](recommendations.md); dashboard **Decision** tab; deck slide 16 |
| Data quality examined before the dashboard | [methodology.md](methodology.md); notebook §1 |

## Dashboard expectation (§8): the five pages

The brief suggests 3-5 pages and an illustrative flow. Ours follows it, with the
diagnostic split across two pages because that is where the argument lives.

| Page | Role in the narrative | Carries |
|---|---|---|
| **Executive Overview** | Context + tension | KPI strip, monthly revenue, monthly margin with the Accelerate 2.0 marker, revenue by category and region |
| **Profitability Deep-Dive** | Diagnostic | Margin by category, discount-vs-margin by promotion, segment AOV and margin |
| **Customers** | Driver detail | New vs returning, loyalty, channel marketing cost, rating distribution |
| **Operations & Delivery** | Driver detail | On-time by fulfilment mode, complaint rate on-time vs late, returns by category, monthly on-time with the logistics-contract marker and festive-peak shading |
| **Decision** | Strategic recommendation | Three prioritised recommendation cards, the driver ranking, the discount-tolerance curves, and the Question 4 pooled-vs-split pair |

Every page respects one global filter row (date range, region, category, segment,
fulfilment mode) rather than per-page filters.

## Storytelling expectation (§9): the deck's arc

| Stage | Slides |
|---|---|
| Context | 2-3: revenue nearly doubled; margin fell by more than a third |
| Tension | 4-5: Accelerate 2.0 grew revenue per month 77% and profit per month 14% |
| Investigation | 6-9: 92% of the decline is within-category; it is Electronics; the mechanism is a 94% merchandise-cost ratio |
| Evidence | 10-14: discount tolerance, driver ranking, the misleading pair, the delivery step change |
| Consequence & decision | 15-17: three prioritised actions, then the limits |

## Visual design expectations (§17)

Chart construction is documented in [visual-design.md](visual-design.md): the
form heuristic, the validated colourblind-safe dark palette (with the validator
output), the mark specifications, and the specific anti-patterns each chart was
checked against.

## Notes on scope

- The case names the primary file `data.csv`; it is committed as
  `data/raw/data-AuroraCart.csv`, under the name it was supplied with.
- The dataset is synthetic and the company fictional, per the brief's cover page.
  The rupee figures describe that fiction; the method is what transfers.
