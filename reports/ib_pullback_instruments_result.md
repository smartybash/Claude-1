# Frozen IB-midpoint pullback on related instruments: the family closes

Frozen specification, unchanged in every respect: **zone B_mid · rejection R2 ·
exit 1.5R**, EZ < 25%, midpoint band ±0.05 IB range, stop at the pullback
extreme, 13:00 expiry, honest fills, same costs. No parameter was touched.

**2021–2025, the related data's span. XLK excluded from the headline pool.
2016–2020 was not opened. Sealed NQ dates were not read.**

---

## 1. The construction transfers. The edge does not.

| instrument | sessions | qualify | reached zone | trades | /mo | risk bps | cost% |
|---|---|---|---|---|---|---|---|
| SPY | 1,253 | 675 | 310 | 179 | 3.0 | 13.01 | 5.12 |
| IWM | 1,249 | 686 | 312 | 178 | 3.0 | 14.93 | 4.47 |
| IJH | 1,161 | 650 | 288 | 170 | 2.8 | 12.41 | 5.37 |
| EFA | 1,244 | 671 | 336 | 196 | 3.3 | 11.50 | 5.80 |
| **QQQ\*** | 1,252 | 674 | 289 | **164** | 2.7 | 14.86 | 4.49 |

The funnel is near-identical everywhere — 2.7–3.3 trades a month, 164–196
trades, comparable risk and cost. **The rule fires the same way on all five
instruments.** Whatever separates them is not the mechanics.

\* QQQ re-run on the same 2021–2025 window for a like-for-like comparison.

---

## 2. Trading results

| instrument | n | win% | avgW | avgL | **exp R** | PF | ddR | strk | yrs | −best5 | +50% c |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 179 | 39.7 | 1.43 | −1.05 | **−0.070** | 0.89 | 26.0 | 14 | 2/5 | −0.114 | −0.098 |
| IWM | 178 | 42.1 | 1.45 | −1.05 | **+0.005** | 1.01 | 21.2 | 11 | 2/5 | −0.038 | −0.019 |
| IJH | 170 | 42.9 | 1.43 | −1.09 | **−0.010** | 0.98 | 16.5 | 9 | 3/5 | −0.055 | −0.038 |
| EFA | 196 | 38.8 | 1.39 | −1.05 | **−0.101** | 0.84 | 26.0 | 9 | 1/5 | −0.142 | −0.130 |
| **POOLED non-QQQ** | **723** | 40.8 | 1.42 | −1.06 | **−0.046** | **0.93** | 40.8 | 14 | 3/5 | −0.056 | −0.073 |
| QQQ\* | 164 | **49.4** | 1.45 | −1.05 | **+0.185** | **1.35** | 8.4 | 5 | **5/5** | +0.145 | +0.161 |

**Clustered by date: SE 0.0499 over 485 shared dates, 95% CI
[−0.1437, +0.0521], t = −0.92.**

**1 of 4 instruments positive** — and that one is IWM at **+0.005**, which is
zero to three decimal places.

### The shape of the result

QQQ on this window is **stronger** than on the full window (+0.185 against
+0.150, 5/5 years, and it even survives top-decile removal at +0.037). Four
other instruments running the identical rule average **−0.046**.

**That is the signature of a single-instrument artefact, not a market
mechanism.** A midpoint pullback is not a QQQ-specific structure; there is no
reason the same geometry should pay on the Nasdaq proxy and cost money on the
S&P, the Russell, mid-caps and developed international.

Long/short offers no refuge: pooled long −0.038, short −0.055. **Both arms
negative.**

---

## 3. The mechanism controls do not reproduce

| control | n | exp R | PF | vs base |
|---|---|---|---|---|
| **BASE (frozen)** | 723 | **−0.046** | 0.93 | — |
| 1 no ending-zone requirement | 1,663 | **−0.039** | 0.94 | **−0.007** |
| 2 touch without rejection | 110 | −0.120 | 0.83 | +0.074 |
| 3 zone shifted 0.25 IB range | 394 | −0.140 | 0.79 | +0.094 |
| 4 opposite directional bias | 368 | **+0.095** | **1.16** | **−0.141** |

Two of the four **invert** relative to QQQ:

