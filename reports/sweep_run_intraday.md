# Corrected same-day sweep/run test — intraday resolution

**Verdict: NOT VALIDATED (insufficient data depth).** The strategy is neither
confirmed nor rejected. The pipeline is built, causally correct, and runs
end-to-end; the data obtainable in this environment is far too shallow to run
the pre-registered walk-forward, so every number here is **diagnostic only**.

This document is the honest status. It follows the same rule the rest of the
program follows: report exactly what was obtained and stop — do not dress a
10-session diagnostic up as a validated edge, and do not keep re-testing
variants until one clears p≤0.05 by chance.

---

## 1. What data was actually obtained

| symbol | 5-min bars | span | full RTH sessions | source |
|---|---|---|---|---|
| NQ (front, contract 770561204, Sep-2026) | 2174 | 2026-06-17 → 07-06 | 10 | IBKR MCP `get_price_history`, RTH |
| ES (front, contract 649180671, Sep-2026) | 2174 | 2026-06-17 → 07-06 | 10 | IBKR MCP `get_price_history`, RTH |
| QQQ | 1001 | 2026-06-15 → 07-06 | 12 | IBKR MCP `get_price_history`, RTH |
| SPY | 1001 | 2026-06-15 → 07-06 | 12 | IBKR MCP `get_price_history`, RTH |

Daily bars for the pre-session level sets: NQ/ES 61 sessions (3 mo), QQQ/SPY 5
years. All cached to `data/parquet/` (see `manifest.json`); re-loadable without
re-hitting IBKR via `sweeplib.data.load(sym, tf)`.

**Futures roll handling / method used:** the intraday series is a single
explicit front-month contract (Sep-2026 NQ/ES), *not* a stitched or continuous
series, and its 10-session span contains **no roll date**, so there is no roll
jump to exclude. The `scripts/fetch_intraday.py` deep-fetch path (for a machine
with TWS) instead uses IBKR's **continuous contract** (`ContFuture`, method:
continuous — no manual stitching) and additionally writes
`{SYM}_roll_dates.json` so sessions spanning a quarterly roll can be excluded
before any level statistic is computed.

### Why the data is this shallow — and it is not for lack of trying

The spec's data target is 2–3 years of 5-minute bars. That target requires the
`ib_async` deep-fetch path against a running TWS/IB Gateway. **Neither piece is
reachable from this research container:**

- **No local TWS/Gateway.** Ports 7496/7497/4001/4002 are all closed — verified
  directly. `ib.connect('127.0.0.1', 7497, …)` cannot succeed here.
- **The IBKR MCP connector hard-caps every historical request at 1000 bars**
  (`"Step count more than 1000 is not allowed"`) with no `endDateTime` paging
  parameter, so it cannot walk backward to accumulate depth. 1000 five-minute
  RTH bars ≈ 12–13 sessions. That is the ceiling, and it is what you see above.

Per the program's non-negotiable rule ("If IBKR data acquisition fails or is
partial, report exactly what was obtained and stop"), that is what this does.
`scripts/fetch_intraday.py` is written, faithful to the spec's chunk-backward +
pace + cache-every-chunk pattern, ready to produce the real depth the moment
it runs where TWS lives.

## 2. The causal design (the actual fix)

The daily-resolution bug conflated the event with the outcome: it used the
day's own high/low to define a "sweep" and the same day's open-to-close return
to score it, sharing data between definition and measurement (88% win, t=10
before it was caught). The intraday rebuild removes that circularity entirely:

1. **Levels fixed pre-session** from data strictly before the open (PDH/PDL,
   PWH/PWL, confirmed equal-H/L pools, round numbers) — `sweeplib.levels`.
2. **Touch** = the first bar whose high/low trades through a level. Not
   tradeable.
3. **Confirmation window K ∈ {0,1,3}**: close back inside within K bars →
   **sweep**; still beyond at window end → **run**.
4. **Entry at the close of the confirming bar** — strictly after (or at) the
   touch bar's own close, using only information available then. The event
   (touch, from high/low) and the return (from the confirming close forward)
   never share data. Audited: 99/99 NQ trades structurally causal, entries
   always a close at/after the touch, stops/exits always resolved forward.
5. Sweep = fade (stop beyond touch extreme); Run = follow (stop at the level);
   exit flat at EOD (the simplest control, tested first); one entry per level
   per session, **no re-entry** (a deliberate, documented design choice, kept
   out of the walk-forward grid).

