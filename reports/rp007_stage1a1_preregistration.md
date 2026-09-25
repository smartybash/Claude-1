# RP-007 Stage 1A1 — broad level validity on QQQ
## Pre-registration. **Not run.** Written before any level was computed.

A **price-only screen**. No footprint, no delta, no volume condition, no
absorption threshold, no trading rule, no P&L, no expectancy, no drawdown.

**Purpose:** reduce fifteen declared level families to **at most three** that
show non-arbitrary rejection behaviour on a large sample. It is **not** a
validation of an NQ strategy and cannot become one. QQQ is never final evidence
for an MNQ strategy, at this stage or any later stage.

**Sample: QQQ one-minute, 2021-01-04 → 2026-08-31, 1,421 RTH sessions.
Discovery only.** Never presentable as validation at any stage.

---

## 1. The multiple-testing burden and the MDE, stated before results

**Primary outcome, declared now and not changed afterwards: *reclaim within 10
minutes*, binary.** It is the middle of the declared ladder, long enough to be
resolvable on one-minute bars and short enough to be a rejection rather than a
drift.

**Primary test grid: 15 families × 2 sides (support, resistance) = 30 tests.**
Controls are not additional tests; they are the comparison within each test.
Everything else in §7 is descriptive and carries no claim.

**Bonferroni over 30: α = 0.00167, z = 3.144.**

Minimum detectable difference in reclaim rate, 80% power, p ≈ 0.5:

| comparison | genuine n | control n | α = 0.05 | **α = 0.00167** |
|---|---|---|---|---|
| family pooled vs the four shifted arms | ~600 | ~2,400 | 6.4 pts | **±9.1 pts** |
| family, one side, vs the four shifted arms | ~300 | ~1,200 | 9.0 pts | **±12.9 pts** |
| family pooled vs the random pool | ~600 | large | 5.7 pts | **±8.1 pts** |
| family, one side, vs the random pool | ~300 | large | 8.1 pts | **±11.5 pts** |
| *for contrast:* NQ at 50 sessions, family pooled | ~20 | ~80 | 35.0 pts | **±49.8 pts** |

Genuine n is taken from the touch counts already measured in
`levels_predictive_result.md` (468–661 first touches per prior-day family over
1,414 sessions). Families that touch more often — current-session VWAP, the IB
levels, round prices — will have larger n and a smaller MDE; that will be
reported per family rather than assumed.

**What this means, written down before the numbers exist:** Stage 1A1 can detect
a level family that reclaims **9 points more often than a price shifted away from
it**. It cannot detect a 3-point effect, and a 3-point effect would not be worth
trading anyway. The last row is why this screen is on QQQ.

---

## 2. Prior, and the burden requirement 7 places on five families

Five of the fifteen have already been tested on essentially this sample.
`levels_predictive_result.md`, 1,414 QQQ sessions: PDH 44.8%, PDL 48.1%,
VAH 47.2%, VAL 51.5%, POC 49.0% reaction at 30 minutes against a 50% null and a
55% bar. **0 of 8.** The one lean, PDH at 44.8%, points against the folk belief.

RP-007 differs in three ways that make re-asking legitimate: a **shifted-price
control** that study did not have, a **reclaim-and-rotation** outcome instead of
"which side of the level", and a **geometric-strata** test. Those are real
additions. They do not erase 1,414 sessions of null.

**Requirement 7 — "adds information not already contained in the earlier QQQ
level study" — therefore binds hardest on exactly these five.** For PDH, PDL,
VAH, VAL and POC, requirement 7 is satisfied only if the family's advantage over
shifted controls survives **and** the earlier study's null is explained by its
different outcome definition rather than contradicted by a smaller sample. Any
other reading would be re-testing until something passes.

**My prior remains against.** I expect zero or one family to advance.

---

## 3. Instrument-native constants — frozen here, derived from the NQ definitions, never transferred as absolute points

