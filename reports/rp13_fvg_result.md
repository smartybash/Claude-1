# RP-13 — FVG family, multi-timeframe: discovery result

Pre-registered at `reports/rp13_fvg_preregistration.md` (`adb6226`) before any
code existed. Harness `scripts/orderflow/rp13_fvg.py`; raw output
`reports/rp13_fvg_output.txt`. QQQ 1-minute RTH 2016-01-05 → 2026-08-31 as the
declared substitute for NQ. **No out-of-sample block exists.**

## 0. Gate and verification

Platform suite, run by the harness first: **PASS 139, FAIL 0.**

Eight 1-minute trades were re-derived outside the harness — ATR at C1, gap and
displacement multiples, the PDH/PDL raid within five bars, entry at the open
after the touch, stop-first honest fills, 2R target, cost in R. **8 of 8 match.**

**Two harness defects found and fixed before this write-up:**

- When the entry open sat numerically on the stop, floating point left a
  "risk" of ~1e-13, and cost ÷ risk produced a mechanism-control mean of
  −1.3 billion R. The frozen void rule ("entry at or beyond the stop") is now
  float-safe. Sub-penny risks are kept, because QQQ bars carry half-cent prints.
- An empty control arm crashed the summary. Now reported as n = 0.

## 1. Counts before any R

2,658 sessions (21 half days excluded), 128 months, 1,036,510 one-minute bars.

| TF | 3-bar gaps with sweep | **valid FVGs** | **valid / month** | your prior / month | trades | trades / month |
|---|---|---|---|---|---|---|
| 1m | 4,473 | 395 | **3.1** | 50–100 | 346 | 2.7 |
| 2m | 3,157 | 315 | **2.5** | 30–60 | 272 | 2.1 |
| 3m | 2,598 | 248 | **1.9** | 20–40 | 207 | 1.6 |
| 5m | 2,127 | 215 | **1.7** | 12–25 | 179 | 1.4 |
| 15m | 1,421 | 162 | 1.3 | 5–12 | 113 | 0.9 |
| 30m | 1,096 | 110 | 0.9 | 3–6 | 68 | 0.5 |
| 60m | 806 | 63 | 0.5 | 1–4 | 16 | 0.1 |

**The priors were 15–30 times too high.** Requiring a gap of at least one ATR,
a displacement candle of at least 1.5 ATR, and a same-direction PDH/PDL raid
within five bars leaves **1.7–3.1 setups a month** at the primary resolutions.

**Frozen grid rule applied before any R:** all four primary timeframes fall
below 12 setups a month and are **demoted to diagnostic**. **The primary set is
empty.** Nothing in this study can promote, and every R below is descriptive.
The realised n (179–346) is also far below the power table's assumptions
(500–8,000), so the stated MDEs do not hold. At n = 346 the 1m MDE is about
±0.16R.

Cost/risk passes everywhere (median 6.8% at 1m down to 1.1% at 60m). The
ATR-scaled stop does fix the cost problem, as the brief intended.

## 2. R, net of cost — all descriptive

| TF | n | mean R | 90% lower | t | incl. entry bar | win % | long | short |
|---|---|---|---|---|---|---|---|---|
| 1m | 346 | **−0.152** | −0.280 | −1.96 | −0.181 | 33.5 | −0.361 | −0.024 |
| 2m | 272 | **−0.325** | −0.470 | **−3.69** | −0.272 | 28.3 | −0.291 | −0.350 |
| 3m | 207 | **−0.249** | −0.544 | −1.39 | −0.080 | 35.3 | −0.658 | −0.003 |
| 5m | 179 | **−0.018** | −0.191 | −0.17 | −0.071 | 37.4 | −0.154 | +0.042 |
| 15m | 113 | −0.375 | −0.600 | −2.75 | −0.276 | 31.0 | −0.202 | −0.463 |
| 30m | 68 | +0.002 | −0.192 | +0.02 | −0.019 | 41.2 | −0.008 | +0.005 |
| 60m | 16 | −0.010 | −0.216 | −0.08 | +0.003 | 56.2 | — | — |

