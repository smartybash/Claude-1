"""Data sanity checks: bar alignment, session completeness, proxy fidelity."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json, rth_only, rth_sessions, overnight_stats

DATA = Path(__file__).resolve().parents[1] / "data"

for name in ["qqq_30min", "qqq_1h", "nq_30min", "nq_1h"]:
    df = load_ibkr_json(DATA / f"{name}.json")
    times = pd.Series(df.index.time).astype(str).value_counts().sort_index()
    print(f"\n=== {name}: {len(df)} bars {df.index[0]} .. {df.index[-1]}")
    print("bar start times (ET) head/tail:")
    print(times.head(8).to_string())
    print("...")
    print(times.tail(4).to_string())

# session completeness for QQQ 30m
q30 = rth_sessions(load_ibkr_json(DATA / "qqq_30min.json"))
print("\nQQQ 30m sessions n_bars distribution:")
print(q30["n_bars"].value_counts().to_string())

# hourly: how many RTH bars per day?
q1h = load_ibkr_json(DATA / "qqq_1h.json")
q1h_rth = rth_only(q1h)
per_day = q1h_rth.groupby(q1h_rth.index.date).size()
print("\nQQQ 1h RTH bars per day distribution:")
print(per_day.value_counts().sort_index().to_string())

# proxy fidelity: NQ vs QQQ 30-min RTH close-to-close returns, overlapping days
nq30 = load_ibkr_json(DATA / "nq_30min.json")
nq_rth = rth_only(nq30)
qq_rth = rth_only(load_ibkr_json(DATA / "qqq_30min.json"))
joined = pd.DataFrame(
    {"nq": nq_rth["close"], "qqq": qq_rth["close"]}
).dropna()
r = joined.pct_change().dropna()
print(f"\nNQ vs QQQ 30-min RTH return correlation: {r['nq'].corr(r['qqq']):.4f} over {len(r)} bars")

es30 = load_ibkr_json(DATA / "es_30min.json")
sp_rth = rth_only(load_ibkr_json(DATA / "spy_30min.json"))
es_rth = rth_only(es30)
j2 = pd.DataFrame({"es": es_rth["close"], "spy": sp_rth["close"]}).dropna()
r2 = j2.pct_change().dropna()
print(f"ES vs SPY 30-min RTH return correlation: {r2['es'].corr(r2['spy']):.4f} over {len(r2)} bars")

# overnight stats sample
on = overnight_stats(nq30)
print(f"\nNQ overnight sessions: {len(on)}, median ON range: {on['on_range'].median():.1f} pts")

# daily data check
for sym in ["qqq", "spy"]:
    d = load_ibkr_json(DATA / f"{sym}_daily_5y.json")
    print(f"\n{sym} daily: {len(d)} rows {d.index[0].date()} .. {d.index[-1].date()}, "
          f"NaNs={d.isna().sum().sum()}, zero-range days={(d['high'] == d['low']).sum()}")
