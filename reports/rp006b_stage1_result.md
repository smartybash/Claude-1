# RP-006B Stage 1 — corrected cross-sectional intraday momentum

Pre-registered at `d26c066`, written and committed **before** the harness was run.
Descriptive only. **No P&L, expectancy, profit factor, drawdown or pass
probability.**

**Discovery block 2023-01-03 → 2023-12-29 ONLY. 2024 and 2025 were not read.**
2021–2022 contributed **no observation and no forward return**; it appears
nowhere in this report except as the labelled invalid diagnostic in §12.

The 20-session beta window and 60-session dispersion reference were drawn from
2022-08-01 → 2022-12-30 as **causal estimation inputs**, exactly as declared in
§1 of the re-registration. No 2022 date produces a row in any table below.

---

## 1. Eligibility funnel

| stage | 2023 sessions |
|---|---|
| calendar sessions present in the data | **250** |
| less: one of the six measurement timestamps missing | **−25** |
| less: stale 10:00 print (close 10:00 = close 09:59) | **−9** |
| less: <300 bars pairwise against SPY | **−2** |
| less: incomplete causal beta | **−1** |
| **eligible observations** | **213 (85.2%)** |

All 26 timestamp misses across those 25 sessions are **IJH**; QQQ, SPY and IWM
miss none. IJH remains the thin instrument — but it now costs 25 sessions rather
than the 292 the defective four-way 380-bar filter destroyed. **Correction 1
works: the corrected filter keeps 85% of 2023 where the old one kept 42% of
2021–22.**

Warm-up window: 2022-08-01 → 2022-12-30, 55 sessions, inputs only.

**IJH split verified before the run.** The five-for-one split appears in the
stored series at 2024-02-22 (280.84 → 56.99). The whole of 2023 is on the
pre-split basis with no discontinuity, so no adjustment applies here and the
~$260 price used in the cost calculation is the price IJH actually traded at.
The adjustment must be applied and re-verified before 2024 is ever opened.

---

## 2. Rank balance — baseline 66.7%, flagged at >80% / <53%

With three instruments every session places one at each extreme, so the neutral
expectation is **66.7% for each name**, not 50%.

| instrument | strongest | weakest | either extreme | deviation | |
|---|---|---|---|---|---|
| **QQQ** | 43.7% | 47.9% | **91.5%** | **+24.9 pts** | **FLAG >80%** |
| IWM | 29.6% | 27.7% | 57.3% | −9.4 pts | |
| **IJH** | 26.8% | 24.4% | **51.2%** | **−15.5 pts** | **FLAG <53%** |

**QQQ sits at an extreme on 91.5% of sessions.** This is not a cross-section; it
is a QQQ pair trade with two alternating counterparties. The 2021–22 halt report
predicted +20.1 pts on invalid data; 2023 gives +24.9 pts on valid data.

As instructed this is a **diagnostic, not an automatic kill**, and the universe
is not redefined. The ex-QQQ figure is reported for information in §11 only.

---

## 3. Pair counts

| long | short | n | share |
|---|---|---|---|
| IWM | QQQ | 53 | 24.9% |
| QQQ | IWM | 51 | 23.9% |
| IJH | QQQ | 49 | 23.0% |
| QQQ | IJH | 42 | 19.7% |
| IWM | IJH | 10 | 4.7% |
| IJH | IWM | 8 | 3.8% |

Unordered: QQQ/IWM 104 · QQQ/IJH 91 · **IWM/IJH 18 (8.5%)**. The one pair not
involving QQQ occurs on fewer than one session a month.

---

## 4. Realised frequency

**213 observations over 12 months = 17.75 per month.** HIGH dispersion 77
(6.42/mo), ORDINARY 136.

**Requirement 9 (≥4 per month) passes, and it is the only requirement that
does.** Frequency was never the constraint in this family.

---

## 5. Future spread by horizon — long strongest, short weakest, forward only

Basis points. Beta-neutral residual returns measured from the 10:00 formation
close forward.

