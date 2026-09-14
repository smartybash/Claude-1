"""Alternative regime proxy: prior realized volatility (not VIX).

Vol clusters, so a simple, model-free regime call is "was recent range quiet or
wild?" Classify each session by the instrument's OWN 10-day realized vol as of
the PRIOR close (no lookahead), median-split into CALM vs ACTIVE. Then re-run
the exact same test as backtest_gex_proxy.py: the 11:00 trade as MOMENTUM (with
the first-90-min move) vs FADE (against), and see if the winning style flips by
regime and holds up across split-halves.

Scope: pooled QQQ+SPY 1h, ~Nov-2025..Jul-2026; costs modelled; PnL in ATR units.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backtest_trend import build_sessions, simulate


def rv_regime(sym: str) -> dict:
    """(date) -> 'CALM'/'ACTIVE' from 10d realized vol as of prior close."""
    r = json.loads((ROOT / "data" / f"{sym}_daily_5y.json").read_text())
    c = pd.Series(r["close"], index=pd.to_datetime([t[:10] for t in r["time"]]))
    c = c[~c.index.duplicated(keep="last")].sort_index()
    rv = c.pct_change().rolling(10).std().shift(1)     # prior-close value
    thr = rv.median()
    reg = pd.Series(np.where(rv > thr, "ACTIVE", "CALM"), index=rv.index)
    reg[rv.isna()] = "NA"
    reg.index = pd.to_datetime(reg.index.date)
    return {"reg": reg, "thr": float(thr)}


def summarise(p):
    a = np.array(p, dtype=float)
    if len(a) == 0:
        return {"n": 0, "win%": np.nan, "avg": np.nan}
    return {"n": len(a), "win%": round((a > 0).mean(), 3), "avg": round(a.mean(), 4)}


def cell(sessions, regmap, regime, style):
    out = []
    for s in sessions:
        reg = regmap[s["sym"]]["reg"]
        if reg.get(s["date"]) != regime:
            continue
        d = 1 if s["p_dec"] >= s["open"] else -1
        p = simulate(s, d if style == "MOM" else -d, "mkt", "atr")
        if p is not None:
            out.append(p)
    return summarise(out)


def main():
    sessions = build_sessions("qqq") + build_sessions("spy")
    regmap = {"qqq": rv_regime("qqq"), "spy": rv_regime("spy")}

    print("REALIZED-VOL REGIME PROXY (10d RV, prior close, median split) — QQQ+SPY 1h")
    print("same 11:00 trade, MOMENTUM (with first-90m move) vs FADE (against), by regime.\n")
    hdr = f"{'regime':7s} {'style':5s} | {'n':>4} {'win%':>6} {'avg_ATR':>8}"
    print(hdr); print("-" * len(hdr))
    res = {}
    for regime in ("CALM", "ACTIVE"):
        for style in ("MOM", "FADE"):
            st = cell(sessions, regmap, regime, style)
            res[(regime, style)] = st
            print(f"{regime:7s} {style:5s} | {st['n']:>4} {st['win%']!s:>6} {st['avg']!s:>8}")
        print("-" * len(hdr))

    print("\nwinning style per regime:")
    for regime in ("CALM", "ACTIVE"):
        m, f = res[(regime, "MOM")]["avg"], res[(regime, "FADE")]["avg"]
        print(f"  {regime:7s}: MOM {m:+.4f} vs FADE {f:+.4f} -> {'MOM' if m > f else 'FADE'}")
    switch = (res[("CALM", "MOM")]["avg"] > res[("CALM", "FADE")]["avg"]) != \
             (res[("ACTIVE", "MOM")]["avg"] > res[("ACTIVE", "FADE")]["avg"])
    best_c = max(res[("CALM", "MOM")]["avg"], res[("CALM", "FADE")]["avg"])
    best_a = max(res[("ACTIVE", "MOM")]["avg"], res[("ACTIVE", "FADE")]["avg"])
    print("\nfull-sample:", "crossover present" if switch else "no crossover",
          f"(best CALM {best_c:+.4f}, best ACTIVE {best_a:+.4f})")

    # split-half stability of whichever style wins each regime full-sample
    ss = sorted(sessions, key=lambda s: s["date"])
    midd = ss[len(ss) // 2]["date"]
    win = {rg: ("MOM" if res[(rg, "MOM")]["avg"] > res[(rg, "FADE")]["avg"] else "FADE")
           for rg in ("CALM", "ACTIVE")}
    print("\nstability of the full-sample winning cells:")
    for lab, sub in [("first half ", [s for s in ss if s["date"] < midd]),
                     ("second half", [s for s in ss if s["date"] >= midd])]:
        parts = []
        for rg in ("CALM", "ACTIVE"):
            st = cell(sub, regmap, rg, win[rg])
            parts.append(f"{rg}/{win[rg]} {st['avg']!s:>8} (n={st['n']:>3})")
        print(f"  {lab}: " + "   ".join(parts))
    print("\nMERIT only if the crossover holds AND both winning cells stay same-sign "
          "in each half. Otherwise it's noise, same as the VIX proxy.")


if __name__ == "__main__":
    main()
