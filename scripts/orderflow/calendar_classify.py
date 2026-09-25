#!/usr/bin/env python3
"""CALENDAR SESSION CLASSIFICATION — classifier and per-session measurement.

Shared by the counts/power pass and the descriptive comparison. Contains NO
comparisons and NO performance measure of any kind.

Every category here is PURE CALENDAR ARITHMETIC on the session list. Nothing
is inferred from price, nothing needs a forecast, and every label is knowable
years in advance -- which is the point of the exercise.

Sealed NQ days are not read; 2016-2020 is never touched (this file reads only
QQQ_1m.parquet, which begins 2021-01-04).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"
MIN_BARS = 360
TRAIL_N = 20

# Intraday windows, in minutes from the 09:30 open.
WINDOWS = {"open30": (0, 30), "mid": (30, 360), "close30": (360, 390)}


# ------------------------------------------------------------- classifier --

def classify(days):
    """One row per session, every flag from the calendar alone."""
    d = pd.DataFrame({"day": days})
    ts = pd.to_datetime(d.day)
    d["year"], d["month"] = ts.dt.year, ts.dt.month
    d["dow"] = ts.dt.dayofweek                      # 0 = Monday
    d["q"] = ts.dt.quarter

    # rank within month / quarter, from the END (1 = last session)
    d["rev_m"] = d.groupby(["year", "month"]).cumcount(ascending=False) + 1
    d["fwd_m"] = d.groupby(["year", "month"]).cumcount() + 1
    d["rev_q"] = d.groupby(["year", "q"]).cumcount(ascending=False) + 1

    d["last3_month"] = d.rev_m <= 3
    d["last3_quarter"] = d.rev_q <= 3
    d["first_of_month"] = d.fwd_m == 1

    # Monthly expiry: the third Friday. Quarterly: third Friday of Mar/Jun/Sep/Dec.
    third_fri = {}
    for (y, m), g in d.groupby(["year", "month"]):
        f = g[g.dow == 4]
        if len(f) >= 3:
            third_fri[(y, m)] = f.day.iloc[2]
    tf = set(third_fri.values())
    d["monthly_expiry"] = d.day.isin(tf)
    d["quarterly_expiry"] = d.day.isin(
        {v for (y, m), v in third_fri.items() if m in (3, 6, 9, 12)})

    order = {x: i for i, x in enumerate(days)}
    prior = {days[order[x] - 1] for x in tf if order[x] > 0}
    d["pre_monthly_expiry"] = d.day.isin(prior) & ~d.monthly_expiry
    qtf = {v for (y, m), v in third_fri.items() if m in (3, 6, 9, 12)}
    qprior = {days[order[x] - 1] for x in qtf if order[x] > 0}
    d["pre_quarterly_expiry"] = d.day.isin(qprior) & ~d.quarterly_expiry

    # Futures roll: the 5 sessions ENDING on the Thursday before quarterly
    # expiry. Declared exactly so it cannot drift.
    roll = set()
    for x in qtf:
        i = order[x]
        end = i - 1                                  # the Thursday before
        for k in range(max(end - 4, 0), end + 1):
            roll.add(days[k])
    d["roll_week"] = d.day.isin(roll)

    for i, nm in enumerate(["mon", "tue", "wed", "thu", "fri"]):
        d[f"dow_{nm}"] = d.dow == i

    d["ordinary_friday"] = (d.dow == 4) & ~d.monthly_expiry
    d["ordinary_thursday"] = (d.dow == 3) & ~d.pre_monthly_expiry
    return d


# ------------------------------------------------------------ measurement --

def measure_sessions():
    """Per-session character. No comparisons, no performance."""
    raw = pd.read_parquet(SRC)
    raw["day"] = raw.timestamp.dt.date
    rows = []
    for day, g in raw.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            continue
        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        mins = (g.timestamp - open_t).dt.total_seconds().to_numpy() / 60.0
        cl = g.close.to_numpy(float)
        hi, lo = g.high.to_numpy(float), g.low.to_numpy(float)
        vol = g.volume.to_numpy(float)
        px = float(g.open.iloc[0])
        r = np.diff(np.log(cl))
        r = r[np.isfinite(r)]
        path = float(np.abs(r).sum())
        m15 = mins < 15
        rec = dict(
            day=day, px=px,
            rv_bps=1e4 * float(np.sqrt((r ** 2).sum())),
            range_bps=1e4 * (hi.max() - lo.min()) / px,
            eff=(float(abs(np.log(cl[-1] / cl[0]))) / path) if path > 0 else np.nan,
            or15_bps=(1e4 * (hi[m15].max() - lo[m15].min()) / px
                      if m15.sum() >= 3 else np.nan))
        tot = vol.sum()
        for nm, (a, b) in WINDOWS.items():
            w = (mins >= a) & (mins < b)
            rec[f"volshare_{nm}"] = 100.0 * vol[w].sum() / tot if tot > 0 else np.nan
            rr = np.diff(np.log(cl[w])) if w.sum() > 2 else np.array([])
            rr = rr[np.isfinite(rr)]
            rec[f"rv_{nm}"] = 1e4 * float(np.sqrt((rr ** 2).sum())) if len(rr) else np.nan
        rows.append(rec)
    F = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    # OR height over its own trailing 20-session mean, shifted: no session is
    # classified using its own data or anything after it.
    F["or_ratio"] = F.or15_bps / (F.or15_bps.rolling(TRAIL_N, min_periods=TRAIL_N)
                                  .mean().shift(1))
    return F


def load():
    F = measure_sessions()
    C = classify(list(F.day))
    return F.merge(C, on="day", how="inner")


# Categories: (label, member mask column, control mask column or None = "rest")
CATS = [
    ("last 3 of month",      "last3_month",          None),
    ("last 3 of quarter",    "last3_quarter",        None),
    ("first of month",       "first_of_month",       None),
    ("Monday",               "dow_mon",              None),
    ("Tuesday",              "dow_tue",              None),
    ("Wednesday",            "dow_wed",              None),
    ("Thursday",             "dow_thu",              None),
    ("Friday",               "dow_fri",              None),
    ("futures roll week",    "roll_week",            None),
    ("monthly expiry",       "monthly_expiry",       "ordinary_friday"),
    ("quarterly expiry",     "quarterly_expiry",     "ordinary_friday"),
    ("pre-monthly expiry",   "pre_monthly_expiry",   "ordinary_thursday"),
    ("pre-quarterly expiry", "pre_quarterly_expiry", "ordinary_thursday"),
]

STATS = ["rv_bps", "range_bps", "eff", "or_ratio"]


if __name__ == "__main__":
    M = load()
    print(f"sessions {len(M):,}   {M.day.min()} .. {M.day.max()}")
    print(f"\n{'category':<24}{'n':>6}{'control n':>11}")
    for label, col, ctrl in CATS:
        a = int(M[col].sum())
        b = int(M[ctrl].sum()) if ctrl else int((~M[col]).sum())
        print(f"{label:<24}{a:>6,}{b:>11,}")
    print(f"\npooled SD of each statistic (marginal, no category involved):")
    for s in STATS:
        v = M[s].dropna()
        print(f"  {s:<12} mean {v.mean():>9.4f}   sd {v.std(ddof=1):>9.4f}"
              f"   n {len(v):,}")
