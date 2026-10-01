"""Intraday entry at 10:30 ET on the earnings reaction session (rule I1/I2).

    python scripts/post_earnings_intraday.py             # full test
    python scripts/post_earnings_intraday.py --coverage  # data check only, no outcomes

Implements section B of reports/post_earnings_preregistration.md exactly:
gap G from the daily open vs the previous close; first-hour return F and
range position P from Alpha Vantage 5-minute RTH bars (09:30-10:25 bars,
10:30 price = close of the 10:25 bar); CONFIRM / REJECT classification;
outcome from 10:30 to the session close (last bar of the day).

Two details the pre-registration left implicit, fixed here before any
outcome was computed:
- F's open is the first 5-minute bar's open. AV intraday bars are
  dividend-adjusted, so all intraday ratios use intraday prices only.
- The base rate is the share of up moves (10:30 -> close) across every
  reaction session in the intraday sample, applied to each event's
  predicted direction (as in the daily study). 50% is shown alongside.
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
    binom_p_greater, load_earnings, load_series, resolve_reactions,
)

ROOT = Path(__file__).resolve().parent.parent
START, END = "2024-01-01", "2026-09-30"


def load_bars(sym: str, month: str) -> dict[str, list[tuple]] | None:
    """{date: [(hh:mm, open, high, low, close), ...]} in time order."""
    f = ROOT / f"data/intraday/{sym}_{month}.json"
    if not f.exists():
        return None
    rows = json.loads(f.read_text())["result"].strip().split("\n")[1:]
    days: dict[str, list[tuple]] = {}
    for row in rows:
        ts, o, h, l, c, _ = row.strip().split(",")
        days.setdefault(ts[:10], []).append((ts[11:16], float(o), float(h), float(l), float(c)))
    for v in days.values():
        v.sort()
    return days


def reaction_events():
    """Every reaction session in the intraday window, with the stock's
    typical move (mean |reaction| of the previous 8 reports)."""
    spy = load_series(ROOT / "data/daily/SPY.json", "SPY")
    out = []
    for folder in ("data/earnings", "data/earnings_holdout"):
        for f in sorted(glob.glob(str(ROOT / folder / "*.json"))):
            sym = os.path.basename(f)[:-5]
            s = load_series(ROOT / f"data/daily/{sym}.json", sym)
            res = [x for x in resolve_reactions(s, spy, load_earnings(f))
                   if x.r is not None and x.r >= 65]
            rs = sorted({x.r for x in res})
            for k, r in enumerate(rs):
                if k < 4 or not START <= s.dates[r] <= END:
                    continue
                prior = rs[max(0, k - 8):k]
                typical = statistics.mean(abs(s.close[p] / s.close[p - 1] - 1) for p in prior)
                out.append((sym, s, r, typical))
    return out


def measure(sym, s, r, typical):
    day = s.dates[r]
    bars = load_bars(sym, day[:7])
    if bars is None:
        return {"sym": sym, "date": day, "missing": "month file"}
    b = bars.get(day)
    times = [x[0] for x in b] if b else []
    if not b or times[0] != "09:30" or "10:25" not in times:
        return {"sym": sym, "date": day, "missing": "session bars"}
    first = [x for x in b if x[0] <= "10:25"]
    p_open, p1030 = b[0][1], first[-1][4]
    hi, lo = max(x[2] for x in first), min(x[3] for x in first)
    c, o = s.close, s.open
    ev = {
        "sym": sym, "date": day, "typical": typical,
        "G": o[r] / c[r - 1] - 1,
        "F": p1030 / p_open - 1,
        "P": (p1030 - lo) / (hi - lo) if hi > lo else 0.5,
        "to_close": b[-1][4] / p1030 - 1,
    }
    for k, key in ((1, "to_next"), (5, "to_p5")):
        if r + k < len(c):
            # exit-at-last-bar chained with daily closes (info only)
            ev[key] = (1 + ev["to_close"]) * c[r + k] / c[r] - 1
    ev["qualifies"] = abs(ev["G"]) >= 0.5 * typical
    ev["state"] = classify(ev["G"], ev["F"], ev["P"], typical)
    return ev


def classify(g: float, f: float, p: float, typical: float) -> str:
    """Pre-registered 10:30 read: '-' (gap too small), CONFIRM, REJECT or MIXED."""
    if g == 0 or abs(g) < 0.5 * typical:
        return "-"
    up = g > 0
    if f != 0 and (f > 0) == up and (p >= 0.70 if up else p <= 0.30):
        return "CONFIRM"
    if f != 0 and (f > 0) != up and (p <= 0.30 if up else p >= 0.70):
        return "REJECT"
    return "MIXED"


def test(evs, sign, outcome, up_rate):
    """sign(ev) -> +1/-1 predicted direction; outcome key; base rate."""
    act = [(sign(e), e[outcome], e["typical"]) for e in evs if outcome in e and e[outcome] != 0]
    if not act:
        return None
    n = len(act)
    hits = sum(1 for d, o, _ in act if (o > 0) == (d > 0))
    naive = statistics.mean(up_rate if d > 0 else 1 - up_rate for d, _, _ in act)
    signed = [d * o for d, o, _ in act]
    return {"n": n, "hit": hits / n, "naive": naive, "lift": hits / n - naive,
            "p": binom_p_greater(hits, n, naive), "p_vs_50": binom_p_greater(hits, n, 0.5),
            "signed": statistics.mean(signed),
            "signed_typ": statistics.mean(x / t for x, (_, _, t) in zip(signed, act)),
            "median_signed": statistics.median(signed)}


def row(label, r):
    if r is None:
        return f"{label:<36} —"
    return (f"{label:<36} {r['n']:>4} {r['hit']:>6.1%} {r['naive']:>6.1%} {r['lift']:>+6.1%} "
            f"{r['p']:>7.4f} {r['p_vs_50']:>7.4f} {r['signed']:>+8.2%} {r['signed_typ']:>+6.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", action="store_true", help="report data coverage only")
    args = ap.parse_args()

    evs = [measure(*e) for e in reaction_events()]
    missing = [e for e in evs if "missing" in e]
    evs = [e for e in evs if "missing" not in e]
    qual = [e for e in evs if e["qualifies"]]
    print(f"{len(evs) + len(missing)} reaction sessions {START}..{END}; "
          f"{len(evs)} with bars, {len(missing)} missing; {len(qual)} qualify (|G| >= 0.5 x typical)")
    for e in missing:
        print(f"  missing {e['sym']} {e['date']}: {e['missing']}")
    counts = {k: sum(e["state"] == k for e in qual) for k in ("CONFIRM", "REJECT", "MIXED")}
    print("  states:", counts)
    if args.coverage:
        return 0

    up_rate = statistics.mean(e["to_close"] > 0 for e in evs if e["to_close"] != 0)
    gsign = lambda e: 1 if e["G"] > 0 else -1
    conf = [e for e in qual if e["state"] == "CONFIRM"]
    rej = [e for e in qual if e["state"] == "REJECT"]
    print(f"  base rate: {up_rate:.1%} of reaction sessions rose 10:30 -> close")

    hdr = (f"{'':<36} {'n':>4} {'hit':>6} {'base':>6} {'lift':>6} {'p(1s)':>7} {'p vs50':>7} "
           f"{'signed':>8} {'/typ':>6}")
    results = {"base_up_rate": up_rate, "n_sessions": len(evs), "n_qualify": len(qual),
               "states": counts, "missing": [f"{e['sym']} {e['date']}" for e in missing]}
    for name, desc, xs, sign in (
        ("I1", "I1 PRIMARY  CONFIRM -> with the gap", conf, gsign),
        ("I2", "I2  REJECT -> against the gap (fade)", rej, lambda e: -gsign(e)),
        ("ALLQ", "ref  all qualifying, with the gap", qual, gsign),
    ):
        print("\n" + desc)
        print(hdr)
        for outcome, label in (("to_close", "10:30 -> close  (tested)"),
                               ("to_next", "10:30 -> next close  (info)"),
                               ("to_p5", "10:30 -> close +5  (info)")):
            r = test(xs, sign, outcome, up_rate)
            print(row(label, r))
            results[f"{name}_{outcome}"] = r

    i1 = results["I1_to_close"]
    ok = i1 is not None and i1["p"] < 0.05
    print(f"\nPRE-REGISTERED VERDICT: I1 {'CONFIRMED' if ok else 'NOT CONFIRMED'}"
          + (f" (hit {i1['hit']:.1%} vs {i1['naive']:.1%}, n {i1['n']}, p {i1['p']:.4f})" if i1 else ""))
    i2 = results["I2_to_close"]
    if i2:
        print(f"Secondary I2: {'confirmed' if i2['p'] < 0.05 else 'not confirmed'} "
              f"(hit {i2['hit']:.1%} vs {i2['naive']:.1%}, n {i2['n']}, p {i2['p']:.4f})")
    results["events"] = [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in e.items()}
                         for e in sorted(evs, key=lambda e: (e["date"], e["sym"]))]
    (ROOT / "reports/post_earnings_intraday_result.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
