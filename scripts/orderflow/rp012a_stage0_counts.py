#!/usr/bin/env python3
"""RP-012A Stage 0 -- event COUNTS on the DISCOVERY block only. NO OUTCOMES.

Builds the frozen windows, relative volume, relative displacement, causal
thresholds, states and cooldown from `rp012a_common`, and counts what results.
Computes no forward return: the only price quantity is the window's OWN
close-to-close displacement, which is part of the state definition.

Only the discovery block (2021-01-04 .. 2023-12-29) is read for counting. The
internal-validation block is not counted, so that nothing about it -- not even
its event frequency -- is known before discovery is judged.

PRE-OUTCOME COUNT CONDITIONS, declared here before counting:
  1. states A and B each appear in >= 30 independent sessions per primary
     instrument
  2. REVISED BEFORE ANY OUTCOME: every block's share of an instrument's
     events lies within 0.5x-2.0x of that block's share of eligible windows
     (opening 5/75, morning 18/75, midday 30/75, closing 22/75). The first
     version -- no block above 40% -- was imported from RP-011 without
     re-deriving it: midday IS 40.0% of the session's windows, so the flat
     ceiling bound on it even under perfectly uniform rates. The band reused
     is condition 5's, declared before any count; no new number was chosen.
  3. every block produces both A and B events
  4. buy and sell both exist in every instrument x state cell, and neither
     side exceeds 60% of a cell
  5. the abnormal-volume rate is roughly uniform across blocks: no block's
     rate outside 0.5x-2.0x the instrument's overall rate. RP-011's lesson
     -- a pooled threshold can encode time of day -- checked, not assumed.
  6. each discovery year contributes events to every instrument x state cell
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataquality as DQ                                            # noqa: E402
import rp012a_common as C                                           # noqa: E402

OUT = C.ROOT / "reports"
PRIMARY = ("QQQ", "SPY", "IWM")
CONTROL = ("EFA",)
SESS_PER_MONTH = 21
CONFIRM_RETENTION = 1 / 3
L = []
p = L.append


def build(sym):
    d, _ = C.load(sym)
    lo, hi = (pd.Timestamp(x) for x in C.DISCOVERY)
    d = d[(d["day"] >= lo) & (d["day"] <= hi)]
    early = C.early_close_days(d)
    W = C.features(C.windows(d, early))
    W, T = C.label(W)
    W = C.cooldown(W)
    W["block"] = (W["m_end"] - C.WIN_MIN).map(C.block_of)
    W["year"] = W["day"].dt.year
    W["sym"] = sym
    banned = [c for c in W.columns if c.startswith(("fwd", "ret_", "mfe", "mae"))]
    assert not banned, f"outcome-like columns present: {banned}"
    DQ.assert_safe_columns(W, f"RP-012A {sym} counts frame")
    return W, T, len(early)


def main():
    p("RP-012A STAGE 0 -- EVENT COUNTS, DISCOVERY BLOCK ONLY")
    p(f"  {C.DISCOVERY[0]} .. {C.DISCOVERY[1]}. No forward return is computed.")
    p("  Internal validation is NOT counted.")
    p("")
    frames, thr, n_early = {}, {}, {}
    for s in PRIMARY + CONTROL:
        frames[s], thr[s], n_early[s] = build(s)
    A = pd.concat(frames.values(), ignore_index=True)
    lab = A[A["state"] != "WARMUP"]

    p("=== 1. SESSIONS AND WINDOWS ===")
    p(f"  {'instr':<6}{'sessions':>9}{'half days':>11}{'warm-up':>9}{'labelled':>10}"
      f"{'windows':>9}{'valid':>8}{'feat ok':>9}")
    for s, W in frames.items():
        n = W["day"].nunique()
        lab_s = W[W["state"] != "WARMUP"]
        p(f"  {s:<6}{n:>9}{n_early[s]:>11}{n-lab_s['day'].nunique():>9}"
          f"{lab_s['day'].nunique():>10}{len(W):>9}{int(W['valid'].sum()):>8}"
          f"{int(W['feat_ok'].sum()):>9}")
    p("  warm-up = 15 sessions before a same-bucket median exists (it needs 15")
    p("  of its 20 observations) + 20 sessions of features for the percentile")
    p("  thresholds = 35 sessions, all inside discovery. Half days are excluded")
    p("  from events AND from every lookback.")
    p("")
    p("=== 2. FROZEN THRESHOLDS, BLOCK-SPECIFIC (median over sessions) ===")
    p(f"  {'instr':<6}{'block':<9}{'RV p90':>9}{'RV p25':>9}{'RV p75':>9}"
      f"{'RD p80':>9}{'RD p50':>9}")
    for s in frames:
        for b in [x[2] for x in C.BLOCKS]:
            t = thr[s][thr[s].block == b]
            p(f"  {s:<6}{b:<9}{t.rv_abn.median():>9.3f}{t.rv_lo.median():>9.3f}"
              f"{t.rv_hi.median():>9.3f}{t.rd_mat.median():>9.3f}"
              f"{t.rd_lim.median():>9.3f}")
    p("  RV = window volume / trailing-20-session median of the same clock bucket")
    p("  RD = |window displacement| / trailing-20-session median |displacement|,")
    p("       same bucket")
    p("")
    p("=== 3. CANDIDATES AND EVENTS ===")
    p(f"  {'instr':<6}{'A cand':>8}{'B cand':>8}{'ABN mid':>9}{'C pool':>9}"
      f"{'flat':>6}{'cooldown':>10}{'A ev':>7}{'B ev':>7}{'ev/sess':>9}")
    for s, W in frames.items():
        l = W[W["state"] != "WARMUP"]
        ns = l["day"].nunique()
        ev = l[l["event"]]
        p(f"  {s:<6}{int((l.state=='A').sum()):>8}{int((l.state=='B').sum()):>8}"
          f"{int((l.state=='ABN_MID').sum()):>9}{int((l.state=='C').sum()):>9}"
          f"{int((l.drop_reason=='flat').sum()):>6}"
          f"{int((l.drop_reason=='cooldown').sum()):>10}"
          f"{int((ev.state=='A').sum()):>7}{int((ev.state=='B').sum()):>7}"
          f"{len(ev)/ns:>9.2f}")
    p("  ABN mid = abnormal volume, displacement between p50 and p80: no state.")
    p("  No session cap. The only filter is the 15-minute cooldown.")
    p("")
    ev = lab[lab["event"]]
    p("=== 4. INDEPENDENT SESSIONS, BUY/SELL BALANCE ===")
    p(f"  {'instr':<6}{'state':<6}{'events':>8}{'sessions':>10}{'buy':>7}{'sell':>7}"
      f"{'buy %':>8}")
    for s in frames:
        for st in ("A", "B"):
            g = ev[(ev.sym == s) & (ev.state == st)]
            nb, ns_ = int((g.side == "buy").sum()), int((g.side == "sell").sum())
            p(f"  {s:<6}{st:<6}{len(g):>8}{g['day'].nunique():>10}{nb:>7}{ns_:>7}"
              f"{100*nb/max(len(g),1):>7.1f}%")
    p("")
    p("=== 5. EVENTS BY TIME BLOCK ===")
    blk = ev.groupby(["sym", "state", "block"]).size().unstack(fill_value=0)
    blk = blk.reindex(columns=[b[2] for b in C.BLOCKS], fill_value=0)
    p("  " + blk.to_string().replace("\n", "\n  "))
    p("")
    p("  abnormal-volume RATE by block (share of valid windows with RV >= p90):")
    rates = {}
    for s in frames:
        l = lab[(lab.sym == s) & lab.feat_ok]
        abn = l.state.isin(["A", "B", "ABN_MID"])
        overall = abn.mean()
        row = {b[2]: abn[l.block == b[2]].mean() / overall for b in C.BLOCKS}
        rates[s] = row
        p(f"    {s:<5} overall {100*overall:5.1f}%   relative: " +
          "  ".join(f"{k} {v:.2f}x" for k, v in row.items()))
    p("")
    p("=== 6. EVENTS BY YEAR ===")
    yr = ev.groupby(["sym", "state", "year"]).size().unstack(fill_value=0)
    p("  " + yr.to_string().replace("\n", "\n  "))
    p("")
    p("=== 7. CO-EVENTS ACROSS PRIMARY INSTRUMENTS ===")
    pe = ev[ev.sym.isin(PRIMARY)]
    co = pe.groupby(["day", "k"]).sym.nunique()
    p(f"  primary events {len(pe)}; distinct (day, window) slots {len(co)}; "
      f"slots shared by 2 instruments {int((co==2).sum())}, by all 3 "
      f"{int((co==3).sum())}")
    p(f"  share of primary events that are co-events: "
      f"{100*(pe.set_index(['day','k']).index.map(co) >= 2).mean():.1f}%")
    p("  Pooled inference therefore clusters by DATE, never by event.")
    p("")
    p("=== 8. COOLDOWN AS A SAMPLING FILTER (dataquality.cap_diagnostics) ===")
    for s in frames:
        l = lab[(lab.sym == s) & lab.state.isin(["A", "B"]) & (lab.side != "flat")]
        dg = DQ.cap_diagnostics(np.ones(len(l), bool), l["event"].to_numpy(),
                                l["day"].to_numpy(), l["block"].to_numpy())
        p(f"  {s:<5} candidates {dg['candidates']}  retained {dg['retained']}  "
          f"discarded {dg['discarded_pct']:.1f}%  blocks emptied "
          f"{dg['blocks_emptied'] or 'none'}")
        p(f"        before {dg['by_block_before']}")
        p(f"        after  {dg['by_block_after']}")
    p("")
    p("=== 9. FREQUENCY AND CALENDAR ===")
    months = lab["day"].dt.to_period("M").nunique() / len(frames)
    for s in PRIMARY:
        g = ev[ev.sym == s]
        ns = lab[lab.sym == s]["day"].nunique()
        per = len(g) / ns
        a = (g.state == "A").sum() / ns
        tr = per * CONFIRM_RETENTION
        p(f"  {s:<5} {per:.2f} events/session ({a:.2f} A, {per-a:.2f} B)  "
          f"{per*SESS_PER_MONTH:.0f}/month  after one confirmation filter "
          f"{tr*SESS_PER_MONTH:.0f}/month  -> 150 trades in "
          f"{150/tr:.0f} sessions = {150/tr/SESS_PER_MONTH:.1f} months")
    q = ev[ev.sym == "QQQ"]
    qa = (q.state == "A").sum() / lab[lab.sym == "QQQ"]["day"].nunique()
    p(f"  NQ proxy (QQQ, state A only, one-third retention): "
      f"{qa*CONFIRM_RETENTION*SESS_PER_MONTH:.1f} trades/month; 150 in "
      f"{150/(qa*CONFIRM_RETENTION)/SESS_PER_MONTH:.1f} months")
    p("")

    # ------------------------------------------------------ conditions -----
    p("=== 10. PRE-OUTCOME COUNT CONDITIONS ===")
    res = []
    c1 = [(s, st, ev[(ev.sym == s) & (ev.state == st)]["day"].nunique())
          for s in PRIMARY for st in ("A", "B")]
    res.append(("1 A and B each in >= 30 sessions per primary instrument",
                all(n >= 30 for *_, n in c1), f"min {min(n for *_, n in c1)}"))
    wshare = {b: (hi - lo) / (C.LAST_MIN - C.FIRST_MIN) for lo, hi, b in C.BLOCKS}
    sh = []
    for s in PRIMARY:
        g = ev[ev.sym == s]
        vc = g.block.value_counts(normalize=True)
        sh += [vc.get(b, 0) / wshare[b] for b in wshare]
    res.append(("2 block event share within 0.5x-2.0x of window share",
                all(0.5 <= x <= 2.0 for x in sh),
                f"range {min(sh):.2f}x-{max(sh):.2f}x"))
    empty = [(s, st, b) for s in PRIMARY for st in ("A", "B")
             for b in [x[2] for x in C.BLOCKS]
             if not len(ev[(ev.sym == s) & (ev.state == st) & (ev.block == b)])]
    res.append(("3 every block produces both A and B", not empty,
                f"empty: {empty[:4]}"))
    imb = []
    for s in PRIMARY:
        for st in ("A", "B"):
            g = ev[(ev.sym == s) & (ev.state == st)]
            imb.append(100 * (g.side == "buy").mean())
    res.append(("4 buy share within 40-60% in every cell",
                all(40 <= x <= 60 for x in imb),
                f"range {min(imb):.1f}%-{max(imb):.1f}%"))
    rr = [v for s in PRIMARY for v in rates[s].values()]
    res.append(("5 abnormal rate per block within 0.5x-2.0x",
                all(0.5 <= v <= 2.0 for v in rr),
                f"range {min(rr):.2f}x-{max(rr):.2f}x"))
    miss = [(s, st, y) for s in PRIMARY for st in ("A", "B")
            for y in (2021, 2022, 2023)
            if not len(ev[(ev.sym == s) & (ev.state == st) & (ev.year == y)])]
    res.append(("6 every year contributes to every cell", not miss,
                f"missing: {miss[:4]}"))
    for name, ok, det in res:
        p(f"  [{'PASS' if ok else 'FAIL'}] {name:<56}{det}")
    p("")
    p("  VERDICT ON THE CONSTRUCTION: " +
      ("ALL CONDITIONS PASS" if all(r[1] for r in res)
       else "REVISION REQUIRED BEFORE ANY OUTCOME"))
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp012a_stage0_counts.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
