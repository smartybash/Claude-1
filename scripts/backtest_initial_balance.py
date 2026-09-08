#!/usr/bin/env python3
"""INITIAL BALANCE (first 60 min) breakout — our own numbers.

ATAS provides Initial Balance natively (Market Profile & TPO). The published
ES/NQ stats claim narrow-IB days break out ~98% of the time with a much larger
extension than wide-IB days. That is the same compression -> expansion principle
our chop-zone breakout backtest already validated over 27y, so before building a
playbook on someone else's numbers we reproduce them on our own data.

QQQ 5-min RTH, ~2y. IB = 09:30-10:30 ET. IB width is classified against the
14-day ATR (narrow <0.5 ATR, normal, wide >1.0 ATR).

Reported per class:
  * break rate (a 5-min close beyond IBH/IBL after 10:30)
  * median extension reached, as a fraction of IB width beyond the broken edge
  * a mechanical trade: enter at the breakout close, stop at the IB midpoint,
    target +100% of IB width beyond the edge; realised R.

Usage: python3 scripts/backtest_initial_balance.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F           # load_sessions()
import backtest_range_breakout as BR   # gamma_reads / gamma_lookup

IB_END = "10:30"


def daily_atr(n=14):
    d = json.load(open(ROOT / "data" / "qqq_daily_full.json"))
    df = pd.DataFrame({k: d[k] for k in ("high", "low", "close")},
                      index=pd.to_datetime(d["time"]).normalize()).sort_index()
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def simulate(b, atr):
    ib = b[b.index.strftime("%H:%M") < IB_END]
    post = b[b.index.strftime("%H:%M") >= IB_END]
    if len(ib) < 8 or len(post) < 10 or not np.isfinite(atr) or atr <= 0:
        return None
    IBH, IBL = float(ib["high"].max()), float(ib["low"].min())
    width = IBH - IBL
    if width <= 0:
        return None
    mid = (IBH + IBL) / 2
    h, l, c = (post[x].values for x in ("high", "low", "close"))
    n = len(post)
    # first close beyond an edge
    bi = bs = None
    for i in range(n):
        if c[i] > IBH:
            bi, bs = i, 1; break
        if c[i] < IBL:
            bi, bs = i, -1; break
    rec = dict(width=width, w_atr=width / atr, broke=bi is not None)
    if bi is None:
        rec.update(ext=0.0, r=np.nan, dir=0)
        return rec
    edge = IBH if bs > 0 else IBL
    # max extension beyond the broken edge, in IB widths
    if bs > 0:
        ext = (h[bi:].max() - edge) / width
    else:
        ext = (edge - l[bi:].min()) / width
    entry = c[bi]; stop = mid
    risk = abs(entry - stop)
    r = np.nan
    if risk > 0:
        tgt = edge + bs * width          # +100% IB extension
        r = None
        for j in range(bi + 1, n):
            hit_stop = (l[j] <= stop) if bs > 0 else (h[j] >= stop)
            hit_tgt = (h[j] >= tgt) if bs > 0 else (l[j] <= tgt)
            if hit_stop and hit_tgt:
                r = -1.0; break
            if hit_stop:
                r = -1.0; break
            if hit_tgt:
                r = abs(tgt - entry) / risk; break
        if r is None:
            r = bs * (c[n - 1] - entry) / risk
    rec.update(ext=ext, r=r, dir=bs)
    return rec


def summ(a):
    a = np.array([x for x in a if np.isfinite(x)], float)
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    wins = a[a > 0].sum(); losses = -a[a < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return (f"n={len(a):4d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  "
            f"PF {pf:.2f}  t={t:+.2f}")


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    atr = daily_atr()
    reads = BR.gamma_reads("QQQ")
    rows = []
    for d in days:
        a = atr.get(pd.Timestamp(d).normalize(), np.nan)
        r = simulate(sess[d], float(a) if pd.notna(a) else np.nan)
        if r:
            g = BR.gamma_lookup(reads, pd.Timestamp(d))
            r["net"] = g.get("net_gex") if g else None
            r["day"] = d
            rows.append(r)
    T = pd.DataFrame(rows)
    print(f"=== INITIAL BALANCE (09:30-10:30) breakout — QQQ 5-min, {len(T)} sessions "
          f"{days[0].date()}..{days[-1].date()} ===\n")
    print(f"IB width vs 14d ATR: median {T.w_atr.median():.2f}x  "
          f"p25 {T.w_atr.quantile(.25):.2f}  p75 {T.w_atr.quantile(.75):.2f}\n")

    print(f"{'IB class':<22}{'n':>5}{'break rate':>12}{'median ext':>12}   trade (stop=IB mid, tgt=+100%)")
    for lo, hi, lbl in ((0, 0.5, "NARROW  <0.5x ATR"), (0.5, 1.0, "normal  0.5-1.0x"),
                        (1.0, 99, "WIDE    >1.0x ATR")):
        sub = T[(T.w_atr >= lo) & (T.w_atr < hi)]
        if len(sub) == 0:
            continue
        br = sub[sub.broke]
        print(f"{lbl:<22}{len(sub):>5}{100*sub.broke.mean():>11.0f}%"
              f"{br.ext.median():>11.2f}x   {summ(br.r)}")

    print(f"\nALL days            : break {100*T.broke.mean():.0f}%   "
          f"median ext {T[T.broke].ext.median():.2f}x   {summ(T[T.broke].r)}")
    B = T[T.broke]
    print(f"longs               : {summ(B[B.dir>0].r)}")
    print(f"shorts              : {summ(B[B.dir<0].r)}")
    G = B.dropna(subset=["net"])
    print(f"POS gamma           : {summ(G[G.net>0].r)}")
    print(f"NEG gamma           : {summ(G[G.net<0].r)}")
    N = B[B.w_atr < 0.5]
    if len(N):
        print(f"\nNARROW-IB only, by direction:")
        print(f"   longs  : {summ(N[N.dir>0].r)}")
        print(f"   shorts : {summ(N[N.dir<0].r)}")


# ---------------------------------------------------------------- sweep ------
def sweep():
    """Is there ANY stop/target combo that makes the IB breakout pay? The naive
    +100% target sits beyond the median extension, so sweep both."""
    sess = F.load_sessions(); days = sorted(sess); atr = daily_atr()
    recs = []
    for d in days:
        a = atr.get(pd.Timestamp(d).normalize(), np.nan)
        if not pd.notna(a) or a <= 0:
            continue
        b = sess[d]
        ib = b[b.index.strftime("%H:%M") < IB_END]
        post = b[b.index.strftime("%H:%M") >= IB_END]
        if len(ib) < 8 or len(post) < 10:
            continue
        IBH, IBL = float(ib["high"].max()), float(ib["low"].min())
        w = IBH - IBL
        if w <= 0:
            continue
        h, l, c = (post[x].values for x in ("high", "low", "close"))
        n = len(post); bi = bs = None
        for i in range(n):
            if c[i] > IBH: bi, bs = i, 1; break
            if c[i] < IBL: bi, bs = i, -1; break
        if bi is None:
            continue
        recs.append((h, l, c, n, bi, bs, IBH if bs > 0 else IBL, w, float(a)))

    print("\n\n=== SWEEP: does any stop/target make the IB breakout pay? ===")
    print("(entry = breakout close; stop & target in IB widths; narrow = IB<0.5xATR)\n")
    for tag, filt in (("NARROW IB (<0.5x ATR)", lambda w, a: w / a < 0.5),
                      ("ALL breakout days", lambda w, a: True)):
        sub = [r for r in recs if filt(r[7], r[8])]
        print(f"--- {tag}  (n={len(sub)}) ---")
        print(f"    {'stop':>10} " + "".join(f"{f'tgt {t:g}x':>16}" for t in (0.25, 0.5, 0.75, 1.0)))
        for sname, sfrac in (("0.25x IB", 0.25), ("0.50x IB", 0.50), ("1.00x IB", 1.00)):
            cells = []
            for tfrac in (0.25, 0.5, 0.75, 1.0):
                rs = []
                for h, l, c, n, bi, bs, edge, w, a in sub:
                    entry = c[bi]; stop = edge - bs * sfrac * w
                    risk = abs(entry - stop)
                    if risk <= 0: continue
                    tgt = edge + bs * tfrac * w
                    r = None
                    for j in range(bi + 1, n):
                        hs = (l[j] <= stop) if bs > 0 else (h[j] >= stop)
                        ht = (h[j] >= tgt) if bs > 0 else (l[j] <= tgt)
                        if hs: r = -1.0; break
                        if ht: r = abs(tgt - entry) / risk; break
                    if r is None: r = bs * (c[n - 1] - entry) / risk
                    rs.append(r)
                a_ = np.array(rs)
                w_ = a_[a_ > 0].sum(); lo_ = -a_[a_ < 0].sum()
                pf = w_ / lo_ if lo_ > 0 else float("inf")
                cells.append(f"{a_.mean():+.3f}R/PF{pf:.2f}")
            print(f"    {sname:>10} " + "".join(f"{x:>16}" for x in cells))
        print()


if __name__ == "__main__":
    main()
    sweep()
