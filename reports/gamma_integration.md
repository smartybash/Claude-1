# Gamma/delta filtering + charts on ToS + WealthCharts — plan & how-to

Decisions: **charts on both ToS and WealthCharts**; **gamma data from WealthCharts
built-in** (full options chain + greeks + options flow). This doc is the build.

## What's already wired (this repo)
- `gamma_context.py` — VIX expected-move band, vol regime, round-strike pin, AND
  now reads `data/gamma_levels.json` (your WealthCharts levels).
- `generate_tos.py` — ToS study plots gamma-flip / call-wall / put-wall /
  zero-gamma when loaded (else a placeholder comment).
- `confluence.py` — read prints the levels + a price-vs-gamma-flip location note.
- `log_gamma.py` — appends the day's levels to `data/gamma_log.jsonl` (builds the
  history we need to backtest, since WealthCharts data is live-only).

## Daily workflow (2 minutes)
1. In **WealthCharts**: open the options chain / gamma view for NQ (or ES/QQQ/SPY).
   Read off: **gamma flip / zero-gamma**, **call wall** (largest call gamma/OI
   strike above), **put wall** (largest below).
2. Type them into `data/gamma_levels.json` (schema in `gamma_levels.example.json`;
   MNQ uses NQ, MES uses ES).
3. Run the rerun. The ToS boxes now carry the gamma lines; paste into ToS as
   usual. Run `python3 scripts/log_gamma.py` to snapshot for backtesting.

## The gamma filter (LOCATION context, not a directional signal)
Backtests (`backtest_gex_proxy.py`, `backtest_regime_rv.py`) showed the
*mechanical* "pos-gamma=fade / neg-gamma=trend" switch has **no robust edge** on
our sample. So gamma is used as location/veto context layered on the 3-filter:
- **Price above gamma flip** → vol-suppressed lean: favour mean-reversion at the
  edges (longs near put wall / EM-low, fades at call wall); breakouts less likely
  to run.
- **Price below gamma flip** → vol-amplified lean: favour breakouts/trend; fading
  gets run over.
- **Call wall** = upside magnet/resistance & short-fade zone; **put wall** =
  downside support & long zone; treat a confluence A+ zone that *coincides* with
  a wall as higher-conviction, one that fights a wall as lower.
- Never trade the flip/wall alone — it must line up with an A+ confluence zone +
  the candle trigger (our existing gate).

## Charts
- **ToS**: done — `generate_tos.py` emits the whole study incl. gamma lines.
- **WealthCharts**: port the same study in **WealthScript** (code view + visual
  builder). First-cut spec to build there:
  - VWAP + upper/lower band (native VWAP indicator, deviation = 0.5).
  - Horizontal levels for the 4 confluence zones (input prices).
  - Expected-move band = two horizontal lines at price ± (VIX/100·√(1/252)·price).
  - Gamma flip / call wall / put wall as horizontal lines.
  - NOTE: WealthScript syntax needs in-app validation — I can produce/refine the
    exact script once you confirm whether WealthCharts already ships a GEX/gamma
    indicator (if so, we skip re-deriving and just read its levels).

## Backtesting the filter (honest path)
WealthCharts built-in = **live, no history**, so we can't retro-test today. Plan:
1. `log_gamma.py` daily → `gamma_log.jsonl` accumulates real levels.
2. After ~20-30 sessions, a `backtest_gamma_filter.py` (to build) will test the
   location rules above against our intraday outcomes — same honest template
   (pre-registered rule, null baseline, split-half, ATR-unit expectancy).
3. Only promote a rule to "traded" if it clears that bar. Until then the gamma
   layer is **context on the chart**, consistent with what the data supports.

Alternative if you want history NOW (no waiting): a provider with historical GEX
(MenthorQ = futures/NQ-ES, or SpotGamma = SPX) — paid, but backtestable day one.

## Negative-gamma-at-open read (added) — the "long day" tell

**Plain version.** Dealers hedge the options they're short. Their *gamma* is how
fast that hedge changes as price moves.
- **Positive gamma** (net GEX > 0, spot above the flip): dealers sell rallies /
  buy dips -> moves get **dampened** -> range/chop, breakouts stall.
- **Negative gamma** (net GEX < 0, spot below the flip / "zero-gamma"): dealers
  buy rallies / sell dips -> moves get **amplified** -> trend/expansion. If it
  turns up in negative gamma, it tends to *keep* going = a **"long day."** Gamma
  is directionless — it says "extend, don't fade"; direction comes from the rest
  of the read (order flow, VWAP reclaim, rotation all-green, etc.).
- **Dealer delta** adds the directional lean: net negative dealer delta => they
  must sell rallies (downward pressure); positive => buy dips (upward).

**How to get it each morning (pick one):**
1. WealthCharts GEX/gamma view -> read net GEX sign + zero-gamma level, type into
   `data/gamma_levels.json` (`net_gex`, `gamma_flip`).
2. Export the chain (OI + gamma or IV) and let the calculator do it:
   `python3 scripts/gex_calc.py chain.csv --sym NQ --spot 29500 --mult 20 --dte 1 --write`
   -> computes net GEX, the gamma flip, call/put walls, dealer delta and writes
   them into `gamma_levels.json`.
3. A provider (MenthorQ/SpotGamma) that publishes zero-gamma + net GEX.

Then the rerun's confluence read prints, e.g.:
`-> NEGATIVE GAMMA at open (net GEX -0.62B): expect TREND/EXPANSION ('long day'
if it turns up); fades get run over.`

**Honest caveat.** We still can't *backtest* real GEX here (no historical OI).
`log_gamma.py` snapshots the daily levels so we can validate the read forward.

## Automated IBKR pull (added) — `pull_ibkr_chain.py`

Pre-open at your machine (TWS/IB Gateway running, API enabled):
```
pip install ib_insync pandas
python3 scripts/pull_ibkr_chain.py --sym NQ --write     # NDX options -> NQ key
python3 scripts/pull_ibkr_chain.py --sym QQQ --write    # add QQQ, ES (SPX), SPY as wanted
# then run the normal rerun — it now prints NEGATIVE/POSITIVE gamma at open.
```
It pulls the nearest expiry's chain (OI + model greeks/IV) for NDX (NQ), SPX (ES),
QQQ, or SPY, computes net GEX / gamma flip / walls / dealer delta via the same
`gex_calc` math, and writes `data/gamma_levels.json`. Flags: `--port` (TWS live
7496 / paper 7497; Gateway 4001/4002), `--delayed` (no live data sub),
`--max-strikes`, `--dte-max`. Live greeks give net GEX from actual gamma; the
flip is repriced from IV. No market-data sub -> use `--delayed`.
