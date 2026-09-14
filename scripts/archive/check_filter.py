"""Consistency check: regime.filter on raw bars must reproduce study calls."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json, rth_only
from regime.filter import TrendChopFilter
from regime.indicators import atr, label_day_type
from study_filter import classify
from study_intraday import session_table

DATA = Path(__file__).resolve().parents[1] / "data"

daily = load_ibkr_json(DATA / "qqq_daily_5y.json")
atr20 = atr(daily, 20).shift(1)
atr20.index = pd.to_datetime(atr20.index.date)
atr5 = atr(daily, 5).shift(1)
atr5.index = atr20.index
prior_close = daily["close"].shift(1)
prior_close.index = atr20.index

intra = load_ibkr_json(DATA / "qqq_1h.json")
bars = rth_only(intra)

t = session_table(intra, daily, 2)
t["study_call"] = classify(t)

mismatch = 0
for date, day in bars.groupby(pd.to_datetime(pd.Series(bars.index.date, index=bars.index))):
    if date not in t.index or date not in atr20.index or np.isnan(atr20[date]):
        continue
    if day.index[0].time().hour != 9:
        continue  # partial session in the data feed
    f = TrendChopFilter(atr20=float(atr20[date]), prior_close=float(prior_close[date]),
                        atr_ratio=float(atr5[date] / atr20[date]))
    r = f.read(day)
    expect = t.loc[date, "study_call"]
    got = "TREND_CALL" if r.state.startswith("TREND") else r.state
    exp = "TREND_CALL" if str(expect).startswith("TREND") else expect
    if got != exp:
        mismatch += 1
        print(f"MISMATCH {date.date()}: filter={r.state} study={expect} (r={r.range_atr}, pos={r.pos}, er={r.er})")

print(f"\nchecked {len(t)} sessions, mismatches: {mismatch}")

# show a few example readings
for date in list(t.index[-3:]):
    day = bars[pd.to_datetime(pd.Series(bars.index.date, index=bars.index)) == date]
    f = TrendChopFilter(atr20=float(atr20[date]), prior_close=float(prior_close[date]),
                        atr_ratio=float(atr5[date] / atr20[date]))
    print(date.date(), f.read(day))
