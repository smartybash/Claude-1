#!/usr/bin/env python3
"""Daily FVG continuation — the edge behind the DAILY MNQ context chart, now
validated on the full ~27y history (QQQ/SPY/IWM) instead of a 5y ad-hoc run.

Reproduces generate_tos_daily.py's exact rule so the chart == the backtest:
  * 3-bar FVG (bull low>high[2], bear high<low[2]), min 0.03% of price
  * the 3 most-recent OPEN gaps per side (thinkScript can't hold an unbounded
    list); a slot empties when price fully fills that gap
  * FIRST touch of an open gap's near edge (price arriving from outside)
  * WITH the 20-SMA trend (long above / short below) — continuation only
  * stop = swing low/high of the last `K` daily bars
Exits compared: fixed 1R/2R/3R and trail-prior-bar. Also fades (against trend)
to reconfirm continuation is the right side, and a maxStopATR risk filter.

Difference from the chart, stated plainly: none in entry logic; the chart draws
signals but doesn't itself pick an exit, so the exit table here is what defines
the tradeable number.

Usage: python3 scripts/backtest_daily_fvg.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_range_breakout as BR       # load_daily, atr, summ

MIN_GAP = 0.0003      # 0.03% of price, same as the chart
TREND = 20            # 20-SMA trend filter
K = 5                 # swing-stop lookback
MAX_ATR = 2.5         # risk filter (skip stops wider than 2.5*ATR)


def fwd_R(dirn, i, entry, stop, risk, h, l, c, n, rule):
    s = 1 if dirn == "long" else -1
    def hit(j): return (l[j] <= stop) if s > 0 else (h[j] >= stop)
    def fav(j): return h[j] if s > 0 else l[j]
    if rule.endswith("R"):
        M = float(rule[:-1]); tgt = entry + s * M * risk
        for j in range(i + 1, n):
            if hit(j): return -1.0
            if (fav(j) >= tgt) if s > 0 else (fav(j) <= tgt): return M
        return s * (c[n - 1] - entry) / risk
    if rule == "trail":
        ts = stop
        for j in range(i + 1, n):
            ts = max(ts, l[j - 1]) if s > 0 else min(ts, h[j - 1])
            if (l[j] <= ts) if s > 0 else (h[j] >= ts): return s * (ts - entry) / risk
        return s * (c[n - 1] - entry) / risk
    raise ValueError(rule)


def signals(df, style="cont"):
    """Yield entries reproducing the chart's 3-slot first-touch logic."""
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    n = len(df)
    trend = pd.Series(c).rolling(TREND).mean().values
    a = BR.atr(h, l, c)
    # 3 bull + 3 bear slots (top/bot); nan = empty
    bbot = [np.nan] * 3; btop = [np.nan] * 3
    rtop = [np.nan] * 3; rbot = [np.nan] * 3
    out = []
    for i in range(n):
        pb_bot, pb_top = bbot[:], btop[:]          # prior-bar snapshots
        pr_top, pr_bot = rtop[:], rbot[:]
        nb = i >= 2 and l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP
        nr = i >= 2 and h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP
        # ---- bull slots ----
        if nb:
            bbot = [h[i - 2], pb_bot[0], pb_bot[1]]
            btop = [l[i],     pb_top[0], pb_top[1]]
        else:
            for k in range(3):
                if np.isnan(pb_bot[k]) or l[i] <= pb_bot[k]:
                    bbot[k] = np.nan; btop[k] = np.nan
                else:
                    bbot[k] = pb_bot[k]; btop[k] = pb_top[k]
        # ---- bear slots ----
        if nr:
            rtop = [l[i - 2], pr_top[0], pr_top[1]]
            rbot = [h[i],     pr_bot[0], pr_bot[1]]
        else:
            for k in range(3):
                if np.isnan(pr_top[k]) or h[i] >= pr_top[k]:
                    rtop[k] = np.nan; rbot[k] = np.nan
                else:
                    rtop[k] = pr_top[k]; rbot[k] = pr_bot[k]
        if i < TREND or np.isnan(trend[i]):
            continue
        up = c[i] > trend[i]
        # first touch of a bull gap top (arriving from above), not the formation bar
        bT = (not nb) and any((not np.isnan(btop[k])) and l[i] <= btop[k] and l[i - 1] > btop[k]
                              for k in range(3))
        rT = (not nr) and any((not np.isnan(rbot[k])) and h[i] >= rbot[k] and h[i - 1] < rbot[k]
                              for k in range(3))
        take_long = up if style == "cont" else (not up)
        take_short = (not up) if style == "cont" else up
        if bT and take_long:
            entry = max(btop[k] for k in range(3)
                        if not np.isnan(btop[k]) and l[i] <= btop[k] and l[i - 1] > btop[k])
            stop = l[max(0, i - K):i + 1].min()
            if entry - stop > 0:
                out.append(dict(i=i, dir="long", entry=entry, stop=stop,
                                risk=entry - stop, atr=a[i]))
        if rT and take_short:
            entry = min(rbot[k] for k in range(3)
                        if not np.isnan(rbot[k]) and h[i] >= rbot[k] and h[i - 1] < rbot[k])
            stop = h[max(0, i - K):i + 1].max()
            if stop - entry > 0:
                out.append(dict(i=i, dir="short", entry=entry, stop=stop,
                                risk=stop - entry, atr=a[i]))
    return out


