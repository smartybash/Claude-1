"""INTRADAY test of 'fade the wall on range days, ride through on trend days'.

For each session D with dealer walls (gex_history) we load the NEXT session's
5-min RTH bars and find the FIRST bar that TAGS each wall (high>=call_wall, or
low<=put_wall). We then classify what happened over the next K bars:
  REJECT  = price came back inside the wall (fade)
  CONTINUE= price held/extended beyond the wall (break)
via react% = signed move of close[tag+K] relative to the wall, oriented so
positive = beyond the wall (continuation), negative = back inside (reject).

Hypothesis: POSITIVE gamma (range) -> REJECT; NEGATIVE gamma (expansion) ->
CONTINUE. We report reject/continue rates per regime and a two-proportion
z-test, for K = 3 / 6 / 12 bars (15/30/60 min).

Data: gex_history.jsonl (walls+net_gex) + data/intraday/qqq_5m_YYYY-MM.csv.
"""

from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BUF = 0.0005   # +/-0.05% dead-zone so tiny wiggles aren't called either way


def load_intraday() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(ROOT / "data" / "intraday" / "qqq_5m_*.csv"))):
        df = pd.read_csv(f)
        frames.append(df)
    all_ = pd.concat(frames, ignore_index=True)
    all_["ts"] = pd.to_datetime(all_["timestamp"])
    all_ = all_.drop_duplicates("ts").sort_values("ts").set_index("ts")
    all_["day"] = all_.index.normalize()
    return all_


def two_prop_z(k1, n1, k2, n2):
    if n1 == 0 or n2 == 0:
        return float("nan")
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (p1 - p2) / se if se else float("nan")


def main():
    intr = load_intraday()
    days = sorted(intr["day"].unique())
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gex = sorted([g for g in gex if g["sym"] == "QQQ"], key=lambda g: g["date"])

    def collect(K, prox):
        """prox = how close counts as a tag (0 = literal touch; 0.0015 = within 0.15%)."""
        events = []
        for g in gex:
            d0 = pd.Timestamp(g["date"]).normalize()
            after = [x for x in days if x > d0]
            if not after:
                continue
            nd = after[0]
            bars = intr[intr["day"] == nd]
            if len(bars) < K + 2:
                continue
            neg = g["net_gex"] < 0
            cw, pw = g["call_wall"], g["put_wall"]
            h, l, c = bars["high"].values, bars["low"].values, bars["close"].values
            ci = next((i for i in range(len(bars)) if h[i] >= cw * (1 - prox)), None)
            if ci is not None and ci + 1 < len(bars):
                j = min(ci + K, len(bars) - 1)
                react = (c[j] - cw) / cw
                if abs(react) >= BUF:
                    events.append((neg, "call", react))
            pi = next((i for i in range(len(bars)) if l[i] <= pw * (1 + prox)), None)
            if pi is not None and pi + 1 < len(bars):
                j = min(pi + K, len(bars) - 1)
                react = (pw - c[j]) / pw
                if abs(react) >= BUF:
                    events.append((neg, "put", react))
        return pd.DataFrame(events, columns=["neg", "wall", "react"])

    for K, prox, plabel in [(3, 0.0, "exact touch"), (6, 0.0, "exact touch"),
                            (12, 0.0, "exact touch"), (6, 0.0015, "within 0.15%")]:
        e = collect(K, prox)
        e["continue_"] = e["react"] > 0
        e["reject"] = e["react"] < 0

        print(f"===== K={K} bars ({K*5} min), tag = {plabel} =====")
        print(f"total wall tags: {len(e)}  (call {int((e['wall']=='call').sum())}, "
              f"put {int((e['wall']=='put').sum())})")
        pos, neg = e[~e["neg"]], e[e["neg"]]
        for lab, sub in [("POSITIVE gamma (expect REJECT/fade)", pos),
                         ("NEGATIVE gamma (expect CONTINUE/break)", neg)]:
            if len(sub) == 0:
                print(f"  {lab}: n=0"); continue
            print(f"  {lab}: n={len(sub)}  reject {sub['reject'].mean():.0%}  "
                  f"continue {sub['continue_'].mean():.0%}  "
                  f"mean react {sub['react'].mean()*100:+.2f}%")
        # hypothesis test: pos-gamma reject rate > neg-gamma reject rate
        z = two_prop_z(int(pos["reject"].sum()), len(pos), int(neg["reject"].sum()), len(neg))
        print(f"  two-prop z (POS reject% - NEG reject%): {z:+.2f}  "
              f"(>~1.6 supports 'range fades, trend continues')\n")

    print("read: hypothesis holds if POS-gamma reject% is clearly higher than NEG-gamma "
          "(z>~1.6) and stable across K. If reject% is similar in both regimes, the wall "
          "just acts as S/R regardless of gamma (no regime switch).")


if __name__ == "__main__":
    main()
