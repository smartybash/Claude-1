#!/usr/bin/env python3
"""VWAP-RETEST continuation — Robert Rother's simple VWAP scalp, mechanised.

The strategy as described: intraday price EXTENDS away from the session VWAP
(establishes a trend leg), pulls BACK to VWAP, and if VWAP holds you enter in the
direction of the original extension (continuation), fixed reward:risk, and he
gates it by VIX (only take it when volatility is in a workable band). Claimed
win rate ~75%.

Mechanised rules (one trade per session, first valid signal):
  * session-anchored VWAP over RTH 5-min bars.
  * EXTENSION: running max distance of price from VWAP must reach `ext` * ATR
    on one side -> that fixes the leg direction (long if it extended ABOVE VWAP).
  * RETRACE + HOLD: a later bar tags VWAP (low<=VWAP<=high within tol) and CLOSES
    back on the leg side (close>VWAP for a long) -> continuation entry at close.
  * STOP: the opposite extreme of the signal bar (low for a long) minus a tick.
  * TARGET: fixed R multiples (swept). exit at session close if neither hit.
  * skip the first 30 min (before 10:00 ET); one entry per session.

Backtested on QQQ 5-min RTH (~2y, data/intraday). VIX gate from vix_daily_5y
(prior-close VIX for the session). We report the real win rate and expectancy,
split by VIX regime, so the 75% claim can be checked against measured results.

Usage: python3 scripts/backtest_vwap_retest.py
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
import backtest_tos_fvg as F              # load_sessions(), atr()

SKIP_UNTIL = pd.Timestamp("10:00").time()
TOL = 0.0004        # "at VWAP" within 0.04%


def vix_map():
    """session date -> prior-session VIX close (what you know at the open)."""
    d = json.load(open(ROOT / "data" / "vix_daily_5y.json"))
    s = pd.Series(d["close"], index=pd.to_datetime(d["time"]).tz_localize(None).normalize())
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return {cur: float(s.iloc[i - 1]) for i, cur in enumerate(s.index) if i > 0}


def simulate(b, ext, targetR):
    """One trade/session. Returns dict or None."""
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    vol = b["volume"].values
    n = len(b)
    hlc3 = (h + l + c) / 3
    vwap = np.cumsum(vol * hlc3) / np.cumsum(vol)
    a = F.atr(h, l, c)
    idx = b.index

    max_up = max_dn = 0.0        # running extension above / below VWAP, in ATR
    for i in range(n):
        if a[i] and a[i] > 0:
            max_up = max(max_up, (h[i] - vwap[i]) / a[i])
            max_dn = max(max_dn, (vwap[i] - l[i]) / a[i])
        if idx[i].time() < SKIP_UNTIL or i < 3:
            continue
        tol = TOL * vwap[i]
        # LONG continuation: extended above, pulls to VWAP, closes back above
        if max_up >= ext and l[i] <= vwap[i] + tol and c[i] > vwap[i]:
            entry = c[i]; stop = l[i] - 0.01
            risk = entry - stop
            if risk <= 0:
                continue
            tgt = entry + targetR * risk
            for j in range(i + 1, n):
                if l[j] <= stop:
                    return dict(dir=1, r=-1.0, ts=idx[i])
                if h[j] >= tgt:
                    return dict(dir=1, r=targetR, ts=idx[i])
            return dict(dir=1, r=(c[n - 1] - entry) / risk, ts=idx[i])
        # SHORT continuation: extended below, pulls up to VWAP, closes back below
        if max_dn >= ext and h[i] >= vwap[i] - tol and c[i] < vwap[i]:
            entry = c[i]; stop = h[i] + 0.01
            risk = stop - entry
            if risk <= 0:
                continue
            tgt = entry - targetR * risk
            for j in range(i + 1, n):
                if h[j] >= stop:
                    return dict(dir=-1, r=-1.0, ts=idx[i])
                if l[j] <= tgt:
                    return dict(dir=-1, r=targetR, ts=idx[i])
            return dict(dir=-1, r=(entry - c[n - 1]) / risk, ts=idx[i])
    return None


def simulate_revert(b, ext, stopR):
    """MEAN-REVERSION reading: when price is extended >= `ext` ATR from VWAP,
    FADE it back toward VWAP (target = VWAP), stop = `stopR` * (entry-VWAP dist)
    beyond the extreme. High win rate / small R is the signature that would match
    a '75% win' claim. One trade/session."""
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    vol = b["volume"].values
    n = len(b)
    hlc3 = (h + l + c) / 3
    vwap = np.cumsum(vol * hlc3) / np.cumsum(vol)
    a = F.atr(h, l, c)
    idx = b.index
    for i in range(n):
        if idx[i].time() < SKIP_UNTIL or i < 3 or not a[i] or a[i] <= 0:
            continue
        up = (h[i] - vwap[i]) / a[i]
        dn = (vwap[i] - l[i]) / a[i]
        # extended ABOVE -> fade SHORT back to VWAP
        if up >= ext and c[i] > vwap[i]:
            entry = c[i]; tgt = vwap[i]; risk = entry * 0.0015 + (h[i] - entry)
            stop = h[i] + stopR * (entry - tgt)
            for j in range(i + 1, n):
                if h[j] >= stop:
                    return dict(dir=-1, r=-(stop - entry) / (entry - tgt), ts=idx[i])
                if l[j] <= tgt:
                    return dict(dir=-1, r=1.0, ts=idx[i])
            return dict(dir=-1, r=(entry - c[n - 1]) / (entry - tgt), ts=idx[i])
        # extended BELOW -> fade LONG back to VWAP
        if dn >= ext and c[i] < vwap[i]:
            entry = c[i]; tgt = vwap[i]
            stop = l[i] - stopR * (tgt - entry)
            for j in range(i + 1, n):
                if l[j] <= stop:
                    return dict(dir=1, r=-(entry - stop) / (tgt - entry), ts=idx[i])
                if h[j] >= tgt:
                    return dict(dir=1, r=1.0, ts=idx[i])
            return dict(dir=1, r=(c[n - 1] - entry) / (tgt - entry), ts=idx[i])
    return None


def summ(rs):
    a = np.asarray(rs, float)
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    return f"n={len(a):4d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  total {a.sum():+6.1f}R  t={t:+.2f}"


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    vix = vix_map()
    print(f"=== VWAP-RETEST continuation — QQQ 5-min, {len(days)} sessions "
          f"{days[0].date()} .. {days[-1].date()} ===\n")

    print("Parameter sweep (extension in ATR x target R) — one trade/session:")
    print(f"  {'ext':>4} {'tgtR':>5}   {'result':<58}")
    best = None
    for ext in (1.0, 1.5, 2.0):
        for tgt in (1.0, 1.5, 2.0, 3.0):
            rs = [t["r"] for d in days if (t := simulate(sess[d], ext, tgt))]
            a = np.asarray(rs, float)
            m = a.mean() if len(a) else -9
            print(f"  {ext:>4.1f} {tgt:>5.1f}   {summ(rs)}")
            if len(a) >= 50 and (best is None or m > best[2]):
                best = (ext, tgt, m)
        print()
    if not best:
        print("no configuration with n>=50"); return
    ext, tgt, _ = best
    print(f"-> best expectancy (n>=50): ext={ext} ATR, target={tgt}R\n")

    rows = []
    for d in days:
        t = simulate(sess[d], ext, tgt)
        if t:
            rows.append(dict(day=d, r=t["r"], dir=t["dir"], vix=vix.get(d)))
    T = pd.DataFrame(rows)
    print(f"=== detail at ext={ext}, target={tgt}R ({len(T)} trades) ===")
    print(f"  ALL          : {summ(T.r)}")
    print(f"  LONG  legs   : {summ(T[T.dir==1].r)}")
    print(f"  SHORT legs   : {summ(T[T.dir==-1].r)}")

    V = T.dropna(subset=["vix"])
    if len(V):
        q1, q2 = V.vix.quantile([1/3, 2/3])
        print(f"\n  VIX terciles (prior close): low<{q1:.1f}  mid  high>{q2:.1f}")
        print(f"  VIX low  (<{q1:.1f}) : {summ(V[V.vix<q1].r)}")
        print(f"  VIX mid          : {summ(V[(V.vix>=q1)&(V.vix<=q2)].r)}")
        print(f"  VIX high (>{q2:.1f}): {summ(V[V.vix>q2].r)}")
        for thr in (16, 18, 20, 25):
            print(f"  VIX < {thr:>2}        : {summ(V[V.vix<thr].r)}")

    # ---- alternate reading: MEAN-REVERSION fade to VWAP (the high-win-rate shape) ----
    print(f"\n=== ALT reading: FADE the extension back TO VWAP (target=VWAP) ===")
    print(f"  {'ext':>4} {'stopR':>6}   {'result':<58}")
    for ext_r in (1.5, 2.0, 2.5, 3.0):
        for stopR in (0.5, 1.0):
            rs = [t["r"] for d in days if (t := simulate_revert(sess[d], ext_r, stopR))]
            print(f"  {ext_r:>4.1f} {stopR:>6.1f}   {summ(rs)}")
    rv = [dict(day=d, r=t["r"], vix=vix.get(d))
          for d in days if (t := simulate_revert(sess[d], 2.0, 1.0))]
    RV = pd.DataFrame(rv).dropna(subset=["vix"])
    if len(RV):
        print(f"\n  reversion (ext=2.0, stopR=1.0) VIX split:")
        for thr in (16, 18, 20):
            print(f"    VIX < {thr:>2} : {summ(RV[RV.vix<thr].r)}")

    print(f"\n  Robert's claim: ~75% win. Measured win rates above are the check.")


if __name__ == "__main__":
    main()
