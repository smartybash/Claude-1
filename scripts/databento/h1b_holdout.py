#!/usr/bin/env python3
"""H1-B holdout test (reports/h1b_preregistration.md). Committed before it runs; run once.

Frozen: entry 15:45 open -> 15:59 close, direction sign(15:44 close / prior close - 1), only
when |r| >= trailing-250-day 90th percentile. Holdout 2021-01-01 -> 2026-09-24.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3g                                                          # noqa: E402
import h1b_explore as X                                             # noqa: E402
import prop_sim as PS                                               # noqa: E402

ENTRY, MEASURE, Q = "15:45", "abs_r", 90
HOLD0, HOLD1 = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-24")
FULL0 = pd.Timestamp("2010-06-07")
SEED = 20260930


def sim_frame(D, T):
    """Columns prop_sim.build_trades needs (unadjusted prices, one instrument per trade)."""
    E = D.loc[T.session]
    F = T.copy()
    F["t_in"] = F.session + pd.Timedelta(hours=15, minutes=45)
    F["t_out"] = F.session + pd.Timedelta(hours=15, minutes=59)
    F["px_in"] = (E[f"o_{ENTRY}"] / E.fac).to_numpy()
    F["px_out"] = (E.c1559 / E.fac).to_numpy()
    F["id_in"] = E.iid.to_numpy()
    F["rolls"], F["exit_at"] = 0, "close"
    F["roll_old_close"] = F["roll_new_open"] = np.nan
    return F


def main():
    rng = np.random.default_rng(SEED)
    Dn, De = X.day_table("NQ", HOLD1), X.day_table("ES", HOLD1)
    T, pool = X.config_trades(Dn, "NQ", ENTRY, MEASURE, Q, HOLD0, HOLD1)
    p, tot = X.null_p(T, pool, "NQ", rng)
    act = T.net_usd.sum()
    ok = act > 0 and p <= 0.05
    L = ["H1-B HOLDOUT (read once) -- NQ 2021-01-01 -> 2026-09-24",
         f"Frozen: entry {ENTRY}, {MEASURE}, trailing 90th percentile. Registered reports/h1b_preregistration.md.", "",
         d3g.line("H1-B holdout", T, "NQ", HOLD0, HOLD1),
         f"  null median ${np.median(tot):,.0f}, 95th ${np.percentile(tot, 95):,.0f}; actual ${act:,.0f}; p {p:.4f}",
         f"  VERDICT (total > 0 and p <= 0.05): {'PASS -> paper-tracking' if ok else 'FAIL -> H1-B closed'}", "",
         "DESCRIPTIVE (cannot change the verdict)"]
    mv = (T.move * X.SPEC["NQ"]["mult"]).to_numpy()
    flips = np.array([(rng.choice([-1, 1], len(T)) * mv).sum() - X.SPEC["NQ"]["rt"] * len(T) for _ in range(5000)])
    L.append(f"  same-days sign flip (direction only): p {(1 + (flips >= act).sum()) / 5001:.4f}, "
             f"median ${np.median(flips):,.0f}")
    y = T.groupby(T.session.dt.year).net_usd.agg(["size", "sum"])
    L.append("  by year (n, net $): " + ", ".join(f"{k} {int(r['size'])} {r['sum']:+,.0f}" for k, r in y.iterrows()))
    big = y["sum"].idxmax()
    rest = T[T.session.dt.year != big]
    L.append(f"  without its biggest year ({big}): n {len(rest)}, total ${rest.net_usd.sum():,.0f}, "
             f"${rest.net_usd.mean():+.1f}/trade")
    L.append(f"  longs {int((T.side > 0).sum())} ${T[T.side > 0].net_usd.mean():+.1f}/trade, shorts "
             f"{int((T.side < 0).sum())} ${T[T.side < 0].net_usd.mean():+.1f}/trade")
    Te, _ = X.config_trades(De, "ES", ENTRY, MEASURE, Q, HOLD0, HOLD1)
    L.append(d3g.line("ES same rule, holdout", Te, "ES", HOLD0, HOLD1))
    txt = "\n".join(L)
    print(txt)
    (X.OUT / "h1b_holdout_output.txt").write_text(txt + "\n")
    if ok:
        Tf, _ = X.config_trades(Dn, "NQ", ENTRY, MEASURE, Q, FULL0, HOLD1)
        F = sim_frame(Dn, Tf)
        F.to_csv(d3g.FROZEN / "h1b_trades.csv", index=False)
        G = d3g.globex("NQ")
        sess = G.index[(G.index >= FULL0) & (G.index <= HOLD1)]
        R = PS.simulate(PS.build_trades(F, "NQ"), sess, X.SPEC["NQ"]["mmult"])
        for c in ("pass_30d", "pass_90d", "pass_365d", "fail_365d"):
            R[c] = (100 * R[c]).map("{:.1f}%".format)
        st = "\n".join(["PROP SIMULATOR, H1-B full window 2010-06 -> 2026-09 (seen + holdout; descriptive)",
                        f"== H1-B: {len(F)} trades, MNQ sizes 1-10 ==", R.to_string(index=False)])
        print(st)
        (X.OUT / "h1b_prop_sim_output.txt").write_text(st + "\n")
    return ok


if __name__ == "__main__":
    main()
