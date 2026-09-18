#!/usr/bin/env python3
"""A SETUP GRADING SCHEME, TESTED AS AN OBJECT.

Pre-registered at `bb0ab30` (`reports/setup_grading_preregistration.md`) before
this ran.

Grades are applied to trades the EXISTING ORB and pullback machines already
generate. No new rule, no re-tuned parameter, no trade added or removed. The
only question is whether the label separates outcome.

THE GRADES, fixed in advance -- one point each:
    cost / realised risk <= 5.0%
    OR height / trailing 20-session mean >= 1.00
    minutes since the cash open <= 60
    A+ = 3 of 3,  A = 2 of 3,  B = 0 or 1

TWO THINGS DECLARED BEFORE THE RESULT

  * Two of three components are ALREADY KNOWN NULL. The OR ratio was the whole
    hypothesis of the OR-height screen (0 of 4, in-sample and held out). Time of
    day is already printed by bucket in the existing runs with no gradient.

  * The third is an ACCOUNTING IDENTITY, not a prediction. R = gross/risk -
    cost/risk, so expectancy differs between grades by the cost differential
    whether or not the market cooperates. Some separation is expected BY
    CONSTRUCTION and this test must not take credit for it. Hence the gross-R
    decomposition on every table: if the spread lives entirely in the cost term,
    the finding is "wider stops pay a smaller toll", not "grade predicts
    outcome".

THE CONTROL: 1,000 random assignments reproducing the observed grade proportions
exactly, over the same pooled trades -- which also preserves the correlation
structure that pooling six overlapping trade sets creates.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/setup_grading.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import or_height as OH                                                 # noqa
import pullback as PB                                                  # noqa

ROOT = Path(__file__).resolve().parents[2]

COST_BPS = 1e4 * OH.COST_F            # 0.667 bps
CR_BAR = 5.0                          # cost/risk %, <= is a point
OR_BAR = 1.00                         # OR ratio, >= is a point
MIN_BAR = 60                          # minutes since open, <= is a point
MIN_PER_GRADE = 300
N_RAND = 1000
GRADES = ["A+", "A", "B"]
RNG = np.random.default_rng(7)


def grade_of(cr, orr, mins):
    pts = int(cr <= CR_BAR) + int(orr >= OR_BAR) + int(mins <= MIN_BAR)
    return "A+" if pts == 3 else ("A" if pts == 2 else "B")


# ------------------------------------------------------------ trade sets --

def build_trades(S1):
    """Six sets from the two unchanged machines. Returns (DataFrame, meta)."""
    days = sorted(S1)
    rows, meta = [], []

    for om in (15, 30):
        ratio = OH.or_ratio(S1, days, om)
        for tg in (3.0, 4.0):
            look = amb = n = 0
            for day in days:
                tr, lk = OH.run_session(S1[day], om, 1.0, tg)
                look += lk
                orr = ratio.get(day, np.nan)
                for x in tr:
                    n += 1
                    amb += int(x["ambiguous"])
                    rows.append(dict(
                        setname=f"ORB OR{om} R{tg:.0f}", family="ORB",
                        day=day, R=x["R"], naive_R=x["naive_R"],
                        risk_bps=x["risk_bps"], mins=x["mins"],
                        or_ratio=orr, ambiguous=x["ambiguous"]))
            meta.append(dict(setname=f"ORB OR{om} R{tg:.0f}", trades=n,
                             lookahead=look, amb=100 * amb / max(n, 1)))

        # pullback, same surplus region, target 3R
        look = amb = n = 0
        for day in days:
            s = S1[day]
            bars = (s["t"], s["hi"], s["lo"], s["op"], s["open_t"],
                    pd.Timestamp(s["t"][-1]), s["atr"])
            tr = PB.run_session(bars, om, 1.0, 3.0, exc=PB.EXC_FIXED,
                                brk=s["brk"], rej=s["px"] * OH.BREAK_F * 2,
                                floor=s["floor"], cost=s["cost"],
                                last_entry=s["last_entry"])
            orr = ratio.get(day, np.nan)
            for x in tr:
                n += 1
                amb += int(x["ambiguous"])
                risk = x["risk"]
                cr = 100.0 * s["cost"] / risk
                R = x["pnl"] / risk
                # Naive fill, recovered exactly without touching the machine:
                # a stopped trade's naive exit IS the stop price, so its naive
                # R is -(1 + cost/risk). Every other exit is identical.
                nR = -(1.0 + s["cost"] / risk) if x["why"] == "stop" else R
                rows.append(dict(
                    setname=f"pullback OR{om} R3", family="pullback",
                    day=day, R=R, naive_R=nR,
                    risk_bps=1e4 * risk / s["px"],
                    mins=float((x["entry_t"] - np.datetime64(s["open_t"]))
                               / np.timedelta64(1, "m")),
                    or_ratio=orr, ambiguous=x["ambiguous"]))
            # entry lookahead: an entry before the OR window closed
            lv = OH.or_levels(s, om)
            if lv:
                cutoff = np.datetime64(s["open_t"] + pd.Timedelta(minutes=om))
                look += sum(1 for x in tr if x["entry_t"] < cutoff)
        meta.append(dict(setname=f"pullback OR{om} R3", trades=n,
                         lookahead=look, amb=100 * amb / max(n, 1)))

    T = pd.DataFrame(rows).dropna(subset=["or_ratio", "R"])
    T["cost_risk"] = COST_BPS / T.risk_bps * 100.0
    T["gross_R"] = T.R + T.cost_risk / 100.0
    T["grade"] = [grade_of(a, b, c)
                  for a, b, c in zip(T.cost_risk, T.or_ratio, T.mins)]
    T["year"] = pd.to_datetime(T.day).dt.year
    return T, pd.DataFrame(meta)


# ------------------------------------------------------------------- run --

def by_grade(T, col="R"):
    g = T.groupby("grade")[col].agg(["count", "mean"])
    return g.reindex(GRADES)


def main():
    print("=" * 108)
    print("  A SETUP GRADING SCHEME, TESTED AS AN OBJECT")
    print("=" * 108)
    print(f"  A+ = 3 of 3   A = 2 of 3   B = 0 or 1 of 3")
    print(f"  points: cost/risk <= {CR_BAR}%   OR ratio >= {OR_BAR:.2f}   "
          f"minutes since open <= {MIN_BAR}")
    print("  Applied to trades the EXISTING machines generate. No new rule.")

    S1, rej = OH.build("data/intraday_long/QQQ_1m.parquet", 1)
    T, M = build_trades(S1)
    years = sorted(T.year.unique())

    print("\n" + "=" * 108)
    print("  COUNTS FIRST")
    print("=" * 108)
    print(f"  sessions {len(S1):,}   rejected {rej}")
    print(f"\n  {'trade set':<20}{'trades':>9}{'lookahead':>11}{'ambiguous':>11}")
    for _, r in M.iterrows():
        print(f"  {r.setname:<20}{r.trades:>9,}{r.lookahead:>11,}"
              f"{r.amb:>10.1f}%")
    print(f"  {'POOLED':<20}{len(T):>9,}{M.lookahead.sum():>11,}"
          f"{100*T.ambiguous.mean():>10.1f}%")

    print(f"\n  {'grade':<8}{'trades':>9}{'share':>8}{'med cost/risk':>15}"
          f"{'med risk bps':>14}{'med mins':>10}{'med OR ratio':>14}")
    for g in GRADES:
        d = T[T.grade == g]
        print(f"  {g:<8}{len(d):>9,}{100*len(d)/len(T):>7.1f}%"
              f"{d.cost_risk.median():>14.2f}%{d.risk_bps.median():>14.1f}"
              f"{d.mins.median():>10.0f}{d.or_ratio.median():>14.2f}")
    ok_count = all(len(T[T.grade == g]) >= MIN_PER_GRADE for g in GRADES)
    print(f"\n  >= {MIN_PER_GRADE} trades in every grade: "
          f"{'YES' if ok_count else 'NO'}")

    print("\n" + "=" * 108)
    print("  EXPECTANCY BY GRADE — and the decomposition that says what it is")
    print("=" * 108)
    net, gross = by_grade(T, "R"), by_grade(T, "gross_R")
    naive = by_grade(T, "naive_R")
    print(f"  {'grade':<8}{'trades':>9}{'NET expR':>11}{'GROSS expR':>12}"
          f"{'NAIVE expR':>12}{'cost drag':>11}")
    for g in GRADES:
        print(f"  {g:<8}{int(net.loc[g,'count']):>9,}"
              f"{net.loc[g,'mean']:>+11.4f}{gross.loc[g,'mean']:>+12.4f}"
              f"{naive.loc[g,'mean']:>+12.4f}"
              f"{gross.loc[g,'mean']-net.loc[g,'mean']:>+11.4f}")

    s_net = net.loc["A+", "mean"] - net.loc["B", "mean"]
    s_gross = gross.loc["A+", "mean"] - gross.loc["B", "mean"]
    mono = net.loc["A+", "mean"] >= net.loc["A", "mean"] >= net.loc["B", "mean"]
    print(f"\n  A+ minus B, NET   : {s_net:+.4f} R")
    print(f"  A+ minus B, GROSS : {s_gross:+.4f} R   "
          f"<- market behaviour only, cost removed")
    print(f"  the difference    : {s_net - s_gross:+.4f} R   "
          f"<- pure arithmetic, expected by construction")
    print(f"  monotonic A+ >= A >= B: {'YES' if mono else 'NO'}")

    print("\n" + "=" * 108)
    print(f"  THE CONTROL — {N_RAND:,} RANDOM ASSIGNMENTS AT THE SAME "
          f"PROPORTIONS")
    print("=" * 108)
    lab = T.grade.to_numpy().copy()
    r_net, r_gross = [], []
    Rv, Gv = T.R.to_numpy(), T.gross_R.to_numpy()
    for _ in range(N_RAND):
        p = RNG.permutation(lab)
        a, b = p == "A+", p == "B"
        r_net.append(Rv[a].mean() - Rv[b].mean())
        r_gross.append(Gv[a].mean() - Gv[b].mean())
    r_net, r_gross = np.array(r_net), np.array(r_gross)
    pct = 100.0 * (r_net < s_net).mean()
    p95 = np.percentile(r_net, 95)
    beats = s_net > p95
    print(f"  random A+ minus B (net R): mean {r_net.mean():+.4f}   "
          f"sd {r_net.std(ddof=1):.4f}")
    print(f"      5th pct {np.percentile(r_net,5):+.4f}   "
          f"95th pct {p95:+.4f}   max {r_net.max():+.4f}")
    print(f"\n  REAL spread {s_net:+.4f} sits at the {pct:.1f}th percentile "
          f"of random")
    print(f"  beats the 95th percentile: {'YES' if beats else 'NO'}")
    print(f"\n  same control on GROSS R: real {s_gross:+.4f}, random 95th pct "
          f"{np.percentile(r_gross,95):+.4f}   "
          f"{'beats' if s_gross > np.percentile(r_gross,95) else 'does NOT beat'}")

    print("\n" + "=" * 108)
    print("  BY YEAR — net expR")
    print("=" * 108)
    print(f"  {'grade':<8}" + "".join(f"{y:>11}" for y in years))
    for g in GRADES:
        d = T[T.grade == g].groupby("year").R.mean()
        print(f"  {g:<8}" + "".join(
            f"{d[y]:>+11.4f}" if y in d.index else f"{'--':>11}" for y in years))
    hold = 0
    print(f"  {'A+ - B':<8}", end="")
    for y in years:
        a = T[(T.grade == "A+") & (T.year == y)].R.mean()
        b = T[(T.grade == "B") & (T.year == y)].R.mean()
        d = a - b
        if np.isfinite(d) and d > 0:
            hold += 1
        print(f"{d:>+11.4f}" if np.isfinite(d) else f"{'--':>11}", end="")
    print(f"   {hold}/{len(years)}")

    print("\n" + "=" * 108)
    print("  PER TRADE SET — A+ minus B, net R")
    print("=" * 108)
    print(f"  {'trade set':<20}{'A+ n':>8}{'A+ expR':>11}{'B n':>8}"
          f"{'B expR':>11}{'spread':>11}")
    for s in M.setname:
        d = T[T.setname == s]
        a, b = d[d.grade == "A+"], d[d.grade == "B"]
        if a.empty or b.empty:
            continue
        print(f"  {s:<20}{len(a):>8,}{a.R.mean():>+11.4f}{len(b):>8,}"
              f"{b.R.mean():>+11.4f}{a.R.mean()-b.R.mean():>+11.4f}")

    print("\n" + "=" * 108)
    print("  VERDICT — all four required")
    print("=" * 108)
    c = [(f">= {MIN_PER_GRADE} trades per grade", ok_count),
         ("monotonic A+ >= A >= B", bool(mono)),
         ("spread beats 95th pct of random", bool(beats)),
         ("A+ > B in >= 4 of 6 years", hold >= 4)]
    for name, v in c:
        print(f"  {name:<36}{'PASS' if v else 'FAIL':>6}")
    if all(v for _, v in c):
        print("\n  ALL FOUR PASS.")
        if abs(s_gross) < 0.25 * abs(s_net):
            print("  But the spread is essentially ALL cost: the finding is "
                  "'wider stops pay a smaller")
            print("  toll', not 'grade predicts outcome'. No grading scheme is "
                  "warranted.")
    else:
        print("\n  THE GRADING DOES NOT PASS.")
        if not beats:
            print("  The real grading does NOT beat random assignment. Grade "
                  "does not separate outcome.")
    T.to_csv(ROOT / "reports/setup_grading_trades.csv", index=False)
    print("\n  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
