#!/usr/bin/env python3
"""FROZEN IB 1R, UNCHANGED, ON RELATED INSTRUMENTS. 5-minute bars.

RELATED-INSTRUMENT CHECK, NOT A REPLICATION. Same period as discovery
(2021-2025), so the macro regime is shared; only the instrument differs.
A pass here is weaker evidence than a true out-of-period holdout.

Rule frozen at the pre-registered spec: IB 09:30-10:30, expected side =
opposite the extreme that formed first, require the 10:30 close in the 0-25%
ending zone, no trade if the opposite boundary breaks first, enter on the first
break of the expected boundary at max(trigger, bar open), stop at the opposite
IB boundary, target 1R, ONE trade, flat at the cash close. Entry bar excluded.
Cost 2 NQ points as a fraction of a ~30,000 index = 0.667 bps, the project's
standing convention applied unchanged.

FIVE INSTRUMENTS: SPY, IWM, XLK, IJH, EFA. 2021-01-04 .. 2025-12-31.

XLK IS NOT AN INDEPENDENT MARKET. It holds the large-cap US technology names
that dominate QQQ by weight. It is reported in the per-instrument table and is
EXCLUDED from the headline pooled estimate, which is declared to be the four
instruments that are not tech-concentrated US large cap: SPY, IWM, IJH, EFA.
Both pooled figures are printed so nothing is hidden by the choice.

THE STANDARD ERROR MUST BE CLUSTERED BY DATE, AND THIS IS DECLARED BEFORE THE
NUMBERS. All five instruments trade the SAME 1,255 calendar sessions and are
driven by the same market. Treating N trades as N independent observations
understates the standard error badly -- the effective sample is closer to the
number of DATES than the number of trades. Three estimators are printed:

  naive       per-trade SE, assumes independence. SHOWN ONLY TO BE REJECTED.
  clustered   cluster-robust by date. THIS IS THE GOVERNING FIGURE.
  per-date    one observation per date (mean R across instruments that traded),
              SE across dates. An independent check on the clustered figure.

HOLDOUT POWER is computed ONE-SIDED, as instructed, at the pooled effect size,
against the 1,259 sealed sessions of 2016-2020 at the discovery trade rate.
No holdout data is read by this script. 2016-2020 stays sealed.
"""
from __future__ import annotations
import datetime as dt, sys
from math import sqrt, erf
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]
COST_F = 2.00 / 30000.0
TGT = 1.0

SYMS = ("SPY", "IWM", "XLK", "IJH", "EFA")
HEADLINE = ("SPY", "IWM", "IJH", "EFA")       # XLK excluded: overlaps QQQ

# Frozen discovery candidate, for reference and for the power calculation.
DISC_MEAN, DISC_SD = 0.0612, 0.7175
DISC_TRADES, DISC_SESSIONS = 685, 1418
HOLDOUT_SESSIONS = 1259                        # sealed 2016-2020, NOT read


