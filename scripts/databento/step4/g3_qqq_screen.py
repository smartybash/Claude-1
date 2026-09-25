#!/usr/bin/env python3
"""Step 4, G3 -- B06 QQQ broad screen (qqq_screen.py at 8a2c313, pre-registered
697fd55) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
The screen is the pullback rule restated scale-free (break, rejection, stop
floor and cost as fractions of price: 0.5/1/2/2 NQ points at 30,000). On NQ the
fractions are kept exactly as frozen -- they ARE the frozen spec -- and applied to
the (adjusted) session open price. qqq_screen.SRC is pointed at the NQ file; the
session build, run_session, flat 18:30 UTC mapped to ET per session, and the
16-variant grid are unchanged. run_session is called with the frozen cost set to
zero to get gross points; the cost is then applied per trade as
max(frozen fraction x price, NQ 0.725 pt) (MNQ: max(frozen, 1.12)), in real
points after dividing by the session's adjustment factor.
Frozen criteria (section 7), recomputed after NQ costs, full sample: expectancy
> 0 in R; t > 3.0 across sessions (zero-trade sessions count as zero); PF >=
1.15; total R > 0 without the top 1% of trades; positive in >= 4 calendar years
(literal, as frozen; with 17 years this is lenient and the count is reported).
p for BH: one-sided session-clustered p of net points, Holm across 16.
Samples: full 2010-06-07 -> 2026-09-24 (primary), 2021-01-04 -> 2026-08-31.
Old verdict: 0 of 16.
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


def trades(QS, S, om, sa, tg):
    rows = []
    for day, s in S.items():
        for tr in QS.run_session(s["bars"], om, sa, tg, exc=QS.EXC_FIXED, brk=s["brk"],
                                 rej=s["rej"], floor=s["floor"], cost=0.0,
                                 last_entry=s["last_entry"]):
            rows.append(dict(day=pd.Timestamp(day), gross_adj=tr["pnl"], risk_adj=tr["risk"],
                             frozen_cost_adj=s["cost"]))
    return pd.DataFrame(rows)


def criteria(T, window):
    fac = BL.factor().reindex(T.day).to_numpy()
    cost = np.maximum(T.frozen_cost_adj.to_numpy() / fac, C.RT_STD_PTS["NQ"])
    R = pd.Series((T.gross_adj.to_numpy() / fac - cost) / (T.risk_adj.to_numpy() / fac), index=T.index)
    days = BL.sessions_in(window)
    per = R.groupby(T.day.to_numpy()).sum().reindex(days).fillna(0.0)
    t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per)))
    w, l = R[R > 0], R[R <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else np.inf
    cut = int(np.ceil(0.01 * len(R)))
    ex1 = R.sum() - R.sort_values(ascending=False).head(cut).sum()
    pos_y = int((R.groupby(T.day.dt.year.to_numpy()).sum() > 0).sum())
    ok = bool(R.mean() > 0 and t > 3.0 and pf >= 1.15 and ex1 > 0 and pos_y >= 4)
    return ok, dict(expR=R.mean(), t=t, pf=pf, ex1=ex1, pos_y=pos_y)


def main():
    import qqq_screen as QS
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        QS.SRC = src
        if window == "full":
            C.run_frozen("qqq_screen", [("qqq_screen", "SRC", src)], "B06_frozen_output.txt")
        S, rej = QS.build_sessions()
        print(f"{window}: sessions {len(S)}, rejected {rej}")
        for om, sa, tg in product(QS.G_OR, QS.G_SATR, QS.G_TGT):
            k = f"OR{om} SATR{sa} R{tg}"
            T = trades(QS, S, om, sa, tg)
            m = BL.evaluate_adj(T.day, T.gross_adj, window, T.frozen_cost_adj)
            res.setdefault(k, {})[window] = m
            if window == "full":
                ok, c = criteria(T, window)
                flags[k] = ok
                notes.append(f"{k}: expR {c['expR']:+.3f} t {c['t']:+.2f} PF {c['pf']:.2f} "
                             f"ex1 {c['ex1']:+.1f} +yrs {c['pos_y']}")
    BL.report_bar("B06", "QQQ broad screen (pullback, 16 variants)", res, list(res), flags,
                  old="0 of 16", note=" | ".join(notes))


if __name__ == "__main__":
    main()
