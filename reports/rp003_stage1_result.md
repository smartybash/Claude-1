# RP-003 Stage 1 — QQQ/SPY beta residual behaviour

Descriptive only. **No P&L, profit factor, drawdown, entries, stops or targets.**

**Discovery block 2021-01-04 → 2022-12-31 ONLY. 2023 and 2024–2025 were not
read, and under the approved sequence rule they must not be** — discovery failed
its gate.

All twelve frozen definitions applied unchanged. No threshold, lookback,
formation window, normalisation or cooldown was varied.

---

## 1. Counts first

| | n | per month | positive | negative | mean \|R\| |
|---|---|---|---|---|---|
| **EXTREME** \|z\| ≥ 2.0 | **1,019** | **44.30** | 513 | 506 | 20.85 bps |
| ORDINARY 0.5 ≤ \|z\| < 1.0 | 2,870 | 124.78 | 1,417 | 1,453 | 5.70 bps |

500 aligned sessions, **3 dropped** below 380 bars, 20 consumed by beta warm-up,
**480 usable across 23 months**. Signal availability by horizon: h5 1,002 ·
h15 986 · h30 968 · h60 939.

**Realised frequency of 44.30/month against my declared design estimate of
15–25.** I under-estimated by roughly 2×. It was declared as a design estimate
and not a pass condition, and the threshold was not touched — but the miss is
recorded. Cause: residual z is fatter-tailed than normal and signals cluster
heavily at the open.

| time-of-day | EXTREME n | share |
|---|---|---|
| 09:30–11:00 | 603 | **59.2%** |
| 11:00–14:00 | 288 | 28.3% |
| 14:00–16:00 | 128 | 12.6% |

By year: 2021 n=493 (42.87/mo) · 2022 n=526 (45.74/mo). Causal beta averaged
**1.2376** (sd 0.0898, range 1.03–1.44).

**Frequency is the one gate condition RP-003 passes**, and it passes the
standalone 12/month bar by a wide margin.

---

## 2. Contraction — EXTREME versus ORDINARY

Positive = movement toward zero. Basis points.

| set | h | n | mean | median | % of residual closed | any contraction | ≥25% | ≥50% | ≥100% | max adverse |
|---|---|---|---|---|---|---|---|---|---|---|
| **EXTREME** | 5 | 1002 | **+0.36** | +0.20 | 1.6% | 50.9% | 22.9 | 7.8 | 0.6 | 3.80 |
| | **15** | 986 | **+0.92** | +0.55 | 3.6% | **52.3%** | 34.2 | 18.7 | 5.6 | **7.02** |
| | 30 | 968 | +0.73 | +0.66 | 2.3% | 52.4% | 38.6 | 26.2 | 10.6 | 10.04 |
| | 60 | 939 | +0.91 | +1.23 | 2.8% | 52.8% | 41.9 | 31.4 | 14.4 | 13.55 |
| ORDINARY | 5 | 2847 | +0.03 | +0.05 | 0.4% | 50.4% | 35.5 | 24.1 | 10.2 | 2.60 |
| | 15 | 2813 | +0.01 | +0.06 | 0.9% | 50.5% | 41.5 | 33.4 | 20.0 | 5.10 |
| | 30 | 2723 | −0.15 | −0.21 | −2.2% | 49.1% | 42.9 | 36.7 | 26.5 | 7.48 |
| | 60 | 2408 | −0.03 | +0.20 | 0.7% | 50.7% | 45.7 | 41.4 | 32.8 | 10.46 |

**The best mean contraction anywhere is +0.92 bps at 15 minutes.** The
pre-registered bar is **2.0 bps**. It is never approached at any horizon.

**Extreme residuals close 1.6–3.6% of themselves.** A mean-reverting residual
should give back materially more. And the rate of *any* contraction is
**50.9–52.8%** against ordinary's 49.1–50.7% — a coin flip plus two points.

---

## 3. Positive versus negative residuals

