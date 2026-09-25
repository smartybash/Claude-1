# RP-008 Stage 1 — do materially different forward trading environments exist?

Pre-registered at `4481bae`, written and committed **before** the harness
existed. **No strategy P&L, no strategy trade, no conditional performance, no
allocator, no pairing, no Monte Carlo.** No strategy module is imported by the
Stage 1 code and the NQ tape is never opened.

QQQ one-minute, 2021-01-04 → 2026-08-31. **1,294 sessions, 62 months, 2,586
labelled classification observations** after the 250-observation warm-up.

---

## 1. The answer, in one table

**Variance in the forward environment explained, by source:**

| forward outcome | time of day alone | RV₆₀ alone | both | **+ the six state labels** |
|---|---|---|---|---|
| realised volatility (bps) | 0.206 | 0.348 | **0.627** | 0.629 — **+0.0014** |
| **excursion, MAE in ATR₁ₘ** | **0.085** | **0.004** | 0.086 | 0.086 — **+0.0001** |
| path efficiency | 0.005 | 0.000 | 0.005 | 0.008 — +0.0036 |

On the block-relative labels — the fairer construction — the tercile adds
**+0.0004**, **+0.0014** and **+0.0050**.

**Carving volatility into states adds essentially nothing that the continuous
variable and the clock did not already contain.**

And the second row is the one that decides it:

> **Correlation of RV₆₀ with the forward 60-minute excursion, measured in ATR₁ₘ:
> −0.091 at 09:30 and +0.079 at 11:30.** Two instants, opposite signs, both
> indistinguishable from zero.

Volatility is forecastable **in basis points** — correlation 0.674 and 0.862
within the two instants, R² 0.348, stable in six of six years. It is **not
forecastable in the units a trader sizes in**, because ATR₁ₘ, the sizing unit,
already contains the same information. Knowing that tomorrow will be volatile
tells you to use a wider stop; it does not tell you the move will be large
relative to that stop.

---

## 2. Counts, before any forward outcome

| | |
|---|---|
| classification observations built | 5,673 |
| at the two primary instants (09:30, 11:30) | 2,837 |
| labelled after the 250-observation warm-up | **2,586** |
| sessions / months / years | 1,294 / 62 / 2021–2026 |

**Pooled terciles — the frozen primary:**

| instant | LO | NORMAL | HI | all |
|---|---|---|---|---|
| 09:30 | **578** | 355 | 359 | 1,292 |
| 11:30 | 347 | 426 | **521** | 1,294 |

The cells came out unbalanced, and the imbalance is a finding rather than a
nuisance. **The two instants do not draw from the same RV₆₀ distribution:** at
09:30 RV₆₀ is the prior session's 15:00–16:00 hour (mean 4.47 bps, median 3.78);
at 11:30 it is the same session's 10:30–11:30 (mean 5.10, median 4.50). A pooled
tercile label therefore partly encodes *which instant*, which is exactly the
confound §3.2 of the pre-registration named in advance.

**Block-relative terciles**, added at this counts stage before any forward
outcome was computed and carried through every table thereafter:

| instant | LO | NORMAL | HI | all |
|---|---|---|---|---|
| 09:30 | 495 | 377 | 420 | 1,292 |
| 11:30 | 470 | 367 | 457 | 1,294 |

State frequency, pooled: 09:30 LO 9.3/month, 09:30 NORMAL 5.7, 09:30 HI 5.8,
11:30 LO 5.6, 11:30 NORMAL 6.9, 11:30 HI 8.4.

---

## 3. Forward environment by state

All scaled quantities in ATR₁ₘ. Forward window 60 minutes, strictly after the
classification bar — the lookback and the measurement share no bar.

| state | n | RV₆₀ | fwd RV | fwd range | MFE med | MAE med | fwd eff | to close |
|---|---|---|---|---|---|---|---|---|
| 09:30 LO | 578 | 2.86 | **5.88** | 14.19 | 5.37 | **5.79** | 0.136 | 390 |
| 09:30 NORMAL | 355 | 4.22 | 6.86 | 13.31 | 5.60 | 5.27 | 0.155 | 390 |
| 09:30 HI | 359 | 7.31 | **9.31** | 11.91 | 4.51 | **5.36** | 0.134 | 390 |
| 11:30 LO | 347 | 3.21 | **2.80** | 6.53 | 2.57 | **2.62** | 0.118 | 270 |
| 11:30 NORMAL | 426 | 4.42 | 3.71 | 7.51 | 2.80 | 2.99 | 0.129 | 270 |
| 11:30 HI | 521 | 6.92 | **5.48** | 8.65 | 3.54 | **3.35** | 0.132 | 270 |

