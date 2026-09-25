#!/usr/bin/env python3
"""Step 4, G2 -- B01 FOMC family (fomc_study.py, a306378).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: NQ 1-minute RTH in the QQQ_1m schema, ratio back-adjusted. calendar_classify.SRC
and fomc_classify.SRC are pointed at it. The FOMC calendar in the repository
(data/events/fomc.csv) covers 2021-01-27 -> 2026-12-09 only, so B01 runs on the
like-for-like window 2021-01-04 -> 2026-08-31; no dates are added from memory.
Every statistic is a return, a volatility or a volume share, so no price constant
needs converting. B01 is DESCRIPTIVE (no trading claim): judged against its own
registered test -- 20 Welch tests at Bonferroni alpha 0.0025, plus matched random
labels -- and excluded from BH (Clarification 2).
Old verdict: 8 of 20 pass, 10 of 20 beat random labels (the FOMC-afternoon
volatility separation; descriptive, not a trade).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402

NQ21 = C.ROOT / "data/clean/step4/NQ_1m_2021.parquet"


def main():
    import calendar_classify as CC
    import fomc_classify as FC
    CC.SRC = NQ21
    FC.SRC = NQ21
    _, txt = C.run_frozen("fomc_study", [], "B01_frozen_output.txt")
    tail = "\n".join(txt.splitlines()[-25:])
    print(tail)
    m = re.search(r"(\d+) of (\d+)", txt)
    C.record(dict(id="B01", study="FOMC family (descriptive)", primary="20 Welch tests, Bonferroni 0.0025",
                  pass_bar=False, old_verdict="8 of 20 pass; 10 of 20 beat random (descriptive)",
                  new_verdict_pre_bh="see B01_frozen_output.txt (descriptive, excluded from BH)"))


if __name__ == "__main__":
    main()
