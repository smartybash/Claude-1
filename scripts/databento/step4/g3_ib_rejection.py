#!/usr/bin/env python3
"""Step 4, G3 -- B15 Initial Balance by Rejection (ib_study.py + ib_rejection.py,
run at 90ffc57, pre-registered 9043ab6) on NQ 1-minute bars. B32 (ib_study.py)
is the same study and is recorded as a duplicate of B15 (inventory correction).

PORT NOTE (committed before this file first ran)
------------------------------------------------
ib_rejection.QQQ -> NQ 1-minute RTH (full; 2021 line). Stage 1 (break rate by
Ending-Zone bucket vs the geometric (100 - EZ)% benchmark) is descriptive and is
printed. The ATAS "NQ tick" arm is not run: the frozen pre-registration already
said no result from it counts as evidence, and the tape here would be different
sessions. The trading claim is Stage 3: long/short the first break of the IB in
the expected direction from the 0-25% bucket, stop = other side of the IB,
targets 1R / 2R / 3R / close, honest fills, entry bar excluded. Frozen cost is
the fraction of price (2 pt at 30,000); trades are re-costed at max(frozen, NQ
0.725 pt). Frozen pass bar per target: t > 3 across trades and expR > 0, after
NQ costs. p for BH: one-sided daily-P&L t, Holm across the four targets.
Old verdict: the break rate is geometry; the trade fails.
"""
from __future__ import annotations

import contextlib
import io
import sys
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def main():
    import ib_rejection as IR
    import ib_study as IS
    res, flags, notes = {}, {}, []
    buf = io.StringIO()
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        IR.QQQ = src
        Q = pd.DataFrame(IR.qqq_sessions())
        Q["bucket"] = Q.ez.map(IR.bucket_of)
        with contextlib.redirect_stdout(buf):
            print(f"\n######## window {window}")
            if window == "full":
                IS.stage1(Q, "NQ (full)")
            T = IS.stage3(Q, f"NQ ({window})")
        px = T.day.map(dict(zip(Q.day, Q.px)))
        risk = T.risk_bps * px / 1e4
        cost = px * IR.COST_F
        day = pd.to_datetime(T.day.astype(str))
        fac = BL.factor().reindex(day).to_numpy()
        for key in ("1R", "2R", "3R", "Close"):
            gross = T[key] * risk + cost
            res.setdefault(key, {})[window] = BL.evaluate_adj(day, gross, window, cost)
            if window == "full":
                R = (gross.to_numpy() / fac - np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"])) \
                    / (risk.to_numpy() / fac)
                tt = R.mean() / (R.std(ddof=1) / sqrt(len(R)))
                flags[key] = bool(tt > 3 and R.mean() > 0)
                notes.append(f"{key}: n {len(R)} expR {R.mean():+.3f} trade t {tt:+.2f} "
                             f"win {100*(R > 0).mean():.1f}%")
    (C.OUT / "B15_frozen_output.txt").write_text(buf.getvalue())
    BL.report_bar("B15", "IB by rejection, Stage 3 trade (4 targets)", res, list(res), flags,
                  old="break rate is geometry; the trade fails", note=" | ".join(notes))
    C.record(dict(id="B32", study="ib_study.py (duplicate of B15)", primary="see B15", pass_bar=False,
                  old_verdict="same study as B15", new_verdict_pre_bh="duplicate of B15; counted once"))


if __name__ == "__main__":
    main()
