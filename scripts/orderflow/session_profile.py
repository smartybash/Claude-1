#!/usr/bin/env python3
"""EUROPEAN vs US SESSION ON NQ — DESCRIPTIVE ONLY. NOT A TEST.

Same instrument, same 21 dates, two windows. This measures what the sessions
ARE, so the question "is it worth buying European-hours data" can be answered
before anything is bought.

THIS SCRIPT DELIBERATELY CANNOT REPORT PERFORMANCE

Signal counting has to run the trading rules, which means P&L exists inside
this process. It is dropped at source: `strip()` deletes every P&L-bearing
field from each trade before anything is aggregated, so no expectancy, win
rate, profit factor or R figure can reach the output even by accident. That is
a guard, not a promise. 21 sessions cannot support a performance claim -- the
minimum detectable effect there is +1.55 R/session against a largest observed
effect of ~0.04 -- and this run must not become a covert test of one.

WHAT IS REPORTED

  range              high-low across the window, in bps of price
  realised vol       sqrt of summed squared 1-minute returns, in bps
  path length        sum of absolute 1-minute moves, in bps
  efficiency ratio   |net move| / path length. High = trends, low = chops.
                     The most decision-relevant number here, because every
                     rule in this project is a continuation rule.
  ATR                mean 1-minute bar range, in bps -- the quantity the stop
                     is a multiple of
  opening range      first 15 and 30 minutes of the window, in bps
  activity           prints and contracts per minute
  signal counts      sessions firing, trades, trades/session, for the ORB and
                     pullback rules anchored to each window's own open
  risk per trade     the stop distance the rule would set, in bps

THE WINDOW OVERLAP IS REPORTED, NOT HIDDEN

07:00-16:00 UTC and 13:30-20:00 UTC share 150 minutes, and those 150 minutes
contain the US cash open -- the most violent part of the day and not European
in character. So a third window, 07:00-13:30, is measured: strictly before the
US open, and the only genuinely clean European comparison.

Sealed days are excluded when the date list is built, not filtered afterwards.

Usage: python3 scripts/orderflow/session_profile.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codec import is_encoded, load_any                                 # noqa
import or_height as OH                                                 # noqa
import pullback as PB                                                  # noqa

TICK = 0.25
ATR_BARS = 20
MAX_TRADES = 2

# NQ constants as a fraction of price, as used by every screen in this project
BREAK_F = 0.50 / 30000.0
REJ_F = 1.00 / 30000.0
FLOOR_F = 2.00 / 30000.0
COST_F = 2.00 / 30000.0

SEALED_PREFIX = "202606"          # the eight sealed June days
SEALED_DATES = {"20260723"}       # sealed inside the discovery window
FROM_DATE = "20260701"

WINDOWS = [
    ("EU  07:00-16:00", 7, 0, 16, 0),
    ("EU- 07:00-13:30", 7, 0, 13, 30),      # strictly before the US open
    ("US  13:30-20:00", 13, 30, 20, 0),
    ("US* 13:30-18:30", 13, 30, 18, 30),    # the window the flat time allows
]

PNL_FIELDS = ("R", "naive_R", "pnl", "slip_R", "exit", "why", "target")


def strip(tr: dict) -> dict:
    """Delete every P&L-bearing field before aggregation. See module docstring."""
    return {k: v for k, v in tr.items() if k not in PNL_FIELDS}


# ------------------------------------------------------------------ data --

def session_dates():
    """Dates with a 0.25 tape covering the European window. Sealed excluded
    AT CONSTRUCTION -- they are never opened."""
    best = {}
    for f in sorted(glob.glob("data/tape/TAPE_NQ_*.csv.*")):
        p = Path(f)
        day = p.name.split("_")[2].split(".")[0].split("_")[0]
        if day.startswith(SEALED_PREFIX) or day in SEALED_DATES or day < FROM_DATE:
            continue
        best.setdefault(day, []).append(p)
    return dict(sorted(best.items()))


def load_day(paths):
    """Finest recording for the date, as full-day 1-minute bars."""
    best = None
    for p in paths:
        try:
            d = load_any(p) if is_encoded(p) else pd.read_csv(p)
        except Exception:
            continue
        tc = next((c for c in d.columns if c.lower() in ("time", "timestamp")), None)
        pc = next((c for c in d.columns if c.lower() in ("price", "px")), None)
        if tc is None or pc is None:
            continue
        d = d.rename(columns={tc: "time", pc: "price"})
        d["time"] = pd.to_datetime(d.time, errors="coerce", format="mixed")
        d = d.dropna(subset=["time", "price"])
        u = np.unique(d.price.to_numpy(float))
        step = float(np.min(np.diff(np.sort(u)))) if len(u) > 1 else np.inf
        if step > 0.25:
            continue
        vc = next((c for c in d.columns if c.lower() in ("volume", "vol", "size")), None)
        d["volume"] = d[vc].astype(float) if vc else 1.0
        if best is None or len(d) > len(best):
            best = d[["time", "price", "volume"]]
    if best is None:
        return None
    g = best.set_index("time").price.resample("1min")
    hi, lo = g.max().dropna(), g.min()
    bars = pd.DataFrame({
        "hi": hi, "lo": lo.reindex(hi.index),
        "op": g.first().reindex(hi.index), "cl": g.last().reindex(hi.index),
        "vol": best.set_index("time").volume.resample("1min").sum().reindex(hi.index),
        "n": best.set_index("time").price.resample("1min").count().reindex(hi.index),
    })
    return bars.dropna(subset=["hi", "lo"])


def slice_window(bars, day, h0, m0, h1, m1):
    d = pd.Timestamp(day[:4] + "-" + day[4:6] + "-" + day[6:])
    a = d + pd.Timedelta(hours=h0, minutes=m0)
    b = d + pd.Timedelta(hours=h1, minutes=m1)
    return bars[(bars.index >= a) & (bars.index < b)], a, b


# ------------------------------------------------------------ statistics --

def profile(w):
    px = float(w.cl.iloc[0])
    r = np.diff(np.log(w.cl.to_numpy(float)))
    r = r[np.isfinite(r)]
    path = float(np.abs(r).sum())
    net = float(abs(np.log(w.cl.iloc[-1] / w.cl.iloc[0])))
    mins = len(w)
    return dict(
        mins=mins,
        range_bps=1e4 * (w.hi.max() - w.lo.min()) / px,
        rv_bps=1e4 * float(np.sqrt((r ** 2).sum())),
        path_bps=1e4 * path,
        eff=net / path if path > 0 else np.nan,
        atr_bps=1e4 * float((w.hi - w.lo).mean()) / px,
        prints_min=float(w.n.sum()) / max(mins, 1),
        vol_min=float(w.vol.sum()) / max(mins, 1),
    )


def or_height(w, minutes):
    if len(w) < minutes:
        return np.nan
    h = w.iloc[:minutes]
    return 1e4 * (h.hi.max() - h.lo.min()) / float(w.cl.iloc[0])


# --------------------------------------------------------------- signals --

def as_bars(w, open_t, flat_t):
    hi = w.hi.to_numpy(float)
    lo = w.lo.to_numpy(float)
    atr = (pd.Series(hi - lo).rolling(ATR_BARS, min_periods=10).mean()
           .shift(1).to_numpy(float))
    return (w.index.to_numpy(), hi, lo, w.op.to_numpy(float), open_t, flat_t, atr)


def orb_signals(w, open_t, flat_t, or_min, tgt_r=3.0):
    """The pre-registered ORB machine (or_height.run_session), anchored to
    THIS window's open. Uses the real rule rather than a re-implementation, so
    the counts describe the rule that would actually be screened."""
    px = float(w.cl.iloc[0])
    hi = w.hi.to_numpy(float)
    lo = w.lo.to_numpy(float)
    atr = (pd.Series(hi - lo).rolling(ATR_BARS, min_periods=10).mean()
           .shift(1).to_numpy(float))
    s = dict(t=w.index.to_numpy(), hi=hi, lo=lo, op=w.op.to_numpy(float),
             cl=w.cl.to_numpy(float), atr=atr, open_t=open_t,
             last_entry=flat_t - pd.Timedelta(minutes=30), px=px,
             brk=px * BREAK_F, floor=px * FLOOR_F, cost=px * COST_F)
    trades, _look = OH.run_session(s, or_min, 1.0, tgt_r)
    return [strip(dict(risk_bps=t["risk_bps"], mins=t["mins"])) for t in trades]


def pullback_signals(w, open_t, flat_t, or_min, tgt_r=3.0):
    """The pre-registered pullback machine, anchored to this window's open."""
    px = float(w.cl.iloc[0])
    bars = as_bars(w, open_t, flat_t)
    trades = PB.run_session(
        bars, or_min, 1.0, tgt_r, exc=PB.EXC_FIXED,
        brk=px * BREAK_F, rej=px * REJ_F, floor=px * FLOOR_F, cost=px * COST_F,
        last_entry=flat_t - pd.Timedelta(minutes=30))
    return [strip(dict(risk_bps=1e4 * t["risk"] / px,
                       mins=(t["entry_t"] - np.datetime64(open_t))
                            / np.timedelta64(1, "m")))
            for t in trades]


