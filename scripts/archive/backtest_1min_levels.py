#!/usr/bin/env python3
"""ONE-MINUTE RESOLUTION — testing the diagnosis directly.

Every level test in this repo ran on 5-minute bars and every one failed the
same way: fading is too early (price runs past and takes the stop), the break
is too late (by the time a 5-minute bar closes beyond the level, the move is
done). The conclusion drawn was that the tradeable move happens INSIDE the
breaking bar.

That conclusion is testable, because the repo holds twelve months of 1-minute
QQQ bars that were never used. If the move really is finished within the
5-minute bar, a 1-minute trigger should see it. If 1-minute does no better,
the move is finished inside the minute too, and bar data of any resolution is
the wrong instrument.

Same levels, same rule, same sessions -- only the bar size changes:

  LEVELS   prior-day RTH VAH / POC / VAL / High / Low, from the 5-min profile
  TRIGGER  a bar pokes through a level and CLOSES back on the original side
  ENTRY    that bar's close (no lookahead)
  STOP     beyond the level
  TARGET   prior-day POC

Run at 1-minute and at 5-minute over the identical 251 sessions so the only
difference in the numbers is resolution. Also runs the continuation direction
at 1-minute, and sweeps the stop, because a 1-minute entry sits much closer to
the level and can afford a tighter one.

Usage: python3 scripts/backtest_1min_levels.py
"""
from __future__ import annotations

import glob
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweeplib.levels import volume_profile
from backtest_aplus import summ

NQ_REF = 29400.0
SKIP = "10:00"
REARM = 0.0015


def load_1m():
    fr = [pd.read_csv(f, parse_dates=["timestamp"])
          for f in sorted(glob.glob(str(ROOT / "data/intraday/qqq_1m_*.csv")))]
    df = pd.concat(fr).set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df.between_time("09:30", "15:59")
    return {d: b for d, b in df.groupby(df.index.normalize()) if len(b) >= 300}


def to_5m(b):
    o = b.resample("5min").agg({"open": "first", "high": "max", "low": "min",
                                "close": "last", "volume": "sum"}).dropna()
    return o


def prof(b):
    p = volume_profile(b, 50)
    if not p:
        return None
    poc, vah, val = p
    return (poc, vah, val) if val < poc < vah else None


def levels_for(sess, days, i):
    if i == 0:
        return {}
    prev5 = to_5m(sess[days[i - 1]])
    p = prof(prev5)
    if not p:
        return {}
    poc, vah, val = p
    return dict(pdPOC=poc, pdVAH=vah, pdVAL=val,
                pdHigh=float(prev5.high.max()), pdLow=float(prev5.low.min())), poc


