#!/usr/bin/env python3
"""Step 4, G1 -- T18 RP-010 (frozen, rp010_stage1.py) on the Databento discovery
ticks, run after RP-011 as decided in P6. Verdict agreement; outside BH.

PORT NOTE (committed before this file first ran)
------------------------------------------------
RP-010's own loader and construction run unchanged: session_frames (tape.load_all
patched to the discovery adapter; its seal check and full-session rule unchanged),
build, label (POOLED causal thresholds, prior ten sessions), cooldown (5 minutes,
six-event cap), outcomes. One adaptation: the tape clock is ET + 4 h in every
season, so sessioncal.minutes_after_open is called on (time - 4 h) with clock
"ET" -- correct for the five EST sessions in early March too. Outputs are
sandboxed. The verdict applies the pass and kill rules operationalised in RP-011
Amendment 1 (fc2ca9f) to RP-010's pooled events, as one block ("all").
Old verdict: RP-010 rejected (8 of 10 kill conditions fire; 2 of 11 pass).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C
sys.path.insert(0, str(C.ROOT / "scripts/databento"))
import rp011_db as R11                                             # noqa: E402


def main():
    import rp010_stage1 as R10
    import sessioncal as SC
    orig = SC.minutes_after_open
    SC.minutes_after_open = lambda ts, day=None, clock="UTC": orig(
        pd.Series(pd.to_datetime(ts)) - pd.Timedelta(hours=4), day=day, clock="ET")
    R10.SC.minutes_after_open = SC.minutes_after_open
    R10.load_all = TL.A.load_tape_all
    W, Q, excluded, keep = R10.build()
    W, THR = R10.label(W)
    W = R10.cooldown(W)
    O = R10.outcomes(W, keep, mask=(W["state"] != "WARMUP"))
    lab = W[W.state != "WARMUP"]
    E = O[O.is_event].copy()
    Oa = O.copy()
    for X in (E, Oa):
        X["block"] = "all"
    months = lab.day.nunique() / 21.0
    rng = np.random.default_rng(R11.SEED)
    P, Kc, i = R11.block_eval("all", E, Oa, months, rng)
    L = [f"=== T18 RP-010 frozen on Databento discovery: sessions {W.day.nunique()}, "
         f"labelled {lab.day.nunique()}, events {len(E)} (INI {i['n_ini']}, ABS {i['n_abs']})",
         f"  15-min: INITIATIVE {i['ini']:+.2f}  ABSORPTION {i['abs']:+.2f}  D {i['D']:+.2f} t {i['t']:+.2f}",
         "  selectors: " + ", ".join(f"{k} {v:+.2f}" for k, v in i["sel"].items()),
         f"  matched times INI {i['m_ini']:+.2f} ABS {i['m_abs']:+.2f}",
         "  pass: " + " ".join(f"[{'Y' if v else 'n'}]{k.split()[0]}" for k, v in P.items())
         + f" ({sum(P.values())} of 11)",
         "  kill: " + " ".join(f"[{'FIRES' if v else '-'}]{k.split()[0]}" for k, v in Kc.items())
         + f" ({sum(Kc.values())} of 10)"]
    txt = "\n".join(L)
    print(txt)
    (C.OUT / "T18_output.txt").write_text(txt)
    agree = sum(Kc.values()) >= 5 and sum(P.values()) < 11
    C.record(dict(id="T18", study="RP-010 frozen (pooled thresholds, 6-event cap)",
                  primary="RP-011 Amendment-1 pass/kill rules, pooled", pass_bar=False,
                  old_verdict="rejected: 8 of 10 kill conditions fire, 2 of 11 pass",
                  new_verdict_pre_bh=(f"{'agrees' if agree else 'DISAGREES'}: {sum(Kc.values())} of 10 kill "
                                      f"conditions fire, {sum(P.values())} of 11 pass (outside BH)"),
                  final_verdict=(f"{'agrees' if agree else 'DISAGREES'}: {sum(Kc.values())}/10 kill, "
                                 f"{sum(P.values())}/11 pass")))


if __name__ == "__main__":
    main()
