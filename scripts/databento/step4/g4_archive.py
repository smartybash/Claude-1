#!/usr/bin/env python3
"""Step 4, G4 -- archive scripts, verdict agreement only, outside BH
(Clarification 4).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Each script runs from its last committed version with ONE change: its module
ROOT (and the ROOT of the archive helpers it imports) points at
reports/step4/frozen/root_nq (nq_root.py), where the QQQ files it reads by name
hold NQ bars (5-minute and 1-minute RTH, daily RTH), ratio back-adjusted. All
constants in these scripts are percentages or NQ-points-at-29,400 fractions, so
nothing is converted. These scripts model NO costs (as frozen); their headline
is gross. If an NQ headline comes out positive, costs are added before any
agreement is stated. Gamma splits read the QQQ gamma log and are meaningless on
NQ; they are ignored. The headline each closure rested on, declared now:
  A01 backtest_ict_sweep      window 09:30-11:00, target mid: expectancy (old -0.19R, t -2.78)
  A02 backtest_nwog           weekend-gap fade expectancy (old -0.34R, t -13.2)
  A03 backtest_orb15          ORB15 + FVG profit factor (old PF 1.01; imbalance filter 0.87)
  A04 backtest_initial_balance best configuration (old: no configuration pays)
  A05 backtest_vwap_retest    expectancy (old +0.049R, noise)
  A06 backtest_aplus4 / aplus5 honest-entry fade (old -0.047R) / best limit cell and its OOS half (old +0.196R t 1.68; OOS -0.235R)
  A07 backtest_open_drive     09:30-10:00 direction at 10:00 (old +0.099R t 1.84, first half +0.021R)
  A08 backtest_irb            IRB expectancy (old: rejected)
  A10 backtest_daily_fvg      daily FVG expectancy (old: rejected)
  A11 backtest_range_breakout daily range breakout (old: rejected)
  A12 backtest_oversold_long  daily oversold bounce (old: the one real daily effect, not a day trade)
Not ported: A09 (handled separately), A13 (sweeplib rebuilds a cache inside
data/ from ~60-session IBKR/Yahoo files; its hypothesis is covered on NQ by
study (d) and T04).
"""
from __future__ import annotations

import contextlib
import importlib
import io
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nq_root                                                     # noqa: E402
C = nq_root.C
ARCH = C.ROOT / "scripts/archive"
sys.path.insert(0, str(ARCH))
sys.path.insert(0, str(C.ROOT))

RUNS = [("A01", "backtest_ict_sweep"), ("A02", "backtest_nwog"), ("A03", "backtest_orb15"),
        ("A04", "backtest_initial_balance"), ("A05", "backtest_vwap_retest"),
        ("A06", "backtest_aplus4"), ("A06b", "backtest_aplus5"), ("A07", "backtest_open_drive"),
        ("A08", "backtest_irb"), ("A10", "backtest_daily_fvg"), ("A11", "backtest_range_breakout"),
        ("A12", "backtest_oversold_long")]
HELPERS = ["backtest_tos_fvg", "backtest_range_breakout", "backtest_aplus", "backtest_open_location"]


def main():
    root = nq_root.build()
    (root / "reports" / "img").mkdir(parents=True, exist_ok=True)
    (root / "charts").mkdir(exist_ok=True)
    for h in HELPERS:
        importlib.import_module(h).ROOT = root
    for tid, mod_name in RUNS:
        buf = io.StringIO()
        try:
            m = importlib.import_module(mod_name)
            if hasattr(m, "ROOT"):
                m.ROOT = root
            for h in HELPERS:
                sys.modules[h].ROOT = root
            old = sys.argv
            sys.argv = [mod_name]
            with contextlib.redirect_stdout(buf):
                m.main()
            sys.argv = old
            status = "ok"
        except Exception:
            status = "ERROR\n" + traceback.format_exc()
        txt = buf.getvalue() + ("" if status == "ok" else "\n" + status)
        (C.OUT / f"{tid}_frozen_output.txt").write_text(txt)
        C.assert_reports_untouched()
        print(f"===== {tid} {mod_name}: {status.splitlines()[0]}")
        print("\n".join(txt.splitlines()[-18:]))


if __name__ == "__main__":
    main()
