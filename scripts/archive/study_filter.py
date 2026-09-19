"""Part C: calibrate and validate the mechanical 3-state filter.

Rule under test (computed at 10:30 ET from first-hour bars + daily ATR):
  CHOP    if fh_range/ATR20 < 0.35, or (mid-range close and fh_er < 0.40)
  TREND_* if fh_range/ATR20 >= 0.55 and close pinned to OR extreme (>=0.8 / <=0.2)
  NEUTRAL otherwise
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from regime.indicators import atr
from study_intraday import session_table, DEC_BARS  # reuse

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 200)


def classify(t: pd.DataFrame) -> pd.Series:
    r, pos, er = t["fh_range_atr"], t["fh_pos"], t["fh_er"]
    out = pd.Series("NEUTRAL", index=t.index)
    trend = (r >= 0.55) & ((pos >= 0.8) | (pos <= 0.2))
    out[trend] = np.where(pos[trend] >= 0.8, "TREND_UP", "TREND_DOWN")
    chop = (r < 0.35) | (pos.between(0.2, 0.8) & (er < 0.40))
    out[chop] = "CHOP"  # chop veto wins over trend call
    return out


def evaluate(tag: str, t: pd.DataFrame):
    t = t.copy()
    t["call"] = classify(t)
    t["is_trend_call"] = t["call"].str.startswith("TREND")
    base_t = (t["day_type"] == "TREND").mean()
    base_c = (t["day_type"] == "CHOP").mean()
    print(f"\n=== {tag}: {len(t)} sessions | base P(TREND)={base_t:.3f} P(CHOP)={base_c:.3f}")
    g = t.groupby(t["call"].where(~t["is_trend_call"], "TREND_CALL"))
    rep = pd.DataFrame(
        {
            "P(TREND)": g["day_type"].apply(lambda s: (s == "TREND").mean()).round(3),
            "P(CHOP)": g["day_type"].apply(lambda s: (s == "CHOP").mean()).round(3),
            "med|rod|/ATR": g["rod_move_atr"].apply(lambda s: s.abs().median()).round(3),
            "med_follow": g["follow_atr"].median().round(3),
            "n": g.size(),
        }
    )
    print(rep.to_string())
    # directional accuracy of TREND calls: did the day close in the called direction?
    tc = t[t["is_trend_call"]]
    if len(tc):
        called_dir = np.where(tc["call"] == "TREND_UP", 1, -1)
        hit = np.sign(tc["close"] - tc["open"]) == called_dir
        rod_dir = np.sign(tc["close"] - tc["p_dec"]) == called_dir
        print(f"TREND calls: day-direction hit={hit.mean():.3f}, rest-of-day-direction hit={rod_dir.mean():.3f} (n={len(tc)})")


qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")

tables = {}
for tag, intra_file, daily in [
    ("qqq1h", "qqq_1h.json", qqq_d),
    ("spy1h", "spy_1h.json", spy_d),
    ("qqq30", "qqq_30min.json", qqq_d),
    ("spy30", "spy_30min.json", spy_d),
]:
    intra = load_ibkr_json(DATA / intra_file)
    step = int(intra.index.to_series().diff().mode()[0].total_seconds())
    tables[tag] = session_table(intra, daily, DEC_BARS[step])

pooled_1h = pd.concat([tables["qqq1h"], tables["spy1h"]])
pooled_30 = pd.concat([tables["qqq30"], tables["spy30"]])
evaluate("POOLED 1h (QQQ+SPY, 7.5mo, decision 11:00)", pooled_1h)
evaluate("POOLED 30m (QQQ+SPY, 3.6mo, decision 10:30)", pooled_30)

# stability: first vs second half of the hourly sample
for tag, tbl in [("qqq1h", tables["qqq1h"]), ("spy1h", tables["spy1h"])]:
    mid = tbl.index[len(tbl) // 2]
    evaluate(f"{tag} first half", tbl[tbl.index < mid])
    evaluate(f"{tag} second half", tbl[tbl.index >= mid])

# futures spot-check
from regime.data import overnight_stats
for tag, fn in [("NQ 1h", "nq_1h.json"), ("ES 1h", "es_1h.json")]:
    intra = load_ibkr_json(DATA / fn)
    t = session_table(intra, None, 2, on=overnight_stats(intra))
    evaluate(tag, t)