# ------------------------------------------------------------------- run --

def main():
    dates = session_dates()
    print("=" * 104)
    print("NQ — EUROPEAN vs US SESSION, SAME INSTRUMENT, SAME DATES. "
          "DESCRIPTIVE ONLY.")
    print("=" * 104)
    print("  No expectancy, no win rate, no profit factor, no verdict on any "
          "rule. P&L fields are\n  deleted at source before aggregation. This "
          "is not a test and cannot become one.\n")

    rows, sigs = [], []
    used = []
    for day, paths in dates.items():
        bars = load_day(paths)
        if bars is None:
            continue
        w0, a0, _ = slice_window(bars, day, 7, 0, 16, 0)
        if len(w0) < 0.9 * 540:
            continue
        used.append(day)
        for label, h0, m0, h1, m1 in WINDOWS:
            w, a, b = slice_window(bars, day, h0, m0, h1, m1)
            if len(w) < 60:
                continue
            p = profile(w)
            p.update(day=day, win=label,
                     or15=or_height(w, 15), or30=or_height(w, 30))
            rows.append(p)
            for name, fn in (("ORB", orb_signals), ("pullback", pullback_signals)):
                for om in (15, 30):
                    tr = fn(w, a, b, om)
                    sigs.append(dict(day=day, win=label, rule=f"{name} OR{om}",
                                     n=len(tr),
                                     risk=np.median([x["risk_bps"] for x in tr])
                                     if tr else np.nan))
    P = pd.DataFrame(rows)
    S = pd.DataFrame(sigs)
    print(f"  sessions: {len(used)}   {used[0]} .. {used[-1]}")
    print(f"  {' '.join(d[4:] for d in used)}")
    print("  sealed June days and 23 July excluded at construction, never "
          "opened\n")

    order = [w[0] for w in WINDOWS]

    def tab(title, cols, fmt="{:>11.2f}"):
        print(f"\n  {title}")
        print(f"    {'window':<18}" + "".join(f"{c:>11}" for c in cols))
        for w in order:
            g = P[P.win == w]
            if g.empty:
                continue
            print(f"    {w:<18}" + "".join(
                fmt.format(g[c].median()) for c in cols))

    print("=" * 104)
    print("  MEDIAN ACROSS THE SESSIONS")
    print("=" * 104)
    tab("SIZE AND SHAPE (bps of price)",
        ["mins", "range_bps", "rv_bps", "path_bps", "eff"])
    print("      mins = minutes in the window   range = high-low   rv = sqrt "
          "sum of squared 1-min returns")
    print("      path = sum of absolute 1-min moves   eff = |net| / path "
          "(high trends, low chops)")

    tab("BAR SCALE AND OPENING RANGE (bps)", ["atr_bps", "or15", "or30"])
    print("      atr = mean 1-minute bar range, the quantity the stop is a "
          "multiple of")

    tab("ACTIVITY (per minute)", ["prints_min", "vol_min"], "{:>11.1f}")

    print("\n" + "=" * 104)
    print("  RATIOS — European window against the US tradeable window")
    print("=" * 104)
    base = P[P.win == "US* 13:30-18:30"]
    print(f"    {'window':<18}" + "".join(
        f"{c:>12}" for c in ["range", "rv", "path", "eff", "atr", "or30",
                             "prints", "vol"]))
    for w in order:
        g = P[P.win == w]
        if g.empty:
            continue
        vals = []
        for c in ["range_bps", "rv_bps", "path_bps", "eff", "atr_bps", "or30",
                  "prints_min", "vol_min"]:
            vals.append(g[c].median() / base[c].median())
        print(f"    {w:<18}" + "".join(f"{v:>12.2f}" for v in vals))
    print("      1.00 = identical to the US tradeable window on that measure")

    print("\n" + "=" * 104)
    print("  SIGNAL COUNTS — how often the EXISTING rules fire, anchored to "
          "each window's own open")
    print("=" * 104)
    print(f"    {'window':<18}{'rule':<16}{'sessions firing':>17}"
          f"{'trades':>8}{'per session':>13}{'median risk bps':>17}")
    for w in order:
        for rule in sorted(S.rule.unique()):
            g = S[(S.win == w) & (S.rule == rule)]
            if g.empty:
                continue
            fired = int((g.n > 0).sum())
            print(f"    {w:<18}{rule:<16}{fired:>8}/{len(g):<8}"
                  f"{int(g.n.sum()):>8}{g.n.mean():>13.2f}"
                  f"{g.risk.median():>17.2f}")

    print("\n  (trades per session is capped at 2 by the rule. Risk is the "
          "stop distance the\n   rule would set, not a result.)")

    P.to_csv("reports/session_profile_raw.csv", index=False)
    S.to_csv("reports/session_profile_signals.csv", index=False)
    print("\n  raw per-session figures written to "
          "reports/session_profile_raw.csv")


if __name__ == "__main__":
    main()
