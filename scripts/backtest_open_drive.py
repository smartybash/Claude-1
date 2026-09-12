#!/usr/bin/env python3
"""OPEN DRIVE — confirm or kill the one positive result.

backtest_open_location.py found the only adequately-sampled positive of the
whole programme: take the direction of the first thirty minutes at 10:00, stop
at the opposing Initial Balance extreme, target 2R. n=523, +0.112R, PF 1.23,
t=+2.10, fires every session.

t=+2.10 is p~0.036 on its own, which after the number of hypotheses tested this
week is not evidence of anything. It needs to survive being split. This does
that, and nothing else:

  * out of sample, by date half
  * by opening location relative to prior-day value, and by gap size -- the
    base rates said a gap >=0.5 ATR flips a day from rotation to trend, so the
    drive should be stronger there if the mechanism is real
  * by Initial Balance width against ATR
  * target sweep, and the drive's own delta (proxy) agreeing with its direction

A real momentum edge should hold in both halves and strengthen on wide-gap /
wide-IB days. If it only exists in one half, or only in one bucket, it is a
fitted artifact and gets reported as such.

Usage: python3 scripts/backtest_open_drive.py
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
from backtest_aplus import session_profile, bar_delta, summ
from backtest_open_location import prior_va, atr_map, walk, IB_END


def build(sess, days, atr, tgt=2.0, bd_min=0.0):
    rows = []
    for i, d in enumerate(days):
        b = sess[d]
        ib = b[b.index.strftime("%H:%M") < IB_END]
        rest = b[b.index.strftime("%H:%M") >= IB_END]
        a = atr.get(d, np.nan)
        if len(ib) < 4 or len(rest) < 10 or not pd.notna(a) or a <= 0:
            continue
        entry = float(ib.close.iloc[-1])
        side = 1 if entry > float(ib.open.iloc[0]) else -1
        stop = float(ib.low.min()) if side > 0 else float(ib.high.max())
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        if bd_min > 0:
            dd = bar_delta(ib).sum()
            vv = float(ib.volume.sum())
            if vv <= 0 or abs(dd) / vv < bd_min or np.sign(dd) != side:
                continue
        target = entry + side * tgt * risk if tgt < 90 else (1e9 if side > 0 else -1e9)
        r = walk(rest.reset_index(drop=True), 0, entry, stop, target, side)
        if not r:
            continue

        va = prior_va(sess, days, i)
        op = float(b.open.iloc[0])
        if va:
            poc, vah, val = va
            loc = "above" if op > vah else ("below" if op < val else "inside")
            gap = (op - vah) / a if op > vah else ((op - val) / a if op < val else 0.0)
        else:
            loc, gap = "n/a", 0.0
        rows.append(dict(day=d, r=r[0], side=side, oloc=loc, gap=abs(gap),
                         ibw=(float(ib.high.max()) - float(ib.low.min())) / a,
                         risk_atr=risk / a))
    return pd.DataFrame(rows)


def line(label, T, nd):
    print(f"{label:44s} {summ(T.r) if len(T) else 'n=0':52s} "
          f"{len(T)/nd*5:.1f}/wk", flush=True)


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    atr = atr_map(sess, days)
    nd = len(days)
    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("open drive: direction of 09:30-10:00, entry at 10:00, "
          "stop at opposing IB extreme\n")

    print("=== target sweep ===", flush=True)
    for tgt in (1.0, 1.5, 2.0, 3.0, 99.0):
        line(f"  target {'hold to close' if tgt > 90 else f'{tgt:g}R'}",
             build(sess, days, atr, tgt), nd)

    T = build(sess, days, atr, 2.0)
    mid = days[len(days) // 2]
    print("\n=== OUT OF SAMPLE (target 2R) ===", flush=True)
    line(f"  first half  to {mid.date()}", T[T.day < mid], nd / 2)
    line(f"  second half from {mid.date()}", T[T.day >= mid], nd / 2)

    print("\n=== by opening location vs prior value ===", flush=True)
    for k, g in T.groupby("oloc"):
        line(f"  open {k} value", g, nd)

    print("\n=== by gap size (|open - value edge| / ATR) ===", flush=True)
    out = T[T["oloc"] != "inside"]
    line("  inside value (no gap)", T[T["oloc"] == "inside"], nd)
    line("  gap < 0.25 ATR", out[out.gap < 0.25], nd)
    line("  gap 0.25-0.50 ATR", out[(out.gap >= 0.25) & (out.gap < 0.50)], nd)
    line("  gap >= 0.50 ATR", out[out.gap >= 0.50], nd)

    print("\n=== by Initial Balance width vs ATR ===", flush=True)
    q = T.ibw.quantile([0.33, 0.67]).values
    line(f"  narrow IB (<{q[0]:.2f}x)", T[T.ibw < q[0]], nd)
    line(f"  mid IB", T[(T.ibw >= q[0]) & (T.ibw < q[1])], nd)
    line(f"  wide IB (>={q[1]:.2f}x)", T[T.ibw >= q[1]], nd)

    print("\n=== IB delta (proxy) agrees with the drive ===", flush=True)
    line("  no filter", T, nd)
    for bd in (0.05, 0.10, 0.20):
        line(f"  IB delta agrees >={bd*100:.0f}%",
             build(sess, days, atr, 2.0, bd), nd)

    print("\n=== by side ===", flush=True)
    for s, g in T.groupby("side"):
        line(f"  {'up' if s > 0 else 'down'} drive", g, nd)

    r = T.r.values
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(eq) - eq).max()
    streak = max((len(list(g)) for k, g in itertools.groupby(r < 0) if k), default=0)
    print(f"\nrisk: median {np.median(r):+.2f}R  max DD {dd:.1f}R  "
          f"worst streak {streak}  mean stop {T.risk_atr.mean():.2f} ATR", flush=True)


if __name__ == "__main__":
    main()
