"""Does the REAL dealer-gamma regime predict the next day? — simple, honest test.

Data: gex_history.jsonl (net GEX / gamma-flip per QQQ session, from Alpha Vantage
premium chains) + QQQ daily OHLC. The chain's OI is as-of session D's close, so
it sets D+1's open -> regime(D) is tested against D+1's realized behavior.

Gamma is about MAGNITUDE, not direction: negative gamma (dealers amplify) should
give BIGGER, trendier next days; positive gamma (dealers dampen) smaller, rangey
ones. Metrics for D+1 (all %):
  range   = (High-Low)/prevClose        (how much it moved in total)
  |o->c|  = |Close-Open|/Open            (net directional travel)
  effic.  = |Close-Open|/(High-Low)      (trend day ~high, chop ~low)
Regime = sign of net GEX (neg = below flip). Compare group means + Welch t.
Scope: QQQ, ~31 sampled sessions Oct-2025..Aug-2026. Small sample — directional
read, not proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def qqq_daily():
    r = json.loads((ROOT / "data" / "qqq_daily_5y.json").read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime([t[:10] for t in r["time"]]))
    return df[~df.index.duplicated(keep="last")].sort_index()


def welch(a, b):
    a, b = np.array(a), np.array(b)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = (a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b)) ** 0.5
    return (a.mean() - b.mean()) / se if se else float("nan")


def main():
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gex = [g for g in gex if g["sym"] == "QQQ"]
    d = qqq_daily()
    dates = list(d.index)

    rows = []
    for g in gex:
        day = pd.Timestamp(g["date"])
        # next trading day in the daily series
        after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]
        o, h, l, c = (float(d.loc[nd, k]) for k in ("open", "high", "low", "close"))
        prevc = float(d.loc[day, "close"]) if day in d.index else o
        rng = (h - l) / prevc * 100
        oc = abs(c - o) / o * 100
        eff = abs(c - o) / (h - l) if h > l else np.nan
        rows.append({"date": g["date"], "neg": g["net_gex"] < 0,
                     "range": rng, "absoc": oc, "eff": eff})
    df = pd.DataFrame(rows)
    neg = df[df["neg"]]; pos = df[~df["neg"]]

    print("REAL GAMMA REGIME -> NEXT-DAY behavior (QQQ, Alpha Vantage GEX)")
    print(f"n = {len(df)}  ({len(neg)} negative-gamma days, {len(pos)} positive-gamma days)\n")
    hdr = f"{'metric':10s} | {'NEG-gamma':>12s} | {'POS-gamma':>12s} | {'diff':>8s} | {'Welch t':>8s}"
    print(hdr); print("-" * len(hdr))
    for col, lab in [("range", "range %"), ("absoc", "|o->c| %"), ("eff", "efficiency")]:
        n, p = neg[col].dropna(), pos[col].dropna()
        print(f"{lab:10s} | {n.mean():>12.3f} | {p.mean():>12.3f} | {n.mean()-p.mean():>+8.3f} | {welch(n,p):>8.2f}")

    print("\nread: positive Welch t on range / |o->c| = negative-gamma days ARE bigger/"
          "trendier next day (the tell holds). |t|>~2 on n this small is suggestive, not proof.")
    # split-half stability on the headline (range)
    df = df.sort_values("date")
    mid = len(df) // 2
    for lab, part in [("first half ", df.iloc[:mid]), ("second half", df.iloc[mid:])]:
        n = part[part["neg"]]["range"]; p = part[~part["neg"]]["range"]
        if len(n) and len(p):
            print(f"  {lab}: NEG range {n.mean():.2f}% vs POS {p.mean():.2f}%  (diff {n.mean()-p.mean():+.2f})")


if __name__ == "__main__":
    main()
