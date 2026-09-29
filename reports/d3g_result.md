# D3-G, ES replication and prop simulator — results (seen data)

Registered `reports/d3g_preregistration.md` (0146a06) before any run. Each test run
once on 2026-09-29. Outputs: `reports/d3g_output.txt`, `reports/prop_sim_output.txt`.

## Verdicts: all four rules pass → forward paper-tracking from 2026-09-29

| rule | trades | $/trade | PF | Sharpe | total | null 95th pct | p | Holm p | verdict |
|---|---|---|---|---|---|---|---|---|---|
| **D3-G/A** NQ, 18:00 reopen → RTH close (primary) | 339 | +$545 | 1.71 | +0.70 | **+$184,752** | $123,822 | 0.0036 | **0.0060** | **PASS** |
| D3-G/B NQ, 18:00 reopen → RTH open | 339 | +$329 | 1.67 | +0.62 | +$111,672 | $74,037 | 0.0030 | 0.0060 | PASS |
| ES-D3 (RTH close → next close; holds through the close) | 345 | +$398 | 1.74 | +0.74 | +$137,195 | $70,324 | 0.0004 | 0.0008 | PASS (replication only) |
| ES-G/A ES, 18:00 reopen → RTH close | 345 | +$370 | 1.65 | +0.67 | +$127,520 | $71,632 | 0.0004 | 0.0008 | PASS |

Figures are per 1 NQ or 1 ES, after the step-4 costs, against 5,000
exposure-matched random-entry lists. The random lists take the same overnight
session at random dates, so the market's overnight drift is already taken out:
+$98 per NQ session and +$48 per ES session.

**Prop compatibility:** the G rules enter at the 18:00 ET reopen and exit by
15:59. That is inside one trading day at Apex (flat by 16:59) and Lucid (flat by
16:45). ES-D3 holds through the close, so it cannot be traded there. It counts
as evidence that the mechanism replicates.

## What tempers it (descriptive; does not change a verdict)

- **Seen data.** D3 on NQ was already known to work. The G variant keeps
  about 88% of D3's net per trade: +28.0 pt gross per trade, giving up a
  +2.5 pt slice from 15:59 to 18:00. It passing was likely. The honest test is the forward paper-tracking.
- **The edge is concentrated after 2018.** NQ D3-G/A: 2010-06 → 2018-06 +$47 per
  trade (PF 1.14), 2018-07 → 2026-09 +$1,089 per trade (PF 1.88). D3-G/B's first
  half is flat (+$6 per trade). 2026 alone contributes +$66,850 of NQ G/A's
  +$184,752. ES is steadier: its first half is positive at PF 1.45.
- **NQ and ES are one bet, not two.** On the 201 sessions where both signal, their
  per-trade P&L correlates at +0.94. Each market also has about 140 signals of
  its own.
- **Big single-trade swings.** Worst trade for NQ G/A is −$12,554 per NQ
  (−$1,256 per MNQ). At 1 MNQ, 5% of trades show an open loss worse than −$756.

## Prop simulator: this rule alone does not pass evaluations well

Evaluations were started on each of 3,931 historical sessions and replayed on the
actual trades, with conservative mechanics. The best cells:

| rule / account | size | pass ≤ 30 d | pass ≤ 90 d | pass ≤ 365 d | fail ≤ 365 d |
|---|---|---|---|---|---|
| NQ G/A, Apex intraday | 4 MNQ | 4.2% | 9.8% | 16.2% | 43.8% |
| NQ G/A, Apex EOD | 6 MNQ | 5.9% | 14.1% | 28.7% | 47.3% |
| NQ G/A, Lucid Flex | 1 MNQ | 0.0% | 0.8% | 11.9% | 5.3% |
| ES G/A, Lucid Flex | 5 MES | 0.1% | 4.7% | 27.8% | 38.5% |

(Full grid: `reports/prop_sim_output.txt`.)

Why it fails as a stand-alone evaluation strategy:
- **Too slow.** About 21 trades a year at +$54 per MNQ. Reaching $3,000 takes
  roughly 55 trades at 1 MNQ, about 2.5 years.
- **Too volatile for the drawdown limit at the size that would be fast enough.**
  Above 3 micros, one bad night plus the trailing threshold ends more
  evaluations than reach the target. Failure beats passing at almost every size
  that passes within 90 days at a useful rate.

**What it could be instead:** a low-frequency overlay in an account that is
already funded, at 1–2 micros, or one sleeve among several uncorrelated
strategies. Passing an evaluation needs a higher-frequency edge; nothing
intraday has shown one yet. Your own trades (the harness) are the next place to
look.

## Next

- Paper-tracking of D3-G/A, D3-G/B, ES-G/A and ES-D3 from 2026-09-29 (review with
  the P7 family on 2027-09-25). ES bars are added to the monthly P8 pull (well
  under $1).
- The simulator is ready for your Tradovate trades and for any combination of
  sleeves.
