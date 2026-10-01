"""Pre-announcement card: should we take a directional earnings position?

    python scripts/earnings_card.py MU --decision 2026-09-30
    python scripts/earnings_card.py NKE --decision 2026-10-01

Computes every driver from data up to the DECISION close only, scores the
composite with the frozen model, and applies the gates:

  G1  DIRECTION  the composite must come from drivers that were confirmed
                 on holdout stocks (reports/earnings_holdout_result.json).
                 If not, no directional position on direction grounds.
  G2  STRENGTH   |score| must reach the pre-registered alignment level.
  G3  PRICING    the option structure must have positive expected value
                 under the stock's own event history, robust to removing
                 its best event — checked with scripts/event_10x.py on the
                 live chain (not repeated here).
  G4  REGIME     Vol Desk market gate reading at the decision close.

If the reaction has already happened (looking back at a past event) the
actual outcome is printed for comparison.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk.earnings_method import (  # noqa: E402
    DRIVERS, drivers, load_earnings, load_series, resolve_reactions,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--decision", required=True, help="decision close (YYYY-MM-DD)")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    sym = args.symbol.upper()

    model = json.loads((root / "reports/earnings_model_v1_frozen.json").read_text())
    holdout = json.loads((root / "reports/earnings_holdout_result.json").read_text())
    signs, selected = model["signs"], model["selected"]

    spy = load_series(root / "data/daily/SPY.json", "SPY")
    s = load_series(root / f"data/daily/{sym}.json", sym)
    ef = next((p for p in (root / f"data/earnings/{sym}.json",
                           root / f"data/earnings_holdout/{sym}.json") if p.exists()), None)
    if ef is None:
        print(f"No earnings history for {sym}")
        return 1
    if args.decision not in s.idx:
        print(f"{args.decision} is not a trading session for {sym}")
        return 1
    d = s.idx[args.decision]
    res = [x for x in resolve_reactions(s, spy, load_earnings(ef))
           if x.r is not None and x.r <= d]
    prior = [x.r for x in res][-8:]
    surprises = [x.surprise for x in res][-8:]
    drv = drivers(s, spy, d, prior, surprises)
    if drv is None:
        print("Not enough history to compute drivers")
        return 1
    typical = statistics.mean(abs(s.close[p] / s.close[p - 1] - 1) for p in prior)

    print("=" * 78)
    print(f"PRE-ANNOUNCEMENT CARD — {sym}, decision close {args.decision} "
          f"({s.close[d]:.2f})")
    print("=" * 78)
    print(f"{'driver':>15}  reading  {'model':>11}  status")
    for name in DRIVERS:
        v = drv[name]
        arrow = {1: "  UP ", -1: " DOWN", 0: "  —  "}[v]
        tag = ("in composite" if name in selected else "no edge found")
        eff = signs[name] * v if name in selected else 0
        imp = {1: "-> UP", -1: "-> DOWN", 0: ""}[eff]
        print(f"{name:>15}  {arrow}   {('contrarian' if signs[name] < 0 else 'momentum'):>11}  "
              f"{tag} {imp}")
    score = sum(signs[n] * drv[n] for n in selected)
    print(f"\nComposite score {score:+d} (validated drivers only; range "
          f"{-len(selected)}..+{len(selected)})")
    print(f"Typical earnings move for {sym} (last {len(prior)} reports): +/-{typical:.1%}")

    print("\nGATES")
    g1 = holdout.get("confirmed", False)
    h1 = holdout["H1"]
    print(f"  G1 direction drivers validated on holdout: {'PASS' if g1 else 'FAIL'} "
          f"(H1 hit {h1['hit']:.1%} vs {h1['naive']:.1%} chance, n {h1['n']}, p {h1['p']:.2f})")
    g2 = abs(score) >= len(selected)
    print(f"  G2 full alignment (|score| = {len(selected)}): {'PASS' if g2 else 'FAIL'} "
          f"(score {score:+d})")
    print("  G3 pricing: run scripts/event_10x.py on the live chain "
          "(positive EV robust to best event)")
    j = spy.idx.get(args.decision)
    spy_chg = spy.close[j] / spy.close[j - 1] - 1
    print(f"  G4 regime: SPY {spy_chg:+.2%} on the session (Vol Desk basket gate needs > +0.50%), "
          f"regime driver {drv['regime']:+d}")

    if g1 and g2:
        direction = "UP" if score > 0 else "DOWN"
        print(f"\nVERDICT: directional lean {direction} — proceed to G3 pricing check.")
    else:
        print("\nVERDICT: NO DIRECTIONAL POSITION. "
              + ("No driver has survived the holdout test, so the method cannot "
                 "pick a direction. " if not g1 else "")
              + ("The validated drivers don't fully align. " if g1 and not g2 else "")
              + "Any trade here would be a bet on the size of the move, judged on "
                "pricing alone (G3).")
        if score != 0:
            lean = "UP" if score > 0 else "DOWN"
            print(f"  (Unvalidated lean, for the record only: {lean}.)")

    # outcome, when the reaction is already in the data
    r = d + 1
    if r < len(s.dates):
        ret = s.close[r] / s.close[d] - 1
        print(f"\nOUTCOME ({s.dates[r]}): {ret:+.2%} ({ret / typical:+.2f}x the typical move)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
