# PROPOSAL — a rare, wide-stop intraday rule. Not approved, not run.

**Nothing in this file has been executed against expectancy.** The only
measurements taken so far are unconditional width distributions, used to size a
stop, and they are reported in §3 so the design inputs are visible.

**Sealed NQ days stay sealed. 2016–2020 stays unread.**

---

## 0. A data-quality finding, surfaced first because it touches two prior results

Sizing the stop required the overnight tape, and the overnight tape is dirty.

| hour (ET) | median 1-min bar range | 99.9th pct | max |
|---|---|---|---|
| 09–15 (RTH) | 4.4–7.6 bps | 42–155 bps | 1,805 bps |
| **16** | 1.7 bps | **1,218 bps** | **4,317 bps** |
| **17** | 1.1 bps | **1,498 bps** | 3,480 bps |
| 18–19 | 1.1–1.2 bps | 24–107 bps | 2,528 bps |

Post-close bars carry prints implying 43% moves. The consequence for the
overnight range, over 1,395 sessions:

| | raw high/low | print-cleaned (closes, local-median filter) |
|---|---|---|
| p50 | 187.5 bps | **88.9 bps** |
| p75 | 593.2 bps | **131.7 bps** |
| p95 | 1,252.3 bps | **234.4 bps** |
| **sessions above 400 bps** | **463 (33.2%)** | **10 (0.7%)** |

**A third of sessions had their overnight range set by a bad print.**

### What this does and does not change

- **`on_range` in the pre-open study (`32620b8`) was not cleanly tested.** Its
  rho +0.297 on realised volatility is partly a bad-print detector. It found
  nothing on the decision outcomes, and contamination adds noise rather than
  signal, so **the null does not reverse** — but that condition should be
  recorded as **"not cleanly tested"** rather than "tested and null".
- **`on_disp` is unaffected** — it reads a single 09:29 close, not an extremum.
- **In the conditioning run (`fb2b87e`), the one subset that passed all four
  bars was `on_range` top quartile.** That quartile is substantially the
  bad-print quartile. It failed the random-label control regardless, so **no
  verdict changes**, but that subset is now doubly discountable and the ledger
  should say so.
- **Any rule built on overnight extremes needs the print filter.** The rule
  proposed below therefore uses **RTH high/low only** and touches no overnight
  extremum.

---

## 1. The firing-rate budget, declared before the design

Available: **1,396 QQQ sessions**, 2021-01-05 → 2026-08-31, over **68 months**
= **20.5 sessions/month**. (The ledger's "1,418" is from an earlier, longer
source; the 1-minute file this rule must run on holds 1,396.)

| trades/month | % of sessions | total n over the window |
|---|---|---|
| 2 | **9.8%** | 136 |
| 3 | 14.6% | 204 |
| 4 | 19.5% | 272 |
| 5 | 24.4% | 340 |
| 6 | 29.3% | 408 |
| 10 | 48.8% | 680 |
| **15** | **73.2%** | 1,020 |

### The upper half of the declared band is not new

Everything already tested fired on 40–100% of sessions. **The IB family fired on
49% — which is 10 trades per month.** A rule at 10–15/month would reproduce
exactly the frequency profile that is closed.

**I propose targeting 3–6 trades per month (n = 204–408, 15–29% of sessions)**
— inside your band, in its lower half, and strictly rarer than anything tested.

### What that costs in resolution

The binding consequence, stated now: **at ~10% of sessions the rule must fire on
a single roughly-decile-rare condition, not on a four-way conjunction.** Any
conjunction of three or four demanding conditions lands at 1–3% of sessions, i.e.
0.2–0.6 trades/month, which is below your floor and unresolvable. **This is the
single hardest constraint on the design and it rules out most "demanding setup"
constructions before they are written down.**

---

## 2. Minimum detectable effect at that n, before proposing anything

A wide stop that is rarely hit compresses |R|, so the per-trade sd will be well
below the IB family's 0.72. Bracketed:

**Two-sided 95%, single variant:**

