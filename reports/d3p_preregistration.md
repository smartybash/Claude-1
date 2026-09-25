# D3P: prop-compatible oversold bounce — pre-registration

**Registered 2026-09-25, before the rule below has been computed on any data.**
Requested by the user as a new test with no spend (the bars are already bought).
Pass = added to forward paper-tracking; fail = closed.

## What is already known (seen-data disclosure)

- **The D3 signal is not new.** It is the frozen D3 signal of the daily-effects
  registration (`reports/daily3_preregistration.md`, 3390a46, repair R7). D3 itself,
  long from the 15:59 close to the next 15:59 close, was run on this same NQ data
  (2010-06-07 → 2026-09-24) in the seen-data context run: 339 trades, +$622/trade,
  null p 0.0016.
- **The intraday leg is partly known too.** The archive's oversold study
  (`reports/oversold_long.txt`, section 5, QQQ/SPY daily data) split the D3 trade
  into its overnight leg (close → next open: QQQ +14.0 bp) and the full hold
  (close → next close: QQQ +37.4 bp). That implies a next-day open → close leg of
  about +23 bp on QQQ, not costed and not tested against a null. It has never been
  computed on NQ, costed, or put against the exposure-matched null.
- Everything below runs on **seen data, 2010-06-07 → 2026-09-24**, and is labelled
  that way. A pass does not show an edge; it only earns a place in forward
  paper-tracking.

## Rule (frozen)

- **Bars:** NQ continuous front month (Databento `GLBX.MDP3` `NQ.v.0`), RTH 1-minute
  bars, ratio back-adjusted. These are the same bars, day filter (≥ 300 one-minute
  bars) and daily-bar build as `scripts/databento/daily3.py`. Real points = adjusted
  points ÷ the trade session's factor.
- **Signal (D3, R7), evaluated at 15:59 ET on session i:** the 15:58 bar's close is
  below session i−1's RTH close, **and** session i−1's close < session i−2's close
  < session i−3's close.
- **Trade:** long **1 NQ** at the **RTH open of session i+1** (the open of its
  first RTH 1-minute bar). Exit at **that session's RTH close** (the close of its
  last RTH 1-minute bar, normally 15:59). No stop, no target, **flat overnight**.
  Session i+1 is the next session in the daily series; half days (< 300 bars) are
  not in the series, the same as for D3.
- **Costs:** NQ $2.25 + 1 tick per side ($14.50 per round trip). This is the
  step-4 rule, the same cost as D3. No roll can occur inside one session.

## Test

- **Null:** 5,000 exposure-matched random-entry lists. Each list has the same
  number of trades. Each trade is long, enters at a session's RTH open, exits at
  the same session's RTH close, and pays the same cost. Its session is drawn
  uniformly from the sessions in the window. This matches the null in the
  daily-effects registration §3, with a hold of zero sessions and entry and exit
  at the open and the close. Market drift is matched, so a rule that only
  captures NQ's intraday drift does not pass.
- **Statistic:** total net P&L in NQ dollars over the window. p = (1 + number of
  random totals ≥ actual) ÷ 5,001. Seed 20260925.
- **Pass:** total net P&L > 0 **and** p ≤ 0.05. This is one primary test with no
  multiplicity adjustment (a single rule, a single statistic).
- **Pass →** D3P joins D1–D3 in forward paper-tracking from 2026-09-25. At the
  first review (2027-09-25) the family becomes four rules, still Holm-adjusted.
- **Fail →** D3P is closed. It is not re-tuned: no other entry times, exits,
  filters or regimes.

## Descriptive only (cannot change the verdict)

Trades per year, $/trade, win rate, profit factor, Sharpe (daily P&L), max
drawdown per NQ and per MNQ, and the worst single-trade loss per NQ and per MNQ
(relevant to a prop daily-loss limit). Also: the two halves of the window
(2010-06-07 → 2018-06-30 and 2018-07-01 → 2026-09-24), the same rule at MNQ costs
($0.62 + 1 tick per side, 1.12 pt round trip), and D3's overnight leg on the same
signals (15:59 close → next RTH open), so the split of D3's return between night
and day is visible.

Script: `scripts/databento/d3p.py`, committed with this file before its first run.
Output: `reports/d3p_result.md`, `reports/d3p_output.txt`.
