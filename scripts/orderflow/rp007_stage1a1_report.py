#!/usr/bin/env python3
"""RP-007 Stage 1A1 -- analysis and report. Reads only the run's own output.

Counts before outcomes. Support and resistance never pooled to conceal a
one-sided result. alpha = 0.05/30 throughout, as pre-registered at a72fe50.
"""
from __future__ import annotations

import json
import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports"
FAMS = ["PDH", "PDL", "PDC", "PDVWAP", "VAH", "VAL", "POC",
        "XH", "XL", "XM", "IBH", "IBL", "IBM", "VWAP", "ROUND"]
PRIOR5 = ("PDH", "PDL", "VAH", "VAL", "POC")
LABEL = {"PDH": "prior RTH high", "PDL": "prior RTH low",
         "PDC": "prior RTH close", "PDVWAP": "prior RTH VWAP",
         "VAH": "prior VAH", "VAL": "prior VAL", "POC": "prior POC",
         "XH": "extended-hours high", "XL": "extended-hours low",
         "XM": "extended-hours mid", "IBH": "IB high", "IBL": "IB low",
         "IBM": "IB mid", "VWAP": "session VWAP (causal)",
         "ROUND": "round $2.50"}
ALPHA = 0.05 / 30
SHIFTS = ["-6.6667", "-3.3333", "+3.3333", "+6.6667"]
NDRAW, SEED = 200, 20260923
FREQ_BAR = 12.0
ECON = 0.2871          # MNQ 3x round turn, in ATR1m units


def _cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def two_prop(x1, n1, x2, n2):
    if n1 < 2 or n2 < 2:
        return np.nan, np.nan
    p1, p2, p = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return p1 - p2, np.nan
    z = (p1 - p2) / se
    return p1 - p2, 2 * (1 - _cdf(abs(z)))


def terc(s):
    """Tercile labels; falls back to a single bucket when degenerate."""
    try:
        return pd.qcut(s, 3, labels=[0, 1, 2], duplicates="drop").astype(float)
    except Exception:
        return pd.Series(np.zeros(len(s)), index=s.index)


def standardise(gen, ctl, col="rec10"):
    """Direct standardisation of the control onto the genuine strata mix.

    Strata are terciles of (location in the session range so far) x (time of
    day) x (trailing volatility). This is what makes the geometric matching
    binding rather than decorative: if the pooled advantage is a composition
    effect it disappears here.
    """
    if not len(gen) or not len(ctl):
        return np.nan, np.nan, 0.0
    both = pd.concat([gen.assign(_a=1), ctl.assign(_a=0)])
    both["s1"] = terc(both["loc"])
    both["s2"] = terc(both["bar"].astype(float))
    both["s3"] = terc(both["vol"])
    both = both.dropna(subset=["s1", "s2", "s3"])
    g, c = both[both._a == 1], both[both._a == 0]
    if not len(g) or not len(c):
        return np.nan, np.nan, 0.0
    key = ["s1", "s2", "s3"]
    gr = g.groupby(key)[col].agg(["mean", "size"])
    cr = c.groupby(key)[col].agg(["mean", "size"])
    j = gr.join(cr, lsuffix="_g", rsuffix="_c", how="inner")
    j = j[(j["size_c"] >= 5)]
    if not len(j):
        return np.nan, np.nan, 0.0
    w = j["size_g"] / j["size_g"].sum()
    cov = j["size_g"].sum() / gr["size"].sum()
    return float((w * j["mean_g"]).sum()), float((w * j["mean_c"]).sum()), float(cov)


