#!/usr/bin/env python3
"""Step 4, G3 -- B14 IB ending zone + pullback rejection (ib_pullback.py at
ebff421/1b0299c, pre-registered 417a012) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
The frozen rule is written in NQ points (risk band 8-40 pt, buffer 2 ticks) and
was converted to QQQ by NQ_RATIO = 41.27. On NQ bars the native meaning applies:
NQ_RATIO = 1.0. SRC -> NQ file; FIRST_YEAR = 2010 for the full sample (2021 for
the like-for-like line); the frozen June-2026 skip is kept. Cost: the frozen
fraction of price and its 10%-of-risk viability rule are unchanged inside the
rule; trades are then re-costed at max(frozen, NQ 0.725 pt) in real points.
Points on adjusted bars are divided by the session factor for dollars; the 8-40
point band is applied to adjusted prices (factor 1.00-1.24), stated here.
Decision rule (section 8), all must hold, full sample, after NQ costs: >= 150
trades; expR > 0; PF >= 1.15; positive in >= 4 calendar years (literal); positive
after removing the best 5 AND under the standing rule max(10, ceil(0.10n))
(split verdict if only one); positive at +50% cost; beats the shifted-zone
control (shift 0.25); rejection beats touch-only; beats the no-ending-zone
control. The ten-th criterion ("drawdown operationally reasonable") is a
judgment: reported, and flagged for the user if a variant meets all the others.
Controls are run only for variants that pass the numeric criteria (the rule is
conjunctive). p for BH: one-sided daily-P&L t, Holm across 18.
Old verdict: one variant cleared every stated bar in-sample; holdout exactly
break-even; family closed (also failed on related instruments).
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


def to_trades(T, SS):
    px = T.day.map({S["day"]: S["px"] for S in SS})
    risk = T.risk_bps * px / 1e4
    cost = T.cost_pct / 100.0 * risk
    gross = T.R * risk + cost
    return pd.to_datetime(T.day.astype(str)), gross, risk, cost


def R_nq(day, gross, risk, cost, cmul=1.0):
    fac = BL.factor().reindex(day).to_numpy()
    c = np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"]) * cmul
    return (gross.to_numpy() / fac - c) / (risk.to_numpy() / fac)


def main():
    import ib_pullback as IB
    IB.NQ_RATIO = 1.0
    res, flags, notes = {}, {}, []
    for window, src, fy in (("full", BL.NQ_FULL, 2010), ("2021", BL.NQ_2021, 2021)):
        IB.SRC, IB.FIRST_YEAR = src, fy
        SS = IB.load()
        SS = [S for S in SS if pd.Timestamp(str(S["day"])) in set(BL.sessions_in(window))] \
            if isinstance(SS, list) else SS
        print(f"{window}: sessions {len(SS)}")
        for zone, rej, ex in product(IB.ZONES, IB.REJECTS, IB.EXITS):
            k = f"{zone} {rej} {ex}"
            T, _ = IB.collect(SS, zone, rej, ex)
            if T.empty:
                res.setdefault(k, {})[window] = C.evaluate([], [], BL.sessions_in(window))
                flags[k] = False
                continue
            day, gross, risk, cost = to_trades(T, SS)
            res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
            if window != "full":
                continue
            R = R_nq(day, gross, risk, cost)
            w, l = R[R > 0], R[R <= 0]
            pf = w.sum() / -l.sum() if len(l) and l.sum() < 0 else np.inf
            yp = int((pd.Series(R).groupby(day.year.to_numpy()).mean() > 0).sum())
            b5 = np.sort(R)[:max(0, len(R) - 5)].mean() if len(R) > 5 else np.nan
            kk = max(10, int(ceil(0.10 * len(R))))
            sc = np.sort(R)[:len(R) - kk].mean() if kk < len(R) else np.nan
            c50 = R_nq(day, gross, risk, cost, 1.5).mean()
            num = [len(R) >= 150, R.mean() > 0, pf >= 1.15, yp >= 4, b5 > 0, sc > 0, c50 > 0]
            s = (f"n {len(R)} expR {R.mean():+.3f} PF {pf:.2f} +yrs {yp} -best5 {b5:+.3f} "
                 f"-std {sc:+.3f} +50%c {c50:+.3f}")
            ok = all(num)
            if ok:
                ctl = {}
                for lab, kw in (("shift", dict(shift=0.25)), ("touch", dict(touch_only=True)),
                                ("noEZ", dict(use_ez=False))):
                    Tc, _ = IB.collect(SS, zone, rej, ex, **kw)
                    dc, gc, rc, cc = to_trades(Tc, SS)
                    ctl[lab] = R_nq(dc, gc, rc, cc).mean() if len(Tc) else -np.inf
                ok = all(R.mean() > v for v in ctl.values())
                s += " | controls " + " ".join(f"{a} {b:+.3f}" for a, b in ctl.items())
                s += " | DRAWDOWN JUDGMENT NEEDED" if ok else ""
            flags[k] = ok
            notes.append(f"{k}: {s}")
    BL.report_bar("B14", "IB ending zone + pullback rejection (18 variants)", res, list(res), flags,
                  old="one variant cleared in-sample; holdout break-even; closed", note=" | ".join(notes))


if __name__ == "__main__":
    main()
