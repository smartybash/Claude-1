# GEX backtest — does the real dealer-gamma regime predict the next day?

First test on REAL gamma (not a proxy): Alpha Vantage premium `HISTORICAL_OPTIONS`
chains for QQQ, 31 sampled sessions Oct-2025..Aug-2026 (19 negative-gamma, 12
positive-gamma). Per session we compute net GEX / gamma-flip (`av_gex.py`); the
chain's OI is as-of the close so it sets the NEXT day's open. We then measure
that next day's realized behavior (`backtest_gamma_filter.py`).

Gamma is about MAGNITUDE, so the metrics are next-day range, net open->close
travel, and efficiency (trend-iness).

| next-day metric | NEG-gamma | POS-gamma | diff | Welch t |
|---|---|---|---|---|
| **range %** | **1.68** | 1.32 | +0.36 | **1.77** |
| \|open->close\| % | 0.78 | 0.60 | +0.19 | 0.98 |
| efficiency | 0.49 | 0.43 | +0.06 | 0.58 |

Split-half (range): first half NEG 1.65 vs POS 1.25 (+0.40); second half NEG 1.69
vs POS 1.39 (+0.30) — **same sign both halves.**

## Verdict
- **SUPPORTED:** negative gamma -> **bigger-range / expansion** next day (~+0.36%/day
  on QQQ), and it's **stable across both halves** — the first gamma signal here that
  didn't sign-flip out of sample.
- **NOT supported:** that negative gamma gives a cleaner one-way **trend** or bigger
  net directional move (efficiency & open->close diffs are weak, t<1).

## How we use it (evidence-based, not Alex's stronger claim)
Gamma is a **volatility / expected-range switch, not a direction switch**:
- NEGATIVE gamma -> widen expectations: bigger EM, give trades room, fades can run
  further; don't assume a clean trend.
- POSITIVE gamma -> tighter/rangey: mean-reversion at the edges more reliable,
  breakouts stall.
Direction still comes from the rest of the stack (structure, VWAP, rotation, flow).

## Caveats
n=31 sampled (not consecutive) sessions, QQQ only, costs not modelled. Directional
read, not proof. `av_gex --log` appends every future rerun to `gex_history.jsonl`,
so this strengthens over time and can be re-run with more sessions / other symbols.

## Follow-up: mining other chain features (backtest_gex_features.py)

- **Dealer delta -> direction: NULL.** Computed dealer delta was net-negative on all
  30 sampled days (assumption artifact, no variation) and its magnitude had ~0
  correlation with next-day return (corr +0.06). Not a usable directional signal.
- **Net GEX magnitude -> next-day range: clean DOSE-RESPONSE.** Terciles:
  most-negative **1.85%** > middle 1.55% > most-positive **1.24%** (monotone).
  corr(distance-below-flip, range) = **+0.40**. So the range edge is graded, not
  binary: the more negative / deeper below flip, the wider the next day.
- **Actionable:** scale the day's expected range by net GEX — most-negative ~1.85%
  QQQ vs most-positive ~1.24%. Direction still comes from elsewhere.

## EM band = VIX 1-sigma scaled by the gamma tercile (shipped)
The dose-response above is now wired into the pipeline. `gamma_context.gamma_em_mult`
reads live terciles from `gex_history.jsonl` and scales the VIX expected-move band:
most-negative tercile **x1.20**, middle **x1.00**, most-positive **x0.80**. The
scaled band shows in the confluence read, the ToS study, and the on-chart label.
Gamma stays a range switch, not a direction switch.

## Follow-up: mega-cap earnings nights widen the next session (backtest_earnings_range.py)
Tested the well-known idea on our own data: the QQQ session that reacts to an
AAPL / MSFT / NVDA report (post-market -> next day, pre-market -> same day; report
dates from AV `EARNINGS`).

| next QQQ session | range % | median |
|---|---|---|
| **earnings-reaction day** (n=61) | **1.926** | 1.749 |
| normal day (n=1191) | 1.591 | 1.361 |

