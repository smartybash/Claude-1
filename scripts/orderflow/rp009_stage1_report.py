#!/usr/bin/env python3
"""RP-009 Stage 1 -- report. Reads only rp009_stage1.py's own output.

No strategy P&L anywhere. The one strategy table is architecture only -- entry
window, risk, holding time -- taken from the committed RP-008 Stage 0 audit.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import rp009_stage1 as S

OUT = Path(__file__).resolve().parents[2] / "reports"
TSL = [t[0] for t in S.TS]
BLK = ["open", "morning", "midday", "close"]
CONT = ["10NQpt", "20NQpt", "30NQpt", "0.5ATR", "1.0ATR", "1.5ATR"]
L = []
p = L.append


def block_atr():
    """Prior session's mean 1-minute true range WITHIN each clock block, bps.

    Causal: session D's label comes from session D-1. Added as a diagnostic
    after section 3 showed the frozen session-level unit cannot vary within a
    day. No frozen definition is replaced.
    """
    d = pd.read_parquet(Path(__file__).resolve().parents[2]
                        / "data/intraday_long/QQQ_1m.parquet",
                        columns=["timestamp", "high", "low", "close"])
    d["ts"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("ts").reset_index(drop=True)
    d["day"] = d.ts.dt.normalize()
    d["m"] = (d.ts.dt.hour * 60 + d.ts.dt.minute) - 570
    bnd = {"open": (0, 30), "morning": (30, 120),
           "midday": (120, 270), "close": (270, 391)}
    d["blk"] = pd.cut(d["m"], bins=[0, 30, 120, 270, 391], right=False,
                      labels=["open", "morning", "midday", "close"])
    pc = d.groupby("day")["close"].shift()
    tr = np.maximum(d.high - d.low,
                    np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    d["tr_bps"] = 1e4 * tr / d.close
    g = (d.dropna(subset=["blk"]).groupby(["day", "blk"], observed=True)
         ["tr_bps"].mean().reset_index().rename(columns={"tr_bps": "batr"}))
    g = g.sort_values(["blk", "day"])
    g["batr"] = g.groupby("blk", observed=True)["batr"].shift()   # CAUSAL
    g["blk"] = g["blk"].astype(str)
    return g.dropna()


def q(s, v):
    s = pd.Series(s).dropna()
    return float(np.percentile(s, v)) if len(s) else np.nan


def main():
    E = pd.read_parquet(OUT / "rp009_qqq_exc.parquet")
    B = pd.read_parquet(OUT / "rp009_qqq_bar.parquet")
    NE = pd.read_parquet(OUT / "rp009_nq_exc.parquet")
    NB = pd.read_parquet(OUT / "rp009_nq_bar.parquet")
    TK = pd.read_parquet(OUT / "rp009_nq_tick.parquet")

    H = E[E.hz.isin([str(h) for h in S.HZ] + ["close"])].copy()
    X = E[E.hz.str.startswith("exc")].copy()
    NH = NE[NE.hz.isin([str(h) for h in S.HZ] + ["close"])].copy()

    p("RP-009 STAGE 1 -- TIME-OF-DAY OPPORTUNITY MAP. BARRIER GEOMETRY ONLY.")
    p("  No strategy P&L, expectancy, profit factor, drawdown, allocator,")
    p("  entry pattern, directional rule or prop-evaluation simulation.")
    p("")
    p("  QQQ provides the PRIMARY long-sample evidence.")
    p("  NQ provides EXPLORATORY instrument-native confirmation only.")
    p("  44 NQ sessions cannot support a standalone commercial verdict.")
    p("  QQQ results cannot validate an MNQ strategy.")
    p("")

    # ---------------------------------------------------------- 1. counts
    p("=== 1. DATA AND SAMPLE COUNTS ===")
    p(f"  QQQ calendar sessions 1421 | excluded: <300 bars 1, no prior "
      f"session 1 | USED {H.day.nunique()}")
    p(f"  QQQ observations: timestamps {H.ts.nunique()} x sessions "
      f"{H.day.nunique()} = {H.day.nunique()*H.ts.nunique()}")
    p(f"  QQQ excursion rows {len(E)} | barrier rows {len(B)}")
    p(f"  NQ full 0.25 sessions {NH.day.nunique()} | excursion rows {len(NE)}"
      f" | barrier rows {len(NB)} | tick-calibration rows {len(TK)}")
    p("")
    p("  HORIZON AVAILABILITY -- horizons past the cash close are marked")
    p("  unavailable, never substituted with a shorter window.")
    p(f"  {'timestamp':<11}{'avail min':>10}" +
      "".join(f"{('h'+str(h)):>9}" for h in S.HZ) + f"{'to close':>10}")
    for t in TSL:
        g = H[H.ts == t]
        av = int(g.avail.median())
        row = f"  {t:<11}{av:>10}"
        for h in S.HZ:
            k = g[(g.hz == str(h))]
            row += f"{int(k.ok.sum()):>9}"
        row += f"{int(g[g.hz=='close'].ok.sum()):>10}"
        p(row)
    p("")

    # ------------------------------------------- 2. absolute gradient
    p("=== 2. ABSOLUTE EXCURSION GRADIENT (bps) -- medians, [p25, p75] ===")
    p("  Long and short measured symmetrically. Long MFE = short MAE by")
    p("  construction, so the pooled geometry is one distribution seen twice.")
    p("")
    for h in ["30", "60", "close"]:
        p(f"  horizon {h}:")
        p(f"  {'timestamp':<11}{'n':>6}{'MFE med':>10}{'[p25':>8}{'p75]':>8}"
          f"{'MAE med':>10}{'[p25':>8}{'p75]':>8}{'range':>9}")
        for t in TSL:
            g = H[(H.ts == t) & (H.hz == h) & H.ok]
            if not len(g):
                p(f"  {t:<11}{'-- unavailable --':>30}")
                continue
            p(f"  {t:<11}{len(g):>6}{g.L_mfe.median():>10.2f}"
              f"{q(g.L_mfe,25):>8.2f}{q(g.L_mfe,75):>8.2f}"
              f"{g.L_mae.median():>10.2f}{q(g.L_mae,25):>8.2f}"
              f"{q(g.L_mae,75):>8.2f}"
              f"{(g.L_mfe+g.L_mae).median():>9.2f}")
        p("")

    # ------------------------------------------- 3. ATR gradient
    p("=== 3. ATR-NORMALISED EXCURSION GRADIENT (ATR1m units) ===")
    p("  THE CONTROL THAT MATTERS: if the day's gradient is pure scale, these")
    p("  numbers are flat where section 2's are not.")
    p("")
    for h in ["30", "60", "close"]:
        p(f"  horizon {h}:")
        p(f"  {'timestamp':<11}{'n':>6}{'MFE med':>10}{'[p25':>8}{'p75]':>8}"
          f"{'MAE med':>10}{'range':>9}{'ATR bps':>10}")
        for t in TSL:
            g = H[(H.ts == t) & (H.hz == h) & H.ok]
            if not len(g):
                p(f"  {t:<11}{'-- unavailable --':>30}")
                continue
            p(f"  {t:<11}{len(g):>6}{g.L_mfe_a.median():>10.3f}"
              f"{q(g.L_mfe_a,25):>8.3f}{q(g.L_mfe_a,75):>8.3f}"
              f"{g.L_mae_a.median():>10.3f}"
              f"{(g.L_mfe_a+g.L_mae_a).median():>9.3f}"
              f"{g.atr_bps.median():>10.2f}")
        p("")
    # ---- BLOCK-LOCAL ATR, added after seeing section 3
    p("  *** A DEFECT IN MY OWN FROZEN UNIT, AND THE FIX ***")
    p("  ATR1m as pre-registered is the PRIOR SESSION'S MEAN 1-minute true")
    p("  range -- ONE NUMBER PER SESSION. Dividing all fourteen timestamps by")
    p("  the same constant cannot flatten an intraday gradient; it rescales")
    p("  every timestamp identically. The frozen unit is therefore")
    p("  MATHEMATICALLY INCAPABLE of answering 'does ATR normalisation remove")
    p("  the opening's advantage'. That is a logical fact, not a data-dependent")
    p("  one, and I should have seen it before running.")
    p("")
    p("  The arm below normalises by the PRIOR SESSION'S ATR MEASURED OVER THE")
    p("  SAME CLOCK BLOCK -- causal, and the construction RP-008 already used.")
    p("  It is a diagnostic added after the fact and it can only REDUCE the")
    p("  opening's apparent advantage, never inflate it, because the open is")
    p("  the block with the largest local ATR.")
    p("")
    bl = block_atr()
    Hb = H.merge(bl, on=["day", "blk"], how="left")
    Hb = Hb[Hb.ok & Hb.batr.notna()].copy()
    Hb["mfe_b"] = Hb.L_mfe / Hb.batr
    Hb["mae_b"] = Hb.L_mae / Hb.batr
    p("  BLOCK-LOCAL ATR NORMALISATION -- 60-minute horizon")
    p(f"  {'block':<10}{'n':>7}{'local ATR bps':>15}{'MFE/localATR':>14}"
      f"{'MAE/localATR':>14}{'ratio vs open':>15}")
    g0 = Hb[(Hb.blk == 'open') & (Hb.hz == '60')]
    b0 = g0.mfe_b.median()
    for b in BLK:
        g = Hb[(Hb.blk == b) & (Hb.hz == "60")]
        if not len(g):
            continue
        p(f"  {b:<10}{len(g):>7}{g.batr.median():>15.3f}"
          f"{g.mfe_b.median():>14.3f}{g.mae_b.median():>14.3f}"
          f"{g.mfe_b.median()/b0:>15.3f}")
    p("")
    p("  BLOCK SUMMARY -- 60-minute horizon")
    p(f"  {'block':<10}{'n':>7}{'MFE bps':>10}{'MAE bps':>10}"
      f"{'MFE ATR':>10}{'MAE ATR':>10}{'ratio vs open (bps)':>21}"
      f"{'ratio vs open (ATR)':>21}")
    base = H[(H.blk == "open") & (H.hz == "60") & H.ok]
    b_bps, b_atr = base.L_mfe.median(), base.L_mfe_a.median()
    for b in BLK:
        g = H[(H.blk == b) & (H.hz == "60") & H.ok]
        if not len(g):
            continue
        p(f"  {b:<10}{len(g):>7}{g.L_mfe.median():>10.2f}"
          f"{g.L_mae.median():>10.2f}{g.L_mfe_a.median():>10.3f}"
          f"{g.L_mae_a.median():>10.3f}"
          f"{g.L_mfe.median()/b_bps:>21.3f}"
          f"{g.L_mfe_a.median()/b_atr:>21.3f}")
    p("")

    # ------------------------------------------- 4. time to excursion
    p("=== 4. TIME TO EXCURSION, and reach rates to the cash close ===")
    p(f"  {'timestamp':<11}{'level':>7}{'n':>7}{'med min up':>12}"
      f"{'p75':>7}{'%up first':>11}{'%up ever':>10}{'%dn ever':>10}")
    for t in TSL:
        for e in S.EXC:
            g = X[(X.ts == t) & (X.hz == f"exc{e}")]
            if not len(g):
                continue
            p(f"  {t:<11}{e:>7}{len(g):>7}{q(g.t_up,50):>12.0f}"
              f"{q(g.t_up,75):>7.0f}{100*g.up_first.mean():>11.1f}"
              f"{100*g.up_any.mean():>10.1f}{100*g.dn_any.mean():>10.1f}")
    p("")

    # ------------------------------------------- 5. barrier geometry
    p("=== 5. BARRIER GEOMETRY BY RISK CONTAINER ===")
    p("  Driftless baseline P(+MR before -1R) = 1/(1+M):")
    p("    M=1.0 -> 50.0%   M=1.5 -> 40.0%   M=2.0 -> 33.3%")
    p("  MATCHING OR BEATING THE BASELINE IS NOT EVIDENCE OF DIRECTIONAL EDGE.")
    p("  It is geometry. A directional entry rule would still be required.")
    p("")
    for M in S.MULT:
        p(f"  target {M}R   (baseline {100/(1+M):.1f}%)")
        p(f"  {'block':<10}{'container':<10}{'n':>7}{'cost%risk':>11}"
          f"{'P(tgt 1st)':>12}{'excl amb':>10}{'amb%':>7}"
          f"{'med min +':>11}{'med min -':>11}{'%unres':>9}")
        for b in BLK:
            for c in CONT:
                g = B[(B.blk == b) & (B.cont == c) & (B.M == M)]
                if len(g) < 50:
                    continue
                res = g[g.out != 0]
                ex = g[~g.amb]
                exr = ex[ex.out != 0]
                p(f"  {b:<10}{c:<10}{len(g):>7}{g.cost_pct.median():>11.1f}"
                  f"{100*(res.out > 0).mean():>12.1f}"
                  f"{100*(exr.out > 0).mean():>10.1f}"
                  f"{100*g.amb.mean():>7.1f}"
                  f"{q(g[g.out>0].bar,50):>11.0f}"
                  f"{q(g[g.out<0].bar,50):>11.0f}"
                  f"{100*(g.out == 0).mean():>9.1f}")
        p("")

    # ------------------------------------------- 6. cost viability
    p("=== 6. COST VIABILITY -- NQ cost 0.68 bps, 2.0 NQ points ===")
    p(f"  {'block':<10}{'container':<10}{'risk bps':>10}{'cost%risk':>11}"
      f"{'med MFE60':>11}{'cost%MFE':>10}{'med resolved':>14}"
      f"{'cost%resolved':>15}{'min gross edge':>16}")
    for b in BLK:
        mfe = H[(H.blk == b) & (H.hz == "60") & H.ok].L_mfe.median()
        for c in CONT:
            g = B[(B.blk == b) & (B.cont == c) & (B.M == 1.0)]
            if len(g) < 50:
                continue
            risk = g.risk_bps.median()
            resolved = risk          # a 1R resolution moves exactly 1R
            p(f"  {b:<10}{c:<10}{risk:>10.2f}{g.cost_pct.median():>11.1f}"
              f"{mfe:>11.2f}{100*S.COST_BPS/mfe:>10.1f}"
              f"{resolved:>14.2f}{100*S.COST_BPS/resolved:>15.1f}"
              f"{S.COST_BPS:>15.2f}b")
    p("")
    p("  'min gross edge' is the gross movement, in bps, a round turn must")
    p("  recover before anything is left. It is 0.68 bps everywhere by")
    p("  construction; what changes is what fraction of the available")
    p("  excursion that represents.")
    p("")

    # ------------------------------------------- 7. truncation
    p("=== 7. HOLDING-TIME TRUNCATION ===")
    p(f"  {'block':<10}{'container':<10}{'M':>5}{'%unresolved at close':>22}"
      f"{'med min to resolve':>20}")
    for b in BLK:
        for c in ("1.0ATR", "1.5ATR", "30NQpt"):
            for M in S.MULT:
                g = B[(B.blk == b) & (B.cont == c) & (B.M == M)]
                if len(g) < 50:
                    continue
                p(f"  {b:<10}{c:<10}{M:>5}{100*(g.out == 0).mean():>22.1f}"
                  f"{q(g[g.out!=0].bar,50):>20.0f}")
    p("")

    # ------------------------------------------- 8. tick calibration
    p("=== 8. TICK-ORDER CALIBRATION -- 44 NQ sessions, EXPLORATORY ===")
    p("  The same dates resolved two ways: true tick order from the tape, and")
    p("  the one-minute adverse-first convention. The 44 sessions do not")
    p("  overturn the QQQ map; they calibrate what the convention costs.")
    p("")
    p(f"  {'M':>5}{'n':>8}{'bar P(tgt)':>12}{'tick P(tgt)':>13}"
      f"{'difference':>12}{'amb%':>8}{'disagree%':>11}")
    for M in S.MULT:
        g = TK[TK.M == M]
        rb = g[g.bar_out != 0]
        rt = g[g.tick_out != 0]
        dis = (g.bar_out != g.tick_out).mean()
        p(f"  {M:>5}{len(g):>8}{100*(rb.bar_out > 0).mean():>12.1f}"
          f"{100*(rt.tick_out > 0).mean():>13.1f}"
          f"{100*((rt.tick_out>0).mean()-(rb.bar_out>0).mean()):>+12.1f}"
          f"{100*g.amb.mean():>8.1f}{100*dis:>11.1f}")
    p("")
    p("  on AMBIGUOUS bars only -- where the convention actually binds:")
    a = TK[TK.amb]
    if len(a):
        p(f"    n={len(a)}  the convention calls 100.0% of them adverse; the")
        p(f"    tape says {100*(a.tick_out>0).mean():.1f}% were actually the "
          f"target.")
    p("")
    p("  NQ native excursion, 60-minute horizon (exploratory):")
    p(f"  {'block':<10}{'n':>6}{'MFE pts':>10}{'MAE pts':>10}{'MFE ATR':>10}"
      f"{'MAE ATR':>10}")
    for b in BLK:
        g = NH[(NH.blk == b) & (NH.hz == "60") & NH.ok]
        if not len(g):
            continue
        px = S.NQ_PX
        p(f"  {b:<10}{len(g):>6}{g.L_mfe.median()*px/1e4:>10.1f}"
          f"{g.L_mae.median()*px/1e4:>10.1f}{g.L_mfe_a.median():>10.3f}"
          f"{g.L_mae_a.median():>10.3f}")
    p("")

    # ------------------------------------------- 9. yearly
    p("=== 9. YEARLY STABILITY -- median MFE, 60-minute horizon ===")
    yrs = sorted(H.yr.unique())
    p(f"  {'block':<10}" + "".join(f"{y:>9}" for y in yrs) + "   units")
    for b in BLK:
        r1 = f"  {b:<10}"
        r2 = f"  {'':<10}"
        for y in yrs:
            g = H[(H.blk == b) & (H.hz == "60") & H.ok & (H.yr == y)]
            r1 += f"{g.L_mfe.median():>9.2f}" if len(g) else f"{'-':>9}"
            r2 += f"{g.L_mfe_a.median():>9.3f}" if len(g) else f"{'-':>9}"
        p(r1 + "   bps")
        p(r2 + "   ATR")
    p("")
    p("  ratio of close-block to open-block median MFE, by year:")
    p(f"  {'':<10}" + "".join(f"{y:>9}" for y in yrs))
    rb, ra = f"  {'bps':<10}", f"  {'ATR':<10}"
    for y in yrs:
        o = H[(H.blk == "open") & (H.hz == "60") & H.ok & (H.yr == y)]
        c = H[(H.blk == "close") & (H.hz == "60") & H.ok & (H.yr == y)]
        rb += f"{c.L_mfe.median()/o.L_mfe.median():>9.3f}" if len(o) and len(c) else f"{'-':>9}"
        ra += f"{c.L_mfe_a.median()/o.L_mfe_a.median():>9.3f}" if len(o) and len(c) else f"{'-':>9}"
    p(rb)
    p(ra)
    p("")

    # ------------------------------------------- appendix
    p("=== APPENDIX -- formal detail ===")
    p("  Long/short symmetry check (should be exact by construction):")
    for h in ["30", "60", "close"]:
        g = H[(H.hz == h) & H.ok]
        p(f"    h{h:<6} long MFE median {g.L_mfe.median():.4f} == short MAE "
          f"median {g.S_mae.median():.4f}   "
          f"max abs diff {float((g.L_mfe-g.S_mae).abs().max()):.2e}")
    p("")
    p("  Directional imbalance (diagnostic only, NOT a strategy):")
    p(f"  {'block':<10}{'n':>7}{'med MFE':>10}{'med MAE':>10}"
      f"{'MFE-MAE':>10}{'% MFE>MAE':>11}")
    for b in BLK:
        g = H[(H.blk == b) & (H.hz == "60") & H.ok]
        p(f"  {b:<10}{len(g):>7}{g.L_mfe.median():>10.2f}"
          f"{g.L_mae.median():>10.2f}"
          f"{g.L_mfe.median()-g.L_mae.median():>10.2f}"
          f"{100*(g.L_mfe > g.L_mae).mean():>11.1f}")
    p("")
    p("  Ambiguous-bar rate by container and target (QQQ):")
    p(f"  {'container':<10}" + "".join(f"{('M='+str(M)):>9}" for M in S.MULT))
    for c in CONT:
        p(f"  {c:<10}" + "".join(
            f"{100*B[(B.cont==c)&(B.M==M)].amb.mean():>9.2f}" for M in S.MULT))
    p("")

    txt = "\n".join(L)
    print(txt)
    (OUT / "rp009_stage1_output.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    main()
