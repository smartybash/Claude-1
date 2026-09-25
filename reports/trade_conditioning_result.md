# Conditioning the existing trade sets: the direction closes

Pre-registered at `242c9c4`. **No new rule was created and nothing was
re-optimised** — all seven trade sets were regenerated from the frozen modules
and reproduce the ledger to four decimals before any conditioning was applied.

**Sealed days stay sealed. 2016–2020 stays unread.**

---

## 1. The sets, reproduced unchanged

| set | ledger n | ledger mean R | regenerated |
|---|---|---|---|
| IB 1R single | 685 | +0.0612 | **685, +0.0612** ✓ |
| IB 1R re-entry | 736 | +0.0628 | **736, +0.0628** ✓ |
| IB 2R re-entry | 719 | +0.0628 | **719, +0.0628** ✓ |
| IB 3R re-entry | 718 | +0.0632 | **718, +0.0632** ✓ |
| IB 4R re-entry | 718 | +0.0610 | **718, +0.0610** ✓ |
| ORB-Fib cont ORB15 A | 112 | +0.1154 | **112, +0.1154** ✓ |
| ORB-Fib cont ORB30 A | 76 | +0.2071 | **76, +0.2071** ✓ |

**8 IB trades are then lost** (685 → 677) because the pre-open study's session
builder additionally requires a session to run to 16:00, which `reopen_study`
does not. Those 8 dates have no conditions, so their trades cannot be
conditioned. Stated rather than absorbed silently.

---

## 2. Counts and burden, before any performance number

| | |
|---|---|
| trade sets | 7 |
| conditions | 6 |
| **subsets examined** | **152** |
| **claimable (n ≥ 150)** | **105** — matching the 105 predicted in §3.2 of the pre-registration |
| unresolvable on size | 47 |
| permutations | 5,000, exactly matched group sizes |

**IB sets 1–5 share entries** and are not independent tests. `R` is already net
of costs.

---

## 3. The answer

### 3.1 No subset beats the control

| | |
|---|---|
| permuted **global max t**, 95th percentile | **+3.777** |
| permuted global max t, **median** | **+2.926** |
| **observed best t across all 152 subsets** | **+2.263** |
| that subset | IB 1R single / FOMC = 0 / n = 652 |
| **beats the control?** | **NO** |
| empirical p of the observed maximum | **0.9902** |

**The observed best subset is weaker than the *median* random-label search.**
Not merely short of the 95th percentile — below the middle of the null. Shuffling
the conditions produces a better-looking best subset 99% of the time than the
real conditions do.

Per trade set, with no exceptions:

| set | observed max t | permuted 95th | beats? |
|---|---|---|---|
| IB 1R single | +2.263 | +3.531 | no |
| IB 1R re-entry | +2.117 | +3.594 | no |
| IB 2R re-entry | +2.125 | +3.297 | no |
| IB 3R re-entry | +2.240 | +3.271 | no |
| IB 4R re-entry | +2.181 | +3.237 | no |
| ORB-Fib cont ORB15 A | +1.874 | +2.823 | no |
| ORB-Fib cont ORB30 A | +1.726 | +3.259 | no |

**The best subset in the whole run is the one that is almost the entire parent
set** — IB 1R single with the 25 FOMC-day trades removed, n = 652 of 677. Its t
is highest because it is largest, not because the condition selected anything.
That is what "conditioning found nothing" looks like in the table.

### 3.2 The concentration rule does the rest

| | |
|---|---|
| claimable subsets | 105 |
| **with mean R > 0 after costs** | **95** |
| **...and surviving max(10, ⌈0.10n⌉)** | **1** |
| median after-concentration mean R across claimable subsets | **−0.1050** |

**Ninety-five of 105 claimable subsets are positive. One survives the
concentration rule.** The pathology found in the retroactive audit — the parent
set's top decile carrying 164% of total R — is inherited by essentially every
subset of it. Slicing a tail-carried distribution yields tail-carried slices.

### 3.3 The one subset that passes all four bars, and why it is not a candidate

| | |
|---|---|
| set | IB 1R single |
| condition / partition | overnight range, **top quartile** |
| n | 168 |
| mean R | **+0.1126** |
| clustered SE (by date) | 0.0550 |
| t | **+2.05** |
| after dropping 17 trades | **+0.0133** |
| years positive | 4 / 6 |

It clears all four declared bars. It does **not** clear the control: t +2.05
against a within-set bar of +3.531 and a global bar of +3.777.

This is exactly the case the control was declared for. **One subset out of 105
clearing a four-part screen is what a null produces** — and its survival margin
after the concentration rule is +0.013 R, which against its own SE of 0.055 is
indistinguishable from zero. Declaring it tradeable would mean taking the single
best-looking slice from a search that, as a whole, performed worse than chance.

---

## 4. The decile ladders that were asked for

Reported as description; as declared in §3.2 of the pre-registration, **no
decile of a 677-trade set (≈ 68 trades) can reach the 150-trade floor**, so none
of these is claimable regardless of what it shows.

**IB 1R single, mean R by decile:**

| condition | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d10−d1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VIX level | +0.048 | +0.017 | +0.049 | +0.195 | −0.092 | +0.094 | +0.067 | −0.058 | +0.168 | +0.039 | −0.009 |

The ladder is noise around the parent mean: no monotonicity, sign changes in
five places, and the largest decile t is +2.12 on 59 trades. The full set of
ladders is in `reports/trade_conditioning_output.txt`.

**ORB-Fib, as predicted, cannot be resolved.** ORB30 A returns "insufficient"
on every condition; ORB15 A manages three ladders at **10–11 trades per decile**,
with decile means ranging from −0.546 to +0.919 — a spread that is pure sampling
noise at that size. Recorded as **not resolvable on available data**, not as a
failure, consistent with how the ORB-Fib reversal family was recorded.

---

## 5. What this closes, and the gap it fills

The pre-open study tested whether conditions predict session *efficiency*, and
found nothing (0 of 30 on decision outcomes). The stated gap was that efficiency
is a proxy — expectancy could in principle be conditional even where efficiency
is not.

**It is not.** Tested directly on per-trade R across 152 subsets of seven frozen
trade sets, with date-clustered errors and a properly sized max-statistic
control, the best real result sits at the 1st percentile of the null.

| direction | tests | result |
|---|---|---|
| price-derived predictors → efficiency | 14 | null, largest rho 0.042 |
| pre-open predictors → efficiency & direction | 30 | null, largest rho 0.076 |
| **pre-open predictors → per-trade expectancy** | **152 subsets** | **null, observed max below the permuted median** |

**Conditioning is finished as a direction.** No new hypotheses are proposed in
it.

---

## 6. Ledger entry

| screen | sample | outcome |
|---|---|---|
| **trade conditioning on pre-open variables** | **7 frozen trade sets, 152 subsets, 105 claimable** | **closed. 0 of 152 beat the random-label 95th percentile; observed global max t +2.263 vs bar +3.777 and vs permuted median +2.926 (empirical p 0.990). 95 of 105 claimable subsets positive, 1 survives the concentration rule, and that one fails the control. ORB-Fib subsets unresolvable on size.** |

Standing constraints honoured: **no new rule, nothing re-optimised**, sealed days
unread, **2016–2020 unread and unspent**. There remains nothing frozen that would
justify opening the holdout.

Reproduce: `python3 scripts/orderflow/trade_conditioning.py`.
Full output in `reports/trade_conditioning_output.txt`; per-subset detail in
`reports/trade_conditioning.csv`.
