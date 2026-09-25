#!/usr/bin/env python3
"""Step 4 -- B04 pullback grid 1, B05 pullback grid 2 (tape studies).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Both grids ran on ATAS tape (20 NQ sessions, one-second bars), so they are
small-sample TAPE closures and run with G1 on the 61 Databento discovery
sessions (tape adapter; roster.split patched to take every full session).
Per step-4 section 4 the script is the one AT THE CLOSING COMMIT, loaded with
`git show`: grid 1 at 75eec2c, grid 2 at 52b925d. The current script (8a2c313:
entry-lookahead fix and honest stop fills) is run on grid 2 as a SECONDARY line.
Frozen constants unchanged: RTH open 13:30 and flat 18:30 / last entry 18:00 on
the adapter clock (= 09:30, 14:30, 14:00 ET); cost 2.0 pt round trip (stricter
than the NQ standard, applies).
Frozen pass bar per variant (the five registered rejection criteria): expectancy
> 0, >= 15 sessions traded, PF >= 1.15, total > 0 without the best five trades,
both date halves positive. p for BH: one-sided session-clustered p of net points
per variant, Holm across the 12; study p = smallest. Revival needs BH p <= 0.05
AND the five criteria.
Old verdicts: grid 1 0 of 12 (specification defect); grid 2 0 of 12.
"""
from __future__ import annotations

import subprocess
import sys
import types
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C
import tape                                                        # noqa: E402
import roster                                                      # noqa: E402


def split_all(days):
    disc, bad = {}, {}
    for d, x in sorted(days.items()):
        (disc if tape.is_full_session(x) else bad)[d] = x
    return disc, {}, bad


roster.split = split_all


def load_at(commit, name):
    src = subprocess.run(["git", "show", f"{commit}:scripts/orderflow/pullback.py"],
                         cwd=C.ROOT, capture_output=True, text=True, check=True).stdout
    m = types.ModuleType(name)
    m.__file__ = str(C.ROOT / "scripts/orderflow/pullback.py")
    exec(compile(src, f"pullback@{commit}", "exec"), m.__dict__)
    m.split = split_all
    m.load_all = TL.A.load_tape_all
    return m


def run_grid(M, tid, label, D, old, record=True):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        M.main()
    (C.OUT / f"{tid}_frozen_output.txt").write_text(buf.getvalue())
    per = M.sessions()
    days_all = sorted(per)
    half = len(days_all) // 2
    first, second = set(days_all[:half]), set(days_all[half:])
    res, crit = {}, {}
    mid, mlab = ((M.GRID_STOP_ATR, "SATR") if hasattr(M, "GRID_STOP_ATR") else (M.GRID_EXC, "EXC"))
    grid = list(product(M.GRID_OR_MIN, mid, M.GRID_TGT_R))
    for g in grid:
        key = " ".join(f"{a}{b}" for a, b in zip(("OR", mlab, "R"), g))
        T = M.evaluate(per, *g)
        if T.empty:
            res[key] = TL.cell_eval([], M.COST_PTS, D)
            crit[key] = False
            continue
        gross = T.pnl + M.COST_PTS
        res[key] = TL.cell_eval([(d, gross[T.day == d].to_numpy()) for d in T.day.unique()],
                                M.COST_PTS, D)
        m = M.metrics(T, days_all)
        h1, h2 = T[T.day.isin(first)].pnl.sum(), T[T.day.isin(second)].pnl.sum()
        crit[key] = bool(m["exp"] > 0 and m["sessions"] >= 15 and m["pf"] >= 1.15
                         and m["ex_top5"] > 0 and h1 > 0 and h2 > 0)
    keys = list(res)
    raw = [res[k]["p_one"] if np.isfinite(res[k]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    note = f"frozen five-criteria survivors: {sum(crit.values())} of {len(crit)}"
    if record:
        TL.report(tid, label, res, keys, extra_ok=crit[best],
                  extra_lab=", five registered criteria", old=old, note=note)
    else:
        L = [f"=== {tid} {label} (secondary, not recorded) ===", f"  note: {note}"]
        L += [f"  {k:<22} {C.fmt(res[k])}" for k in keys]
        txt = "\n".join(L)
        (C.OUT / f"{tid}_output.txt").write_text(txt)
        print(txt, "\n")


def main():
    D = TL.days()
    print(f"sessions: {len(D)}")
    run_grid(load_at("75eec2c", "pullback_g1"), "B04", "pullback grid 1 (75eec2c)", D,
             "0 of 12 (specification defect)")
    run_grid(load_at("52b925d", "pullback_g2"), "B05", "pullback grid 2 (52b925d)", D, "0 of 12")
    run_grid(load_at("8a2c313", "pullback_now"), "B05b", "pullback grid 2, current script (8a2c313)",
             D, "0 of 12", record=False)


if __name__ == "__main__":
    main()
