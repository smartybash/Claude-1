# Pre-announcement method for earnings trades

You asked for a more diligent way to choose a position before an earnings
report, with several drivers required to agree beforehand. This is that
method, plus the evidence on which drivers actually earn a place in it.

**Short version.** I tested ten common pre-announcement drivers on 1,309
earnings reports across 14 stocks, using a training period, a later test
period, and six holdout stocks that were set aside under a hypothesis
written down in advance. **No driver survived.** The usual "alignment"
signals (trend, relative strength, market regime, beat streak, 52-week
high, accumulation) have no edge on the reaction at all. Two contrarian
drivers looked promising in training but were **not confirmed** on the
holdout. So the method currently returns **no directional position** for
every event. It will keep doing that until a driver passes. That's the
correct output, not a failure of the method.

## 1. What went wrong with the Micron spread

- **Direction was never researched.** The call side ranked first only
  because put skew made calls cheaper. No driver chose it.
- **Size was what actually mattered.** MU did rise (+3.0% on the reaction
  session), so the direction happened to be right. But a 10x needed +14%.
  Better direction calls alone wouldn't have saved that trade.
- **The best of the drivers tested here would have called it wrong.**
  Micron had run up into the print and jumped on its previous report. Both
  contrarian drivers fired and leaned DOWN.

## 2. The method: four gates

A position is recommended only if every gate passes, and each gate has to
be backed by evidence from data it wasn't fitted on.

| Gate | Question | Evidence required | Status today |
|---|---|---|---|
| G1 Direction | Do the drivers predict which way the stock reacts? | Confirmed on holdout stocks under a hypothesis written down beforehand | **FAIL**: no driver confirmed |
| G2 Strength | Do enough validated drivers agree? | Full alignment of the validated set | n/a until G1 passes |
| G3 Pricing | Is the option structure worth more than it costs, given this stock's event history? | Positive expected value that survives removing the best event (`event_10x.py`) | Checked per trade |
| G4 Regime | Is the market backdrop supportive? | Vol Desk basket gate (SPY or QQQ > +0.5%) | Checked per trade |

If G1 fails, any trade is a bet on the *size* of the move, not its
direction, and it has to stand on pricing alone (G3).

## 3. The evidence

**Data.** 14 stocks: AAPL, JPM, META, MSFT, MU, NKE, NVDA and TSLA for
training and testing; AMD, GOOGL, INTC, NFLX, ORCL and QCOM held out. That
gives 1,309 usable reports from 2000 to 2026. Report dates come from Alpha
Vantage `EARNINGS`. The reaction session is fixed by volume, because older
vendor timing labels are unreliable: the label stands unless the other
session's volume clearly beats it. Prices are adjusted for splits (each
split confirmed in the data). A test checks that no driver uses data after
the decision close.

**Protocol.**
1. Learn each driver's direction (momentum or contrarian) on reports before
   2017.
2. Measure its skill on 2017–2026 against that period's own base rate (not
   50%, so a rising market can't flatter bullish drivers).
3. Freeze the model and write the hypothesis down
   (`reports/earnings_preregistration.md`, commit b6e8604).
4. Only then collect the holdout stocks and test once.

**Drivers, training → test** (hit rate when the driver fires, minus the
base-rate expectation):

| Driver | Learned as | Train lift (p) | Test lift (p) |
|---|---|---|---|
| Run-up into the print | contrarian | +7.9% (0.009) | +5.4% (0.135) |
| Previous report's reaction | contrarian | +7.6% (0.004) | +2.7% (0.393) |
| Last EPS surprise | contrarian | +4.3% (0.131) | +2.4% (0.442) |
| Relative strength (60d) | — | +3.3% (0.208) | −3.3% (0.297) |
| Trend (price/50/200 stack) | — | +2.5% (0.426) | −1.9% (0.588) |
| Accumulation (up vs down volume) | — | +1.8% (0.635) | +1.3% (0.761) |
| Drift since last report | — | +1.3% (0.694) | −3.9% (0.242) |
| Market regime | — | +0.7% (0.832) | 0.0% (1.000) |
| Distance from 52-week high | — | +0.1% (1.000) | +3.6% (0.382) |
| Beat streak | — | +0.1% (1.000) | −2.1% (0.547) |

Only the first two passed the training bar (p < 0.10), and neither was
significant in the test period on its own.

**Full alignment of those two (the pre-registered hypothesis H1):**

| Sample | Events | Hit rate | Chance | Lift | p |
|---|---|---|---|---|---|
| Training (8 stocks, < 2017) | 126 | 60.3% | 48.7% | +11.6% | 0.010 |
| Test (8 stocks, 2017+) | 90 | 61.1% | 50.4% | +10.7% | 0.045 |
| **Holdout (6 new stocks)** | **177** | **54.8%** | **50.6%** | **+4.2%** | **0.146** |

**H1 is not confirmed.** The lift kept the same sign everywhere but shrank
by about two-thirds on clean data. That pattern usually means an effect
that was inflated by selection, or one that is real but small. Even taking
the holdout number at face value, the average move in the predicted
direction was **+0.6%**. Aligned events weren't bigger moves either (1.2×
the stock's typical move, against 1.1× overall). An edge that small can't
carry a directional option trade once spreads and event premium are paid,
let alone a 10x.

## 4. Cards for this week

`scripts/earnings_card.py` shows every driver's reading and the gate
status, using only data up to the decision close.

**Micron, decision Sep 30, looking back:** both validated-candidate drivers
fired (score −2, lean DOWN). G1 fails, so no position. Actual reaction:
**+3.0%**. Acting on the unvalidated lean would have been wrong.

**Nike, decision Oct 1 (reports tonight):** run-up says UP, previous
reaction says DOWN, so the score is 0 with no lean. G1 and G4 fail (SPY
+0.18%). **No directional position.** The reaction is tomorrow, and this
card was produced from data through today's close only.

## 5. After the announcement

Waiting for the reaction was tested separately, under its own
pre-registration ([`post_earnings_method.md`](post_earnings_method.md)):

- **Drift from the reaction-session close is confirmed** (53.3% vs
  50.0%, 1,299 reports, p = 0.010). It's worth about +0.3% over five
  sessions: a tilt, not an option trade.
- **A 10:30 first-hour entry is not confirmed.** It was right 57% of the
  time but averaged −0.06% per trade, because the losses were larger
  than the wins.

## 6. What could change the verdict

- **Options-derived drivers are the untested family**, and they're the
  closest to the Vol Desk thesis: pre-event put/call skew, implied move
  against the stock's realised event history, open-interest positioning and
  dealer gamma. Testing them needs a chain for every past event. Alpha
  Vantage `HISTORICAL_OPTIONS` can supply that, one call per event. That's
  the natural next study, using the same freeze-then-holdout protocol.
- **More stocks.** The holdout lift (+4.2%) needs roughly 800 aligned events
  to be distinguishable from zero. That's around 45 stocks of history.
- **Forward record.** Log every card's lean and outcome. That's slower, but
  it's the cleanest out-of-sample test there is.

## Reproduce

```
python scripts/earnings_backtest.py       # train/test driver study -> reports/earnings_model.json
python scripts/earnings_holdout.py        # frozen model on holdout -> reports/earnings_holdout_result.json
python scripts/earnings_card.py NKE --decision 2026-10-01
python -m pytest tests/test_earnings_method.py
```
