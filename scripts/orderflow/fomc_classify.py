#!/usr/bin/env python3
"""FOMC SESSION CLASSIFICATION — classifier and window measurement.

FOMC decisions land at 14:00 ET, MID-SESSION. That is a different experiment
from an 08:30 release, so this family is kept separate and never pooled with
one: 14:00 splits the session into a pre-decision and a post-decision regime,
where an 08:30 print is fully absorbed before the cash open.

The 08:30 family (CPI / NFP / PPI) is NOT built here. Their release dates are
unobtainable in this environment -- see the report.

Windows, in minutes from the 09:30 open:
    pre   0..270    09:30-14:00, ends exactly at the statement
    post  270..390  14:00-16:00
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calendar_classify import ROOT, SRC, MIN_BARS, TRAIL_N          # noqa

FOMC_CSV = ROOT / "data/events/fomc.csv"
PRE = (0, 270)
POST = (270, 390)


def _seg(cl, mins, lo, hi):
    w = (mins >= lo) & (mins < hi)
    if w.sum() < 5:
        return np.nan, np.nan
    c = cl[w]
    r = np.diff(np.log(c))
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return np.nan, np.nan
    path = float(np.abs(r).sum())
    rv = 1e4 * float(np.sqrt((r ** 2).sum()))
    eff = (float(abs(np.log(c[-1] / c[0]))) / path) if path > 0 else np.nan
    return rv, eff


def measure():
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
        rv_pre, eff_pre = _seg(cl, mins, *PRE)
        rv_post, eff_post = _seg(cl, mins, *POST)
        m15 = mins < 15
        tot = vol.sum()
        rows.append(dict(
            day=day, rv_pre=rv_pre, rv_post=rv_post,
            eff_pre=eff_pre, eff_post=eff_post,
            rv_ratio=(rv_post / rv_pre) if (np.isfinite(rv_pre) and rv_pre > 0) else np.nan,
            or15_bps=(1e4 * (hi[m15].max() - lo[m15].min()) / px
                      if m15.sum() >= 3 else np.nan),
            volshare_post=(100.0 * vol[(mins >= POST[0])].sum() / tot
                           if tot > 0 else np.nan)))
    F = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    F["or_ratio"] = F.or15_bps / (F.or15_bps.rolling(TRAIL_N, min_periods=TRAIL_N)
                                  .mean().shift(1))
    return F


def load():
    F = measure()
    days = list(F.day)
    order = {d: i for i, d in enumerate(days)}
    fo = pd.read_csv(FOMC_CSV)
    fo["date"] = pd.to_datetime(fo.date).dt.date
    fset = {d for d in fo.date if d in order}
    sep = {d for d, s in zip(fo.date, fo.has_sep) if d in order and s == 1}
    after = {days[order[d] + 1] for d in fset if order[d] + 1 < len(days)}
    F["fomc"] = F.day.isin(fset)
    F["fomc_after"] = F.day.isin(after) & ~F.fomc
    F["fomc_sep"] = F.day.isin(sep)
    F["fomc_nosep"] = F.fomc & ~F.fomc_sep
    F["control"] = ~F.fomc & ~F.fomc_after
    F["year"] = pd.to_datetime(F.day).dt.year
    return F, len(fo), len(fset)


CATS = [("FOMC decision day", "fomc"), ("day after FOMC", "fomc_after"),
        ("FOMC with SEP", "fomc_sep"), ("FOMC without SEP", "fomc_nosep")]
STATS = ["rv_pre", "rv_post", "rv_ratio", "eff_post", "or_ratio"]