**The 09:30 rows contain the study's most informative anomaly.** Forward RV
rises 5.88 → 9.31 bps from LO to HI, a clean 1.58× — and median MAE **falls**,
5.79 → 5.36. The high-volatility state is followed by more volatility in bps and
*slightly smaller* excursions in ATR units. That is the normalisation effect
stated plainly: the denominator moved with the numerator.

**Stop-out probability, P(adverse excursion ≥ d), %:**

| state | d=0.5 | d=1.0 | d=1.5 | d=2.0 |
|---|---|---|---|---|
| 09:30 LO | 94.5 | 90.3 | 86.0 | 81.8 |
| 09:30 NORMAL | 92.4 | 84.8 | 80.6 | 75.8 |
| 09:30 HI | 96.1 | 90.8 | 85.8 | 81.3 |
| 11:30 LO | 88.5 | 78.1 | 67.7 | 61.7 |
| 11:30 NORMAL | 91.1 | 82.2 | 72.8 | 64.6 |
| 11:30 HI | 89.3 | 82.3 | 73.9 | 66.4 |

**A specification defect of mine, recorded:** the "either side" columns —
P(adverse *or* favourable ≥ d) — return 95.7% to 100.0% in every cell at every
distance. They saturate and carry no information. The one-sided columns work and
are what §5's condition 3 is judged on. The frozen stop grid was not changed.

---

## 4. The decisive separation test

**(a) At matched volatility, does the instant matter?**

| vol | fwd RV 09:30 | fwd RV 11:30 | ratio | MAE 09:30 | MAE 11:30 | ratio |
|---|---|---|---|---|---|---|
| LO | 5.88 | 2.80 | **0.48** | 5.79 | 2.62 | **0.45** |
| NORMAL | 6.86 | 3.71 | 0.54 | 5.27 | 2.99 | 0.57 |
| HI | 9.31 | 5.48 | 0.59 | 5.36 | 3.35 | 0.62 |

**Yes, enormously.** At matched volatility the 11:30 environment is roughly half
the 09:30 environment on every measure.

**(b) At matched instant, does the volatility tercile matter?**

| instant | fwd RV LO | fwd RV HI | ratio | MAE LO | MAE HI | ratio | overlap |
|---|---|---|---|---|---|---|---|
| 09:30 | 5.88 | 9.31 | **1.58** | 5.79 | 5.36 | **0.93** | 0.836 |
| 11:30 | 2.80 | 5.48 | **1.96** | 2.62 | 3.35 | **1.28** | 0.796 |

**(c) Same, block-relative labels**

| instant | ratio (RV) | ratio (MAE) | overlap |
|---|---|---|---|
| 09:30 | 1.66 | **0.93** | 0.809 |
| 11:30 | 2.10 | **1.34** | 0.792 |

In bps, yes. In ATR units, no at 09:30 (0.93, the wrong side of 1.00) and
marginally at 11:30 (1.28 against a 1.30 bar; 1.34 on the diagnostic labels).

**(d) Stop-out spread — the economically binding comparison, percentage points**

| comparison | d=0.5 | d=1.0 | d=1.5 | d=2.0 |
|---|---|---|---|---|
| 09:30 HI − LO | +1.6 | +0.5 | −0.2 | −0.5 |
| 11:30 HI − LO | +0.8 | +4.2 | +6.2 | +4.7 |
| **LO, 11:30 − 09:30** | −6.0 | **−12.2** | **−18.3** | **−20.2** |
| **NORMAL, 11:30 − 09:30** | −1.3 | −2.6 | −7.8 | **−11.2** |
| **HI, 11:30 − 09:30** | −6.8 | −8.5 | **−11.9** | **−14.9** |

On the block-relative labels the best volatility-axis spread is **+7.8 points**
(11:30, d=1.5). On the time axis it reaches **20.2 points**.

**The volatility axis never reaches the 10-point bar. The time axis clears it at
seven of twelve cells.**

---

## 5. Stability and transitions

HI/LO forward-RV ratio by year:

| instant | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | years > 1 |
|---|---|---|---|---|---|---|---|
| 09:30 | 1.74 | 1.22 | 1.26 | 1.57 | 2.15 | 1.47 | **6 of 6** |
| 11:30 | 2.19 | 1.73 | 1.59 | 1.86 | 2.63 | 1.96 | **6 of 6** |

The volatility ordering is stable. State frequencies are not: 09:30 LO ranges
17.4% (2022) to 32.2% (2023) of the year's observations, and 11:30 LO ranges
5.7% (2026) to 17.8% (2023).

**Transition matrix**, %:

| from ↓ to → | 09:30 LO | 09:30 NORM | 09:30 HI | 11:30 LO | 11:30 NORM | 11:30 HI |
|---|---|---|---|---|---|---|
| 09:30 LO | — | — | — | **43.8** | 34.9 | 21.3 |
| 09:30 NORMAL | — | — | — | 21.7 | 39.2 | 39.2 |
| 09:30 HI | — | — | — | 4.5 | 23.4 | **72.1** |
| 11:30 LO | **74.9** | 17.3 | 7.5 | — | — | — |
| 11:30 NORMAL | 51.3 | 31.3 | 17.4 | — | — | — |
| 11:30 HI | 19.2 | 31.1 | **49.7** | — | — | — |