def ncdf(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def cluster_se(R, keys):
    """Cluster-robust SE of a mean, clusters = distinct keys."""
    R = np.asarray(R, float)
    n = len(R)
    mu = R.mean()
    d = pd.Series(R - mu).groupby(np.asarray(keys)).sum().to_numpy()
    g = len(d)
    if g < 2:
        return np.nan, g
    adj = g / (g - 1.0)
    return sqrt(adj * float((d ** 2).sum())) / n, g


def run(df, name, lo_year=2021, hi_year=2025):
    df = df.copy()
    df["day"] = df.timestamp.dt.date
    rows, look, amb_n, ties, qual = [], 0, 0, 0, 0
    for day, g in df.groupby("day", sort=True):
        if not (lo_year <= day.year <= hi_year):
            continue
        g = g.sort_values("timestamp")
        if len(g) < 70:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        t = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        hi = g.high.to_numpy(float); lo = g.low.to_numpy(float)
        op = g.open.to_numpy(float); cl = g.close.to_numpy(float)
        px = float(op[0]); n = len(t)
        ib = (t >= 0) & (t < 60)
        if ib.sum() < 10 or (t >= 60).sum() < 20:
            continue
        ih, il, tib = hi[ib], lo[ib], t[ib]
        a, b = int(np.argmax(ih)), int(np.argmin(il))
        if tib[a] == tib[b]:
            ties += 1; continue
        ibh, ibl = float(ih[a]), float(il[b]); rng = ibh - ibl
        if rng <= 0:
            continue
        high_first = tib[a] < tib[b]
        close = float(cl[ib][-1])
        exp_lvl = ibl if high_first else ibh
        stop = ibh if high_first else ibl
        ez = 100.0 * abs(close - exp_lvl) / rng
        if ez >= 25:
            continue
        qual += 1
        d = -1 if high_first else 1
        i0 = int(np.searchsorted(t, 60, "left"))
        fe = np.where(hi[i0:] > exp_lvl)[0] if d > 0 else np.where(lo[i0:] < exp_lvl)[0]
        fo = np.where(lo[i0:] < stop)[0] if d > 0 else np.where(hi[i0:] > stop)[0]
        if len(fe) == 0:
            continue
        if len(fo) and int(fo[0]) < int(fe[0]):
            continue
        i = i0 + int(fe[0])
        if i + 1 >= n:
            continue
        if i < i0:
            look += 1
        fill = max(exp_lvl, op[i]) if d > 0 else min(exp_lvl, op[i])
        risk = abs(fill - stop)
        if risk <= 0:
            continue
        cost = px * COST_F
        tgt = fill + d * TGT * risk
        ex, why, mfe, mae, ambi = None, "", 0.0, 0.0, False
        for j in range(i + 1, n):                      # entry bar EXCLUDED
            fav = d * (hi[j] - fill) if d > 0 else d * (lo[j] - fill)
            adv = d * (lo[j] - fill) if d > 0 else d * (hi[j] - fill)
            mfe = max(mfe, fav); mae = min(mae, adv)
            st = lo[j] <= stop if d > 0 else hi[j] >= stop
            ht = hi[j] >= tgt if d > 0 else lo[j] <= tgt
            if st and ht: ambi = True
            if st:
                ex = min(stop, op[j]) if d > 0 else max(stop, op[j]); why = "stop"; break
            if ht:
                ex, why = tgt, "target"; break
        if ex is None:
            ex, why = cl[-1], "close"
        amb_n += int(ambi)
        rows.append(dict(day=day, year=day.year, dir=d,
                         R=(d * (ex - fill) - cost) / risk,
                         naive_R=(d * ((stop if why == "stop" else ex) - fill) - cost) / risk,
                         why=why, risk_bps=1e4 * risk / px,
                         cost_pct=100 * cost / risk,
                         mfe=mfe / risk, mae=mae / risk, amb=ambi))
    T = pd.DataFrame(rows)
    return T, dict(name=name, look=look, ties=ties, qual=qual)


def report(T, meta, sessions_total):
    if T.empty:
        print(f"  {meta['name']:<10} no trades"); return
    R = T.R; w, l = R[R > 0], R[R <= 0]
    t = R.mean() / (R.std(ddof=1) / sqrt(len(R)))
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() else np.inf
    top = R.sort_values(ascending=False).head(int(np.ceil(0.01 * len(R)))).sum()
    ex1 = R.sum() - top
    hc = (R - 0.5 * T.cost_pct / 100.0).mean()
    yrs = R.groupby(T.year).mean()
    yp = int((yrs > 0).sum())
    ok = (R.mean() > 0 and pf > 1.15 and yp >= 4 and ex1 > 0 and hc > 0)
    print(f"  {meta['name']:<10}{sessions_total:>9,}{meta['qual']:>7,}"
          f"{len(T):>8,}{R.mean():>+9.4f}{pf:>7.2f}{t:>+7.2f}{yp:>4}/{len(yrs)}"
          f"{ex1:>+9.1f}{hc:>+10.4f}{T.risk_bps.median():>9.1f}b"
          f"{T.cost_pct.median():>7.2f}%{100*T.amb.mean():>6.1f}%"
          f"{meta['look']:>6}{'PASSES 5' if ok else '':>10}")
    return dict(name=meta['name'], T=T, yrs=yrs, t=t, pf=pf, ok=ok)


if __name__ == "__main__":
    print("=" * 130)
    print("  FROZEN IB 1R ON RELATED INSTRUMENTS — 5-minute bars, 2021-2025")
    print("=" * 130)
    print("  RELATED-INSTRUMENT CHECK, NOT A REPLICATION. Same period as")
    print("  discovery, so the macro regime is shared. Only the instrument is")
    print("  new. A pass is weaker evidence than a true out-of-period holdout.")
    print("  Rule and cost convention unchanged. Entry bar excluded.\n")
    print(f"  {'inst':<10}{'sessions':>9}{'qualif':>7}{'trades':>8}{'expR':>9}"
          f"{'PF':>7}{'t':>7}{'yrs+':>7}{'ex-top1%':>9}{'+50%cost':>10}"
          f"{'med risk':>10}{'cost/R':>7}{'amb':>6}{'look':>6}{'':>10}")
    out = []
    for sym in SYMS:
        p = ROOT / f"data/related/{sym}_5m.parquet"
        if not p.exists():
            print(f"  {sym:<10}   not fetched")
            continue
        d = pd.read_parquet(p)
        T, m = run(d, sym)
        tot = d[(d.timestamp.dt.year >= 2021) & (d.timestamp.dt.year <= 2025)]
        r = report(T, m, tot.timestamp.dt.date.nunique())
        if r: out.append(r)
    if out:
        print(f"\n  BY YEAR — mean R")
        yrs = sorted({y for r in out for y in r["yrs"].index})
        print(f"  {'inst':<10}" + "".join(f"{y:>11}" for y in yrs))
        for r in out:
            print(f"  {r['name']:<10}" + "".join(
                f"{r['yrs'][y]:>+11.4f}" if y in r["yrs"].index else f"{'--':>11}"
                for y in yrs))
        print(f"\n  EXITS / FILLS")
        print(f"  {'inst':<10}{'mean MFE':>10}{'mean MAE':>10}"
              f"{'naive expR':>12}{'correction':>12}{'exit mix':>40}")
        for r in out:
            T = r["T"]
            print(f"  {r['name']:<10}{T.mfe.mean():>+10.3f}{T.mae.mean():>+10.3f}"
                  f"{T.naive_R.mean():>+12.4f}"
                  f"{T.naive_R.mean()-T.R.mean():>+12.4f}"
                  f"{str(T.why.value_counts().to_dict()):>40}")

    # ---------------------------------------------------------------- pooled
    if not out:
        sys.exit(0)
    A = pd.concat([r["T"].assign(inst=r["name"]) for r in out], ignore_index=True)

    print("\n" + "=" * 130)
    print("  POOLED NON-QQQ ESTIMATE")
    print("=" * 130)
    print("  The SE is CLUSTERED BY DATE. All instruments trade the same 1,255")
    print("  sessions and move together, so per-trade independence is false and")
    print("  the naive SE is too small. The clustered figure governs; the naive")
    print("  one is printed only so the size of the mistake is visible.\n")
    print("  XLK holds the large-cap US technology names that dominate QQQ by")
    print("  weight. It is the LEAST INDEPENDENT instrument in the set and is")
    print("  EXCLUDED from the headline pooling. Both versions are shown.\n")

    print(f"  {'set':<26}{'trades':>8}{'dates':>7}{'mean R':>9}{'sd':>8}"
          f"{'naive SE':>10}{'clus SE':>9}{'t clus':>8}"
          f"{'95% CI (clustered)':>26}")
    pooled = {}
    for label, syms in (("HEADLINE  SPY IWM IJH EFA", HEADLINE),
                        ("all five  + XLK", SYMS)):
        S = A[A.inst.isin(syms)]
        R = S.R.to_numpy(float)
        mu = R.mean()
        se_n = R.std(ddof=1) / sqrt(len(R))
        se_c, g = cluster_se(R, S.day.to_numpy())
        lo, hi_ = mu - 1.96 * se_c, mu + 1.96 * se_c
        pooled[label] = dict(mu=mu, se=se_c, n=len(R), g=g, lo=lo, hi=hi_)
        print(f"  {label:<26}{len(R):>8,}{g:>7,}{mu:>+9.4f}"
              f"{R.std(ddof=1):>8.4f}{se_n:>10.4f}{se_c:>9.4f}"
              f"{mu/se_c:>+8.2f}   [{lo:>+7.4f}, {hi_:>+7.4f}]")

    # Per-date estimator. NOTE: this is NOT the same estimand. It equal-weights
    # dates; the per-trade mean weights dates by how many instruments traded
    # them. The two disagree, and the reason is shown immediately below.
    print(f"\n  RE-WEIGHTING DIAGNOSTIC — equal-weight by DATE instead of by trade")
    print(f"  This answers a DIFFERENT question and is NOT comparable to the")
    print(f"  discovery figure. It is shown because the two disagree.\n")
    print(f"  {'set':<26}{'dates':>8}{'mean R':>9}{'sd':>8}{'SE':>9}{'t':>8}"
          f"{'95% CI':>26}")
    for label, syms in (("HEADLINE  SPY IWM IJH EFA", HEADLINE),
                        ("all five  + XLK", SYMS)):
        S = A[A.inst.isin(syms)]
        v = S.groupby("day").R.mean().to_numpy(float)
        mu = v.mean(); se = v.std(ddof=1) / sqrt(len(v))
        print(f"  {label:<26}{len(v):>8,}{mu:>+9.4f}{v.std(ddof=1):>8.4f}"
              f"{se:>9.4f}{mu/se:>+8.2f}   "
              f"[{mu-1.96*se:>+7.4f}, {mu+1.96*se:>+7.4f}]")

    print(f"\n  WHY THEY DISAGREE — headline set, by how many of the four")
    print(f"  instruments qualified and traded that date (k):")
    S = A[A.inst.isin(HEADLINE)]
    k = S.groupby("day").R.agg(["size", "mean"])
    print(f"  {'k':>3}{'dates':>8}{'trades':>8}{'mean R':>10}"
          f"{'share of trades':>17}")
    for kk, g in k.groupby("size"):
        print(f"  {kk:>3}{len(g):>8,}{kk*len(g):>8,}{g['mean'].mean():>+10.4f}"
              f"{100*kk*len(g)/len(S):>16.1f}%")
    print(f"\n  The whole pooled effect sits on the dates where MOST instruments")
    print(f"  qualify at once. Those dates also carry most of the trades, so")
    print(f"  per-trade weighting lands at {S.R.mean():+.4f} while equal-weighting")
    print(f"  dates lands at {k['mean'].mean():+.4f}. The per-trade figure is the one")
    print(f"  that matches the discovery estimand -- expected R per trade taken --")
    print(f"  and it is the one carried forward. The k pattern is NOT actionable:")
    print(f"  it was found in this data, it is a new free parameter, and k is not")
    print(f"  knowable at 10:30 without watching four instruments at once.")

    print(f"\n  PER-INSTRUMENT MEAN R, side by side with the discovery figure")
    print(f"  {'QQQ 2021-2025 (discovery, frozen)':<38}{DISC_MEAN:>+9.4f}"
          f"   {DISC_TRADES} trades")
    for r in out:
        T = r["T"]
        se_c, _ = cluster_se(T.R.to_numpy(float), T.day.to_numpy())
        tag = "  <- overlaps QQQ, not independent" if r["name"] == "XLK" else ""
        print(f"  {r['name']:<38}{T.R.mean():>+9.4f}   {len(T)} trades"
              f"   clus SE {se_c:.4f}{tag}")

    # -------------------------------------------------- holdout power, 1-sided
    print("\n" + "=" * 130)
    print("  IMPLIED HOLDOUT POWER AT THE POOLED EFFECT SIZE — ONE-SIDED")
    print("=" * 130)
    rate = DISC_TRADES / DISC_SESSIONS
    n_hold = int(round(HOLDOUT_SESSIONS * rate))
    z_a = 1.6449                                   # one-sided alpha = 0.05
    print(f"  Sealed holdout 2016-2020: {HOLDOUT_SESSIONS:,} sessions."
          f"  Discovery trade rate {100*rate:.1f}%"
          f"  -> expect ~{n_hold} trades.")
    print(f"  One candidate, one test, so no Bonferroni: one-sided alpha = 0.05,"
          f" z = {z_a}.  sd = {DISC_SD}.")
    print(f"  NOTHING IN 2016-2020 IS READ. This is an arithmetic projection.\n")
    print(f"  {'effect assumed':<44}{'delta R':>9}{'power':>9}"
          f"{'trades for 80%':>16}")
    cands = [("discovery estimate (QQQ, in-sample)", DISC_MEAN)]
    for label, d in pooled.items():
        cands.append((f"pooled {label.split()[0].lower()}: {d['mu']:+.4f}", d["mu"]))
        cands.append((f"   its CI lower bound {d['lo']:+.4f}", d["lo"]))
        cands.append((f"   its CI upper bound {d['hi']:+.4f}", d["hi"]))
    cands.append(("the decision-rule threshold +0.05", 0.05))
    for label, d in cands:
        if d <= 0:
            print(f"  {label:<44}{d:>+9.4f}{'n/a':>9}{'infinite':>16}"
                  f"   (effect <= 0)")
            continue
        pw = ncdf(d * sqrt(n_hold) / DISC_SD - z_a)
        need = int(np.ceil(((z_a + 0.8416) * DISC_SD / d) ** 2))
        print(f"  {label:<44}{d:>+9.4f}{100*pw:>8.0f}%{need:>16,}")
    print(f"\n  MDE at {n_hold} trades, one-sided, 80% power:"
          f"  {(z_a + 0.8416) * DISC_SD / sqrt(n_hold):+.4f} R per trade")
    print("\n  Sealed NQ days were not read. 2016-2020 remains sealed.")
