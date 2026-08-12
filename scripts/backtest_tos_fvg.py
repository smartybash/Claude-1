#!/usr/bin/env python3
"""Backtest the EXACT rule set the ThinkOrSwim study plots — no approximation.

Why this exists: the earlier FVG backtests tested the *idea*. The chart study
implements a slightly narrower version of it, because thinkScript tracks the
most-recent gap in a `rec` variable rather than a list of every open gap. This
script mirrors the study line-for-line so the number on the chart is the number
that was tested:

  * 3-bar FVG, min size 0.03% of price          (same as backtest)
  * only the MOST RECENT bull / bear gap is live (study limitation, tested here)
  * gap dies when price fully fills it
  * entry = retrace to the gap's near edge, in the direction of session VWAP
  * one entry per gap
  * no entries 09:30-10:30 ET                    (OOS-validated skip-first-hour)
  * stop = structure swing low/high of the last K=5 bars (inclusive)

It then sweeps the exit rules and a MAX-RISK filter (the study's `maxStopATR`),
so the chart's defaults are chosen from measured expectancy, not taste.

Usage:  python3 scripts/backtest_tos_fvg.py [--sym QQQ]
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_GAP = 0.0003     # 0.03% of price
K = 5                # structure-stop lookback (bars back, inclusive)
SKIP_UNTIL = pd.Timestamp("10:30").time()
ATR_N = 14


# ----------------------------- data ------------------------------------------
def load_sessions():
    """QQQ 5-min RTH bars -> {date: DataFrame}."""
    frames = []
    for f in sorted(glob.glob(str(ROOT / "data/intraday/qqq_5m_*.csv"))):
        frames.append(pd.read_csv(f, parse_dates=["timestamp"]))
    df = pd.concat(frames).set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return {d: b for d, b in df.groupby(df.index.normalize()) if len(b) >= 20}


def regime_map():
    """date -> net GEX sign from the options log (the pre-open read)."""
    f = ROOT / "data" / "gex_history.jsonl"
    out = {}
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[pd.Timestamp(r["date"]).normalize()] = r.get("net_gex")
    return out


def atr(h, l, c, n=ATR_N):
    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[h[0] - l[0]], tr])
    out = np.full(len(tr), np.nan)
    run = tr[0]
    for i, x in enumerate(tr):
        run = x if i == 0 else (run * (n - 1) + x) / n
        out[i] = run
    return out


# ----------------------------- the study's logic ------------------------------
def signals(b, skip_first_hour=True, single_gap=True):
    """Mirror of the thinkScript. single_gap=True reproduces the chart exactly;
    False tracks every open gap (the original backtest) for comparison."""
    o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
    vol = b["volume"].values
    n = len(b)
    hlc3 = (h + l + c) / 3
    vwap = np.cumsum(vol * hlc3) / np.cumsum(vol)      # session-anchored, RTH
    a = atr(h, l, c)
    out = []

    if single_gap:
        bTop = bBot = rTop = rBot = np.nan
        bUsed = rUsed = False
        for i in range(n):
            t = b.index[i].time()
            newBull = i >= 2 and l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP
            newBear = i >= 2 and h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP
            if newBull:
                bTop, bBot, bUsed = l[i], h[i - 2], False
            elif not np.isnan(bBot) and l[i] <= bBot:
                bTop = bBot = np.nan; bUsed = False
            if newBear:
                rTop, rBot, rUsed = l[i - 2], h[i], False
            elif not np.isnan(rTop) and h[i] >= rTop:
                rTop = rBot = np.nan; rUsed = False
            timeOK = (not skip_first_hour) or t >= SKIP_UNTIL
            if (not np.isnan(bTop)) and not newBull and l[i] <= bTop and c[i] > vwap[i] \
                    and timeOK and not bUsed and i >= K:
                entry = bTop; stop = l[max(0, i - K):i + 1].min()
                if entry - stop > 0 and l[i] > stop:
                    out.append(dict(i=i, s=1, entry=entry, stop=stop,
                                    risk=entry - stop, atr=a[i], t=t))
                bUsed = True
            if (not np.isnan(rBot)) and not newBear and h[i] >= rBot and c[i] < vwap[i] \
                    and timeOK and not rUsed and i >= K:
                entry = rBot; stop = h[max(0, i - K):i + 1].max()
                if stop - entry > 0 and h[i] < stop:
                    out.append(dict(i=i, s=-1, entry=entry, stop=stop,
                                    risk=stop - entry, atr=a[i], t=t))
                rUsed = True
    else:
        gaps = []
        for i in range(n):
            t = b.index[i].time()
            if i >= 2:
                if l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
                    gaps.append(dict(side="bull", top=l[i], bot=h[i - 2], formed=i, used=False))
                if h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
                    gaps.append(dict(side="bear", top=l[i - 2], bot=h[i], formed=i, used=False))
            timeOK = (not skip_first_hour) or t >= SKIP_UNTIL
            for g in gaps:
                if g["used"] or i <= g["formed"] or i < K or not timeOK:
                    continue
                if g["side"] == "bull" and l[i] <= g["top"] and c[i] > vwap[i]:
                    entry = g["top"]; stop = l[max(0, i - K):i + 1].min()
                    if entry - stop > 0 and l[i] > stop:
                        out.append(dict(i=i, s=1, entry=entry, stop=stop,
                                        risk=entry - stop, atr=a[i], t=t))
                    g["used"] = True
                elif g["side"] == "bear" and h[i] >= g["bot"] and c[i] < vwap[i]:
                    entry = g["bot"]; stop = h[max(0, i - K):i + 1].max()
                    if stop - entry > 0 and h[i] < stop:
                        out.append(dict(i=i, s=-1, entry=entry, stop=stop,
                                        risk=stop - entry, atr=a[i], t=t))
                    g["used"] = True
            gaps = [g for g in gaps if g["used"] or not (
                (g["side"] == "bull" and l[i] <= g["bot"]) or
                (g["side"] == "bear" and h[i] >= g["top"]))]
    return out, vwap


# ----------------------------- exits (same as backtest_fvg_exits) -------------
def exit_R(rule, s, i, entry, stop, risk, h, l, c, vwap, n):
    def favor(j):   return h[j] if s > 0 else l[j]
    def stopped(j): return (l[j] <= stop) if s > 0 else (h[j] >= stop)
    def rr(p):      return s * (p - entry) / risk
    def vlost(j):   return (c[j] < vwap[j]) if s > 0 else (c[j] > vwap[j])

    if rule.startswith("fixed"):
        M = float(rule[5]); tgt = entry + s * M * risk
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if (favor(j) >= tgt) if s > 0 else (favor(j) <= tgt): return M
        return rr(c[n - 1])
    if rule == "vwapCross":
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if vlost(j): return rr(c[j])
        return rr(c[n - 1])
    if rule == "trailPrevLow":
        ts = stop
        for j in range(i + 1, n):
            ts = max(ts, l[j - 1]) if s > 0 else min(ts, h[j - 1])
            if (l[j] <= ts) if s > 0 else (h[j] >= ts):
                return s * (ts - entry) / risk
        return rr(c[n - 1])
    if rule.startswith("half@"):
        P = float(rule[5]); tgt = entry + s * P * risk
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if (favor(j) >= tgt) if s > 0 else (favor(j) <= tgt):
                rem = rr(c[n - 1])
                for k in range(j + 1, n):
                    if (l[k] <= entry) if s > 0 else (h[k] >= entry): rem = 0.0; break
                    if vlost(k): rem = rr(c[k]); break
                return 0.5 * P + 0.5 * rem
        return rr(c[n - 1])
    raise ValueError(rule)


def summarize(rs):
    rs = np.asarray(rs, dtype=float)
    if len(rs) == 0:
        return dict(n=0, mean=0.0, win=0.0, total=0.0, t=0.0)
    sd = rs.std(ddof=1) if len(rs) > 1 else 0.0
    return dict(n=len(rs), mean=rs.mean(), win=(rs > 0).mean() * 100,
                total=rs.sum(), t=(rs.mean() / (sd / np.sqrt(len(rs)))) if sd > 0 else 0.0)


# ----------------------------- main ------------------------------------------
RULES = ["fixed1R", "fixed2R", "fixed3R", "vwapCross", "trailPrevLow", "half@1", "half@2"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="QQQ")
    a = ap.parse_args()

    sess = load_sessions()
    reg = regime_map()
    days = sorted(sess)
    print(f"\n=== EXACT ToS FVG rule set — {a.sym} 5-min, {len(days)} sessions "
          f"{days[0].date()} .. {days[-1].date()} ===")

    # collect trades once (chart logic), and the multi-gap variant for comparison
    for label, single in (("CHART (most-recent gap only)", True),
                          ("multi-gap (original backtest)", False)):
        trades = []
        for d in days:
            b = sess[d]
            sigs, vwap = signals(b, skip_first_hour=True, single_gap=single)
            h, l, c = (b[x].values for x in ("high", "low", "close"))
            n = len(b)
            for g in sigs:
                rec = dict(day=d, net=reg.get(d), risk_atr=(g["risk"] / g["atr"]) if g["atr"] else np.nan,
                           risk_pct=g["risk"] / g["entry"] * 100, hour=g["t"].hour)
                for r in RULES:
                    rec[r] = exit_R(r, g["s"], g["i"], g["entry"], g["stop"], g["risk"],
                                    h, l, c, vwap, n)
                trades.append(rec)
        T = pd.DataFrame(trades)
        print(f"\n--- {label}: {len(T)} trades ({len(T)/len(days):.1f}/session) ---")
        print(f"{'exit rule':14} {'n':>5} {'mean R':>8} {'win%':>6} {'total R':>9} {'t-stat':>7}")
        for r in RULES:
            s = summarize(T[r])
            print(f"{r:14} {s['n']:5d} {s['mean']:+8.3f} {s['win']:6.0f} {s['total']:+9.1f} {s['t']:7.2f}")
        if single:
            CHART = T

    # ---- MAX-RISK filter sweep on the chart logic ----
    print(f"\n=== MAX-RISK FILTER (chart logic) — does capping stop size help? ===")
    print(f"risk distribution: median {CHART.risk_atr.median():.2f} ATR, "
          f"p75 {CHART.risk_atr.quantile(.75):.2f}, p90 {CHART.risk_atr.quantile(.90):.2f}, "
          f"max {CHART.risk_atr.max():.2f}")
    best = ("trailPrevLow", None, -9)
    for r in ("trailPrevLow", "fixed3R", "half@1"):
        print(f"\n  exit = {r}")
        print(f"    {'maxStopATR':>11} {'n':>5} {'kept%':>6} {'mean R':>8} {'win%':>6} {'total R':>9}")
        for cap in (None, 3.0, 2.5, 2.0, 1.5, 1.0):
            sub = CHART if cap is None else CHART[CHART.risk_atr <= cap]
            s = summarize(sub[r])
            tag = "none" if cap is None else f"{cap:.1f}"
            print(f"    {tag:>11} {s['n']:5d} {100*len(sub)/len(CHART):6.0f} "
                  f"{s['mean']:+8.3f} {s['win']:6.0f} {s['total']:+9.1f}")
            if s["n"] >= 100 and s["mean"] > best[2]:
                best = (r, cap, s["mean"])
    print(f"\n  -> best (n>=100): exit={best[0]}  maxStopATR={best[1]}  mean {best[2]:+.3f}R")

    # ---- regime split on the winner ----
    print(f"\n=== regime split (exit={best[0]}, maxStopATR={best[1]}) ===")
    sub = CHART if best[1] is None else CHART[CHART.risk_atr <= best[1]]
    for name, m in (("NEG gamma", sub.net < 0), ("POS gamma", sub.net > 0)):
        s = summarize(sub[m][best[0]])
        print(f"  {name}: n={s['n']:4d}  mean {s['mean']:+.3f}R  win {s['win']:.0f}%  total {s['total']:+.1f}R")


if __name__ == "__main__":
    main()