No NQ point value appears anywhere in the QQQ computation. Each NQ constant is
converted to a **dimensionless ratio** and the ratio is what is frozen.

### 3.1 Volatility unit

**ATR₁ₘ(D) = the mean one-minute true range of the previous RTH session.**

Causal by construction — it is known before session D opens, uses no bar from
session D, and is a single number per session. Sessions whose previous RTH
session is not in the sample contribute nothing and are reported as exclusions.

Measured, for scale only:

| | QQQ | NQ |
|---|---|---|
| mean 1-minute true range | **$0.2945** | 20.9 pts (implied) |
| as bps of price | **7.04** | 7.07 |

The two instruments agree to three hundredths of a basis point, which is the
single best justification available for screening on one and confirming on the
other.

### 3.2 Zone

| quantity | frozen value |
|---|---|
| **θ (zone full width ÷ ATR₁ₘ)** | **0.1435** |
| derivation | NQ 3.00 points ÷ 20.9 points |
| **zone** | `level ± (θ/2) × ATR₁ₘ` = `level ± 0.0718 × ATR₁ₘ` |
| QQQ, pooled illustration | full width **$0.0423**, half **$0.0211** |
| QQQ 2021 / 2026 illustration | $0.0295 / $0.0636 |

**One width. No sweep.** The zone breathes with volatility, which is the point:
a fixed dollar zone would be relatively three times wider in 2021 than in 2026
and would confound the year-consistency test with a price-level trend.

### 3.3 Shifted controls

**`level ± (10/3) × W` and `level ± (20/3) × W`**, where `W = θ × ATR₁ₘ`.

Exactly the NQ geometry: NQ shifted at 10 and 20 points against a 3.00-point
zone, so 10/3 and 20/3 zone widths. Equivalently **±0.4785 × ATR₁ₘ** and
**±0.9569 × ATR₁ₘ**. Four arms per genuine interaction.

**Contamination rule, declared now:** a shifted price whose zone overlaps any
genuine declared level's zone, or any cluster's zone, is **excluded from the
control arm and labelled**, never treated as arbitrary. Both counts — generated
and surviving — are reported before any outcome. If the near shifts lose a large
fraction, that is a finding about how crowded the level universe is and it is
reported as one.

### 3.4 Round prices

**$2.50, fixed.**

Chosen to match NQ's *density*, not its price. NQ's 100-point grid puts
`282 ÷ 100 = 2.82` round levels inside a mean RTH range. On QQQ:

| interval | round levels per mean RTH range |
|---|---|
| $1.00 | 6.69 |
| **$2.50** | **2.68** |
| $5.00 | 1.33 |
| $10.00 | 0.67 |

$2.50 is the closest match and is a number a participant plausibly watches. Per
year density is 3.0 (2022) to 4.0 (2026) and will be reported, since QQQ's price
roughly doubles across the sample.

### 3.5 Economic hurdle, in ATR units

Deployment is **MNQ**, round turn ≈ 2.0 NQ points (one tick spread each way plus
commission). The 3× bar is 6.0 NQ points = **0.287 × ATR₁ₘ**.

**The rotation hurdle is therefore `0.287 × ATR₁ₘ`, a dimensionless quantity.**
On QQQ that is $0.0845, or 1.94 bps. **This is a screening threshold expressed in
volatility units, not a claim about QQQ P&L**, and no QQQ profit figure is
computed anywhere in Stage 1A1.

---

## 4. The fifteen families on QQQ

Sessions: **RTH `[09:30, 16:00)`**. Extended hours: **`[16:00, 20:00)` on D−1
and `[04:00, 09:30)` on D**, from `QQQ_1m_eth.parquet`. **Initial Balance
`[09:30, 10:30)`.**

