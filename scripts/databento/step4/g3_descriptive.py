#!/usr/bin/env python3
"""Step 4, G3 -- descriptive studies with their own registered tests (outside BH,
Clarification 2): B09 regime forecastability, B13 calendar classification, B18
pre-open conditioning.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Each frozen script runs unchanged except for its data path; frozen writes to
ROOT/reports land in the step-4 sandbox (run_frozen), and a guard restores any
earlier result a run touches.
B09 regime_forecast.py (43ab596 / 64da7fa): 14 tests, pass = |rho| >= 0.10 AND
    p < 0.05/14 AND |decile spread| >= 0.020. SRC -> NQ full history (primary)
    and the 2021 window. Old verdict: 0 of 14.
B13 calendar_session_study.py + calendar_classify.py (c147285 / fe08dcc): 13
    categories x 4 statistics = 52 tests at alpha 0.000962; categories are pure
    calendar rules, so the full NQ history is used. Old verdict: the mechanism
    families show nothing.
B18 preopen.py (dc4f4bf / 32620b8): 30 tests (6 pre-open conditions x 5
    outcomes), pass = |rho| >= 0.10 AND permutation p < 0.001667 AND spread rule;
    positive control rho > 0.40 or the run is void. Its VIX (5-year file) and
    FOMC inputs start in 2021 and the builder asserts 2021, so it runs on the
    2021 window only (RTH and ETH NQ files). Old verdict: null replicates.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def grab(txt, pat):
    m = re.findall(pat, txt)
    return m[-1] if m else "n/a"


def main():
    import regime_forecast as RF
    out = []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        RF.SRC = src
        _, txt = C.run_frozen("regime_forecast", [], f"B09_frozen_output_{window}.txt")
        pat = r"cleared ALL THREE:\s+(\d+ of 14)"
        out.append(f"{window}: cleared all three " + grab(txt, pat))
    print("B09", out)
    C.record(dict(id="B09", study="regime forecastability (descriptive)", primary="14 tests, all three bars",
                  pass_bar=False, old_verdict="0 of 14",
                  new_verdict_pre_bh="; ".join(out) + " (descriptive, outside BH)"))

    import calendar_classify as CC
    CC.SRC = BL.NQ_FULL
    _, txt = C.run_frozen("calendar_session_study", [], "B13_frozen_output.txt")
    tail = " | ".join(l.strip() for l in txt.splitlines()[-12:] if l.strip())
    print("B13", tail[-600:])
    C.record(dict(id="B13", study="calendar classification (descriptive)", primary="52 tests, alpha 0.000962",
                  pass_bar=False, old_verdict="mechanism families show nothing",
                  new_verdict_pre_bh="NQ full history; see B13_frozen_output.txt (descriptive, outside BH)"))

    import preopen as PO
    PO.RTH, PO.ETH = BL.NQ_2021, BL.NQ_ETH_2021
    _, txt = C.run_frozen("preopen", [], "B18_frozen_output.txt")
    tail = " | ".join(l.strip() for l in txt.splitlines()[-12:] if l.strip())
    print("B18", tail[-600:])
    C.record(dict(id="B18", study="pre-open conditioning (descriptive)", primary="30 tests + positive control",
                  pass_bar=False, old_verdict="null replicates on non-price predictors",
                  new_verdict_pre_bh="NQ 2021-2026; see B18_frozen_output.txt (descriptive, outside BH)"))


if __name__ == "__main__":
    main()
