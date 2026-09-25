#!/usr/bin/env python3
"""Step 4, G3 -- B08 opening-range height (or_height.py at e2508bb, pre-registered
9307834) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
The frozen study had three runs because QQQ lacked 1-minute data before 2021:
A (1-minute, 2021-2026, in-sample), B (5-minute bridge), C (5-minute 2016-2020,
the evidence). NQ has 1-minute bars for every year, so the port runs the
1-minute rule (run A's grid, stop 1.0 x ATR1m) on the full NQ history as the
primary sample, and on 2021-2026 as the like-for-like line. No 5-minute rescale
is needed or used. Frozen fractions of price (break, floor, cost) kept; gross
points recovered as R x risk + frozen cost; costed at max(frozen, NQ 0.725 pt).
The tradeable object is the WIDE-only arm (OR height >= 1.00 x trailing
20-session mean). Frozen criteria (section 7), full sample, after NQ costs:
expR > 0; >= 15 sessions traded; PF >= 1.15; ex-top-1% > 0; positive in >= 4
calendar years (literal); gradient (wide minus narrow mean R) positive in >= 4
years; t > 3 across sessions. p for BH: one-sided daily-P&L t of the wide arm
over every session of the window (zero on non-wide days), Holm across 4.
Old verdict: 0 of 4.
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


def main():
    import or_height as OH
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        S, rej = OH.build(str(src.relative_to(C.ROOT)), 1)
        days = sorted(S)
        print(f"{window}: sessions {len(S)}, rejected {rej}")
        for om, tg in product(OH.G_OR, OH.G_TGT):
            k = f"OR{om} R{tg} (wide)"
            T, _ = OH.evaluate(S, days, om, tg, OH.STOP_ATR_1M)
            r = OH.or_ratio(S, days, om)
            wide = set(r[r >= OH.THRESHOLD].dropna().index)
            narrow = set(r.dropna().index) - wide
            px = T.day.map(lambda d: S[d]["px"])
            cost = T.day.map(lambda d: S[d]["cost"])
            risk = T.risk_bps * px / 1e4
            gross = T.R * risk + cost
            day = pd.to_datetime(T.day.astype(str))
            w = T.day.isin(wide).to_numpy()
            res.setdefault(k, {})[window] = BL.evaluate_adj(day[w], gross[w], window, cost[w])
            if window == "full":
                ok, s = BL.criteria_screen(day[w], gross[w], risk[w], cost[w], window)
                fac = BL.factor().reindex(day).to_numpy()
                Rn = (gross.to_numpy() / fac - np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"])) \
                    / (risk.to_numpy() / fac)
                yr = day.year.to_numpy()
                n = T.day.isin(narrow).to_numpy()
                gw = pd.Series(Rn[w]).groupby(yr[w]).mean()
                gn = pd.Series(Rn[n]).groupby(yr[n]).mean()
                grad_years = int(((gw - gn).dropna() > 0).sum())
                ntr = int(pd.Series(day[w]).nunique())
                ok = bool(ok and ntr >= 15 and grad_years >= 4)
                flags[k] = ok
                notes.append(f"{k}: {s}; sessions traded {ntr}; gradient +yrs {grad_years}")
    BL.report_bar("B08", "opening-range height, wide arm (4 variants)", res, list(res), flags,
                  old="0 of 4", note=" | ".join(notes))


if __name__ == "__main__":
    main()
