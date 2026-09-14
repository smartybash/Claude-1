"""Do mega-cap earnings nights widen the next QQQ session? — simple, honest test.

Hypothesis (well-known, but verify on OUR data): the day the market reacts to a
big-tech earnings report, QQQ's range expands. If real, it's a FORWARD-KNOWN
range amplifier (the calendar is published weeks ahead) that stacks with the
gamma-scaled EM as a second band multiplier.

Report dates (reportedDate + reportTime) are from Alpha Vantage EARNINGS for the
three heaviest QQQ movers: AAPL, MSFT, NVDA. Reaction session =
  post-market report -> the NEXT trading day (the gap+drift day)
  pre-market  report -> the SAME reportedDate (it trades that morning)
Metric: QQQ range % = (High-Low)/prevClose. Compare reaction days vs all other
days; Welch t + split-half stability. Scope = whatever overlaps qqq_daily_5y.
Small, 3-name sample -> directional read, not proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# (reportedDate, reportTime) 2020+, from AV EARNINGS. post=after close, pre=before open.
EARNINGS = {
    "AAPL": [("2026-07-30", "post"), ("2026-04-30", "post"), ("2026-01-29", "post"),
             ("2025-10-30", "post"), ("2025-07-31", "post"), ("2025-05-01", "post"),
             ("2025-01-30", "post"), ("2024-10-31", "post"), ("2024-08-01", "post"),
             ("2024-05-02", "post"), ("2024-02-01", "post"), ("2023-11-02", "post"),
             ("2023-08-03", "post"), ("2023-05-04", "post"), ("2023-02-02", "post"),
             ("2022-10-27", "post"), ("2022-07-28", "post"), ("2022-04-28", "post"),
             ("2022-01-27", "post"), ("2021-10-28", "post"), ("2021-07-27", "post"),
             ("2021-04-28", "post"), ("2021-01-27", "post"), ("2020-10-29", "post"),
             ("2020-07-30", "post"), ("2020-04-30", "post"), ("2020-01-28", "post")],
    "MSFT": [("2026-07-29", "post"), ("2026-04-29", "post"), ("2026-01-28", "post"),
             ("2025-10-29", "post"), ("2025-07-30", "post"), ("2025-04-30", "post"),
             ("2025-01-29", "post"), ("2024-10-30", "post"), ("2024-07-30", "post"),
             ("2024-04-25", "post"), ("2024-01-30", "post"), ("2023-10-24", "post"),
             ("2023-07-25", "pre"),  ("2023-04-25", "post"), ("2023-01-24", "post"),
             ("2022-10-25", "post"), ("2022-07-26", "pre"),  ("2022-04-26", "post"),
             ("2022-01-25", "post"), ("2021-10-26", "post"), ("2021-07-27", "pre"),
             ("2021-04-27", "post"), ("2021-01-26", "post"), ("2020-10-27", "post"),
             ("2020-07-22", "post"), ("2020-04-29", "post"), ("2020-01-29", "post")],
    "NVDA": [("2026-05-20", "post"), ("2026-02-25", "post"), ("2025-11-19", "post"),
             ("2025-08-27", "post"), ("2025-05-28", "post"), ("2025-02-26", "post"),
             ("2024-11-20", "post"), ("2024-08-28", "post"), ("2024-05-22", "post"),
             ("2024-02-21", "post"), ("2023-11-21", "post"), ("2023-08-23", "post"),
             ("2023-05-24", "post"), ("2023-02-22", "post"), ("2022-11-16", "post"),
             ("2022-08-24", "post"), ("2022-05-25", "post"), ("2022-02-16", "post"),
             ("2021-11-17", "post"), ("2021-08-18", "post"), ("2021-05-26", "post"),
             ("2021-02-24", "post"), ("2020-11-18", "post"), ("2020-08-19", "post"),
             ("2020-05-21", "post"), ("2020-02-13", "post")],
}


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


def reaction_days(dates) -> set:
    """Map each earnings event to the QQQ session that reacts to it."""
    out = set()
    dl = list(dates)
    for name, evs in EARNINGS.items():
        for d, t in evs:
            ts = pd.Timestamp(d)
            if t == "pre":
                if ts in dates:               # trades that morning
                    out.add(ts)
            else:                              # post -> next trading day
                after = [x for x in dl if x > ts]
                if after:
                    out.add(after[0])
    return out


def main():
    d = qqq_daily()
    d["range"] = (d["high"] - d["low"]) / d["close"].shift(1) * 100
    d = d.dropna(subset=["range"])
    rx = reaction_days(d.index)
    d["earn"] = d.index.isin(rx)
    e, n = d[d["earn"]]["range"], d[~d["earn"]]["range"]

    print("MEGA-CAP EARNINGS NIGHT -> next QQQ session range % (AAPL/MSFT/NVDA)")
    print(f"sample {d.index.min().date()}..{d.index.max().date()}  "
          f"earnings-reaction days n={len(e)}  normal days n={len(n)}\n")
    print(f"  earnings-reaction day range : {e.mean():.3f}%  (median {e.median():.3f})")
    print(f"  normal day range            : {n.mean():.3f}%  (median {n.median():.3f})")
    print(f"  ratio                       : {e.mean()/n.mean():.2f}x   Welch t {welch(e, n):+.2f}")

    # split-half stability
    mid = d.index[len(d)//2]
    print("\n  split-half (earnings ratio vs normal):")
    for lab, part in [("first ", d[d.index < mid]), ("second", d[d.index >= mid])]:
        pe, pn = part[part["earn"]]["range"], part[~part["earn"]]["range"]
        if len(pe) and len(pn):
            print(f"    {lab}: {pe.mean():.3f}% vs {pn.mean():.3f}%  ({pe.mean()/pn.mean():.2f}x, n={len(pe)})")

    print("\nread: ratio >1 with t>~2 and both halves >1 = earnings nights ARE wider -> "
          "worth a forward EM widener. ~1.0x = no usable earnings-range edge.")


if __name__ == "__main__":
    main()
