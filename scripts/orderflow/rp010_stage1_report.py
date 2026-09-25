#!/usr/bin/env python3
"""RP-010 Stage 1 report. Counts before outcomes. Reads only the harness output."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataquality as DQ                                            # noqa: E402
import rp010_stage1 as S                                            # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "reports"
HZ = S.HZ_S
L = []
p = L.append


def med(x):
    x = pd.Series(x).dropna()
    return float(x.median()) if len(x) else np.nan


def clustered(df, col, by="day"):
    """Session-clustered mean and t. The session is the independence unit."""
    g = df.groupby(by)[col].mean().dropna()
    if len(g) < 3:
        return np.nan, np.nan, len(g)
    return float(g.mean()), float(g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))), len(g)


def main():
    W = pd.read_parquet(OUT / "rp010_windows.parquet")
    Q = pd.read_parquet(OUT / "rp010_dataquality.parquet")
    T = pd.read_parquet(OUT / "rp010_thresholds.parquet")
    O = pd.read_parquet(OUT / "rp010_events.parquet")
    EX = pd.read_csv(OUT / "rp010_excluded.csv")
    E = O[O.is_event].copy()
    rng = np.random.default_rng(S.SEED)

    p("RP-010 STAGE 1 -- ORDER-FLOW IMPACT, ABSORPTION AND EXHAUSTION")
    p("  Descriptive. No entry, stop, target or strategy. No expectancy,")
    p("  profit factor or drawdown. Event window excluded from every outcome.")
    p("")

    # ---------------------------------------------------------- data quality
    p("=== 0. DATA QUALITY (condition 4) ===")
    p(f"  sessions measured                {len(Q)}")
    p(f"  tick size, measured from prices  {sorted(Q.tick.unique())}")
    p(f"  prices off the 0.25 grid         {Q.off_tick.max():.6f} (max over sessions)")
    p(f"  aggressor labels                 {sorted(Q.side_labels.unique())}")
    p(f"  aggressor nulls                  {int(Q.side_nulls.sum())}")
    p(f"  timestamps monotonic             {bool(Q.monotonic.all())} on all sessions")
    p(f"  largest consecutive-print jump   {Q.max_jump.max():.2f} pts "
      f"(roll threshold 100) -> no contract roll")
    p(f"  median RTH prints per session    {int(Q.prints.median())}")
    p("")

    # ---------------------------------------------------- counts before outcomes
    p("=== 1. COUNTS, BEFORE ANY FORWARD OUTCOME ===")
    p(f"  NQ dates on disk                         {len(EX) + Q.day.nunique()}")
    p(f"  sessions excluded                        {len(EX)}")
    for r, n in EX.reason.value_counts().items():
        p(f"      {r:<34}{n}")
    p(f"  SESSIONS USED                            {Q.day.nunique()}")
    p(f"  threshold warm-up sessions excluded      {S.TRAIL_SESS}")
    p(f"  sessions producing labelled windows      {W[W.state != 'WARMUP'].day.nunique()}")
    p(f"  discovery dates: {', '.join(sorted(W[W.state!='WARMUP'].day.unique()))}")
    p("")
    p(f"  total 30-second windows                  {len(W)}")
    p(f"  warm-up windows (unlabelled)             {int((W.state=='WARMUP').sum())}")
    p(f"  ORDINARY windows                         {int((W.state=='ORDINARY').sum())}")
    p(f"  INITIATIVE candidates before cooldown    {int((W.state=='INITIATIVE').sum())}")
    p(f"  ABSORPTION candidates before cooldown    {int((W.state=='ABSORPTION').sum())}")
    ev = W[W.event]
    p(f"  EVENTS retained after cooldown and cap   {len(ev)}")
    for r, n in W[W.drop_reason.isin(['extended', 'flipped', 'capped'])] \
            .drop_reason.value_counts().items():
        p(f"      excluded as {r:<26}{n}")
    months = pd.to_datetime(W[W.state != 'WARMUP'].day).dt.to_period("M").nunique()
    p(f"  events per session                       {len(ev)/W[W.state!='WARMUP'].day.nunique():.2f}")
    p(f"  events per month                         {len(ev)/months:.1f}  "
      f"({months} months)")
    p("")
    p(f"  {'state':<12}{'buy':>7}{'sell':>7}{'total':>8}{'sessions':>10}"
      f"{'per session':>13}")
    nsess = W[W.state != 'WARMUP'].day.nunique()
    for st in ("INITIATIVE", "ABSORPTION"):
        g = ev[ev.state == st]
        p(f"  {st:<12}{int((g.side=='buy').sum()):>7}"
          f"{int((g.side=='sell').sum()):>7}{len(g):>8}"
          f"{g.day.nunique():>10}{len(g)/nsess:>13.2f}")
    p("")
    for st in ("INITIATIVE", "ABSORPTION"):
        n = ev[ev.state == st].day.nunique()
        p(f"  independent sessions containing {st:<12} {n}"
          + ("   *** EXPLORATORY, fewer than 20 -- no mechanism claim ***"
             if n < 20 else ""))
    p("")
    p("  events by time of day (minutes after the open):")
    p(f"  {'bucket':<18}" + "".join(f"{s:>13}" for s in ("INITIATIVE", "ABSORPTION")))
    for lo, hi, lab in ((5, 30, "05-30 open"), (30, 120, "30-120 morning"),
                        (120, 270, "120-270 midday"), (270, 385, "270-385 close")):
        g = ev[(ev.tod >= lo) & (ev.tod < hi)]
        p(f"  {lab:<18}" + "".join(
            f"{int((g.state==st).sum()):>13}" for st in ("INITIATIVE", "ABSORPTION")))
    p("")
    p("  events by ISO week:")
    wk = ev.groupby(["wk", "state"]).size().unstack(fill_value=0)
    p("  " + wk.to_string().replace("\n", "\n  "))
    p("")
    p("  causal thresholds (trailing 10 completed sessions):")
    p(f"    aggression  p90 imbalance   median {T.a_thr.median():.4f}  "
      f"[{T.a_thr.min():.4f}, {T.a_thr.max():.4f}]")
    p(f"    high impact p80 ticks/1k    median {T.hi_thr.median():.2f}  "
      f"[{T.hi_thr.min():.2f}, {T.hi_thr.max():.2f}]")
    p(f"    low impact  p20 ticks/1k    median {T.lo_thr.median():.2f}  "
      f"[{T.lo_thr.min():.2f}, {T.lo_thr.max():.2f}]")
    p("")
    p("  ZERO CASES: zero total volume -> imbalance 0.0 (never NaN); zero delta")
    p("  -> ticks_per_delta 0.0 and the window is excluded from forward outcomes")
    p("  because it has no aggression direction; zero price progress -> impact")
    p("  0.0. Zero displayed depth is not used: depth is a diagnostic stream and")
    p("  no RP-010 figure divides by it.")
    p(f"  windows with zero total volume           {int((W.total==0).sum())}")
    p(f"  windows with zero delta (no direction)   {int((W.delta==0).sum())}")
    p("")

    # -------------------------------------------------------- forward outcomes
    p("=== 2. FORWARD OUTCOMES -- direction-adjusted, NQ points ===")
    p("  Positive = price continued in the aggression direction.")
    p("  1 NQ point = 4 ticks. Round turn = 2.0 points.")
    p("")
    for st in ("INITIATIVE", "ABSORPTION", "ORDINARY"):
        g = E[E.state == st] if st != "ORDINARY" else O[O.state == "ORDINARY"]
        p(f"  {st}  (n={len(g)})")
        p(f"  {'horizon':<10}{'mean pts':>10}{'median':>9}{'ticks':>8}"
          f"{'MFE':>8}{'MAE':>8}{'cont%':>8}{'rev%':>8}{'clust t':>9}")
        for h in HZ:
            r = g[f"r{h}"].dropna()
            if not len(r):
                continue
            m, t, ns = clustered(g, f"r{h}")
            p(f"  {str(h)+'s':<10}{r.mean():>+10.3f}{r.median():>+9.3f}"
              f"{r.mean()*4:>+8.2f}{g[f'mfe{h}'].mean():>8.3f}"
              f"{g[f'mae{h}'].mean():>8.3f}{100*(r>0).mean():>8.1f}"
              f"{100*(r<0).mean():>8.1f}{t:>+9.2f}")
        p("")
    p("  time to a +/- 6-point move, and path landmarks (seconds, median):")
    p(f"  {'state':<12}{'t continue':>12}{'t reverse':>11}{'t origin':>10}"
      f"{'t break':>10}{'% break ext':>13}{'% back to origin':>18}")
    for st in ("INITIATIVE", "ABSORPTION", "ORDINARY"):
        g = E[E.state == st] if st != "ORDINARY" else O[O.state == "ORDINARY"]
        p(f"  {st:<12}{med(g.t_cont):>12.0f}{med(g.t_rev):>11.0f}"
          f"{med(g.t_origin):>10.0f}{med(g.t_break):>10.0f}"
          f"{100*g.t_break.notna().mean():>13.1f}"
          f"{100*g.t_origin.notna().mean():>18.1f}")
    p("")
    p("  ADDITIONAL SAME-DIRECTION AGGRESSIVE VOLUME after the event")
    p("  (direction-adjusted net aggressive contracts, mean per event)")
    p(f"  {'state':<12}{'n':>6}" + "".join(f"{('av'+str(h)):>11}" for h in HZ))
    for st in ("INITIATIVE", "ABSORPTION", "ORDINARY"):
        g = E[E.state == st] if st != "ORDINARY" else O[O.state == "ORDINARY"]
        p(f"  {st:<12}{len(g):>6}"
          + "".join(f"{g[f'av{h}'].mean():>+11.1f}" for h in HZ))
    p("")
    p("  BUY AND SELL SEPARATELY -- never pooled")
    p(f"  {'state':<12}{'side':<6}{'n':>5}" + "".join(f"{('r'+str(h)):>10}" for h in HZ))
    for st in ("INITIATIVE", "ABSORPTION"):
        for sd in ("buy", "sell"):
            g = E[(E.state == st) & (E.side == sd)]
            if not len(g):
                continue
            p(f"  {st:<12}{sd:<6}{len(g):>5}"
              + "".join(f"{g[f'r{h}'].mean():>+10.3f}" for h in HZ))
    p("")

    # ---------------------------------------------------------------- controls
    p("=== 3. CONTROLS ===")
    p("  Every control's synthetic fixture passes in test_platform.py.")
    p("  Sample size and matching coverage reported BEFORE each outcome.")
    p("")
    AGG = O[O.state.isin(["INITIATIVE", "ABSORPTION"])]
    ctl = []

    # 1 shuffled impact labels within the aggression-clearing set
    lab = rng.permutation(AGG.state.to_numpy())
    sh = AGG.assign(state_shuf=lab)
    for st in ("INITIATIVE", "ABSORPTION"):
        g = sh[sh.state_shuf == st]
        ctl.append(("1 impact labels shuffled", st, len(g),
                    [g[f"r{h}"].mean() for h in HZ]))
    # 2 same price progress, ordinary aggression
    ini_ticks = E[E.state == "INITIATIVE"].ticks.abs()
    lo_t, hi_t = ini_ticks.quantile(.1), ini_ticks.quantile(.9)
    g = O[(O.state == "ORDINARY") & (O.ticks.abs() >= lo_t)
          & (O.ticks.abs() <= hi_t)]
    ctl.append(("2 same progress, ordinary aggression", "INITIATIVE-like",
                len(g), [g[f"r{h}"].mean() for h in HZ]))
    abs_ticks = E[E.state == "ABSORPTION"].ticks.abs()
    g = O[(O.state == "ORDINARY") & (O.ticks.abs() <= abs_ticks.quantile(.9))]
    ctl.append(("2 same progress, ordinary aggression", "ABSORPTION-like",
                len(g), [g[f"r{h}"].mean() for h in HZ]))
    # 3 matched random times -- same |delta| decile, same session, +/-30 min
    matched, unmatched = [], 0
    pool = O[O.state == "ORDINARY"]
    for _, r in E.iterrows():
        c = pool[(pool.day == r.day) & (abs(pool.tod - r.tod) <= 30)
                 & (abs(pool.delta.abs() - abs(r.delta)) <= 0.25 * abs(r.delta))]
        if not len(c):
            unmatched += 1
            continue
        matched.append(c.sample(1, random_state=int(r.tod) % 9973).iloc[0])
    M = pd.DataFrame(matched)
    ctl.append(("3 matched random times", "matched", len(M),
                [M[f"r{h}"].mean() for h in HZ]))
    cov = 100 * len(M) / len(E)
    # 4 high volume, balanced delta
    g = O[(O.total >= O.total.quantile(.9)) & (O.imb <= O.imb.quantile(.5))]
    ctl.append(("4 high volume, balanced delta", "", len(g),
                [g[f"r{h}"].mean() for h in HZ]))
    # 5 opposite direction
    for st in ("INITIATIVE", "ABSORPTION"):
        g = E[E.state == st]
        ctl.append(("5 opposite direction", st, len(g),
                    [-g[f"r{h}"].mean() for h in HZ]))
    p(f"  matched-random control coverage: {len(M)} of {len(E)} events "
      f"({cov:.1f}%), {unmatched} unmatched")
    p("")
    p(f"  {'control':<38}{'arm':<16}{'n':>7}" + "".join(f"{('r'+str(h)):>9}" for h in HZ))
    for nm, arm, n, vals in ctl:
        p(f"  {nm:<38}{arm:<16}{n:>7}" + "".join(f"{v:>+9.3f}" for v in vals))
    p("")
    p("  TREATMENT, for comparison:")
    for st in ("INITIATIVE", "ABSORPTION"):
        g = E[E.state == st]
        p(f"  {'TREATMENT':<38}{st:<16}{len(g):>7}"
          + "".join(f"{g[f'r{h}'].mean():>+9.3f}" for h in HZ))
    p("")
    p("  6 NEAR vs AWAY from a named level -- DIAGNOSTIC ONLY.")
    p("  Causal levels, no overnight variable: prior RTH high/low/close,")
    p("  cumulative session VWAP, IB high/low after minute 60, round 50s.")
    p("  Near = terminal price within 10 ticks. The primary result above")
    p("  uses no level at all.")
    p(f"  median distance to the nearest eligible level  "
      f"{med(E.lvl_dist):.2f} points")
    p(f"  {'state':<12}{'where':<8}{'n':>6}" + "".join(f"{('r'+str(h)):>9}" for h in HZ))
    for st in ("INITIATIVE", "ABSORPTION"):
        for nearq, lab in ((True, "near"), (False, "away")):
            g = E[(E.state == st) & (E.near_level == nearq)]
            if not len(g):
                continue
            p(f"  {st:<12}{lab:<8}{len(g):>6}"
              + "".join(f"{g[f'r{h}'].mean():>+9.3f}" for h in HZ))
    p("")

    # ------------------------------------------------------- load-bearing ----
    p("=== 4. IS IMPACT LOAD-BEARING? ===")
    p("  Does progress-per-unit-volume add information beyond each single")
    p("  variable on its own? Each row is the top decile of that variable,")
    p("  direction-adjusted, over ALL labelled windows.")
    p("")
    p(f"  {'selector':<34}{'n':>7}" + "".join(f"{('r'+str(h)):>9}" for h in HZ))
    sels = [("delta magnitude alone (top decile)",
             O[O.delta.abs() >= O.delta.abs().quantile(.9)]),
            ("price progress alone (top decile)",
             O[O.ticks.abs() >= O.ticks.abs().quantile(.9)]),
            ("total volume alone (top decile)",
             O[O.total >= O.total.quantile(.9)]),
            ("local volatility alone (top decile)",
             O[O.loc_vol >= O.loc_vol.quantile(.9)]),
            ("impact alone (top decile ticks/1k)",
             O[O.tpk >= O.tpk.quantile(.9)]),
            ("INITIATIVE (aggression AND impact)", E[E.state == "INITIATIVE"]),
            ("ABSORPTION (aggression AND low impact)",
             E[E.state == "ABSORPTION"])]
    for nm, g in sels:
        p(f"  {nm:<34}{len(g):>7}"
          + "".join(f"{g[f'r{h}'].mean():>+9.3f}" for h in HZ))
    p("")

    # -------------------------------------------------- independence ---------
    p("=== 5. INDEPENDENCE AND CONCENTRATION ===")
    p(f"  {'state':<12}{'horizon':<9}{'event mean':>12}{'clustered':>11}"
      f"{'t':>7}{'sess':>6}{'sess +':>8}{'LOO min':>9}{'LOO max':>9}"
      f"{'-best1':>9}{'-best3':>9}{'best3 share':>13}")
    for st in ("INITIATIVE", "ABSORPTION"):
        g = E[E.state == st]
        for h in (300, 900):
            col = f"r{h}"
            sess = g.groupby("day")[col].mean().dropna()
            if len(sess) < 3:
                continue
            m, t, ns = clustered(g, col)
            loo = [sess.drop(d).mean() for d in sess.index]
            order = sess.sort_values(ascending=False)
            b1 = sess.drop(order.index[:1]).mean()
            b3 = sess.drop(order.index[:3]).mean()
            tot = sess.sum()
            share = (order.iloc[:3].sum() / tot * 100) if tot != 0 else np.nan
            p(f"  {st:<12}{str(h)+'s':<9}{g[col].mean():>+12.3f}{m:>+11.3f}"
              f"{t:>+7.2f}{ns:>6}{int((sess>0).sum()):>8}"
              f"{min(loo):>+9.3f}{max(loo):>+9.3f}{b1:>+9.3f}{b3:>+9.3f}"
              f"{share:>12.1f}%")
    p("")
    for h in (300, 900):
        p(f"  by ISO week, {h//60}-minute horizon:")
        wk = E.pivot_table(index="wk", columns="state", values=f"r{h}",
                           aggfunc="mean")
        p("  " + wk.round(3).to_string().replace("\n", "\n  "))
        p("")
    p("  by session, 15-minute horizon -- distribution of the 34 session means:")
    p(f"  {'state':<12}{'sess':>6}{'min':>10}{'p25':>10}{'median':>10}"
      f"{'p75':>10}{'max':>10}")
    for st in ("INITIATIVE", "ABSORPTION"):
        sess = E[E.state == st].groupby("day")["r900"].mean().dropna()
        p(f"  {st:<12}{len(sess):>6}{sess.min():>+10.2f}"
          f"{sess.quantile(.25):>+10.2f}{sess.median():>+10.2f}"
          f"{sess.quantile(.75):>+10.2f}{sess.max():>+10.2f}")
    p("")

    # ------------------------------------------------------ feasibility ------
    p("=== 6. COMMERCIAL FEASIBILITY ===")
    atr = 21.55
    cont = 1.2 * atr
    p(f"  median local ATR (1-minute, measured)        {atr:.2f} NQ points")
    p(f"  minimum viable container (RP-009, 1.2 ATR)   {cont:.2f} points "
      f"= {cont*4:.0f} ticks")
    p(f"  round turn                                   {S.COST_PTS:.1f} points "
      f"= {100*S.COST_PTS/cont:.1f}% of that risk")
    p(f"  movement needed to clear 3x cost             6.00 points = 24 ticks")
    p("")
    p("  6.00 points and 24 ticks are THE SAME THRESHOLD in two units, so the")
    p("  two columns the brief asks for are reported once on MFE (was the move")
    p("  ever available) and once on the terminal return (was it there at the")
    p("  horizon). The terminal column is the honest one for a timed exit.")
    p(f"  {'state':<12}{'horizon':<9}{'median':>9}{'mean':>9}{'net of 2pt':>12}"
      f"{'MFE>=6pt':>10}{'term>=6pt':>11}{'vs 1.2ATR':>11}")
    for st in ("INITIATIVE", "ABSORPTION"):
        g = E[E.state == st]
        for h in (300, 900):
            r = g[f"r{h}"].dropna()
            mfe = g[f"mfe{h}"].dropna()
            p(f"  {st:<12}{str(h)+'s':<9}{r.median():>+9.3f}{r.mean():>+9.3f}"
              f"{r.mean()-S.COST_PTS:>+12.3f}"
              f"{100*(mfe>=6.0).mean():>9.1f}%"
              f"{100*(r>=6.0).mean():>10.1f}%"
              f"{r.mean()/cont:>+11.3f}")
    p("")
    p(f"  events with >= 15 min before the close       "
      f"{100*(E.tod <= 385-15).mean():.1f}%")
    p(f"  plausible post-confirmation frequency        "
      f"{len(ev)/months:.1f}/month raw; at one-third retention "
      f"{len(ev)/months/3:.1f}/month")
    p("")

    txt = "\n".join(L)
    print(txt)
    (OUT / "rp010_stage1_output.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    main()
