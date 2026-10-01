"""Post-announcement entries on daily data: gap-and-go and post-earnings drift.

    python scripts/post_earnings_daily.py

Tests the daily hypotheses fixed in reports/post_earnings_preregistration.md
on every usable report of the 14-stock universe. Directions are set in
advance (continuation), so the whole sample is a test; results are also
broken out by the earlier train / test / holdout groupings to show whether
an effect is stable.
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
    binom_p_greater, load_earnings, load_series, resolve_reactions,
)

ROOT = Path(__file__).resolve().parent.parent


def load_events():
    spy = load_series(ROOT / "data/daily/SPY.json", "SPY")
    out = []
    for folder, group in (("data/earnings", "train-stocks"), ("data/earnings_holdout", "holdout")):
        for f in sorted(glob.glob(str(ROOT / folder / "*.json"))):
            sym = os.path.basename(f)[:-5]
            s = load_series(ROOT / f"data/daily/{sym}.json", sym)
            res = [x for x in resolve_reactions(s, spy, load_earnings(f))
                   if x.r is not None and x.r >= 65]
            rs = sorted({x.r for x in res})
            for k, r in enumerate(rs):
                if k < 4 or r + 20 >= len(s.close):
                    continue
                prior = rs[max(0, k - 8):k]
                typical = statistics.mean(abs(s.close[p] / s.close[p - 1] - 1) for p in prior)
                c, o = s.close, s.open
                out.append({
                    "sym": sym, "date": s.dates[r], "group": group, "typical": typical,
                    "gap": o[r] / c[r - 1] - 1,
                    "intraday": c[r] / o[r] - 1,
                    "reaction": c[r] / c[r - 1] - 1,
                    "fwd5": c[r + 5] / c[r] - 1,
                    "fwd20": c[r + 20] / c[r] - 1,
                })
    return out


def test(evs, signal, outcome):
    """Continuation test: predicted direction = sign(signal)."""
    act = [(e[signal], e[outcome], e["typical"]) for e in evs if e[signal] != 0 and e[outcome] != 0]
    if not act:
        return None
    up = statistics.mean(o > 0 for _, o, _ in act)
    hits = sum(1 for s, o, _ in act if (s > 0) == (o > 0))
    naive = statistics.mean(up if s > 0 else 1 - up for s, _, _ in act)
    n = len(act)
    signed = [(1 if s > 0 else -1) * o for s, o, _ in act]
    return {"n": n, "hit": hits / n, "naive": naive, "lift": hits / n - naive,
            "p": binom_p_greater(hits, n, naive), "signed": statistics.mean(signed),
            "signed_typ": statistics.mean(x / t for x, (_, _, t) in zip(signed, act) if t > 0)}


def row(label, r):
    if r is None:
        return f"{label:<44} —"
    return (f"{label:<44} {r['n']:>5} {r['hit']:>6.1%} {r['naive']:>6.1%} {r['lift']:>+6.1%} "
            f"{r['p']:>7.4f} {r['signed']:>+8.2%} {r['signed_typ']:>+7.2f}")


def main() -> int:
    evs = load_events()
    groups = {
        "ALL": evs,
        "  train stocks < 2017": [e for e in evs if e["group"] == "train-stocks" and e["date"] < "2017-01-01"],
        "  train stocks 2017+": [e for e in evs if e["group"] == "train-stocks" and e["date"] >= "2017-01-01"],
        "  holdout stocks": [e for e in evs if e["group"] == "holdout"],
    }
    big = lambda xs, key: [e for e in xs if abs(e[key]) >= e["typical"]]
    print(f"{len(evs)} events, 14 stocks. Continuation predicted in every test.")
    hdr = (f"{'':<44} {'n':>5} {'hit':>6} {'naive':>6} {'lift':>6} {'p(1s)':>7} "
           f"{'signed':>8} {'/typ':>7}")
    results = {}
    for name, signal, outcome, desc in (
        ("D2", "reaction", "fwd5", "D2 PRIMARY  reaction close -> +5 sessions"),
        ("D1", "gap", "intraday", "D1  gap -> open-to-close same session"),
        ("D3", "reaction", "fwd20", "D3  reaction close -> +20 sessions"),
    ):
        print("\n" + desc)
        print(hdr)
        for g, xs in groups.items():
            r = test(xs, signal, outcome)
            print(row(g, r))
            if g == "ALL":
                results[name] = r
        rb = test(big(evs, signal), signal, outcome)
        print(row("  large reactions only (|move| >= typical)", rb))
        results[name + "_large"] = rb

    d2 = results["D2"]
    verdict = d2 is not None and d2["p"] < 0.05
    print(f"\nPRE-REGISTERED VERDICT: D2 {'CONFIRMED' if verdict else 'NOT CONFIRMED'} "
          f"(hit {d2['hit']:.1%} vs {d2['naive']:.1%}, p {d2['p']:.4f})")
    (ROOT / "reports/post_earnings_daily_result.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
