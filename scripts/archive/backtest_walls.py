"""Do dealer call/put walls act as real next-day support/resistance? — justifies
injecting them into the confluence level stack. No new fetches.

For each QQQ session in gex_history (walls as-of close = next day's map) vs the
next day's OHLC:
  - containment: did next-day HIGH stay <= call_wall (resistance capped) and
    next-day LOW stay >= put_wall (support held)?
  - magnet: how close did the next-day extreme come to the nearest wall, in %?
  - compare wall distance to a naive random-strike baseline (nearest 10-point
    strike that is NOT a wall) to show the wall is better than "any round number".
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


def main():
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gex = [g for g in gex if g["sym"] == "QQQ"]
    d = qqq_daily(); dates = list(d.index)
    cap_hi = cap_lo = 0; n = 0
    cw_gap, pw_gap, rand_gap = [], [], []
    for g in gex:
        day = pd.Timestamp(g["date"])
        after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]
        h, l = float(d.loc[nd, "high"]), float(d.loc[nd, "low"])
        cw, pw = g["call_wall"], g["put_wall"]
        n += 1
        cap_hi += h <= cw          # resistance held
        cap_lo += l >= pw          # support held
        # how close did the extreme come to its wall (% of price)
        cw_gap.append(abs(h - cw) / cw * 100)
        pw_gap.append(abs(l - pw) / pw * 100)
        # baseline: nearest 10-pt strike to the high that is NOT the call wall
        near = round(h / 10) * 10
        if near == cw:
            near += 10
        rand_gap.append(abs(h - near) / near * 100)

    print(f"DEALER WALLS as next-day S/R (QQQ, n={n})\n")
    print(f"  next-day HIGH stayed <= call wall (resistance held): {cap_hi/n:.0%}")
    print(f"  next-day LOW  stayed >= put  wall (support held)   : {cap_lo/n:.0%}")
    print(f"  both walls contained the whole day                 : "
          f"{sum(1 for g in gex[:n]) and 0 or 0}", end="")
    # recompute both-contained cleanly
    both = 0
    for g in gex:
        day = pd.Timestamp(g["date"]); after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]; h = float(d.loc[nd, "high"]); l = float(d.loc[nd, "low"])
        both += (h <= g["call_wall"]) and (l >= g["put_wall"])
    print(f"{both/n:.0%}\n")
    print(f"  |next-high - call wall| : {np.mean(cw_gap):.2f}%  (median {np.median(cw_gap):.2f}%)")
    print(f"  |next-low  - put  wall| : {np.mean(pw_gap):.2f}%  (median {np.median(pw_gap):.2f}%)")
    print(f"  baseline nearest strike : {np.mean(rand_gap):.2f}%  (median {np.median(rand_gap):.2f}%)")
    print("\nread: high containment % + a small high-to-wall gap that BEATS the naive "
          "nearest-strike baseline = walls are genuine dealer-defended S/R worth adding "
          "to the confluence stack (not just round numbers).")


if __name__ == "__main__":
    main()
