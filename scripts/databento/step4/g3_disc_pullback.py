#!/usr/bin/env python3
"""Step 4, G3 -- B10 mechanised discretionary pullback (disc_pullback.py at
ce84e66, pre-registered b8db9d2) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
disc_pullback.SRC points at the NQ file. Frozen fractions of price (tick, cost,
daily stop) are kept and applied to the adjusted price. The eight variants
(trend T1/T2 x target P1/P2 x floor 0.33/0.50) without the daily stop are the
tested objects, as in the frozen criteria table. Gross points = pts + frozen cost;
risk = risk_bps x px / 1e4; costed at max(frozen, NQ 0.725 pt).
Frozen criteria (section 6), full sample, after NQ costs, all must pass: expR >
0; >= 15 sessions traded; PF >= 1.15; ex-top-1% > 0; positive in >= 4 calendar
years (literal); t > 3 across the sessions that traded (as the frozen stats()
computes it); win rate beats the variant's own realised random-walk rate at
z > 2.73. p for BH: one-sided daily-P&L t, Holm across 8.
Old verdict: 0 of 8, below the random walk.
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def frozen_criteria(day, gross, risk, cost):
    fac = BL.factor().reindex(day).to_numpy()
    c = np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"])
    R = pd.Series((gross.to_numpy() / fac - c) / (risk.to_numpy() / fac))
    d = day.to_numpy()
    w, l = R[R > 0], R[R <= 0]
    per = R.groupby(d).sum()
    M = w.mean() / abs(l.mean()) if len(l) and l.mean() != 0 else np.nan
    rw = 1.0 / (1.0 + M) if np.isfinite(M) and M > 0 else np.nan
    obs = float((R > 0).mean())
    z = (obs - rw) / np.sqrt(rw * (1 - rw) / len(R)) if np.isfinite(rw) and 0 < rw < 1 else np.nan
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else np.inf
    t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 2 else np.nan
    ex1 = R.sum() - R.sort_values(ascending=False).head(int(np.ceil(0.01 * len(R)))).sum()
    yp = int((R.groupby(day.year.to_numpy()).mean() > 0).sum())
    c7 = [R.mean() > 0, per.size >= 15, pf >= 1.15, ex1 > 0, yp >= 4, t > 3, z > 2.73]
    return bool(all(c7)), (f"expR {R.mean():+.3f} PF {pf:.2f} t {t:+.2f} +yrs {yp} "
                           f"win {100*obs:.1f}% vs RW {100*rw:.1f}% z {z:+.2f}")


def main():
    import disc_pullback as DP
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        DP.SRC = src
        if window == "full":
            C.run_frozen("disc_pullback", [("disc_pullback", "SRC", src)], "B10_frozen_output.txt")
        S, rej = DP.sessions()
        print(f"{window}: sessions {len(S)}, rejected {rej}")
        for tr_, tg, fl in product(DP.G_TREND, DP.G_TGT, DP.G_FLOOR):
            k = f"{tr_} {tg} f{fl:.2f}"
            T, _ = DP.evaluate(S, tr_, tg, fl, False)
            px = T.day.map(lambda d: S[d]["px"])
            cost = T.day.map(lambda d: S[d]["cost"])
            risk = T.risk_bps * px / 1e4
            gross = T.pts + cost
            day = pd.to_datetime(T.day.astype(str))
            res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
            if window == "full":
                ok, s = frozen_criteria(pd.DatetimeIndex(day), gross, risk, cost)
                flags[k] = ok
                notes.append(f"{k}: {s}")
    BL.report_bar("B10", "mechanised discretionary pullback (8 variants)", res, list(res), flags,
                  old="0 of 8, below the random walk", note=" | ".join(notes))


if __name__ == "__main__":
    main()
