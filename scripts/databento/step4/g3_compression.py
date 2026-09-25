#!/usr/bin/env python3
"""Step 4, G3 -- B17 compressed range resolution (compression.py +
compression_run.py at 9d27bae; proposal 2417092, amendments 02e0746, c2abfcb) on
NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
compression.SRC -> NQ file; FIRST_YEAR = 2010 (full) / 2021 (like-for-like).
BUFFER is one QQQ cent -> 0.41 NQ points (x41, step-4 section 4). W_FLOOR_BPS,
N_RANGE, TRAIL_N and C_FROZEN = 1.00 are scale-free and unchanged. The frozen
cost fraction stays inside the rule; trades are re-costed at max(frozen, NQ
0.725 pt). Gross points = R x risk + frozen cost (risk = risk_bps x px / 1e4,
cost = cost_pct x risk / 100).
Variants: D {10:00, 10:30} x exit {flat, +0.5R, +1.0R}, BOTH arm (the frozen
headline), led by excess_R (raw R minus the unconditional drift benchmark,
Amendment 1). Pass, full sample, after NQ costs, all must hold: excess_R > 0;
positive after the strict concentration drop (compression.strict_drop); excess_R
positive in >= 4 calendar years (YEARS_REQUIRED, literal); mechanism control 1 --
excess_R at c = 0.60 above excess_R at c = 1.00 (the effect must grow as
compression tightens). p for BH: one-sided daily-P&L t of raw net points, Holm
across the six.
Old verdict: economics met, mechanism falsified (largest |t| 0.61; the c ladder
ran the wrong way).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def excess_nq(T):
    """excess_R re-costed at the NQ floor: excess_R + (frozen - nq_cost)/risk."""
    day = pd.to_datetime(T.day.astype(str))
    fac = BL.factor().reindex(day).to_numpy()
    px_risk = T.risk_bps.to_numpy() / 1e4          # risk / px
    risk_adj = px_risk * T._px.to_numpy()
    frozen = T.cost_pct.to_numpy() / 100 * risk_adj
    nq = np.maximum(frozen / fac, C.RT_STD_PTS["NQ"]) * fac
    return T.excess_R.to_numpy() + (frozen - nq) / risk_adj


def main():
    import compression as M
    M.BUFFER = 0.01 * 41.0
    res, flags, notes = {}, {}, []
    for window, src, fy in (("full", BL.NQ_FULL, 2010), ("2021", BL.NQ_2021, 2021)):
        M.SRC, M.FIRST_YEAR = src, fy
        M.C_FROZEN = 1.00
        S = M.frame(M.load())
        drift = M.drift_fracs(S)
        pxmap = {s["day"]: s["px"] for s in S}
        print(f"{window}: sessions {len(S)}")
        ladder = {}
        if window == "full":
            for c in (0.60, 1.00):
                M.C_FROZEN = c
                X = M.trades(S, "10:00", "flat", drift)
                X["_px"] = X.day.map(pxmap)
                ladder[c] = excess_nq(X).mean() if len(X) else np.nan
            M.C_FROZEN = 1.00
        for dlab in M.D_MINS:
            for tlab in M.TARGETS:
                k = f"D {dlab} exit {tlab}"
                T = M.trades(S, dlab, tlab, drift)
                if T.empty:
                    res.setdefault(k, {})[window] = C.evaluate([], [], BL.sessions_in(window))
                    flags.setdefault(k, False)
                    continue
                T["_px"] = T.day.map(pxmap)
                risk = T.risk_bps / 1e4 * T._px
                cost = T.cost_pct / 100 * risk
                gross = T.R * risk + cost
                day = pd.to_datetime(T.day.astype(str))
                res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
                if window == "full":
                    ex = excess_nq(T)
                    conc, _ = M.strict_drop(ex)
                    yp, yt = M.years_pos(ex, T.year.to_numpy())
                    grows = bool(ladder[0.60] > ladder[1.00])
                    ok = bool(ex.mean() > 0 and conc > 0 and yp >= 4 and grows)
                    flags[k] = ok
                    notes.append(f"{k}: n {len(T)} excess_R {ex.mean():+.4f} conc {conc:+.4f} "
                                 f"yrs {yp}/{yt} ladder c0.60 {ladder[0.60]:+.4f} vs c1.00 {ladder[1.00]:+.4f}")
    BL.report_bar("B17", "compressed range resolution (6 variants, BOTH arm)", res, list(res), flags,
                  old="economics met, mechanism falsified", note=" | ".join(notes))


if __name__ == "__main__":
    main()
