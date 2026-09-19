"""Part A: do daily-history signals predict TREND vs CHOP days?

Everything evaluated here is knowable BEFORE the session opens (prior-day
indicators) or at the opening print (gap). Outcome = ex-post day type of
the session about to trade.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from regime.indicators import (
    adx,
    atr,
    directional_range_capture,
    efficiency_ratio,
    inside_day,
    label_day_type,
    nr_flag,
)

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 160)


def build(sym: str) -> pd.DataFrame:
    d = load_ibkr_json(DATA / f"{sym}_daily_5y.json")
    a20 = atr(d, 20)
    f = pd.DataFrame(index=d.index)
    f["day_type"] = label_day_type(d)
    f["drc"] = directional_range_capture(d)
    f["range_atr"] = (d["high"] - d["low"]) / a20.shift(1)

    # --- predictors known at t-1 close ---
    f["adx14"] = adx(d, 14).shift(1)
    f["er10"] = efficiency_ratio(d["close"], 10).shift(1)
    ema8 = d["close"].ewm(span=8, adjust=False).mean()
    ema21 = d["close"].ewm(span=21, adjust=False).mean()
    f["ema_dist"] = ((ema8 - ema21).abs() / a20).shift(1)
    f["atr_ratio"] = (atr(d, 5) / a20).shift(1)
    f["nr7"] = nr_flag(d, 7).shift(1).astype(float)
    f["inside"] = inside_day(d).shift(1).astype(float)
    f["prev_type"] = f["day_type"].shift(1)
    f["prev_drc"] = f["drc"].shift(1)
    # --- known at the open ---
    f["gap_atr"] = (d["open"] - d["close"].shift(1)).abs() / a20.shift(1)
    return f.dropna(subset=["adx14", "er10", "gap_atr", "day_type"])


def quintile_table(f: pd.DataFrame, col: str) -> pd.DataFrame:
    q = pd.qcut(f[col], 5, labels=False, duplicates="drop")
    g = f.groupby(q)
    return pd.DataFrame(
        {
            "lo": g[col].min().round(3),
            "hi": g[col].max().round(3),
            "P(TREND)": g["day_type"].apply(lambda s: (s == "TREND").mean()).round(3),
            "P(CHOP)": g["day_type"].apply(lambda s: (s == "CHOP").mean()).round(3),
            "mean_DRC": g["drc"].mean().round(3),
            "n": g["drc"].size(),
        }
    )


for sym in ["qqq", "spy"]:
    f = build(sym)
    base = f["day_type"].value_counts(normalize=True)
    print(f"\n################ {sym.upper()}  ({len(f)} sessions) base rates: "
          + "  ".join(f"{k}={v:.3f}" for k, v in base.items()))

    for col in ["adx14", "er10", "ema_dist", "atr_ratio", "gap_atr", "prev_drc"]:
        print(f"\n--- {sym.upper()} {col} quintiles ---")
        print(quintile_table(f, col).to_string())

    for col in ["nr7", "inside"]:
        g = f.groupby(f[col] > 0)
        t = pd.DataFrame(
            {
                "P(TREND)": g["day_type"].apply(lambda s: (s == "TREND").mean()).round(3),
                "P(CHOP)": g["day_type"].apply(lambda s: (s == "CHOP").mean()).round(3),
                "mean_range_atr": g["range_atr"].mean().round(3),
                "n": g["drc"].size(),
            }
        )
        print(f"\n--- {sym.upper()} {col} (False/True) ---")
        print(t.to_string())

    g = f.groupby("prev_type")
    t = pd.DataFrame(
        {
            "P(TREND)": g["day_type"].apply(lambda s: (s == "TREND").mean()).round(3),
            "P(CHOP)": g["day_type"].apply(lambda s: (s == "CHOP").mean()).round(3),
            "n": g["drc"].size(),
        }
    )
    print(f"\n--- {sym.upper()} by previous day type ---")
    print(t.to_string())
