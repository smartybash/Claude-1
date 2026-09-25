#!/usr/bin/env python3
"""RP-011 Stage 0 -- time-stratified order-flow state study. COUNTS ONLY.

NO OUTCOME IS READ. This script opens the RP-010 window frame, which carries
the state label, the time of day and the window's flow statistics, and never
touches the outcome frame. Grep for `r300`, `r900`, `mfe` or `mae` in here and
you will find nothing: that is the point.

The RP-010 discovery dates are CONTAMINATED for RP-011 evidence. They are used
here for one purpose the brief asks for -- a candidate-frequency estimate and
the calendar arithmetic that follows from it -- and for nothing else. The
estimate is a planning figure, not a result.

Sealed dates are excluded at the loader by `holdout`, so this reads the
de-sealed frame only.

FROZEN BLOCKS (ET), converted to minutes after the cash open:
  opening   09:35-10:00     5-30
  morning   10:00-11:30    30-120
  midday    11:30-14:00   120-270
  closing   14:00-15:55   270-385

FROZEN RETENTION: at most TWO initiative and TWO absorption events per block,
the first qualifying one after a five-minute cooldown from ANY retained event.
Theoretical maximum 8 + 8 = 16 per session.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = Path(__file__).resolve().parents[2] / "reports"

BLOCKS = [(5, 30, "opening 09:35-10:00"), (30, 120, "morning 10:00-11:30"),
          (120, 270, "midday 11:30-14:00"), (270, 385, "closing 14:00-15:55")]
NAMES = [b[2] for b in BLOCKS]
MAX_PER_CELL = 2
COOLDOWN_MIN = 5
SESSIONS_PER_MONTH = 21
TARGET_SESSIONS_PER_CELL = 30
TARGET_TRADES = 150
CONFIRM_RETENTION = 1 / 3      # one later confirmation filter, as in RP-010

L = []
p = L.append


def block_of(t):
    for lo, hi, lab in BLOCKS:
        if lo <= t < hi:
            return lab
    return "outside"


def retain(W):
    """The frozen RP-011 sampling rule. Chronology decides nothing but ties."""
    keep = np.zeros(len(W), bool)
    for _, g in W.groupby("day"):
        last, n = -1e9, {}
        for i in g.index:
            st = W.at[i, "state"]
            if st not in ("INITIATIVE", "ABSORPTION"):
                continue
            b, t0 = W.at[i, "block"], W.at[i, "tod"]
            if b == "outside" or t0 - last < COOLDOWN_MIN:
                continue
            if n.get((st, b), 0) >= MAX_PER_CELL:
                continue
            keep[i] = True
            n[(st, b)] = n.get((st, b), 0) + 1
            last = t0
    return keep


def grid(df, val="widx", how="count"):
    t = df.pivot_table(index="block", columns="state", values=val, aggfunc=how)
    return t.reindex(NAMES).fillna(0).astype(int)


def main():
    src = OUT / "rp010_windows_desealed.parquet"
    if not src.exists():
        print(f"missing {src} -- run rp010_stage1.py first")
        return 2
    W = pd.read_parquet(src)
    for bad in [c for c in W.columns if c.startswith(("r", "mfe", "mae"))
                if c in ("r30", "r900", "mfe900")]:
        raise AssertionError(f"outcome column {bad} present -- wrong frame")
    W = W[W.state != "WARMUP"].sort_values(["day", "widx"]).reset_index(drop=True)
    W["block"] = W.tod.map(block_of)
    nsess = W.day.nunique()
    C = W[W.state.isin(["INITIATIVE", "ABSORPTION"])]

    p("RP-011 STAGE 0 -- TIME-STRATIFIED ORDER-FLOW STATE STUDY")
    p("  COUNTS ONLY. No forward outcome is read anywhere in this script.")
    p("  Estimates come from RP-010's own sessions, which are CONTAMINATED")
    p("  for RP-011 evidence and usable only for frequency arithmetic.")
    p("")
    p(f"  estimate base: {nsess} de-sealed labelled sessions, "
      f"{len(W)} windows, {len(C)} candidates")
    p("")
    p("=== CANDIDATES by state x block, RP-010 thresholds unchanged ===")
    p("  " + grid(C).to_string().replace("\n", "\n  "))
    p("")
    p("=== RETAINED under the frozen RP-011 rule (2 per state per block) ===")
    K = W[retain(W)]
    p(f"  {len(K)} of {len(C)} candidates retained, "
      f"{100*(1-len(K)/len(C)):.1f}% discarded")
    p("  " + grid(K).to_string().replace("\n", "\n  "))
    p("")
    p("  RP-010's chronological six-event cap, for comparison:")
    p(f"    6.00 events/session, cap bound on 100% of sessions, "
      f"CLOSING BLOCK EMPTY")
    p(f"    RP-011 rule: {len(K)/nsess:.2f} events/session, "
      f"{100*len(K)/(16*nsess):.1f}% of the theoretical 16")
    p("")
    p("=== INDEPENDENT SESSIONS per cell (gate: >=5; target: 30) ===")
    s = K.groupby(["block", "state"]).day.nunique().unstack(fill_value=0)
    s = s.reindex(NAMES).fillna(0).astype(int)
    p("  " + s.to_string().replace("\n", "\n  "))
    p("")
    p("=== BUY / SELL BALANCE of retained events ===")
    p("  " + K.groupby(["state", "side"]).size().unstack(fill_value=0)
      .to_string().replace("\n", "\n  "))
    p("")
    p("=== WHY THE OPENING BLOCK IS NEARLY EMPTY -- distributions, not outcomes ===")
    p("  The aggression gate is a percentile POOLED over the whole session.")
    p("  Opening windows carry the most volume and the LEAST one-sidedness,")
    p("  so they almost never clear a pooled p90 imbalance.")
    p("")
    p(f"  {'block':<22}{'windows':>9}{'/sess':>8}{'med imb':>10}{'own p90':>10}"
      f"{'med vol':>10}{'clears pooled p90':>20}")
    gate = float(C.imb.min())
    for lab in NAMES:
        g = W[W.block == lab]
        p(f"  {lab:<22}{len(g):>9}{len(g)/nsess:>8.0f}{g.imb.median():>10.4f}"
          f"{g.imb.quantile(.9):>10.4f}{g.total.median():>10.0f}"
          f"{100*(g.imb>=gate).mean():>19.1f}%")
    p("")
    p("  This is RP-008's pooled-tercile defect in a new place: a threshold")
    p("  pooled across the session partly encodes TIME OF DAY, which is the")
    p("  very axis RP-011 sets out to stratify on.")
    p("")
    p("=== CALENDAR TIME ===")
    rate = (s / nsess)
    p(f"  assumed {SESSIONS_PER_MONTH} sessions/month")
    p(f"  {'cell':<36}{'rate':>8}{'sessions for 30':>18}{'months':>9}")
    worst_ok = 0.0
    for lab in NAMES:
        for st in ("ABSORPTION", "INITIATIVE"):
            r = float(rate.loc[lab, st]) if st in rate.columns else 0.0
            need = TARGET_SESSIONS_PER_CELL / r if r > 0 else np.inf
            p(f"  {lab + ' / ' + st:<36}{r:>8.3f}"
              + (f"{need:>18.0f}{need/SESSIONS_PER_MONTH:>9.1f}"
                 if np.isfinite(need) else f"{'never observed':>18}{'--':>9}"))
            if lab != NAMES[0] and np.isfinite(need):
                worst_ok = max(worst_ok, need)
    p("")
    p(f"  30 independent sessions in every NON-OPENING cell: "
      f"{worst_ok:.0f} sessions = {worst_ok/SESSIONS_PER_MONTH:.1f} months")
    per_sess = len(K) / nsess
    trades = per_sess * CONFIRM_RETENTION
    p(f"  {TARGET_TRADES} final trades at {per_sess:.2f} events/session and "
      f"one-third retention ({trades:.2f}/session): "
      f"{TARGET_TRADES/trades:.0f} sessions = "
      f"{TARGET_TRADES/trades/SESSIONS_PER_MONTH:.1f} months")
    p(f"  monthly event frequency: {per_sess*SESSIONS_PER_MONTH:.0f} retained, "
      f"{per_sess*SESSIONS_PER_MONTH*CONFIRM_RETENTION:.0f} post-confirmation")
    p("")
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp011_stage0_output.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
