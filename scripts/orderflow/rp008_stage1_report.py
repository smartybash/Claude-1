#!/usr/bin/env python3
"""RP-008 Stage 1 -- analysis. Counts first, then forward environment.

Reads only rp008_stage1.py's own output. No strategy anything.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import rp008_stage1 as S1

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports"
LAB = ("LO", "NORMAL", "HI")
STOPS = S1.STOPS
ORDER = [f"{i} {v}" for i in ("09:30", "11:30") for v in LAB]

L = []
p = L.append


def blk(df, key="state"):
    g = df.groupby(key, dropna=True)
    out = g.agg(n=("f_rv", "size"),
                rv60=("rv60", "mean"),
                f_rv=("f_rv", "mean"),
                f_rng=("f_rng", "mean"),
                mfe=("f_mfe", "median"),
                mae=("f_mae", "median"),
                mfe_m=("f_mfe", "mean"),
                mae_m=("f_mae", "mean"),
                eff=("f_eff", "mean"),
                to_close=("to_close", "mean"))
    for s in STOPS:
        out[f"dn{s}"] = g[f"dn{s}"].mean() * 100
        out[f"ei{s}"] = g[f"ei{s}"].mean() * 100
    return out


def main():
    P = pd.read_parquet(OUT / "rp008_stage1_states.parquet")
    R = pd.read_parquet(OUT / "rp008_stage1_obs.parquet")
    P = P[P["vol"].notna()].copy()
    P["state"] = P["instant"] + " " + P["vol"]
    P["staterel"] = np.where(P["volrel"].notna(),
                             P["instant"] + " " + P["volrel"].astype(str), None)
    months = P.day.dt.to_period("M").nunique()
    years = sorted(P.year.unique())

    p("RP-008 STAGE 1 -- REGIME VALIDITY. THE MARKET, NOT THE STRATEGIES.")
    p("  No strategy P&L, no trade, no allocator, no pairing, no Monte Carlo.")
    p(f"  QQQ 1-minute, {P.day.nunique()} sessions, {months} months, "
      f"{len(P)} labelled classification observations.\n")

    # ------------------------------------------------ 1. counts
    p("=== 1. COUNTS, BEFORE ANY FORWARD OUTCOME ===")
    p(f"  classification observations built      {len(R)}")
    p(f"  at the two PRIMARY instants            "
      f"{int(R.instant.isin(S1.INSTANTS).sum())}")
    p(f"  labelled after the 250-observation warm-up  {len(P)}")
    p(f"  sessions {P.day.nunique()} | months {months} | years {years[0]}-{years[-1]}")
    p("")
    ct = P.groupby(["instant", "vol"]).size().unstack().reindex(columns=LAB)
    ct["all"] = ct.sum(axis=1)
    p("  POOLED terciles (the frozen primary):")
    p(ct.to_string())
    p("")
    p("  *** The two instants do NOT draw from the same RV60 distribution. ***")
    r0 = P[P.instant == "09:30"]["rv60"]
    r1 = P[P.instant == "11:30"]["rv60"]
    p(f"  RV60 at 09:30 (prior session 15:00-16:00): mean {r0.mean():.2f} bps, "
      f"median {r0.median():.2f}")
    p(f"  RV60 at 11:30 (same session 10:30-11:30) : mean {r1.mean():.2f} bps, "
      f"median {r1.median():.2f}")
    p("  A pooled tercile label therefore partly encodes WHICH INSTANT, which is")
    p("  the confound the pre-registration named. The block-relative labels")
    p("  below were added at this counts stage, before any forward outcome was")
    p("  computed, and both are carried through every table.")
    p("")
    cr = P[P.volrel.notna()].groupby(["instant", "volrel"]).size().unstack()
    cr = cr.reindex(columns=LAB)
    cr["all"] = cr.sum(axis=1)
    p("  BLOCK-RELATIVE terciles (declared diagnostic):")
    p(cr.to_string())
    p("")
    p("  days per month, by state (pooled):")
    for st in ORDER:
        g = P[P.state == st]
        if len(g):
            p(f"    {st:<14} {len(g):>5}  {len(g)/months:>6.2f}/mo  "
              f"{100*len(g)/len(P):>5.1f}% of sample")
    p("")
    p("  Each observation classifies a 60-minute forward window, so one state")
    p("  occurrence = 60 forward minutes. Duration is fixed by construction and")
    p("  carries no information; it is reported for completeness only.")
    p("")

    # ------------------------------------------------ 2. forward environment
    p("=== 2. FORWARD ENVIRONMENT BY STATE (pooled terciles, frozen primary) ===")
    p("  All scaled quantities in ATR1m units. Forward window is 60 minutes,")
    p("  strictly after the classification bar.")
    p("")
    B = blk(P).reindex(ORDER)
    p(f"  {'state':<14}{'n':>5}{'RV60':>8}{'fwd RV':>8}{'fwd rng':>9}"
      f"{'MFE med':>9}{'MAE med':>9}{'fwd eff':>9}{'to close':>9}")
    for st in ORDER:
        if st not in B.index or not np.isfinite(B.loc[st, "n"]):
            continue
        b = B.loc[st]
        p(f"  {st:<14}{int(b['n']):>5}{b['rv60']:>8.2f}{b['f_rv']:>8.2f}"
          f"{b['f_rng']:>9.3f}{b['mfe']:>9.3f}{b['mae']:>9.3f}"
          f"{b['eff']:>9.3f}{int(b['to_close']):>9}")
    p("")
    p("  STOP-OUT PROBABILITY -- P(adverse excursion >= d), %")
    p(f"  {'state':<14}" + "".join(f"{('dn '+str(s)):>9}" for s in STOPS)
      + "".join(f"{('either '+str(s)):>12}" for s in STOPS))
    for st in ORDER:
        if st not in B.index or not np.isfinite(B.loc[st, "n"]):
            continue
        b = B.loc[st]
        p(f"  {st:<14}" + "".join(f"{b[f'dn{s}']:>9.1f}" for s in STOPS)
          + "".join(f"{b[f'ei{s}']:>12.1f}" for s in STOPS))
    p("")

    # ------------------------------------------------ 3. the separation test
    p("=== 3. THE DECISIVE SEPARATION TEST ===")
    p("  At matched volatility, does the INSTANT matter?")
    p("  At matched instant, does the VOLATILITY tercile matter?")
    p("")
    p("  (a) MATCHED VOLATILITY, 11:30 vs 09:30")
    p(f"  {'vol':<9}{'fwd RV 09:30':>14}{'fwd RV 11:30':>14}{'ratio':>8}"
      f"{'MAE 09:30':>11}{'MAE 11:30':>11}{'ratio':>8}")
    for v in LAB:
        a = P[(P.instant == "09:30") & (P.vol == v)]
        b = P[(P.instant == "11:30") & (P.vol == v)]
        if len(a) < 30 or len(b) < 30:
            continue
        p(f"  {v:<9}{a.f_rv.mean():>14.2f}{b.f_rv.mean():>14.2f}"
          f"{b.f_rv.mean()/a.f_rv.mean():>8.2f}"
          f"{a.f_mae.median():>11.3f}{b.f_mae.median():>11.3f}"
          f"{b.f_mae.median()/a.f_mae.median():>8.2f}")
    p("")
    p("  (b) MATCHED INSTANT, HI vs LO tercile")
    p(f"  {'instant':<9}{'fwd RV LO':>12}{'fwd RV HI':>12}{'ratio':>8}"
      f"{'MAE LO':>10}{'MAE HI':>10}{'ratio':>8}{'overlap':>9}")
    sep = {}
    for i in ("09:30", "11:30"):
        a = P[(P.instant == i) & (P.vol == "LO")]
        b = P[(P.instant == i) & (P.vol == "HI")]
        if len(a) < 30 or len(b) < 30:
            continue
        ov = S1.overlap(a.f_mae, b.f_mae)
        sep[i] = dict(rv_ratio=b.f_rv.mean() / a.f_rv.mean(),
                      mae_ratio=b.f_mae.median() / a.f_mae.median(),
                      overlap=ov)
        p(f"  {i:<9}{a.f_rv.mean():>12.2f}{b.f_rv.mean():>12.2f}"
          f"{sep[i]['rv_ratio']:>8.2f}{a.f_mae.median():>10.3f}"
          f"{b.f_mae.median():>10.3f}{sep[i]['mae_ratio']:>8.2f}{ov:>9.3f}")
    p("")
    p("  (c) SAME, on the BLOCK-RELATIVE labels")
    p(f"  {'instant':<9}{'fwd RV LO':>12}{'fwd RV HI':>12}{'ratio':>8}"
      f"{'MAE LO':>10}{'MAE HI':>10}{'ratio':>8}{'overlap':>9}")
    seprel = {}
    for i in ("09:30", "11:30"):
        a = P[(P.instant == i) & (P.volrel == "LO")]
        b = P[(P.instant == i) & (P.volrel == "HI")]
        if len(a) < 30 or len(b) < 30:
            continue
        ov = S1.overlap(a.f_mae, b.f_mae)
        seprel[i] = dict(rv_ratio=b.f_rv.mean() / a.f_rv.mean(),
                         mae_ratio=b.f_mae.median() / a.f_mae.median(),
                         overlap=ov)
        p(f"  {i:<9}{a.f_rv.mean():>12.2f}{b.f_rv.mean():>12.2f}"
          f"{seprel[i]['rv_ratio']:>8.2f}{a.f_mae.median():>10.3f}"
          f"{b.f_mae.median():>10.3f}{seprel[i]['mae_ratio']:>8.2f}{ov:>9.3f}")
    p("")
    p("  (d) STOP-OUT SPREAD -- the economically binding comparison")
    p(f"  {'comparison':<34}" + "".join(f"{('d='+str(s)):>10}" for s in STOPS))
    rowsd = []
    for i in ("09:30", "11:30"):
        a = P[(P.instant == i) & (P.vol == "LO")]
        b = P[(P.instant == i) & (P.vol == "HI")]
        if len(a) < 30 or len(b) < 30:
            continue
        d = [100 * (b[f"dn{s}"].mean() - a[f"dn{s}"].mean()) for s in STOPS]
        rowsd.append((f"{i}  HI minus LO (pooled)", d))
    for v in LAB:
        a = P[(P.instant == "09:30") & (P.vol == v)]
        b = P[(P.instant == "11:30") & (P.vol == v)]
        if len(a) < 30 or len(b) < 30:
            continue
        d = [100 * (b[f"dn{s}"].mean() - a[f"dn{s}"].mean()) for s in STOPS]
        rowsd.append((f"{v:<6} 11:30 minus 09:30", d))
    for nm, d in rowsd:
        p(f"  {nm:<34}" + "".join(f"{x:>+10.1f}" for x in d))
    p("")

    # ------------------------------------------------ 4. persistence control
    p("=== 4. PERSISTENCE CONTROL -- is the state a lookup table for RV60? ===")
    q = P.dropna(subset=["rv60", "f_rv"]).copy()
    x, y = q.rv60.to_numpy(float), q.f_rv.to_numpy(float)
    b1 = np.polyfit(x, y, 1)
    yhat = np.polyval(b1, x)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2_ar1 = 1 - float(((y - yhat) ** 2).sum()) / ss_tot
    gm = q.groupby("state")["f_rv"].transform("mean")
    r2_state = 1 - float(((y - gm.to_numpy()) ** 2).sum()) / ss_tot
    res = y - yhat
    gm2 = pd.Series(res).groupby(q.state.to_numpy()).transform("mean").to_numpy()
    r2_extra = 1 - float(((res - gm2) ** 2).sum()) / float((res ** 2).sum())
    p(f"  R2 of a linear fit on RV60 alone              {r2_ar1:>7.4f}")
    p(f"  R2 of the six state means alone               {r2_state:>7.4f}")
    p(f"  extra R2 the states add ON TOP of RV60        {r2_extra:>7.4f}")
    p("  If the third number is near zero the state labels are a coarse lookup")
    p("  table for RV60 and carry no independent forward information.")
    p("")
    p("  That third figure is inflated by the INSTANT, which the state label")
    p("  carries and a linear fit on RV60 cannot. Decomposed properly:")
    p("")

    def _r2(y, yh):
        y, yh = np.asarray(y, float), np.asarray(yh, float)
        return 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    def _ols(X, y):
        X = np.column_stack([np.ones(len(y))] + X)
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        return X @ b

    qq = P.dropna(subset=["rv60", "f_rv", "f_mae", "f_eff"]).copy()
    inst = (qq.instant == "11:30").astype(float).to_numpy()
    rvv = qq.rv60.to_numpy(float)
    p(f"  {'target':<22}{'instant':>9}{'RV60':>9}{'both':>9}"
      f"{'+tercile':>10}{'tercile adds':>14}")
    for tgt, nm in (("f_rv", "forward RV (bps)"),
                    ("f_mae", "forward MAE (ATR)"),
                    ("f_eff", "forward efficiency")):
        y = qq[tgt].to_numpy(float)
        for col, tag in (("vol", "pooled"), ("volrel", "block-relative")):
            hi = (qq[col] == "HI").astype(float).to_numpy()
            lo = (qq[col] == "LO").astype(float).to_numpy()
            a = _r2(y, _ols([inst, rvv], y))
            b = _r2(y, _ols([inst, rvv, hi, lo], y))
            if tag == "pooled":
                p(f"  {nm:<22}{_r2(y,_ols([inst],y)):>9.4f}"
                  f"{_r2(y,_ols([rvv],y)):>9.4f}{a:>9.4f}{b:>10.4f}"
                  f"{b-a:>+14.4f}")
            else:
                p(f"  {'  (block-relative)':<22}{'':>9}{'':>9}{a:>9.4f}"
                  f"{b:>10.4f}{b-a:>+14.4f}")
    p("")
    p("  correlation of RV60 with the forward outcome, WITHIN each instant:")
    for i in ("09:30", "11:30"):
        g = qq[qq.instant == i]
        p(f"    {i}   vs forward RV (bps) {g[['rv60','f_rv']].corr().iloc[0,1]:+.3f}"
          f"   vs forward MAE (ATR) {g[['rv60','f_mae']].corr().iloc[0,1]:+.3f}")
    p("")

    # ------------------------------------------------ 5. stability
    p("=== 5. STABILITY BY YEAR ===")
    p("  HI/LO forward-RV ratio at each instant, per year "
      "(bar: ordering holds in >=5 of 6)")
    p(f"  {'instant':<9}" + "".join(f"{y:>9}" for y in years) + f"{'yrs>1':>8}")
    stab = {}
    for i in ("09:30", "11:30"):
        line, good = f"  {i:<9}", 0
        for y in years:
            a = P[(P.instant == i) & (P.vol == "LO") & (P.year == y)]
            b = P[(P.instant == i) & (P.vol == "HI") & (P.year == y)]
            if len(a) < 15 or len(b) < 15:
                line += f"{'-':>9}"
                continue
            r = b.f_rv.mean() / a.f_rv.mean()
            line += f"{r:>9.2f}"
            good += int(r > 1.0)
        stab[i] = good
        p(line + f"{good:>8}")
    p("")
    p("  state frequency by year (pooled terciles), % of that year's "
      "observations")
    fy = (P.groupby(["year", "state"]).size().unstack().reindex(columns=ORDER)
          .fillna(0))
    fy = 100 * fy.div(fy.sum(axis=1), axis=0)
    p(fy.round(1).to_string())
    p("")

    # ------------------------------------------------ 6. transitions
    p("=== 6. TRANSITION MATRIX ===")
    Q = P.sort_values(["day", "instant"]).reset_index(drop=True)
    Q["next"] = Q["state"].shift(-1)
    Q.loc[Q.index[-1], "next"] = None
    TM = pd.crosstab(Q["state"], Q["next"], normalize="index") * 100
    TM = TM.reindex(index=ORDER, columns=ORDER)
    p(TM.round(1).to_string())
    p("")
    p("  Transitions alternate 09:30 -> 11:30 within a session and")
    p("  11:30 -> 09:30 across sessions, so the instant half of the transition")
    p("  is deterministic. Only the volatility half carries information.")
    p("")
    p("  volatility-only transition, per year (% staying in the same tercile):")
    Q["v0"] = Q["vol"]
    Q["v1"] = Q["vol"].shift(-1)
    for y in years:
        g = Q[(Q.year == y) & Q.v1.notna()]
        if len(g) < 50:
            continue
        p(f"    {y}   stay {100*(g.v0 == g.v1).mean():>5.1f}%   n={len(g)}")
    p("")

    # ------------------------------------------------ 7. neighbouring
    p("=== 7. NEIGHBOURING THRESHOLDS ===")
    p(f"  {'cut':<10}{'instant':<9}{'fwd RV ratio HI/LO':>20}"
      f"{'MAE ratio':>12}{'dn1.0 spread':>14}")
    for cut, col in (("33/67", "vol"), ("30/70", "t3070"), ("40/60", "t4060")):
        for i in ("09:30", "11:30"):
            a = P[(P.instant == i) & (P[col] == "LO")]
            b = P[(P.instant == i) & (P[col] == "HI")]
            if len(a) < 30 or len(b) < 30:
                continue
            p(f"  {cut:<10}{i:<9}{b.f_rv.mean()/a.f_rv.mean():>20.2f}"
              f"{b.f_mae.median()/a.f_mae.median():>12.2f}"
              f"{100*(b['dn1.0'].mean()-a['dn1.0'].mean()):>+14.1f}")
    p("")

    # ------------------------------------------------ 8. secondary panel
    p("=== 8. SECONDARY DESCRIPTIVE PANEL -- all four blocks, no pass weight ===")
    Rr = R.copy()
    g = Rr.groupby("instant").agg(n=("f_rv", "size"), rv60=("rv60", "mean"),
                                  f_rv=("f_rv", "mean"), f_rng=("f_rng", "mean"),
                                  mae=("f_mae", "median"), mfe=("f_mfe", "median"),
                                  eff=("f_eff", "mean"))
    for s in STOPS:
        g[f"dn{s}"] = Rr.groupby("instant")[f"dn{s}"].mean() * 100
    p(g.reindex(["09:30", "10:00", "11:30", "14:00"]).round(3).to_string())
    p("")

    txt = "\n".join(L)
    print(txt)
    (OUT / "rp008_stage1_output.txt").write_text(txt)
    json.dump(dict(sep=sep, seprel=seprel, r2_ar1=r2_ar1,
                   r2_state=r2_state, r2_extra=r2_extra, stab=stab),
              open(OUT / "rp008_stage1_summary.json", "w"), indent=1,
              default=str)
    return 0


if __name__ == "__main__":
    main()