The instant half of every transition is deterministic — 09:30 is always followed
by 11:30 within the session and 11:30 by the next session's 09:30 — so only the
volatility half carries information. It does: 72.1% of high-volatility opens
stay high at 11:30 against a 40% base rate.

Volatility stay-rate by year: 48.2 / 58.5 / 45.4 / 48.4 / 57.6 / **39.9**
(2026, n=331, partial year) against a 33% chance baseline. Persistent, and the
year-to-year swing of 18.6 points is wide enough that **kill condition 5 is
arguable**. I do not rest the verdict on it.

---

## 6. Neighbouring thresholds

| cut | instant | fwd RV ratio HI/LO | MAE ratio | d=1.0 stop-out spread |
|---|---|---|---|---|
| 33/67 | 09:30 | 1.58 | 0.93 | +0.5 |
| 33/67 | 11:30 | 1.96 | 1.28 | +4.2 |
| 30/70 | 09:30 | 1.63 | 0.92 | +0.2 |
| 30/70 | 11:30 | 2.00 | 1.26 | +3.1 |
| 40/60 | 09:30 | 1.51 | 0.94 | −0.2 |
| 40/60 | 11:30 | 1.83 | 1.29 | +5.5 |

**Both readings of this test are true and they point the same way.** Pass
condition 6 is satisfied — the differences survive. Kill condition 6 is also
satisfied — the boundaries produce the same results wherever they are placed,
which means they are **not load-bearing**. There is a monotone gradient in a
continuous variable, not a regime with edges. Moving the boundary by ten
percentage points changes nothing because there is nothing there to change.

---

## 7. Secondary descriptive panel — all four blocks

No pass weight. Reported because it is the clearest picture in the study.

| instant | n | RV₆₀ | fwd RV | fwd range | MAE med | MFE med | fwd eff | d=1.0 stop-out |
|---|---|---|---|---|---|---|---|---|
| **09:30** | 1,418 | 4.47 | **7.05** | 13.35 | **5.56** | 5.29 | 0.140 | **88.4%** |
| 10:00 | 1,418 | 7.45 | 5.87 | 11.10 | 4.50 | 4.37 | 0.136 | 86.0% |
| 11:30 | 1,419 | 5.06 | 4.14 | 7.73 | 2.95 | 3.09 | 0.129 | 80.9% |
| **14:00** | 1,418 | 3.69 | **3.96** | 7.26 | **2.49** | 2.50 | 0.127 | **76.0%** |

Forward volatility falls **44%** across the day, excursions fall **55%**, and
the probability of a 1-ATR adverse move falls **12.4 points**. Monotone at every
step, on 1,418 sessions per block.

**Path efficiency is flat: 0.140, 0.136, 0.129, 0.127.** The day gets quieter,
not straighter — which is the same conclusion §3.5 of this project reached from
the other direction.

---

## 8. Pass conditions

| # | condition | bar | result | |
|---|---|---|---|---|
| 1 | volatility differs | ≥1.50× | **1.58 and 1.96** | **PASS**, in bps |
| 2 | excursion distributions differ | ≥1.30× median and overlap ≤0.85 | **0.93** and **1.28**; overlap 0.836 / 0.796 | **FAIL** |
| 3 | stop-out risk differs | ≥10 points | **max 6.2** on the volatility axis (7.8 block-relative) | **FAIL** |
| 4 | holding opportunity differs | efficiency ≥0.05 | **max spread 0.037** across all six states | **FAIL** |
| 5 | stable across years | ≥5 of 6 | **6 of 6** on the volatility ordering | **PASS** |
| 6 | survives neighbouring thresholds | ordering preserved | preserved — **and the boundaries do no work** | ambiguous by design |
| 7 | economically meaningful | ≥10 points at a real stop | volatility axis ≤7.8 points everywhere | **FAIL** |

**Two clear passes, four clear fails, one ambiguous.** Both passes are about
volatility measured in basis points; every failure is about the quantities a
position actually experiences.

The requirement "at least two states must have clearly different forward
environments" **is satisfied** — 09:30 states differ from 11:30 states by a
factor of two on every measure. But they differ **by the clock**.

## 9. Kill conditions

