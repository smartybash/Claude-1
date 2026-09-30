# Two economically motivated, higher-frequency sleeves — pre-registration

**Registered 2026-09-30, before either rule below has been computed on any data.**
Requested by the user on 2026-09-30 ("Run the pre registered search for edge on
economic reasons as suggested"). The brief: at most two mechanisms, each with a
stated economic reason and a trade frequency high enough to help pass prop
evaluations. Pre-registered, with a discovery/holdout split. No spend: the NQ
and ES 1-minute bars are already bought.

## 0. Prior exposure (disclosure)

- The bars (NQ and ES, 2010-06-07 → 2026-09-24) have been read by many earlier
  studies. **Neither hypothesis below has been tested on them as a directional
  return effect.** Repository searches: no market-intraday-momentum test (RP-006B
  was *cross-sectional* ETF momentum, closed for lack of data). The calendar
  classification study found month-end and first-of-month days flat on
  *volatility and range* statistics (QQQ, about 1,400 sessions; first-of-month
  opening-range ratio beat random but failed Bonferroni). It never measured
  direction, but it was on related days, so it is disclosed.
- Both effects are published, and published effects often weaken after
  publication. That is a reason for the holdout, not for tuning.

## 1. H1 — late-day momentum (hedging demand and leveraged-ETF rebalancing)

**Economic reason.**
- Option dealers who are short gamma must hedge in the direction of the day's
  move, and they concentrate that hedging into the close.
- Leveraged and inverse ETFs (TQQQ/SQQQ, SPXL/SPXS) must rebalance in the same
  direction as the day's return, in size proportional to it, near the close.
- Both flows are forced and predictable from the return so far.

Literature: Gao, Han, Li & Zhou (2018, *JFE*); Baltussen, Da, Lammers &
Martens (2021, *JFE*, "Hedging demand and market intraday momentum"); Cheng &
Madhavan (2009) on leveraged-ETF rebalancing.

**Rule (frozen), NQ, every eligible RTH day:**
- Signal r = (close of the 15:29 bar) ÷ (prior day's RTH close) − 1, on the
  back-adjusted RTH series. Days need ≥ 300 RTH bars, as in `daily3.py`; the
  prior day is the previous day in that series.
- r > 0 → **long**; r < 0 → **short**; r = 0 → no trade.
- Entry at the **open of the 15:30 bar**. Exit at the **close of the 15:59 bar**.
  About 250 trades a year, flat every night.

## 2. H2 — turn-of-month cash flows

**Economic reason.** Salaries, pension contributions and fund inflows arrive
around the turn of the month and are invested within a few days. Month-end
index and pension rebalancing and window dressing add to this. The result is
predictable buying pressure from the last trading day of a month through the
third trading day of the next. Literature: Ariel (1987); Lakonishok & Smidt
(1988); Ogden (1990); Etula, Rinne, Suominen & Vaittinen (2020, *RFS*, "Dash for
cash").

**Rule (frozen), NQ:**
- Turn-of-month sessions are the **last** Globex session of each calendar month
  and the **first three** of the next. A Globex session carries the date of its
  RTH day and must have RTH bars.
- In each, **long from the first bar of the session (the 18:00 ET reopen) to the
  close of its last RTH bar**. This uses the Globex-session trade and roll
  handling of `scripts/databento/d3g.py` (the D3-G/A leg), so it is
  prop-compatible: flat from 15:59 to 18:00 every day.
- About 48 trades a year.

## 3. Costs and nulls

- **Costs:** the step-4 rule, NQ $2.25 + 1 tick per side ($14.50 per round trip).
  A roll inside a session costs one extra round trip (H2). Descriptive only:
  MNQ $2.24 per round trip.
- **H1 null:** 5,000 lists. Each random trade keeps one actual trade's
  **direction**, the same 15:30 open → 15:59 close window and the same cost, on
  a uniformly random eligible day of the same window. The long/short mix and
  the late-day drift are matched, so the test is whether the signal picks the
  direction.
- **H2 null:** 5,000 lists of the same number of long 18:00 → RTH-close trades on
  uniformly random eligible sessions of the same window, with the same costs and
  roll treatment. The overnight and intraday drift is matched, so the test is
  whether the turn-of-month sessions are special.
- **Statistic:** total net P&L (1 NQ per trade). p = (1 + number of random
  totals ≥ actual) ÷ 5,001. Seed 20260930.

## 4. Split and decision rule

- **Discovery:** trade days 2010-06-07 → 2020-12-31. **Holdout:** 2021-01-01 →
  2026-09-24, labelled *never used for these hypotheses; read by other studies*.
- **Discovery pass:** total net > 0 **and** Holm-adjusted p ≤ 0.05, **Holm across
  H1 and H2**.
- **The holdout is read once, only for a hypothesis that passes discovery.** The
  script does this automatically; there is no choice in between. **Holdout
  pass:** total net > 0 **and** p ≤ 0.05 on the holdout's own null. If both
  hypotheses reach the holdout, Holm across the two applies there too.
- **Final pass** (discovery and holdout) → forward paper-tracking from
  2026-09-30, plus the prop simulator on the full-window trades. **Anything
  else → closed**, with no other windows, thresholds, filters or instruments.
- **Power, stated now:** H1 has about 2,600 discovery trades, H2 about 500. A
  null result here is informative, not underpowered.

## 5. Descriptive only (cannot change a verdict)

For each hypothesis:
- $/trade, win rate, profit factor, Sharpe, max drawdown and worst trade, per
  NQ and per MNQ;
- the two halves of discovery, results by year, and the holdout (only when it
  is read).

For H1 alone:
- results by quintile of |r|. The mechanism predicts larger gains on bigger
  days;
- the Gao et al. first-half-hour predictor (prior close → 09:59 close) as an
  alternative signal.

Replication: both rules on ES ($29.50 per round trip), over the same windows.

## 6. Files

Script: `scripts/databento/econ2.py` (committed with this file before any run).
The simulator (`prop_sim.py`) gains short-side support (the open P&L of a short
is entry − price) and is re-checked with `--selftest` before the run.

Outputs:
- `reports/econ2_output.txt` and `reports/econ2_result.md`
- `reports/econ2_prop_sim_output.txt` (final passes only)