| # | family | computation |
|---|---|---|
| 1 | prior RTH high | `max(high)` over the previous RTH session |
| 2 | prior RTH low | `min(low)` |
| 3 | prior RTH close | close of the 15:59 bar |
| 4 | prior RTH VWAP | `Σ(typical × volume)/Σ(volume)`, typical = `(H+L+C)/3`, previous RTH session |
| 5 | prior VAH | §4.1 |
| 6 | prior VAL | §4.1 |
| 7 | prior POC | §4.1 |
| 8 | **extended-hours high** | `max(high)` over `[16:00 D−1, 20:00 D−1] ∪ [04:00 D, 09:30 D]` |
| 9 | **extended-hours low** | `min(low)` over the same |
| 10 | **extended-hours midpoint** | `(8 + 9)/2` |
| 11 | IB high | `max(high)` over `[09:30, 10:30)` |
| 12 | IB low | `min(low)` over the same |
| 13 | IB midpoint | `(11 + 12)/2` |
| 14 | current-session VWAP | causal: at bar *t*, over `[09:30, t]` inclusive of *t*, nothing after |
| 15 | round prices | every multiple of **$2.50** |

### 4.1 Value area

Histogram of the previous RTH session's **one-minute volume assigned to the
bar's typical price `(H+L+C)/3` rounded to $0.01**. POC = highest-volume price;
ties broken toward the session's volume-weighted mean, then to the lower price.
**70%**, conventional two-price-pair expansion: from the POC, repeatedly compare
the two prices above against the two below and annex the larger pair, ties to the
upper pair, until the region holds ≥70% of session volume. VAH and VAL are its
extremes.

**Bar-level volume attribution is an approximation of a tick histogram**, and it
is a known limit of doing this on QQQ rather than on tape. It is declared here,
and it is one of the things Stage 1A2 re-does natively.

### 4.2 Families 8–10 are the least comparable of the fifteen

QQQ has **no overnight auction**. The window above is US pre and post market
with a **20:00–04:00 hole** where nothing trades and price can move on futures
that QQQ never prints. An "extended-hours high" is genuinely a different object
from NQ's continuous 22:00–13:30 UTC auction.

They are included, because the ruling includes them, and they are **labelled
extended-hours throughout — never "overnight"**. If one of them advances it
carries a standing caveat and needs Stage 1A2 more than any other family.

Coverage: extended-hours data exists for 1,399 of 1,421 sessions. **The 22
missing are exactly June 2026 plus 2026-07-23** — the QQQ extended-hours fetch
already honours the NQ seal. Those sessions contribute no families 8–10 and are
reported as exclusions.

### 4.3 Eligibility and duplicates

* Families 1–7 need a previous RTH session in the sample; families 11–13 are not
  eligible before 10:30; family 14 from the first bar.
* **Exact duplicates collapse to one price carrying both labels.** Never counted
  twice.
* A level outside the session's traded range is counted in "levels available"
  and never in "interactions".

---

## 5. Interaction, reclaim, rotation

### 5.1 Interaction

The first bar whose `[low, high]` intersects the zone, having **not** intersected
it on the previous bar. **Approach side** is the side price occupied on the last
bar strictly outside the zone: from below → **resistance** test; from above →
**support** test. The label comes from the approach, never from the family's
name — a prior-day high approached from above is a support test and is counted
as one.

### 5.2 The four ambiguous cases, resolved in advance

| case | rule |
|---|---|
| **session opens inside the zone** | **no interaction on that approach.** There is no approach side; assigning one is a coin flip the outcomes would inherit. Re-eligible once price leaves by ≥ one full zone width and returns. Counted and reported. |
| **price gaps across the zone** | consecutive bars straddle without intersecting → recorded as **`CROSSED`, not an interaction**, reported with its own count. The level was never tested. Re-eligible on any later return. |
| **several levels overlap** | **one cluster, one interaction** against the cluster mean (§8). Never one each. |
| **multiple zones in the same bar** | on one-minute bars intra-bar order is **undefined**. Both are recorded, each against its own cluster, and **both are flagged simultaneous**. The flagged subset is reported separately and excluded from the primary test. |

