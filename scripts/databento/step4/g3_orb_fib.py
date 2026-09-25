#!/usr/bin/env python3
"""Step 4, G3 -- B16 ORB + Fibonacci, continuation and reversal (orb_fib.py at
476be02, pre-registered 5612140 with amendments 1-2) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
orb_fib.SRC -> NQ file. BUFFER is written in QQQ dollars ("one cent on QQQ") and
is converted by x41 per step-4 section 4: 0.41 NQ points. The cost fraction of
price is kept inside the rule; trades are re-costed at max(frozen, NQ 0.725 pt).
Eight variants: {continuation, reversal} x ORB {15, 30} x band {A, B}, amended
(non-literal) outburst rule, one managed scale-out trade per setup (targets are
not a variant axis, as frozen). Gross points = R x risk + cost.
Rejection rules (section 9 with amendment 2), full sample, after NQ costs, all
must hold: expR > 0; PF > 1.15; positive in >= 4 calendar years (literal);
positive after removing max(10, ceil(0.10 n)) best trades; positive at +50% cost;
win rate above the random-walk rate 1/(1+M) at the realised reward-to-risk.
p for BH: one-sided daily-P&L t, Holm across 8.
Old verdict: reversal unresolvable, continuation not demonstrated; family closed
(also on related instruments).
"""
from __future__ import annotations

import sys
from itertools import product
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def crit(day, gross, risk, cost):
    fac = BL.factor().reindex(day).to_numpy()
    base = np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"])
    R = (gross.to_numpy() / fac - base) / (risk.to_numpy() / fac)
    R50 = (gross.to_numpy() / fac - 1.5 * base) / (risk.to_numpy() / fac)
    w, l = R[R > 0], R[R <= 0]
    pf = w.sum() / -l.sum() if len(l) and l.sum() < 0 else np.inf
    yp = int((pd.Series(R).groupby(day.year.to_numpy()).mean() > 0).sum())
    k = max(10, int(ceil(0.10 * len(R))))
    conc = np.sort(R)[:len(R) - k].sum() if k < len(R) else -np.inf
    M = w.mean() / abs(l.mean()) if len(l) and l.mean() != 0 else np.nan
    rw = 1 / (1 + M) if np.isfinite(M) and M > 0 else np.nan
    win = (R > 0).mean()
    ok = bool(len(R) and R.mean() > 0 and pf > 1.15 and yp >= 4 and conc > 0
              and R50.mean() > 0 and win > rw)
    return ok, (f"n {len(R)} expR {R.mean():+.3f} PF {pf:.2f} +yrs {yp} conc {conc:+.1f} "
                f"+50%c {R50.mean():+.3f} win {100*win:.1f}% vs RW {100*rw:.1f}%")


def main():
    import orb_fib as OF
    OF.BUFFER = 0.01 * 41.0
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        OF.SRC = src
        sessions = OF.load()
        print(f"{window}: sessions {len(sessions)}")
        for om, band in product(OF.ORB_MINS, OF.BANDS):
            Cn, Rv, _ = OF.run(sessions, om, band, literal=False)
            for lab, T in (("continuation", Cn), ("reversal", Rv)):
                k = f"{lab} ORB{om} band {band}"
                if T.empty:
                    res.setdefault(k, {})[window] = C.evaluate([], [], BL.sessions_in(window))
                    flags.setdefault(k, False)
                    continue
                cost = T.cost_pct / 100.0 * T.risk
                gross = T.R * T.risk + cost
                day = pd.to_datetime(T.day.astype(str))
                res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
                if window == "full":
                    ok, s = crit(pd.DatetimeIndex(day), gross, T.risk, cost)
                    flags[k] = ok
                    notes.append(f"{k}: {s}")
    BL.report_bar("B16", "ORB + Fibonacci (8 variants)", res, list(res), flags,
                  old="reversal unresolvable; continuation not demonstrated; closed",
                  note=" | ".join(notes))


if __name__ == "__main__":
    main()
