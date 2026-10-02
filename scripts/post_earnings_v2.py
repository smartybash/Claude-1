"""Post-earnings intraday rule V1: the first hour beats the market in the gap's direction.

    python scripts/post_earnings_v2.py              # discovery + validation + 2024-26
    python scripts/post_earnings_v2.py --coverage   # data check only, no outcomes

Implements reports/post_earnings_v2_preregistration.md exactly.

V1 (primary). On the reaction session:
- G = open / previous close - 1, from daily bars. The event qualifies when
  |G| >= 0.5 x typical move (mean |reaction| of the previous 8 reports).
- At 10:30 ET (close of the 10:25 5-minute bar):
  idio = sign(G) x [(stock 10:30 / stock open - 1) - (SPY 10:30 / SPY open - 1)].
  This is the stock's first-hour move beyond the market, in the gap's direction.
- idio > 0: enter in the gap's direction at 10:30, hedged one-for-one
  with SPY, and exit at the last 5-minute bar. Otherwise no trade.

Outcome h = sign(G) x [(stock close / stock 10:30 - 1) - (SPY close / SPY 10:30 - 1)].
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk.earnings_method import (  # noqa: E402
    binom_p_greater, load_earnings, load_series, resolve_reactions,
)

ROOT = Path(__file__).resolve().parent.parent
PERIODS = {"discovery": ("2001-01-01", "2013-01-01"),
           "validation": ("2013-01-01", "2024-01-01"),
           "oos_2024": ("2024-01-01", "2026-10-01")}
COST = 0.0010          # round trip, stock leg + hedge, as a fraction of notional
ENTRY = "10:30"        # first bar starting at or after this time is excluded


def _store(sym: str, cache: dict) -> dict:
    if sym not in cache:
        p = ROOT / f"data/intraday_sessions/{sym}.json"
        cache[sym] = json.loads(p.read_text()) if p.exists() else {}
    return cache[sym]


def session_bars(sym: str, day: str, cache: dict) -> list | None:
    """[[hh:mm, o, h, l, c, v], ...] for one RTH session, or None."""
    b = _store(sym, cache).get(day)
    if b:
        return b
    f = ROOT / f"data/intraday/{sym}_{day[:7]}.json"
    if not f.exists():
        return None
    rows = [r.strip().split(",") for r in json.loads(f.read_text())["result"].strip().split("\n")[1:]]
    out = sorted([r[0][11:16]] + [float(x) for x in r[1:6]] for r in rows if r[0][:10] == day)
    return out or None


def usable(b) -> bool:
    times = [x[0] for x in b] if b else []
    return bool(times) and times[0] == "09:30" and "10:25" in times and times[-1] >= "15:30"


def classify_v1(g: float, typical: float, f: float, mf: float) -> int:
    """+1 long / -1 short / 0 no trade."""
    if g == 0 or abs(g) < 0.5 * typical:
        return 0
    side = 1 if g > 0 else -1
    return side if side * (f - mf) > 0 else 0


def reaction_events(lo: str, hi: str):
    spy = load_series(ROOT / "data/daily/SPY.json", "SPY")
    out = []
    for folder in ("data/earnings", "data/earnings_holdout"):
        for f in sorted(glob.glob(str(ROOT / folder / "*.json"))):
            sym = os.path.basename(f)[:-5]
            s = load_series(ROOT / f"data/daily/{sym}.json", sym)
            rs = sorted({x.r for x in resolve_reactions(s, spy, load_earnings(f))
                         if x.r is not None and x.r >= 65})
            for k, r in enumerate(rs):
                if k < 4 or not lo <= s.dates[r] < hi:
                    continue
                prior = rs[max(0, k - 8):k]
                typical = statistics.mean(abs(s.close[p] / s.close[p - 1] - 1) for p in prior)
                out.append((sym, s, r, typical))
    return out


def measure(sym, s, r, typical, cache):
    day = s.dates[r]
    b, m = session_bars(sym, day, cache), session_bars("SPY", day, cache)
    if not usable(b) or not usable(m):
        return {"sym": sym, "date": day, "missing": "stock" if not usable(b) else "SPY"}
    fb = [x for x in b if x[0] < ENTRY]
    fm = [x for x in m if x[0] < ENTRY]
    o, p, c = b[0][1], fb[-1][4], b[-1][4]
    mo, mp, mc = m[0][1], fm[-1][4], m[-1][4]
    g = s.open[r] / s.close[r - 1] - 1
    ev = {"sym": sym, "date": day, "typical": typical, "G": g,
          "F": p / o - 1, "mF": mp / mo - 1,
          "stock": c / p - 1, "spy": mc / mp - 1}
    ev["side"] = classify_v1(g, typical, ev["F"], ev["mF"])
    gs = 1 if g > 0 else -1
    ev["idio_typ"] = gs * (ev["F"] - ev["mF"]) / typical
    ev["h"] = gs * (ev["stock"] - ev["spy"])          # hedged, in the gap's direction
    ev["raw"] = gs * ev["stock"]
    if r + 1 < len(s.open):
        ev["overnight"] = s.open[r + 1] / s.close[r] - 1
    return ev


def summarise(xs: list[float]) -> dict | None:
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    n = len(xs)
    wins = sum(1 for x in xs if x > 0)
    m = statistics.mean(xs)
    sd = statistics.pstdev(xs)
    return {"n": n, "hit": wins / n, "p": binom_p_greater(wins, n, 0.5),
            "mean": m, "net": m - COST, "median": statistics.median(xs),
            "t": m / (sd / math.sqrt(n)) if sd else 0.0}


def row(label, r):
    if r is None:
        return f"  {label:<44} —"
    return (f"  {label:<44} n {r['n']:>4}  hit {r['hit']:>5.1%}  p {r['p']:.4f}  "
            f"mean {r['mean']:+.2%}  net {r['net']:+.2%}  t {r['t']:+.2f}")


def run_period(name, lo, hi, cache, coverage_only=False):
    evs = [measure(*e, cache) for e in reaction_events(lo, hi)]
    missing = [e for e in evs if "missing" in e]
    evs = [e for e in evs if "missing" not in e]
    trades = [e for e in evs if e["side"] != 0]
    print(f"\n== {name} {lo}..{hi}: {len(evs) + len(missing)} reaction sessions, "
          f"{len(evs)} with stock+SPY bars, {len(missing)} missing; {len(trades)} V1 trades")
    if coverage_only:
        return {"n_sessions": len(evs) + len(missing), "n_missing": len(missing), "n_trades": len(trades)}
    res = {
        "V1": summarise([e["h"] for e in trades]),
        "V2_unhedged": summarise([e["raw"] for e in trades]),
        "V3_overnight_fade": summarise([-(1 if e["G"] > 0 else -1) * e["overnight"]
                                        for e in trades if "overnight" in e]),
        "V4_strong": summarise([e["h"] for e in trades if e["idio_typ"] > 0.1]),
        "ref_no_trade_with_gap": summarise([e["h"] for e in evs
                                            if abs(e["G"]) >= 0.5 * e["typical"] and e["side"] == 0]),
    }
    labels = {"V1": "V1 PRIMARY hedged, 10:30 -> close",
              "V2_unhedged": "V2 same trades, unhedged",
              "V3_overnight_fade": "V3 fade close -> next open",
              "V4_strong": "V4 idio > 0.1 x typical",
              "ref_no_trade_with_gap": "ref qualifying, idio <= 0, with gap"}
    for k, v in res.items():
        print(row(labels[k], v))
    res["n_sessions"] = len(evs) + len(missing)
    res["n_missing"] = len(missing)
    res["events"] = [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in e.items()}
                     for e in sorted(evs, key=lambda e: (e["date"], e["sym"]))]
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--period", choices=list(PERIODS), action="append")
    args = ap.parse_args()
    cache: dict = {}
    out = {}
    for name in args.period or list(PERIODS):
        out[name] = run_period(name, *PERIODS[name], cache, args.coverage)
    if args.coverage:
        return 0
    v = out.get("validation", {}).get("V1")
    if v:
        ok = v["p"] < 0.05 and v["net"] > 0
        print(f"\nPRE-REGISTERED VERDICT (validation 2013-2023): V1 {'CONFIRMED' if ok else 'NOT CONFIRMED'} "
              f"(hit {v['hit']:.1%}, n {v['n']}, p {v['p']:.4f}, net {v['net']:+.2%})")
    if not args.period:
        (ROOT / "reports/post_earnings_v2_result.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
