#!/usr/bin/env python3
"""OPEN LOCATION — the structure every test so far has thrown away.

Every fade and continuation test in this repo skips 09:30-10:00 and keys off a
level touch. Both families are now exhausted: fading fixed levels loses
(-0.513R, t=-10.30), taking the break loses (-0.133R, t=-2.43). The diagnosis
is that the tradeable move at a level happens inside the breaking bar, below
the resolution of 5-minute data.

So this drops level-touch events entirely and tests a different structure: WHERE
THE DAY OPENS relative to prior-day value, and what it does in the first thirty
minutes. That is known at 09:30 with no lookahead, it is the foundation of
auction market theory, and it has never been tested here.

Part 1 measures base rates -- no trade, just what the market actually does from
each opening location. Those numbers are worth having even if nothing is
tradeable, because every "open outside value" claim in the literature is a
statement about them.

Part 2 tests three rules that follow from the base rates:

  A  RETURN TO VALUE   open outside prior value; when price trades back inside
                       (5-min close through the edge), take it toward the far
                       side of the value area. The classic failed-auction trade.
                       A late entry costs proportionally less here than in the
                       earlier tests because the target is the whole value area
                       rather than the POC.
  B  OPEN DRIVE        direction of the first 30 minutes, entered at 10:00,
                       stop at the opposing Initial Balance extreme.
  C  GAP FADE          open outside value, faded straight back toward the
                       nearest value edge from the 09:35 close.

Entries are always at a bar close that has already printed. No level-price
fills, which is the bug that invalidated the earlier results.

Usage: python3 scripts/backtest_open_location.py
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
from backtest_aplus import session_profile, summ

NQ_REF = 29400.0
IB_END = "10:00"


def prior_va(sess, days, i):
    if i == 0:
        return None
    return session_profile(sess[days[i - 1]], key=days[i - 1])


def classify(op, poc, vah, val):
    if op > vah:
        return "above value"
    if op < val:
        return "below value"
    return "inside value"


def atr_map(sess, days, n=14):
    tr, prev_c = {}, None
    for d in days:
        b = sess[d]
        h, l, c = float(b.high.max()), float(b.low.min()), float(b.close.iloc[-1])
        tr[d] = max(h - l, abs(h - prev_c), abs(l - prev_c)) if prev_c else h - l
        prev_c = c
    return pd.Series(tr).rolling(n).mean().shift(1)


def walk(b, start, entry, stop, target, side):
    """Return R from bar `start` onward. side +1 long, -1 short."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    rr = abs(target - entry) / risk
    for j in range(start, len(b)):
        if side > 0:
            if l[j] <= stop:
                return -1.0, rr
            if h[j] >= target:
                return rr, rr
        else:
            if h[j] >= stop:
                return -1.0, rr
            if l[j] <= target:
                return rr, rr
    last = c[-1]
    return (((last - entry) if side > 0 else (entry - last)) / risk), rr


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    atr = atr_map(sess, days)

    rows = []
    for i, d in enumerate(days):
        va = prior_va(sess, days, i)
        a = atr.get(d, np.nan)
        if not va or not pd.notna(a) or a <= 0:
            continue
        poc, vah, val = va
        b = sess[d]
        op = float(b["open"].iloc[0])
        cl = float(b["close"].iloc[-1])
        hi, lo = float(b["high"].max()), float(b["low"].min())
        rows.append(dict(
            day=d, cls=classify(op, poc, vah, val), op=op, cl=cl, atr=a,
            poc=poc, vah=vah, val=val,
            ret=(cl - op) / a,
            touch_poc=lo <= poc <= hi,
            touch_vah=lo <= vah <= hi,
            touch_val=lo <= val <= hi,
            back_in=(lo <= vah if op > vah else (hi >= val if op < val else True)),
            gap=(op - vah) / a if op > vah else ((op - val) / a if op < val else 0.0),
        ))
    D = pd.DataFrame(rows)

    print(f"QQQ 5-min RTH — {len(D)} sessions, {D.day.min().date()} to "
          f"{D.day.max().date()}\n")
    print("=" * 86)
    print("PART 1 — BASE RATES BY OPENING LOCATION (prior-day value area)")
    print("=" * 86)
    print(f"{'open':14s} {'days':>5s} {'%':>4s}  {'ret/ATR':>8s}  "
          f"{'P(back in)':>10s} {'P(POC)':>7s} {'P(VAH)':>7s} {'P(VAL)':>7s}")
    for c, g in D.groupby("cls"):
        print(f"{c:14s} {len(g):5d} {100*len(g)/len(D):3.0f}%  "
              f"{g.ret.mean():+8.3f}  {100*g.back_in.mean():9.0f}% "
              f"{100*g.touch_poc.mean():6.0f}% {100*g.touch_vah.mean():6.0f}% "
              f"{100*g.touch_val.mean():6.0f}%", flush=True)

    out = D[D.cls != "inside value"].copy()
    print(f"\nopen OUTSIDE value: {len(out)} days ({100*len(out)/len(D):.0f}%)")
    print(f"  price returns INTO value same day : {100*out.back_in.mean():.0f}%")
    print(f"  and then reaches the POC          : "
          f"{100*out[out.back_in].touch_poc.mean():.0f}%")
    for lbl, sub in (("  small gap (<0.5 ATR)", out[out.gap.abs() < 0.5]),
                     ("  large gap (>=0.5 ATR)", out[out.gap.abs() >= 0.5])):
        if len(sub):
            print(f"{lbl:24s} n={len(sub):4d}  back in "
                  f"{100*sub.back_in.mean():3.0f}%  ret/ATR {sub.ret.mean():+.3f}")

    print("\n" + "=" * 86)
    print("PART 2 — TRADEABLE RULES  (entry always at a printed bar close)")
    print("=" * 86)

    # --- A: return to value, target the FAR side of the value area
    for stop_atr in (0.25, 0.40, 0.60):
        res = []
        for i, d in enumerate(days):
            va = prior_va(sess, days, i)
            a = atr.get(d, np.nan)
            if not va or not pd.notna(a) or a <= 0:
                continue
            poc, vah, val = va
            b = sess[d]
            op = float(b["open"].iloc[0])
            if val <= op <= vah:
                continue
            side = -1 if op > vah else +1
            edge = vah if side < 0 else val
            far = val if side < 0 else vah
            c = b["close"].values
            for k in range(len(b)):
                back = (c[k] < edge) if side < 0 else (c[k] > edge)
                if not back:
                    continue
                entry = c[k]
                stop = entry + (stop_atr * a if side < 0 else -stop_atr * a)
                if (side < 0 and far >= entry) or (side > 0 and far <= entry):
                    break
                r = walk(b, k + 1, entry, stop, far, side)
                if r:
                    res.append(r[0])
                break
        print(f"A  return to value, stop {stop_atr:.2f} ATR   "
              f"{summ(res):52s} {len(res)/len(days)*5:.1f}/wk", flush=True)

    # --- B: open drive — first 30 min direction, entered at 10:00
    for tgt in (1.0, 2.0, 99.0):
        res = []
        for d in days:
            b = sess[d]
            ib = b[b.index.strftime("%H:%M") < IB_END]
            rest = b[b.index.strftime("%H:%M") >= IB_END]
            if len(ib) < 4 or len(rest) < 10:
                continue
            side = 1 if float(ib.close.iloc[-1]) > float(ib.open.iloc[0]) else -1
            entry = float(ib.close.iloc[-1])
            stop = float(ib.low.min()) if side > 0 else float(ib.high.max())
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            target = entry + side * (tgt * risk if tgt < 90 else 1e9)
            r = walk(rest.reset_index(drop=True), 0, entry, stop,
                     target if tgt < 90 else (1e9 if side > 0 else -1e9), side)
            if r:
                res.append(r[0])
        lbl = f"{tgt:.0f}R" if tgt < 90 else "hold to close"
        print(f"B  open drive, target {lbl:13s}   "
              f"{summ(res):52s} {len(res)/len(days)*5:.1f}/wk", flush=True)

    # --- C: gap fade from the 09:35 close back to the nearest value edge
    for stop_atr in (0.25, 0.40):
        res = []
        for i, d in enumerate(days):
            va = prior_va(sess, days, i)
            a = atr.get(d, np.nan)
            if not va or not pd.notna(a) or a <= 0:
                continue
            poc, vah, val = va
            b = sess[d]
            op = float(b["open"].iloc[0])
            if val <= op <= vah or len(b) < 6:
                continue
            side = -1 if op > vah else +1
            edge = vah if side < 0 else val
            entry = float(b["close"].iloc[0])
            if (side < 0 and edge >= entry) or (side > 0 and edge <= entry):
                continue
            stop = entry + (stop_atr * a if side < 0 else -stop_atr * a)
            r = walk(b, 1, entry, stop, edge, side)
            if r:
                res.append(r[0])
        print(f"C  gap fade to value edge, stop {stop_atr:.2f} ATR  "
              f"{summ(res):52s} {len(res)/len(days)*5:.1f}/wk", flush=True)


if __name__ == "__main__":
    main()
