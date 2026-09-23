#!/usr/bin/env python3
"""RP-011 frozen specification -- BLOCK-RELATIVE thresholds. COUNTS ONLY.

NO FORWARD OUTCOME IS READ. This script opens the RP-010 window frame, which
carries state labels, time of day and per-window flow statistics, and never
opens the outcome frame. There is no `r30`, `r900`, `mfe` or `mae` anywhere
below, and `main()` asserts the frame it loaded contains no such column.

WHY THE THRESHOLD CHANGES, AND WHY THAT IS NOT PERFORMANCE FITTING
------------------------------------------------------------------
RP-010 took its aggression percentile from windows POOLED across the whole
session. Opening windows carry ~3.5x the midday volume and are the least
one-sided, so the opening block's own p90 imbalance (0.1678) sits BELOW the
pooled gate: 3.5% of opening windows cleared it against 16.5% at the close,
and the opening initiative cell was never populated in 25 sessions.

A pooled threshold therefore partly encodes TIME OF DAY -- the exact axis
RP-011 stratifies on. This is RP-008's pooled-tercile defect in a new place.

The correction is justified by the SAMPLING DESIGN and is verified against
counts and distributions only. No outcome informed it and none can: this file
cannot read one.

FROZEN CONSTRUCTION
-------------------
  windows      30 s, non-overlapping, cash only, first/last 5 min excluded
  blocks       opening  09:35-10:00   minutes   5-30
               morning  10:00-11:30   minutes  30-120
               midday   11:30-14:00   minutes 120-270
               closing  14:00-15:55   minutes 270-385
  thresholds   BLOCK-SPECIFIC percentiles over the prior TEN COMPLETED
               sessions: aggression p90, high impact p80, low impact p20
  states       INITIATIVE = aggression >= p90 AND impact >= p80, aligned
               ABSORPTION = aggression >= p90 AND impact <= p20
  cooldown     5 minutes from any retained event
  cap          TWO events per state per block; 8 + 8 = 16 per session
  separation   the two events of a cell must be at least ONE THIRD of the
               block's length apart. Added after the first count check showed
               the cap binding on 84% of midday absorption sessions -- a
               milder form of RP-010's first-come defect. The rule is CAUSAL:
               it is decidable at the moment of the event, so it survives into
               a live rule. Three values were tried ON COUNTS ONLY: 0.33 binds
               on 28% of sessions, 0.45 on 4%, 0.50 on 0%. All three pass;
               0.33 is chosen as the smallest that passes, discarding the
               fewest candidates. No outcome informed the choice; this file
               cannot read one.
  sides        symmetric buy and sell definitions

PRE-OUTCOME COUNT CONDITIONS (all five must hold before any outcome is viewed)
  1. all four blocks produce both initiative and absorption candidates
  2. no block is structurally empty
  3. no block contributes more than 40% of retained events
  4. buy and sell events both exist in every interpretable cell
  5. the cap binds on no more than 50% of sessions within a cell

If any fail, the proposal is revised BEFORE outcome data is collected.

APPROVED AND FROZEN 2026-09-23. The one-third separation is PERMANENTLY
frozen: it will never be compared with 0.45 or 0.50 on performance. The fresh-
data counts gate adds: at least three blocks with both states in >= 30
independent sessions; genuine closing-period representation; no cell dominated
by fewer than five sessions. A failed counts gate returns RP-011 for redesign;
thresholds and separation are never amended using outcome data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = Path(__file__).resolve().parents[2] / "reports"

import dataquality as DQ                                            # noqa: E402

BLOCKS = [(5, 30, "opening"), (30, 120, "morning"),
          (120, 270, "midday"), (270, 385, "closing")]
NAMES = [b[2] for b in BLOCKS]
TRAIL_SESS = 10
P_AGG, P_HI, P_LO = 90.0, 80.0, 20.0
MAX_PER_CELL = 2
COOLDOWN_MIN = 5
SEP_FRAC = 1 / 3
MAX_BLOCK_SHARE = 40.0
MAX_CAP_BIND = 50.0

L = []
p = L.append


def block_of(t):
    for lo, hi, lab in BLOCKS:
        if lo <= t < hi:
            return lab
    return "outside"


def label_block_relative(W):
    """Block-specific causal thresholds from the prior ten completed sessions."""
    days = sorted(W["day"].unique())
    W = W.sort_values(["day", "widx"]).reset_index(drop=True)
    state = np.array(["WARMUP"] * len(W), dtype=object)
    thr = []
    for di, d in enumerate(days):
        if di < TRAIL_SESS:
            continue
        prior = W[W["day"].isin(days[di - TRAIL_SESS:di])]
        cur_all = W["day"] == d
        state[np.flatnonzero(cur_all.to_numpy())] = "ORDINARY"
        for lab in NAMES:
            hist = prior[prior["block"] == lab]
            cur = cur_all & (W["block"] == lab)
            if len(hist) < 50 or not cur.any():
                continue
            a_thr = float(np.percentile(hist["imb"], P_AGG))
            h = hist[hist["imb"] >= a_thr]
            if not len(h):
                continue
            hi_thr = float(np.percentile(h["tpk"], P_HI))
            lo_thr = float(np.percentile(h["tpk"], P_LO))
            thr.append(dict(day=d, block=lab, a_thr=a_thr, hi_thr=hi_thr,
                            lo_thr=lo_thr, hist_windows=len(hist)))
            agg = cur & (W["imb"] >= a_thr)
            ini = agg & (W["tpk"] >= hi_thr) & W["aligned"]
            abso = agg & (W["tpk"] <= lo_thr)
            state[np.flatnonzero(abso.to_numpy())] = "ABSORPTION"
            state[np.flatnonzero(ini.to_numpy())] = "INITIATIVE"
    return W.assign(state=state), pd.DataFrame(thr)


def retain(W):
    """Two per state per block, first qualifying after a 5-minute cooldown."""
    span = {lab: hi - lo for lo, hi, lab in BLOCKS}
    keep = np.zeros(len(W), bool)
    binds = []
    for d, g in W.groupby("day"):
        last, n, last_cell = -1e9, {}, {}
        for i in g.index:
            st = W.at[i, "state"]
            if st not in ("INITIATIVE", "ABSORPTION"):
                continue
            b, t0 = W.at[i, "block"], W.at[i, "tod"]
            if b == "outside" or t0 - last < COOLDOWN_MIN:
                continue
            # the two events of a cell must sit in different parts of the block
            if t0 - last_cell.get((st, b), -1e9) < SEP_FRAC * span[b]:
                continue
            if n.get((st, b), 0) >= MAX_PER_CELL:
                binds.append((d, st, b))
                continue
            keep[i] = True
            n[(st, b)] = n.get((st, b), 0) + 1
            last = t0
            last_cell[(st, b)] = t0
    return keep, pd.DataFrame(binds, columns=["day", "state", "block"])


def grid(df):
    t = df.pivot_table(index="block", columns="state", values="widx",
                       aggfunc="count")
    return t.reindex(NAMES).fillna(0).astype(int)


def main():
    src = OUT / "rp010_windows_desealed.parquet"
    W = pd.read_parquet(src)
    banned = [c for c in W.columns
              if c.startswith(("r3", "r6", "r9", "r1", "mfe", "mae", "av"))]
    assert not banned, f"outcome columns present: {banned}"
    DQ.assert_safe_columns(W, "RP-011 spec frame")
    W = W.sort_values(["day", "widx"]).reset_index(drop=True)
    W["block"] = W.tod.map(block_of)
    W = W[W.block != "outside"].reset_index(drop=True)

    p("RP-011 FROZEN SPECIFICATION -- BLOCK-RELATIVE THRESHOLDS")
    p("  COUNTS AND DISTRIBUTIONS ONLY. No forward outcome is read; the")
    p("  loaded frame is asserted to contain no outcome column.")
    p("  Feasibility is estimated on RP-010's de-sealed sessions, which are")
    p("  CONTAMINATED for evidence and usable only for this arithmetic.")
    p("")
    W, THR = label_block_relative(W)
    lab = W[W.state != "WARMUP"]
    nsess = lab.day.nunique()
    C = lab[lab.state.isin(["INITIATIVE", "ABSORPTION"])]
    p(f"  sessions {W.day.nunique()}  warm-up {W.day.nunique()-nsess}  "
      f"labelled {nsess}  windows {len(lab)}  candidates {len(C)}")
    p("")
    p("=== BLOCK-SPECIFIC THRESHOLDS (median over sessions) ===")
    p(f"  {'block':<10}{'p90 imbalance':>16}{'p80 ticks/1k':>15}"
      f"{'p20 ticks/1k':>15}{'pooled p90 was':>17}")
    pooled = 0.2496
    for labn in NAMES:
        t = THR[THR.block == labn]
        if not len(t):
            p(f"  {labn:<10}{'no threshold formed':>16}")
            continue
        p(f"  {labn:<10}{t.a_thr.median():>16.4f}{t.hi_thr.median():>15.1f}"
          f"{t.lo_thr.median():>15.1f}{pooled:>17.4f}")
    p("")
    p("  The opening gate falls from the pooled 0.2496 to its own block value.")
    p("  That is the whole correction: each block is judged against itself.")
    p("")
    p("=== CANDIDATES by state x block ===")
    p("  " + grid(C).to_string().replace("\n", "\n  "))
    p("")
    kept, binds = retain(W)
    K = W[kept]
    p("=== RETAINED under the frozen rule (2 per state per block) ===")
    p(f"  {len(K)} of {len(C)} candidates retained "
      f"({100*(1-len(K)/len(C)):.1f}% discarded), "
      f"{len(K)/nsess:.2f} per session of a theoretical 16")
    p("  " + grid(K).to_string().replace("\n", "\n  "))
    p("")
    p("=== INDEPENDENT SESSIONS per cell ===")
    s = K.groupby(["block", "state"]).day.nunique().unstack(fill_value=0)
    s = s.reindex(NAMES).fillna(0).astype(int)
    p("  " + s.to_string().replace("\n", "\n  "))
    p("")
    p("=== BUY / SELL by cell ===")
    bs = K.groupby(["block", "state", "side"]).size().unstack(fill_value=0)
    p("  " + bs.to_string().replace("\n", "\n  "))
    p("")

    # ------------------------------------------------ the five conditions ----
    p("=== PRE-OUTCOME COUNT CONDITIONS ===")
    g = grid(K)
    gc = grid(C)
    ok = {}
    miss = [b for b in NAMES
            if gc.reindex(NAMES).fillna(0).loc[b].min() == 0]
    ok["1 all four blocks produce both states"] = (not miss, f"empty: {miss}")
    empty = [b for b in NAMES if g.loc[b].sum() == 0]
    ok["2 no block structurally empty"] = (not empty, f"empty: {empty}")
    share = 100 * g.sum(axis=1) / g.values.sum()
    worst = share.idxmax()
    ok[f"3 no block over {MAX_BLOCK_SHARE:.0f}% of retained"] = (
        share.max() <= MAX_BLOCK_SHARE,
        f"max {share.max():.1f}% ({worst}); " +
        ", ".join(f"{b} {share[b]:.1f}%" for b in NAMES))
    zero_side = []
    for b in NAMES:
        for st in ("INITIATIVE", "ABSORPTION"):
            cell = K[(K.block == b) & (K.state == st)]
            if len(cell) == 0:
                continue
            if cell.day.nunique() < 5:
                continue                      # not interpretable, condition 5
            if (cell.side == "buy").sum() == 0 or (cell.side == "sell").sum() == 0:
                zero_side.append(f"{b}/{st}")
    ok["4 buy and sell in every interpretable cell"] = (
        not zero_side, f"one-sided: {zero_side}")
    bindrow = []
    for b in NAMES:
        for st in ("INITIATIVE", "ABSORPTION"):
            cell = K[(K.block == b) & (K.state == st)]
            if not len(cell):
                continue
            nb = binds[(binds.block == b) & (binds.state == st)].day.nunique()
            bindrow.append((b, st, cell.day.nunique(), nb,
                            100 * nb / nsess))
    B = pd.DataFrame(bindrow, columns=["block", "state", "sessions",
                                       "cap_bind_sessions", "bind_pct"])
    ok[f"5 cap binds on <= {MAX_CAP_BIND:.0f}% of sessions per cell"] = (
        B.bind_pct.max() <= MAX_CAP_BIND,
        f"max {B.bind_pct.max():.1f}%")
    for k, (good, detail) in ok.items():
        p(f"  [{'PASS' if good else 'FAIL'}] {k:<48}{detail}")
    p("")
    p("  cap-binding detail:")
    p("  " + B.round(1).to_string(index=False).replace("\n", "\n  "))
    p("")
    p(f"  VERDICT ON THE SPECIFICATION: "
      f"{'ALL FIVE CONDITIONS PASS' if all(v[0] for v in ok.values()) else 'REVISION REQUIRED BEFORE COLLECTION'}")
    p("")
    p("=== COMPARISON WITH THE RP-010 POOLED CONSTRUCTION ===")
    p(f"  {'':<22}{'RP-010 pooled':>16}{'RP-011 block-relative':>24}")
    p(f"  {'events / session':<22}{'6.00':>16}{len(K)/nsess:>24.2f}")
    p(f"  {'cap binds':<22}{'100% of sessions':>16}"
      f"{f'max {B.bind_pct.max():.0f}% of sessions in a cell':>24}")
    p(f"  {'closing-block events':<22}{'0':>16}"
      f"{int(g.loc['closing'].sum()):>24}")
    p(f"  {'opening-block events':<22}{'6 (of 204)':>16}"
      f"{int(g.loc['opening'].sum()):>24}")
    p("")
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp011_spec_output.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