| set | h | n | mean bps | % closed | any contraction |
|---|---|---|---|---|---|
| **EXT-POS** | 15 | 491 | **+1.40** | 6.7% | 54.6% |
| | 30 | 481 | **+1.82** | 9.0% | 55.3% |
| | 60 | 463 | **+2.18** | 11.4% | 56.8% |
| **EXT-NEG** | 15 | 495 | +0.45 | 0.5% | 50.1% |
| | 30 | 487 | **−0.35** | −4.3% | 49.5% |
| | 60 | 476 | **−0.34** | −5.5% | 48.9% |

**Only one side contracts.** When QQQ has over-performed (positive residual) it
gives some back, growing with horizon. When QQQ has **under**-performed, the
residual **expands further** at 30 and 60 minutes.

This is the asymmetry a relative-value mechanism must not have. The proposed
story — common macro flow transmitting unevenly, then correcting — is
direction-symmetric. What the data shows is closer to a QQQ-specific
over-extension effect on one side only. **Kill condition 3 is met.**

EXT-POS reaching +2.18 bps at h60 clears the 2.0 bar, but the gate is written on
the **state**, not on one side, and pass condition 4 requires both sides to
contract. A one-sided finding is not a hedged spread mechanism.

---

## 4. Controls

### Wrong beta — the decisive control failure

| hedge ratio | h5 | h15 | h30 | h60 |
|---|---|---|---|---|
| **β × 1.00 (true)** | +0.36 | **+0.92** | +0.73 | +0.91 |
| β × 0.75 | **+0.51** | +0.68 | +0.40 | **+1.51** |
| β × 1.25 | +0.35 | +0.57 | −0.23 | +0.09 |

**A deliberately wrong hedge ratio of 0.75× beats the true beta at both h5 and
h60** — +0.51 against +0.36, and +1.51 against +0.91. The 1.25× distortion is
weaker. One distortion better, one worse, is what you see when the hedge ratio
is **not load-bearing**: the result is insensitive to getting it right.

**Kill condition 5 is met: wrong-beta residuals perform similarly or better.**

### Date-shuffled pairing — passes

| | h5 | h15 | h30 | h60 |
|---|---|---|---|---|
| true pairing | +0.36 | +0.92 | +0.73 | +0.91 |
| date-shuffled | +0.19 | −0.06 | **−2.07** | **−2.01** |

Donor SPY sessions drawn from the same calendar year with full-session realised
volatility within ±10%, minute-of-day preserved, whole sessions shuffled rather
than individual bars. Clearly weaker. **This control passes.**

### QQQ alone — passes

| | h5 | h15 | h30 | h60 |
|---|---|---|---|---|
| hedged residual | +0.36 | +0.92 | +0.73 | +0.91 |
| QQQ only, hedge removed | −1.45 | −0.43 | −2.03 | −0.48 |

Unhedged QQQ directional behaviour does **not** explain the result — it is
negative at every horizon. **This control passes, and it is the one genuinely
encouraging result in this report:** whatever small effect exists, the hedge is
contributing to it rather than being window dressing.

### Time of day

| bucket | h15 | h30 | h60 |
|---|---|---|---|
| 09:30–11:00 (n=603) | **+1.30** | +1.03 | +1.27 |
| 11:00–14:00 (n=288) | +0.52 | +0.49 | +0.36 |
| 14:00–16:00 (n≤95) | **−0.21** | **−0.71** | −0.40 |

Concentrated at the open and **negative in the afternoon**. Consistent with
uneven transmission of opening flow — and equally consistent with the open
simply being the noisiest part of the session.

---

## 5. Commercial interpretation

The declared paired round-trip cost is **0.538 bps**.

| horizon | gross contraction | × cost | net | mean max adverse | **adverse : gain** |
|---|---|---|---|---|---|
| 5 | +0.36 | 0.66× | **−0.18** | 3.80 | 10.7 : 1 |
| **15** | **+0.92** | **1.72×** | **+0.38** | 7.02 | **7.6 : 1** |
| 30 | +0.73 | 1.35× | +0.19 | 10.04 | 13.8 : 1 |
| 60 | +0.91 | 1.68× | +0.37 | 13.55 | 14.9 : 1 |

