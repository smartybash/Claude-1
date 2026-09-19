#!/usr/bin/env python3
"""THE BROAD SCREEN: the same pullback rule, on QQQ one-minute bars, 2021-2026.

Grid and rejection criteria pre-registered at 697fd55
(`reports/qqq_screen_preregistration.md`, sections 6 and 7) before this ran.
The bar-resolution gate that licenses the use of one-minute data is at 26e0350
(`reports/bar_resolution_gate.md`).

WHY QQQ AT ALL

Twenty NQ sessions can detect an 18-point-per-session effect and nothing
smaller. A realistic edge needs several hundred sessions. QQQ has 1,400-odd
and tracks the same index, so it can reject things twenty sessions cannot.

WHAT HAD TO BE RESTATED, AND WHAT DID NOT

The rule is scale-free -- excursion is a multiple of the opening range, the
stop a multiple of ATR, the target a multiple of risk -- so none of THAT
changes. Four constants were written in NQ points and mean nothing on a $600
share, so each is restated as the same fraction of price:

    break        0.50 NQ pts  ->  0.167 bps
    rejection    1.00 NQ pts  ->  0.333 bps
    stop floor   2.00 NQ pts  ->  0.667 bps
    cost         2.00 NQ pts  ->  0.667 bps  round turn

The cost figure is deliberately the NQ one. On QQQ it is about four cents a
round turn against a penny spread, which is generous to the point of harsh --
and harsh is the right direction for a screen.

THE CLOCK IS NOT FIXED IN ET

Flat is 22:30 Dubai, which is 18:30 UTC, which is 14:30 ET in US summer and
13:30 ET in US winter. The trading window is genuinely an hour shorter for
roughly four months of the year and is modelled that way, per session, rather
than pinned to a single ET time.

Usage: python3 scripts/orderflow/qqq_screen.py
"""
from __future__ import annotations

import datetime as dt
import sys
from itertools import product
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pullback import ATR_BARS, EXC_FIXED, run_session                  # noqa

SRC = Path(__file__).resolve().parents[2] / "data/intraday_long/QQQ_1m.parquet"
ET = ZoneInfo("America/New_York")

# the four NQ constants as a fraction of price
BREAK_F = 0.50 / 30000.0
REJ_F = 1.00 / 30000.0
FLOOR_F = 2.00 / 30000.0
COST_F = 2.00 / 30000.0

FLAT_UTC = (18, 30)
LAST_ENTRY_UTC = (18, 0)
MIN_BARS = 360          # of 390; excludes half days and broken sessions

# pre-registered grid, section 6
G_OR = (15, 30)
G_SATR = (0.5, 1.0)
G_TGT = (1.0, 2.0, 3.0, 4.0)


def et_wall(day: dt.date, hh: int, mm: int) -> pd.Timestamp:
    """The ET wall-clock time matching hh:mm UTC on that date."""
    u = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=dt.timezone.utc)
    return pd.Timestamp(u.astimezone(ET).replace(tzinfo=None))


def build_sessions():
    d = pd.read_parquet(SRC)
    d["day"] = d.timestamp.dt.date
    out, rejected = {}, 0
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            rejected += 1
            continue
        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        flat_t = et_wall(day, *FLAT_UTC)
        last_e = et_wall(day, *LAST_ENTRY_UTC)
        if g.timestamp.iloc[0] > open_t or g.timestamp.iloc[-1] < flat_t:
            rejected += 1
            continue
        g = g[(g.timestamp >= open_t) & (g.timestamp <= flat_t)]
        if len(g) < 120:
            rejected += 1
            continue
        hi = g.high.to_numpy(np.float64)
        lo = g.low.to_numpy(np.float64)
        op = g.open.to_numpy(np.float64)
        rng = pd.Series(hi - lo)
        atr = (rng.rolling(ATR_BARS, min_periods=10).mean().shift(1)
               .to_numpy(np.float64))
        px0 = float(g.open.iloc[0])
        out[day] = dict(
            bars=(g.timestamp.to_numpy(), hi, lo, op, open_t, flat_t, atr),
            last_entry=last_e, px=px0,
            brk=px0 * BREAK_F, rej=px0 * REJ_F,
            floor=px0 * FLOOR_F, cost=px0 * COST_F)
    return out, rejected


def evaluate(S, or_min, satr, tgt):
    rows = []
    for day, s in S.items():
        for tr in run_session(s["bars"], or_min, satr, tgt, exc=EXC_FIXED,
                              brk=s["brk"], rej=s["rej"], floor=s["floor"],
                              cost=s["cost"], last_entry=s["last_entry"]):
            rows.append(dict(day=day, R=tr["pnl"] / tr["risk"],
                             why=tr["why"], amb=tr["ambiguous"],
                             risk_bps=1e4 * tr["risk"] / s["px"]))
    T = pd.DataFrame(rows)
    if not T.empty:
        T["year"] = pd.to_datetime(T.day).dt.year
    return T


