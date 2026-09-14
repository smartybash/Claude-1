"""Mine the AV options-chain features we already logged for more simple edges —
no new fetches. Uses data/gex_history.jsonl (31 QQQ sessions) + QQQ daily.

Tests, regime(D) -> next day D+1:
  1. DEALER DELTA sign -> next-day DIRECTION (signed open->close return). Delta is
     the directional axis: net-negative dealer delta = dealers must sell rallies
     (down pressure); positive = buy dips (up). Does it predict direction?
  2. NET GEX tercile -> next-day RANGE (dose-response check on the confirmed
     'negative gamma = wider day' finding: is more-negative even wider?)
  3. Spot vs gamma-flip DISTANCE -> next-day range (are we-deep-below-flip days
     the widest?)
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
    a, b = np.array(a, float), np.array(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = (a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b)) ** 0.5
    return (a.mean() - b.mean()) / se if se else float("nan")


def main():
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    d = qqq_daily(); dates = list(d.index)
    rows = []
    for g in gex:
        day = pd.Timestamp(g["date"])
        after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]
        o, h, l, c = (float(d.loc[nd, k]) for k in ("open", "high", "low", "close"))
        prevc = float(d.loc[day, "close"]) if day in d.index else o
        rows.append({"date": g["date"], "net_gex": g["net_gex"], "dd": g["dealer_delta"],
                     "flip_dist": (g["spot"] - g["gamma_flip"]) / g["spot"] * 100,
                     "ret": (c - o) / o * 100, "range": (h - l) / prevc * 100})
    df = pd.DataFrame(rows)
    print(f"AV options-chain features -> next-day (QQQ, n={len(df)})\n")

    # 1. dealer delta -> DIRECTION
    print("1) DEALER DELTA sign -> next-day signed return (open->close):")
    for lab, sub in [("delta<0 (dealers sell rallies)", df[df.dd < 0]),
                     ("delta>0 (dealers buy dips)   ", df[df.dd > 0])]:
        r = sub["ret"]
        print(f"   {lab}: mean {r.mean():+.3f}%  P(up) {(r>0).mean():.0%}  n={len(sub)}")
    lo, hi = df[df.dd < 0]["ret"], df[df.dd > 0]["ret"]
    print(f"   Welch t (up-delta minus down-delta): {welch(hi, lo):+.2f}   "
          f"corr(delta, ret) = {df['dd'].corr(df['ret']):+.2f}")

    # 2. net GEX tercile -> RANGE (dose)
    print("\n2) NET GEX tercile -> next-day range % (dose-response):")
    df["gbin"] = pd.qcut(df["net_gex"], 3, labels=["most negative", "middle", "most positive"])
    for b, sub in df.groupby("gbin", observed=True):
        print(f"   {b:14s}: range {sub['range'].mean():.3f}%  n={len(sub)}")

    # 3. distance below flip -> RANGE
    print("\n3) spot vs flip -> next-day range %:")
    for lab, sub in [("below flip (neg gamma)", df[df.flip_dist < 0]),
                     ("above flip (pos gamma)", df[df.flip_dist >= 0])]:
        print(f"   {lab}: range {sub['range'].mean():.3f}%  n={len(sub)}")
    print(f"   corr(distance-below-flip, range) = {(-df['flip_dist']).corr(df['range']):+.2f}")

    print("\nread: (1) delta t/|corr| near 0 = no directional edge; large = tradeable lean. "
          "(2) monotone rise toward 'most negative' = dose-response confirms the range finding.")


if __name__ == "__main__":
    main()
