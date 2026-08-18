# Deliverable C — Executive recommendations

Three actions for the next twelve months, in priority order. The case brief asks
for no more than three and for prioritisation rather than a list, so the ordering
below is the argument, not a formatting choice.

**How they were ranked.** By contribution at stake first, controllability second,
strength of evidence third. Recommendation 1 is the largest pool of money.
Recommendation 2 is the fastest to implement and the most certain. Recommendation
3 is the one the data supports least confidently, and it says so.

---

## Priority 1 — Re-cost and re-price Electronics before scaling it further

**The finding.** Electronics is 50.6% of net revenue and the only category
losing money, at −4.9%. Within it, Smartphones are 31.2% of *company* revenue at
−9.1% margin, destroying ₹3.70M of contribution against ₹11.6M earned
company-wide over three years. The mechanism is not discounting — average
discount is within 0.3 points across all five categories — it is that
merchandise cost consumes 94.1% of what an Electronics order recognises, against
54–67% everywhere else.

**Why first.** It is the largest single recoverable pool in the dataset, and it
is the only one where fixing it does not require anything to change in the four
healthy categories. It is also the root cause behind two other findings that
look independent: the "Premium segment problem" (a mix artifact — see
[Question 4](mandatory-questions.md#question-4--the-misleading-dashboard)) and
most of the 2023→2025 margin decline.

**Expected benefit.** Moving Electronics to break-even adds roughly ₹3.2M of
contribution — a ~28% increase on total contribution — with no change to the rest
of the portfolio.

**Principal risk and trade-off.** Electronics may be the traffic and attachment
engine: if smartphone volume is what brings customers who then buy 21% margin
Home & Kitchen, repricing it could cost more contribution than it recovers.
Order-level data sees basket attachment only weakly. Accept a volume decline
deliberately and monitored, not as a surprise.

**Information required before committing.** SKU-level cost of goods and a
competitor price index for the top smartphone SKUs. The dataset proves
Electronics loses money; it cannot distinguish a supplier-terms problem from an
under-pricing problem from a handful of loss-leader SKUs — and those are three
different projects with three different owners.

---

## Priority 2 — Set a category-aware discount ceiling; restructure or retire Flash Deals

**The finding.** Discount tolerance is a function of cost structure, and
AuroraCart has been setting it company-wide. Margin by discount band:

| Discount applied | Electronics | Rest of business |
|---|---|---|
| 0–5% | +7.9% | +30.7% |
| 5–10% | +3.1% | +27.7% |
| **10–15%** | **−3.0%** | +24.4% |
| 15–20% | −8.5% | +21.3% |
| 20–25% | −14.4% | +16.1% |
| 25%+ | −23.3% | **+10.5%** |

Electronics crosses into loss somewhere between a 10% and 15% discount. The rest
of the business is still earning double digits above 25%. Separately, Flash Deals
carry the deepest average discount (24.1%), are 10.0% of revenue, and are the
only promotion type with a negative margin (−2.0%). Un-promoted orders are the
most profitable demand the company has: 15.2% margin on 34.9% of revenue.

**Why second.** Smaller than Priority 1, but it is a *rule* rather than a bet —
it can be configured in the pricing system next quarter and enforced
automatically, where Priority 1 needs a supplier negotiation or a price change
with a lead time.

**Expected benefit.** ₹45.3M of Electronics revenue currently sits in
loss-making discount bands. A 10% Electronics ceiling addresses that band
directly; the equivalent constraint costs the other four categories almost
nothing, because they are profitable at every observed depth.

**Principal risk and trade-off.** Promotion is partly defensive. Withdrawn Flash
Deals may not convert into full-price demand — the volume may move to a
competitor, or simply migrate to Festival Sale, which already runs at 3.8%. The
15.2% margin on un-promoted orders describes customers who chose not to wait for
a discount; it is not a forecast of what discounted orders would earn without
one.

**Information required before committing.** Promotion incrementality — a holdout
group or a historical A/B — to separate demand a promotion *created* from demand
it merely *discounted*.

---

## Priority 3 — Underwrite acquisition on contribution, not revenue

**The finding.** Under Accelerate 2.0, revenue per month rose 77% while
contribution per month rose 14%. Channel margins after the programme, against
what each channel spends on marketing per rupee of revenue it earns:

| Channel | Margin before | Margin after | Marketing cost / revenue | Revenue share |
|---|---|---|---|---|
| Marketplace Ads | 5.1% | **1.2%** | 9.0% | 14.3% |
| Paid Social | 7.9% | **3.9%** | 7.2% | 23.9% |
| Email | 12.7% | 9.0% | 1.3% | 8.4% |
| Referral | 12.9% | 9.5% | 2.5% | 11.1% |
| Organic Search | 13.1% | 10.6% | 1.2% | 27.4% |
| Direct | 17.6% | 11.2% | 0.6% | 15.0% |

Every channel lost margin. The two paid channels lost the most while spending
the most, and together they are 38.1% of revenue.

**Why third.** Not because it is unimportant — 38% of revenue is not a footnote
— but because it is the recommendation this dataset supports least confidently,
and priority should track evidence strength. `Marketing_Cost` is *allocated* to
orders, so channel margin partly reflects an allocation rule rather than observed
spend. Recommendation 1 and 2 do not depend on any allocation assumption.

**Expected benefit.** Shifting the marginal acquisition rupee toward Organic
Search, Direct and Referral — which retained 9.5–11.2% margins at a twentieth of
the marketing cost ratio — protects growth while stopping the purchase of revenue
at near-zero contribution.

**Principal risk and trade-off.** The CMO's argument is not refuted by this data.
Paid channels may reach audiences that organic cannot and may seed customers
whose value appears after the observation window. Cutting paid spend on
first-order contribution alone could destroy value that this dataset simply
cannot see.

**Information required before committing.** Cohort retention and repeat-purchase
value by acquisition channel, plus the methodology behind the `Marketing_Cost`
allocation. If Marketplace Ads customers repeat at twice the rate of Organic
Search customers, a 1.2% first-order margin may be entirely rational and this
recommendation inverts.

---

## What we are explicitly not recommending, and why

Prioritisation means saying what falls below the line. Three candidates that a
reader of the summary tables would reasonably expect here:

**Do not cut delivery investment.** The January 2025 logistics restructure
worked: on-time delivery 34.4% → 55.0%, complaints 10.1% → 6.9%, average rating
4.15 → 4.27, delay 0.74 → 0.43 days, for about ₹45 more per order — 0.26 points
of revenue. The company-wide 43% on-time figure that makes delivery look like a
failing function is an average of the period before the contract and the period
after it, and describes neither.

**Do not commission a customer-segment programme.** Premium's 2.9% pooled margin
is a category-mix artifact; outside Electronics it earns 21.9%, within 2.4 points
of every other segment.

**Do not build a regional strategy off this data.** Region separates margin by
0.8 revenue-weighted points and Urban Tier by 0.5. Whatever differences exist
between North and South are not where the profit went.

## One operating item, not a strategic recommendation

On-time delivery collapses to roughly 34% every October–November — a 26.7-point
gap against the rest of 2025, and the same pattern in 2023 (21.4 points) and 2024
(21.2 points). This is a peak-capacity problem, it is consistent and predictable,
and it should sit on the operating review with a named owner. It is not in the
three because its contribution impact is an order of magnitude below Priority 1,
and because the fix is already understood — the analysis adds nothing to it
beyond confirming that it recurs.