- **Control 1 fails outright.** On QQQ the ending-zone condition was
  load-bearing: +0.150 with it, −0.036 without. On non-QQQ the difference is
  **−0.007** — the 0–25% qualification **adds nothing**. The element that
  carried the QQQ result does not exist on four other instruments.
- **Control 4 is better than the rule.** Taking the *opposite* direction on
  qualified sessions returns **+0.095 at PF 1.16**, against the frozen rule's
  −0.046. The directional claim is not merely absent, it points the wrong way.

**Control 4 is not promoted and is not a strategy.** It was declared in advance
as a mechanism check only, it is one of four controls on a family that has just
failed, and a +0.095 result found this way is exactly what the prior families
have repeatedly shown to be noise. Recording it and leaving it is the point.

Controls 2 and 3 do point the right way, but with the base itself negative they
only show that the frozen construction loses less than two worse ones.

---

## 4. The desk decision rule

| # | condition | result | |
|---|---|---|---|
| 1 | pooled expectancy ≥ +0.08R | **−0.046** | **FAIL** |
| 2 | pooled PF ≥ 1.15 | **0.93** | **FAIL** |
| 3 | CI not centred on zero | **[−0.144, +0.052]** | **FAIL** |
| 4 | ≥3 of 4 instruments positive | **1 of 4** | **FAIL** |
| 5 | positive after removing best 5 | **−0.056** | **FAIL** |
| 6 | positive at +50% costs | **−0.073** | **FAIL** |
| 7 | beats no-EZ, touch-only, shifted-zone controls | **beats 2 of 3; fails no-EZ** | **FAIL** |

**0 of 7.** Three independent triggers for closure fire simultaneously: pooled
expectancy below +0.08R, fewer than three instruments positive, and the
mechanism controls not reproducing.

**Concentration diagnostic**, reported as a diagnostic and not a pass/fail per
the amendment: pooled non-QQQ after removing the top decile (73 trades)
**−0.216**. It changes nothing here — the family fails on the headline.

---

## 5. Verdict

# CLOSED. The holdout is not opened.

The 2016–2020 holdout remains **unread and unspent**. Nothing in this result
would be clarified by it: the failure is cross-sectional, not a sample-size
problem, and 1,259 more QQQ sessions cannot explain why SPY, IWM, IJH and EFA
lose money on the identical rule.

**What the QQQ result was.** +0.150 R over 175 trades, every declared criterion
met, all four mechanism controls pointing the right way — and a best-of-18
t of 1.58 that a random search beats 65% of the time. The related-instrument
test was the right next step precisely because the statistics could not settle
it, and it settled it in one run for the cost of no new data.

---

## 6. Methodology amendment, recorded

**The top-decile concentration rule is demoted from a binary pass/fail to a
reported diagnostic**, on the stated reasoning that removing 10% of all trades
changes the economic strategy rather than removing outliers.

This reverses a standing rule adopted at `6c99ff1` and applied **retroactively
to the entire ledger**, so consistency required checking whether any closed
family reopens under it. **None does:**

| family | closed on | independent of concentration? |
|---|---|---|
| IB 1R frozen candidate + 4 re-entry exits | pooled non-QQQ +0.0269, CI spans zero | **yes** |
| IB 1R related instruments (XLK, EFA) | the same pooled estimate | **yes** |
| ORB-Fib continuation (ORB15 A, ORB30 A) | pooled non-QQQ −0.0272, CI spans zero | **yes** |

All nine historical passes were closed on pooled cross-instrument evidence, not
on the concentration rule. **The demotion changes no prior verdict.**

---

## 7. Ledger entry

| screen | sample | outcome |
|---|---|---|
| **IB midpoint pullback + R2 rejection, 1.5R** | QQQ 175 trades; 4 instruments 723 trades | **CLOSED. QQQ +0.150 R (t 1.58, best of 18) did not reproduce: pooled non-QQQ −0.046, CI [−0.144, +0.052], 1 of 4 instruments positive, 0 of 7 desk conditions. The ending-zone condition that carried QQQ adds −0.007 on non-QQQ, and the opposite directional bias beats the rule at +0.095. Holdout not opened.** |

Reproduce: `python3 scripts/orderflow/ib_pullback_instruments.py`.
Full output `reports/ib_pullback_instruments_output.txt`.
