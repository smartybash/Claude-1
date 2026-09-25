#!/usr/bin/env python3
"""Step 4, G3 -- further studies judged on their own registered tests (outside BH,
Clarification 2): B11 prior-day levels predictive, B12 setup grading, B20 RP-002,
B21 RP-003, B22 RP-005, B23 RP-007 1A1, B24 RP-008.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Frozen scripts run unchanged except for data paths; writes are sandboxed and
guarded (run_frozen). These are descriptive or classification studies with no
standalone profitability claim, so each is reported against its own registered
verdict and kept out of BH.
- Their frozen DATE BLOCKS are kept (RP-002 discovery 2021-2024, RP-003
  2021-2022, RP-005 2021-2023 + validation 2024-2025, RP-007 / RP-008 as frozen):
  the rerun is like-for-like on NQ over the same dates.
- B11 levels_predictive.py (d6539a1): gamma levels come from QQQ option data and
  have no meaning on NQ prices, so gamma_map returns nothing and only the five
  prior-day price levels are tested (test A reaction at touch vs 50%, test B
  clustering vs a stranger's levels). SRC -> NQ full history.
- B12 setup_grading.py (bb0ab30): or_height.build is redirected from the QQQ
  path to the NQ 1-minute file (full history); everything else frozen.
- B21 rp003_stage1.py: QQQ -> NQ and SPY -> ES 1-minute (the index-future pair),
  by replacing the two path strings in its source.
- B23 / B24: rp007_stage1a1.py and rp008_stage1.py write parquet that their
  report scripts read; both sides use the sandboxed OUT.
Old verdicts: B11 0 of 13 (0 of 8 + 0 of 5); B12 worse than random and backwards;
B20 descriptive fail; B21 closed; B22 closed; B23 a precisely measured zero; B24
closed.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C
ES_FULL = BL.S4 / "ES_1m.parquet"


def rec(tid, study, old, txt):
    tail = " | ".join(l.strip() for l in txt.splitlines()[-10:] if l.strip())
    print(f"--- {tid}: {tail[-700:]}\n")
    C.record(dict(id=tid, study=study, primary="own registered test (outside BH)", pass_bar=False,
                  old_verdict=old, new_verdict_pre_bh=f"see {tid}_frozen_output.txt (outside BH)"))


def main():
    import levels_predictive as LP
    LP.SRC = BL.NQ_FULL
    LP.gamma_map = lambda days: {}
    _, t = C.run_frozen("levels_predictive", [], "B11_frozen_output.txt")
    rec("B11", "prior-day levels predictive (price levels only)", "0 of 13", t)

    import or_height as OH
    orig = OH.build
    OH.build = lambda path, f, *a, **k: orig(str(BL.NQ_FULL.relative_to(C.ROOT)), f, *a, **k)
    _, t = C.run_frozen("setup_grading", [], "B12_frozen_output.txt")
    OH.build = orig
    rec("B12", "setup grading scheme", "worse than random and backwards", t)

    import rp002_stage1 as R2
    R2.RTH, R2.ETH = BL.NQ_FULL, BL.NQ_ETH_FULL
    _, t = C.run_frozen("rp002_stage1", [], "B20_frozen_output.txt")
    rec("B20", "RP-002 opening auction inventory (descriptive)", "descriptive fail", t)

    src_path = C.ROOT / "scripts/orderflow/rp003_stage1.py"
    src = src_path.read_text()
    for a, b in (('"data/intraday_long/QQQ_1m.parquet"', '"data/clean/step4/NQ_1m.parquet"'),
                 ('"data/related/SPY_1m.parquet"', '"data/clean/step4/ES_1m.parquet"')):
        assert src.count(a) == 1
        src = src.replace(a, b)
    m = types.ModuleType("rp003_nq_es")
    m.__file__ = str(src_path)
    exec(compile(src, str(src_path), "exec"), m.__dict__)
    sys.modules["rp003_nq_es"] = m
    _, t = C.run_frozen("rp003_nq_es", [], "B21_frozen_output.txt")
    rec("B21", "RP-003 beta residual, NQ/ES (descriptive)", "closed", t)

    import rp005_stage1 as R5
    R5.RTH = BL.NQ_FULL
    _, t = C.run_frozen("rp005_stage1", [], "B22_frozen_output.txt")
    rec("B22", "RP-005 close auction flow (descriptive)", "closed", t)

    import rp007_stage1a1 as R7
    R7.RTH, R7.ETH = BL.NQ_FULL, BL.NQ_ETH_FULL
    _, t1 = C.run_frozen("rp007_stage1a1", [], "B23_frozen_stage_output.txt")
    _, t = C.run_frozen("rp007_stage1a1_report", [], "B23_frozen_output.txt")
    rec("B23", "RP-007 1A1 level validity (descriptive)", "a precisely measured zero", t)

    import rp008_stage1 as R8
    R8.RTH = BL.NQ_FULL
    _, t1 = C.run_frozen("rp008_stage1", [], "B24_frozen_stage_output.txt")
    _, t = C.run_frozen("rp008_stage1_report", [], "B24_frozen_output.txt")
    rec("B24", "RP-008 regime validity (descriptive)", "closed", t)


if __name__ == "__main__":
    main()