| horizon | n | mean spread | median | positive rate |
|---|---|---|---|---|
| 30 min | 213 | **−0.76** | −0.22 | 49.3% |
| 60 min | 213 | **−1.38** | −0.49 | 48.4% |
| 120 min | 213 | **+0.61** | +2.06 | 52.1% |
| cash close | 213 | **+2.24** | +0.51 | 51.6% |

**The first hour is reversal, the rest is noise.** The best figure anywhere is
+2.24 bps at the close on a 51.6% positive rate — a coin flip plus 1.6 points.

---

## 6. Pair-specific cost and headroom

Round trip $0.017 per share per leg, computed on each date's realised prices for
the two legs actually traded.

| horizon | gross | 3 × realised cost | **headroom** |
|---|---|---|---|
| 30 min | −0.76 | 3.99 | **−4.75** |
| 60 min | −1.38 | 3.99 | **−5.37** |
| 120 min | +0.61 | 3.99 | **−3.38** |
| close | +2.24 | 3.99 | **−1.75** |

By realised pair:

| pair | n | 3 × cost | h30 | h60 | h120 | close |
|---|---|---|---|---|---|---|
| IWM / QQQ | 104 | 4.28 | +2.41 | +0.79 | +2.46 | **+3.54** |
| IJH / QQQ | 91 | 3.50 | −3.82 | −3.53 | −1.34 | +1.15 |
| IWM / IJH | 18 | 4.76 | −3.63 | −3.01 | −0.20 | +0.29 |

**Requirement 2 fails at every horizon.** The single best pair-horizon cell in
the entire study — IWM/QQQ at the close, +3.54 bps — still sits **below its own
4.28 bps hurdle**, and that is before slippage, before any stop, and on 104
observations selected after the fact.

---

## 7. Leg contributions

| horizon | long leg | short leg | who carries it |
|---|---|---|---|
| 30 min | **−1.47** | +0.71 | long leg is negative |
| 60 min | **−2.18** | +0.80 | long leg is negative |
| 120 min | **−1.49** | +2.10 | long leg is negative |
| close | +0.49 | +1.75 | short leg carries **78%** |

**Requirement 3 fails.** At three of four horizons the long leg — the instrument
selected as *strongest*, the side the hypothesis is actually about — **loses
money on its own**, and the spread is positive only because the short leg loses
less. At the close the short leg carries 78% of the result.

The mechanism proposed was persistence of relative strength. What the data shows
is that the strongest residual does not persist at all; the only recoverable
structure is mild weakness in the weakest name, which is the opposite leg.

---

## 8. HIGH versus ORDINARY dispersion

| set | horizon | n | spread | positive rate | long leg | short leg |
|---|---|---|---|---|---|---|
| HIGH | 30 | 77 | **+3.26** | 53.2% | +0.02 | +3.24 |
| HIGH | 60 | 77 | **+4.27** | 54.5% | −0.56 | +4.83 |
| HIGH | 120 | 77 | +1.78 | 58.4% | −1.12 | +2.90 |
| **HIGH** | **close** | 77 | **−1.49** | **45.5%** | −3.03 | +1.54 |
| ORDINARY | 30 | 136 | −3.04 | 47.1% | −2.31 | −0.73 |
| ORDINARY | 60 | 136 | −4.57 | 44.9% | −3.09 | −1.48 |
| ORDINARY | 120 | 136 | −0.05 | 48.5% | −1.70 | +1.65 |
| **ORDINARY** | **close** | 136 | **+4.36** | **55.1%** | +2.48 | +1.87 |

Mean dispersion D: HIGH 81.41 bps, ORDINARY 29.45 bps — the conditioning
variable separates cleanly.

This is the one table with a pattern in it, and it **contradicts the headline**.
HIGH dispersion is better at 30, 60 and 120 minutes — and then **inverts at the
close**, where HIGH is −1.49 against ORDINARY's +4.36. The horizon that produces
the study's single best number is the horizon where the state variable points the
wrong way.

**Requirement 4 fails at the close.** I am recording explicitly that the HIGH
subset was **not separately controlled** — the random-pair and shuffled
distributions in §9 were computed on all 213 observations. Building a new control
for a subset after seeing that the subset looks better is the post-hoc move this
desk exists to prevent, and I am not doing it. The HIGH h60 figure of +4.27 bps
is therefore **unresolved, not supportive** — and in any case it sits below the
3.99 bps cost hurdle and reverses by the close.