def main():
    G = pd.read_parquet(OUT / "rp007_1a1_genuine.parquet")
    S = pd.read_parquet(OUT / "rp007_1a1_shifted.parquet")
    SALL = S.copy()
    SALL["famset2"] = SALL["fams"].str.split("|")
    S = S[S["first"]]
    pools = pickle.load(open(OUT / "rp007_1a1_pools.pkl", "rb"))
    meta = json.loads((OUT / "rp007_1a1_meta.json").read_text())
    rng = np.random.default_rng(SEED)

    G["famset"] = G["fams"].str.split("|")
    S["famset"] = S["fams"].str.split("|")
    F = G[G["first"]]
    RPT = G[~G["first"]]
    months = G["mo"].nunique()

    L = []
    p = L.append
    p("RP-007 STAGE 1A1 -- QQQ price-level screen. DESCRIPTIVE. NO P&L.")
    p(f"  sessions {meta['fun']['sessions']} | used {meta['fun']['used']} | "
      f"months {months} | alpha {ALPHA:.6f}")
    p("")

    # ---------------- headline ----------------
    gg, ss = F[F["iso"]], S[S["iso"]]
    d0, p0 = two_prop(gg["rec10"].sum(), len(gg), ss["rec10"].sum(), len(ss))
    zc = _ppf975 = 1.959963985
    mde0 = (zc + 0.8416212336) * math.sqrt(0.25 * (1/len(gg) + 1/len(ss)))
    p("=== 0. THE HEADLINE, POOLED OVER ALL FIFTEEN FAMILIES ===")
    p(f"  genuine levels   n={len(gg):>6}  reclaim-10 {100*gg['rec10'].mean():.2f}%")
    p(f"  shifted controls n={len(ss):>6}  reclaim-10 {100*ss['rec10'].mean():.2f}%")
    p(f"  difference {100*d0:+.2f} pts   p={p0:.3f}   "
      f"MDE at this n = +/-{100*mde0:.2f} pts")
    p("  A precisely measured zero, not an underpowered null.")
    p("")

    # ---------------- counts ----------------
    p("=== 1. COUNTS, BEFORE ANY OUTCOME ===")
    p(f"  sessions available                         {meta['fun']['sessions']}")
    p(f"  excluded: no usable prior session          {meta['fun']['no_prior']}")
    p(f"  excluded: fewer than 300 bars              {meta['fun']['short']}")
    p(f"  sessions used                              {meta['fun']['used']}")
    p(f"  sessions with no extended-hours data       {meta['fun']['no_eth']}"
      "   (families XH/XL/XM only)")
    p(f"  clusters: isolated {meta['cl']['iso']} | two-level {meta['cl']['c2']}"
      f" | three-or-more {meta['cl']['c3']}")
    p(f"  CROSSED events (gapped through, not tested) {meta['cross']}")
    p(f"  shifted controls generated {meta['shift_gen']} | excluded for "
      f"overlapping a genuine level {meta['shift_excl']} "
      f"({100*meta['shift_excl']/max(meta['shift_gen'],1):.1f}%)")
    nf = len(F)
    p(f"  matched random control: {meta['matched']} of "
      f"{meta['matched']+meta['unmatched']} first interactions "
      f"({100*meta['matched']/max(meta['matched']+meta['unmatched'],1):.1f}%)")
    p(f"  first interactions {nf} | repeated {len(RPT)} | total {len(G)}")
    p("")
    p(f"  {'family':<8}{'lvl obs':>9}{'first':>8}{'iso 1st':>9}{'repeat':>8}"
      f"{'supp':>7}{'resist':>7}{'1st/mo':>8}{'iso/mo':>8}")
    cnt = {}
    for f in FAMS:
        m = F["famset"].apply(lambda x: f in x)
        mi = m & F["iso"]
        mr = RPT["famset"].apply(lambda x: f in x)
        sub = F[m]
        cnt[f] = dict(first=int(m.sum()), iso=int(mi.sum()),
                      rpt=int(mr.sum()),
                      supp=int((sub.side == 1).sum()),
                      res=int((sub.side == -1).sum()),
                      permo=m.sum() / months, isopermo=mi.sum() / months)
        p(f"  {f:<8}{meta['lvl_obs'][f]:>9}{cnt[f]['first']:>8}"
          f"{cnt[f]['iso']:>9}{cnt[f]['rpt']:>8}{cnt[f]['supp']:>7}"
          f"{cnt[f]['res']:>7}{cnt[f]['permo']:>8.1f}"
          f"{cnt[f]['isopermo']:>8.1f}")
    p("")
    p("  PRIMARY PER-FAMILY SAMPLE = ISOLATED FIRST INTERACTIONS. A cluster's")
    p("  outcome cannot be attributed to one member, and the selection rule")
    p("  requires a family to pass ALONE before any cluster may qualify.")
    p("")

    # ---------------- random control resampling ----------------
    pdf = pd.DataFrame([dict(gi=x["gi"], fams=x["fams"], iso=x["iso"],
                             yr=x["yr"], side=x["side"],
                             n=len(x["rec"])) for x in pools])
    pdf["famset"] = pdf["fams"].str.split("|")
    rec_pool = [x["rec"] for x in pools]
    rot_pool = [x["rot"] for x in pools]

    def rand_dist(mask):
        """200 repetitions: one draw per interaction, aggregated each time."""
        idx = np.flatnonzero(mask.to_numpy())
        if len(idx) < 5:
            return np.nan, np.nan, np.nan, np.nan, 0
        out = np.empty(NDRAW)
        rr = np.random.default_rng(SEED)
        for t in range(NDRAW):
            v = [rec_pool[k][rr.integers(0, len(rec_pool[k]))] for k in idx]
            out[t] = float(np.mean(v))
        return (float(out.mean()), float(out.std()),
                float(np.percentile(out, 5)), float(np.percentile(out, 95)),
                len(idx))

    # ---------------- per-family ----------------
    p("=== 2. LEVEL-FAMILY RESULTS -- isolated first interactions ===")
    p("  reclaim = penetrated the zone and closed back through it within 10 min")
    p("")
    res = {}
    p(f"  {'family':<8}{'n':>6}{'rec10':>8}{'pen%':>7}"
      + "".join(f"{('sh'+s):>10}" for s in SHIFTS)
      + f"{'rand':>9}{'cov':>6}{'p(best)':>9}")
    for f in FAMS:
        g = F[F["famset"].apply(lambda x: f in x) & F["iso"]]
        n = len(g)
        if n < 30:
            res[f] = dict(n=n, skip=True)
            p(f"  {f:<8}{n:>6}   -- fewer than 30 isolated first interactions --")
            continue
        r10 = g["rec10"].mean()
        pen = g["penetrated"].mean()
        row = f"  {f:<8}{n:>6}{100*r10:>8.1f}{100*pen:>7.1f}"
        adv, pv = {}, {}
        for s in SHIFTS:
            c = S[S["famset"].apply(lambda x: f in x) & S["iso"] &
                  (S["arm"] == s)]
            if len(c) < 30:
                adv[s], pv[s] = np.nan, np.nan
                row += f"{'-':>10}"
                continue
            d, q = two_prop(g["rec10"].sum(), n, c["rec10"].sum(), len(c))
            adv[s], pv[s] = d, q
            row += f"{100*d:>+9.1f} "
        mask = pdf["famset"].apply(lambda x: f in x) & pdf["iso"]
        rm, rs, r5, r95, rn = rand_dist(mask)
        radv = r10 - rm if np.isfinite(rm) else np.nan
        row += f"{100*radv:>+8.1f} " if np.isfinite(radv) else f"{'-':>9}"
        row += f"{100*rn/max(n,1):>5.0f}%"
        worst = max([pv[s] for s in SHIFTS if np.isfinite(pv.get(s, np.nan))],
                    default=np.nan)
        row += f"{worst:>9.4f}" if np.isfinite(worst) else f"{'-':>9}"
        p(row)
        res[f] = dict(n=n, rec10=r10, pen=pen, adv=adv, pv=pv,
                      rand_mean=rm, rand_p95=r95, rand_n=rn, radv=radv,
                      worst_p=worst, skip=False)
    p("")
    p("  'rand' is the true rate minus the mean of 200 matched-random "
      "repetitions.")
    p("  'p(best)' is the LEAST significant of the four shifted comparisons: a "
      "family")
    p("  must beat all four, so the weakest one governs.")
    p("")

    # ---------------- support vs resistance ----------------
    p("=== 3. SUPPORT AND RESISTANCE, NEVER POOLED ===")
    p(f"  {'family':<8}{'n supp':>8}{'rec10':>8}{'vs sh':>8}{'|':>3}"
      f"{'n res':>8}{'rec10':>8}{'vs sh':>8}{'both+':>8}")
    for f in FAMS:
        if res[f].get("skip"):
            continue
        g = F[F["famset"].apply(lambda x: f in x) & F["iso"]]
        out, both = [], True
        for sd in (1, -1):
            gg = g[g.side == sd]
            cc = S[S["famset"].apply(lambda x: f in x) & S["iso"] &
                   (S["side"] == sd)]
            if len(gg) < 20 or len(cc) < 20:
                out.append((len(gg), np.nan, np.nan))
                both = False
                continue
            d, _ = two_prop(gg["rec10"].sum(), len(gg),
                            cc["rec10"].sum(), len(cc))
            out.append((len(gg), gg["rec10"].mean(), d))
            if not (d > 0):
                both = False
        (ns, rs_, ds), (nr, rr_, dr) = out
        p(f"  {f:<8}{ns:>8}{100*rs_ if np.isfinite(rs_) else float('nan'):>8.1f}"
          f"{100*ds if np.isfinite(ds) else float('nan'):>+8.1f}{'|':>3}"
          f"{nr:>8}{100*rr_ if np.isfinite(rr_) else float('nan'):>8.1f}"
          f"{100*dr if np.isfinite(dr) else float('nan'):>+8.1f}"
          f"{('YES' if both else 'no'):>8}")
        res[f]["both_sides"] = both
        res[f]["supp_adv"], res[f]["res_adv"] = ds, dr
    p("")

    # ---------------- rotation, MFE, MAE ----------------
    p("=== 4. ROTATION AFTER RECLAIM, MFE AND MAE (ATR units) ===")
    p(f"  economic reference: 3x MNQ round turn = {ECON:.4f} ATR")
    p(f"  {'family':<8}{'n rec':>7}{'rot5':>8}{'rot10':>8}{'rot15':>8}"
      f"{'rot30':>8}{'ctl rot30':>10}{'MFE':>7}{'MAE':>7}{'vs 3x':>8}")
    for f in FAMS:
        if res[f].get("skip"):
            continue
        g = F[F["famset"].apply(lambda x: f in x) & F["iso"]]
        rr_ = g[g["rec10"]]
        cc = S[S["famset"].apply(lambda x: f in x) & S["iso"] & S["rec10"]]
        v = [rr_[f"rot{m}"].mean() for m in (5, 10, 15, 30)]
        cr = cc["rot30"].mean() if len(cc) else np.nan
        p(f"  {f:<8}{len(rr_):>7}" + "".join(f"{x:>+8.3f}" for x in v)
          + f"{cr:>+10.3f}{g['mfe'].mean():>7.3f}{g['mae'].mean():>7.3f}"
          + f"{(v[3]-ECON):>+8.3f}")
        res[f]["rot30"] = v[3]
        res[f]["rot30_ctl"] = cr
        res[f]["rot_adv"] = v[3] - cr if np.isfinite(cr) else np.nan
    p("")

    # ---------------- first vs repeated ----------------
    p("=== 5. FIRST VERSUS REPEATED INTERACTIONS ===")
    p("  The same comparison is run on the SHIFTED control, because a "
      "condition that")
    p("  every family passes is a structural artefact until something "
      "arbitrary fails it.")
    p(f"  {'family':<8}{'n 1st':>8}{'rec10':>8}{'n rpt':>8}{'rec10':>8}"
      f"{'1st-rpt':>9}{'CONTROL':>9}{'correct':>9}")
    for f in FAMS:
        if res[f].get("skip"):
            continue
        a = F[F["famset"].apply(lambda x: f in x) & F["iso"]]
        b = RPT[RPT["famset"].apply(lambda x: f in x) & RPT["iso"]]
        if len(b) < 30:
            res[f]["first_gt_rpt"] = False
            p(f"  {f:<8}{len(a):>8}{100*a['rec10'].mean():>8.1f}{len(b):>8}"
              f"{'-':>8}{'-':>9}{'no':>9}")
            continue
        d, _ = two_prop(a["rec10"].sum(), len(a), b["rec10"].sum(), len(b))
        res[f]["first_gt_rpt"] = bool(d > 0)
        s1 = SALL[SALL["famset2"].apply(lambda x: f in x) & SALL["iso"]
                  & SALL["first"]]
        s2 = SALL[SALL["famset2"].apply(lambda x: f in x) & SALL["iso"]
                  & ~SALL["first"]]
        cd = (s1["rec10"].mean() - s2["rec10"].mean()) if (len(s1) > 30 and
                                                           len(s2) > 30) else np.nan
        res[f]["first_gt_rpt_ctl"] = cd
        p(f"  {f:<8}{len(a):>8}{100*a['rec10'].mean():>8.1f}{len(b):>8}"
          f"{100*b['rec10'].mean():>8.1f}{100*d:>+9.1f}{100*cd:>+9.1f}"
          f"{('YES' if d > 0 else 'no'):>9}")
    p("")

    # ---------------- by year ----------------
    p("=== 6. BY CALENDAR YEAR -- advantage over the pooled shifted control ===")
    yrs = sorted(G["yr"].unique())
    p(f"  {'family':<8}" + "".join(f"{y:>9}" for y in yrs) + f"{'yrs +':>8}")
    for f in FAMS:
        if res[f].get("skip"):
            continue
        line, good = f"  {f:<8}", 0
        for y in yrs:
            g = F[F["famset"].apply(lambda x: f in x) & F["iso"] & (F.yr == y)]
            c = S[S["famset"].apply(lambda x: f in x) & S["iso"] & (S.yr == y)]
            if len(g) < 30 or len(c) < 30:
                line += f"{'-':>9}"
                continue
            d, _ = two_prop(g["rec10"].sum(), len(g), c["rec10"].sum(), len(c))
            line += f"{100*d:>+9.1f}"
            good += int(d > 0)
        res[f]["years_pos"] = good
        p(line + f"{good:>8}")
    p("")

    # ---------------- geometric strata ----------------
    p("=== 7. MATCHED GEOMETRIC STRATA (binding) ===")
    p("  Direct standardisation of the shifted control onto the genuine mix of")
    p("  (range-location x time-of-day x volatility) terciles.")
    p(f"  {'family':<8}{'pooled adv':>12}{'std adv':>10}{'coverage':>10}"
      f"{'survives':>10}")
    for f in FAMS:
        if res[f].get("skip"):
            continue
        g = F[F["famset"].apply(lambda x: f in x) & F["iso"]]
        c = S[S["famset"].apply(lambda x: f in x) & S["iso"]]
        pooled = (g["rec10"].mean() - c["rec10"].mean()) if len(c) else np.nan
        gm, cm, cov = standardise(g, c)
        std = gm - cm if np.isfinite(gm) and np.isfinite(cm) else np.nan
        surv = bool(np.isfinite(std) and std > 0 and np.isfinite(pooled)
                    and pooled > 0)
        res[f]["std_adv"] = std
        res[f]["geo_survives"] = surv
        p(f"  {f:<8}{100*pooled:>+12.1f}{100*std:>+10.1f}{100*cov:>9.0f}%"
          f"{('YES' if surv else 'no'):>10}")
    p("")

    # ---------------- selection ----------------
    p("=== 8. SELECTION RULE -- all eight conditions ===")
    p(f"  {'family':<8}{'1 sh':>6}{'2 rnd':>7}{'3 geo':>7}{'4 s/r':>7}"
      f"{'5 1>r':>7}{'6 yrs':>7}{'7 frq':>7}{'8 new':>7}{'PASS':>7}")
    passed = []
    for f in FAMS:
        r = res[f]
        if r.get("skip"):
            p(f"  {f:<8}{'--- insufficient isolated first interactions ---':>60}")
            continue
        c1 = all(np.isfinite(r["adv"].get(s, np.nan)) and r["adv"][s] > 0
                 for s in SHIFTS) and np.isfinite(r["worst_p"]) \
            and r["worst_p"] < ALPHA
        c2 = bool(np.isfinite(r["radv"]) and r["rec10"] > r["rand_p95"])
        c3 = bool(r.get("geo_survives"))
        c4 = bool(r.get("both_sides"))
        c5 = bool(r.get("first_gt_rpt"))
        c6 = r.get("years_pos", 0) >= 4
        c7 = cnt[f]["permo"] >= FREQ_BAR
        c8 = True if f not in PRIOR5 else (c1 and c2 and c3)
        ok = all([c1, c2, c3, c4, c5, c6, c7, c8])
        if ok:
            passed.append(f)
        y = lambda b: "Y" if b else "."
        p(f"  {f:<8}{y(c1):>6}{y(c2):>7}{y(c3):>7}{y(c4):>7}{y(c5):>7}"
          f"{y(c6):>7}{y(c7):>7}{y(c8):>7}{('PASS' if ok else 'fail'):>7}")
    p("")
    p(f"  FAMILIES PASSING ALL EIGHT CONDITIONS: "
      f"{', '.join(passed) if passed else 'NONE'}")
    p("")

    # ---------------- confluence ----------------
    p("=== 9. CONFLUENCE -- descriptive only ===")
    for k, lab in ((1, "isolated"), (2, "two-level"), (3, "three-or-more")):
        g = F[F["ksize"] == k] if k < 3 else F[F["ksize"] >= 3]
        if not len(g):
            continue
        c = S[S["iso"]] if k == 1 else S[~S["iso"]]
        p(f"  {lab:<16} n={len(g):>6}  rec10 {100*g['rec10'].mean():>5.1f}%  "
          f"rot30 {g[g['rec10']]['rot30'].mean():>+6.3f}  "
          f"MFE {g['mfe'].mean():.3f}  MAE {g['mae'].mean():.3f}")
    p("  No cluster may qualify unless a member family passes alone. "
      f"{'No family passed alone, so nothing is claimed from confluence.' if not passed else ''}")
    p("")

    # ---------------- reconciliation ----------------
    p("=== 10. RECONCILIATION WITH THE 1,414-SESSION QQQ NULL ===")
    prior = {"PDH": 44.8, "PDL": 48.1, "VAH": 47.2, "VAL": 51.5, "POC": 49.0}
    p(f"  {'family':<8}{'2021-26 earlier':>17}{'now rec10':>11}"
      f"{'now vs shift':>14}{'now vs rand':>13}{'adds info':>11}")
    for f in PRIOR5:
        r = res[f]
        if r.get("skip"):
            p(f"  {f:<8}{prior[f]:>16.1f}%{'--':>11}")
            continue
        best = np.nanmax([r["adv"][s] for s in SHIFTS])
        p(f"  {f:<8}{prior[f]:>16.1f}%{100*r['rec10']:>10.1f}%"
          f"{100*best:>+13.1f}{100*r['radv']:>+12.1f}"
          f"{('YES' if (r.get('geo_survives') and best > 0) else 'no'):>11}")
    p("")

    txt = "\n".join(L)
    print(txt)
    (OUT / "rp007_1a1_output.txt").write_text(txt)
    json.dump({k: {a: (float(b) if isinstance(b, (int, float, np.floating))
                       else b) for a, b in v.items() if a != "adv" and a != "pv"}
               for k, v in res.items()},
              open(OUT / "rp007_1a1_family_summary.json", "w"),
              indent=1, default=str)
    return passed


if __name__ == "__main__":
    main()