### 5.3 First versus repeated

At most one counted interaction per cluster until price moves **≥ one full zone
width** beyond the zone boundary and later returns. First = the first qualifying
interaction with that cluster that session; repeated = the 2nd, 3rd, … each
numbered. Counts reset at the RTH boundary.

**First interactions are the primary sample. Repeated interactions are measured
identically and reported separately, never pooled** — pooling would hide the
exact gradient requirement 4 tests for.

### 5.4 Outcomes

All measured in **ATR₁ₘ units** as well as in dollars and bps, so nothing depends
on QQQ's price level.

For a **support** interaction (mirrored exactly for resistance):

* **maximum excursion below the zone**, bars 1 → 30 after the interaction;
* **reclaim within 1, 3, 5, 10, 15 minutes** — price closes back above the zone's
  upper boundary having been below its lower boundary;
* **rotation above the zone after reclaim** — binary;
* **rotation distance at 5, 10, 15, 30 minutes** from the zone's upper boundary;
* **maximum favourable rotation** and **maximum adverse excursion**, 30 bars.

**One-minute resolution limit, declared:** the 1-minute reclaim figure is
bar-resolution-limited — the zone is roughly one fifth of a single bar's range —
and the bar-resolution gate already measured that **23.5% of tick-level trades
open and close inside one minute**. The 1-minute column is reported as a
diagnostic and is **not** a gate. Gates use 3, 5, 10 and 15.

### 5.5 Reporting splits

Each level family · support and resistance · isolated and confluence · first and
repeated · **by calendar year** · by session period (09:30–11:00, 11:00–14:00,
14:00–16:00). Counts before performance, in every table.

---

## 6. Controls

**Four shifted arms** (§3.3), following the identical interaction, reclaim and
rotation definitions, with the contamination rule applied and reported.

**Matched random control.** For each genuine interaction, a random price from the
**same session**, matched simultaneously on:

| axis | tolerance |
|---|---|
| interaction time | ± 30 minutes |
| trailing 30-minute realised volatility | ± 10% |
| distance from the RTH open | ± 10% |
| **relative location inside the session range observed so far** | ± 0.05 |

**200 draws per genuine interaction, fixed seed, reported as a distribution
(mean, sd, p5, p95), never as a single draw.** RP-006 is the reason this is
specified rather than assumed: a single draw is not a control, and a control
whose construction makes it mechanically similar to the true arm is worse than
none.

Interactions with no admissible candidate are reported as **unmatched** and are
excluded from the random comparison only.

**Geometric-strata test (the §12 requirement).** Every genuine and control
observation carries `(relative location in range, distance from price at
interaction, time of day, trailing 30-minute volatility)`. The genuine-minus-
control difference is reported **within matched strata** as well as pooled.

> **If the pooled advantage disappears inside strata, the family is reported as
> explained by starting geometry and it fails — regardless of the pooled number.**

Written down now so that a pooled positive cannot later be defended as
"directionally right".

---

## 7. Confluence — descriptive only at this stage

The declared definition is kept: **two or more levels whose zones overlap**,
transitive closure, cluster reference price = unweighted mean, **zone does not
widen with membership**, contributing families named, no subjective weights.
Buckets: isolated / 2-level / 3-or-more.

**Confluence is descriptive until an isolated family has first shown validity.**
A confluence claim requires **all three**:

1. at least one member family already valid **alone**;
2. cluster performance better than **matched isolated** interactions;
3. comparable geometry and time of day.

**Clusters may not create a positive result by combining individually invalid
levels.** If no family passes alone, confluence is reported as counts only and
nothing is claimed from it.

---

## 8. Selection rule — a family advances only if all seven hold

1. Genuine levels beat **both** shifted and random prices.
2. The advantage **survives within matched geometric strata**.
3. The effect exists for **support and resistance**.
4. **First interactions outperform repeated** interactions.
5. The result appears across **at least four calendar years** (of 2021–2026;
   2026 is 8 months and is counted as a year only if it qualifies on its own).
