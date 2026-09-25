#!/usr/bin/env python3
"""Step 4, G3 -- B07 ORB with a session VWAP filter (orb_vwap.py at d1ade39,
pre-registered bbbddb1) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Same translation as B06: the frozen fractions of price (break 0.5, floor 2, cost
2 NQ points at 30,000) are kept and applied to the adjusted session open;
orb_vwap.SRC points at the NQ file; entry_bar_exit=False and use_vwap=True as in
the frozen main. Gross points are recovered from each trade exactly as
R x risk + frozen cost (risk = risk_bps x px / 1e4), then costed at max(frozen,
NQ 0.725 pt) in real points (MNQ max(frozen, 1.12)).
Frozen criteria (section 7), full sample, after NQ costs: expR > 0, t > 3.0
across sessions, PF >= 1.15, ex-top-1% > 0, >= 4 positive years.
p for BH: one-sided session-clustered p of net points, Holm across 16.
Old verdict: 0 of 16 (a third fill-model defect found).
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def main():
    import orb_vwap as OV
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        OV.SRC = src
        if window == "full":
            C.run_frozen("orb_vwap", [("orb_vwap", "SRC", src)], "B07_frozen_output.txt")
        S, rej = OV.build_sessions()
        days = sorted(S)
        print(f"{window}: sessions {len(S)}, rejected {rej}")
        for om, sa, tg in product(OV.G_OR, OV.G_SATR, OV.G_TGT):
            k = f"OR{om} SATR{sa} R{tg}"
            T, _ = OV.evaluate(S, days, om, sa, tg, True, False)
            px = T.day.map(lambda d: S[d]["px"])
            cost = T.day.map(lambda d: S[d]["cost"])
            risk = T.risk_bps * px / 1e4
            gross = T.R * risk + cost
            day = pd.to_datetime(T.day.astype(str))
            res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
            if window == "full":
                ok, s = BL.criteria_screen(day, gross, risk, cost, window)
                flags[k] = ok
                notes.append(f"{k}: {s}")
    BL.report_bar("B07", "ORB + session VWAP filter (16 variants)", res, list(res), flags,
                  old="0 of 16", note=" | ".join(notes))


if __name__ == "__main__":
    main()
