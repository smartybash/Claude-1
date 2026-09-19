# A setup grading scheme, tested as an object — declared before running

Grades are applied to trades **already generated** by the existing ORB and
pullback rules. No new rule is created, no parameter is re-tuned, no trade is
added or removed. The only question is whether the grade label separates outcome.

Sealed NQ days are not read. This screen never opens the NQ tape.

---

## 1. The trade sets the grades are applied to

The surplus region used by every recent screen: **stop 1.0 ATR**, entry bar
skipped, honest fills, flat 18:30 UTC, on the **1,418 QQQ sessions**
(2021-01-04 to 2026-08-31).

| family | machine | OR_MIN | target | sets |
|---|---|---|---|---|
| ORB | `or_height.run_session`, unchanged | 15, 30 | 3R, 4R | 4 |
| pullback | `pullback.run_session`, unchanged | 15, 30 | 3R | 2 |

**Six trade sets.** Reported pooled (the primary analysis, where the ≥300
requirement applies) and per set (for transparency).

---

## 2. The three quantities, all measurable at the decision timestamp

| quantity | source | available at entry? |
|---|---|---|
| **cost / realised risk** | 0.667 bps ÷ the trade's own risk in bps | yes — risk is \|entry − stop\|, fixed when the stop is placed |
| **OR height ÷ trailing 20-session mean** | `or_height.or_ratio`, shifted one session | yes — uses only prior sessions and the OR window |
| **minutes since the cash open** | entry timestamp − 09:30 | yes, trivially |

---

## 3. The grades — exact thresholds, fixed now

One point per condition met:

| condition | threshold | why this threshold |
|---|---|---|
| cost / risk | **≤ 5.0%** | 0.667 bps ÷ 5% = a 13.3 bps stop. The existing runs report a median risk near 10.6 bps, so this splits near the middle without being chosen from the outcome |
| OR ratio | **≥ 1.00** | the trailing mean itself — the same split the OR-height pre-registration used |
| minutes since open | **≤ 60** | the first hour; an existing time-of-day bucket edge in the current pipeline, and the window with the most session left to reach a 3R target |

| grade | points |
|---|---|
| **A+** | 3 of 3 |
| **A** | 2 of 3 |
| **B** | 0 or 1 of 3 |

---

## 4. Two things declared before the result, because they determine how to read it

### Two of the three components are already known to be null

- **OR ratio** was the entire hypothesis of the OR-height screen, which returned
  **0 of 4** across 1,418 in-sample and 1,256 held-out sessions. There is no
  measured gradient for it to contribute.
- **Time of day** is already printed in the existing ORB runs by bucket, and no
  gradient was reported.

### The third is an accounting identity, not a prediction

`R = gross/risk − cost/risk`, so **expectancy differs between grades by the cost
differential whether or not the market cooperates.** A trade at 2% cost/risk
starts 0.02R ahead of one at 8%, mechanically, before any price moves.

**So some separation is expected by construction, and the test must not take
credit for it.** The decomposition is therefore reported every time:

| reported | meaning |
|---|---|
| **spread in net R** | what a trader would actually receive |
| **spread in gross R** (= net R + cost/risk) | market behaviour only, cost removed |
| difference between them | the arithmetic |

**If the spread lives entirely in the cost term, the finding is not "grade
predicts outcome" — it is "wider stops pay a smaller toll", which is already
known, requires no grading scheme, and is obtained by preferring wider stops.**
That will be stated in exactly those words if it is what the numbers show.

---

## 5. The control that decides it

**1,000 random grade assignments**, drawn without replacement to reproduce the
**observed A+ / A / B proportions exactly**, over the same pooled trade set.

This is the right control and not merely a convenient one: permuting labels over
the same trades preserves the correlation structure that pooling six overlapping
trade sets creates, so no separate correction for it is needed.

Reported: the full distribution of the random A+ − B spread, and **the
percentile the real spread lands in**.

---

## 6. Pass criteria — all four required

1. **≥ 300 trades in each grade**, pooled.
2. **Monotonic**: A+ ≥ A ≥ B in net R. A scheme where the middle grade wins is
   not a grading scheme.
3. **The real A+ − B spread exceeds the 95th percentile** of the 1,000 random
   assignments.
4. **A+ > B in at least 4 of the 6 calendar years.**

If all four pass, the gross-R decomposition then says whether it was market or
arithmetic — and that determination is reported either way, not only when
convenient.

---

## 7. Standing instrumentation, unchanged

- **Counts before any performance number.**
- **Honest fills with the naive result alongside.** ORB carries `naive_R`
  directly. Pullback's existing record does not, but its naive value is exactly
  recoverable without touching the rule: a stopped trade's naive fill is the stop
  price itself, so `naive_R = −1 − cost/risk`, and every non-stop exit is
  identical under both. No machine is modified.
- **Entry bar skipped** for the exit search — already true in both machines.
- **Entry lookahead check**, counted and printed.
- **Ambiguous bar rate** per trade set.

---

## 8. What each outcome means, fixed now

- **The real grading does not beat random assignment.** Then grade does not
  separate outcome, the idea is dropped, and it will be said plainly in one
  sentence rather than softened.
- **It beats random but the spread is entirely in the cost term.** Then it is
  re-described as a stop-width preference, not a setup grade, and no grading
  scheme is warranted.
- **It beats random with a surviving gross-R spread.** Then two of three
  components are known-null, so the honest next step is to find which component
  is carrying it — not to ship the composite.

---

Committed before `scripts/orderflow/setup_grading.py` was run.
