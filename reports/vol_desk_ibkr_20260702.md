# Vol Desk read from IBKR — July 2, 2026 (~11:12 ET, intraday)

Universe: the six single-stock options names from the account's last 90 days
of trading (TSLA, NVDA, AMD, PLTR, MU, INTC — futures and ETFs excluded;
RXT/WDCX chains too thin). IBKR exposes no watchlists, so recent trades are
the proxy.

**What this is and is not.** The GEX levels below are computed from the
front-monthly (Jul 17, 15 DTE) chain: per-strike open interest × Black-Scholes
gamma, dealers long-calls/short-puts convention (`scripts/gex_levels.py`).
That reproduces the *level map* — it does not reproduce the vendor gamma
screen. **Grade (11 rules), delta balance, and db_change are not derivable
from IBKR**, so filters 1–2 are UNKNOWN for every name and no setup can be
CONFIRMED off this report alone. Spike-crash is approximated from 3-month
price history.

## Regime gates — no new entries approvable today

| Gate | Reading | Verdict |
|---|---|---|
| Basket (SPY or QQQ > +0.5%) | SPY −0.68%, QQQ −2.31% | **FAIL** |
| Bull:Bear > 3.0:1 | needs the 700-name screen | UNKNOWN |
| VIX dealer delta < 0 | needs vendor positioning data | UNKNOWN |

Best case is 2/3, and the one gate we can verify failed on a broad risk-off
tape (TSLA −8.0%, MU −7.3%, INTC −6.2%, AMD −5.9%, NVDA −2.4%). B Continuation
(needs 3/3) is dead today; P2P Track 1 has no verified approval. This report
is a levels read, not a greenlight.

## Computed GEX levels

| Name | Spot | Δ day | nTrans | zeroGEX | pTrans | +GEX (T1) | T2 | COTMP | COTMC | Cushion | R/R | GEX@spot ($M/1%) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PLTR | 131.04 | +4.2% | 128.75 | 129.34 | 129.80 | 145 | — | 127.3 | 133.5 | +2.9% | 11.2 | +1.6 |
| TSLA | 391.15 | −8.0% | 384.50 | 386.46 | 388.02 | 430 | — | 386.1 | 403.7 | +1.3% | 12.4 | +6.6 |
| AMD | 508.85 | −5.9% | — | — | — | 470 | 550 | 491.9 | 501.5 | +3.4% | — | +9.6 |
| NVDA | 192.81 | −2.4% | 194.16 | 194.93 | 195.61 | 200 | 210 | 190.1 | 199.6 | +1.4% | — | −14.8 |
| MU | 957.00 | −7.3% | — | — | — | 910 | 960 | 944.9 | 963.2 | +1.3% | — | −45.5 |
| INTC | 119.10 | −6.2% | 126.48 | 127.56 | 128.57 | 130 | — | 118.4 | 120.9 | +0.6% | — | −0.4 |

“—” for nTrans/pTrans means the gamma curve doesn’t cross zero within ±15% of
spot (AMD one-signed positive, MU one-signed negative).

## Per-name reads

**PLTR — the only live P2P-shaped structure, with one flag.** Above pTrans
(129.80), +4.2% against a deep-red tape (real relative strength), positive
gamma at spot. Cushion +2.9% PASSES, R/R to the 145 target PASSES (11.2).
Flag: 145 was a May 1 spike high (146.4) followed by a −5.7% two-session
drop, and June's 160→107 collapse traversed the level — the spike-crash
screen reads CAUTION, not clean. Grade and db_change unknown. **Action: run
PLTR through the vendor screen tonight; entry only if grade ≥ 9, db_change
clears, the spike-crash read on 145 is clean on validated data, and gates
allow.**

**TSLA — spike-crash live at the target, structurally blocked.** Spot sits
above pTrans (388) and the R/R math looks gorgeous (12.4) — and it's a trap.
The 430 +GEX magnet is exactly where price was rejected TODAY: tagged 432.35
this morning (July 1 high 432.86, May distribution 445–453) and crashed −8%
from it. That is the 0/3-win-rate pattern, at the target, in real time.
Cushion +1.3% also fails the 2% bar. **Hard no.**

**NVDA — below nTrans, negative gamma.** Spot 192.81 is under the whole
transition band (flip at ~195); dealer gamma at spot is −$15M/1%, meaning
dealers chase moves rather than dampen them. The 180 put wall (85k) is the
big structure below; 200 (92k calls / 51k puts) caps above. No long setup; a
P2P candidate only after reclaiming ~195.6 on a confirmed close.

**AMD — extended above its own magnet.** Positive gamma everywhere in range
(+$9.6M/1%), but the biggest positive-gamma strike is *below* spot at 470,
with secondary structure at 500/COTMC 501.5. There is no pTrans-break setup
here; price is above the magnet on a −5.9% day. If anything this is a
future B-Continuation watch on a pullback that holds the 500 zone — needs
3/3 gates, which today is impossible.

**MU — deep negative gamma, avoid.** −$45M/1% at spot, put-dominated
structure (880/900 put blocks, 1000 straddle mass), −7.3% on the day.
Dealer hedging amplifies downside here. Nothing to do.

**INTC — far below the flip, blocked.** The transition band sits 6–8% above
spot (126.5–128.6); cushion is +0.6%; the 120 strike (12.6k calls / 14.9k
puts) is the pin. Bearish structure until the band is reclaimed.

## Bottom line

One name earned homework (PLTR), one name is the textbook blocked pattern
(TSLA), and the regime gate failed on the only leg IBKR can verify — so
zero entries today either way. Tonight's vendor screen decides whether PLTR
graduates from "structure live" to CONFIRMED for tomorrow's open trigger
(first 5-min close above 129.80, re-check R/R at that close).

## Reproduce

```
python scripts/gex_levels.py data/ibkr_oi_20260702.json
```

Raw OI snapshot (as fetched, 69 strikes): `data/ibkr_oi_20260702.json`.
Methodology and its limits: docstring of `scripts/gex_levels.py`.
