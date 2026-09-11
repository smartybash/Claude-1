#!/usr/bin/env python3
"""A+ v4 — the same trade with the lookahead removed.

Every earlier version of this test (including backtest_va_fade.py, the original
+0.334R / t=+3.80 result) enters at the LEVEL price but only takes the trade if
the bar CLOSES BACK through it. Those two facts cannot both be available at the
moment of entry: when price touches the level, the bar has not closed and the
rejection is not yet known. Entering at the level is therefore a price you
could not have been filled at on the information the rule uses.

Three entry conventions are compared here, on an otherwise identical spec:

  level   entry at the level         (what was tested before -- lookahead)
  close   entry at the trigger bar's close, stop anchored to the level
          (realistic: you see the rejection, then you act)
  limit   resting limit at the level, filled on EVERY touch, no rejection
          condition at all (realistic, and needs no hindsight -- but it also
          takes the breakouts that never come back)

The "close" convention keeps the stop where the structure puts it, so risk is
measured from the close to just beyond the level. That distance is larger than
level-to-stop, so R multiples must shrink. The question is by how much, and
whether anything survives.

Delta stays a proxy on QQQ bars: ((close-open)/(high-low)) * volume.

Usage: python3 scripts/backtest_aplus4.py
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


def trade(b, L, side, target, stop_pct, mode, bd_min=0.0):
    """First qualifying trade at level L. mode: 'level' | 'close' | 'limit'."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    d = bar_delta(b)
    dv, vol = d.values, b["volume"].values
    n = len(b)
    tol = 0.0006 * L
    stop = L * (1 + stop_pct) if side < 0 else L * (1 - stop_pct)
    if (side < 0 and target >= L) or (side > 0 and target <= L):
        return None

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

        if mode == "limit":
            entry = L                      # resting order, filled on the touch
        else:
            if not rejected:               # needs the close -> cannot enter at L
                continue
            if bd_min > 0:
                if vol[i] <= 0 or abs(dv[i]) / vol[i] < bd_min \
                   or np.sign(dv[i]) != side:
                    continue
            entry = L if mode == "level" else c[i]

        risk = abs(stop - entry)
        if risk <= 0:
            continue
        rr = abs(entry - target) / risk
        if (side < 0 and target >= entry) or (side > 0 and target <= entry):
            continue

        # a limit fill happens mid-bar, so the rest of that same bar can stop it
        start = i if mode == "limit" else i + 1
        r = np.nan
        for j in range(start, n):
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
            r = ((entry - c[n - 1]) if side < 0 else (c[n - 1] - entry)) / risk
        return dict(r=r, rr=rr, ts=idx[i], entry=entry)
    return None


def collect(sess, days, stop_pct, mode, bd_min=0.0, levels=ALL8):
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
            t = trade(b, lv[name], side, lv["pdPOC"], stop_pct, mode, bd_min)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=name, side=side, day=d)
                best = t
        if best:
            rows.append(best)
    return pd.DataFrame(rows)


def line(label, T, nd):
    s = summ(T.r) if len(T) else "n=0"
    print(f"{label:40s} {s:52s} {len(T)/nd*5:.1f}/wk", flush=True)


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    nd = len(days) - COMPOSITE_N - 1
    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("all 8 fixed levels · both sides · target prior-day POC · "
          "first trigger after 10:00\n")

    for pct in (0.0015, 0.0025):
        print(f"=== stop {pct*100:.2f}%  ({pct*NQ_REF:.0f} NQ pts beyond the level) ===",
              flush=True)
        line("  entry at LEVEL (lookahead)", collect(sess, days, pct, "level"), nd)
        line("  entry at CLOSE (realistic)", collect(sess, days, pct, "close"), nd)
        line("  resting LIMIT, every touch", collect(sess, days, pct, "limit"), nd)
        line("  CLOSE + bar delta >=10%",
             collect(sess, days, pct, "close", 0.10), nd)
        line("  CLOSE + bar delta >=20%",
             collect(sess, days, pct, "close", 0.20), nd)
        print(flush=True)

    print("=== realistic entry: stop sweep (CLOSE + bar delta >=10%) ===", flush=True)
    print(f"{'stop':>7s} {'NQ pts':>7s}  {'':52s} {'meanRR':>7s}", flush=True)
    for pct in (0.0015, 0.0020, 0.0025, 0.0035, 0.0050, 0.0070):
        T = collect(sess, days, pct, "close", 0.10)
        s = summ(T.r) if len(T) else "n=0"
        rr = f"{T.rr.mean():.2f}" if len(T) else "-"
        print(f"{pct*100:6.2f}% {pct*NQ_REF:7.0f}  {s:52s} {rr:>7s}", flush=True)

    print("\n=== out of sample, realistic entry (stop 0.25%, bar delta >=10%) ===",
          flush=True)
    T = collect(sess, days, 0.0025, "close", 0.10)
    mid = days[len(days) // 2]
    line(f"  first half  to {mid.date()}", T[T.day < mid], nd / 2)
    line(f"  second half from {mid.date()}", T[T.day >= mid], nd / 2)
    if len(T):
        r = T.r.values
        eq = np.cumsum(r)
        dd = (np.maximum.accumulate(eq) - eq).max()
        streak = max((len(list(g)) for k, g in itertools.groupby(r < 0) if k), default=0)
        print(f"\n  median {np.median(r):+.2f}R   max DD {dd:.1f}R   "
              f"worst streak {streak}   best {r.max():+.1f}R   "
              f"mean R:R {T.rr.mean():.2f}", flush=True)
        print("\n  by level:", flush=True)
        for nm, g in T.groupby("level"):
            line(f"    {nm}", g, nd)


if __name__ == "__main__":
    main()