6. **Expected NQ frequency could plausibly exceed four eventual trades per
   month** after absorption and reclaim filters (§9).
7. The family **adds information not already contained** in the earlier QQQ level
   study (§2, and the heavier burden it places on families 1, 2, 5, 6, 7).

Statistical significance is judged at **α = 0.00167** (§1). A difference below
the family's own MDE is **unresolvable**, not a pass and not a fail — and it is
reported as unresolvable rather than rounded into either.

**At most three families advance.**

### 8.1 Frozen commercial score, for ranking only if more than three qualify

Declared now so it cannot be tuned to a preferred survivor. Each component is
**rank-normalised across qualifying families to [0, 1]**, then weighted:

| component | weight |
|---|---|
| rotation advantage over controls, at 30 minutes, in ATR₁ₘ units | **0.35** |
| frequency (first interactions per session) | **0.20** |
| support / resistance balance — `1 − |support − resistance| ÷ (support + resistance)` on the primary outcome | **0.20** |
| year consistency — fraction of eligible years in which the advantage is positive | **0.15** |
| first-interaction advantage over repeated | **0.10** |

Ties are broken by frequency, then by the number of qualifying years.

**Selection is by this score. It is explicitly not by the largest isolated
result**, and the largest single number in the study carries no weight of its
own.

### 8.2 If no family qualifies

**RP-007 closes without NQ being used.** No re-specification, no relaxed zone, no
extra horizon, no fourth family admitted on appeal. The preserved NQ sessions
remain preserved and unspent for a future family.

---

## 9. Expected NQ frequency (requirement 6)

Requirement 6 is arithmetic, declared here and evaluated after the QQQ counts
exist:

```
NQ trades/month = (QQQ first interactions per session for this family)
                × 21 sessions
                × r_absorption
                × r_reclaim
```

`r_absorption` and `r_reclaim` are the retention rates of Stage 1B and Stage 1C.
**They are not defined yet and must not be.** Requirement 6 is therefore tested
against a **declared reference retention of 1/3 combined**, stated now:

> A family passes requirement 6 if it produces **≥ 12 first interactions per
> month** on QQQ, so that a one-third combined retention still leaves four
> trades per month.

One-third is generous. It is chosen to be generous on purpose, because failing
requirement 6 at a generous retention is decisive while passing it at a generous
retention is not.

---

## 10. What Stage 1A1 cannot do, stated in advance

* It cannot validate anything. QQQ 2021–2026 is **discovery only**, forever.
* It cannot see sub-minute path. 23.5% of tick-level activity is invisible to it.
* It cannot test overnight behaviour, because QQQ has none.
* It cannot establish that a surviving family works on NQ. That is Stage 1A2, it
  is a **mechanism confirmation and not a performance test**, and the nine sealed
  sessions are a **falsification check** — they are not validation, not
  confirmation, and will not be described as either.
* **No 12-month NQ out-of-sample block exists.** Any candidate surviving Stage 1C
  requires forward collection through **at least September 2027** and **at least
  150 frozen-rule trades** before prop deployment. QQQ is never final evidence
  for an MNQ strategy.

---

## 11. Declared before approval

No level was computed. No interaction was counted. No outcome was measured. No
sealed date was opened. 2016–2020 remains spent and unused. No absorption,
delta, volume or footprint threshold is defined anywhere in this document, and
**Stage 1B remains unauthorised** — it opens only if a family survives both the
QQQ screen and NQ confirmation.

Every constant in §3 is frozen: **θ = 0.1435**, shifts at **10/3** and **20/3**
zone widths, round interval **$2.50**, primary outcome **reclaim within 10
minutes**, **α = 0.00167**, requirement-6 reference **12 first interactions per
month**, commercial-score weights **0.35 / 0.20 / 0.20 / 0.15 / 0.10**.

None of them will be varied during or after the run.