| n | sd 0.35 | sd 0.45 | sd 0.60 |
|---|---|---|---|
| 136 (2/mo) | ±0.059 | ±0.076 | ±0.101 |
| 204 (3/mo) | ±0.048 | ±0.062 | ±0.082 |
| 272 (4/mo) | ±0.042 | ±0.054 | ±0.071 |
| 340 (5/mo) | ±0.037 | ±0.048 | ±0.064 |
| 408 (6/mo) | ±0.034 | ±0.044 | ±0.058 |

**Bonferroni over 6 variants** (α = 0.00833, z = 2.638) inflates these by 1.35×:
at n = 272, sd 0.45, the bar is **±0.072 R**.

**In money, which is the point of the wide stop.** At a 250 bps risk container,
±0.072 R = **18 bps of price per trade**. The IB family's +0.061 R at ~70 bps
risk was **4.3 bps per trade**. So this rule needs a *larger* R edge but each
unit of R is worth ~3.5× more, and 272 trades × 18 bps ≈ 4,900 bps of total
required signal against the IB family's 685 × 4.3 ≈ 2,950. **This is a harder
test, not an easier one.** Stated before the design so it cannot be reframed
later.

**Concentration rule at these n:** max(10, ⌈0.10n⌉) removes 14 of 136 (10.3%),
21 of 204, 28 of 272, 34 of 340. The `max(10, ·)` arm does not bind above
n = 100, so the rule is a clean top-decile removal throughout.

---

## 3. The economic requirement, and the measurements that drove the design

Round-trip cost is **0.667 bps of price**. Cost as a share of risk is therefore
fixed entirely by the width of the stop:

| family | risk width | cost / risk |
|---|---|---|
| ATR-stopped families | 4–13 bps | **5–16%** |
| IB family | 57–87 bps | **0.77–1.16%** |
| **target for this rule** | **≥ 150 bps** | **≤ 0.44%** |

Unconditional prior-N-session RTH range widths (descriptive; no rule applied):

| N sessions | p25 | p50 | p75 | cost/risk at p25 / p50 |
|---|---|---|---|---|
| 2 | 157 bps | 219 | 306 | 0.42% / 0.30% |
| **3** | **203 bps** | **278** | **394** | **0.33% / 0.24%** |
| 5 | 276 bps | 380 | 530 | 0.24% / 0.18% |
| 10 | 411 bps | 567 | 769 | 0.16% / 0.12% |

### The design constraint this exposes, stated plainly

**A stop placed anywhere inside the current session cannot meet the target.**
I worked through and discarded two constructions on exactly this ground, before
writing any code:

1. **Overnight-extreme sweep and reclaim.** Stop at the sweep extreme ≈ 20–60
   bps → cost/risk **1.1–3.3%**, *worse* than the IB family. Rejected on design
   grounds.
2. **Stress-gap opening-drive failure**, stop at the 09:30–10:00 extreme. Entry
   sits ~half the gap from the extreme, so risk ≈ 75–100 bps → cost/risk
   **0.7–0.9%**. No better than the IB family. Rejected on design grounds.

**The stop must sit outside the session, at a multi-day structural level.** That
forces the trade to be a *continuation* — entered on the resolution of a range,
stopped at the range's far edge — because a fade entered near one edge has its
stop at the near edge and is necessarily tight. **The economics pick the
direction of the trade, not a preference of mine.**

---

## 4. THE RULE

### 4.1 Definitions

- **RANGE** = high/low of the **prior 3 RTH sessions**, excluding today.
  RTH only — the overnight tape is not touched, per §0. Width **W** in bps.
- **Compression** `k = W / (trailing 20-session mean of W)`, shifted so no
  session uses its own data.
- **D** = decision timestamp, 10:00 or 10:30 ET.

### 4.2 Trigger — all four required

1. **Compressed:** `k ≤ c`, where **c is the single calibration knob**, set by a
   counts-only pass (§5) that never reads R.
2. **Economically viable:** `W ≥ 150 bps`. This is the cost requirement written
   into the entry condition, not applied afterwards.
3. **Resolved:** at D, price is **outside** RANGE and the D bar **closed**
   outside. Direction = the side broken.
4. **Held:** the resolution is still intact at D — a break that has already
   reverted inside does not qualify.

### 4.3 Execution

