#!/usr/bin/env python3
"""Step 4, G4 -- A09 trendline reversal, bounded reconstruction
(trendline_recon.py), verdict agreement only (Clarification 4).

PORT NOTE (committed before this file first ran)
------------------------------------------------
The frozen script reads ATAS tape files (24-hour sessions) through sessions()
and codec.load_any. Both are patched to read the 61 Databento discovery sessions
from the tape adapter (full Globex session per file; clock ET + 4 h as for every
tape port). Nothing else changes: the nine specifications (pivot 2/2, 3/3, 5/5 x
stop 0.5, 1.0, 1.2 ATR14; TP 1.2 ATR14), the three execution models and the cost
ladder. Headline the closure rested on: Model C (tick order) with commission +
1 tick (0.72 pt, equal to the step-4 NQ standard) -- old: 0 of 9 positive, best
PF 1.03 against a 1.15 bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C, A = TL.C, TL.A


def main():
    import trendline_recon as TR
    files = sorted((A.OUT / "tape").glob("TAPE_NQ_*.parquet"))
    TR.sessions = lambda: [(p.stem.split("_")[-1], str(p)) for p in files]
    TR.load_any = lambda path, *a, **k: pd.read_parquet(path)
    _, txt = C.run_frozen("trendline_recon", [], "A09_frozen_output.txt")
    print("\n".join(txt.splitlines()[-40:]))


if __name__ == "__main__":
    main()
