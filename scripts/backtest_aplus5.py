#!/usr/bin/env python3
"""A+ v5 — the last honest way to get the level price.

v4 established that the fade's apparent edge was the lookahead: filled at the
level, but only on bars that had already closed back through it. Entering at
the trigger bar's close instead is flat to negative at every stop width from 44
to 206 NQ points, in both halves of the sample.

One entry remains that needs no hindsight and still pays the level price:

    wait for the rejection bar to CLOSE, then rest a limit back AT the level,
    valid for the next K bars. Filled only if price returns.

The rejection is confirmed before the order exists, so nothing is known that
was not available at the time. The cost is that price often does not come back,
which is a real filter rather than a free one -- the question is whether the
trades it does catch are the good ones or the bad ones.

If this is flat, the value-area fade is finished and the file says so.

Delta stays a proxy on QQQ bars: ((close-open)/(high-low)) * volume.

Usage: python3 scripts/backtest_aplus5.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F
from backtest_aplus import build_levels, bar_delta, summ, COMPOSITE_N
from backtest_aplus2 import UPPER, LOWER, REARM, SKIP

ALL8 = UPPER + LOWER
NQ_REF = 29400.0


def trade(b, L, side, target, stop_pct, patience, bd_min=0.0):
    """Rejection bar closes -> rest a limit at L for `patience` bars."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    d = bar_delta(b)
    dv, vol = d.values, b["volume"].values
    n = len(b)
    tol = 0.0006 * L
    stop = L * (1 + stop_pct) if side < 0 else L * (1 - stop_pct)
    risk = abs(stop - L)
    if risk <= 0 or (side < 0 and target >= L) or (side > 0 and target <= L):
        return None
    rr = abs(L - target) / risk

    armed = True
    for i in range(n):
        if idx[i].strftime("%H:%M") < SKIP:
            continue
        if side < 0:
            if l[i] < L * (1 - REARM):
                armed = True
            tagged, rejected = h[i] >= L - tol, c[i] < L
        else:
            if h[i] > L * (1 + REARM):
                armed = True
            tagged, rejected = l[i] <= L + tol, c[i] > L
        if not (tagged and armed):
            continue
        armed = False
        if not rejected:
            continue
        if bd_min > 0:
            if vol[i] <= 0 or abs(dv[i]) / vol[i] < bd_min \
               or np.sign(dv[i]) != side:
                continue

        # order rests from the NEXT bar; fill needs price to come back to L
        fill = None
        for j in range(i + 1, min(i + 1 + patience, n)):
            if (side < 0 and h[j] >= L) or (side > 0 and l[j] <= L):
                fill = j
                break
        if fill is None:
            return dict(r=np.nan, filled=False, ts=idx[i], rr=rr)

        r = np.nan
        for j in range(fill, n):
            if side < 0:
                if h[j] >= stop:
                    r = -1.0; break
                if l[j] <= target:
                    r = rr; break
            else:
                if l[j] <= stop:
                    r = -1.0; break
                if h[j] >= target:
                    r = rr; break
        if not np.isfinite(r):
            r = ((L - c[n - 1]) if side < 0 else (c[n - 1] - L)) / risk
        return dict(r=r, filled=True, ts=idx[i], rr=rr)
    return None


def collect(sess, days, stop_pct, patience, bd_min=0.0, levels=ALL8):
    rows = []
    for i, d in enumerate(days):
        if i < COMPOSITE_N + 1:
            continue
        b = sess[d]
        lv = build_levels(sess, days, i, float(b["open"].iloc[0]))
        if not lv or "pdPOC" not in lv:
            continue
        best = None
        for name in levels:
            if name not in lv:
                continue
            side = -1 if name in UPPER else +1
            t = trade(b, lv[name], side, lv["pdPOC"], stop_pct, patience, bd_min)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=name, side=side, day=d)
                best = t
        if best:
            rows.append(best)
    return pd.DataFrame(rows)


def line(label, T, nd):
    if not len(T):
        print(f"{label:44s} n=0", flush=True)
        return
    got = T[T.filled]
    s = summ(got.r) if len(got) else "n=0"
    print(f"{label:44s} {s:52s} fill {100*T.filled.mean():3.0f}%  "
          f"{len(got)/nd*5:.1f}/wk", flush=True)


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    nd = len(days) - COMPOSITE_N - 1
    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("rejection bar closes -> limit rests AT the level for K bars\n")

    for pct in (0.0015, 0.0025):
        print(f"=== stop {pct*100:.2f}% ({pct*NQ_REF:.0f} NQ pts) ===", flush=True)
        for K in (1, 2, 3, 6, 12):
            line(f"  patience {K:2d} bars", collect(sess, days, pct, K), nd)
        print("  -- with trigger-bar delta >=10% --", flush=True)
        for K in (3, 6, 12):
            line(f"  patience {K:2d} bars", collect(sess, days, pct, K, 0.10), nd)
        print(flush=True)

    print("=== detail: stop 0.25%, patience 6, bar delta >=10% ===", flush=True)
    T = collect(sess, days, 0.0025, 6, 0.10)
    got = T[T.filled]
    if len(got):
        r = got.r.values
        eq = np.cumsum(r)
        dd = (np.maximum.accumulate(eq) - eq).max()
        streak = max((len(list(g)) for k, g in itertools.groupby(r < 0) if k), default=0)
        print(f"  median {np.median(r):+.2f}R  max DD {dd:.1f}R  "
              f"worst streak {streak}  best {r.max():+.1f}R", flush=True)
        mid = days[len(days) // 2]
        line(f"  first half  to {mid.date()}", T[T.day < mid], nd / 2)
        line(f"  second half from {mid.date()}", T[T.day >= mid], nd / 2)
        print("\n  by level:", flush=True)
        for nm, g in T.groupby("level"):
            line(f"    {nm}", g, nd)


if __name__ == "__main__":
    main()