Ratio **1.21x**, Welch t **+2.70**, split-half **1.20x / 1.22x** (both halves > 1).

- **SUPPORTED & stable:** mega-cap earnings nights run ~1.2x wider — and it's a
  **forward-known** amplifier (the calendar is public weeks ahead), unlike gamma
  which is only known one day out.
- **Shipped:** `earnings_mult()` widens the band **x1.20** on a reaction day and
  **stacks** with the gamma multiplier (e.g. a positive-gamma earnings day nets
  0.80 x 1.20 = 0.96). Reaction days come from `data/earnings_calendar.json`,
  refreshed by `earnings_cal.py` from AV `EARNINGS_CALENDAR`. AV's forward coverage
  is partial (as of 2026-08-10 it had NVDA 8/26, TSLA 10/21, GOOGL 10/28); missing
  names are simply absent (no widener) until AV populates them.

## Direction: is there a DIRECTIONAL edge in the chain? (backtest_direction.py)
Everything above is a range switch. This hunted the harder thing — next-day SIGN.
**Verdict: NO genuine directional edge in the daily chain summary. Do not ship one.**

At first glance two rules looked strong (positive-gamma "revert to flip" and
"revert to wall-channel center", both ~73% hit, t up to +2.5). Skew controls
killed them:
- The sample is **down-skewed** (P(up)=37%), so "always predict down" already
  hits 63% for free — that alone explains dealer-delta (63%) and any down-leaning
  rule.
- In **every** positive-gamma session spot was **above** the flip (spot>flip is
  essentially definitional for positive gamma), so the reversion rule made **zero
  up-calls** (n=0) — it only ever said "down" and rode the skew.
- The continuous check `corr(spot-vs-flip distance, next-day return)` in positive
  gamma is just **-0.12** (right sign, negligible size).
- Momentum control (yesterday persists) is null (47%, t~0), as expected.

So direction is NOT in this data. Direction should keep coming from: (1) the
trend/balance regime (`intraday_engine`), (2) the rotation/breadth leadership read
(`rotation.py`, already built), and (3) the gamma flip used **intraday** as a bias
pivot (above flip = favor longs at support; below = favor shorts at resistance) —
framed as context, not a mechanical daily trigger.
**Next real probe if we want to keep hunting direction:** 25-delta IV skew /
risk-reversal computed from the full AV `HISTORICAL_OPTIONS` chain we already
fetch — store per session and test ~50 sessions before trusting. Not shipped blind.

## Levels: dealer walls sharpen confluence (backtest_walls.py — SHIPPED)
Do the call/put walls act as next-day S/R? On QQQ (n=30):
- next-day **HIGH stayed <= call wall 90%** of the time (resistance cap),
- next-day **LOW stayed >= put wall 73%** (support floor), both contained 63%.
Price typically stops ~2% short of a wall, so walls are **outer range boundaries /
high-conviction caps**, not precise magnets (precise touch-and-reject needs
intraday data to confirm).

**Shipped:** `confluence.build_zones` now injects the dealer levels as heavy,
distinct sources — call wall `cWall` (3.0), put wall `pWall` (3.0), gamma flip
`gFlip` (2.5) — for both NQ and QQQ (QQQ's feed into the cross-ref too). A
structural swing that also sits at the call wall now clusters into a DENSE zone
(e.g. NQ 30074-30112 = 1h+4h swing + wkH + cWall), so the map upgrades exactly
where dealers are defending. This is the model-free half of Alex's wall read.

## Other AV data assessed
- **News Sentiment — NOT usable as a daily signal.** QQQ returned ~3 articles over
  3 days and the items are descriptive/backward-looking ("QQQ ETF Gains 1.2%"),
  i.e. reverse-causal. Too sparse and lagging on an ETF ticker to mechanize.
- **Put/Call Ratio — parked** (user said forget PCR): contrarian PCR is a weak/noisy
  daily signal; live QQQ PCR ~0.95 is fine as passive chart context only.
