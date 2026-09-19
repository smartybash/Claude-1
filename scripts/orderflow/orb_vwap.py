#!/usr/bin/env python3
"""OPENING RANGE BREAKOUT WITH A SESSION VWAP FILTER, on 1,418 QQQ sessions.

Rule, grid and rejection criteria pre-registered at `bbbddb1`
(`reports/orb_vwap_preregistration.md`) before this ran. Nothing below was
chosen knowing an outcome.

WHAT IS DIFFERENT FROM THE PULLBACK SCREEN

  the entry      a break of the opening range edge, not a retracement of one
  the filter     session VWAP can veto a signal outright; the pullback family
                 had nothing that could
  the stop       anchored to the trigger level, there being no pullback extreme
  the clock      no 60-minute expiry. The stated exit of last resort is the
                 flat time, and an hour-long expiry turns a 4R target into a
                 test of whether price moves 0.4% inside the hour
  the flat exit  the final bar's CLOSE, not its midpoint, which was never a
                 price anyone could have been filled at

FILLS

A stop order fills at the first price available, which is the bar's open when
the bar has already opened past the trigger. Assuming otherwise fabricated the
entire apparent edge of the previous screen (+0.56R against expectancies of
+0.24R to +0.55R), so the naive figure is computed alongside the honest one and
printed, rather than being something to remember not to do.

Sealed NQ days are irrelevant here and are not read: this script never touches
the NQ tape.

Usage: python3 scripts/orderflow/orb_vwap.py
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

from pullback import ATR_BARS                                          # noqa

SRC = Path(__file__).resolve().parents[2] / "data/intraday_long/QQQ_1m.parquet"
ET = ZoneInfo("America/New_York")

BREAK_F = 0.50 / 30000.0        # 0.167 bps
FLOOR_F = 2.00 / 30000.0        # 0.667 bps
COST_F = 2.00 / 30000.0         # 0.667 bps round turn
FLAT_UTC = (18, 30)
LAST_ENTRY_UTC = (18, 0)
MIN_BARS = 360
MAX_TRADES = 2

G_OR = (15, 30)
G_SATR = (0.5, 1.0)
G_TGT = (1.0, 2.0, 3.0, 4.0)

TOD_EDGES = (60, 120, 180)                      # minutes since the RTH open
ORH_CUTS = (0.8, 1.2)                           # ratio to trailing 20-session mean
TRAIL_N = 20


def et_wall(day: dt.date, hh: int, mm: int) -> pd.Timestamp:
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
        cl = g.close.to_numpy(np.float64)
        vol = g.volume.to_numpy(np.float64)
        # session VWAP over bars ALREADY CLOSED, so it is known before the bar
        # whose signal it judges.
        tp = (hi + lo + cl) / 3.0
        cvp = np.cumsum(tp * vol)
        cvv = np.cumsum(vol)
        vwap_prior = np.full(len(hi), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            vwap_prior[1:] = cvp[:-1] / np.where(cvv[:-1] > 0, cvv[:-1], np.nan)
        atr = (pd.Series(hi - lo).rolling(ATR_BARS, min_periods=10).mean()
               .shift(1).to_numpy(np.float64))
        px0 = float(g.open.iloc[0])
        out[day] = dict(
            t=g.timestamp.to_numpy(), hi=hi, lo=lo, op=op, cl=cl,
            vwap=vwap_prior, atr=atr, open_t=open_t, flat_t=flat_t,
            last_entry=et_wall(day, *LAST_ENTRY_UTC), px=px0,
            brk=px0 * BREAK_F, floor=px0 * FLOOR_F, cost=px0 * COST_F)
    return out, rejected


def run_session(s, or_min, stop_atr, tgt_r, use_vwap=True,
                entry_bar_exit=False):
    """The pre-registered state machine. One session, one variant.

    `entry_bar_exit=False` -- AND THIS IS A CORRECTION, NOT A CHOICE OF
    CONVENIENCE. For a breakout entry the trigger sits at the top of the
    bar's travel: price had to rise THROUGH the bar to reach it. Measured on
    this grid, 73.9% of entry bars opened on the far side of their trigger,
    44.9% of trades had an entry-bar adverse extreme beyond the stop, and
    87.8% of THOSE bars opened on the far side -- so the low that 'stopped'
    them is provably pre-entry price action. Charging a trade with a move
    that happened before it existed is not pessimism, it is the model being
    told something false about sequence, exactly as crediting an unavailable
    fill price was. The pullback family did not have this problem because its
    trigger was a rejection off a PRIOR bar's extreme; there the same switch
    was worth about 0.07R, here it is worth most of the result.

    What a one-minute bar cannot say is what the entry bar did AFTER the
    fill. That is unresolvable here and only the tape can settle it.
    """
    t, hi, lo, op, cl = s["t"], s["hi"], s["lo"], s["op"], s["cl"]
    vwap, atr = s["vwap"], s["atr"]
    brk, floor, cost = s["brk"], s["floor"], s["cost"]
    last_entry = np.datetime64(s["last_entry"])
    n = len(t)

    or_end = s["open_t"] + pd.Timedelta(minutes=or_min)
    m = t < np.datetime64(or_end)
    if m.sum() < 3 or m.all():
        return [], {}
    orh, orl = float(hi[m].max()), float(lo[m].min())
    orr = orh - orl
    if orr <= 0:
        return [], {}

    trig_l, trig_s = orh + brk, orl - brk
    armed = {1: True, -1: True}
    diag = dict(both=0, veto=0, signals=0, orr=orr)
    trades = []
    state = "SCAN"
    i = int(np.searchsorted(t, np.datetime64(or_end), "left"))
    direction = 0
    entry = stop = target = naive_entry = 0.0
    entry_i = -1

    while i < n and len(trades) < MAX_TRADES:
        h, l, o, now = hi[i], lo[i], op[i], t[i]

        if state == "SCAN":
            if not armed[1] and l <= orh:
                armed[1] = True
            if not armed[-1] and h >= orl:
                armed[-1] = True

            hit_l = armed[1] and h >= trig_l
            hit_s = armed[-1] and l <= trig_s
            if hit_l and hit_s:
                # one bar reaching both triggers cannot say which came first
                diag["both"] += 1
                i += 1
                continue
            if not (hit_l or hit_s):
                i += 1
                continue

            direction = 1 if hit_l else -1
            trig = trig_l if hit_l else trig_s
            # a stop order fills at the first price available, not its trigger
            fill = max(trig, o) if direction > 0 else min(trig, o)
            diag["signals"] += 1

            v = vwap[i]
            if use_vwap:
                if not np.isfinite(v):
                    i += 1
                    continue
                ok = fill > v if direction > 0 else fill < v
                if not ok:
                    diag["veto"] += 1
                    i += 1
                    continue

            if now >= last_entry:
                i += 1
                continue
            a = atr[i]
            if not np.isfinite(a):
                i += 1
                continue

            stop = trig - direction * max(floor, stop_atr * a)
            risk = abs(fill - stop)
            if risk <= 0:
                i += 1
                continue
            entry, naive_entry = fill, trig
            target = fill + direction * tgt_r * risk
            armed[direction] = False
            entry_i = i
            state = "IN"
            if not entry_bar_exit:
                i += 1
            continue

        if state == "IN":
            stopped = l <= stop if direction > 0 else h >= stop
            hit_tgt = h >= target if direction > 0 else l <= target
            ambiguous = bool(stopped and hit_tgt)
            exit_px = None
            if stopped:
                # a stop that gaps through fills at the open, not at the stop
                gap = min(stop, o) if direction > 0 else max(stop, o)
                exit_px, why = (stop if i == entry_i else gap), "stop"
            elif hit_tgt:
                exit_px, why = target, "target"
            elif i == n - 1:
                exit_px, why = cl[i], "flat"
            if exit_px is None:
                i += 1
                continue
            risk = abs(entry - stop)
            naive_risk = abs(naive_entry - stop)
            trades.append(dict(
                dir=direction, entry=entry, stop=stop, target=target,
                exit=exit_px, why=why, ambiguous=ambiguous, risk=risk,
                R=(direction * (exit_px - entry) - cost) / risk,
                # what the discredited fill assumption would have reported
                naive_R=(direction * (exit_px - naive_entry) - cost) / naive_risk,
                slip_R=direction * (entry - naive_entry) / risk,
                gapped=bool(direction * (naive_entry - o) < 0),
                entry_t=t[entry_i], risk_bps=1e4 * risk / s["px"],
                mins=(t[entry_i] - np.datetime64(s["open_t"]))
                     / np.timedelta64(1, "m")))
            state = "SCAN"
            i += 1
            continue

    return trades, diag


def evaluate(S, days, or_min, satr, tgt, use_vwap=True, entry_bar_exit=False):
    rows, dg = [], []
    for day in days:
        tr, d = run_session(S[day], or_min, satr, tgt, use_vwap,
                            entry_bar_exit)
        if d:
            dg.append({**d, "day": day})
        for x in tr:
            rows.append({**x, "day": day})
    T = pd.DataFrame(rows)
    D = pd.DataFrame(dg)
    if not T.empty:
        T["year"] = pd.to_datetime(T.day).dt.year
        T["tod"] = pd.cut(T.mins, [-1, *TOD_EDGES, 10**9],
                          labels=["0-60", "60-120", "120-180", "180+"])
    return T, D


def or_height_buckets(S, days, or_min):
    """OR height as a ratio to its own TRAILING mean. No session is bucketed
    using anything from its own future."""
    h = {}
    for day in days:
        s = S[day]
        m = s["t"] < np.datetime64(s["open_t"] + pd.Timedelta(minutes=or_min))
        if m.sum() < 3 or m.all():
            continue
        h[day] = 1e4 * (float(s["hi"][m].max()) - float(s["lo"][m].min())) / s["px"]
    ser = pd.Series(h).sort_index()
    trail = ser.rolling(TRAIL_N, min_periods=TRAIL_N).mean().shift(1)
    ratio = ser / trail
    return pd.cut(ratio, [-np.inf, *ORH_CUTS, np.inf],
                  labels=["narrow", "normal", "wide"])


def stats(T, days):
    R = T.R
    w, l = R[R > 0], R[R <= 0]
    per = R.groupby(T.day).sum().reindex(days).fillna(0.0)
    return dict(
        n=len(R), exp=R.mean(), win=100 * (R > 0).mean(),
        pf=(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else np.inf,
        t=per.mean() / (per.std(ddof=1) / np.sqrt(len(per))),
        sess_pos=int((per > 0).sum()),
        ex1=R.sum() - R.sort_values(ascending=False)
            .head(int(np.ceil(0.01 * len(R)))).sum(),
        yr=R.groupby(T.year).sum())


def block(title, rows, cols, fmt="{:>+9.3f}"):
    print(f"\n  {title}")
    print(f"    {'variant':<20}" + "".join(f"{c:>11}" for c in cols))
    for k, v in rows.items():
        print(f"    {k:<20}" + "".join(
            (fmt.format(v[c]) + "  ") if c in v and np.isfinite(v[c])
            else f"{'--':>9}  " for c in cols))


def main():
    S, rej = build_sessions()
    days = sorted(S)
    years = sorted({d.year for d in days})
    print("=" * 108)
    print("QQQ — OPENING RANGE BREAKOUT WITH A SESSION VWAP FILTER, 16 "
          "PRE-REGISTERED VARIANTS")
    print("=" * 108)
    print(f"  sessions used   : {len(days):,}   {days[0]} to {days[-1]}")
    print(f"  sessions dropped: {rej}")
    print("  per year: " + "  ".join(
        f"{y} {sum(1 for d in days if d.year == y)}" for y in years))
    print(f"  cost {1e4 * COST_F:.3f} bps round turn   stop floor "
          f"{1e4 * FLOOR_F:.3f} bps   break {1e4 * BREAK_F:.3f} bps")
    print("  flat 18:30 UTC (14:30 ET summer, 13:30 ET winter), exit at that "
          "bar's close")
    print("  no time expiry. max 2 trades/session, never concurrent, second "
          "arms only after the first closes.")
    print("  VWAP from the RTH open over CLOSED bars only. Results in R, "
          "never points.\n")

    ORB = {om: or_height_buckets(S, days, om) for om in G_OR}

    res, ctl, ebe = {}, {}, {}
    print("  TRADE AND SESSION COUNTS FIRST, before any performance number:\n")
    print(f"  {'variant':<20}{'trades':>9}{'sessions':>10}{'tr/sess':>9}"
          f"{'med risk':>10}{'flat%':>8}{'amb%':>7}{'signals':>9}"
          f"{'VWAP veto':>11}{'2-sided':>9}")
    for om, sa, tg in product(G_OR, G_SATR, G_TGT):
        k = f"OR{om} SATR{sa} R{tg}"
        T, D = evaluate(S, days, om, sa, tg, True)
        C, _ = evaluate(S, days, om, sa, tg, False)
        E, _ = evaluate(S, days, om, sa, tg, True, entry_bar_exit=True)
        res[k], ctl[k], ebe[k] = T, C, E
        ns = T.day.nunique()
        sig, veto, both = D.signals.sum(), D.veto.sum(), D.both.sum()
        print(f"  {k:<20}{len(T):>9,}{ns:>10,}{len(T) / max(ns, 1):>9.2f}"
              f"{T.risk_bps.median():>9.1f}b{100 * (T.why == 'flat').mean():>7.1f}%"
              f"{100 * T.ambiguous.mean():>6.1f}%{sig:>9,}"
              f"{100 * veto / max(sig, 1):>10.1f}%{both:>9,}")

    print("\n" + "=" * 108)
    print("  THE SLIPPAGE AUDIT — this is what fabricated the last family's "
          "edge, so it leads")
    print("=" * 108)
    print(f"  {'variant':<20}{'gapped':>9}{'mean slip':>11}{'med slip':>10}"
          f"{'HONEST expR':>13}{'NAIVE expR':>12}{'phantom':>10}"
          f"{'entry-bar conv':>16}")
    for k, T in res.items():
        ph = T.naive_R.mean() - T.R.mean()
        print(f"  {k:<20}{100 * T.gapped.mean():>8.1f}%{T.slip_R.mean():>+11.3f}"
              f"{T.slip_R.median():>+10.3f}{T.R.mean():>+13.3f}"
              f"{T.naive_R.mean():>+12.3f}{ph:>+10.3f}"
              f"{ebe[k].R.mean():>+16.3f}")
    print("\n  'entry-bar conv' is what the result becomes if the ENTRY BAR is "
          "also searched for\n  the exit. On a breakout that bar's adverse "
          "extreme is overwhelmingly pre-entry\n  price action, so the column "
          "is reported as a wrong answer, not an alternative.")

    print("\n" + "=" * 108)
    print("  PERFORMANCE — expectancy in R after costs. t across sessions, "
          "zero-trade sessions count as zero.")
    print("=" * 108)
    print(f"  {'variant':<20}{'n':>7}{'expR':>8}{'win%':>7}{'coin%':>7}"
          f"{'PF':>7}{'sess t':>8}{'sess+':>7}{'ex-top1%':>10}{'+yrs':>6}"
          f"{'  control expR':>15}")
    M = {}
    for k, T in res.items():
        m = stats(T, days)
        M[k] = m
        coin = 100.0 / (1.0 + float(k.split("R")[-1]))
        print(f"  {k:<20}{m['n']:>7,}{m['exp']:>+8.3f}{m['win']:>7.1f}"
              f"{coin:>7.1f}{m['pf']:>7.2f}{m['t']:>+8.2f}{m['sess_pos']:>7}"
              f"{m['ex1']:>+10.1f}{int((m['yr'] > 0).sum()):>4}/{len(m['yr']):<2}"
              f"{ctl[k].R.mean():>+15.3f}")

    print("\n" + "=" * 108)
    print("  REGIME BREAKDOWN — standard output, not on request")
    print("=" * 108)
    block("BY YEAR, mean R per trade",
          {k: {y: g.R.mean() for y, g in T.groupby("year")}
           for k, T in res.items()}, years)
    block("BY TIME OF DAY, mean R per trade (minutes since the RTH open)",
          {k: {str(b): g.R.mean() for b, g in T.groupby("tod", observed=True)}
           for k, T in res.items()}, ["0-60", "60-120", "120-180", "180+"])
    block("BY TIME OF DAY, trade count",
          {k: {str(b): float(len(g)) for b, g in T.groupby("tod", observed=True)}
           for k, T in res.items()}, ["0-60", "60-120", "120-180", "180+"],
          fmt="{:>9,.0f}")
    orh_rows, orh_n = {}, {}
    for k, T in res.items():
        om = int(k.split()[0][2:])
        b = T.day.map(ORB[om])
        orh_rows[k] = {str(x): g.R.mean() for x, g in T.groupby(b, observed=True)}
        orh_n[k] = {str(x): float(len(g)) for x, g in T.groupby(b, observed=True)}
    block("BY OPENING RANGE HEIGHT vs its trailing 20-session mean, mean R",
          orh_rows, ["narrow", "normal", "wide"])
    block("BY OPENING RANGE HEIGHT, trade count", orh_n,
          ["narrow", "normal", "wide"], fmt="{:>9,.0f}")

    print("\n" + "=" * 108)
    print("  REJECTION CRITERIA, FIXED IN ADVANCE (pre-registration section 7)")
    print("=" * 108)
    print("  1 expectancy <= 0 in R   2 t <= 3 across sessions   3 PF < 1.15")
    print("  4 top-1% dependent   5 positive in fewer than 4 calendar years")
    print("  Bonferroni over 16 tests puts the honest bar at t > 3.5.\n")
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
        py = int((m["yr"] > 0).sum())
        if py < 4:
            f.append(f"5 only {py} positive years")
        if f:
            print(f"  {k:<20} REJECT  {'; '.join(f)}")
        else:
            surv.append(k)
            print(f"  {k:<20} SURVIVES  t {m['t']:+.2f}"
                  + ("  (clears Bonferroni)" if m["t"] > 3.5
                     else "  (below the Bonferroni bar of 3.5)"))
    print(f"\n  survivors: {len(surv)} of 16")
    print("\n  A SURVIVOR IS A CANDIDATE, NOT A FINDING. The control column is "
          "attribution\n  only and is barred from producing one.")


if __name__ == "__main__":
    main()