---

## 9. Corrected controls

### Reversed spread

| horizon | true | reversed |
|---|---|---|
| 30 | −0.76 | **+0.76** |
| 60 | −1.38 | **+1.38** |
| 120 | +0.61 | −0.61 |
| close | +2.24 | −2.24 |

**Requirement 7 fails.** The reversed construction is stronger than the true one
at 30 and 60 minutes. Short-the-strongest beats long-the-strongest over the first
hour.

### Raw ranking with no beta neutralisation

| horizon | beta-neutral | raw |
|---|---|---|
| 30 | −0.76 | +0.17 |
| 60 | −1.38 | −0.03 |
| 120 | +0.61 | +1.09 |
| close | +2.24 | +1.30 |

The beta adjustment is not load-bearing. Raw is better at h30 and h120, worse at
the close — one distortion better, one worse, the same signature RP-003 produced.

### Random-pair — 200 repetitions, drawn pair evaluated on **every** date

| horizon | control mean | sd | p5 | p95 | **true** |
|---|---|---|---|---|---|
| 30 | −0.06 | 1.63 | −2.67 | +2.48 | −0.76 |
| 60 | +0.23 | 2.25 | −3.75 | +3.58 | −1.38 |
| 120 | −0.21 | 2.57 | −4.23 | +4.12 | +0.61 |
| close | −0.55 | 3.23 | −5.67 | +5.06 | **+2.24** |

### Shuffled ranking — 200 repetitions, permutes the **(strongest, weakest) identity** across dates

| horizon | control mean | sd | p5 | p95 | **true** |
|---|---|---|---|---|---|
| 30 | +0.08 | 1.99 | −2.95 | +3.40 | −0.76 |
| 60 | −0.07 | 2.54 | −4.09 | +4.04 | −1.38 |
| 120 | −0.30 | 2.73 | −5.01 | +4.49 | +0.61 |
| close | −0.57 | 3.54 | −6.08 | +5.58 | **+2.24** |

Both controls now behave — they centre near zero with a real spread, rather than
reproducing the true means to two decimals as the defective implementation did.
**Correction 3 and correction 4 both work.**

**Requirements 5 and 6 fail at every horizon.** The true value sits comfortably
inside both distributions everywhere. At the close, +2.24 against a p95 of +5.06
and +5.58: **randomly picking two of the three instruments and going long one of
them would beat the ranking rule about a third of the time.** The ranking carries
no information the shuffle does not.

---

## 10. Pair concentration

| horizon | IWM/IJH | IJH/QQQ | IWM/QQQ | max | |
|---|---|---|---|---|---|
| 30 | 9.8% | 52.4% | 37.8% | 52.4% | ok |
| 60 | 11.9% | **70.2%** | 17.9% | IJH/QQQ | **>60%** |
| 120 | 0.9% | 32.0% | **67.0%** | IWM/QQQ | **>60%** |
| close | 1.1% | 22.0% | **76.9%** | IWM/QQQ | **>60%** |

**Requirement 8 fails at three of four horizons**, including the close, where a
single pair carries **76.9%** of total spread continuation. The result is not a
cross-sectional effect; it is one pair.

---

## 11. Discovery gate

| # | requirement | result | |
|---|---|---|---|
| 1 | spread positive at ≥1 horizon | +0.61 at h120, +2.24 at close | **pass** |
| 2 | exceeds 3× pair-specific cost | best +2.24 vs 3.99; best cell +3.54 vs 4.28 | **FAIL** |
| 3 | both legs contribute | long leg negative at 3 of 4 horizons; short carries 78% at close | **FAIL** |
| 4 | HIGH not worse than ORDINARY | −1.49 vs +4.36 at the close | **FAIL** |
| 5 | beats random-pair p95 | inside the distribution at every horizon | **FAIL** |
| 6 | beats shuffled p95 | inside the distribution at every horizon | **FAIL** |
| 7 | reversed materially weaker | reversed stronger at h30 and h60 | **FAIL** |
| 8 | no pair >60% of continuation | 70.2% / 67.0% / 76.9% | **FAIL** |
| 9 | ≥4 sessions per month | 17.75 | **pass** |

