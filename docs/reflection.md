# Deliverable D: analytical reflection

The case brief (§15.4) asks for four things briefly. Each is stated first, then
justified.

---

## One important assumption we made

**That `Profit` is a usable contribution measure at the order level, and that
summing it across orders is meaningful.**

The dataset defines `Profit` as net revenue less product, delivery, marketing and
allocated operating cost. Two of those four, marketing and operating, are
*allocated* rather than observed at the order. We assumed the allocation is
proportionate enough that comparisons between groups remain valid.

This assumption is load-bearing and unevenly so. It barely matters for
Recommendation 1: Electronics' problem is `Product_Cost` at 94.1% of net revenue,
which is a direct merchandise cost, and marketing plus operating together are
only 9.2 points of it. It matters a great deal for Recommendation 3, where the
entire finding is about marketing cost by channel. If `Marketing_Cost` is
allocated by revenue share rather than measured by campaign, the channel margin
differences are partly an artifact of the allocation rule. That is the single
biggest reason acquisition is ranked third rather than first.

---

## One dataset limitation that affects interpretation

**Returns are recorded as a flag but never reversed financially.**

`Return_Flag` marks 7.2% of orders as having generated a return request, but no
value flows back out of `Net_Revenue` or `Profit`. Every margin figure in this
analysis is therefore optimistic by an unknown amount, and optimistic
*unevenly*: the overstatement is largest wherever return rates are highest, so
the ranking between categories could shift, not just the levels.

The practical consequence: every contribution figure here is an upper bound, and
the adjustment does not fall evenly. Return rates run 4.9% (Beauty & Personal
Care) to 10.7% (Fashion), with Electronics at 8.2%, so netting returns out
would penalise Fashion, one of the *healthy* categories, hardest. Two things
follow. The gap between Electronics and the rest would narrow somewhat, and the
ranking among the four profitable categories could re-order. Neither reverses
the conclusion: Fashion would have to lose more than 27 points of margin to
returns before it looked anything like Electronics. Priority 1 depends on
Electronics being negative and large, not on it being exactly −4.9%.

---

## One plausible but misleading interpretation we deliberately avoided

**That the Premium customer segment is unprofitable and needs to be re-priced or
re-positioned.**

Pooled across all orders, Premium shows a 2.9% margin against 9.3-11.9% for
every other segment, on the highest average order value in the business
(₹12,957). Spends the most, earns the least: that combination is a compelling
narrative, and it is where an earlier draft of this analysis went.

It is a confounded comparison. 65.9% of Premium's revenue is Electronics, the
loss-making category, against 41.9% for Family. Split the same orders by whether
they contained Electronics and Premium earns 21.9% outside it, within 2.4 points
of every other segment, and loses money inside it, exactly like everyone else.

We avoided it by stratifying on the confounder before comparing, and the general
rule it produced governs the rest of the analysis: **in this dataset, any
comparison that does not control for product category is a category-mix
comparison in disguise.** The same trap sits in the acquisition-channel,
membership-tier and regional cuts, and each was checked against it. This is
written up in full as
[Question 4](mandatory-questions.md#question-4-the-misleading-dashboard).

A second interpretation avoided, worth a line: **that delivery performance is
uniformly poor and a candidate for cost reduction.** The pooled 43% on-time rate
supports that reading. The monthly series does not. It shows a 34% → 55% step
change when the new logistics contract began, pooled with a festive-season
collapse that recurs every year. Cutting there would have withdrawn funding from
the one function that measurably improved.

---

## One additional dataset we would request

**Customer-level lifetime value with retention beyond the observation window: a
cohort table keyed on first-order date, carrying forward revenue and
contribution by acquisition channel.**

This is the single dataset that could change a recommendation rather than merely
refine one. The entire third recommendation rests on first-order contribution by
channel, and the CMO's objection (that paid channels reach audiences with
strategic value that first-order economics cannot see) is not testable with what
we have. `Customer_Tenure_Months` and `Days_Since_Last_Purchase` describe history
at the moment of the order; neither says what a customer went on to be worth.

If customers acquired through Marketplace Ads repeat at twice the rate of
Organic Search customers, a 1.2% first-order margin is a rational investment and
Recommendation 3 should be reversed rather than softened. If they do not,
Recommendation 3 becomes considerably more urgent than its current third place.
Either way the number moves the decision, which is the test for asking.

Two others we would take if offered, in order: SKU-level cost of goods (turns
Priority 1 from a diagnosis into a specific remedy) and a promotion holdout flag
(turns Priority 2's association into measured incrementality). All three are set
out in the
[bonus challenge answer](mandatory-questions.md#bonus-challenge-the-three-variables-we-would-request).
