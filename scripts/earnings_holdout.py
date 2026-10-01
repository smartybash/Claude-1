"""Evaluate the FROZEN earnings model on holdout stocks, as pre-registered.

    python scripts/earnings_holdout.py

Reads reports/earnings_model_v1_frozen.json and the hypotheses in
reports/earnings_preregistration.md, and scores every usable report in
data/earnings_holdout/ — stocks that played no part in training or model
selection. Nothing in the model is refit. One-sided exact binomial tests
against the holdout's own base rate.
"""

from __future__ import annotations

import glob
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk.earnings_method import (  # noqa: E402
    binom_p_greater, build_events, load_earnings, load_series, resolve_reactions,
)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    model = json.loads((root / "reports/earnings_model_v1_frozen.json").read_text())
    signs, selected = model["signs"], model["selected"]
    spy = load_series(root / "data/daily/SPY.json", "SPY")

    events = []
    print(f"Frozen model: drivers {selected}, signs {[signs[d] for d in selected]}")
    for f in sorted(glob.glob(str(root / "data/earnings_holdout/*.json"))):
        sym = os.path.basename(f)[:-5]
        s = load_series(root / f"data/daily/{sym}.json", sym)
        res = [x for x in resolve_reactions(s, spy, load_earnings(f)) if x.r is not None and x.r >= 65]
        seen, keep = set(), []
        for x in res:
            if x.r not in seen:
                seen.add(x.r)
                keep.append(x)
        evs = build_events(s, spy, [x.r for x in keep], [x.surprise for x in keep])
        events += evs
        print(f"  {sym:5s} reports {len(keep):3d} -> events {len(evs):3d}  splits {s.splits}")

    up = statistics.mean(e.ret > 0 for e in events)
    print(f"\nHoldout: {len(events)} events, base rate UP {up:.1%}, "
          f"mean |reaction| {statistics.mean(abs(e.ret) for e in events):.2%}")

    def test(label, keep):
        sel = []
        for e in events:
            c = sum(signs[d] * e.drv[d] for d in selected)
            if keep(c):
                sel.append((c, e))
        n = len(sel)
        if n == 0:
            print(f"{label}: no events")
            return None
        hits = sum(1 for c, e in sel if (c > 0) == (e.ret > 0))
        naive = statistics.mean(up if c > 0 else 1 - up for c, _ in sel)
        p = binom_p_greater(hits, n, naive)
        signed = statistics.mean((1 if c > 0 else -1) * e.ret for c, e in sel)
        norm = statistics.mean(abs(e.ret) / e.typical for _, e in sel if e.typical > 0)
        print(f"{label}: n {n}, hit {hits / n:.1%} vs naive {naive:.1%} "
              f"(lift {hits / n - naive:+.1%}), one-sided p {p:.4f}, "
              f"mean signed move {signed:+.2%}, |move|/typical {norm:.2f}")
        return {"n": n, "hit": hits / n, "naive": naive, "p": p,
                "mean_signed_move": signed, "abs_over_typical": norm}

    print()
    h1 = test("H1 (primary)   |score| = 2", lambda c: abs(c) == 2)
    h2 = test("H2 (secondary) |score| >= 1", lambda c: abs(c) >= 1)
    test("   (info) score = +2 only", lambda c: c == 2)
    test("   (info) score = -2 only", lambda c: c == -2)
    for d in selected:
        sel = [(signs[d] * e.drv[d], e) for e in events if e.drv[d] != 0]
        hits = sum(1 for c, e in sel if (c > 0) == (e.ret > 0))
        naive = statistics.mean(up if c > 0 else 1 - up for c, _ in sel)
        print(f"   (info) {d:15s} alone: n {len(sel)}, hit {hits / len(sel):.1%} vs naive "
              f"{naive:.1%}, one-sided p {binom_p_greater(hits, len(sel), naive):.4f}")

    ok = h1 is not None and h1["p"] < 0.05
    print(f"\nPRE-REGISTERED VERDICT: H1 {'CONFIRMED' if ok else 'NOT CONFIRMED'} at alpha 0.05")
    (root / "reports/earnings_holdout_result.json").write_text(
        json.dumps({"H1": h1, "H2": h2, "confirmed": ok, "n_events": len(events),
                    "base_up": up}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
