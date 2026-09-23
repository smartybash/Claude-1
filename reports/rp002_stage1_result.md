# RP-002 Stage 1 — descriptive mechanism test

Pre-registered `1a65e8c`. Discovery block only: QQQ 2021-01-04 → 2024-12-31.
**The 2025-01 → 2026-08 internal validation block was not read.** No expectancy,
no profit factor, no P&L, no evaluation simulation.

**940 usable sessions, 45 months.** 60 sessions consumed by the causal 60-session
warm-up for the `q` percentile.

---

## 1. Data quality and cleaning impact — the estimator I proposed is wrong

| | raw | cleaned |
|---|---|---|
| mean overnight range | 117.6 bps | **91.7 bps** |
| sessions where cleaning changed the range | — | **922 of 940 (98.1%)** |
| range shrink, median / p90 / p99 / max | — | 8.2 / 65.6 / 239.2 / 791.8 bps |

**This is a specification failure and it is mine.** I proposed the two-bar
confirmation rule as "mildly conservative on clean sessions" and told you it
"targets the documented defect exactly." It does neither. The maximum of ~330
overnight bar highs is almost never tied, so the second-largest value is almost
always strictly below it — **the rule removes the genuine extreme on virtually
every session**, not just contaminated ones, and cuts 22% off the mean range.

A correct bad-print filter needs a **magnitude** test — is the extreme far from
its neighbours — not a **count** test. In trying to eliminate a tunable
parameter I introduced a systematic bias that is worse than the parameter would
have been.

**The rule was frozen and I have not changed it.** Two consequences, stated
rather than buried:

- All states use the same estimator, so **the S1/S3/S4 comparisons below are
  internally consistent.** The null they produce is not an artefact of cleaning.
- Absolute range figures are biased ~22% low, and `loc` is computed against a
  shrunken range, making "outer third" marginally easier to reach. State
  assignment is affected in level, not in the comparison.

Kill condition 7 asks whether cleaned and raw differ enough to show dependence
on bad prints. They differ enormously — but because of estimator aggressiveness,
not contamination. **The bad-print question is unresolved, not answered.**

---

## 2. State counts and monthly frequency

| state | n | /month | long | short | ON range bps | 15-min extend % |
|---|---|---|---|---|---|---|
| **S1** | **253** | **5.62** | 147 | 106 | 131.1 | 46.6 |
| S2 | 214 | 4.76 | 114 | 100 | 82.4 | 50.5 |
| S3 *(inventory control)* | 102 | 2.27 | 47 | 55 | 65.9 | 47.1 |
| **S4** *(location control)* | **36** | **0.80** | 16 | 20 | 112.2 | 41.7 |
| S5 | 98 | 2.18 | 50 | 48 | 78.5 | 49.0 |
| S6 | 122 | 2.71 | 63 | 59 | 69.8 | 48.4 |
| RESID *(opposite outer third)* | 115 | 2.56 | 65 | 50 | 73.6 | 51.3 |

S1 fired on **26.9%** of sessions against the 23% projected — the pre-declared
firing estimate was well calibrated.

**Two structural problems.**

**S4 has 36 sessions.** The location control — the single most important control
in this design, because it holds overnight inventory fixed and moves only the
open — **is too small to test anything.** Its numbers below are noise.

**The opposite-outer residual is 12.2% of sessions.** As flagged before running,
location has three bins, not two; folding these into "middle" would have
contaminated S4 further. They are reported, not merged.

**S1 at 253 sessions is below the 300-session Stage 2 threshold** set in the
original §7.

---

## 3. S1 versus its controls

| state | n | ON rng | ret15 | ret60 | 09:44→10:59 | RV h1 | MFE | MAE | MFE45 | MAE45 | touch ONhi | touch ONlo | touch prev close | gap ≥50% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1** | 253 | 131.1 | −3.3 | **−1.0** | **−0.3** | 58.5 | 79.6 | 97.3 | 77.4 | 88.7 | 63.6 | 59.3 | **37.9** | **61.7** |
| S3 | 102 | 65.9 | −0.2 | +2.0 | −1.0 | 47.8 | 77.9 | 79.1 | 73.3 | 74.2 | 74.5 | 73.5 | 87.3 | 95.0 |
| S4 | 36 | 112.2 | +0.1 | +5.3 | +11.7 | 66.1 | 103.7 | 104.6 | 97.4 | 92.7 | 66.7 | 63.9 | 47.2 | 63.9 |
| MATCHED | 234 | 114.6 | −2.2 | −6.9 | −1.7 | 69.4 | 94.2 | 103.9 | 91.1 | 95.9 | 65.8 | 65.4 | 73.1 | 85.4 |

Returns and excursions in bps, direction-adjusted so positive = in the overnight
direction. Frequencies in %.

**Directionally there is nothing.** S1's first-hour return is **−1.0 bps** and
its post-09:45 return is **−0.3 bps**. The volatility-matched control gives −6.9
and −1.7. All four are indistinguishable from zero and from each other.
**Kill condition 4 is met: the effect does not survive matching on overnight
volatility, because there was no directional effect to survive.**

**The one large separation is gap behaviour, and it is an identity.** S1 touches
the prior cash close on **37.9%** of sessions against S3's **87.3%**. But S3 is
*defined* as the small-overnight-move tier — its mean range is 65.9 bps against
S1's 131.1. A small gap is arithmetically easier to fill. This is the same
geometric identity that appeared in the IB family, where `P(break) ≈ (100 − EZ)%`
turned out to be a restatement of the condition rather than a finding.

