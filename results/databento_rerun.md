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

**Result: 0 of 31 trading claims revived after Benjamini-Hochberg (q = 0.05). Every closed study stays closed on NQ.** Rows reported: 62 (tape, bar, archive, descriptive). The closest misses: B15 IB-by-rejection (+4.6 NQ pt/trade after costs, daily-P&L p 0.054, fails its frozen t > 3) and B31 IB re-entry (p 0.085). Descriptive replications on NQ: FOMC-afternoon volatility (B01), the opening block's larger excursions (B02), and mean-reverting VWAP-displacement / cumulative-delta correlations at 15 minutes (T09) that no frozen trade converts into profit. Archive positives that replicate (A10 daily FVG, A11 compression breakout, A12 oversold bounce) are unregistered multi-day effects and cannot be revived; see decision P7.

| id | study | old verdict | net pt/trade | Sharpe | study p | BH p | final verdict |
|---|---|---|---|---|---|---|---|
| A01 | ICT prior-day sweep + reclaim (archive) | -0.19R, t -2.78 |  |  |  |  | agrees: -0.013R, t -0.40 (gross, 2,035 trades 2010-2026) |
| A02 | NWOG weekend-gap fade (archive) | -0.34R, t -13.2 |  |  |  |  | agrees: -0.271R, t -7.96 (793 gaps) |
| A03 | 15-min ORB + FVG (archive) | PF 1.01 |  |  |  |  | agrees: PF 1.03 gross, +0.015R; median stop 0.17% of price, so NQ costs take it to about zero |
| A04 | initial-balance breakout (archive) | no configuration pays |  |  |  |  | agrees: +0.037R, PF 1.08, t 2.24 gross -- fails PF >= 1.15 and t > 3 before costs |
| A05 | VWAP retest (archive) | +0.049R noise |  |  |  |  | agrees: best cell +0.006R, t 0.23 |
| A06 | fixed-level fade, honest entry (aplus4/aplus5, archive) | -0.047R; best limit cell +0.196R t 1.68, OOS -0.235R |  |  |  |  | agrees: honest entry +0.013R t 0.55; lookahead version +0.715R reproduces the artefact; aplus5 best of 16 cells +0.113R t 2.55 gross (< t 3) |
| A07 | open drive (archive) | +0.099R t 1.84; first half +0.021R |  |  |  |  | agrees (closed): +0.044R t 2.28 at 2R gross, both halves positive on NQ (+0.028 / +0.059) but t < 3 before costs |
| A08 | inventory retracement bar (archive) | rejected |  |  |  |  | agrees: no timeframe beats its null (IRB 36-53% vs null 47-63%) |
| A09 | trendline reversal reconstruction (archive) | 0 of 9 positive under tick execution; best PF 1.03 |  |  |  |  | agrees: 0 of 9 pass on 61 discovery sessions; Model C loses in all nine (PF 0.82-0.91) |
| A10 | daily FVG continuation (archive; NOT a closed study -- inventory error) | positive, unregistered: QQQ 3R +0.476R t 5.14 (27y) |  |  |  |  | replicates positive on NQ: 286 trades, 3R +0.542R, t 4.71 gross (daily risk; costs negligible). Cannot be revived (clarification 4); see P7 |
| A11 | daily compression / range breakout (archive; NOT a closed study -- inventory error) | positive, unregistered (2fed2b4) |  |  |  |  | replicates positive on NQ: 5-day box, 927 trades, 3R +0.366R t 5.88 gross. Cannot be revived; see P7 |
| A12 | daily oversold bounce (archive) | the one real daily effect; not a day trade |  |  |  |  | agrees: NQ 3+ down closes +25bp next day, t 3.19, positive in every 5-year block |
| A13 | sweep/run intraday + POC sweep (archive) | nan |  |  |  |  | not ported: sweeplib rebuilds a cache inside data/ from ~60-session IBKR/Yahoo files; hypothesis covered by study (d) and T04 |
| B01 | FOMC family (descriptive) | 8 of 20 pass; 10 of 20 beat random (descriptive) |  |  |  |  | replicates: 8 of 20 pass Bonferroni, 12 of 20 beat random labels (NQ 2021-2026); descriptive, excluded from BH |
| B02 | RP-009 time-of-day map (descriptive) | 44 NQ sessions cannot support a standalone verdict |  |  |  |  | descriptive rerun on 4,189 NQ sessions: opening block has the largest excursions every year 2010-2026 (close/open median MFE 0.34-0.71); no verdict, outside BH |
| B03 | European vs US session profile | descriptive only, 'NOT A TEST'; no verdict |  |  |  |  | not rerun: no verdict to compare; its question (buy EU-hours data?) is moot, pull A holds full Globex sessions |
| B04 | pullback grid 1 (75eec2c) | 0 of 12 (specification defect) | -0.18 | -0.99 | 1.0000 | 1.000 | stays closed |
| B05 | pullback grid 2 (52b925d) | 0 of 12 | +0.96 | +1.09 | 1.0000 | 1.000 | stays closed |
| B06 | QQQ broad screen (pullback, 16 variants) | 0 of 16 | -0.76 | -0.44 | 1.0000 | 1.000 | stays closed |
| B07 | ORB + session VWAP filter (16 variants) | 0 of 16 | -0.54 | -0.37 | 1.0000 | 1.000 | stays closed |
| B08 | opening-range height, wide arm (4 variants) | 0 of 4 | -0.36 | -0.16 | 1.0000 | 1.000 | stays closed |
| B09 | regime forecastability (descriptive) | 0 of 14 |  |  |  |  | agrees: 0 of 14 on NQ full history and 0 of 14 on 2021-2026 |
| B10 | mechanised discretionary pullback (8 variants) | 0 of 8, below the random walk | -1.00 | -0.28 | 1.0000 | 1.000 | stays closed |
| B11 | prior-day levels predictive (price levels only) | 0 of 13 |  |  |  |  | agrees: 0 of 5 price levels pass reaction-at-touch (best POC 53.0% vs 55% bar), 0 of 3 clustering sets pass (best ratio 0.906 vs 0.90 bar); NQ full history, price levels only |
| B12 | setup grading scheme | worse than random and backwards |  |  |  |  | agrees: grading fails (not monotonic A+>=A>=B; spread does not beat random labels) |
| B13 | calendar classification (descriptive) | mechanism families show nothing |  |  |  |  | near-agreement: 1 of 52 clears Bonferroni and random labels (Wednesday OR ratio -0.07); 9 of 52 beat random vs 2.6 expected; no mechanism family (descriptive, outside BH) |
| B14 | IB ending zone + pullback rejection (18 variants) | one variant cleared in-sample; holdout break-even; closed | +1.31 | +0.30 | 1.0000 | 1.000 | stays closed |
| B15 | IB by rejection, Stage 3 trade (4 targets) | break rate is geometry; the trade fails | +4.61 | +0.54 | 0.0537 | 1.000 | stays closed |
| B16 | ORB + Fibonacci (8 variants) | reversal unresolvable; continuation not demonstrated; closed | +5.50 | +0.35 | 0.5925 | 1.000 | stays closed |
| B17 | compressed range resolution (6 variants, BOTH arm) | economics met, mechanism falsified | +4.63 | +0.24 | 0.9944 | 1.000 | stays closed |
| B18 | pre-open conditioning (descriptive) | null replicates on non-price predictors |  |  |  |  | agrees: no pre-open condition predicts efficiency or direction beyond the corrected threshold (NQ 2021-2026) |
| B19 | trade conditioning on pre-open variables | direction closes (nothing beat the permuted maximum) |  |  | 0.7638 | 1.000 | stays closed |
| B20 | RP-002 opening auction inventory (descriptive) | descriptive fail |  |  |  |  | no mechanical verdict printed by the frozen script (RP-002's registered verdict was a written reading); NQ S1 continuation/rejection states are small and unstable by year -- nothing contradicts the rejection; registered decision rule not mechanically re-applied |
| B21 | RP-003 beta residual, NQ/ES (descriptive) | closed |  |  |  |  | no mechanical verdict printed; NQ/ES residual extremes revert ~0.5-2 bps with ~50% expansion rates -- nothing contradicts the rejection; registered rule not mechanically re-applied |
| B22 | RP-005 close auction flow (descriptive) | closed |  |  |  |  | no mechanical verdict printed; NQ closing-flow effects -1.5 to +1.2 bps, retrace rates ~60% in every size bucket -- nothing contradicts the closure; registered rule not mechanically re-applied |
| B23 | RP-007 1A1 level validity (descriptive) | a precisely measured zero |  |  |  |  | agrees: no level family passes alone; nothing adds information over shifted or random levels |
| B24 | RP-008 regime validity (descriptive) | closed |  |  |  |  | agrees: HI-LO stop-out spread <= 5.7 pts vs 10-pt bar; neighbouring thresholds reproduce; time of day dominates (11:30 vs 09:30 up to -18.8 pts) |
| B25 | RP-012A relative volume (descriptive; NQ/ES for QQQ/SPY) | rejected: relative volume adds nothing beyond displacement |  |  |  |  | agrees: Stage 0 counts pass, but NQ state A at 15 min is +0.25 bp (clustered t -0.93) and no instrument shows a relative-volume effect |
| B26 | RP-13 FVG multi-timeframe (4 primary timeframes) | null, closed | +0.66 | +0.15 | 1.0000 | 1.000 | stays closed |
| B27 | level rules, fade and break (15 cells) | fade loses; PDH/PDL break tilt < cost | +0.17 | +0.15 | 1.0000 | 1.000 | stays closed |
| B28 | structure trade by timeframe (10 cells) | negative at every timeframe | +0.39 | +0.10 | 1.0000 | 1.000 | stays closed |
| B29 | gap structure trade (as drawn, with control) | closed: structure beats blind control but the trade loses | -1.42 | -0.27 | 0.8608 | 1.000 | stays closed |
| B30 | gap fill base rate / gap trade | base rate only; structure trade on 5 tape sessions |  |  |  |  | not rerun: trade superseded by B29 (2,680 sessions); base rate is descriptive |
| B31 | reopened IB re-entry and VWAP hold (8 cells) | one candidate frozen; holdout break-even; closed | +4.67 | +0.57 | 0.0847 | 1.000 | stays closed |
| B32 | ib_study.py (duplicate of B15) | same study as B15 |  |  |  |  | duplicate of B15; counted once |
| T01 | absorption 2x2 | dead | -1.91 | -12.21 | 1.0000 | 1.000 | stays closed |
| T02 | tape hypothesis sweep | dead except H3 cell | +0.35 | +0.57 | 1.0000 | 1.000 | stays closed |
| T03 | CVD divergence audit | dead | -2.79 | -7.26 | 0.9996 | 1.000 | stays closed |
| T04 | tape level fade (audit grid) | dead: shrank with sample; assumed fill | -2.02 | -4.65 | 1.0000 | 1.000 | stays closed |
| T05 | weight rule (fade light levels) | dead: OOS -1.36 pt | -0.88 | -1.63 | 0.7865 | 1.000 | stays closed |
| T06 | weight rule + 1.5% CVD filter | dead (OOS) | +0.57 | +0.98 | 0.3162 | 1.000 | stays closed |
| T07 | CVD CHANGE gate on structure break | dead: does not reproduce | -2.45 | -0.74 | 1.0000 | 1.000 | stays closed |
| T08 | gap + early CVD (direction only) | direction only (p 0.028, 6 sessions) | +8.71 | +3.23 | 0.0095 |  | direction p 0.0095; not a candidate (lookahead) |
| T09 | IC harness (descriptive) | IC is not edge |  |  |  |  | replicates as correlation: vwap_disp IC -0.255 at 15 min, t -15.1, 100% sessions; cvd -0.254, t -12.5; not a trading test |
| T10 | VWAP displacement, three registered exits | cannot be won at 30 sessions; holdout sealed | -5.63 | -0.67 | 1.0000 | 1.000 | stays closed |
| T11 | order-size / sweep gates on structure break | dead: month D -0.434R | +0.33 | +0.09 | 1.0000 | 1.000 | stays closed |
| T12 | range filter on structure break (magnitude) | rejected | -19.73 | -3.69 | 0.9629 | 1.000 | stays closed |
| T13 | footprint shapes (absorb_lo priced) | dead | -8.38 | -5.01 | 1.0000 | 1.000 | stays closed |
| T14 | footprint levels (revisit) + placebo | dead: placebo pays the same | -1.06 | -0.39 | 1.0000 | 1.000 | stays closed |
| T15 | order-flow batch A B C E (registered bar) | 0 of 12 (A B C E: 0 of 8) | -1.77 | -2.43 | 1.0000 | 1.000 | stays closed |
| T16 | filter survey, tape families | no filter | +14.75 | +3.46 | 1.0000 | 1.000 | stays closed |
| T17 | CVD LEVEL gates on structure break | dead | -2.38 | -0.53 | 1.0000 | 1.000 | stays closed |

## 4b. Order-flow hypotheses OF-1..OF-4 — discovery (provisional)

Pre-registered at `665c1e4` (`reports/orderflow_h_preregistration.md`). Data-inspired by the step-4 tape reruns, so discovery is a development set; the holdout (read once, at the very end) and the P2 top-up are the real tests.

| hypothesis | trades | net pt/trade | Sharpe | daily-P&L t | Holm p | discovery |
|---|---|---|---|---|---|---|
| OF-1 VWAP reversion | 195 | -4.16 | -3.34 | -1.64 | 1.0000 | fails |
| OF-2 CVD reversion | 248 | -0.45 | -0.38 | -0.19 | 1.0000 | fails |
| OF-3 sweep reversal | 290 | +2.84 | +2.61 | +1.28 | 0.4090 | fails |
| OF-4 opening flow, gap days | 21 | -21.52 | -5.96 | -2.93 | 1.0000 | fails |

Per-study output: `reports/step4/<id>_output.txt`; frozen scripts' own output:
`reports/step4/<id>_frozen_output.txt`.

## 5. Next tests

- **P6** decides whether RP-011 runs (and on what footing, given the disclosure
  in its addendum). T18 (RP-010) waits for the same decision.
- Step 4 is complete except T18 (RP-010), held with P6; B03, B30, A13 not rerun
  (reasons in the table); X01-X08 need depth, options or other instruments.
- OF-1..OF-4 all failed discovery, so none goes to the holdout. The D2 holdout
  is still unread; it is reserved for RP-011 if P6 lets RP-011 run.
- **P7**: whether to register a forward-only test of the three multi-day daily
  effects that replicate on NQ.
- **P2** (early November): top-up of fresh sessions from 2026-09-25 as a
  confirmation-only holdout, within the cap.
