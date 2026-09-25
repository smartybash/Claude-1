#!/usr/bin/env python3
"""D3P, prop-compatible oversold bounce (reports/d3p_preregistration.md).

Signal = frozen D3 (R7) on session i; long 1 NQ from session i+1's RTH open to
its RTH close; NQ step-4 costs; exposure-matched random-entry null (long,
open -> close of a uniformly random session in the window, same cost).
Seen data, 2010-06-07 -> 2026-09-24. Committed with the registration before
its first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily3 as D3                                                 # noqa: E402
import step4_common as C                                            # noqa: E402

OUT = C.ROOT / "reports"
RT = {"NQ": C.RT_STD_PTS["NQ"], "MNQ": C.RT_STD_PTS["MNQ"]}
MULT = {"NQ": 20.0, "MNQ": 2.0}
HALF = pd.Timestamp("2018-07-01")


def signals(D):
    """Frozen D3 R7 signal sessions (index positions), as in daily3.trades_oversold."""
    c, c58 = D.c.to_numpy(), D.c58.to_numpy()
    return [i for i in range(3, len(D) - 1)
            if c58[i] < c[i - 1] and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3]]


def trades(D, days, sig):
    o, c, fac = D.o.to_numpy(), D.c.to_numpy(), D.fac.to_numpy()
    j = np.array(sig) + 1
    T = pd.DataFrame({"signal_day": days[np.array(sig)], "day": days[j],
                      "entry": o[j], "exit": c[j], "fac": fac[j]})
    T["gross"] = (T.exit - T.entry) / T.fac                           # real NQ points
    # D3's overnight leg on the same signals: 15:59 close of i -> RTH open of i+1
    # (same factor when no roll between them; skipped otherwise)
    fi = fac[np.array(sig)]
    T["overnight_pts"] = np.where(fi == fac[j], (o[j] - c[np.array(sig)]) / fac[j], np.nan)
    for k in ("NQ", "MNQ"):
        T[f"net_usd_{k}"] = (T.gross - RT[k]) * MULT[k]
    return T


def null(D, days, T, lo, hi, rng, n_sim=D3.N_SIM):
    o, c, fac = D.o.to_numpy(), D.c.to_numpy(), D.fac.to_numpy()
    pool = np.flatnonzero((days >= lo) & (days <= hi))
    day_net = ((c[pool] - o[pool]) / fac[pool] - RT["NQ"]) * MULT["NQ"]
    tot = np.array([day_net[rng.integers(0, len(pool), len(T))].sum() for _ in range(n_sim)])
    act = T.net_usd_NQ.sum()
    return act, float((1 + (tot >= act).sum()) / (n_sim + 1)), tot, float(day_net.mean())


def describe(T, days, lo, hi, label):
    ev = C.evaluate(pd.Index(T.day), T.gross.to_numpy(), days[(days >= lo) & (days <= hi)])
    yrs = (hi - lo).days / 365.25
    return (f"  {label:<34} n {len(T):>4} ({len(T) / yrs:.0f}/yr) | ${T.net_usd_NQ.mean():+,.0f}/trade NQ, "
            f"${T.net_usd_MNQ.mean():+,.2f}/trade MNQ | win {100 * (T.net_usd_NQ > 0).mean():.1f}% | "
            f"PF {ev['pf']:.2f} | Sharpe {ev['sharpe']:+.2f} | maxDD ${ev['dd_NQ']:,.0f}/NQ "
            f"${ev['dd_MNQ']:,.0f}/MNQ | worst trade ${T.net_usd_NQ.min():,.0f}/NQ "
            f"${T.net_usd_MNQ.min():,.0f}/MNQ | total ${T.net_usd_NQ.sum():,.0f}"), ev


def main():
    d, D, days, start, end, arr, P = D3.load()
    lo, hi = D3.A0, D3.A1
    sig = signals(D)
    T = trades(D, days, sig)
    T = T[(T.day >= lo) & (T.day <= hi)].reset_index(drop=True)
    rng = np.random.default_rng(D3.SEED)
    act, p, tot, base = null(D, days, T, lo, hi, rng)
    verdict = "PASS -> forward paper-tracking" if (act > 0 and p <= 0.05) else "FAIL -> closed"
    L = ["D3P PROP-COMPATIBLE OVERSOLD BOUNCE -- SEEN DATA, NQ 2010-06-07 -> 2026-09-24",
         "Registered reports/d3p_preregistration.md. Long session i+1 RTH open -> RTH close after a D3 signal.",
         "Costs NQ $2.25 + 1 tick per side. Null: 5,000 random lists, long open -> close of a random session.", ""]
    line, ev = describe(T, days, lo, hi, "D3P [primary]")
    L += [line,
          f"  null: median ${np.median(tot):,.0f}, 95th ${np.percentile(tot, 95):,.0f}; random day "
          f"${base:+,.2f}/trade NQ; actual ${act:,.0f}; p {p:.4f}",
          f"  VERDICT (primary: total > 0 and p <= 0.05): {verdict}", "",
          "DESCRIPTIVE (cannot change the verdict)"]
    for a, b, lab in ((lo, HALF - pd.Timedelta(days=1), "first half 2010-06 -> 2018-06"),
                      (HALF, hi, "second half 2018-07 -> 2026-09")):
        Th = T[(T.day >= a) & (T.day <= b)]
        L.append(describe(Th, days, a, b, lab)[0])
    L.append(f"  MNQ costs (1.12 pt round trip): total ${T.net_usd_MNQ.sum():,.0f} "
             f"(${T.net_usd_MNQ.sum() * 10:,.0f} per 10 MNQ)")
    on = T.overnight_pts.dropna()
    L.append(f"  D3 split on the same signals, gross real points per trade: overnight (15:59 -> next open) "
             f"{on.mean():+.2f} (n {len(on)}), day (open -> close) {T.gross.mean():+.2f}")
    yr = T.groupby(T.day.dt.year).agg(n=("gross", "size"), usd=("net_usd_NQ", "sum"))
    L.append("  by year (n, net $ NQ): " + ", ".join(f"{y} {r.n} {r.usd:+,.0f}" for y, r in yr.iterrows()))
    txt = "\n".join(L)
    print(txt)
    (OUT / "d3p_output.txt").write_text(txt + "\n")
    T.drop(columns=["entry", "exit", "fac"]).to_csv(C.OUT / "frozen" / "d3p_trades.csv", index=False)
    return dict(n=len(T), total=act, p=p, verdict=verdict, sharpe=ev["sharpe"], pf=ev["pf"])


if __name__ == "__main__":
    main()
