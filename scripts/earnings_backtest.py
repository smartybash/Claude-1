"""Which pre-announcement drivers actually predict the earnings reaction?

    python scripts/earnings_backtest.py [--train-end 2017-01-01]

For every confirmed earnings report in data/earnings/ (dates from Alpha
Vantage, reaction session pinned by volume — see
vol_desk/earnings_method.resolve_reactions), computes the ten drivers at
the decision close and the reaction-session return.

Discipline:
  * Each driver's DIRECTION (momentum or contrarian) is learned on the
    training years only.
  * Its skill is then measured on the test years it never saw, against the
    test period's own base rate (so a bull market can't make "bullish"
    drivers look skilful) with an exact binomial p-value.
  * Drivers enter the composite only if they were significant in TRAINING
    (p < 0.10). The alignment threshold k is also chosen on training data.
    Nothing about the test years feeds back into the model.

Writes reports/earnings_model.json, which scripts/earnings_card.py uses to
score a live event.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk.earnings_method import (  # noqa: E402
    DRIVERS, binom_p, build_events, load_earnings, load_series, resolve_reactions,
)

MIN_HIT, MIN_N, MAX_P = 0.56, 60, 0.05   # alignment-gate criteria (applied on TRAIN)
SELECT_P = 0.10                           # driver admission (applied on TRAIN)


def load_all(root: Path):
    spy = load_series(root / "data/daily/SPY.json", "SPY")
    events, audit = [], {}
    for f in sorted(glob.glob(str(root / "data/earnings/*.json"))):
        sym = os.path.basename(f)[:-5]
        s = load_series(root / f"data/daily/{sym}.json", sym)
        res = [x for x in resolve_reactions(s, spy, load_earnings(f)) if x.r is not None and x.r >= 65]
        # one reaction per session (guards against duplicate vendor rows)
        seen, keep = set(), []
        for x in res:
            if x.r not in seen:
                seen.add(x.r)
                keep.append(x)
        evs = build_events(s, spy, [x.r for x in keep], [x.surprise for x in keep])
        events += evs
        audit[sym] = {"reports": len(keep), "events": len(evs), "splits": s.splits,
                      "weak_volume": sum(1 for x in keep if x.abn < 1.5),
                      "relabelled": sum(1 for x in keep if x.relabelled)}
    return events, audit


def score_driver(evs, name, sign, base_up):
    """Hit rate of a driver (with a given sign) vs the naive base-rate hit rate."""
    act = [(sign * e.drv[name], e.ret) for e in evs if e.drv[name] != 0]
    if not act:
        return {"n": 0, "hit": None, "naive": None, "lift": None, "p": 1.0}
    hits = sum(1 for d, r in act if (d > 0 and r > 0) or (d < 0 and r < 0))
    naive = statistics.mean(base_up if d > 0 else 1 - base_up for d, _ in act)
    n = len(act)
    return {"n": n, "hit": hits / n, "naive": naive, "lift": hits / n - naive,
            "p": binom_p(hits, n, naive)}


def composite(e, signs, selected):
    return sum(signs[d] * e.drv[d] for d in selected)


def bucket_stats(evs, signs, selected, k, base_up):
    al = [(composite(e, signs, selected), e) for e in evs]
    al = [(c, e) for c, e in al if abs(c) >= k]
    if not al:
        return {"n": 0, "hit": None, "naive": None, "p": 1.0}
    hits = sum(1 for c, e in al if (c > 0) == (e.ret > 0))
    naive = statistics.mean(base_up if c > 0 else 1 - base_up for c, _ in al)
    norm = [abs(e.ret) / e.typical for _, e in al if e.typical > 0]
    return {"n": len(al), "hit": hits / len(al), "naive": naive,
            "p": binom_p(hits, len(al), naive),
            "mean_signed_move": statistics.mean((1 if c > 0 else -1) * e.ret for c, e in al),
            "mean_abs_over_typical": statistics.mean(norm) if norm else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-end", default="2017-01-01")
    ap.add_argument("--out", default="reports/earnings_model.json")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent

    events, audit = load_all(root)
    train = [e for e in events if e.date < args.train_end]
    test = [e for e in events if e.date >= args.train_end]
    up_tr = statistics.mean(e.ret > 0 for e in train)
    up_te = statistics.mean(e.ret > 0 for e in test)

    print("=" * 100)
    print(f"Universe: {len(audit)} stocks, {len(events)} usable events "
          f"(train < {args.train_end}: {len(train)}, test: {len(test)})")
    for sym, a in audit.items():
        print(f"  {sym:5s} reports {a['reports']:3d} -> events {a['events']:3d}  "
              f"weak-volume {a['weak_volume']:2d}  relabelled {a['relabelled']:2d}")
    print(f"Base rate of an UP reaction: train {up_tr:.1%}, test {up_te:.1%}")
    print(f"Mean |reaction|: train {statistics.mean(abs(e.ret) for e in train):.2%}, "
          f"test {statistics.mean(abs(e.ret) for e in test):.2%}")

    print("\nDRIVERS — direction learned on train, skill measured on test vs test base rate")
    hdr = (f"{'driver':>15} {'sign':>11} | {'train n':>7} {'hit':>6} {'lift':>6} {'p':>6} | "
           f"{'test n':>6} {'hit':>6} {'naive':>6} {'lift':>6} {'p':>6}")
    print(hdr)
    print("-" * len(hdr))
    signs, selected, table = {}, [], {}
    for name in DRIVERS:
        raw = score_driver(train, name, 1, up_tr)
        sign = 1 if (raw["lift"] or 0) >= 0 else -1
        tr = score_driver(train, name, sign, up_tr)
        te = score_driver(test, name, sign, up_te)
        signs[name] = sign
        if tr["n"] >= 30 and tr["p"] < SELECT_P:
            selected.append(name)
        table[name] = {"sign": sign, "train": tr, "test": te}
        f = lambda v, fmt: format(v, fmt) if v is not None else "  —"
        print(f"{name:>15} {'momentum' if sign > 0 else 'contrarian':>11} | {tr['n']:>7} "
              f"{f(tr['hit'], '.1%'):>6} {f(tr['lift'], '+.1%'):>6} {tr['p']:>6.3f} | {te['n']:>6} "
              f"{f(te['hit'], '.1%'):>6} {f(te['naive'], '.1%'):>6} {f(te['lift'], '+.1%'):>6} "
              f"{te['p']:>6.3f}{'  *selected (train)' if name in selected else ''}")

    print(f"\nSelected on train (p < {SELECT_P}): {selected or 'NONE'}")
    model = {"train_end": args.train_end, "signs": signs, "selected": selected,
             "base_up": {"train": up_tr, "test": up_te}, "drivers": table, "k": None,
             "gate": {"min_hit": MIN_HIT, "min_n": MIN_N, "max_p": MAX_P}}

    if selected:
        print("\nCOMPOSITE of selected drivers — by alignment strength")
        print(f"{'|score|>=':>9} | {'train n':>7} {'hit':>6} {'naive':>6} {'p':>6} | "
              f"{'test n':>6} {'hit':>6} {'naive':>6} {'p':>6} {'signed mv':>9} {'|mv|/typ':>8}")
        k_star = None
        for k in range(1, len(selected) + 1):
            tr = bucket_stats(train, signs, selected, k, up_tr)
            te = bucket_stats(test, signs, selected, k, up_te)
            if tr["n"] == 0:
                break
            ok = tr["hit"] >= MIN_HIT and tr["n"] >= MIN_N and tr["p"] < MAX_P
            if ok and k_star is None:
                k_star = k
            fm = lambda d, key, fmt: format(d[key], fmt) if d.get(key) is not None else "—"
            print(f"{k:>9} | {tr['n']:>7} {fm(tr, 'hit', '.1%'):>6} {fm(tr, 'naive', '.1%'):>6} "
                  f"{tr['p']:>6.3f} | {te['n']:>6} {fm(te, 'hit', '.1%'):>6} {fm(te, 'naive', '.1%'):>6} "
                  f"{te['p']:>6.3f} {fm(te, 'mean_signed_move', '+.2%'):>9} "
                  f"{fm(te, 'mean_abs_over_typical', '.2f'):>8}{'  <- k chosen on train' if ok and k == k_star else ''}")
        model["k"] = k_star
        if k_star:
            te = bucket_stats(test, signs, selected, k_star, up_te)
            model["gate_test"] = te
            verdict = te["hit"] is not None and te["hit"] >= MIN_HIT and te["p"] < MAX_P
            print(f"\nGate k={k_star} (chosen on train) on TEST: n {te['n']}, hit {te['hit']:.1%} "
                  f"vs naive {te['naive']:.1%}, p {te['p']:.3f} -> "
                  f"{'VALIDATED' if verdict else 'NOT VALIDATED out of sample'}")
            model["validated"] = verdict
        else:
            print("\nNo alignment level met the gate on TRAINING data -> nothing to validate.")
            model["validated"] = False
    else:
        model["validated"] = False

    # conditional move distributions, normalised by each stock's typical move
    dist: dict[str, list[float]] = {}
    for e in events:
        c = composite(e, signs, selected) if selected else 0
        key = str(max(-3, min(3, c)))
        dist.setdefault(key, []).append(e.ret / e.typical if e.typical > 0 else 0.0)
    model["normalised_moves_by_score"] = dist
    model["universe"] = audit
    Path(root / args.out).write_text(json.dumps(model, indent=1))
    print(f"\n[model written to {args.out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
