#!/usr/bin/env python3
"""Chop-zone (range-compression) breakout — is it a real edge, and does the
gamma regime tell you when a breakout RUNS vs FADES?

Motivation: on a positive-gamma day the fade at the edges failed — price had
compressed for days and then broke out and ran. This tests that directly:

  compression : the prior N daily bars form a TIGHT box — box width in the
                bottom tercile of its own trailing 60-day distribution
  breakout    : price trades beyond the box (long above box-hi / short below
                box-lo); entry at the box edge (stop-order fill, no lookahead)
  stop        : the opposite side of the box (a clean range stop)
  exits       : measured-move (box height), fixed 2R/3R, trail prior bar
  regime      : split by the PRIOR session's option read (net GEX sign, price
                vs flip, and whether the breakout punches THROUGH a wall) —
                the 'gamma squeeze' is a breakout in negative gamma / through
                a wall, where dealers must chase.

Also measures the FAILURE rate (price closes back inside the box within 3 days)
so we can see whether positive gamma really does fade breakouts.

Daily QQQ 5y for the raw edge; gamma split limited to the 279 days with an
option read (2025-07+). Honest about the small n there.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load_daily():
    d = json.load(open(ROOT / "data/qqq_daily_5y.json"))
    df = pd.DataFrame({k: d[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(d["time"]).tz_localize(None)).sort_index()
    return df


def gamma_map():
    """session date -> prior session's option read (no lookahead)."""
    reads = []
    for line in (ROOT / "data/gex_history.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line); r["_d"] = pd.Timestamp(r["date"]).normalize()
            reads.append(r)
    reads.sort(key=lambda r: r["_d"])
    out = {}
    for i in range(1, len(reads)):
        out[reads[i]["_d"]] = reads[i - 1]      # prior read = pre-market known
    return out


def atr(h, l, c, n=14):
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[h[0] - l[0]], tr])
    return pd.Series(tr).ewm(alpha=1/n, adjust=False).mean().values


def walk(dirn, i, entry, stop, risk, box_h, h, l, c, n, rule):
    """forward R for one breakout under an exit rule."""
    s = 1 if dirn == "long" else -1
    def hit_stop(j): return (l[j] <= stop) if s > 0 else (h[j] >= stop)
    def fav(j): return h[j] if s > 0 else l[j]
    def rr(p): return s * (p - entry) / risk
    if rule == "measured":                       # target = box height
        tgt = entry + s * box_h
        for j in range(i + 1, n):
            if hit_stop(j): return -1.0
            if (fav(j) >= tgt) if s > 0 else (fav(j) <= tgt): return box_h / risk
        return rr(c[n - 1])
    if rule.startswith("fixed"):
        M = float(rule[5]); tgt = entry + s * M * risk
        for j in range(i + 1, n):
            if hit_stop(j): return -1.0
            if (fav(j) >= tgt) if s > 0 else (fav(j) <= tgt): return M
        return rr(c[n - 1])
    if rule == "trail":
        ts = stop
        for j in range(i + 1, n):
            ts = max(ts, l[j - 1]) if s > 0 else min(ts, h[j - 1])
            if (l[j] <= ts) if s > 0 else (h[j] >= ts): return s * (ts - entry) / risk
        return rr(c[n - 1])
    raise ValueError(rule)


def failed_back_in(dirn, i, box_hi, box_lo, h, l, c, n, k=3):
    """did price close back inside the box within k days? (false breakout)"""
    for j in range(i + 1, min(i + 1 + k, n)):
        if box_lo <= c[j] <= box_hi:
            return True
    return False


def summ(x):
    x = np.asarray(x, float)
    if len(x) == 0: return dict(n=0, mean=0, win=0, t=0, tot=0)
    sd = x.std(ddof=1) if len(x) > 1 else 0
    return dict(n=len(x), mean=x.mean(), win=(x > 0).mean()*100, tot=x.sum(),
                t=(x.mean()/(sd/np.sqrt(len(x)))) if sd > 0 else 0)