The matched control is the fairer comparison and still shows 73.1% against 37.9%
at a similar range — but matching was on **overnight range**, not on **gap
size**, and S1 requires the open near the extreme, which mechanically implies a
larger gap. The separation remains a consequence of the conditioning, not a
behavioural difference.

**S1's excursion profile is mildly adverse**: MFE 79.6 against MAE 97.3, i.e.
price travels *against* the overnight direction more than with it. The matched
control does the same (94.2 / 103.9). Not specific to S1.

---

## 4. Continuation versus rejection — the separation is circular

Never pooled, per the ruling. They are opposite hypotheses.

| branch | n | /month | long | short | ret15 | ret60 | **09:44→10:29** | **09:44→10:59** | MFE45 | MAE45 | touch prev | gap ≥50% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1-EXTEND** | 118 | **2.62** | 66 | 52 | **+26.6** | +31.3 | **+4.7** | **+6.4** | 82.0 | 77.7 | 21.2 | 43.2 |
| **S1-REJECT** | 135 | **3.00** | 81 | 54 | **−29.5** | −29.3 | **+0.1** | **−6.2** | 73.3 | 98.4 | 52.6 | 77.8 |

**The headline `ret60` separation of +31.3 against −29.3 is an artefact of the
construction.** The branch is *defined* by the sign of the 09:30→09:44 return,
and `ret60` is measured from 09:30, so it contains the conditioning window:

- EXTEND: of the +31.3, **+26.6 is the first fifteen minutes** — 85% of it.
  The residual after the conditioning window closes is **+4.7**.
- REJECT: of the −29.3, **−29.5 is the first fifteen minutes** — all of it.
  The residual is **+0.1**.

**The only non-circular measures are the ones anchored at 09:44.** There:
**+6.4 bps and −6.2 bps.** Near-perfect mirror images of each other, which is
kill condition 3 almost exactly — the two branches cancel and neither dominates.

**Frequency after the mandatory split is the decisive commercial fact.**
2.62/month and 3.00/month. **Both below the 4/month floor**, and pooling them is
barred because they are opposite hypotheses, not the same mechanism. **Kill
condition 6 is met.**

---

## 5. Yearly stability

Post-09:45 window only — the circular measure is not worth tabulating by year.

| branch | 2021 | 2022 | 2023 | 2024 | all | **excluding 2022** |
|---|---|---|---|---|---|---|
| S1-EXTEND | −7.5 (n19) | **+21.6** (n31) | +2.2 (n29) | +4.4 (n39) | +6.4 | **+1.1** |
| S1-REJECT | +9.3 (n24) | **−21.0** (n36) | −5.2 (n35) | −3.1 (n40) | −6.2 | **−0.8** |

**The effect is 2022.** Each branch has one wrong-signed year (2021 for both),
and removing the single high-volatility year collapses both to **≈1 bp** —
roughly 1.5× the NQ round-trip cost, on a measure that has not been charged any
cost at all. **Kill condition 5 is met: the effect is not present in four
calendar years.**

---

## 6. Commercial interpretation

The hypothesis was that a material overnight imbalance plus an open near the
corresponding extreme creates forced rebalancing with a tradeable directional
consequence. Descriptively:

- **The state is real and fires at a usable rate.** S1 at 26.9% of sessions,
  5.62/month, close to the 23% projected.
- **It has no directional consequence.** −1.0 bps over the first hour, −0.3 bps
  after 09:45, against a volatility-matched control at −6.9 and −1.7.
- **Its apparent continuation/reversal split is 85–100% the conditioning
  window.** After 09:44 the branches are ±6 bps, they mirror each other, and
  ex-2022 they are ±1 bp.
- **Neither branch reaches 4 trades per month**, and they cannot be pooled.
- **The location control could not be run** — 36 sessions.
- **The only large difference is gap-fill frequency, and it restates gap size.**

The requirement was explicit: a difference consisting only of higher volatility
does not pass; the family must show a difference in directional path, excursion,
gap behaviour, or level interaction. S1 does show higher volatility (RV 58.5 vs
S3's 47.8) and a lower gap-fill rate — **and both are arithmetic consequences of
conditioning on a large overnight move.** The directional path and the excursion
ratio do not separate from the matched control.

This is §3.5 of the ledger once more, now at the opening auction: the *size* of
the overnight move predicts the *size* of what follows, and nothing predicts its
**direction**.

**Kill conditions met: 3 (branches cancel, no dominant), 4 (no effect survives
volatility matching), 5 (not present in four years), 6 (both branches below
4/month).** Any one closes the family; four together leave no ambiguity.

---

## Appendix — formal detail

| branch | mean (bps) | sd | SE | t |
|---|---|---|---|---|
| S1-EXTEND, 09:44→10:59 | +6.4 | 57.9 | 5.3 | **+1.21** |
| S1-REJECT, 09:44→10:59 | −6.2 | 69.2 | 6.0 | **−1.04** |

Neither reaches a single-test threshold before any multiplicity correction, and
no correction has been applied because none is needed to reach the verdict.

Matched control: for each S1 session, one non-S1 session drawn without
replacement whose cleaned overnight range lies within ±10% of the S1 session's;
234 of 253 matched; seed 20260923. Residual range mismatch 131.1 vs 114.6 bps
means the match is imperfect **in S1's favour**, and S1 still shows no effect.

---

# VERDICT: MECHANISM REJECTED — CLOSE RP-002

No Stage 2 proposal follows. No NQ data is to be acquired. No ETF extended-hours
data is to be acquired. The spend was one discovery pass on data already held,
which is what the staged gate was designed to achieve.

**The cleaning-estimator failure in §1 is recorded separately in the correction
ledger.** It did not cause this verdict, but it would have contaminated any
Stage 2 that followed, and a future overnight-range family must not reuse it.
