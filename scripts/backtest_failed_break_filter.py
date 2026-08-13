#!/usr/bin/env python3
"""Does a FAILED breakout on one side make the OTHER side's break run harder?

The trap idea (Wyckoff spring / upthrust): price pokes above a compressed range
and closes back inside — longs are trapped. When it then breaks the LOW, those
trapped longs bail into the move, so the downside break should run further than
a downside break with no prior failed poke. And symmetrically for a failed poke
below preceding an upside break.

Test, mechanically, no lookahead:
  box        : N-day range (prior bars), compressed = box height <= k*ATR(14)
               — the exact rule the ToS chart ships.
  failed poke: on a prior day, price traded BEYOND the box but CLOSED BACK
               INSIDE it (a rejected breakout).
  primed     : a breakout entry whose OPPOSITE side saw a failed poke within
               the last W days (the trapped-trader setup).
  entry/stop : box edge / far side, risk = box height (same as the base test).

Compares primed vs un-primed breakouts on mean R (3R and measured-move exits),
win rate, and false-breakout rate. If primed clearly wins, it is a usable
extra filter for the breakout study.

Usage: python3 scripts/backtest_failed_break_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_range_breakout as BR   # load_daily, atr, walk, failed_back_in, summ


def build(N=5, atr_k=2.0, W=5, sym="qqq"):
    df = BR.load_daily(sym)
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    n = len(df); a = BR.atr(h, l, c)
    idx = df.index

    box_hi = pd.Series(h).rolling(N).max().shift(1).values
    box_lo = pd.Series(l).rolling(N).min().shift(1).values
    compressed = np.zeros(n, bool)
    fail_up = np.zeros(n, bool)     # poke above, closed back inside
    fail_dn = np.zeros(n, bool)     # poke below, closed back inside
    for i in range(N + 1, n):
        bh, bl = box_hi[i], box_lo[i]
        if np.isnan(bh) or np.isnan(a[i]) or (bh - bl) <= 0:
            continue
        compressed[i] = (bh - bl) <= atr_k * a[i]
        if not compressed[i]:
            continue
        inside = bl <= c[i] <= bh
        fail_up[i] = h[i] > bh and inside
        fail_dn[i] = l[i] < bl and inside

    trades = []
    for i in range(N + 1, n):
        if not compressed[i]:
            continue
        bh, bl = box_hi[i], box_lo[i]; box_h = bh - bl
        # failed poke on either side in the prior W bars (strictly before today)
        w0 = max(0, i - W)
        prior_fail_up = fail_up[w0:i].any()
        prior_fail_dn = fail_dn[w0:i].any()
        for dirn, brk in (("long", h[i] > bh), ("short", l[i] < bl)):
            if not brk:
                continue
            entry = bh if dirn == "long" else bl
            stop = bl if dirn == "long" else bh
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            # primed = the OPPOSITE side failed recently (trapped traders fuel us)
            primed = prior_fail_up if dirn == "short" else prior_fail_dn
            same_primed = prior_fail_dn if dirn == "short" else prior_fail_up
            rec = dict(dir=dirn, date=idx[i].date(), primed=bool(primed),
                       same_primed=bool(same_primed))
            for rule in ("measured", "fixed2R", "fixed3R", "trail"):
                rec[rule] = BR.walk(dirn, i, entry, stop, risk, box_h, h, l, c, n, rule)
            rec["failback"] = BR.failed_back_in(dirn, i, bh, bl, h, l, c, n)
            trades.append(rec)
    return pd.DataFrame(trades)


def line(tag, x):
    s = BR.summ(x["fixed3R"]); m = BR.summ(x["measured"])
    fb = x.failback.mean() * 100 if len(x) else 0
    print(f"  {tag:<34} n={s['n']:4d}  3R {s['mean']:+.3f}R (t {s['t']:4.2f})  "
          f"meas {m['mean']:+.3f}R  win3R {s['win']:3.0f}%  falseBrk {fb:3.0f}%")


SYMS = ("qqq", "spy", "iwm")


def pooled(W):
    parts = []
    for sym in SYMS:
        try:
            t = build(W=W, sym=sym); t["sym"] = sym; parts.append(t)
        except FileNotFoundError:
            pass
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main():
    for W in (3, 5):
        T = build(W=W)
        print(f"\n{'='*78}\nFAILED-BREAK FILTER — N=5 box<=2.0*ATR, "
              f"opposite-side fail within W={W} days  (QQQ daily 5y)\n{'='*78}")
        line("ALL breakouts", T)
        line("PRIMED (opposite side failed)", T[T.primed])
        line("un-primed", T[~T.primed])
        # is it the trap direction specifically, or just any recent fail?
        line("  SAME-side failed recently", T[T.same_primed])
        # split by direction to make sure it isn't one-sided noise
        for d in ("long", "short"):
            sub = T[T.dir == d]
            line(f"{d}: PRIMED", sub[sub.primed])
            line(f"{d}: un-primed", sub[~sub.primed])

    # breadth: does the null hold across markets, on the bigger pooled sample?
    for W in (3, 5):
        P = pooled(W)
        if P.empty:
            continue
        print(f"\n{'='*78}\nFAILED-BREAK FILTER — POOLED QQQ+SPY+IWM, W={W} days"
              f"\n{'='*78}")
        line("ALL breakouts (pool)", P)
        line("PRIMED (opposite side failed)", P[P.primed])
        line("un-primed", P[~P.primed])


if __name__ == "__main__":
    main()