- **Entry:** open of the bar **after** D. Entry bar excluded from the exit
  search. Honest fill primary, naive alongside. Lookahead counted.
- **Stop:** the **opposite edge of RANGE**, ±$0.01. Risk ≈ W plus the overshoot
  at entry.
- **Exit:** flat at **16:00 ET**. Same session in, same session out.

### 4.4 The six variants, fixed now

**3 exits × 2 decision timestamps = 6.** Nothing else is swept.

| | D = 10:00 | D = 10:30 |
|---|---|---|
| flat at 16:00 only | 1 | 4 |
| flat, or +0.5R target | 2 | 5 |
| flat, or +1.0R target | 3 | 6 |

`N = 3` sessions is **fixed, not swept** — chosen from the §3 table because
N = 2 gives 0.42% at p25 (not materially below the IB family) and N = 5+ widens
the risk container faster than it widens the expected move. Bonferroni
α = 0.05/6 = **0.00833**. The six share entries and are **not independent**.

### 4.5 The mechanism — why someone is on the other side

**Not a pattern description. A claim about who must trade and why.**

A compressed multi-day range means the auction has found balance and
**positioning has accumulated on both sides at a tight, commonly-referenced
pair of levels.** Two populations are then forced when it resolves:

1. **Mean-reversion providers who sold the top / bought the bottom of the
   range.** Their stops rest just beyond the edges. A stop is a market order —
   **price-insensitive supply or demand from a participant who is already
   wrong.** The tighter the range, the more of that positioning sits within a
   few bps of the edge.
2. **Option dealers short gamma across the balance area.** Above the range they
   must buy as price rises and sell as it falls. Their hedging is mechanical,
   non-discretionary, and in the direction of the move.

**Why the rare sessions are different:** in an uncompressed or trending market,
there is no accumulated two-sided positioning at a tight reference, so the same
break generates no forced flow — it is just price moving. **Compression is what
manufactures the counterparty.** That is the whole claim.

**It is falsifiable in two specific ways, both of which I will report:**
- The effect should be **larger at smaller `k`** (tighter compression → more
  concentrated positioning). If mean R does not increase as `k` falls, the
  mechanism is wrong even if the headline number is positive.
- The effect should **vanish for breaks that are not held to D** (condition 4
  removed). A "not-held" arm is run as a **mechanism control**, not as a
  seventh variant, and is reported whatever it shows.

### 4.6 The control that matters most here, declared now

A wide-stop, flat-at-close, long-biased rule on a rising index will show
positive mean R **from drift alone.** So:

- **Beta control (headline):** for every triggered session, the R of a
  long-always open-to-close hold using **the same risk denominator**. The rule's
  claim is **excess over that**, reported as the primary number.
- **Random-label control:** 5,000 permutations of the **trade direction** across
  triggered sessions with matched long/short counts, max-statistic bar at the
  95th percentile, as in `fb2b87e`.
- Standing instrumentation otherwise unchanged: clustered SEs by date,
  max(10, ⌈0.10n⌉), 4 of 6 years, ambiguous-bar rate.

---

## 5. The calibration pass, and the design-grounds rejection trigger

`c` is set by a pass that reads **counts and widths only — never R.** It reports,
for a ladder of `c`:

- sessions triggering, trades/month, total n
- **the realised cost/risk distribution** (median, p75, p90)
- the compression and width distributions of the triggered set

**`c` is then frozen at the value landing 3–6 trades/month**, and the expectancy
pass runs once against the frozen `c`.

> **Design-grounds rejection, declared now:** if the realised **median cost/risk
> at the frozen `c` is not below 0.50%**, the rule is **rejected before the
> expectancy pass runs** and reported as such. It would mean the selectivity is
> not buying a wider stop, which is the entire economic premise.

---

## 6. The concentration caveat, recorded in the ledger as you asked

> **max(10, ⌈0.10n⌉) is close to a tail-independence requirement and rejects
> convex, tail-driven payoffs by construction. A selective rule is more likely
> than a frequent one to be convex.**

Recorded. Two things to add, one of which cuts against my own design:

