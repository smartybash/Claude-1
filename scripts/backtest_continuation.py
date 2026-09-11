#!/usr/bin/env python3
"""CONTINUATION through fixed levels — the inverse of the trade that failed.

The fade testing produced one overwhelming result: a resting limit at prior-day
VAH / VAL / High / Low, filled on every touch, loses -0.513R at t=-10.30 over
500 trades. That is a far stronger signal than any positive number in this
repo, and it was treated as a caution instead of as a hypothesis.

A strategy that loses that reliably is an edge with the sign flipped. The
mechanism is straightforward: those levels are where stops sit. Price travels
to them in order to take them, the liquidity is consumed, and price continues.
Fading is standing in front of that.

So: same eight fixed levels, same harness, same discipline — but go WITH the
break rather than against it.

  TRIGGER  first 5-min bar after 10:00 that CLOSES beyond a fixed level by a
           margin (the level is taken, not merely touched)
  ENTRY    that bar's close. No lookahead anywhere: the close is known when
           the decision is made.
  STOP     back inside the level, by the same margin
  TARGETS  swept — next fixed level in the direction of travel, fixed R
           multiples, and hold-to-session-close

Also tests a RETEST entry (break confirmed, then a limit back at the level),
which pays a better price at the cost of not always filling.

Risk is capped: if the break bar is so large that the stop is further than
MAX_RISK away, the trade is skipped rather than taken at a terrible R.

Delta stays a proxy on QQQ bars: ((close-open)/(high-low)) * volume.

Usage: python3 scripts/backtest_continuation.py
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
from backtest_aplus2 import UPPER, LOWER, SKIP

ALL8 = UPPER + LOWER
NQ_REF = 29400.0
MAX_RISK = 0.0060       # skip if the stop sits further than 0.6% from entry


def trade(b, L, side, levels, stop_pct, target_mode, entry_mode="close",
          patience=6, bd_min=0.0):
    """First break of L after SKIP, taken in the direction of the break.

    side = +1 breaking UP through an upper level, -1 breaking DOWN through a
    lower one. Entry at the break bar's close, or on a retest limit at L.
    """
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    d = bar_delta(b)
    dv, vol = d.values, b["volume"].values
    n = len(b)
    marg = stop_pct * L

    for i in range(n):
        if idx[i].strftime("%H:%M") < SKIP:
            continue
        broke = (c[i] > L + marg) if side > 0 else (c[i] < L - marg)
        if not broke:
            continue
        if bd_min > 0:
            if vol[i] <= 0 or abs(dv[i]) / vol[i] < bd_min \
               or np.sign(dv[i]) != side:
                return None
        stop = L - marg if side > 0 else L + marg

        if entry_mode == "close":
            entry, start = c[i], i + 1
        else:                                    # retest: limit back at L
            fill = None
            for j in range(i + 1, min(i + 1 + patience, n)):
                if (side > 0 and l[j] <= L) or (side < 0 and h[j] >= L):
                    fill = j
                    break
            if fill is None:
                return dict(r=np.nan, filled=False, ts=idx[i])
            entry, start = L, fill

        risk = abs(entry - stop)
        if risk <= 0 or risk / entry > MAX_RISK:
            return None

        if target_mode == "level":
            cand = [v for v in levels.values() if (v > entry if side > 0 else v < entry)]
            if not cand:
                return None
            T = min(cand) if side > 0 else max(cand)
        elif target_mode == "close":
            T = None
        else:                                     # "2R", "3R" ...
            m = float(target_mode[:-1])
            T = entry + side * m * risk

        rr = abs(entry - T) / risk if T is not None else np.nan
        r = np.nan
        for j in range(start, n):
            if side > 0:
                if l[j] <= stop:
                    r = -1.0; break
                if T is not None and h[j] >= T:
                    r = rr; break
            else:
                if h[j] >= stop:
                    r = -1.0; break
                if T is not None and l[j] <= T:
                    r = rr; break
        if not np.isfinite(r):
            r = ((c[n - 1] - entry) if side > 0 else (entry - c[n - 1])) / risk
        return dict(r=r, rr=rr, filled=True, ts=idx[i], entry=entry)
    return None


def collect(sess, days, stop_pct, target_mode, entry_mode="close",
            patience=6, bd_min=0.0, levels_used=ALL8):
    rows = []
    for i, d in enumerate(days):
        if i < COMPOSITE_N + 1:
            continue
        b = sess[d]
        lv = build_levels(sess, days, i, float(b["open"].iloc[0]))
        if not lv or "pdPOC" not in lv:
            continue
        best = None
        for name in levels_used:
            if name not in lv:
                continue
            side = +1 if name in UPPER else -1       # break up through highs
            t = trade(b, lv[name], side, lv, stop_pct, target_mode,
                      entry_mode, patience, bd_min)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=name, side=side, day=d)
                best = t
        if best:
            rows.append(best)
    return pd.DataFrame(rows)


def line(label, T, nd):
    if not len(T):
        print(f"{label:42s} n=0", flush=True)
        return
    got = T[T.filled] if "filled" in T else T
    s = summ(got.r) if len(got) else "n=0"
    fill = f"fill {100*T.filled.mean():3.0f}%  " if "filled" in T else ""
    print(f"{label:42s} {s:52s} {fill}{len(got)/nd*5:.1f}/wk", flush=True)


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    nd = len(days) - COMPOSITE_N - 1
    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("break of a fixed level, taken WITH the break · entry at the bar's "
          "close · no lookahead\n")

    print("=== target sweep (stop 0.15% inside the level = 44 NQ pts) ===", flush=True)
    for tm in ("level", "1R", "2R", "3R", "close"):
        line(f"  target {tm}", collect(sess, days, 0.0015, tm), nd)

    print("\n=== stop sweep (target 2R) ===", flush=True)
    for pct in (0.0010, 0.0015, 0.0020, 0.0030, 0.0050):
        line(f"  stop {pct*100:.2f}% ({pct*NQ_REF:.0f} NQ pts)",
             collect(sess, days, pct, "2R"), nd)

    print("\n=== entry: break close vs retest limit (stop 0.15%, target 2R) ===",
          flush=True)
    line("  enter at break close", collect(sess, days, 0.0015, "2R"), nd)
    for K in (3, 6, 12):
        line(f"  retest limit, patience {K}",
             collect(sess, days, 0.0015, "2R", "retest", K), nd)

    print("\n=== best-guess config + flow filter ===", flush=True)
    line("  no filter", collect(sess, days, 0.0015, "2R"), nd)
    line("  break-bar delta agrees >=10%",
         collect(sess, days, 0.0015, "2R", bd_min=0.10), nd)
    line("  break-bar delta agrees >=20%",
         collect(sess, days, 0.0015, "2R", bd_min=0.20), nd)

    print("\n=== detail: stop 0.15%, target 2R, no filter ===", flush=True)
    T = collect(sess, days, 0.0015, "2R")
    if len(T):
        r = T.r.values
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
        print("\n  by side:", flush=True)
        for s, g in T.groupby("side"):
            line(f"    {'break up' if s > 0 else 'break down'}", g, nd)


if __name__ == "__main__":
    main()