| # | condition | verdict |
|---|---|---|
| 1 | states differ only by construction | **FIRES.** The tercile labels add +0.0014 R² for forward RV and +0.0001 for forward MAE on top of continuous RV₆₀ and the instant |
| 2 | forward environments materially similar | fires on the volatility axis, not on the time axis |
| 3 | excursion distributions overlap heavily | overlap 0.796–0.836 against a 0.85 bar — marginal, does not fire outright |
| 4 | stop-out probabilities similar | **FIRES on the volatility axis** — ≤7.8 points everywhere against a 10-point bar |
| 5 | transition behaviour unstable across years | arguable — stay-rate swings 39.9% to 58.5%; not relied on |
| 6 | neighbouring thresholds produce the same results | **FIRES.** 30/70 and 40/60 reproduce 33/67 to two decimals |
| 7 | **the only meaningful distinction is time of day itself** | **FIRES.** Time explains 0.085 of forward excursion variance, RV₆₀ explains 0.004, and the state labels add 0.0001 |

---

# VERDICT A: REGIMES NOT MEANINGFUL — CLOSE RP-008

The frozen causal states do not create materially different forward trading
environments. Three kill conditions fire outright and a fourth is arguable.

**Stage 2 is not opened. No strategy P&L was read at any point.**

---

## What is actually true, stated precisely

Closing this cleanly matters more than closing it tidily, so here is what the
study did establish.

**Volatility clusters, and it is genuinely forecastable in basis points.** RV₆₀
predicts the next hour's realised volatility with correlation 0.674 at 09:30 and
0.862 at 11:30, R² 0.348, stable in six of six years, with 72.1% of
high-volatility opens still high at 11:30. That is a real property of the
market and this study confirms it.

**It does not survive normalisation.** Expressed in ATR₁ₘ — the unit in which a
stop is placed and a position is sized — the correlation between RV₆₀ and the
forward excursion is **−0.091 and +0.079**. The predictable part of volatility
is already inside the sizing unit. This is the reason "trade only when
volatility is high" does not work, and it is a general result, not a fact about
these six states: *you widen the stop by exactly the amount the move widens.*

**Time of day is a large, monotone, stable gradient** — forward volatility down
44% and excursions down 55% from the open to 14:00, on 1,418 sessions per block,
with efficiency flat throughout. This is economically material and it is the
only thing in the study that clears the 10-point stop-out bar.

**But a clock is not a regime.** Time of day requires no detection, no
classification, no state variable and no research. It is known in advance, every
day, by everyone. Building an allocator to discover it would be building
machinery to read a clock.

## What this closes, and what it does not

**It closes the premise of conditional allocation on this evidence.** Every
future "trade only when X" rule where X is a causal volatility state now has a
measured answer: the state changes the size of what happens next in basis
points, and does not change it relative to the stop you would have used anyway.
That is worth more than another closed setup, and it is what the pivot was for.

**It does not close** conditioning on something other than volatility or the
clock — order-flow state, event structure, or cross-asset condition. None of
those was tested here and none inherits this result. Any such proposal now has a
higher bar: it must show it survives normalisation by the sizing unit, because
that is where this one died.

**It does not close** time-of-day *design*. A strategy that trades the open
because excursions there are twice as large is using a real fact. It simply does
not need a regime detector to do it.

---

## Declared

No strategy P&L, no strategy trade, no conditional performance, no allocator, no
pairing, no Monte Carlo. No strategy module imported. Sealed NQ dates not read;
the NQ tape was never opened. 2016–2020 not opened. Every frozen constant was
applied unchanged; the one addition — block-relative terciles — was made at the
counts stage before any forward outcome was computed, is labelled a diagnostic
throughout, and made the volatility axis look **better**, not worse, without
changing the verdict.

---

## Closure entry, as recorded by the principal

RP-008 is accepted as closed and the dynamic regime allocator branch is closed
with it. Recorded:

1. **Forward volatility in basis points is predictable from recent volatility.**
2. **Once movement is normalised by the ATR unit used to size risk, volatility
   states do not create materially different excursion or stop-out
   environments.**
3. **The six regime labels add effectively no explanatory value beyond time of
   day and current volatility** — +0.0014 R² for forward volatility, +0.0001 for
   forward excursion.
4. **Path efficiency remains broadly flat through the session** (0.127–0.140).
5. **Time of day produces the only large, stable forward distinction.**
6. **Forward volatility falls approximately 44% and excursions approximately
   55% from the open to the later session.**
7. **The session becomes quieter, not more directional.**
8. **Neighbouring volatility thresholds produce nearly identical results**,
   indicating a continuous gradient rather than distinct regimes.

> **Therefore there is no basis for a dynamic selector switching strategies
> according to low, normal or high volatility states.**

**Verdict: regimes not meaningful. RP-008 closed before strategy P&L was
opened.**

Stage 2 was not opened. No conditional strategy performance was inspected. No
allocator was constructed from the existing strategy library.

**Preserved finding, recorded in the form it should carry forward:** *time of
day is economically meaningful, and it is a **continuous opportunity gradient**,
not a regime.* It requires no detection, no classification and no state
variable. It is the input to RP-009.
