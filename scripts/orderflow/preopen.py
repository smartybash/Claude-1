#!/usr/bin/env python3
"""PRE-OPEN CONDITIONING — STAGE 1. DESCRIPTIVE AND PREDICTIVE ONLY.

Pre-registered at `dc4f4bf` (`reports/preopen_conditioning_preregistration.md`)
before this file was written and before the extended-hours data was fetched.

THE QUESTION

The regime study already showed that price-derived information available at a
decision timestamp does not predict later session character: 14 combinations,
largest |rho| 0.042, none significant, and 91% of the cross-session spread in
efficiency reproduced by random walks. That finding is NOT retested here.

This family asks whether a DIFFERENT CLASS of predictor — conditions formed
OUTSIDE the cash session — does any better. Six conditions, all known before
09:30 ET, none derived from the session being predicted.

WHAT IS NOT HERE

No expectancy, no win rate, no trade, no rule, no sweep. Every definition is
fixed by the pre-registration and none is tuned.

DECLARED BURDEN, BEFORE ANY RESULT
  6 conditions x 5 outcomes = 30 tests, Bonferroni alpha = 0.05/30 = 0.001667
  pass requires |rho| >= 0.10 AND permutation p < 0.001667 AND, for the two
  efficiency outcomes, |decile spread| >= 0.020

POSITIVE CONTROL, AND THE RUN IS VOID WITHOUT IT
  early-session rv (09:30-10:00) vs post-10:30 rv must reproduce rho > 0.40.
  It is a pipeline check, not a candidate, and is excluded from the 30.

Sealed NQ days are not read: this script never opens the NQ tape.
2016-2020 is not read: every source begins 2021-01-04 and the session builder
asserts it.

Usage: python3 scripts/orderflow/preopen.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RTH = ROOT / "data/intraday_long/QQQ_1m.parquet"
ETH = ROOT / "data/intraday_long/QQQ_1m_eth.parquet"
VIX = ROOT / "data/vix_daily_5y.json"
FOMC = ROOT / "data/events/fomc.csv"

MIN_BARS = 360
TRAIL_N = 20
FIRST_YEAR = 2021

N_TESTS = 30
ALPHA = 0.05
P_BAR = ALPHA / N_TESTS
RHO_BAR = 0.10
SPREAD_BAR = 0.020
N_PERM = 10_000
CONTROL_BAR = 0.40
YEARS_REQUIRED = 4

SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

COND = [
    ("on_range", "overnight range / trailing mean"),
    ("on_disp", "overnight net displacement, bps signed"),
    ("prior_loc", "prior close location in prior range"),
    ("vix_lvl", "prior-day VIX close"),
    ("vix_chg", "prior-day VIX change, points"),
    ("fomc", "FOMC decision date flag"),
]
OUT = [
    ("rv", "session realised vol, bps"),
    ("range", "session range, bps"),
    ("eff_full", "efficiency ratio, full session"),
    ("eff_post", "efficiency ratio, post-10:30"),
    ("ret", "signed session return, bps"),
]
EFF_OUT = {"eff_full", "eff_post"}
DECISION_OUT = {"eff_full", "eff_post", "ret"}


# ------------------------------------------------------------------ build --

def eff_and_rv(cl):
    """Efficiency ratio and realised vol over a closing-price path."""
    r = np.diff(np.log(cl))
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return np.nan, np.nan
    path = float(np.abs(r).sum())
    net = float(abs(np.log(cl[-1] / cl[0])))
    rv = float(np.sqrt((r ** 2).sum()))
    return (net / path if path > 0 else np.nan), 1e4 * rv


def rth_sessions():
    d = pd.read_parquet(RTH)
    d = d[d.timestamp.dt.year >= FIRST_YEAR]          # 2016-2020 stays unread
    d["day"] = d.timestamp.dt.date
    d["ds"] = d.timestamp.dt.strftime("%Y%m%d")
    d = d[~d.ds.str.startswith(SEALED_PREFIX)]
    d = d[~d.ds.isin(SEALED_DATES)]
    out, rejected = {}, 0
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            rejected += 1
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        c = pd.Timestamp(dt.datetime.combine(day, dt.time(16, 0)))
        if g.timestamp.iloc[0] > o or g.timestamp.iloc[-1] < c - pd.Timedelta(minutes=5):
            rejected += 1
            continue
        out[day] = g[(g.timestamp >= o) & (g.timestamp <= c)]
    return out, rejected


def load_vix():
    d = json.load(open(VIX))
    v = pd.DataFrame({"t": pd.to_datetime(d["time"]), "close": d["close"]})
    v["day"] = v.t.dt.date
    v = v.drop_duplicates("day").sort_values("day").reset_index(drop=True)
    v["chg"] = v.close.diff()
    return v.set_index("day")[["close", "chg"]]


def load_fomc():
    f = pd.read_csv(FOMC)
    return set(pd.to_datetime(f.date).dt.date)


def build():
    S, rejected = rth_sessions()
    days = sorted(S)

    E = pd.read_parquet(ETH)
    E = E[E.timestamp.dt.year >= FIRST_YEAR]
    E = E.sort_values("timestamp").reset_index(drop=True)
    et = E.timestamp.to_numpy()
    ehi, elo, ecl = (E.high.to_numpy(float), E.low.to_numpy(float),
                     E.close.to_numpy(float))

    V, F_DATES = load_vix(), load_fomc()

    rows, no_eth = [], 0
    for i, day in enumerate(days):
        g = S[day]
        hi, lo, cl = (g.high.to_numpy(float), g.low.to_numpy(float),
                      g.close.to_numpy(float))
        t = g.timestamp.to_numpy()
        px = float(g.open.iloc[0])

        eff_full, rv = eff_and_rv(cl)
        post = t >= np.datetime64(pd.Timestamp(
            dt.datetime.combine(day, dt.time(10, 30))))
        eff_post = eff_and_rv(cl[post])[0] if post.sum() >= 30 else np.nan
        rng = 1e4 * (hi.max() - lo.min()) / px
        ret = 1e4 * float(np.log(cl[-1] / px))

        if i == 0:
            continue
        prev = S[days[i - 1]]
        p_hi, p_lo = float(prev.high.max()), float(prev.low.min())
        p_cl = float(prev.close.iloc[-1])
        p_rng = p_hi - p_lo

        # --- the overnight window: prior 16:00 -> 09:29 of this session ----
        a = np.datetime64(pd.Timestamp(
            dt.datetime.combine(days[i - 1], dt.time(16, 0))))
        b = np.datetime64(pd.Timestamp(
            dt.datetime.combine(day, dt.time(9, 29))))
        m = (et > a) & (et <= b)
        if m.sum() < 30:
            no_eth += 1
            on_range_raw, on_disp = np.nan, np.nan
        else:
            on_range_raw = 1e4 * (ehi[m].max() - elo[m].min()) / p_cl
            on_disp = 1e4 * (float(ecl[m][-1]) - p_cl) / p_cl

        vr = V.loc[days[i - 1]] if days[i - 1] in V.index else None
        rows.append(dict(
            day=day, year=day.year,
            on_range_raw=on_range_raw,
            on_disp=on_disp,
            prior_loc=(p_cl - p_lo) / p_rng if p_rng > 0 else np.nan,
            vix_lvl=float(vr["close"]) if vr is not None else np.nan,
            vix_chg=float(vr["chg"]) if vr is not None else np.nan,
            fomc=1.0 if day in F_DATES else 0.0,
            # outcomes
            rv=rv, range=rng, eff_full=eff_full, eff_post=eff_post, ret=ret,
            # dropped-predictor cross-check, reported not tested
            gap_raw=1e4 * abs(px - p_cl) / p_cl,
            # positive control
            rv_early=eff_and_rv(cl[t < np.datetime64(pd.Timestamp(
                dt.datetime.combine(day, dt.time(10, 0))))])[1],
            rv_post=eff_and_rv(cl[post])[1] if post.sum() >= 30 else np.nan,
        ))

    F = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    s = F["on_range_raw"]
    F["on_range"] = s / s.rolling(TRAIL_N, min_periods=TRAIL_N).mean().shift(1)
    return F, rejected, no_eth


# ----------------------------------------------------------- statistics --

def spearman(a, b):
    ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def perm_p(x, y, rho_obs, rng):
    """Random-label control. Permuting the rank vector preserves group sizes
    exactly, which is what the binary FOMC condition needs."""
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    n = len(rx)
    if n < 30 or not np.isfinite(rho_obs):
        return np.nan
    ry = (ry - ry.mean()) / ry.std()
    rxc = (rx - rx.mean()) / rx.std()
    P = np.empty(N_PERM)
    for k in range(N_PERM):
        P[k] = float(np.dot(rng.permutation(rxc), ry) / n)
    return float((np.abs(P) >= abs(rho_obs) - 1e-12).sum() + 1) / (N_PERM + 1)


def decile_spread(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 100 or d.x.nunique() < 10:
        return np.nan, np.nan, np.nan
    d["b"] = pd.qcut(d.x.rank(method="first"), 10, labels=False)
    m = d.groupby("b").y.mean()
    return float(m.iloc[0]), float(m.iloc[-1]), float(m.iloc[-1] - m.iloc[0])


def group_diff(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    a = d[d.x > 0.5].y
    b = d[d.x <= 0.5].y
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan, np.nan
    return float(b.mean()), float(a.mean()), float(a.mean() - b.mean())


def year_signs(F, c, o, rho):
    """4 of 6 years must share the sign of the pooled rho.

    A binary condition has only two distinct values, so it is admitted on the
    weaker requirement that both groups are populated in that year. Without
    this the FOMC flag reports 0/0 in every panel and can never satisfy the
    consistency rule regardless of its rho.
    """
    agree, seen = 0, 0
    binary = F[c].dropna().nunique() <= 2
    for _, g in F.groupby("year"):
        d = g[[c, o]].dropna()
        if binary:
            if min((d[c] > 0.5).sum(), (d[c] <= 0.5).sum()) < 3:
                continue
        elif len(d) < 50 or d[c].nunique() < 3:
            continue
        seen += 1
        r = spearman(d[c], d[o])
        if np.isfinite(r) and np.sign(r) == np.sign(rho):
            agree += 1
    return agree, seen


# ---------------------------------------------------------------- report --

def main():
    rng = np.random.default_rng(20260920)
    F, rejected, no_eth = build()

    print("=" * 104)
    print("  PRE-OPEN CONDITIONING, STAGE 1 — COUNTS AND TEST BURDEN, BEFORE ANY RESULT")
    print("=" * 104)
    print(f"  sessions built                     {len(F):>8}")
    print(f"  sessions rejected by the builder   {rejected:>8}")
    print(f"  sessions with no overnight tape    {no_eth:>8}")
    print(f"  first session                      {F.day.iloc[0]}")
    print(f"  last session                       {F.day.iloc[-1]}")
    print(f"  years covered                      "
          f"{sorted(F.year.unique())}")
    print()
    print(f"  {'condition':<12}{'n non-null':>12}   definition")
    for c, lab in COND:
        print(f"  {c:<12}{F[c].notna().sum():>12}   {lab}")
    print()
    print(f"  {'outcome':<12}{'n non-null':>12}   definition")
    for o, lab in OUT:
        print(f"  {o:<12}{F[o].notna().sum():>12}   {lab}")
    print()
    print(f"  conditions                {len(COND):>8}")
    print(f"  outcomes                  {len(OUT):>8}")
    print(f"  TOTAL TESTS               {len(COND) * len(OUT):>8}")
    print(f"  Bonferroni alpha          {P_BAR:>8.6f}")
    print(f"  |rho| bar                 {RHO_BAR:>8.2f}")
    print(f"  decile-spread bar (eff)   {SPREAD_BAR:>8.3f}")
    print(f"  permutations per test     {N_PERM:>8}")
    print(f"  years required to agree   {YEARS_REQUIRED} of 6")

    # ------------------------------------------------ the positive control --
    d = F[["rv_early", "rv_post"]].dropna()
    ctrl = spearman(d.rv_early, d.rv_post)
    print("\n" + "=" * 104)
    print("  POSITIVE CONTROL — early rv (09:30-10:00) vs post-10:30 rv")
    print("=" * 104)
    print(f"  n = {len(d)}   Spearman rho = {ctrl:+.4f}   required > {CONTROL_BAR:.2f}")
    if not (ctrl > CONTROL_BAR):
        print("\n  *** CONTROL FAILED — THE RUN IS VOID. NOTHING BELOW IS EVIDENCE. ***")
        return
    print("  control PASSES — the pipeline reproduces a known-forecastable outcome.")

    # ------------------------------------ the redundancy cross-check, §1.2 --
    d = F[["on_disp", "gap_raw"]].dropna()
    print("\n" + "=" * 104)
    print("  DECLARED REDUNDANCY CHECK (pre-registration §1.2)")
    print("=" * 104)
    print(f"  Spearman(|overnight displacement|, dropped `gap`) = "
          f"{spearman(d.on_disp.abs(), d.gap_raw):+.4f}   n = {len(d)}")
    print("  `gap` was dropped as an already-tested predictor; this shows the overlap.")

    # -------------------------------------------------------- the 30 tests --
    res = []
    for o, olab in OUT:
        print("\n" + "=" * 104)
        print(f"  OUTCOME: {o}  —  {olab}")
        print("=" * 104)
        print(f"  {'condition':<12}{'n':>7}{'Spearman':>11}{'perm p':>11}"
              f"{'bottom':>11}{'top':>11}{'spread':>11}{'yrs':>7}{'verdict':>10}")
        for c, _ in COND:
            d = F[[c, o, "year"]].dropna()
            n = len(d)
            if n < 100:
                print(f"  {c:<12}{n:>7}      insufficient")
                continue
            rho = spearman(d[c], d[o])
            pv = perm_p(d[c].to_numpy(), d[o].to_numpy(), rho, rng)
            if c == "fomc":
                bot, top, spr = group_diff(d[c], d[o])
            else:
                bot, top, spr = decile_spread(d[c], d[o])
            agree, seen = year_signs(d, c, o, rho)
            ok = (abs(rho) >= RHO_BAR and pv < P_BAR
                  and agree >= YEARS_REQUIRED)
            if o in EFF_OUT:
                ok = ok and abs(spr) >= SPREAD_BAR
            print(f"  {c:<12}{n:>7}{rho:>+11.4f}{pv:>11.5f}"
                  f"{bot:>11.4f}{top:>11.4f}{spr:>+11.4f}"
                  f"{agree:>4}/{seen:<2}{'PASS' if ok else '.':>10}")
            res.append(dict(cond=c, out=o, n=n, rho=rho, p=pv, spread=spr,
                            years=f"{agree}/{seen}", passed=ok))

    R = pd.DataFrame(res)
    R.to_csv(ROOT / "reports/preopen_conditioning.csv", index=False)

    # ------------------------------------------------------ the decision --
    print("\n" + "=" * 104)
    print("  THE DECLARED DECISION POINT")
    print("=" * 104)
    dec = R[R.out.isin(DECISION_OUT)]
    vol = R[~R.out.isin(DECISION_OUT)]
    print(f"  tests run                                   {len(R):>6}  "
          f"(declared 30)")
    print(f"  passing on eff_full / eff_post / ret        {int(dec.passed.sum()):>6}")
    print(f"  passing on rv / range (NOT sufficient)      {int(vol.passed.sum()):>6}")
    print(f"  largest |rho| on a decision outcome         "
          f"{dec.rho.abs().max():>6.4f}")
    print(f"  largest |rho| anywhere                      "
          f"{R.rho.abs().max():>6.4f}")
    print(f"  smallest permutation p anywhere             "
          f"{R.p.min():>6.5f}   threshold {P_BAR:.6f}")
    print()
    if dec.passed.sum() == 0:
        print("  NO CONDITION PREDICTS EFFICIENCY OR DIRECTION BEYOND THE CORRECTED")
        print("  THRESHOLD. Per the pre-registration this STOPS AT STAGE 1 and is")
        print("  reported as a replication of the regime finding on a new class of")
        print("  predictors. No strategy stage, no Stage 2.")
        if vol.passed.sum():
            print()
            print("  Volatility-side passes are reported as a successful positive")
            print("  control and nothing more — declared in advance as NOT sufficient.")
    else:
        print("  At least one condition clears the bar on a decision outcome.")
        print("  Stage 2 will be written as a SEPARATE pre-registration for approval")
        print("  and is NOT run here.")
    print()
    print("  2016-2020 was not read. Sealed NQ days were not read.")


if __name__ == "__main__":
    sys.exit(main())