def run(N, atr_cap=None, comp_mode="quantile", atr_k=2.0):
    """comp_mode:
       'quantile' — box width in bottom tercile of trailing 60d (adaptive, but
                    needs a rolling quantile that thinkScript can't compute).
       'atr'      — box height <= atr_k * ATR(14). Dimensionless, one line of
                    thinkScript, so THIS is the rule the ToS chart ships. The
                    daily backtest below proves the ATR rule keeps the edge."""
    df = load_daily()
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    n = len(df); a = atr(h, l, c)
    gm = gamma_map()
    idx = df.index

    # rolling box + compression flag
    box_hi = pd.Series(h).rolling(N).max().shift(1).values
    box_lo = pd.Series(l).rolling(N).min().shift(1).values
    width = (box_hi - box_lo) / c
    wser = pd.Series(width)
    comp_thr = wser.rolling(60).quantile(0.33).values      # bottom tercile, adaptive

    trades = []
    for i in range(N + 60, n):
        if comp_mode == "quantile":
            if np.isnan(comp_thr[i]) or width[i] > comp_thr[i]:
                continue                                    # not a chop zone
        else:  # atr-native (thinkScript-implementable)
            if np.isnan(a[i]) or (box_hi[i] - box_lo[i]) > atr_k * a[i]:
                continue
        bh, bl = box_hi[i], box_lo[i]; box_h = bh - bl
        if box_h <= 0: continue
        g = gm.get(idx[i].normalize())
        for dirn, brk in (("long", h[i] > bh), ("short", l[i] < bl)):
            if not brk: continue
            entry = bh if dirn == "long" else bl
            stop = bl if dirn == "long" else bh
            risk = abs(entry - stop)
            if risk <= 0: continue
            if atr_cap and risk > atr_cap * a[i]: continue  # optional risk filter
            rec = dict(dir=dirn, i=i, date=idx[i].date(), box_h=box_h,
                       risk_atr=risk/a[i] if a[i] else np.nan)
            for rule in ("measured", "fixed2R", "fixed3R", "trail"):
                rec[rule] = walk(dirn, i, entry, stop, risk, box_h, h, l, c, n, rule)
            rec["failback"] = failed_back_in(dirn, i, bh, bl, h, l, c, n)
            # regime tags
            if g:
                rec["net"] = g.get("net_gex")
                flip = g.get("gamma_flip"); rec["above_flip"] = (entry > flip) if flip else None
                cw, pw = g.get("call_wall"), g.get("put_wall")
                # 'through a wall' = breakout entry punches past the wall on its side
                rec["thru_wall"] = ((dirn == "long" and cw and bh < cw <= h[i]) or
                                    (dirn == "short" and pw and bl > pw >= l[i]))
            trades.append(rec)
    return pd.DataFrame(trades)


def main():
    for N in (5, 10):
        T = run(N)
        print(f"\n{'='*70}\nCOMPRESSION-BREAKOUT — {N}-day box, QQQ daily 5y, "
              f"{T.date.nunique()} breakout days, {len(T)} trades\n{'='*70}")
        print(f"{'exit':10} {'n':>5} {'mean R':>8} {'win%':>6} {'total':>8} {'t':>6}")
        for rule in ("measured", "fixed2R", "fixed3R", "trail"):
            s = summ(T[rule]); print(f"{rule:10} {s['n']:5d} {s['mean']:+8.3f} "
                                     f"{s['win']:6.0f} {s['tot']:+8.1f} {s['t']:6.2f}")
        print(f"false-breakout rate (close back in box <=3d): {T.failback.mean()*100:.0f}%")

        # gamma split (where available)
        G = T.dropna(subset=["net"]) if "net" in T else T.iloc[0:0]
        if len(G) >= 30:
            print(f"\n  gamma split (n={len(G)} with a prior read), exit=trail:")
            for lab, m in (("NEG gamma (squeeze fuel)", G.net < 0),
                           ("POS gamma (should fade)", G.net > 0)):
                s = summ(G[m]["trail"]); fb = G[m].failback.mean()*100
                print(f"    {lab:26} n={s['n']:3d}  mean {s['mean']:+.3f}R  "
                      f"win {s['win']:3.0f}%  falseBrk {fb:.0f}%")
            tw = G[G.thru_wall == True]; nw = G[G.thru_wall != True]
            if len(tw) >= 10:
                print(f"    through a WALL (the squeeze)  n={len(tw):3d}  "
                      f"mean {summ(tw['trail'])['mean']:+.3f}R  "
                      f"win {summ(tw['trail'])['win']:.0f}%   vs no-wall "
                      f"{summ(nw['trail'])['mean']:+.3f}R")

    # ---- the rule the ToS chart actually ships (box height <= k*ATR) ----
    print(f"\n{'='*70}\nATR-NATIVE compression (this is what the chart computes; "
          f"thinkScript-safe)\n{'='*70}")
    print(f"{'N,k':>8} {'n':>5} {'meas R':>8} {'2R':>8} {'3R':>8} {'trail':>8} {'t(3R)':>7}")
    for N in (5, 10):
        for k in (2.0, 2.5):
            T = run(N, comp_mode="atr", atr_k=k)
            if len(T) == 0:
                print(f"{N},{k:>4} {'0':>5}  (no trades)"); continue
            s = {r: summ(T[r]) for r in ("measured", "fixed2R", "fixed3R", "trail")}
            print(f"{N},{k:>4} {len(T):5d} {s['measured']['mean']:+8.3f} "
                  f"{s['fixed2R']['mean']:+8.3f} {s['fixed3R']['mean']:+8.3f} "
                  f"{s['trail']['mean']:+8.3f} {s['fixed3R']['t']:7.2f}")
    print("\nChart ships N=5, box<=2.0*ATR, exit=run-it (3R target / box-height "
          "measured move). False-breakout ~55%: low win rate, high payoff — the "
          "OPPOSITE psychology to the fade. Take the break, let it run.")


if __name__ == "__main__":
    main()