def run_one(b, L, side, target, stop_pct, mode):
    """side -1 = fade a poke above; +1 = fade a poke below.
    mode 'fade' takes the reversal, 'cont' takes the break."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    n = len(b)
    tol = 0.0006 * L
    marg = stop_pct * L
    armed = True
    for i in range(n):
        if idx[i].strftime("%H:%M") < SKIP:
            continue
        if mode == "fade":
            if side < 0:
                if l[i] < L * (1 - REARM):
                    armed = True
                hit, ok = h[i] >= L - tol, c[i] < L
            else:
                if h[i] > L * (1 + REARM):
                    armed = True
                hit, ok = l[i] <= L + tol, c[i] > L
            if not (hit and armed):
                continue
            armed = False
            if not ok:
                continue
            entry = c[i]
            stop = L + marg if side < 0 else L - marg
            tgt = target
        else:                                   # continuation
            brk = (c[i] > L + marg) if side > 0 else (c[i] < L - marg)
            if not brk:
                continue
            entry = c[i]
            stop = L - marg if side > 0 else L + marg
            risk0 = abs(entry - stop)
            tgt = entry + side * 2.0 * risk0
        risk = abs(entry - stop)
        if risk <= 0 or risk / entry > 0.008:
            return None
        s = side if mode == "cont" else side
        if (s < 0 and tgt >= entry) or (s > 0 and tgt <= entry):
            return None
        rr = abs(entry - tgt) / risk
        r = np.nan
        for j in range(i + 1, n):
            if s > 0:
                if l[j] <= stop:
                    r = -1.0; break
                if h[j] >= tgt:
                    r = rr; break
            else:
                if h[j] >= stop:
                    r = -1.0; break
                if l[j] <= tgt:
                    r = rr; break
        if not np.isfinite(r):
            r = ((entry - c[n - 1]) if s < 0 else (c[n - 1] - entry)) / risk
        return dict(r=r, rr=rr, ts=idx[i])
    return None


UPPER = ("pdVAH", "pdHigh")
LOWER = ("pdVAL", "pdLow")


def collect(sess, days, res, stop_pct, mode):
    rows = []
    for i, d in enumerate(days):
        got = levels_for(sess, days, i)
        if not got:
            continue
        lv, poc = got
        b = sess[d] if res == "1m" else to_5m(sess[d])
        if len(b) < 20:
            continue
        best = None
        for nm in UPPER + LOWER:
            L = lv[nm]
            if mode == "fade":
                side = -1 if nm in UPPER else +1
            else:
                side = +1 if nm in UPPER else -1
            t = run_one(b, L, side, poc, stop_pct, mode)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=nm, day=d, side=side)
                best = t
        if best:
            rows.append(best)
    return pd.DataFrame(rows)


def line(label, T, nd):
    print(f"{label:46s} {summ(T.r) if len(T) else 'n=0':52s} "
          f"{len(T)/nd*5:.1f}/wk", flush=True)


def main():
    sess = load_1m()
    days = sorted(sess)
    nd = len(days)
    print(f"QQQ — {nd} sessions, {days[0].date()} to {days[-1].date()}")
    print("identical levels, identical rule; only the bar size changes\n")

    print("=== FADE: 1-minute vs 5-minute, same sessions ===", flush=True)
    print(f"{'':46s} {'':52s} freq", flush=True)
    for pct in (0.0005, 0.0010, 0.0015, 0.0025):
        line(f"  5-min  stop {pct*100:.2f}% ({pct*NQ_REF:.0f} NQ pts)",
             collect(sess, days, "5m", pct, "fade"), nd)
        line(f"  1-min  stop {pct*100:.2f}% ({pct*NQ_REF:.0f} NQ pts)",
             collect(sess, days, "1m", pct, "fade"), nd)
        print(flush=True)

    print("=== CONTINUATION: 1-minute vs 5-minute (target 2R) ===", flush=True)
    for pct in (0.0005, 0.0010, 0.0015):
        line(f"  5-min  stop {pct*100:.2f}%",
             collect(sess, days, "5m", pct, "cont"), nd)
        line(f"  1-min  stop {pct*100:.2f}%",
             collect(sess, days, "1m", pct, "cont"), nd)
        print(flush=True)

    print("=== detail: best 1-min fade config ===", flush=True)
    best, bestv = None, -9
    for pct in (0.0005, 0.0010, 0.0015, 0.0025):
        T = collect(sess, days, "1m", pct, "fade")
        if len(T) and T.r.mean() > bestv:
            best, bestv, bp = T, T.r.mean(), pct
    if best is not None and len(best):
        r = best.r.values
        eq = np.cumsum(r)
        dd = (np.maximum.accumulate(eq) - eq).max()
        st = max((len(list(g)) for k, g in itertools.groupby(r < 0) if k), default=0)
        print(f"  stop {bp*100:.2f}%  median {np.median(r):+.2f}R  "
              f"max DD {dd:.1f}R  worst streak {st}  mean R:R {best.rr.mean():.2f}",
              flush=True)
        mid = days[len(days) // 2]
        line("  first half", best[best.day < mid], nd / 2)
        line("  second half", best[best.day >= mid], nd / 2)
        print("\n  by level:", flush=True)
        for nm, g in best.groupby("level"):
            line(f"    {nm}", g, nd)


if __name__ == "__main__":
    main()