**All four primary timeframes have a net mean ≤ 0.** The entry-bar-inclusive
sensitivity does not change a sign at any primary timeframe. By year, 1m is
positive in 2 of 11 years and 2m in 2 of 11.

## 3. Controls — descriptive

**Mechanism (registered test: control net ≥ primary net → fail).** Passes at
every timeframe. **But the registered test is biased toward passing:** unfiltered
three-bar gaps can be a cent wide, so the control carries a median cost of
8–18% of risk and loses on cost alone. The gross comparison, a diagnostic added
after the first run and not the registered test, still favours the filter:

| TF | primary gross | control gross |
|---|---|---|
| 1m | −0.053 | −0.474 |
| 2m | −0.242 | −0.775 |
| 3m | −0.187 | −0.665 |
| 5m | +0.030 | −0.372 |

The displacement and gap filters do select better behaviour than any gap after a
sweep. They improve a losing selection. They do not produce a winning one.

**Placebo** (random windows, same ATR-width zones, same direction): **as good or
better than the real FVGs at 1m (−0.094 vs −0.152), 2m (−0.189 vs −0.325), 3m
(−0.198 vs −0.249), 15m and 30m.** Only 5m is worse (−0.161 vs −0.018). By the
brief's own criterion, the pattern is not doing the work.

**Timing:** at 1m the 09:30–11:00 subset is +0.042 (n 179) against −0.361 for
the rest; at 5m +0.106 (n 102) against −0.183. That is what a time-of-day bet
looks like, and it isn't claimable.

**iFVG:** beats the primary at 1m, 2m, 3m and 15m (for example 3m +0.091 against
−0.249), and reaches +2.198 at 30m on **n = 11**. None of these is claimable, and
the brief bars iFVG as a rescue.

**Max-statistic permutation:** not run. No primary timeframe remained to test.

## 4. Promotion table

| criterion | 1m | 2m | 3m | 5m |
|---|---|---|---|---|
| 1 expectancy ≥ +0.10R, CI > 0 | ✗ | ✗ | ✗ | ✗ |
| 2 ≥ 12 trades/month | ✗ (2.7) | ✗ (2.1) | ✗ (1.6) | ✗ (1.4) |
| 3 trades × expectancy ≥ 2R | ✗ | ✗ | ✗ | ✗ |
| 4 OOS drawdown ≤ 6R | ✗ no OOS | ✗ | ✗ | ✗ |
| 5 MC pass ≥ 45% | not run | — | — | — |
| 6 cost/risk ≤ 10% | ✓ | ✓ | ✓ | ✓ |
| 7 mechanism control | ✓ (registered, biased) | ✓ | ✓ | ✓ |
| 8 permutation p < 0.05 | not run | — | — | — |

## 5. What this establishes

- The ATR-scaled stop **does** fix the cost problem that killed the compression
  family: cost is 1–7% of risk.
- The filters **do** select better than unfiltered gaps. But the selection is
  still negative, and random zones of the same width do as well.
- The frozen filters make the family **commercially impossible regardless of
  edge**: 1.4–2.7 trades a month against a bar of 12.
- The earlier positive FVG results in this repository (`f2bab1f`, `0761d41`)
  used different rules — swing stops, trend filters, no ATR floor, no sweep —
  and are **neither confirmed nor refuted** by this run.

---

## Verdict

> **Null at all four primary timeframes. FVG family, as frozen, closed.**

Net mean ≤ 0 at 1m, 2m, 3m and 5m, which triggers the registered falsification
rule. Independently, no timeframe reaches a sixth of the frequency bar, so the
family could not promote even with a positive mean. No rescue through iFVG,
order blocks, Silver Bullet or the 09:30–11:00 subset: those are separate
families requiring their own pre-registration.
