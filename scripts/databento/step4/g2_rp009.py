#!/usr/bin/env python3
"""Step 4, G2 -- B02 RP-009 time-of-day opportunity map (rp009_stage1.py +
rp009_stage1_report.py, 04d8d4b).

PORT NOTE (committed before this file first ran)
------------------------------------------------
RP-009 is barrier geometry only: no strategy P&L, no verdict, so it is
DESCRIPTIVE and outside BH (Clarification 2). Its closure was "44 NQ sessions
cannot support a standalone commercial verdict"; the port answers that with NQ.
- "QQQ arm" (the long-sample arm) reads NQ 1-minute RTH, full history
  2010-06-07 -> 2026-09-24, in place of QQQ. Every container is frozen in bps
  (fixed 10/20/30 NQ points converted at the frozen 29,460), so nothing is
  re-tuned; at 2010 prices those bps are fewer NQ points, exactly as the frozen
  definition implies.
- "NQ arm" (tick-order calibration) reads the 61 Databento discovery sessions
  through the tape adapter in place of the 44 ATAS sessions.
- The report's block_atr() reads the QQQ file by a hard-coded path; its source is
  loaded with only that path replaced by the NQ file.
- Outputs go to reports/step4/frozen/ (module OUT redirected); nothing in
  reports/ is overwritten.
"""
from __future__ import annotations

import contextlib
import io
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C

NQ = C.ROOT / "data/clean/step4/NQ_1m.parquet"


def main():
    safe = C.OUT / "frozen"
    safe.mkdir(parents=True, exist_ok=True)
    import rp009_stage1 as R9
    R9.OUT, R9.QQQ = safe, NQ
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        E, B, sk, nd = R9.qqq()
        E.to_parquet(safe / "rp009_qqq_exc.parquet")
        B.to_parquet(safe / "rp009_qqq_bar.parquet")
        print("NQ-as-long-arm exc", E.shape, "bar", B.shape, "skipped", sk, "calendar days", nd)
        E, B, T, nn = R9.nq()
        E.to_parquet(safe / "rp009_nq_exc.parquet")
        B.to_parquet(safe / "rp009_nq_bar.parquet")
        T.to_parquet(safe / "rp009_nq_tick.parquet")
        print("NQ tape sessions", nn, "exc", E.shape, "bar", B.shape, "tick", T.shape)
    src_path = C.ROOT / "scripts/orderflow/rp009_stage1_report.py"
    src = src_path.read_text()
    old = '"data/intraday_long/QQQ_1m.parquet"'
    assert src.count(old) == 1
    src = src.replace(old, '"data/clean/step4/NQ_1m.parquet"')
    m = types.ModuleType("rp009_report_nq")
    m.__file__ = str(src_path)
    exec(compile(src, str(src_path), "exec"), m.__dict__)
    m.OUT = safe
    with contextlib.redirect_stdout(buf):
        m.main()
    txt = buf.getvalue()
    (C.OUT / "B02_frozen_output.txt").write_text(txt)
    print(txt[-3000:])
    C.record(dict(id="B02", study="RP-009 time-of-day map (descriptive)", primary="none (barrier geometry)",
                  pass_bar=False, old_verdict="44 NQ sessions cannot support a standalone verdict",
                  new_verdict_pre_bh="descriptive rerun on 4,189 NQ sessions; see B02_frozen_output.txt"))


if __name__ == "__main__":
    main()
