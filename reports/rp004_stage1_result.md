# RP-004 Stage 1 — SPY → EFA intraday lead-lag

Falsification study. **No P&L, expectancy, profit factor, drawdown or pass
probability.** Discovery 2021-01-04 → 2022-12-31 **only**; 2023 and 2024–2025
**not read** and, under the sequence rule, must not be.

Frozen: 1-minute log returns, lags 1/2/5/10 only, reverse direction as the
mechanism control, same-minute correlation as a control rather than an edge.
Returns never cross a session boundary.

---

## 0. Alignment and data quality — this settled the family

| | SPY | EFA |
|---|---|---|
| bars | 196,046 | 195,695 |
| exact-timestamp intersection | **195,694** | |
| instrument-only bars | 352 (0.18%) | 1 (0.00%) |
| aligned bars/session | median 390, p1 386 | |
| sessions dropped (<380 aligned) | **3 of 503** | |
| session-open jumps >10% (split check) | **0**, max 5.51% | **0**, max 5.39% |
| **zero-change 1-minute bars** | **1.77%** | **13.42%** |
| **max repeated-close run** | 4 bars | **9 bars** |
| **≥3-bar flat runs** | 0.19% of bars | **6.23% of bars** |

Alignment and price adjustment are clean. **Staleness is not.**

**EFA fails to print a new close on 13.42% of minutes — 7.6× SPY's rate.** This
is the precondition for kill condition 7, and it turns out to explain the only
positive number in the study.

194,404 usable return observations over 24 months. SPY 1-minute sd **4.77 bps**;
mean EFA price **$72.70**.

---

## 1. Headline — SPY_t → EFA_{t+lag}

| lag | n | correlation | ΔR² from adding SPY | beta | sign agreement | response to 1-sd SPY |
|---|---|---|---|---|---|---|
| **0 (CONTROL)** | 193,904 | **+0.8532** | **72.80%** | 0.6553 | 72.3% | 3.13 bps |
| 1 | 193,404 | **+0.0239** | 0.2271% | 0.0706 | 43.8% | **0.34 bps** |
| 2 | 192,904 | −0.0035 | 0.0001% | −0.0016 | 42.4% | −0.01 bps |
| 5 | 191,404 | −0.0039 | 0.0015% | −0.0058 | 42.8% | −0.03 bps |
| 10 | 188,904 | +0.0051 | 0.0018% | −0.0063 | 43.0% | −0.03 bps |

**The correlation peaks at lag zero by a factor of 36** — 0.8532 against 0.0239.
Same-minute explanatory power is **72.80%**; the best lagged increment is
**0.23%**. **Kill condition 1 is met, and it is not close.**

At lags 2, 5 and 10 the relationship is **zero or slightly negative**. There is
no decay curve — there is a contemporaneous spike and then nothing.

### Sign agreement is exactly what staleness alone predicts

Sign agreement at every lag sits at **42.4–44.7%, below chance.** That is not a
reversal effect. `sign(0) ≠ ±1`, so EFA's 13.42% zero-return bars can never
agree. The ceiling is therefore `0.866 × 50% = 43.3%` under pure chance.

**Observed 42.4–44.7% against a chance prediction of 43.3%.** The sign agreement
carries no information whatsoever.

---

## 2. Control — reverse direction, EFA_t → SPY_{t+lag}

| lag | correlation | ΔR² | response to 1-sd EFA |
|---|---|---|---|
| 0 | +0.8532 | 72.79% | 4.07 bps |
| 1 | **+0.0131** | 0.0073% | 0.08 bps |
| 2 | −0.0067 | 0.0011% | 0.03 bps |
| 5 | −0.0039 | 0.0005% | 0.02 bps |
| 10 | +0.0071 | 0.0024% | 0.04 bps |

SPY→EFA at lag 1 (0.0239) is roughly **1.8× the reverse** (0.0131). Directionally
correct — and both are statistical noise at 193k observations. The asymmetry is
real but worthless.

---

## 3. Controls — shuffled, sign-reversed

| control | lag 1 | lag 2 | lag 5 | lag 10 |
|---|---|---|---|---|
| **true SPY** | **+0.0239** | −0.0035 | −0.0039 | +0.0051 |
| time-shuffled SPY (same year + bucket) | +0.0027 | +0.0028 | −0.0045 | +0.0023 |
| SPY sign reversed, magnitude kept | −0.0024 | −0.0059 | −0.0079 | +0.0014 |

The shuffled and sign-reversed controls are near zero, so the lag-1 number is
not a construction artefact. **It is a real 0.0239 correlation — and it is the
signature of stale EFA prices**, not of a lead: when EFA does not print in minute
*t*, its minute *t+1* return absorbs the minute-*t* move. **To trade it you would
have to transact in the instrument that is not trading.**

