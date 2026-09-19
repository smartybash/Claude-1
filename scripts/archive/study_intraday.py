"""Part B: regime read from the first 60-90 minutes of the session.

Decision time = end of bar k (10:30 ET on 30-min data, 11:00 ET on hourly).
Features known at decision time; outcomes measured on the rest of the day.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json, overnight_stats, rth_only
from regime.indicators import atr, label_day_type

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 200)

DEC_BARS = {1800: 2, 3600: 2}  # 30m: 9:30-10:30, 1h: 9:30-11:00


def session_table(intra: pd.DataFrame, daily: pd.DataFrame | None, dec_bars: int,
                  on: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per session: decision-time features + rest-of-day outcomes."""
    bars = rth_only(intra).copy()
    bars["date"] = pd.to_datetime(pd.Series(bars.index.date, index=bars.index))

    rows = []
    for date, day in bars.groupby("date"):
        if len(day) < dec_bars + 3:  # need a meaningful "rest of day"
            continue
        fh = day.iloc[:dec_bars]  # first-hour(ish) bars
        rest = day.iloc[dec_bars:]
        o = day["open"].iloc[0]
        fh_hi, fh_lo = fh["high"].max(), fh["low"].min()
        p_dec = fh["close"].iloc[-1]
        path = fh["close"].diff().abs().sum() + abs(fh["close"].iloc[0] - o)
        c = day["close"].iloc[-1]
        first_dir = np.sign(p_dec - o)
        rows.append(
            {
                "date": date,
                "open": o,
                "close": c,
                "high": day["high"].max(),
                "low": day["low"].min(),
                "fh_range": fh_hi - fh_lo,
                "fh_er": abs(p_dec - o) / path if path > 0 else np.nan,
                "fh_pos": (p_dec - fh_lo) / (fh_hi - fh_lo) if fh_hi > fh_lo else np.nan,
                "p_dec": p_dec,
                "first_dir": first_dir,
                # outcomes
                "rod_move": c - p_dec,
                "rod_hi": rest["high"].max(),
                "rod_lo": rest["low"].min(),
            }
        )
    t = pd.DataFrame(rows).set_index("date")

    # daily ATR20 reference (prior day's value; futures fall back to own sessions)
    if daily is not None:
        ref = atr(daily, 20).shift(1)
        ref.index = pd.to_datetime(ref.index.date)
        t["atr20"] = ref.reindex(t.index)
        lab = label_day_type(daily)
        lab.index = pd.to_datetime(lab.index.date)
        t["day_type"] = lab.reindex(t.index)
    else:
        ohlc = t[["open", "high", "low", "close"]]
        t["atr20"] = atr(ohlc, 20).shift(1)  # min 20 sessions burn-in
        t["day_type"] = label_day_type(ohlc)

    t = t.dropna(subset=["atr20", "day_type"])
    t["fh_range_atr"] = t["fh_range"] / t["atr20"]
    t["rod_move_atr"] = t["rod_move"] / t["atr20"]
    # follow-through: rest-of-day move signed by first-hour direction
    t["follow_atr"] = t["rod_move_atr"] * t["first_dir"]
    # adverse excursion against first-hour direction, rest of day
    t["mae_atr"] = np.where(
        t["first_dir"] > 0, (t["p_dec"] - t["rod_lo"]) / t["atr20"],
        (t["rod_hi"] - t["p_dec"]) / t["atr20"],
    )
    if on is not None:
        t = t.join((on["on_range"] / t["atr20"]).rename("on_range_atr"))
    return t


def bucket_report(t: pd.DataFrame, col: str, edges: list[float], name: str) -> pd.DataFrame:
    b = pd.cut(t[col], edges)
    g = t.groupby(b, observed=True)
    return pd.DataFrame(
        {
            "P(TREND)": g["day_type"].apply(lambda s: (s == "TREND").mean()).round(3),
            "P(CHOP)": g["day_type"].apply(lambda s: (s == "CHOP").mean()).round(3),
            "med_follow": g["follow_atr"].median().round(3),
            "med_mae": g["mae_atr"].median().round(3),
            "n": g["follow_atr"].size(),
        }
    ).rename_axis(name)


def run(tag: str, t: pd.DataFrame):
    base_t = (t["day_type"] == "TREND").mean()
    base_c = (t["day_type"] == "CHOP").mean()
    print(f"\n################ {tag}: {len(t)} sessions | base P(TREND)={base_t:.3f} P(CHOP)={base_c:.3f} "
          f"| med follow={t['follow_atr'].median():.3f} ATR")
    print(bucket_report(t, "fh_er", [0, 0.4, 0.7, 1.01], "fh_er").to_string())
    print(bucket_report(t, "fh_range_atr", [0, 0.35, 0.55, 5], "fh_range_atr").to_string())
    print(bucket_report(t, "fh_pos", [-0.01, 0.2, 0.8, 1.01], "fh_pos").to_string())
    # composite: directional first hour = ER high AND close pinned to extreme
    strong = (t["fh_er"] >= 0.6) & ((t["fh_pos"] >= 0.75) | (t["fh_pos"] <= 0.25))
    weak = (t["fh_er"] <= 0.35) & (t["fh_pos"].between(0.25, 0.75))
    for nm, m in [("STRONG(dir FH)", strong), ("WEAK(rot FH)", weak)]:
        s = t[m]
        if len(s):
            print(f"{nm:>16}: n={len(s):3d} P(TREND)={(s['day_type'] == 'TREND').mean():.3f} "
                  f"P(CHOP)={(s['day_type'] == 'CHOP').mean():.3f} "
                  f"med follow={s['follow_atr'].median():+.3f} ATR med MAE={s['mae_atr'].median():.3f}")
    if "on_range_atr" in t.columns and t["on_range_atr"].notna().sum() > 10:
        print(bucket_report(t.dropna(subset=["on_range_atr"]), "on_range_atr", [0, 0.5, 0.8, 5], "on_range_atr").to_string())


qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")

for tag, intra_file, daily in [
    ("QQQ 1h (7.5mo)", "qqq_1h.json", qqq_d),
    ("SPY 1h (7.5mo)", "spy_1h.json", spy_d),
    ("QQQ 30m (3.6mo)", "qqq_30min.json", qqq_d),
    ("SPY 30m (3.6mo)", "spy_30min.json", spy_d),
]:
    intra = load_ibkr_json(DATA / intra_file)
    t = session_table(intra, daily, DEC_BARS[int(intra.index.to_series().diff().mode()[0].total_seconds())])
    run(tag, t)

# futures: own-session ATR (needs burn-in), overnight range available
for tag, f30 in [("NQ 1h (2mo)", "nq_1h.json"), ("ES 1h (2mo)", "es_1h.json")]:
    intra = load_ibkr_json(DATA / f30)
    on = overnight_stats(intra)
    t = session_table(intra, None, 2, on=on)
    run(tag, t)
