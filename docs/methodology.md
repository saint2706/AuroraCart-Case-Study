# Methodology: data quality, definitions and denominators

The case brief says decisions about "standardization, duplicates, missing values,
outliers and denominator choices are part of the analytical task" (§7). This is
the record of those decisions and the reasoning behind each. The audit that
justified them, with the output of every check, is in
[`notebooks/AuroraCart_EDA.ipynb`](../notebooks/AuroraCart_EDA.ipynb) §1; the
code that applies them is
[`src/auroracart/data_prep.py`](../src/auroracart/data_prep.py).

Both the notebook and the dashboard import `load_data()` from that one module,
so there is no version of "clean" that exists in only one artifact.

---

## The dataset

`data/raw/data-AuroraCart.csv` is the case's `data.csv`, kept under the name it
was exported with. 15,000 raw rows × 50 columns, one row per order, January 2023
to December 2025. After cleaning and feature engineering: **14,970 orders ×
54 columns, 6,778 customers**.

---

## Data-quality decisions

### 1. Exact duplicate rows: dropped

30 rows are byte-identical duplicates of another row, including `Order_ID`. The
brief states these are seeded deliberately (§7.1). They are the same order
captured twice in the export, not two orders; leaving them in would
double-count both revenue and the operational events attached to them.

**Decision: drop.** `df.drop_duplicates()`, applied before anything else so no
downstream figure sees them.

### 2. Inconsistent category and channel labels: standardised

`Home & kitchen` → `Home & Kitchen`, `Beauty and Personal Care` → `Beauty &
Personal Care`, `organic search` → `Organic Search`, `Paid social` → `Paid
Social`. These are casing and connector-word variants of existing values, not
new levels. We confirmed that by checking that the variants' distributions match
their canonical twin rather than forming a distinct population.

**Decision: map to the canonical label.** Left unfixed, Electronics' 50.6%
revenue share would compete against a Home & Kitchen split across two rows.

### 3. Missing values: three different causes, three different treatments

Each missing field was checked against its related columns before deciding
anything, because "missing" here means three unrelated things:

| Field | Why it is missing | Treatment |
| --- | --- | --- |
| `Promotion_Type` | No promotion was applied | Recode to `"No Promotion"`. This is information, not absence |
| `Membership_Type` | Customer has no paid membership | Recode to `"No Membership"` |
| `Age_Group` | Not captured in the profile | Recode to `"Unknown"`, an explicit level, so it can be excluded knowingly |
| `Days_Since_Last_Purchase` | First observed order, so there is no previous purchase | **Leave NaN.** Zero would mean "bought yesterday" |
| `Customer_Rating` | Order cancelled, or customer did not rate | **Leave NaN.** Imputing the mean would invent satisfaction |
| `Profit_Margin` | Order cancelled → zero net revenue → undefined | **Leave NaN** (and never used, see below) |

**The principle:** structurally-missing *categoricals* become an explicit label
so they appear in every chart rather than silently vanishing from a groupby.
Numerically *unknown* values stay NaN and every aggregation uses skipna
semantics. Nothing is imputed. Imputation here would manufacture the exact
signal the analysis is trying to measure.

### 4. Outliers: kept

No order was excluded for being extreme. The high-value tail is Premium-band
smartphones, which is the substance of the finding rather than noise, and
trimming it would remove the loss it carries. Where an extreme value could
distort a chart, the response was a better encoding (bands, revenue weighting),
not deletion.

---

## Denominator decisions

The case warns that "a technically correct metric can still produce a misleading
managerial interpretation if the level of aggregation is inappropriate" (§10).
Three choices carry most of the weight.

### Margin is weighted, never averaged

**Margin = `sum(Profit) ÷ sum(Net_Revenue)`, never `mean(Profit_Margin)`.**

The dataset ships a per-order `Profit_Margin` column, and averaging it is the
obvious move. It is also wrong for every managerial question here: it weights a
₹400 lipstick order identically to a ₹90,000 smartphone order. The company does
not experience margin that way. It experiences rupees.

The two diverge violently here, and in the direction that flatters: the
revenue-weighted margin is **8.9%**, the mean of order-level margins is
**16.2%**, nearly double. The gap is Electronics, which is a modest share of
*orders* and half the *rupees*, so averaging ratios all but erases it. Every
margin in every artifact here is revenue-weighted;
[`tests/test_data_prep.py`](../tests/test_data_prep.py) asserts it, including an
explicit assertion that the two are not equal, so the trap cannot creep back in.

### Cancelled orders leave the revenue denominator and stay in the operations one

Cancelled orders (2.9% of rows) recognise zero net revenue by construction,
verified 1:1 against `Cancellation_Flag` in the source. They are excluded from
every revenue, margin and AOV figure via the derived `Is_Valid_Revenue` flag,
because a zero-revenue row in a margin denominator dilutes the result toward
nothing while describing no economic activity.

They are **kept** for cancellation, complaint, return and on-time rates, where
the cancellation is the subject rather than a nuisance. Every chart states which
denominator it used.

### Time comparisons are per-month, and anchored to dated events

Comparing two windows of unequal length by totals guarantees the longer one wins.
Both event comparisons, Accelerate 2.0 (July 2024) and the logistics
restructure (January 2025), report revenue, profit and orders **per month**, and
[`analysis.era_comparison()`](../src/auroracart/analysis.py) computes the
divisor from the data rather than assuming equal windows.

Both dates come from the case narrative (§3), not from hunting the series for a
break. Anchoring to a pre-declared date is what keeps a before/after comparison
from being a story fitted to a wiggle.

---

## Metric definitions used throughout

| Metric | Definition | Denominator |
| --- | --- | --- |
| Net revenue | `sum(Net_Revenue)` | Non-cancelled orders |
| Contribution / profit | `sum(Profit)` = net revenue − product − delivery − marketing − operating cost | Non-cancelled orders |
| Margin | `sum(Profit) ÷ sum(Net_Revenue) × 100` | Non-cancelled orders |
| AOV | `sum(Net_Revenue) ÷ count(orders)` | Non-cancelled orders |
| Discount depth | `mean(Discount_Percentage)` | Non-cancelled orders |
| Marketing cost ratio | `sum(Marketing_Cost) ÷ sum(Net_Revenue)` | Non-cancelled orders |
| On-time rate | `mean(On_Time_Flag)` | **All** orders |
| Return / complaint / cancellation rate | `mean(flag)` | **All** orders |
| Weighted margin spread | `sqrt(Σ wᵍ (marginᵍ − m)²)`, `wᵍ` = revenue share | Non-cancelled orders |
| Profit gap | `Σ max(0, m − marginᵍ) ÷ 100 × revenueᵍ` | Non-cancelled orders |

---

## What the analysis does not claim

Stated here once so the claims elsewhere can be read literally:

- **No causal claims.** Late delivery correlates with lower ratings (r ≈ −0.48)
  and orders delivered late complain at 12.3% against 4.0% on time. That is an
  association. The dataset has no randomisation and no instrument.
- **The discount-band curves are tolerance, not response.** Deeply discounted
  orders differ from lightly discounted ones in what they contain, not only in
  their discount. The policy conclusion, that a ceiling must be category-aware,
  survives either reading, which is why it is the one stated.
- **Event windows are before/after comparisons, not difference-in-differences.**
  There is no control group unaffected by Accelerate 2.0 or by the logistics
  contract. Other things changed in the same months.
- **The dataset is synthetic.** The method transfers; the specific rupee figures
  describe a fictional company.
