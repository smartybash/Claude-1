#!/usr/bin/env python3
"""Step 4, G1 -- T04 tape level fade (levels.py + levels_audit.py), T05 weight
rule (level_weight.py).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions (tape adapter). Frozen constants unchanged:
touch 0.25, re-arm 8, merge 5, IB end 14:30 on the adapter clock (= 10:30 ET),
cost 2.0 pt round trip (stricter than NQ 0.725 / MNQ 1.12, so it applies);
T05's HEAVY_THRESHOLD 10,000 contracts within +/-2.0 pt, stop = target = 30.
Session pairs follow each frozen script: levels.py pairs every consecutive
recorded session; levels_audit.py and level_weight.py pair consecutive TRADING
days only (pd.bdate_range length 2).

T04 primary: the audit's section 4 -- merged levels, in range, consecutive
    trading-day pairs, de-overlapped, the six stop/target cells (10/10, 15/15,
    20/20, 15/30, 20/40, 30/30). Holm on one-sided session-clustered p; study p
    = smallest.
T05 primary: fade LIGHT levels, frozen parameters, all sessions (every session
    here is out-of-sample for the rule), de-overlapped. One cell.
Pass bar: net mean > 0 and study p <= 0.05. Old verdicts: T04 dead (shrank with
sample, assumed fill); T05 dead (out-of-sample -1.36 pt).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C


def trading_pairs(keys):
    return [(a, b) for a, b in zip(keys, keys[1:]) if len(pd.bdate_range(a, b)) == 2]


def t04(D):
    import levels as LV
    import levels_audit as LA
    C.run_frozen("levels", [], "T04_frozen_levels_output.txt")
    C.run_frozen("levels_audit", [], "T04_frozen_audit_output.txt")
    rows = []
    for prev_d, d in trading_pairs(sorted(D)):
        cur = D[d]
        lv = LV.session_levels(D[prev_d])
        ibl, ib_end = LV.ib_levels(cur)
        lv.update(ibl)
        merged = LA.merge_levels(lv)
        p = cur.price.to_numpy()
        inr = {k: v for k, v in merged.items() if p.min() <= v <= p.max()}
        for tch in LA.touches_merged(cur, inr, ib_end):
            if LV.features(cur, tch["idx"], tch["price"]) is None:
                continue
            rows.append(dict(day=d, **tch))
    T = pd.DataFrame(rows).reset_index(drop=True)
    res = {}
    for stop, target in ((10, 10), (15, 15), (20, 20), (15, 30), (20, 40), (30, 30)):
        per = {}
        busy, cd = -1, None
        for _, r in T.iterrows():
            if r.day != cd:
                cd, busy = r.day, -1
            if r.idx < busy:
                continue
            p = D[r.day].price.to_numpy()
            direction = +1 if r.from_above else -1
            v, j = LV.resolve(p, int(r.idx), p[int(r.idx)], direction, stop, target)
            per.setdefault(r.day, []).append(v)
            busy = j
        res[f"stop {stop} / target {target}"] = TL.cell_eval(list(per.items()),
                                                             LA.COST_PTS, D)
    return res


def t05(D):
    import level_weight as LW
    import sweep2 as S2
    C.run_frozen("level_weight", [], "T05_frozen_output.txt")
    T = LW.build(D, trading_pairs(sorted(D)))
    res = {}
    for lab, sel in (("fade LIGHT (the rule)", T.light), ("fade heavy (avoid)", ~T.light)):
        rows = []
        for d in sorted(T.day.unique()):
            rows.append((d, S2.trade(D, T, LW.STOP, LW.TARGET, True, (sel & (T.day == d)).values)))
        res[lab] = TL.cell_eval(rows, LW.COST_PTS, D)
    return res


def main():
    D = TL.days()
    print(f"sessions: {len(D)}; trading-day pairs: {len(trading_pairs(sorted(D)))}")
    r4 = t04(D)
    TL.report("T04", "tape level fade (audit grid)", r4, list(r4),
              old="dead: shrank with sample; assumed fill")
    r5 = t05(D)
    TL.report("T05", "weight rule (fade light levels)", r5, ["fade LIGHT (the rule)"],
              old="dead: OOS -1.36 pt")


if __name__ == "__main__":
    main()