The identical state machine (`sweeplib.engine.SweepRunTracker`) drives both the
backtest and the live screener, so what is tested is exactly what is watched.

## 3. Diagnostic results (NOT evidence — depth floor not met)

Full machine-generated tables: [`sweep_run_intraday_results.md`](sweep_run_intraday_results.md).
Regenerate with `python scripts/sweep_run_intraday_test.py`.

Across all four instruments, six variants each (sweep/run × K∈{0,1,3}), at 1×
conservative cost, matched-null resampling (2000 draws, matched on trade count,
per-trade holding time in bars, and direction mix):

- **No variant beats its matched null at even the raw p≤0.05 level** — the best
  raw p is 0.40 (ES sweep K=0); every corrected p is 1.000. The one cell with a
  positive diagnostic Sharpe (NQ run K=3, +4.9 bp/trade, raw p=0.434) does not
  replicate on any other instrument.
- **Run-follow is consistently negative** on ES/QQQ/SPY (−9 to −17 bp/trade),
  i.e. chasing a break of a level and holding to EOD bled in this sample.
- These are 10–12 session reads with 7–26 trades per cell. They are noise at
  this size and are labelled as such.

**No equity-curve / drawdown charts are produced** because the spec ties them
to "whichever variants pass Part B's kill criteria" — none pass, so plotting
them would misrepresent rejected noise as a result.

## 4. Kill-criteria checklist (pre-registered, not adjusted after seeing results)

| # | criterion | status |
|---|---|---|
| 1 | OOS Sharpe ≥ 0.8 | **NOT ASSESSABLE** — needs ≥ ~60 sessions for ≥5 folds; have 10–12 |
| 2 | Beats matched null, corrected p ≤ 0.05 | **FAIL** on diagnostic sample (best corrected p = 1.000) |
| 3 | MaxDD ≤ buy & hold MaxDD over span | mixed; assessable only with real depth |
| 4 | Consistent sign+significance on ≥ 3 of 4 instruments | **FAIL** — the single positive cell is one-instrument |
| 5 | Net CAGR > 0 after 1× cost | **FAIL** for most variants on the diagnostic sample |

**Prior this test was updating:** the daily-resolution version was not
significant (matched-null **p = 0.179**). The intraday diagnostic does nothing
to overturn that prior; it simply lacks the depth to update it in either
direction. The honest statement is: *still not validated, and now tested the
right (causal) way — pending the data depth to make the test conclusive.*

## 5. How to complete the test properly

1. On a machine with TWS/IB Gateway running (paper is fine — read-only):
   `pip install ib_async pandas pyarrow && python scripts/fetch_intraday.py --port 7497 --years 3`
2. It writes `data/parquet/{NQ,ES,QQQ,SPY}_5min.parquet` directly (chunked
   backward, paced, cached per chunk) plus roll-date files.
3. `python scripts/sweep_run_intraday_test.py` — **unchanged**. With ≥ ~60
   sessions the walk-forward becomes feasible and the verdict block flips from
   "NOT ASSESSABLE" to a real pass/fail against the same pre-registered
   criteria. Do not touch K, stops, targets, or pivot tolerance in between —
   that is the tuning-after-OOS trap.

## 6. Part C — live screener (built and tested)

`scripts/live_level_screener.py`: a `rich` in-place dashboard showing current
price, every pre-session level with signed distance and live touch/sweep/run
status, and a rolling event log. It runs the **same** `sweeplib.engine` logic
per bar, so a sweep/run is flagged the instant it confirms.

- **Alerts wired and tested:** every touch and every confirmation fires an HTTP
  POST to `SWEEP_WEBHOOK_URL` (Slack/Discord/Telegram-style) and, with
  `--desktop`, a `notify-send` + terminal bell. Verified end-to-end here: a
  `--replay NQ --force-event` run drove real cached bars through the engine and
  **8/8 touch/confirmation events landed as POSTs** at a local sink.
- **`--selftest`** asserts the alert path fires and the engine classifies a
  planted sweep and a planted run correctly (PASS).
- **Fail-loud:** if the live bar feed stalls (>7 min without a new bar) or
  errors, the dashboard header turns red with the error rather than freezing
  silently.
- **`--live SYM`** uses `reqHistoricalData(keepUpToDate=True)` against TWS
  (needs a running gateway; not runnable in this container).

Dashboard render (static capture): [`img/screener_dashboard.svg`](img/screener_dashboard.svg).

## 7. Deviations from spec

See [`sweep_run_deviations.md`](sweep_run_deviations.md).
