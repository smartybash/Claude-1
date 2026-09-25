# Databento programme — results

Branch `claude/databento-rerun`. Lifetime Databento spend **$84.54** of the $125
cap (plan $84.54, every job billed at its estimate; ledger
`data/databento_ledger.csv`). Nothing here is promoted on a backtest.

## 1. New studies (a)–(e), against the kill criteria

Kill criteria for (a)–(e): Sharpe ≥ 0.8, profit factor ≥ 1.3, beats the random-direction null at
Holm p ≤ 0.05 (plus Sharpe ≥ buy-and-hold for the overlay). Decisive block
2010–2020, labelled *"never used for this hypothesis; read by other daily
studies, incl. overnight gap base rates"*.

| study | decisive-block result | verdict |
|---|---|---|
| (a) overnight drift overlay, NQ | Sharpe +0.81 = always-overnight +0.81; null p 0.32; buy-and-hold +0.84; PF 1.23 | **killed** (forward data is the only true test) |
| (b) regime switch, strict replication | Sharpe −1.00, PF 0.75, permutation p 0.99 | **closed permanently** |
| (c) Zarattini noise-boundary momentum | ES Sharpe −0.24; NQ +0.61 (null p 0.0006), PF 1.16 | **killed** (closest miss) |
| (d) liquidity sweep PDH/PDL/ONH/ONL | Sharpe −0.69, loses in 9 of 11 years | **killed** |
| (e) gap-and-go / gap-fade / PDH-PDL breakout / intraday Donchian | Sharpe −0.09 / +0.01 / −0.16 / +0.14 | **all killed** |

Details: `reports/db_a_overnight_drift_result.md`, `db_b_regime_switch_result.md`,
`db_cd_result.md`, `db_e_result.md`.

## 2. RP-011 on pull B

**Stopped at the registered quality gate:** 27 of 65 discovery sessions pass
(50 needed). 60 pass everything except the ±2% volume reconciliation to CME
cleared volume, which the tick feed misses by a steady 1–3.5% (block and
spread-leg volume not in the outright feed). No RP-011 window was built.
Decision **P6** in `reports/decisions_pending.md`; the holdout is untouched.
`reports/rp011_stage1_result.md`.

## 3. Power of 3

Specification drafted and waiting for your approval (**P1**). Not tested.

## 4. The repository's closed studies on NQ (step 4)

Pre-registered at `reports/step4_preregistration.md` (inventory
`reports/step4_inventory.csv`), with Clarification 1 (the p entering BH is
one-sided in the profitable direction) and Clarification 2 (BH covers trading
claims only; descriptive studies are judged on their own test). Tape studies use
the 61 discovery sessions; bar studies use NQ 1-minute, full 2010-06-07 →
2026-09-24, with 2021–2026 as the like-for-like line. Costs per side NQ $2.25 +
1 tick, MNQ $0.62 + 1 tick, or the frozen spec's own cost if stricter.

Studies reported so far: **23** of 63 portable. Trading claims with a p: **18**. Frozen pass bar met after NQ costs: **0**. BH is computed once, when the batch is complete.

| id | study | old verdict | net pt/trade | Sharpe | study p (1-sided, Holm) | new verdict (before BH) |
|---|---|---|---|---|---|---|
| B01 | FOMC family (descriptive) | 8 of 20 pass; 10 of 20 beat random (descriptive) |  |  |  | replicates: 8 of 20 pass Bonferroni, 12 of 20 beat random labels (NQ 2021-2026); descriptive, excluded from BH |
| B02 | RP-009 time-of-day map (descriptive) | 44 NQ sessions cannot support a standalone verdict |  |  |  | descriptive rerun on 4,189 NQ sessions: opening block has the largest excursions every year 2010-2026 (close/open median MFE 0.34-0.71); no verdict, outside BH |
| B03 | European vs US session profile | descriptive only, 'NOT A TEST'; no verdict |  |  |  | not rerun: no verdict to compare; its question (buy EU-hours data?) is moot, pull A holds full Globex sessions |
| B04 | pullback grid 1 (75eec2c) | 0 of 12 (specification defect) | -0.18 | -0.99 | 1.0000 | stays closed |
| B05 | pullback grid 2 (52b925d) | 0 of 12 | +0.96 | +1.09 | 1.0000 | stays closed |
| B06 | QQQ broad screen (pullback, 16 variants) | 0 of 16 | -1.00 | -0.63 | 1.0000 | stays closed |
| T01 | absorption 2x2 | dead | -1.91 | -12.21 | 1.0000 | stays closed |
| T02 | tape hypothesis sweep | dead except H3 cell | +0.10 | +0.15 | 1.0000 | stays closed |
| T03 | CVD divergence audit | dead | -2.79 | -7.26 | 0.9990 | stays closed |
| T04 | tape level fade (audit grid) | dead: shrank with sample; assumed fill | -2.05 | -5.60 | 1.0000 | stays closed |
| T05 | weight rule (fade light levels) | dead: OOS -1.36 pt | -0.88 | -1.63 | 0.1943 | stays closed |
| T06 | weight rule + 1.5% CVD filter | dead (OOS) | +0.57 | +0.98 | 0.1509 | stays closed |
| T07 | CVD CHANGE gate on structure break | dead: does not reproduce | -2.45 | -0.74 | 1.0000 | stays closed |
| T08 | gap + early CVD (direction only) | direction only (p 0.028, 6 sessions) | +8.71 | +3.23 | 0.0095 | direction p 0.0095; not a candidate (lookahead) |
| T09 | IC harness (descriptive) | IC is not edge |  |  |  | replicates as correlation: vwap_disp IC -0.255 at 15 min, t -15.1, 100% sessions; cvd -0.254, t -12.5; not a trading test |
| T10 | VWAP displacement, three registered exits | cannot be won at 30 sessions; holdout sealed | -5.63 | -0.67 | 1.0000 | stays closed |
| T11 | order-size / sweep gates on structure break | dead: month D -0.434R | +0.33 | +0.09 | 1.0000 | stays closed |
| T12 | range filter on structure break (magnitude) | rejected | -19.73 | -3.69 | 0.9960 | stays closed |
| T13 | footprint shapes (absorb_lo priced) | dead | -8.38 | -5.01 | 1.0000 | stays closed |
| T14 | footprint levels (revisit) + placebo | dead: placebo pays the same | -1.06 | -0.39 | 1.0000 | stays closed (ordinary-rung control empty at 0.25: MIN_RUNG_VOL 200 was set on the 5-pt grid) |
| T15 | order-flow batch A B C E (registered bar) | 0 of 12 (A B C E: 0 of 8) | -1.77 | -2.43 | 1.0000 | stays closed; C1/C2 pass IC and null gates (t -5.2) but the frozen quintile trade loses: correlation that does not trade |
| T16 | filter survey, tape families | no filter | +14.75 | +3.46 | 1.0000 | stays closed |
| T17 | CVD LEVEL gates on structure break | dead | -2.38 | -0.53 | 1.0000 | stays closed |

Per-study output: `reports/step4/<id>_output.txt`; frozen scripts' own output:
`reports/step4/<id>_frozen_output.txt`.

## 5. Next tests

- **P6** decides whether RP-011 runs (and on what footing, given the disclosure
  in its addendum). T18 (RP-010) waits for the same decision.
- Remaining step-4 studies continue in the registered order; BH is computed once,
  when the batch is complete.
- Order-flow hypotheses on the discovery ticks (at most five, provisional) are
  still to be registered.
- **P2** (early November): top-up of fresh sessions from 2026-09-25 as a
  confirmation-only holdout, within the cap.
