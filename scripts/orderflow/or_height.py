#!/usr/bin/env python3
"""OPENING RANGE HEIGHT AS THE HYPOTHESIS, not as a filter on something else.

Rule, grid, threshold and rejection criteria pre-registered at `9307834`
(`reports/or_height_preregistration.md`) before this ran.

THE CLAIM

Breakouts from an opening range TALL relative to its own recent history beat
breakouts from a SHORT one, at a 1.0 ATR stop and 3R/4R targets. Directional:
the folk version ("a tight range coils") predicts the opposite sign, so a
reversal is as much a failure as a null.

THREE RUNS, AND ONLY ONE OF THEM IS EVIDENCE

  A  1-minute, 2021-2026   IN SAMPLE. The gradient was FOUND here. This run
                           sharpens and stress-tests it; it cannot confirm it.
  B  5-minute, 2021-2026   BRIDGE. Must reproduce A. If it does not, the
                           5-minute grid is not measuring the same rule and
                           run C is not interpretable.
  C  5-minute, 2016-2020   OUT OF SAMPLE. 1,259 sessions never read by this
                           project. This is the evidence.

The stop is rescaled on the 5-minute grid by the measured ratio of mean bar
ranges (2.344, from the 1,421 overlapping sessions) so risk in bps matches. A
units conversion fixed before the run, not a fitted parameter -- realised
median risk is printed on every grid so the match is checked, not trusted.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/or_height.py
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

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")

BREAK_F = 0.50 / 30000.0        # 0.167 bps
FLOOR_F = 2.00 / 30000.0        # 0.667 bps
COST_F = 2.00 / 30000.0         # 0.667 bps round turn
FLAT_UTC = (18, 30)
LAST_ENTRY_UTC = (18, 0)
ATR_BARS = 20
MAX_TRADES = 2

G_OR = (15, 30)
G_TGT = (3.0, 4.0)
STOP_ATR_1M = 1.0
BAR_RANGE_RATIO = 2.344         # measured on the overlap, declared in advance
STOP_ATR_5M = STOP_ATR_1M / BAR_RANGE_RATIO
THRESHOLD = 1.00                # ratio to the trailing 20-session mean
TRAIL_N = 20
TOD_EDGES = (60, 120, 180)


def et_wall(day, hh, mm):
    u = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=dt.timezone.utc)
    return pd.Timestamp(u.astimezone(ET).replace(tzinfo=None))


def build(path, freq_min, lo_year=None, hi_year=None):
    d = pd.read_parquet(ROOT / path)
    d["day"] = d.timestamp.dt.date
    if lo_year is not None:
        d = d[(d.timestamp.dt.year >= lo_year) & (d.timestamp.dt.year <= hi_year)]
    need = int(0.92 * 390 / freq_min)
    out, rejected = {}, 0
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < need:
            rejected += 1
            continue
        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        flat_t = et_wall(day, *FLAT_UTC)
        if g.timestamp.iloc[0] > open_t or g.timestamp.iloc[-1] < flat_t:
            rejected += 1
            continue
        g = g[(g.timestamp >= open_t) & (g.timestamp <= flat_t)]
        if len(g) < int(0.3 * need):
            rejected += 1
            continue
        hi = g.high.to_numpy(np.float64)
        lo = g.low.to_numpy(np.float64)
        atr = (pd.Series(hi - lo).rolling(ATR_BARS, min_periods=10).mean()
               .shift(1).to_numpy(np.float64))
        px0 = float(g.open.iloc[0])
        out[day] = dict(
            t=g.timestamp.to_numpy(), hi=hi, lo=lo,
            op=g.open.to_numpy(np.float64), cl=g.close.to_numpy(np.float64),
            atr=atr, open_t=open_t, last_entry=et_wall(day, *LAST_ENTRY_UTC),
            px=px0, brk=px0 * BREAK_F, floor=px0 * FLOOR_F, cost=px0 * COST_F)
    return out, rejected


def or_levels(s, or_min):
    m = s["t"] < np.datetime64(s["open_t"] + pd.Timedelta(minutes=or_min))
    if m.sum() < 3 or m.all():
        return None
    orh, orl = float(s["hi"][m].max()), float(s["lo"][m].min())
    return (orh, orl, int(m.sum())) if orh > orl else None


def run_session(s, or_min, stop_atr, tgt_r):
    """Identical to the ORB machine minus the VWAP filter. Entry bar is skipped
    for the exit search; a stop order fills at the first price available."""
    lv = or_levels(s, or_min)
    if lv is None:
        return [], 0
    orh, orl, n_or = lv
    t, hi, lo, op, cl = s["t"], s["hi"], s["lo"], s["op"], s["cl"]
    atr, brk, floor, cost = s["atr"], s["brk"], s["floor"], s["cost"]
    last_entry = np.datetime64(s["last_entry"])
    n = len(t)

    trig_l, trig_s = orh + brk, orl - brk
    armed = {1: True, -1: True}
    trades, lookahead = [], 0
    state = "SCAN"
    i = int(np.searchsorted(
        t, np.datetime64(s["open_t"] + pd.Timedelta(minutes=or_min)), "left"))
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
            if (hit_l and hit_s) or not (hit_l or hit_s):
                i += 1
                continue
            # ENTRY LOOKAHEAD CHECK. The trigger comes from the OR window,
            # which closed before this bar existed; a bar inside that window
            # can never trigger. Counted, not assumed.
            if i < n_or:
                lookahead += 1
            direction = 1 if hit_l else -1
            trig = trig_l if hit_l else trig_s
            fill = max(trig, o) if direction > 0 else min(trig, o)
            if now >= last_entry or not np.isfinite(atr[i]):
                i += 1
                continue
            stop = trig - direction * max(floor, stop_atr * atr[i])
            risk = abs(fill - stop)
            if risk <= 0:
                i += 1
                continue
            entry, naive_entry = fill, trig
            target = fill + direction * tgt_r * risk
            armed[direction] = False
            entry_i = i
            state = "IN"
            i += 1
            continue

        if state == "IN":
            stopped = l <= stop if direction > 0 else h >= stop
            hit_tgt = h >= target if direction > 0 else l <= target
            exit_px = None
            if stopped:
                exit_px = min(stop, o) if direction > 0 else max(stop, o)
                why = "stop"
            elif hit_tgt:
                exit_px, why = target, "target"
            elif i == n - 1:
                exit_px, why = cl[i], "flat"
            if exit_px is None:
                i += 1
                continue
            risk = abs(entry - stop)
            nrisk = abs(naive_entry - stop)
            trades.append(dict(
                why=why, R=(direction * (exit_px - entry) - cost) / risk,
                naive_R=(direction * (exit_px - naive_entry) - cost) / nrisk,
                slip_R=direction * (entry - naive_entry) / risk,
                gapped=bool(direction * (naive_entry - o) < 0),
                ambiguous=bool(stopped and hit_tgt),
                risk_bps=1e4 * risk / s["px"],
                mins=(t[entry_i] - np.datetime64(s["open_t"]))
                     / np.timedelta64(1, "m")))
            state = "SCAN"
            i += 1
            continue

    return trades, lookahead


def or_ratio(S, days, or_min):
    """OR height over its own TRAILING 20-session mean. Shifted, so no session
    is classified using its own data or anything after it."""
    h = {}
    for day in days:
        lv = or_levels(S[day], or_min)
        if lv:
            h[day] = 1e4 * (lv[0] - lv[1]) / S[day]["px"]
    ser = pd.Series(h).sort_index()
    trail = ser.rolling(TRAIL_N, min_periods=TRAIL_N).mean().shift(1)
    return ser / trail


def evaluate(S, days, or_min, tgt, stop_atr):
    rows, look = [], 0
    for day in days:
        tr, lk = run_session(S[day], or_min, stop_atr, tgt)
        look += lk
        for x in tr:
            rows.append({**x, "day": day})
    T = pd.DataFrame(rows)
    if not T.empty:
        T["year"] = pd.to_datetime(T.day).dt.year
        T["tod"] = pd.cut(T.mins, [-1, *TOD_EDGES, 10 ** 9],
                          labels=["0-60", "60-120", "120-180", "180+"])
    return T, look


def welch(a, b):
    if len(a) < 3 or len(b) < 3:
        return np.nan
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    return (a.mean() - b.mean()) / np.sqrt(va + vb) if va + vb > 0 else np.nan


def arm_stats(T, sess):
    """Per-arm figures. `sess` is the session set that arm is allowed to use."""
    T = T[T.day.isin(sess)]
    if T.empty:
        return None
    R = T.R
    w, l = R[R > 0], R[R <= 0]
    per = R.groupby(T.day).sum().reindex(sorted(sess)).fillna(0.0)
    return dict(
        n=len(R), sessions=T.day.nunique(), exp=R.mean(), win=100 * (R > 0).mean(),
        pf=(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else np.inf,
        t=per.mean() / (per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 2 else np.nan,
        ex1=R.sum() - R.sort_values(ascending=False)
            .head(int(np.ceil(0.01 * len(R)))).sum(),
        yr=R.groupby(T.year).mean(), per=per, T=T)


def run_block(name, S, days, stop_atr, note):
    years = sorted({d.year for d in days})
    print("\n" + "=" * 110)
    print(f"  {name}")
    print("=" * 110)
    print(f"  {note}")
    print(f"  sessions {len(days):,}   {days[0]} to {days[-1]}   "
          f"STOP_ATR {stop_atr:.4f}")
    print("  per year: " + "  ".join(
        f"{y} {sum(1 for d in days if d.year == y)}" for y in years))

    RAT = {om: or_ratio(S, days, om) for om in G_OR}
    for om in G_OR:
        r = RAT[om].dropna()
        print(f"  OR{om}: classified {len(r):,} sessions   "
              f"WIDE {int((r >= THRESHOLD).sum()):,}   "
              f"NARROW {int((r < THRESHOLD).sum()):,}   "
              f"median ratio {r.median():.3f}")

    out = {}
    print("\n  TRADE AND SESSION COUNTS FIRST:\n")
    print(f"  {'variant':<16}{'trades':>8}{'sessions':>10}{'tr/sess':>9}"
          f"{'med risk':>10}{'flat%':>7}{'amb%':>7}{'lookahead':>11}")
    for om, tg in product(G_OR, G_TGT):
        k = f"OR{om} R{tg}"
        T, lk = evaluate(S, days, om, tg, stop_atr)
        r = RAT[om]
        cls = set(r.dropna().index)
        wide = set(r[r >= THRESHOLD].dropna().index)
        narrow = cls - wide
        out[k] = dict(T=T, wide=wide, narrow=narrow, cls=cls, look=lk)
        ns = T.day.nunique()
        print(f"  {k:<16}{len(T):>8,}{ns:>10,}{len(T) / max(ns, 1):>9.2f}"
              f"{T.risk_bps.median():>9.1f}b{100 * (T.why == 'flat').mean():>6.1f}%"
              f"{100 * T.ambiguous.mean():>6.1f}%{lk:>11,}")

    print("\n  SLIPPAGE AUDIT (wide arm) — honest fill beside the naive one:")
    print(f"  {'variant':<16}{'gapped':>9}{'mean slip':>11}{'HONEST expR':>13}"
          f"{'NAIVE expR':>12}{'phantom':>10}")
    for k, v in out.items():
        W = v["T"][v["T"].day.isin(v["wide"])]
        print(f"  {k:<16}{100 * W.gapped.mean():>8.1f}%{W.slip_R.mean():>+11.3f}"
              f"{W.R.mean():>+13.3f}{W.naive_R.mean():>+12.3f}"
              f"{W.naive_R.mean() - W.R.mean():>+10.3f}")

    print("\n  THE GRADIENT — the expectancy difference the threshold produces")
    print(f"  {'variant':<16}{'all expR':>10}{'WIDE expR':>11}{'NARROW expR':>13}"
          f"{'wide-narrow':>13}{'Welch t':>9}{'wide n':>8}{'narrow n':>10}")
    G = {}
    for k, v in out.items():
        T = v["T"]
        aw, an = arm_stats(T, v["wide"]), arm_stats(T, v["narrow"])
        ac = arm_stats(T, v["cls"])
        if aw is None or an is None:
            continue
        g = aw["exp"] - an["exp"]
        tt = welch(aw["per"], an["per"])
        G[k] = dict(w=aw, n=an, a=ac, grad=g, t=tt)
        print(f"  {k:<16}{ac['exp']:>+10.3f}{aw['exp']:>+11.3f}{an['exp']:>+13.3f}"
              f"{g:>+13.3f}{tt:>+9.2f}{aw['n']:>8,}{an['n']:>10,}")

    print("\n  BY TIME OF DAY, wide arm — mean R (count)")
    tods = ["0-60", "60-120", "120-180", "180+"]
    print(f"  {'variant':<16}" + "".join(f"{c:>18}" for c in tods))
    for k, v in out.items():
        W = v["T"][v["T"].day.isin(v["wide"])]
        cells = []
        for c in tods:
            g = W[W.tod == c]
            cells.append(f"{g.R.mean():>+9.3f} ({len(g):>4,})" if len(g)
                         else f"{'--':>16}")
        print(f"  {k:<16}" + "".join(f"{c:>18}" for c in cells))

    print("\n  BY YEAR, wide arm — mean R")
    print(f"  {'variant':<16}" + "".join(f"{y:>10}" for y in years))
    for k, v in out.items():
        W = v["T"][v["T"].day.isin(v["wide"])]
        yr = W.groupby("year").R.mean()
        print(f"  {k:<16}" + "".join(
            f"{yr[y]:>+10.3f}" if y in yr.index else f"{'--':>10}"
            for y in years))

    print("\n  GRADIENT BY YEAR (wide mean R minus narrow mean R)")
    print(f"  {'variant':<16}" + "".join(f"{y:>10}" for y in years) + "   holds")
    for k, g in G.items():
        row, hold = [], 0
        for y in years:
            wv = g["w"]["yr"].get(y, np.nan)
            nv = g["n"]["yr"].get(y, np.nan)
            d = wv - nv
            row.append(d)
            if np.isfinite(d) and d > 0:
                hold += 1
        print(f"  {k:<16}" + "".join(
            f"{v:>+10.3f}" if np.isfinite(v) else f"{'--':>10}" for v in row)
            + f"   {hold}/{len(years)}")
        G[k]["hold"] = hold
    return G, years


def main():
    print("=" * 110)
    print("QQQ — OPENING RANGE HEIGHT AS THE HYPOTHESIS. 4 PRE-REGISTERED "
          "VARIANTS, 2 OF THE BUDGET UNSPENT.")
    print("=" * 110)
    print(f"  WIDE = OR height >= {THRESHOLD:.2f} x its trailing "
          f"{TRAIL_N}-session mean (shifted; no session uses its own data)")
    print("  stop 1.0 ATR, targets 3R and 4R, no VWAP filter, entry bar "
          "skipped, honest fills")
    print("  max 2 trades/session, never concurrent, flat 18:30 UTC, cost "
          f"{1e4 * COST_F:.3f} bps round turn")

    S1, r1 = build("data/intraday_long/QQQ_1m.parquet", 1)
    A, yrs_a = run_block(
        "RUN A — 1-MINUTE, 2021-2026 — IN SAMPLE, CANNOT CONFIRM",
        S1, sorted(S1), STOP_ATR_1M,
        "The gradient was FOUND on these sessions. This run stress-tests it; "
        "it is not evidence.")

    S5b, r5b = build("data/intraday_long/QQQ_5m.parquet", 5, 2021, 2026)
    B, _ = run_block(
        "RUN B — 5-MINUTE, 2021-2026 — BRIDGE CHECK",
        S5b, sorted(S5b), STOP_ATR_5M,
        "Must reproduce run A. If it does not, run C is not interpretable.")

    S5c, r5c = build("data/intraday_long/QQQ_5m.parquet", 5, 2016, 2020)
    C, yrs_c = run_block(
        "RUN C — 5-MINUTE, 2016-2020 — OUT OF SAMPLE. THIS IS THE EVIDENCE.",
        S5c, sorted(S5c), STOP_ATR_5M,
        "1,259 sessions this project has never read, in any family, in any run.")

    print("\n" + "=" * 110)
    print("  BRIDGE CHECK — does the 5-minute grid measure the same rule?")
    print("=" * 110)
    print(f"  {'variant':<16}{'A gradient':>12}{'B gradient':>12}{'diff':>9}"
          f"{'A risk bps':>12}{'B risk bps':>12}")
    ok = True
    for k in A:
        if k not in B:
            continue
        ra = A[k]["w"]["T"].risk_bps.median()
        rb = B[k]["w"]["T"].risk_bps.median()
        d = B[k]["grad"] - A[k]["grad"]
        if np.sign(A[k]["grad"]) != np.sign(B[k]["grad"]):
            ok = False
        print(f"  {k:<16}{A[k]['grad']:>+12.3f}{B[k]['grad']:>+12.3f}"
              f"{d:>+9.3f}{ra:>12.1f}{rb:>12.1f}")
    print(f"\n  signs agree on all four variants: {'YES' if ok else 'NO'}"
          + ("" if ok else "  -> RUN C IS NOT INTERPRETABLE AND IS WITHDRAWN"))

    print("\n" + "=" * 110)
    print("  REJECTION CRITERIA, FIXED IN ADVANCE — applied to the WIDE arm")
    print("=" * 110)
    print("  1 expectancy <= 0   2 fewer than 15 sessions traded   3 PF < 1.15")
    print("  4 top-1% dependent  5 positive in fewer than 4 of 6 years")
    print("  6 NEW: gradient positive in fewer than 4 of 6 years")
    print("  plus the standing bar from the last two screens: t > 3 across "
          "sessions.\n")
    for label, blk, yrs in (("IN SAMPLE (run A)", A, yrs_a),
                            ("OUT OF SAMPLE (run C)", C, yrs_c)):
        print(f"  --- {label} ---")
        surv = []
        for k, g in blk.items():
            w = g["w"]
            f = []
            if w["exp"] <= 0:
                f.append(f"1 exp {w['exp']:+.3f}")
            if w["sessions"] < 15:
                f.append(f"2 {w['sessions']} sessions")
            if w["pf"] < 1.15:
                f.append(f"3 PF {w['pf']:.2f}")
            if w["ex1"] <= 0:
                f.append("4 top-1% dependent")
            py = int((w["yr"] > 0).sum())
            if py < 4:
                f.append(f"5 only {py}/{len(yrs)} positive years")
            if g["hold"] < 4:
                f.append(f"6 gradient holds {g['hold']}/{len(yrs)}")
            if not np.isfinite(w["t"]) or w["t"] <= 3.0:
                f.append(f"t {w['t']:+.2f}")
            if f:
                print(f"  {k:<16} REJECT  {'; '.join(f)}")
            else:
                surv.append(k)
                print(f"  {k:<16} SURVIVES  exp {w['exp']:+.3f}  t {w['t']:+.2f}"
                      f"  gradient {g['grad']:+.3f} (t {g['t']:+.2f})")
        print(f"  survivors: {len(surv)} of {len(blk)}\n")

    print("  A SURVIVOR IS A CANDIDATE, NOT A FINDING. Nothing here has been "
          "verified on NQ ticks.")


if __name__ == "__main__":
    main()
