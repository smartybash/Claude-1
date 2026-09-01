#!/usr/bin/env python3
"""15-minute Opening Range Breakout + imbalance (FVG) confirmation — tested.

The Reddit/"Kasraborhan" rules:
  * mark ORH/ORL off the first 15 minutes of the session
  * wait for a candle to CLOSE outside the range (not just wick through)
  * confirm with a 3-candle imbalance (FVG) in the direction of the break
  * enter on the close of that imbalance
  * stop beyond the imbalance (below its low for a long / above its high short)
  * target 1-2R by stop size: on NQ, stop <30pt -> 2R, stop >30pt -> 1R
  * one trade/day (two max); move to BE once structure clears

Tested on QQQ 5-min RTH, ~2y (data/intraday) as the NQ proxy (same index; we
lack multi-year NQ 1-min). The opening range = the 09:30-09:45 bars. The
imbalance is the same 3-bar FVG our other backtests use (min 0.03% gap). NQ's
30-point stop threshold maps to ~0.10% of price, which is what we use to pick
the 1R vs 2R target.

Controls reported alongside:
  * plain ORB with no imbalance confirmation (does the FVG filter earn its keep?)
  * fixed 1R and fixed 2R vs the conditional target
  * gamma-regime split

Usage: python3 scripts/backtest_orb15.py
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F           # load_sessions()
import backtest_range_breakout as BR   # gamma_reads / gamma_lookup

OR_END = "09:45"          # first 15 minutes
MIN_GAP = 0.0003          # 3-bar FVG min size, 0.03% of price (same as our others)
TIGHT_STOP_PCT = 0.0010   # ~30 NQ pts as a fraction of price -> 2R, else 1R
MAX_WAIT = 24             # bars after the break to find the imbalance


def load_1m():
    """QQQ 1-min RTH bars -> {date: DataFrame} (12 months, data/intraday)."""
    frames = [pd.read_csv(f, parse_dates=["timestamp"])
              for f in sorted(glob.glob(str(ROOT / "data/intraday/qqq_1m_*.csv")))]
    df = pd.concat(frames).set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return {d: b for d, b in df.groupby(df.index.normalize()) if len(b) >= 200}


def opening_range(b):
    orb = b[b.index.strftime("%H:%M") < OR_END]
    if len(orb) < 2:
        return None
    return float(orb["high"].max()), float(orb["low"].min())


def manage(s, i, entry, stop, tgtR, h, l, c, n):
    """Return realised R for a fixed-R target, stop-first on ambiguous bars."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    tgt = entry + s * tgtR * risk
    for j in range(i + 1, n):
        hit_stop = (l[j] <= stop) if s > 0 else (h[j] >= stop)
        hit_tgt = (h[j] >= tgt) if s > 0 else (l[j] <= tgt)
        if hit_stop and hit_tgt:
            return -1.0
        if hit_stop:
            return -1.0
        if hit_tgt:
            return float(tgtR)
    return s * (c[n - 1] - entry) / risk


def simulate(b, use_fvg=True):
    """First ORB signal of the day. Returns dict or None."""
    rng = opening_range(b)
    if not rng:
        return None
    ORH, ORL = rng
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    idx = b.index
    n = len(b)
    start = int(np.searchsorted(np.array([t < OR_END for t in idx.strftime("%H:%M")]), False))
    brk_i = brk_s = None
    for i in range(start, n):
        if c[i] > ORH:
            brk_i, brk_s = i, 1; break
        if c[i] < ORL:
            brk_i, brk_s = i, -1; break
    if brk_i is None:
        return None
    s = brk_s

    if not use_fvg:
        # control: enter at the breakout close, stop at the far side of the OR
        entry = c[brk_i]; stop = ORL if s > 0 else ORH
        return _pack(s, brk_i, entry, stop, h, l, c, n, idx)

    # find a 3-bar imbalance in the break direction after the break
    for i in range(max(brk_i, 2) + 1, min(n, brk_i + MAX_WAIT + 1)):
        if s > 0 and l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
            entry = c[i]; stop = h[i - 2]            # "below the imbalance low"
            return _pack(s, i, entry, stop, h, l, c, n, idx)
        if s < 0 and h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
            entry = c[i]; stop = l[i - 2]            # "above the imbalance high"
            return _pack(s, i, entry, stop, h, l, c, n, idx)
    return None


def _pack(s, i, entry, stop, h, l, c, n, idx):
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    tight = (risk / entry) < TIGHT_STOP_PCT
    cond = manage(s, i, entry, stop, 2.0 if tight else 1.0, h, l, c, n)
    r1 = manage(s, i, entry, stop, 1.0, h, l, c, n)
    r2 = manage(s, i, entry, stop, 2.0, h, l, c, n)
    if cond is None:
        return None
    return dict(dir=s, r_cond=cond, r_1R=r1, r_2R=r2, tight=tight,
                risk_pct=risk / entry * 100, ts=idx[i])


def summ(rows, key):
    a = np.array([r[key] for r in rows], float) if rows else np.array([])
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    wins = a[a > 0].sum(); losses = -a[a < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return (f"n={len(a):4d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  "
            f"PF {pf:.2f}  total {a.sum():+6.1f}R  t={t:+.2f}")


def main():
    global MAX_WAIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="5m", choices=("5m", "1m"))
    ap.add_argument("--wait", type=int, help="bars after break to find the imbalance")
    a = ap.parse_args()
    if a.tf == "1m":
        sess = load_1m(); MAX_WAIT = a.wait or 20
    else:
        sess = F.load_sessions(); MAX_WAIT = a.wait or 24
    days = sorted(sess)
    reads = BR.gamma_reads("QQQ")
    print(f"=== 15-min ORB + imbalance — QQQ {a.tf}, {len(days)} sessions "
          f"{days[0].date()}..{days[-1].date()} (imbalance window {MAX_WAIT} bars) ===")
    print("(NQ proxy; OR = 09:30-09:45; break = CLOSE outside range; "
          "imbalance = 3-bar FVG; stop = far edge of the FVG)\n")

    for label, use in (("WITH imbalance confirmation (their rules)", True),
                       ("CONTROL: plain ORB, no imbalance filter", False)):
        rows = []
        for d in days:
            r = simulate(sess[d], use_fvg=use)
            if r:
                g = BR.gamma_lookup(reads, pd.Timestamp(d))
                r["net"] = g.get("net_gex") if g else None
                rows.append(r)
        print(f"--- {label}: {len(rows)} trades ({len(rows)/len(days):.2f}/day) ---")
        print(f"   their conditional target (2R if stop<0.10%, else 1R):")
        print(f"      {summ(rows, 'r_cond')}")
        print(f"   fixed 1R : {summ(rows, 'r_1R')}")
        print(f"   fixed 2R : {summ(rows, 'r_2R')}")
        if rows:
            print(f"   longs    : {summ([r for r in rows if r['dir']>0], 'r_cond')}")
            print(f"   shorts   : {summ([r for r in rows if r['dir']<0], 'r_cond')}")
            G = [r for r in rows if r.get("net") is not None]
            print(f"   POS gamma: {summ([r for r in G if r['net']>0], 'r_cond')}")
            print(f"   NEG gamma: {summ([r for r in G if r['net']<0], 'r_cond')}")
            rp = np.array([r["risk_pct"] for r in rows])
            print(f"   stop size: median {np.median(rp):.3f}% of price  "
                  f"({100*np.mean([r['tight'] for r in rows]):.0f}% qualify as 'tight' -> 2R)")
        print()


if __name__ == "__main__":
    main()