**Seven of nine requirements fail.**

**Kill conditions met: 2** (positive but below the cost hurdle at every horizon),
**3** (one leg carries it, the other is negative), **4** (HIGH worse than ORDINARY
at the close), **5** (both control distributions contain the true value), **6**
(reversed as strong or stronger), **7** (a single pair carries >60%), **9**
(discovery fails before validation is opened).

Rank-domination diagnostic, for information only and **not promoted**: excluding
every QQQ pair leaves **n = 18** — h30 −3.63, h60 −3.01, h120 −0.20, close +0.29.
Eighteen sessions in a year is not a strategy and this is not a second front.

---

## 12. Labelled invalid diagnostic — 2021–2022

Recorded once, for completeness, and **used in no calculation above**: the
defective run's 2022-only output was negative at every horizon (−3.94 / −2.92 /
−3.79 / −8.57 bps) on 129 sessions with two broken controls. It is not a result.
2023, tested cleanly with corrected controls, is **also weak and also reverses
over the first hour** — which is consistent with it, but the consistency proves
nothing because the earlier run was invalid.

---

## Appendix — formal detail

| horizon | n | mean bps | sd | SE | t |
|---|---|---|---|---|---|
| 30 | 213 | −0.76 | 27.92 | 1.91 | **−0.40** |
| 60 | 213 | −1.38 | 35.05 | 2.40 | **−0.57** |
| 120 | 213 | +0.61 | 42.19 | 2.89 | **+0.21** |
| close | 213 | +2.24 | 54.55 | 3.74 | **+0.60** |

Each observation is one session, so these standard errors are already
date-clustered. **No |t| exceeds 0.60.** Nothing here is distinguishable from
zero, and no multiplicity correction is needed because the economic bar was set
in advance and was not approached.

Mean dispersion D 48.23 bps (HIGH 81.41, ORDINARY 29.45). Beta estimated
causally from the 20 prior completed sessions, no intercept, current session
excluded.

Seed 20260923, 200 repetitions per randomised control. No threshold, lookback,
formation window, factor, universe or dispersion boundary was varied during or
after the run.

---

# VERDICT: CROSS-SECTIONAL MOMENTUM REJECTED — CLOSE RP-006

The corrected harness did its job: the filter recovered 85% of the discovery
block, both controls now discriminate, and the hypothesis was given a fair test
on untouched data. It failed seven of nine pre-registered requirements.

**No Stage 2. No trading proposal. No data acquisition. 2024 and 2025 not
opened. 2021–2022 not re-run.**

The prior stated in the re-registration — *"I expect this to fail, most likely on
requirement 2 or requirement 8"* — is now measured. It failed both, and five
others.

---

## Closure entry

Closed as a **structural and economic failure**, not a marginal one:

1. **The universe cannot support a cross-section.** QQQ occupies an extreme on
   91.5% of sessions against a 66.7% neutral baseline; the one pair excluding it
   occurs 18 times a year. Three instruments give three pairs, and in practice
   they give one and a half.
2. **The long leg does not work.** At 30, 60 and 120 minutes the instrument
   selected as strongest has a negative forward residual. The hypothesis was
   persistence of relative strength; relative strength does not persist.
3. **Nothing clears cost.** Best horizon +2.24 bps against a 3.99 bps hurdle;
   best pair-horizon cell +3.54 against 4.28.
4. **The ranking carries no information.** True spreads sit inside the
   random-pair and shuffled-identity distributions at all four horizons, and a
   shuffle beats the rule roughly a third of the time at the close.
5. **Concentration.** One pair carries 76.9% of continuation at the close.
6. Frequency was never the problem: 17.75 sessions per month.

> The three-ETF cross-section ranks reliably, cheaply and often — and what it
> ranks does not persist. The only horizon with a positive spread is the one
> where the conditioning variable points the wrong way, the spread is carried by
> one leg and one pair, and a random draw matches it. **It is not tradeable.**

RP-006 is closed. 2023 is now spent for this family. 2024, 2025 and forward data
remain unread and intact.
