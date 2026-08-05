# "Worth-stealing" ideas from Flow Zone Trader — honest verdicts

Four ideas from Alex's stream looked non-overlapping with our stack. Each was
tested in the repo's backtest style (pre-registered rule, symmetric ±1R or
forward-return, null baseline, expectancy in R / mean fwd return), or given an
honest feasibility verdict where the data doesn't exist. Scope caveats are
explicit; costs/slippage not modelled.

## 1. Initial-Balance (60-min) break-and-hold — REJECTED
`scripts/backtest_ib.py`. First-hour range set; first bar to close beyond an IB
edge + next bar holds = entry; stop = opposite edge (risk = IB range);
symmetric +1R-before-−1R = win. Null = same mechanic on a random intraday level.
- win@1R ~67% (n=27) looks nice but **E[R] ≈ +0.05 / 0.00 / −0.04** at 1R/1.5R/2R.
- Null was degenerate (0%, n=39) — the random band rarely gets a clean
  break+hold, so the "edge vs null" number is not trustworthy.
- Direction split lopsided (long 33% / short 93%) on a tiny, one-month,
  correlated sample.
- **Verdict:** no demonstrated edge. High hit-rate at 1R is eaten by the far
  target; the measured-move (1×IB) is too far to reach intraday often enough.

## 2. VIX-divergence "unhealthy market" tell — REJECTED
`scripts/backtest_vix_divergence.py`. Daily, 5y, SPY+QQQ vs VIX. On every up-day,
split by whether VIX also rose (up & VIX-up = "unhealthy"/hedging-into-strength)
vs up & VIX-down ("healthy"). Compare forward 1d/5d returns.
- SPY: unhealthy − healthy = **−0.02% (1d, z=−0.3) / −0.03% (5d, z=−0.1)** — noise.
- QQQ: the sign **flips positive** (+0.06% z=+0.5 / +0.08% z=+0.3).
- **Verdict:** no predictive merit as a long-veto/fade filter. The intraday
  version (VIX ticking up while price ticks up) may still be a *sentiment* read,
  but it is not a mechanical edge on daily data.

## 3. Dealer gamma / GEX (positive→mean-revert, negative→trend) — NOT BACKTESTABLE HERE
Requires option **open interest by strike** (and per-strike gamma) to compute
net dealer gamma, plus a **history of OI** to backtest. The IBKR MCP
`get_option_data` returns contract *structure only* (strikes + contract ids), no
OI/IV/gamma; those need a per-contract snapshot, and **no historical OI is
available at all**. A proper GEX backtest is therefore impossible with this data
source, and a live GEX would be dozens of fragile per-strike snapshot calls.
- **Verdict:** can't be honestly backtested. Not adopting a black-box GEX read.

## 4. Expected move (VIX-implied) — ADOPTED (net-new keeper)
The one genuinely useful, cheap, reliable piece adjacent to the options/gamma
world. 1-sigma daily expected move = `price × VIX/100 × √(1/252)`. Gives an
objective "how far is normal today" band that overlays directly on the
confluence map: a target/zone *inside* the EM band is reachable on a normal day;
one *beyond* it needs an above-average range day.

Today (VIX 16.46):

| inst | price   | 1σ day EM | normal day range | weekly EM |
|------|---------|-----------|------------------|-----------|
| SPY  | 774.35  | ±8.03     | 766.3 – 782.4    | ±17.95    |
| QQQ  | 723.77  | ±7.50     | 716.3 – 731.3    | ±16.78    |
| ES   | 7795.50 | ±80.83    | 7714.7 – 7876.3  | ±180.74   |
| NQ   | 29854   | ±309.6    | 29544 – 30164    | ±692      |

Use: on NQ today the upside A+ resistance 29877–30001 sits *inside* the +1σ EM
(30164) → reachable on a normal day. The lower supports 28178–28258 / 28080 sit
*below* −1σ (29544) → only in play on an above-average down day. This is the
keeper; wiring it into the rerun as a one-line overlay is trivial.

## Net
3 of 4 rejected/​infeasible; **expected-move overlay adopted**. Our existing
regime + confluence + 3-filter stack is not improved by IB break-hold, the VIX
tell, or a GEX read on the data we have. The EM band is a cheap, honest addition.
