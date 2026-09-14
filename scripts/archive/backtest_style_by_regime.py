#!/usr/bin/env python3
"""Should the TRADE STYLE switch with the gamma regime?

Hypothesis under test: in POSITIVE gamma dealers dampen moves, so fading the
edges should beat continuation; in NEGATIVE gamma dealers amplify, so
continuation should win. The chart currently plots continuation in both.

Two style variants, same FVG machinery, same structure stop, same
skip-first-hour, same one-per-gap, same maxStopATR filter:

  CONT : take the gap retrace WITH session VWAP  (long above / short below)
  FADE : take the gap retrace AGAINST session VWAP (bet on reversion to VWAP)

Conditioners tested:
  * net GEX sign from the PRIOR session's option chain (no lookahead)
  * spot vs gamma flip
  * where the entry sits between the put wall and the call wall
    (0 = at put wall, 1 = at call wall) — "the edges" the theory talks about

Usage: python3 scripts/backtest_style_by_regime.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest_tos_fvg as B

ROOT = Path(__file__).resolve().parent.parent
MAX_ATR = 2.5          # the study's default risk filter
EXIT = "trailPrevLow"  # steadiest exit (t=5.8)


def prior_gex():
    """session date -> the option read from the PRIOR session (what you'd know
    pre-open). Returns dict with net_gex, gamma_flip, call_wall, put_wall."""
    recs = []
    f = ROOT / "data" / "gex_history.jsonl"
    for line in f.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            r["_d"] = pd.Timestamp(r["date"]).normalize()
            recs.append(r)
    recs.sort(key=lambda r: r["_d"])
    return recs


def lookup_prior(recs, day):
    prev = None
    for r in recs:
        if r["_d"] < day:
            prev = r
        else:
            break
    return prev


def signals_mode(b, mode):
    """Exact ToS machinery, but `mode` picks which side of VWAP we accept.
    mode='cont' -> with VWAP (the chart). mode='fade' -> against VWAP."""
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    vol = b["volume"].values
    n = len(b)
    hlc3 = (h + l + c) / 3
    vwap = np.cumsum(vol * hlc3) / np.cumsum(vol)
    a = B.atr(h, l, c)
    out = []
    bTop = bBot = rTop = rBot = np.nan
    bUsed = rUsed = False
    for i in range(n):
        t = b.index[i].time()
        newBull = i >= 2 and l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= B.MIN_GAP
        newBear = i >= 2 and h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= B.MIN_GAP
        if newBull:
            bTop, bBot, bUsed = l[i], h[i - 2], False
        elif not np.isnan(bBot) and l[i] <= bBot:
            bTop = bBot = np.nan; bUsed = False
        if newBear:
            rTop, rBot, rUsed = l[i - 2], h[i], False
        elif not np.isnan(rTop) and h[i] >= rTop:
            rTop = rBot = np.nan; rUsed = False
        timeOK = t >= B.SKIP_UNTIL
        above = c[i] > vwap[i]
        if (not np.isnan(bTop)) and not newBull and l[i] <= bTop and timeOK \
                and not bUsed and i >= B.K:
            want = above if mode == "cont" else (not above)
            if want:
                entry = bTop; stop = l[max(0, i - B.K):i + 1].min()
                if entry - stop > 0 and l[i] > stop:
                    out.append(dict(i=i, s=1, entry=entry, stop=stop,
                                    risk=entry - stop, atr=a[i]))
            bUsed = True
        if (not np.isnan(rBot)) and not newBear and h[i] >= rBot and timeOK \
                and not rUsed and i >= B.K:
            want = (not above) if mode == "cont" else above
            if want:
                entry = rBot; stop = h[max(0, i - B.K):i + 1].max()
                if stop - entry > 0 and h[i] < stop:
                    out.append(dict(i=i, s=-1, entry=entry, stop=stop,
                                    risk=stop - entry, atr=a[i]))
            rUsed = True
    return out, vwap


def collect():
    sess = B.load_sessions()
    recs = prior_gex()
    rows = []
    for d in sorted(sess):
        g = lookup_prior(recs, d)
        if not g:
            continue
        b = sess[d]
        h, l, c = (b[x].values for x in ("high", "low", "close"))
        n = len(b)
        pw, cw = g.get("put_wall"), g.get("call_wall")
        flip, net = g.get("gamma_flip"), g.get("net_gex")
        for mode in ("cont", "fade"):
            sigs, vwap = signals_mode(b, mode)
            for s in sigs:
                if s["atr"] and s["risk"] / s["atr"] > MAX_ATR:
                    continue
                R = B.exit_R(EXIT, s["s"], s["i"], s["entry"], s["stop"], s["risk"],
                             h, l, c, vwap, n)
                pos = np.nan
                if pw and cw and cw > pw:
                    pos = (s["entry"] - pw) / (cw - pw)      # 0=put wall, 1=call wall
                rows.append(dict(day=d, mode=mode, dir=s["s"], R=R,
                                 net=net, flip=flip, wallpos=pos,
                                 above_flip=(s["entry"] > flip) if flip else np.nan))
    return pd.DataFrame(rows)


def show(T, title, groups):
    print(f"\n{title}")
    print(f"  {'bucket':<26} {'CONT n':>7} {'CONT R':>8} {'FADE n':>7} {'FADE R':>8}  winner")
    for label, mask in groups:
        c = T[(T["mode"] == "cont") & mask]
        f = T[(T["mode"] == "fade") & mask]
        if len(c) < 25 and len(f) < 25:
            continue
        cm, fm = c.R.mean() if len(c) else np.nan, f.R.mean() if len(f) else np.nan
        win = "CONT" if (cm or -9) > (fm or -9) else "FADE"
        print(f"  {label:<26} {len(c):7d} {cm:+8.3f} {len(f):7d} {fm:+8.3f}  {win}")


def main():
    T = collect()
    print(f"=== STYLE vs GAMMA REGIME — {T.day.nunique()} sessions, exit={EXIT}, "
          f"maxStopATR={MAX_ATR} ===")
    print(f"total trades: cont {len(T[T['mode']=='cont'])}, fade {len(T[T['mode']=='fade'])}")

    show(T, "1) By net GEX sign (prior session's chain — no lookahead):",
         [("NEGATIVE gamma", T.net < 0), ("POSITIVE gamma", T.net > 0)])

    show(T, "2) By price vs gamma flip at entry:",
         [("below flip (short gamma)", T.above_flip == False),
          ("above flip (long gamma)", T.above_flip == True)])

    W = T.dropna(subset=["wallpos"])
    show(W, "3) Where the entry sits between the walls (0=put wall, 1=call wall):",
         [("lower edge  (<0.25)", W.wallpos < 0.25),
          ("mid range   (0.25-0.75)", (W.wallpos >= 0.25) & (W.wallpos <= 0.75)),
          ("upper edge  (>0.75)", W.wallpos > 0.75)])

    # the sharpest version of the user's question:
    P = W[W.net > 0]
    show(P, "4) POSITIVE gamma only, by wall position (theory says fade the edges):",
         [("pos-gamma lower edge", P.wallpos < 0.25),
          ("pos-gamma mid", (P.wallpos >= 0.25) & (P.wallpos <= 0.75)),
          ("pos-gamma upper edge", P.wallpos > 0.75)])

    # direction split at the edges — are longs into the call wall the problem?
    print("\n5) CONT trades by direction near the edges (is buying into the call "
          "wall the leak?):")
    C = W[W["mode"] == "cont"]
    for lab, m in (("upper edge (>0.75)", C.wallpos > 0.75),
                   ("lower edge (<0.25)", C.wallpos < 0.25)):
        for dlab, dm in (("long", C.dir == 1), ("short", C.dir == -1)):
            x = C[m & dm]
            if len(x) < 15:
                continue
            print(f"   {lab:<20} {dlab:<6} n={len(x):4d}  mean {x.R.mean():+.3f}R  "
                  f"win {100*(x.R>0).mean():.0f}%")


if __name__ == "__main__":
    main()
