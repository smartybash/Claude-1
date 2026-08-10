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

## Other AV data assessed (not yet backtested)
Put/Call Ratio (realtime + historical to 2008) and News Sentiment are available
"other data" families. PCR pulls are one-per-date and verbose, and contrarian PCR
is historically a weak/noisy daily signal — recommend a dedicated ~50-session test
before trusting it, rather than half-powered. Live QQQ PCR ~0.95 (neutral) is fine
as chart context. News-sentiment (date-range, few calls) is the better next probe.
