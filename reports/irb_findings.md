# Inventory Retracement Bar (IRB) — backtest findings

**Question:** does Rob Hoffman's Inventory Retracement Bar add an edge to the
day-trading strategy, and at what timeframe?

**Verdict: NO for the canonical setup — do not add it.** As strictly defined,
the IRB not only fails to beat chance, it underperforms a trend-matched
random-break baseline at every timeframe tested. A mild, inconsistent signal
shows up only in the *inverse* (rejection-wick) variant on the daily chart, and
even there most of the win rate is the trend+breakout mechanic, not the candle
shape. Script: [`scripts/backtest_irb.py`](../scripts/backtest_irb.py) ·
figure: [`reports/img/irb_backtest.png`](img/irb_backtest.png).

## Method (same honesty bar as the other backtests)

- **Pre-registered definition (Hoffman):** in an uptrend, a bar whose real body
  has retraced ≥45% below the high (body in the lower 55%, big trend-side upper
  wick); buy-stop above the bar high, hard stop at the bar low. Mirror for
  shorts. Trend filter = EMA20 (price on the trend side + EMA sloping that way).
- **Mechanics:** intrabar high/low, stop-first on ties; fill only if the entry
  stop triggers within 3 bars; symmetric **+1R-before-−1R = win**; expectancy
  also at 1R/1.5R/2R targets with a 1R stop. Intraday trades open and resolve
  inside one RTH session; daily runs continuously.
- **Null (the control that matters):** identical break-of-bar trade on *random
  bars that pass only the trend filter* — not the IRB shape. Same count and
  long/short split. If IRB ≈ null, the shape adds nothing beyond "trend + break".
- **Pool:** NQ / ES / QQQ / SPY. Daily = 5y (QQQ/SPY, ~1,250 bars each); 1h/30m
  ~1–6 months; 15m/5m ~1 month RTH. Correlated instruments, short intraday
  windows — a real sample (~1,000 filled trades), not multi-year-independent.

## Results — canonical Hoffman IRB (win@1R = P(+1R before −1R))

| TF | signals | IRB win@1R | null win@1R | edge | E[R] @1R / 1.5R / 2R |
|----|--------:|-----------:|------------:|-----:|----------------------|
| 5m  | 376 | 36% | 49% | **−13%** | −0.28 / −0.22 / −0.21 |
| 15m | 201 | 42% | 46% | −4% | −0.16 / −0.19 / −0.16 |
| 30m | 161 | 41% | 47% | −6% | −0.16 / −0.12 / −0.19 |
| 1h  |  61 | 54% | 55% | −1% | +0.06 / +0.12 / +0.01 |
| 1D  | 226 | 45% | 54% | −9% | −0.10 / −0.10 / −0.03 |
| **ALL** | **1025** | **41%** | **49%** | **−8%** | −0.17 / −0.14 / −0.14 |

Every timeframe is negative-expectancy and below its own trend-matched null. The
lone non-negative expectancy (1h, +0.12 at 1.5R) sits on n=61 with a −1% edge vs
null — indistinguishable from the plain trend+breakout trade.

**Why it fails, mechanically:** the canonical IRB puts the entry (the trend-side
extreme) far from the body, so risk R = the full bar range and the +1R target is
a large move. Intraday that target often can't be reached before the session
ends or price reverses — wide-stop / far-target geometry that the tighter random
bars don't suffer from.

## Robustness — inverse-wick variant (long = big *lower* wick, short = big *upper* wick)

| TF | inv win@1R | null | edge | E[R]@1.5R | n |
|----|-----------:|-----:|-----:|----------:|--:|
| 5m  | 49% | 40% | +9% | +0.01 | 528 |
| 15m | 56% | 55% | +1% | +0.13 | 236 |
| 30m | 50% | 52% | −2% | +0.05 | 246 |
| 1h  | 56% | 62% | −6% | +0.01 | 115 |
| 1D  | 58% | 49% | **+9%** | **+0.22** | 410 |

Flipping the wick side (i.e. a hammer/shooting-star rejection-continuation) lifts
raw win rates, but the **edge vs the null is inconsistent** (+9pts at 5m and 1D,
negative at 30m/1h). Only the **daily** cut is halfway convincing: 58% vs 49%
null, +0.22R expectancy at a 1.5R target, n=410. That is a *rejection-wick*
continuation on the daily — not the IRB Hoffman describes, and it still needs
genuine out-of-sample confirmation before it earns a place.

## Takeaways

1. **Don't add the canonical IRB** to the intraday plan — it's negative here and
   worse than random trend entries, worst of all at 5m (the timeframe it's most
   often taught on).
2. Whatever works in "IRB-style" trading on this data is the **trend + break-of-
   bar** mechanic, not the 45% body rule — the null already captures it.
3. The only thread worth pulling is a **daily rejection-wick (inverse) continuation**;
   park it as a hypothesis for a dedicated, out-of-sample test rather than a live
   rule.

_Costs/slippage not modelled; fills assumed at the stop level. Adding costs makes
every negative-expectancy line above worse, not better._
