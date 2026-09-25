#!/usr/bin/env python3
"""Step 4, G3 -- B25 RP-012A intraday relative volume and price-impact
persistence (rp012a_stage0_inventory.py + rp012a_stage1.py at faed29d,
pre-registered 3816474). Descriptive mechanism study: own registered verdict,
outside BH (Clarification 2).

PORT NOTE (committed before this file first ran)
------------------------------------------------
rp012a_common.PATH["QQQ"] -> NQ 1-minute RTH and PATH["SPY"] -> ES 1-minute RTH
(the index-future pair); IWM, IJH and EFA stay as frozen (they are the design's
other primary and control instruments). Stage 0 inventory is rebuilt first
(sandboxed OUT), because Stage 1 reads it. The frozen discovery block
(2021-01-04 -> 2023-12-29) is kept: like-for-like. Output rows labelled "QQQ"
and "SPY" are NQ and ES. The frozen commercial-hurdle section uses an ETF cost
model and HURDLE values in bps; it is reported as frozen and NOT used for any
verdict here -- the registered verdict of RP-012A rested on the mechanism
controls (does relative volume add anything beyond the price move).
Old verdict: rejected; relative volume adds nothing beyond displacement
(A minus displacement-only negative in 8 of 9 instrument-years).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def main():
    import rp012a_common as RC
    RC.PATH["QQQ"] = BL.NQ_FULL
    RC.PATH["SPY"] = BL.S4 / "ES_1m.parquet"
    _, t0 = C.run_frozen("rp012a_stage0_inventory", [], "B25_frozen_stage0_output.txt")
    _, t1 = C.run_frozen("rp012a_stage1", [], "B25_frozen_output.txt")
    print("\n".join(t1.splitlines()[-40:]))
    C.record(dict(id="B25", study="RP-012A relative volume (descriptive; NQ/ES for QQQ/SPY)",
                  primary="own registered verdict (outside BH)", pass_bar=False,
                  old_verdict="rejected: relative volume adds nothing beyond displacement",
                  new_verdict_pre_bh="see B25_frozen_output.txt (outside BH)"))


if __name__ == "__main__":
    main()