- **This particular rule is deliberately the non-convex kind.** A stop at a
  multi-day far edge is rarely reached, so the payoff is closer to
  truncated-linear than to a lottery. **That partly defuses the caveat — and it
  also means passing the concentration rule here is weaker evidence than it
  would be for a convex rule**, because a non-convex payoff is expected to pass.
  I would rather say that now than claim the pass as a strength later.
- **If a variant fails only on concentration** while clearing cost, expectancy,
  4-of-6 years and the control, it is **reported separately, not closed**, with
  the full profile: the R distribution, the top-decile share of total R, mean R
  after removing 1/5/10/20 trades, and the per-year breakdown — so you can judge
  whether the concentration is a fat right tail (possibly real) or two lucky
  sessions (not).

---

## 7. What I am asking you to approve

| | |
|---|---|
| target firing rate | **3–6 trades/month** (n = 204–408), your band's lower half |
| one rule | compressed 3-session range, resolved and held at D |
| variants | **6** (3 exits × 2 decision timestamps), N = 3 fixed |
| headline economic number | **cost/risk**, required median **< 0.50%**, expected ~0.33–0.44% |
| calibration | counts-and-widths only, `c` frozen before any R is read |
| headline performance number | **excess over a long open-to-close hold at the same risk** |
| kill switch | rejected on design grounds if cost/risk ≥ 0.50% at the frozen `c` |

**Not run. Awaiting your approval.** Two alternative constructions were already
rejected on the cost/risk requirement before reaching code (§3), which is the
filter working as you specified.

---

# AMENDMENT 1 — approved, declared before the calibration pass ran

Approved at 3–6 trades/month, six variants. Two amendments from you, and one
correction of my own that they forced into view.

## A1.1 Excess over buy-and-hold is the headline in every table

`excess_R` is printed first in every table; raw `R` is reported beside it, never
in front of it.

## A1.2 Long and short arms reported separately from the outset

Every table carries LONG, SHORT and BOTH rows. The pooled row is printed last,
and the per-arm rows are never suppressed in favour of it. If one arm carries
the result entirely, that is visible before pooling.

## A1.3 A correction: my proposed benchmark was wrong for the short arm

The proposal (§4.6) defined the benchmark as *"the R of a long-always
open-to-close hold using the same risk denominator"*. **That definition is wrong
once the short arm is reported separately**, and it only became obvious when
A1.2 forced the two arms apart.

For a short trade held to the close with no barrier, `R = −(close − entry)/risk`,
which is exactly minus the long hold. Subtracting a *long* benchmark would give
`excess = R − bh = −2 × bh` — it would double the session's realised move rather
than remove drift, and would mechanically reward the short arm on down days and
punish it on up days. It is not a drift control at all.

**The corrected definition, used from here:**

```
drift_D  = mean over ALL 1,396 sessions of (close_16:00 − price at entry clock D+1)
excess_R = R − d × drift_D / risk
```

`drift_D` is an **unconditional constant per decision timestamp**, not the
triggered session's own move. It subtracts exactly the expected profit of a
directional position of sign `d`, sized `1/risk`, held over the same clock
window. A long-biased rule on a rising index has its drift removed; a
short-biased rule has it added back, which is the correct sign.

Declared limitations: `drift_D` is a full-sample constant and therefore in-sample.
It is a benchmark, not a predictor, so this does not leak — but it is stated.

**The same-session long hold is retained as a second diagnostic**, labelled
`vs_hold`, because it answers a different and still useful question: did the
stop, target and timing add anything over passive exposure on the same days.
It is a diagnostic, not the headline.

## A1.4 Both mechanism controls run regardless of outcome

1. **Effect must grow as `c` falls.** Mean `excess_R` by compression bucket
   within the triggered set, and across a nested ladder of `c`. Reported
   whatever it shows. `c` is already frozen before this runs, so the ladder is
   a mechanism check, not a sweep.
2. **Effect must vanish for breaks not held to D.** Sessions that broke the
   range before D but had reverted inside by D, traded identically in the
   direction of the earlier break. Reported whatever it shows.

## A1.5 Unchanged

Calibration on counts and widths only, `c` frozen before any R is read, and the
design-grounds rejection if realised median cost/risk ≥ 0.50% at the frozen `c`.
Sealed days unread, 2016–2020 unread.