---

## 4. Positive versus negative SPY moves

| lag | side | n | mean EFA response | sign agreement |
|---|---|---|---|---|
| 1 | SPY up | 95,922 | **+0.084 bps** | 44.7% |
| 1 | SPY down | 94,054 | **−0.067 bps** | 43.9% |
| 2 | SPY up | 95,682 | −0.012 | 43.2% |
| 2 | SPY down | 93,802 | +0.032 | 42.6% |

At lag 1 both sides respond with the correct sign — **pass condition 4 is met**.
The magnitudes are **0.08 and 0.07 basis points**.

---

## 5. Stability

| lag | 2021 | 2022 | 09:30–11:00 | 11:00–14:00 | 14:00–16:00 |
|---|---|---|---|---|---|
| 1 | +0.0285 | +0.0224 | +0.0240 | +0.0224 | +0.0256 |
| 2 | −0.0036 | −0.0035 | −0.0117 | +0.0040 | −0.0027 |
| 5 | +0.0034 | −0.0062 | +0.0019 | −0.0037 | −0.0115 |
| 10 | +0.0126 | +0.0027 | −0.0039 | +0.0061 | +0.0155 |

The lag-1 effect is **remarkably stable** — both years, all three time buckets,
range 0.0224–0.0285. **Pass condition 5 is met.** Stable, because staleness is a
stable property of the instrument.

---

## 6. Executability — declared before results

EFA at $72.70: spread **1.38** + one tick slippage **1.38** + commission **0.96**
= **round trip 3.71 bps.** Required: response **> 3 × cost = 11.14 bps**.

| lag | response to 1-sd SPY move | vs bar | response to a top-decile SPY move | vs bar |
|---|---|---|---|---|
| **1** | **0.34 bps** | **0.03×** | **0.80 bps** | **0.07×** |
| 2 | −0.01 | −0.00× | −0.02 | −0.00× |
| 5 | −0.03 | −0.00× | −0.07 | −0.01× |
| 10 | −0.03 | −0.00× | −0.07 | −0.01× |

**The best case is short of the bar by a factor of 14.** Even conditioning on the
largest decile of SPY moves, the predicted EFA response is **0.80 bps against a
3.71 bps round trip** — it does not cover one fifth of its own execution cost.

**Kill condition 5 is met by more than an order of magnitude.**

---

## 7. Discovery gate

| # | condition | result | |
|---|---|---|---|
| 1 | SPY consistently leads EFA at ≥1 frozen lag | lag 1 r=+0.0239, stable | technically yes |
| 2 | reverse materially weaker | 0.0131 vs 0.0239 | weaker, both noise |
| 3 | adds information beyond EFA's own prior | ΔR² 0.23% | marginally yes |
| 4 | both directions respond | +0.084 / −0.067 bps | yes |
| 5 | present in both 2021 and 2022 | +0.0285 / +0.0224 | yes |
| 6 | **net response > 3× cost** | **0.34–0.80 vs 11.14 bps** | **FAIL, 14×** |
| 7 | **strongest after the move, not contemporaneous** | **0.8532 at lag 0 vs 0.0239 at lag 1** | **FAIL, 36×** |

**Kill conditions met: 1 (correlation peaks at lag zero), 5 (response far too
small relative to cost), 7 (stale EFA prices create the apparent lag).**

---

## 8. What this actually shows

The structural story behind RP-004 was the stale-NAV wedge: EFA holds developed
markets whose home exchanges are closed during US hours, so EFA's intraday price
is a forecast of a NAV that will not update until tomorrow.

**That wedge is real — and it lives in the NAV, not in the price.** A
contemporaneous correlation of **0.8532** says EFA market makers have already
priced the US move into their quotes **within the same minute**. There is nothing
left over to collect at one minute or beyond. The only lagged signal in the data,
+0.0239 at lag 1, is EFA's 13.42% non-printing rate mechanically deferring a
move into the next bar — an artefact of the instrument not trading, which is
precisely the state in which you cannot trade it.

The prior stated in the proposal — *"at 1-minute resolution between US-listed
liquid ETFs a retail-exploitable lead-lag is near-certain to be absent; I would
not expect it to pass"* — is now measured rather than assumed. **One correlogram
settled it, which is exactly what the proposal said it would cost.**

---

# VERDICT: LEAD AND LAG REJECTED — CLOSE RP-004

No validation. **2023, 2024 and 2025 not read.** No Stage 2. No data acquisition.
No threshold optimisation, volume filter, or alternative instrument pair was
tested, as instructed.

All three proposals from the RP-003/004/005 batch are now closed.
