"""'Fade the wall on range days, ride it through on trend days.' — honest test.

Hypothesis (the user's simplest idea): when price reaches a dealer wall,
  POSITIVE gamma (range/dampen day)  -> it FADES  (rejects, closes back inside)
  NEGATIVE gamma (expansion/trend day)-> it CONTINUES (accepts, closes beyond)

Data we already have (no fetches): gex_history.jsonl (call/put wall + net_gex as
of session D close -> governs D+1) + QQQ daily OHLC for D+1. This is a DAILY
proxy: a "touch" = the next day's High reached the call wall (or Low reached the
put wall); "fade" = it closed back inside the wall, "continue" = it closed
beyond. Intraday touch-and-go is the real test (needs intraday bars) — this is
the coarse first look.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TOL = 0.001   # "reached the wall" = within 0.1% of it (or beyond)


def qqq_daily():
    r = json.loads((ROOT / "data" / "qqq_daily_5y.json").read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime([t[:10] for t in r["time"]]))
    return df[~df.index.duplicated(keep="last")].sort_index()


def main():
    gex = [json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip()]
    gex = [g for g in gex if g["sym"] == "QQQ"]
    d = qqq_daily(); dates = list(d.index)
    ev = []   # one row per wall TOUCH
    for g in gex:
        day = pd.Timestamp(g["date"])
        after = [x for x in dates if x > day]
        if not after:
            continue
        nd = after[0]
        o, h, l, c = (float(d.loc[nd, k]) for k in ("open", "high", "low", "close"))
        neg = g["net_gex"] < 0
        cw, pw = g["call_wall"], g["put_wall"]
        if h >= cw * (1 - TOL):                       # reached the CALL wall
            ev.append({"wall": "call", "neg": neg,
                       "fade": c < cw,                 # closed back below = fade
                       "continue": c >= cw})
        if l <= pw * (1 + TOL):                        # reached the PUT wall
            ev.append({"wall": "put", "neg": neg,
                       "fade": c > pw,                  # closed back above = fade
                       "continue": c <= pw})
    # how CLOSE does each regime even get to the walls? (a touch has to happen first)
    gap_c = {"pos": [], "neg": []}; gap_p = {"pos": [], "neg": []}
    for g in gex:
        day = pd.Timestamp(g["date"]); aft = [x for x in dates if x > day]
        if not aft:
            continue
        nd = aft[0]; h = float(d.loc[nd, "high"]); l = float(d.loc[nd, "low"])
        k = "neg" if g["net_gex"] < 0 else "pos"
        gap_c[k].append((g["call_wall"] - h) / g["call_wall"] * 100)
        gap_p[k].append((l - g["put_wall"]) / g["put_wall"] * 100)
    print("WALL-TOUCH: fade vs continue, split by gamma regime (QQQ, daily proxy)\n")
    print("how far the day gets from each wall (median %, smaller = closer):")
    print(f"   to CALL wall: POS gamma {np.median(gap_c['pos']):.2f}% | NEG gamma {np.median(gap_c['neg']):.2f}%")
    print(f"   to PUT  wall: POS gamma {np.median(gap_p['pos']):.2f}% | NEG gamma {np.median(gap_p['neg']):.2f}%")
    print("   -> range (POS-gamma) days sit FAR from the far wall; expansion (NEG) days "
          "drive INTO the wall they trend toward.\n")

    e = pd.DataFrame(ev)
    ncall = (e["wall"] == "call").sum() if len(e) else 0
    nput = (e["wall"] == "put").sum() if len(e) else 0
    print(f"touch events: {len(e)}  (call-wall {ncall}, put-wall {nput}) "
          f"out of {len(gex)} sessions\n")
    if len(e) == 0:
        print("no wall touches at daily resolution -> price rarely reaches the walls "
              "(consistent with 90%/73% containment). Need intraday bars to test this.")
        return

    for lab, mask in [("POSITIVE gamma (expect FADE)", ~e["neg"]),
                      ("NEGATIVE gamma (expect CONTINUE)", e["neg"])]:
        sub = e[mask]
        if len(sub) == 0:
            print(f"{lab}: no touches\n"); continue
        print(f"{lab}:  n={len(sub)}")
        print(f"   faded (rejected)   : {sub['fade'].mean():.0%}")
        print(f"   continued (accepted): {sub['continue'].mean():.0%}")
        print()

    # the hypothesis wants fade% high in POS gamma and continue% high in NEG gamma
    pos, neg = e[~e["neg"]], e[e["neg"]]
    print("read: hypothesis holds if POS-gamma fade% is high AND NEG-gamma continue% "
          "is high, on a decent n. With few touches this is only suggestive; the honest "
          "test is intraday (does a wall TAG reject or break in each regime).")
    if len(pos) and len(neg):
        print(f"\nsummary: POS-gamma fade {pos['fade'].mean():.0%} (n={len(pos)})  vs  "
              f"NEG-gamma continue {neg['continue'].mean():.0%} (n={len(neg)})")


if __name__ == "__main__":
    main()
