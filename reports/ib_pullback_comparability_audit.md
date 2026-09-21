# Instrument comparability audit — no performance was rerun for this file

Measured on 2021–2025, the window the related-instrument test used. Stop
distances are read from that run's funnel; nothing was re-executed.

---

## 1. Confirmed: three parameters are genuinely dimensionless

Verbatim from the frozen rule:

```
ez = 100.0 * abs(close1030 - exp_lvl) / rng      # rng = that session's own IB range
if use_ez and ez >= EZ_MAX:                      # 25
r = Q["rng"]
c, w = Q["mid"], 0.05 * r                        # midpoint band
sh = shift * r * (-Q["d"])                       # 0.25 shift control
```

**The ending zone, the midpoint band and the shift control are all fractions of
each instrument's own IB range.** They carry no absolute price quantity.

**The measurement confirms it.** If the 25% threshold were mis-scaled, the
qualification rate would diverge across instruments. It does not:

| | QQQ | SPY | IWM | IJH | EFA |
|---|---|---|---|---|---|
| **qualify at 10:30** | 53.8% | 53.9% | 54.9% | 56.0% | 53.9% |
| **reach a trade** | 13.1% | 14.3% | 14.3% | 14.6% | 15.8% |

**A 2.2-point spread on qualification across five instruments whose IB ranges
differ by 2.34×.** The dimensionless machinery transferred correctly.

> **SPY's smaller absolute movement does not invalidate the 25% ending zone.
> That claim is withdrawn in advance — the data does not support it.**

---

## 2. Parameter classification

| # | parameter | class | note |
|---|---|---|---|
| 1 | ending-zone threshold | **1 · instrument-normalised** | fraction of own IB range |
| 2 | midpoint zone width | **1 · instrument-normalised** | ±0.05 of own IB range |
| 3 | shifted-zone control | **1 · instrument-normalised** | 0.25 of own IB range |
| 4 | 2-tick stop buffer | **3 → 2** | fixed absolute in the QQQ run; price-ratio converted in the transfer |
| 5 | minimum stop distance | **2 / 4** | `max(8 NQ pts, 10 × cost)`; the cost arm bound, so it inherited the cost error |
| 6 | maximum stop distance | **3 → 2** | 40 NQ points, date-matched to QQQ bps |
| 7 | **round-trip cost** | **4 · depends on tick size, spread, liquidity** | **NOT adjusted. NQ futures cost applied to five ETFs** |
| 8 | cost as % of risk | **4** | derived from 7; inherits the error |
| 9 | rejection bar definition | **1 · instrument-normalised** | purely ordinal on the instrument's own bars |
| 10 | target distance | **1 · instrument-normalised** | 1.5 × actual risk from actual entry |

**Six of ten were already correct. The failure is concentrated in the cost
model and the two limits that depend on it.**

---

## 3. The comparability measurements

| | med px | ATR 1m bps | IB range bps | stop bps | **stop/ATR** | **zone/ATR** | 1 tick bps | cost charged % of risk | **TRUE cost % of risk** |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | $375.7 | 5.52 | 80.8 | 14.86 | 2.69 | 0.73 | 0.266 | 4.49 | **1.79** |
| SPY | $450.7 | 4.08 | 50.2 | 13.01 | 3.19 | 0.61 | 0.222 | 5.13 | **1.71** |
| IWM | $205.2 | 5.89 | 99.8 | 14.93 | 2.54 | 0.85 | 0.487 | 4.47 | **3.26** |
| IJH | $242.0 | 4.00 | 80.6 | 12.41 | 3.11 | 1.01 | 0.413 | 5.37 | **3.33** |
| **EFA** | **$77.1** | **2.77** | **42.6** | **11.50** | **4.15** | 0.77 | **1.298** | 5.80 | **11.28** |

| quantity | min | max | spread |
|---|---|---|---|
| ATR 1m (bps) | 2.77 | 5.89 | 2.12× |
| IB range (bps) | 42.6 | 99.8 | 2.34× |
| stop / ATR | 2.54 | 4.15 | **1.63×** |
| zone / ATR | 0.61 | 1.01 | **1.64×** |
| **TRUE cost as % of risk** | **1.71** | **11.28** | **6.62×** |