def main():
    S, rej = build_sessions()
    days = sorted(S)
    years = sorted({d.year for d in days})
    print("=" * 104)
    print("QQQ BROAD SCREEN — 16 PRE-REGISTERED VARIANTS, ONE-MINUTE BARS")
    print("=" * 104)
    print(f"  sessions used   : {len(days):,}   "
          f"{days[0]} to {days[-1]}")
    print(f"  sessions dropped: {rej}  (short, half day, or not reaching the "
          f"flat time)")
    print(f"  per year: " + "  ".join(
        f"{y} {sum(1 for d in days if d.year == y)}" for y in years))
    print(f"  cost {1e4 * COST_F:.3f} bps round turn   stop floor "
          f"{1e4 * FLOOR_F:.3f} bps   flat 18:30 UTC (14:30 ET summer, "
          f"13:30 ET winter)")
    print(f"  max 2 trades/session, never concurrent. Results in R, never "
          f"points.\n")

    res = {}
    print("  TRADE AND SESSION COUNTS FIRST, before any performance number:\n")
    print(f"  {'variant':<20}{'trades':>9}{'sessions':>10}{'trades/sess':>13}"
          f"{'med risk':>10}{'expiry%':>9}{'ambiguous%':>12}")
    for om, sa, tg in product(G_OR, G_SATR, G_TGT):
        k = f"OR{om} SATR{sa} R{tg}"
        T = evaluate(S, om, sa, tg)
        res[k] = T
        ns = T.day.nunique()
        print(f"  {k:<20}{len(T):>9,}{ns:>10,}{len(T) / max(ns, 1):>13.2f}"
              f"{T.risk_bps.median():>9.1f}b{100 * (T.why == 'expiry').mean():>8.1f}%"
              f"{100 * T.amb.mean():>11.2f}%")

    print("\n" + "=" * 104)
    print("  PERFORMANCE — expectancy in R, t across sessions (zero-trade "
          "sessions count as zero)")
    print("=" * 104)
    print(f"  {'variant':<20}{'n':>7}{'expR':>8}{'win%':>7}{'PF':>7}"
          f"{'sess t':>8}{'sess+':>7}{'ex-top1%':>10}{'amb%':>7}"
          f"{'+ve years':>11}")
    M = {}
    for k, T in res.items():
        R = T.R
        w, l = R[R > 0], R[R <= 0]
        pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else np.inf
        per = R.groupby(T.day).sum().reindex(days).fillna(0.0)
        t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per)))
        cut = int(np.ceil(0.01 * len(R)))
        ex1 = R.sum() - R.sort_values(ascending=False).head(cut).sum()
        yr = R.groupby(T.year).sum()
        pos_y = int((yr > 0).sum())
        M[k] = dict(exp=R.mean(), t=t, pf=pf, ex1=ex1, pos_y=pos_y,
                    n=len(R), yr=yr, per=per)
        print(f"  {k:<20}{len(R):>7,}{R.mean():>+8.3f}{100 * (R > 0).mean():>7.1f}"
              f"{pf:>7.2f}{t:>+8.2f}{int((per > 0).sum()):>7}"
              f"{ex1:>+10.1f}{100 * T.amb.mean():>7.2f}"
              f"{pos_y:>7}/{len(yr):<3}")

    print("\n" + "=" * 104)
    print("  BY YEAR, total R  (criterion 5: positive in at least 4)")
    print("=" * 104)
    print(f"  {'variant':<20}" + "".join(f"{y:>9}" for y in years))
    for k in res:
        yr = M[k]["yr"].reindex(years).fillna(0.0)
        print(f"  {k:<20}" + "".join(f"{v:>+9.1f}" for v in yr))

    print("\n" + "=" * 104)
    print("  REJECTION CRITERIA, FIXED IN ADVANCE (pre-registration section 7)")
    print("=" * 104)
    print("  1 expectancy <= 0 in R   2 t <= 3 across sessions   3 PF < 1.15")
    print("  4 top-1% dependent   5 positive in fewer than 4 calendar years")
    print("  Bonferroni over 16 tests puts the honest bar at t > 3.5; "
          "criterion 2 is\n  stated at 3.0 and the stricter figure is applied "
          "when judging survivors.\n")
    surv = []
    for k in res:
        m = M[k]
        f = []
        if m["exp"] <= 0:
            f.append("1 expectancy")
        if m["t"] <= 3.0:
            f.append(f"2 t {m['t']:+.2f}")
        if m["pf"] < 1.15:
            f.append(f"3 PF {m['pf']:.2f}")
        if m["ex1"] <= 0:
            f.append("4 top-1% dependent")
        if m["pos_y"] < 4:
            f.append(f"5 only {m['pos_y']} positive years")
        if f:
            print(f"  {k:<20} REJECT  {'; '.join(f)}")
        else:
            surv.append(k)
            print(f"  {k:<20} SURVIVES  t {m['t']:+.2f}"
                  f"{'  (clears the Bonferroni bar too)' if m['t'] > 3.5 else '  (below the Bonferroni bar of 3.5)'}")
    print(f"\n  survivors: {len(surv)} of 16")
    print("\n  A SURVIVOR IS A CANDIDATE, NOT A FINDING. It has passed a real "
          "test on a\n  proxy instrument. It is not a result for NQ until it "
          "is re-run on the 20\n  tick sessions with every outcome decided by "
          "the tape.")


if __name__ == "__main__":
    main()
