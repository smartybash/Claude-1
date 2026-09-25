#!/usr/bin/env python3
"""Step 4, G3 -- B26 RP-13 FVG family, multi-timeframe (rp13_fvg.py at f5f91a0,
pre-registered adb6226) on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
load() concatenates two QQQ files by literal path; both strings are replaced by
the NQ 1-minute file (full history; a second copy uses the 2021 window) --
drop_duplicates in load() makes the double read harmless. TICK = 0.01 is one
QQQ tick; constants in ticks stay in ticks, so TICK = 0.25 (one NQ tick). ATR
multiples, COST_BPS 0.667 and MAX_COST_RISK are scale-free and unchanged; trades
are re-costed at max(frozen, NQ 0.725 pt). Gross points = (R + cost_r) x risk.
Primary timeframes 1, 2, 3, 5 minutes (15/30/60 are diagnostic, never
promotable, as frozen). Promotion rule (section 6) at one timeframe, after NQ
costs: net expectancy >= +0.10R with 90% CI lower bound > 0; >= 12 trades/month;
trades/month x expectancy >= 2.0R; median cost/risk <= 10%; plus the frozen
mechanism control and max-statistic permutation p < 0.05, read from the frozen
output. Criterion 4 (OOS drawdown) cannot be met on a backtest, so at best a
timeframe "survives discovery". p for BH: one-sided daily-P&L t, Holm across the
four primary timeframes.
Old verdict: null, closed.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def patched(src_file, name):
    p = C.ROOT / "scripts/orderflow/rp13_fvg.py"
    s = p.read_text()
    rel = str(src_file.relative_to(C.ROOT))
    for a in ('"data/intraday_long/QQQ_1m_holdout.parquet"', '"data/intraday_long/QQQ_1m.parquet"'):
        assert s.count(a) == 1
        s = s.replace(a, f'"{rel}"')
    m = types.ModuleType(name)
    m.__file__ = str(p)
    exec(compile(s, str(p), "exec"), m.__dict__)
    m.TICK = 0.25
    sys.modules[name] = m
    return m


def main():
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        M = patched(src, f"rp13_nq_{window}")
        if window == "full":
            _, txt = C.run_frozen(f"rp13_nq_{window}", [], "B26_frozen_output.txt")
            verdict = [l for l in txt.splitlines() if "VERDICT" in l.upper() or "surviv" in l.lower()]
            notes.append("frozen verdict lines: " + " / ".join(v.strip() for v in verdict[-4:]))
        d, half = M.load()
        months = d["day"].dt.to_period("M").nunique()
        for tf in M.PRIMARY:
            b = M.resample(d, tf)
            F = M.detect(b, True)
            T, _, _ = M.trades(b, F)
            k = f"{tf}-min FVG"
            gross = (T.R + T.cost_r) * T.risk
            frozen = T.cost_r * T.risk
            day = pd.to_datetime(T.day)
            res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, frozen)
            if window == "full":
                fac = BL.factor().reindex(day).to_numpy()
                cost = np.maximum(frozen.to_numpy() / fac, C.RT_STD_PTS["NQ"])
                R = (gross.to_numpy() / fac - cost) / (T.risk.to_numpy() / fac)
                se = R.std(ddof=1) / np.sqrt(len(R))
                lo90 = R.mean() - 1.645 * se
                tpm = len(R) / months
                cr = np.median(cost / (T.risk.to_numpy() / fac))
                flags[k] = bool(R.mean() >= 0.10 and lo90 > 0 and tpm >= 12 and tpm * R.mean() >= 2.0
                                and cr <= 0.10)
                notes.append(f"{k}: n {len(R)} expR {R.mean():+.3f} 90%lo {lo90:+.3f} trades/mo {tpm:.1f} "
                             f"monthly R {tpm*R.mean():+.2f} med cost/risk {100*cr:.1f}%")
    BL.report_bar("B26", "RP-13 FVG multi-timeframe (4 primary timeframes)", res, list(res), flags,
                  old="null, closed", note=" | ".join(notes))


if __name__ == "__main__":
    main()