**At the best horizon you must sit through an average 7.02 bps of adverse
residual expansion to harvest 0.92 bps gross and 0.38 bps net.** That is a
7.6 : 1 adverse-to-gain ratio before slippage, before any stop is placed, and
before the fact that a stop tight enough to control the 7 bps excursion would
cut off most of the 0.92.

The h5 horizon does not cover its own cost at all.

**The residual is real, measurable, and economically inert.** It exists — mean
|R| of 20.85 bps at the extreme state, cleanly separated from ordinary at
5.70 — and it does not contract enough to pay for the two-leg execution needed
to capture it.

---

## 6. Discovery gate — the sequence rule

The approved rule: 2023 is opened **only if all five** conditions hold.

| # | condition | result | |
|---|---|---|---|
| 1 | mean contraction ≥ 2.0 bps at one horizon | **max +0.92** | **FAIL** |
| 2 | extreme contracts more than ordinary | +0.92 vs +0.01 in bps; 3.6% vs 0.9% closed | marginal |
| 3 | both positive and negative residuals contract | **negative side expands at h30 and h60** | **FAIL** |
| 4 | ≥ 4 signals per month | **44.30** | **PASS** |
| 5 | wrong-beta, shuffled and QQQ-only controls all weaker | **β×0.75 stronger at h5 and h60** | **FAIL** |

**Kill conditions met: 2 (contraction below 2.0 bps), 3 (only one side
contracts), 5 (wrong beta similar or better), 8 (discovery fails before
validation is opened).**

**2023, 2024 and 2025 remain unread**, exactly as the sequence rule requires.
They are preserved intact for any future family.

---

## Appendix — formal detail

| h | n | mean bps | sd | SE | t |
|---|---|---|---|---|---|
| 5 | 1002 | +0.36 | 7.56 | 0.24 | +1.49 |
| **15** | 986 | **+0.92** | 12.68 | 0.40 | **+2.29** |
| 30 | 968 | +0.73 | 16.83 | 0.54 | +1.34 |
| 60 | 939 | +0.91 | 21.17 | 0.69 | +1.31 |

The h15 t of +2.29 is the only statistic in this report that looks supportive,
and it is exactly the kind of number this desk has learned not to promote: it
sits on a mean of 0.92 bps against a 2.0 bps pre-registered bar, a 7.6 : 1
adverse-to-gain ratio, a one-sided residual response, and a wrong-beta control
that beats it. **No multiplicity correction is applied because none is needed —
the economic bar was set in advance and was not reached.**

Median time to first 50% contraction: **13.0 minutes**, resolved within 60
minutes on **52.3%** of signals.

---

# VERDICT: RESIDUAL MECHANISM REJECTED — CLOSE RP-003

No Stage 2. No trading proposal. No data acquired. **2023–2025 not read.**

RP-004 (intraday lead-lag) remains unrun and awaits separate authorisation.

---

## Closure entry, as recorded by the principal

Closed as an **economic and mechanism failure**:

1. Best gross contraction **+0.92 bps** against the pre-declared **2.0 bps**.
2. Estimated net contraction after paired costs **+0.38 bps**.
3. Average adverse expansion **7.02 bps ≈ 7.6×** the gross contraction.
4. **Positive residuals contracted; negative residuals kept expanding.** The
   proposed relative-value mechanism was not symmetric.
5. A deliberately incorrect beta of **0.75×** performed better at key horizons.
   The estimated hedge ratio was **not load-bearing**.
6. Frequency was excellent at **44 signals/month** — and frequency does not
   rescue economically inert signals.
7. QQQ alone did not explain the result, which is worth recording, but is
   insufficient to overcome the failed economics and controls.

> The QQQ and SPY residual exists and is measurable, but its future contraction
> is too small, too adverse before resolution, one sided, and insensitive to the
> proposed hedge ratio. **It is not tradeable after paired execution costs.**

2023 and 2024–2025 not opened. No Stage 2. No data acquisition.
