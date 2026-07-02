# NQ/ES Trend-vs-Chop Regime Filter

A mechanical intraday regime filter for NQ/ES day trading, built and validated on
IBKR price history (QQQ/SPY as validated proxies, spot-checked on front-month
NQ/ES futures).

**Read the study first: [`reports/trend_regime_study.md`](reports/trend_regime_study.md).**

TL;DR — daily trend indicators (ADX, efficiency ratio, EMA spreads) do **not**
predict whether the next session trends or chops. The session tells you itself by
11:00 ET: a compressed first hour (< 0.35× daily ATR) means a chop day with 71–93%
probability; an expanded first 90 minutes (≥ 0.55× ATR) closing pinned to its
extreme doubles the odds of a trend day and calls its direction correctly 82% of
the time.

## Layout

```
regime/            the library
  data.py          IBKR columnar-JSON loader, ET session bucketing
  indicators.py    ATR, ADX, efficiency ratio, day-type labels
  filter.py        TrendChopFilter — the mechanical 10:30/11:00 regime read
scripts/
  diagnostics.py   data sanity checks + NQ↔QQQ / ES↔SPY proxy validation
  study_daily.py   Part A: pre-open predictors on 5y of daily data
  study_intraday.py Part B: first-90-min features vs rest-of-day outcomes
  study_filter.py  Part C: calibration + stability splits of the 3-state rule
  check_filter.py  consistency test: packaged filter == study classification
  make_charts.py   report figures
data/              raw IBKR price-history JSON (as fetched)
reports/           the write-up + figures
```

## Using the filter

```python
from regime.filter import TrendChopFilter, chop_veto_1030

# 10:30 ET early veto
if chop_veto_1030(or_high, or_low, atr20):
    ...  # stand down from continuation plays

# 11:00 ET full read (session_bars = today's RTH bars so far, ET-indexed OHLC)
f = TrendChopFilter(atr20=atr20, prior_close=prior_close, atr_ratio=atr5/atr20)
reading = f.read(session_bars)
reading.state   # TREND_UP | TREND_DOWN | CHOP | NEUTRAL
reading.score   # 0-100, for sizing
```

Reproduce everything: `pip install -r requirements.txt`, then run the scripts in
the order listed above (they only need the checked-in `data/` files).
