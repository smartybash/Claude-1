"""Does 25-delta IV skew / risk-reversal predict next-day DIRECTION? — honest test.

Data: skew_history.jsonl (RR25 = IV(25d put) - IV(25d call) per QQQ session, from
av_skew.py over ~50 real chains) + QQQ daily OHLC. Skew(D close) -> tested on
D+1's open->close return.

Two framings, each with a contrarian and a momentum reading:
  LEVEL   high RR25 = lots of downside hedging (fear).
          contrarian -> next day UP (fear priced in); momentum -> next day DOWN.
  CHANGE  d_RR25 = today's RR25 minus prior session's (skew steepening/flattening).
          fear draining (d<0) -> UP; fear building (d>0) -> DOWN  (or the reverse).

Because the sample can be up/down skewed, direction is judged by (a) tercile
dose-response in mean return, (b) correlation (hard to game by guessing the
majority side), and (c) split-half stability -- not hit-rate alone.
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


def corr(a, b):
    a, b = np.array(a, float), np.array(b, float)
    return float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 else float("nan")


def main():
    sk = [json.loads(l) for l in (ROOT / "data" / "skew_history.jsonl").read_text().splitlines() if l.strip()]
    sk = sorted([s for s in sk if s["sym"] == "QQQ"], key=lambda s: s["date"])
    d = qqq_daily(); dates = list(d.index)
    prev = None
    rows = []
    for s in sk:
        day = pd.Timestamp(s["date"])
        d_rr = (s["rr25"] - prev) if prev is not None else np.nan
        prev = s["rr25"]
        after = [x for x in dates if x > day]
        if not after:                       # no next-day in daily (e.g. after 07-01)
            continue
        nd = after[0]
        o, c = float(d.loc[nd, "open"]), float(d.loc[nd, "close"])
        h, l = float(d.loc[nd, "high"]), float(d.loc[nd, "low"])
        prevc = float(d.loc[day, "close"]) if day in d.index else o
        rows.append({"date": s["date"], "rr25": s["rr25"], "rr25_norm": s["rr25_norm"],
                     "d_rr": d_rr, "atm": s["atm_iv"],
                     "ret": (c - o) / o * 100, "range": (h - l) / prevc * 100})
    df = pd.DataFrame(rows)
    print(f"25-DELTA SKEW -> next-day open->close return (QQQ, n={len(df)})")
    print(f"sample {df['date'].min()}..{df['date'].max()}   "
          f"base P(up)={ (df['ret']>0).mean():.0%}  mean ret {df['ret'].mean():+.3f}%\n")

    def terciles(col, label, drop_na=False):
        sub = df.dropna(subset=[col]) if drop_na else df
        sub = sub.copy()
        sub["b"] = pd.qcut(sub[col], 3, labels=["low", "mid", "high"])
        print(f"{label}:")
        for b, g in sub.groupby("b", observed=True):
            print(f"   {b:4s} {col}: mean ret {g['ret'].mean():+.3f}%  P(up) {(g['ret']>0).mean():.0%}  "
                  f"n={len(g)}")
        c = corr(sub[col], sub["ret"])
        print(f"   corr({col}, next-ret) = {c:+.2f}   "
              f"({'contrarian: high->up' if c>0 else 'momentum: high->down'})")
        # split-half correlation stability
        mid = len(sub) // 2
        c1 = corr(sub[col].iloc[:mid], sub["ret"].iloc[:mid])
        c2 = corr(sub[col].iloc[mid:], sub["ret"].iloc[mid:])
        print(f"   split-half corr: {c1:+.2f} / {c2:+.2f}\n")

    terciles("rr25", "LEVEL: RR25 (put-call skew) tercile -> next-day return")
    terciles("d_rr", "CHANGE: d_RR25 (skew steepening) tercile -> next-day return", drop_na=True)

    # secondary: does skew predict RANGE (magnitude), like gamma does?
    r = corr(df["rr25"], df["range"])
    print(f"secondary (magnitude): corr(RR25, next-day range) = {r:+.2f}  "
          f"(high skew -> wider day?)")

    print("\nread: a usable directional edge = monotone tercile dose-response in mean "
          "ret AND |corr|>~0.25 AND both split-halves same sign. Flat terciles / "
          "corr~0 / sign-flip across halves = no directional edge (park it).")


if __name__ == "__main__":
    main()