---

## 4. Verdict: the earlier test was not a like-for-like economic test

**Three specific failures.**

**4.1 The cost model is the wrong cost model.** `COST_F = 2.00/30000` is
**NQ futures**: $2.00 on a 30,000 index. It was applied unchanged to five ETFs
whose one-tick floors span **0.222 to 1.298 bps — a 5.8× range**. The true
cost as a share of risk spans **6.62×** across the pool.

**4.2 EFA breaches the project's own rejection rule.** Its true cost is
**11.28% of risk**, above the declared 10% limit. **Under honest costs most EFA
trades should have been rejected before entry, not taken and lost.** EFA
contributed 196 of 723 pooled trades at −0.101 R. It was never economically
eligible.

**4.3 The 2-tick buffer is not the same object across instruments.**

| | 2 ticks in bps | as % of that instrument's stop |
|---|---|---|
| QQQ | 0.53 | **3.6%** |
| SPY | 0.44 | 3.4% |
| IWM | 0.97 | 6.5% |
| IJH | 0.83 | 6.7% |
| **EFA** | **2.60** | **22.6%** |

**On EFA the irreducible tick buffer eats nearly a quarter of the stop.** That
is a market fact, not a parameter choice — you cannot place a stop closer than
one tick.

**The stop/ATR and zone/ATR misalignments (1.63× and 1.64×) are moderate** and
would not on their own invalidate the comparison. **The cost mismatch would.**

### What this does and does not imply

**It does not rescue the result.** Of the five, only EFA was *under*charged;
QQQ, SPY, IWM and IJH were all charged **more** than their one-tick floor.
Correcting costs therefore *improves* three of the four non-QQQ instruments and
*worsens* one. First-order arithmetic on the existing trades:

| | old exp R | cost delta in R | ≈ corrected |
|---|---|---|---|
| SPY | −0.070 | +0.034 | −0.036 |
| IWM | +0.005 | +0.012 | +0.017 |
| IJH | −0.010 | +0.020 | +0.010 |
| EFA | −0.101 | −0.055 | −0.156 |

**A rerun is still required**, because the minimum-stop floor is cost-driven:
lower costs lower the floor and admit different trades. This is a change to the
trade set, not just to pricing. **The arithmetic above is an estimate and is
not the answer.**

---

## 5. Declarations, made before any performance is viewed

Applied to **all five instruments including QQQ**, and QQQ is reported under
**both** its frozen definition and the native one, so any change to QQQ caused
by the renormalisation is visible rather than hidden.

| # | native definition |
|---|---|
| 1 | ending zone, midpoint band, shift control — **unchanged**, already own-IB fractions |
| 2 | **stop buffer = max(2 ticks, 0.10 × ATR1m)** — the fraction is declared here, now |
| 3 | **minimum stop = max(1.0 × ATR1m, 10 × true cost)** |
| 4 | **maximum stop = 6.0 × ATR1m** |
| 5 | **true cost = 1 tick round turn + $0.0035/share commission**, per instrument |
| 6 | cost > 10% of risk still rejects the trade |
| 7 | target = 1.5R from actual entry and actual risk — **unchanged** |

The min/max stop bracket (1.0–6.0 × ATR) was chosen to **contain QQQ's realised
2.69 × ATR with margin on both sides**, so it is not a threshold tuned to
produce an outcome. No per-instrument thresholds. One run.

---

## 6. What the rerun can and cannot settle

**It cannot make cross-instrument profitability a condition for QQQ.** Per the
brief, the related instruments answer two narrower questions:

1. **Does the same dimensionless structure behave similarly elsewhere?**
2. **Was QQQ's result a QQQ-specific effect or discovery-sample luck?**

**If QQQ stays positive and the others stay negative under proper native
normalisation, the classification is QQQ-specific and unresolved — not closed**
— and the correct next test is the untouched **2016–2020 QQQ** period, once,
with the frozen rule.

**The QQQ rule is not changed. No filters are added. The direction is not
inverted, whatever control 4 showed.**