def collect(sym, style="cont", max_atr=MAX_ATR):
    df = BR.load_daily(sym)
    h, l, c = (df[x].values for x in ("high", "low", "close")); n = len(df)
    idx = df.index
    reads = BR.gamma_reads("QQQ") if sym == "qqq" else []   # regime tag (QQQ only)
    rows = []
    for s in signals(df, style):
        if max_atr and s["atr"] and s["risk"] / s["atr"] > max_atr:
            continue
        rec = dict(sym=sym, dir=s["dir"])
        for rule in ("1R", "2R", "3R", "trail"):
            rec[rule] = fwd_R(s["dir"], s["i"], s["entry"], s["stop"], s["risk"],
                              h, l, c, n, rule)
        g = BR.gamma_lookup(reads, idx[s["i"]]) if reads else None
        rec["net"] = g.get("net_gex") if g else None
        rows.append(rec)
    return pd.DataFrame(rows)


def line(tag, T):
    if len(T) == 0:
        print(f"  {tag:<26} (no trades)"); return
    s2 = BR.summ(T["2R"]); s3 = BR.summ(T["3R"]); tr = BR.summ(T["trail"])
    print(f"  {tag:<26} n={s3['n']:4d}  2R {s2['mean']:+.3f}  3R {s3['mean']:+.3f} "
          f"(t {s3['t']:4.2f})  trail {tr['mean']:+.3f} (t {tr['t']:4.2f})")


def main():
    syms = ("qqq", "spy", "iwm")
    print("=== DAILY FVG CONTINUATION — full history (~27y), 3-slot first-touch, "
          f"trend={TREND}SMA, stopK={K}, maxStopATR={MAX_ATR} ===")
    pool = []
    for sym in syms:
        try:
            T = collect(sym, "cont")
        except FileNotFoundError:
            continue
        pool.append(T); line(sym.upper() + " continuation", T)
    if pool:
        P = pd.concat(pool, ignore_index=True)
        line("POOL continuation", P)
        line("  POOL long only", P[P.dir == "long"])
        line("  POOL short only", P[P.dir == "short"])
    # fade check — continuation should beat fading
    fpool = [collect(s, "fade") for s in syms if (ROOT / f"data/{s}_daily_full.json").exists()
             or (ROOT / f"data/{s}_daily_5y.json").exists()]
    if fpool:
        line("POOL FADE (against trend)", pd.concat(fpool, ignore_index=True))

    # gamma-regime split (QQQ, carry-forward reads from the extended history)
    if pool:
        Q = pool[0]
        G = Q.dropna(subset=["net"]) if "net" in Q else Q.iloc[0:0]
        if len(G) >= 30:
            print(f"\n  QQQ continuation by gamma regime (n={len(G)} tagged):")
            line("    NEG gamma", G[G.net < 0])
            line("    POS gamma", G[G.net > 0])


if __name__ == "__main__":
    main()
