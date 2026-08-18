# The five mandatory questions

Answers to §13 of the case brief, plus the §14 bonus challenge. Every figure
referenced here is in [`../deliverables/figures/`](../deliverables/figures/) and
appears in the deck; every number is computed in
[`src/auroracart/analysis.py`](../src/auroracart/analysis.py) and re-checked by
[`tests/test_analysis.py`](../tests/test_analysis.py).

Throughout, **margin means contribution margin computed as `sum(profit) ÷
sum(net revenue)`** over non-cancelled orders. Why that and not the average of
`Profit_Margin` is argued in [methodology.md](methodology.md#margin-is-weighted-never-averaged).

---

## Question 1 — Executive diagnosis

> If you were given only five minutes with the CEO, what would you identify as
> the most important story contained in the dataset?

**The story in one sentence:** AuroraCart's growth is real, but roughly nine
tenths of the profitability it has lost since 2023 comes from margin erosion
inside categories it already sold — concentrated almost entirely in Electronics,
where merchandise cost alone consumes 94% of what an order recognises — and the
company has been applying one discount policy to two businesses with completely
different tolerance for it.

**The five primary visuals**, in the order I would show them:

| # | Visual | What it establishes |
|---|---|---|
| 1 | `01_growth_vs_margin` | Revenue +98% while margin fell 12.4% → 7.1%. The tension. |
| 2 | `03_margin_decomposition` | 92% of the fall is within-category erosion, not mix shift. Kills the comfortable explanation. |
| 3 | `04_category_margin` + `05_cost_structure` | Electronics is 50.6% of revenue at −4.9%, and the reason is a 94% merchandise-cost ratio, not discounting. |
| 4 | `06_discount_tolerance` | Electronics goes loss-making above a 10% discount; the rest of the business earns 10%+ even at 25%. The controllable lever. |
| 5 | `09_on_time_monthly` | The January 2025 logistics contract worked (34% → 55% on-time). Don't cut there — and note the festive collapse. |

**Why these and not the other patterns.** The dataset offers a dozen true
statements. These five earn executive time because each one changes a decision:

- *Ranked by money at stake.* Product subcategory splits margin by 15.1
  revenue-weighted points and carries a ₹9.3M profit gap. Region splits it by
  0.8 points and ₹0.4M. A regional strategy discussion cannot move the number
  that is moving.
- *Ranked by controllability.* Discount policy can change next quarter. Cost of
  goods takes a supplier negotiation. Customer segment mix takes years. The deck
  spends its middle on the two that are actionable inside twelve months.
- *One is included because it says "stop worrying".* Delivery looks broken at a
  43% pooled on-time rate and is the natural target for a cost cut. It is the
  one function that measurably improved. Telling leadership what *not* to do is
  worth a slide.

What I deliberately left out of the five: weekday/weekend patterns, gender and
age splits, membership tiers, and city-level performance. All are computable;
none of them separate profitability by more than about one point, so none of
them would change where the money goes.

---

## Question 2 — Growth versus value

> Management believes growth should continue because headline indicators are
> improving. Evaluate this claim.

**Verdict: the growth is real, the value creation is not — but the failure is
narrower than "growth is bad", and that distinction is the whole answer.**

### The headline indicators are genuinely improving

| Measure | 2023 | 2025 |
|---|---|---|
| Net revenue | ₹29.3M | ₹58.0M (+98%) |
| Orders (revenue-recognising) | 3,542 | 6,169 |
| Distinct customers | — | 6,778 across the period |
| Average order value | ₹8,268 | ₹9,401 |

The Chief Growth Officer's position survives contact with the data. Volume,
basket size and customer count all moved the right way.

### Two levels of segmentation, and the claim stops surviving

**Level 1 — by time, against a dated intervention.** Accelerate 2.0 launched in
July 2024. Comparing the 18 months either side (`02_accelerate_split`):

| Per month | Before | After | Change |
|---|---|---|---|
| Net revenue | ₹2.62M | ₹4.64M | **+77%** |
| Contribution | ₹0.30M | ₹0.34M | **+14%** |
| Margin | 11.5% | 7.4% | −4.1 pts |
| Average discount | 11.0% | 14.9% | +3.9 pts |
| New-customer share | 37.6% | 49.9% | +12.3 pts |

Revenue grew five and a half times faster than the profit it produced. The
programme delivered what it promised — more customers, more Tier 2, more
volume — at a price nobody costed.

**Level 2 — by category, decomposed.** Margin fell 5.27 points overall. Split
into a mix effect (we sell a different basket now) and a rate effect (the same
basket earns less):

- Mix effect: **−0.41 points**
- Within-category rate effect: **−4.75 points**
- Interaction residual: −0.12 points

**92% of the decline is rate erosion.** Holding the 2023 category mix constant,
2025 margin would still be 7.6%. This matters because the two diagnoses imply
opposite responses: a mix problem is a merchandising problem, an erosion problem
is a pricing and cost problem. Electronics went from −0.3% margin in 2023 to
−7.5% in 2025 while its share of revenue barely moved (49.4% → 51.1%).

### The integrated answer

Growth should continue **selectively**. The evidence does not support "pull
back" — four of five categories earn 18–28% margins and un-promoted demand earns
15.2%. It supports the narrower claim that AuroraCart is currently buying
revenue in the one place it cannot afford to, using a discount policy that does
not distinguish between a Fashion order and a smartphone.

The CFO's framing — what does it cost us to generate each rupee — is the right
one, and answered: in Electronics under promotion, more than a rupee.

---

## Question 3 — Hidden drivers

> Identify the factors most strongly associated with differences in business
> performance. Define what you mean by "performance," justify that definition,
> and support your conclusion visually.

### Defining performance

**Performance = contribution margin**, `sum(Profit) ÷ sum(Net_Revenue)` over
non-cancelled orders.

Justification:

1. **It is the measure the decision needs.** The board is allocating growth
   capital. Revenue tells you size, not whether an incremental rupee of spend
   returns anything.
2. **It is comparable across cuts of wildly different scale.** A ratio lets
   Beauty & Personal Care (7% of revenue) be judged against Electronics (51%).
3. **It is already net of the four costs the dataset models** — product,
   delivery, marketing, operating — so it captures the CMO's channel economics
   and the COO's fulfilment costs in one number rather than arguing about them
   separately.

Its limits, stated up front: returns are not netted out of `Net_Revenue`, so
contribution is somewhat overstated wherever returns run high; and a ratio hides
absolute size, which is why every ranking below is revenue-weighted and reported
alongside rupees at stake.

### Ranking the candidate explanations

For each candidate dimension: the revenue-weighted standard deviation of group
margin around the company margin, `sqrt(Σ wᵍ (marginᵍ − m)²)`, where `wᵍ` is the
group's share of revenue. Weighting is the point — an unweighted range lets a
thin, wild group outrank a dimension that splits half the business.
(`07_driver_ranking`)

| Dimension | Weighted spread (pts) | Margin range | Profit gap (₹M) |
|---|---|---|---|
| **Subcategory** | **15.1** | −9.1% → 31.1% | 9.3 |
| **Category** | **14.2** | −4.9% → 27.7% | 9.1 |
| **Price band** | **13.2** | −6.9% → 24.1% | 8.1 |
| Promotion type | 5.6 | −2.0% → 15.2% | 2.9 |
| Coupon used | 4.2 | 4.9% → 13.3% | 2.7 |
| Acquisition channel | 3.8 | 2.6% → 13.5% | 2.3 |
| Customer segment | 3.7 | 2.9% → 11.9% | 2.1 |
| Brand tier | 3.3 | 4.0% → 12.9% | 1.9 |
| New vs returning | 1.7 | 7.0% → 10.4% | 1.1 |
| Membership type | 1.0 | 6.8% → 9.8% | 0.6 |
| State | 0.8 | 7.6% → 10.2% | 0.5 |
| **Region** | **0.8** | 8.0% → 10.4% | 0.4 |
| **Fulfilment mode** | **0.6** | 7.9% → 9.8% | 0.3 |
| Urban tier | 0.5 | 8.4% → 9.4% | 0.3 |

### Conclusion

**Product mix is the dominant driver, by a factor of roughly twenty over
geography and fulfilment.** Pricing and discounting is the clear second.

Three refinements that matter:

1. **Category, subcategory and price band are the same finding.** 74.9% of
   Electronics revenue sits in the Premium price band, and the Premium band's
   −6.9% margin is essentially Electronics restated; these are not three
   independent explanations. Within Electronics, the loss concentrates further: Smartphones
   are 31.2% of *company* revenue at −9.1% margin, losing ₹3.70M — against
   company-wide contribution of ₹11.6M.

2. **The mechanism is cost structure, not discount depth.** Average discount is
   within 0.3 points across all five categories (13.3%–13.5%). What differs is
   what the goods cost: merchandise is 94.1% of net revenue in Electronics
   against 54.4% in Beauty & Personal Care (`05_cost_structure`). Delivery,
   marketing and operating costs are near-identical across categories.

3. **Customer segment is a confounded proxy, not a driver** — see Question 4.

The leadership meeting was arguing about geography, fulfilment mode and customer
type. Those three dimensions between them explain almost none of the variation
in profitability. That is the most useful thing this analysis can tell the room.

---

## Question 4 — The misleading dashboard

> Construct one technically accurate visualization that could nevertheless lead
> senior management toward a misleading conclusion, then a better one.

### Exhibit A — the misleading view (accurate in every number)

**Profit margin by customer segment, pooled across all orders**
(`08_misleading_pair`, left panel)

| Segment | Margin | Average order value |
|---|---|---|
| **Premium** | **2.9%** | ₹12,957 |
| Occasional | 9.3% | ₹8,731 |
| Family | 11.2% | ₹8,551 |
| Value Seeker | 11.9% | ₹7,275 |

Every figure is correct. The chart is honest bar-per-category work with a zero
baseline, sorted, direct-labelled. The conclusion it invites is immediate and
wrong: *"Premium is our least profitable segment despite the highest order
value — the Premium proposition is broken. Commission a segment review."*

### Why it misleads

The chart pools across product category, and category is exactly what drives
margin (Question 3). Premium's revenue is **65.9% Electronics** — the
loss-making category — against 41.9% for Family and 44.4% for Value Seeker. The
segment axis is silently carrying a product-mix effect.

This is a textbook confounded comparison, and in this dataset it very nearly
reverses the ordering.

### Exhibit B — the corrected view

**The same orders, split by whether they were Electronics**
(`08_misleading_pair`, right panel)

| Segment | Electronics orders | Everything else | Electronics share of revenue |
|---|---|---|---|
| Premium | −6.9% | **21.9%** | 65.9% |
| Family | −4.2% | 22.3% | 41.9% |
| Value Seeker | −3.5% | 24.3% | 44.4% |
| Occasional | −3.4% | 23.5% | 52.7% |

Outside Electronics, Premium earns 21.9% — within 2.4 points of every other
segment, and the ordering among segments is now trivially small. Inside
Electronics, every segment loses money. **The segment was never the problem.**

### The analytical choice that changes the interpretation

**Stratifying by the confounder before comparing.** Nothing about the chart
type, the palette, the sorting or the baseline changed — Exhibit A is a
well-built chart. What changed is the *unit of comparison*: Exhibit A compares
segments as though their baskets were interchangeable; Exhibit B compares
segments holding the basket fixed.

The generalisation for anyone building on this dashboard: **in this dataset, any
comparison that does not control for category is a comparison of category mix
wearing a disguise.** The same trap is waiting in acquisition channel, region
and membership tier.

A second, structural instance of the same failure is worth naming: the
company-wide on-time rate of 43% (`09_on_time_monthly`). Pooled across three
years, it reads as a function that is uniformly broken and a natural place to
cut cost. The monthly series shows a step change from 34% to 55% when the new
logistics contract started, plus a collapse to ~34% in every October–November.
The pooled number is the average of a success and a recurring failure, and it
describes neither.

---

## Question 5 — Decision recommendation

The full write-up, with the reasoning behind the prioritisation, is in
[recommendations.md](recommendations.md). Summarised against the four parts the
question asks for:

### 1. Re-cost and re-price Electronics before scaling it further

- **(a) Evidence.** `04_category_margin`, `05_cost_structure`. Electronics is
  50.6% of net revenue at −4.9% margin, losing ₹3.23M of contribution;
  Smartphones alone are 31.2% of revenue at −9.1%, losing ₹3.70M. Merchandise
  cost is 94.1% of net revenue against 54–67% elsewhere. Discount depth is at
  the company norm, so this is not a promotion problem.
- **(b) Expected benefit.** The largest recoverable pool in the dataset. Moving
  Electronics from −4.9% to break-even adds roughly ₹3.2M of contribution — a
  28% increase on the ₹11.6M the company earned across three years — without
  changing anything about the other four categories.
- **(c) Principal risk.** Electronics is the traffic and attachment engine. If
  its volume is what brings customers who then buy 22%-margin Home & Kitchen,
  repricing it could cost more contribution than it recovers. The dataset can
  see basket-level attachment only weakly.
- **(d) What we would ask for first.** SKU-level cost of goods and a competitor
  price index for the top smartphone SKUs. The dataset can prove Electronics
  loses money; it cannot say whether the fix is a supplier renegotiation, a
  price rise, or exiting specific SKUs — and those are three different projects.

### 2. Set a category-aware discount ceiling; restructure or retire Flash Deals

- **(a) Evidence.** `06_discount_tolerance`. Electronics margin by discount
  band: +7.9% (0–5%), +3.1% (5–10%), **−3.0% (10–15%)**, −8.5%, −14.4%, −23.3%.
  The rest of the business at the same bands: +30.7%, +27.7%, +24.4%, +21.3%,
  +16.1%, **+10.5% even above 25%**. Separately, Flash Deals carry a 24.1%
  average discount, 10.0% of revenue, and are the only promotion type at a
  negative margin (−2.0%); un-promoted orders earn 15.2% and are 34.9% of
  revenue.
- **(b) Expected benefit.** The only recommendation here that is a *rule* rather
  than a bet — it can be configured in the pricing system next quarter. Holding
  Electronics discounts at or below 10% would have moved ₹45.3M of Electronics
  revenue out of the loss-making bands.
- **(c) Principal risk.** Promotion is partly defensive. Withdrawing Flash Deals
  may not convert to full-price demand — it may go to a competitor, or simply
  migrate to Festival Sale. The observed 15.2% margin on un-promoted orders is
  not a forecast of what promoted orders would earn unpromoted.
- **(d) What we would ask for first.** Promotion incrementality — a holdout or
  a historical A/B — to distinguish demand the promotion *created* from demand
  it *discounted*.

### 3. Underwrite acquisition on contribution, not revenue

- **(a) Evidence.** `02_accelerate_split`, `10_channel_economics`. Revenue per
  month +77% against contribution per month +14%. Every channel lost margin
  after Accelerate 2.0, but the paid ones lost most and cost most: Marketplace
  Ads 5.1% → 1.2% margin while spending 9.0% of the revenue it generates, Paid
  Social 7.9% → 3.9% at 7.2%. Together they are 38.1% of revenue. Organic
  Search, Direct and Referral held 9.5–11.2% at 0.6–2.5% marketing cost.
- **(b) Expected benefit.** Shifting the marginal acquisition rupee toward the
  channels that retained their contribution protects growth while stopping the
  purchase of revenue at near-zero margin.
- **(c) Principal risk.** This is the recommendation the evidence supports least
  well, and it is third for that reason. Marketing cost here is *allocated* to
  orders, so channel margin partly reflects an allocation rule rather than
  observed spend. And paid channels may be seeding customers whose value appears
  outside this window — the CMO's point is not refuted by order-level data.
- **(d) What we would ask for first.** Cohort retention and repeat-purchase
  value by acquisition channel, plus the actual allocation methodology behind
  `Marketing_Cost`.

### What we are explicitly *not* recommending

**Cutting delivery investment.** On-time went 34.4% → 55.0% after the January
2025 contract, complaints fell 10.1% → 6.9%, ratings rose 4.15 → 4.27, for about
₹45 more per order (0.26 points of revenue). It is the one function that
demonstrably improved. The operational item worth tracking is narrower: on-time
collapses to ~34% every October–November, a 26.7-point gap against the rest of
2025. That is a peak-capacity problem, and it belongs on the operating review,
not in a three-item strategic list.

---

## Bonus challenge — the three variables we would request

> If you could obtain only three additional variables, which and why?

**1. SKU-level (or subcategory-level) cost of goods, split into unit cost and
supplier terms.**
*Why it changes the decision:* the whole analysis converges on Electronics
having a 94% merchandise-cost ratio, but `Product_Cost` is a single modelled
figure. Whether that ratio comes from unfavourable supplier terms, from
under-pricing against the market, or from a handful of loss-leader SKUs
determines whether Recommendation 1 is a procurement negotiation, a price
increase, or an assortment cut. Right now we can prove the problem and not the
remedy.

**2. A promotion holdout / control flag — which orders were exposed to a
promotion and did not take it.**
*Why it changes the decision:* every promotion conclusion in this analysis is a
comparison of self-selected groups. Un-promoted orders earn 15.2% and promoted
Flash Deal orders lose 2.0%, but customers who buy without a discount may simply
be different customers. A control group converts "Flash Deals are unprofitable"
from an association into a measurement of incrementality, which is the
difference between retiring the mechanic and merely re-pricing it.

**3. Customer-level lifetime revenue and retention beyond the observation
window (or, equivalently, a cohort join date with forward revenue).**
*Why it changes the decision:* Recommendation 3 rests on order-level
contribution, and the CMO's defence of paid acquisition — that it reaches
audiences with strategic value — is not testable with what we have.
`Customer_Tenure_Months` and `Days_Since_Last_Purchase` describe history, not
future value. If Marketplace Ads customers repeat at twice the rate of Organic
Search customers, a 1.2% first-order margin could be perfectly rational, and
Recommendation 3 inverts.

**Honourable mention (a fourth we would take if offered):** returns and refunds
as financial reversals. `Return_Flag` records that a return happened but no
value flows back through `Net_Revenue` or `Profit`, so every margin in this
analysis is optimistic by an unknown amount that is largest wherever return
rates are highest.
