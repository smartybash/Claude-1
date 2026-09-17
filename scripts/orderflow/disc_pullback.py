#!/usr/bin/env python3
"""A PUBLIC DISCRETIONARY NQ STRATEGY, MECHANISED. 8 pre-registered variants.

Pre-registered at `b8db9d2`
(`reports/pullback_discretionary_preregistration.md`) before this ran.

THE CLAIM

77% win rate at 1.87 reward:risk, profit factor 6.39, 31 trades, January 2024,
backtested by hand in TradingView bar replay. For a driftless random walk with a
1R stop and an MR target, P(target first) = 1/(1+M); at M = 1.87 that is 34.8%.
The reported rate therefore sits 42 points above chance -- a five-sigma claim
from 31 manually replayed trades with no fill model.

The definitions below are the USER'S, used as given. Cleaner substitutes are not
permitted: the object is their rule, not an improved one.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/disc_pullback.py
"""
from __future__ import annotations

import datetime as dt
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"

# NQ point quantities as a fraction of a ~30,000 index level (project standing
# convention), applied to QQQ's price.
TICK_F = 0.25 / 30000.0         # one NQ tick
COST_F = 2.00 / 30000.0         # 0.667 bps round turn
DSTOP_F = 10.00 / 30000.0       # the 10-point daily stop, 3.33 bps

OR_MIN = 15                     # both trend rules need the opening range
WIN_MIN = 90                    # decision window, minutes from the cash open
ATR_N = 14
MIN_BARS = 360
DEEP_MAX = 0.75                 # retracement ceiling, from the spec

G_TREND = ("T1", "T2")
G_TGT = ("P1", "P2")
G_FLOOR = (0.33, 0.50)


# ------------------------------------------------------------------ build --

def sessions():
    """Full-session levels from day d-1, decision-window bars from day d."""
    d = pd.read_parquet(SRC)
    d["day"] = d.timestamp.dt.date
    days = sorted(d.day.unique())
    prior = None
    out, rejected = {}, 0
    for day in days:
        g = d[d.day == day].sort_values("timestamp")
        # Levels come from the FULL prior session (to 15:59), which is what a
        # trader means by "prior day high/low/close/VWAP".
        tp = (g.high + g.low + g.close) / 3.0
        full = dict(
            hi=float(g.high.max()), lo=float(g.low.min()),
            cl=float(g.close.iloc[-1]),
            vwap=float((tp * g.volume).sum() / g.volume.sum())
            if g.volume.sum() > 0 else float(tp.mean()))

        if len(g) < MIN_BARS or prior is None:
            rejected += 1
            prior = full
            continue

        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        or_end = open_t + pd.Timedelta(minutes=OR_MIN)
        win_end = open_t + pd.Timedelta(minutes=WIN_MIN)
        if g.timestamp.iloc[0] > open_t or g.timestamp.iloc[-1] < win_end:
            rejected += 1
            prior = full
            continue
        w = g[(g.timestamp >= open_t) & (g.timestamp <= win_end)]
        if len(w) < WIN_MIN * 0.9:
            rejected += 1
            prior = full
            continue

        hi = w.high.to_numpy(float)
        lo = w.low.to_numpy(float)
        cl = w.close.to_numpy(float)
        # True-range ATR(14), shifted one bar. Prior session's close seeds the
        # first bar's true range.
        pc = np.concatenate([[prior["cl"]], cl[:-1]])
        tr = np.maximum.reduce([hi - lo, np.abs(hi - pc), np.abs(lo - pc)])
        atr = (pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean()
               .shift(1).to_numpy(float))
        px = float(w.open.iloc[0])
        out[day] = dict(
            t=w.timestamp.to_numpy(), op=w.open.to_numpy(float),
            hi=hi, lo=lo, cl=cl, atr=atr,
            sess_open=px, px=px,
            n_or=int((w.timestamp < or_end).sum()),
            levels=np.array([prior["hi"], prior["lo"], prior["cl"],
                             prior["vwap"]], dtype=float),
            pvwap=prior["vwap"],
            tick=px * TICK_F, cost=px * COST_F, dstop=px * DSTOP_F)
        prior = full
    return out, rejected


# ------------------------------------------------------------------- rule --

def run_session(s, trend, target, floor):
    """One session. Returns (trades, lookahead). No daily stop applied here --
    it is a post-filter, so the same trade list serves both reported versions."""
    t, op, hi, lo, cl = s["t"], s["op"], s["hi"], s["lo"], s["cl"]
    atr, lv, cost, tick = s["atr"], s["levels"], s["cost"], s["tick"]
    so, n_or, n = s["sess_open"], s["n_or"], len(t)
    if n_or < 3 or n_or >= n - 2:
        return [], 0

    or_h = float(hi[:n_or].max())
    or_l = float(lo[:n_or].min())
    or_height = or_h - or_l
    if or_height <= 0:
        return [], 0

    # T1 is fixed at the close of the first 15-minute bar and never revised.
    t1_bias = 1 if cl[n_or - 1] > s["pvwap"] else -1
    t2_band = 0.5 * or_height

    # Running extremes from the session open, and the counter-extreme since the
    # favourable extreme was last made.
    run_hi = float(hi[:n_or].max())
    run_lo = float(lo[:n_or].min())
    pb_lo, pb_hi = run_hi, run_lo          # pullback extremes, per direction
    void = {1: False, -1: False}

    trades, lookahead = [], 0
    i = n_or
    state, direction = "SCAN", 0
    entry = naive_entry = stop = tgt = 0.0
    entry_i = -1

    while i < n:
        h, l, o, c = hi[i], lo[i], op[i], cl[i]

        if h > run_hi:
            run_hi, pb_lo = h, l
            void[1] = False
        if l < run_lo:
            run_lo, pb_hi = l, h
            void[-1] = False
        pb_lo = min(pb_lo, l)
        pb_hi = max(pb_hi, h)

        if state == "IN":
            # Entry bar is skipped for the exit search.
            if i > entry_i:
                stopped = l <= stop if direction > 0 else h >= stop
                hit = h >= tgt if direction > 0 else l <= tgt
                exit_px, why = None, ""
                if stopped:
                    exit_px = min(stop, o) if direction > 0 else max(stop, o)
                    why = "stop"
                elif hit:
                    exit_px, why = tgt, "target"
                elif i == n - 1:
                    exit_px, why = c, "flat"
                if exit_px is not None:
                    risk = abs(entry - stop)
                    nrisk = abs(naive_entry - stop)
                    gross = direction * (exit_px - entry)
                    trades.append(dict(
                        why=why, R=(gross - cost) / risk,
                        naive_R=(direction * (exit_px - naive_entry) - cost)
                        / nrisk if nrisk > 0 else np.nan,
                        slip_R=direction * (entry - naive_entry) / risk,
                        ambiguous=bool(stopped and hit),
                        gapped=bool(direction * (naive_entry - o) < 0),
                        risk_bps=1e4 * risk / s["px"],
                        pts=gross - cost,            # price units, net
                        rr=abs(tgt - entry) / risk,
                        mins=float((t[entry_i] - t[0]) / np.timedelta64(1, "m")),
                        entry_i=entry_i))
                    state = "SCAN"
            i += 1
            continue

        # ---- SCAN ----------------------------------------------------------
        bias = t1_bias if trend == "T1" else (
            1 if c - so >= t2_band else (-1 if so - c >= t2_band else 0))
        if bias == 0 or i >= n - 1:
            i += 1
            continue

        ext = run_hi if bias > 0 else run_lo
        pbx = pb_lo if bias > 0 else pb_hi
        move = (ext - so) if bias > 0 else (so - ext)
        if move <= 0:
            i += 1
            continue
        frac = ((ext - pbx) if bias > 0 else (pbx - ext)) / move
        if frac > DEEP_MAX:
            void[bias] = True
        if void[bias] or frac < floor:
            i += 1
            continue
        # Confirmation: a bar closing back in the direction of the bias.
        if not ((c > o) if bias > 0 else (c < o)):
            i += 1
            continue

        # ---- entry at the NEXT bar's open ----------------------------------
        j = i + 1
        if not np.isfinite(atr[j]):
            i += 1
            continue
        fill = op[j]
        prot = lv[lv < fill] if bias > 0 else lv[lv > fill]
        lvl_d = (fill - prot.max()) if (bias > 0 and len(prot)) else (
            (prot.min() - fill) if (bias < 0 and len(prot)) else 0.0)
        swing_d = (fill - pbx + 2 * tick) if bias > 0 else (pbx - fill + 2 * tick)
        dist = max(atr[j], swing_d, lvl_d)
        if dist <= 0:
            i += 1
            continue
        stop = fill - bias * dist
        risk = dist
        if target == "P2":
            tgt = fill + bias * 3.0 * risk
        else:
            beyond = lv[lv > fill] if bias > 0 else lv[lv < fill]
            tgt = (beyond.min() if bias > 0 else beyond.max()) if len(beyond) \
                else fill + bias * 2.0 * risk
        entry, naive_entry = fill, c
        direction, entry_i, state = bias, j, "IN"
        if j < n_or:
            lookahead += 1
        i = j
        continue

    return trades, lookahead


# -------------------------------------------------------------- aggregate --

def apply_daily_stop(tr, dstop):
    """Truncate the session's trades at the first daily-stop trigger."""
    out, cum = [], 0.0
    for x in tr:
        out.append(x)
        cum += x["pts"]
        if x["pts"] >= dstop or cum >= dstop:
            break
    return out


def evaluate(S, trend, target, floor, daily_stop):
    rows, look = [], 0
    for day in sorted(S):
        tr, lk = run_session(S[day], trend, target, floor)
        look += lk
        if daily_stop:
            tr = apply_daily_stop(tr, S[day]["dstop"])
        for x in tr:
            rows.append({**x, "day": day})
    T = pd.DataFrame(rows)
    if not T.empty:
        T["year"] = pd.to_datetime(T.day).dt.year
    return T, look


def stats(T, n_sess):
    R = T.R
    w, l = R[R > 0], R[R <= 0]
    per = R.groupby(T.day).sum()
    per = per.reindex(sorted(set(T.day))).fillna(0.0)
    # Realised reward:risk, and the random-walk hit rate it implies.
    M = (w.mean() / abs(l.mean())) if len(l) and l.mean() != 0 else np.nan
    rw = 1.0 / (1.0 + M) if np.isfinite(M) and M > 0 else np.nan
    obs = float((R > 0).mean())
    z = ((obs - rw) / np.sqrt(rw * (1 - rw) / len(R))) \
        if np.isfinite(rw) and 0 < rw < 1 else np.nan
    top = R.sort_values(ascending=False).head(int(np.ceil(0.01 * len(R)))).sum()
    return dict(
        n=len(R), sess=T.day.nunique(), exp=R.mean(), win=100 * obs,
        rr=M, rw=100 * rw, gap=100 * (obs - rw), z=z,
        pf=(w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else np.inf,
        t=per.mean() / (per.std(ddof=1) / np.sqrt(len(per)))
        if len(per) > 2 else np.nan,
        ex1=R.sum() - top, risk=T.risk_bps.median(),
        amb=100 * T.ambiguous.mean(), gapd=100 * T.gapped.mean(),
        slip=T.slip_R.mean(), naive=T.naive_R.mean(),
        flat=100 * (T.why == "flat").mean(),
        yr=R.groupby(T.year).mean(), per=per)


def main():
    print("=" * 118)
    print("  A PUBLIC DISCRETIONARY NQ STRATEGY, MECHANISED — 8 PRE-REGISTERED "
          "VARIANTS")
    print("=" * 118)
    print("  CLAIMED: 77% win rate, 1.87 R:R, PF 6.39, 31 trades, Jan 2024, "
          "manual TradingView bar replay.")
    print("  At 1.87 R:R a driftless random walk touches the target first "
          "34.8% of the time, so the claim")
    print("  sits ~42 points above chance: z = 4.9 on n = 31, from a method "
          "with no fill model.")
    print("\n  Entry at the NEXT bar's open. Entry bar skipped for the exit "
          "search. Cost 0.667 bps round turn.")
    print("  Win rate is judged against each variant's OWN realised "
          "reward:risk, not against 50%.")

    S, rejected = sessions()
    days = sorted(S)
    years = sorted({d.year for d in days})
    print(f"\n  sessions {len(S):,}   {days[0]} to {days[-1]}   "
          f"rejected {rejected}")
    print("  per year: " + "  ".join(
        f"{y} {sum(1 for d in days if d.year == y)}" for y in years))

    variants = list(product(G_TREND, G_TGT, G_FLOOR))
    res = {}

    for ds in (False, True):
        tag = "WITH the 10-point daily stop" if ds else "WITHOUT the daily stop"
        print("\n" + "=" * 118)
        print(f"  TRADE AND SESSION COUNTS FIRST — {tag}")
        print("=" * 118)
        print(f"  {'variant':<18}{'trades':>8}{'sessions':>10}{'tr/sess':>9}"
              f"{'max/sess':>10}{'med risk':>10}{'flat%':>8}{'amb%':>7}"
              f"{'lookahead':>11}")
        for tr_, tg, fl in variants:
            k = f"{tr_} {tg} f{fl:.2f}"
            T, lk = evaluate(S, tr_, tg, fl, ds)
            res[(ds, k)] = (T, lk)
            if T.empty:
                print(f"  {k:<18}{'no trades':>8}")
                continue
            st = stats(T, len(S))
            mx = T.groupby("day").size().max()
            print(f"  {k:<18}{st['n']:>8,}{st['sess']:>10,}"
                  f"{st['n'] / max(st['sess'], 1):>9.2f}{mx:>10}"
                  f"{st['risk']:>9.1f}b{st['flat']:>7.1f}%{st['amb']:>6.1f}%"
                  f"{lk:>11,}")

    print("\n" + "=" * 118)
    print("  THE COMPARISON THAT MATTERS — observed hit rate against the "
          "RANDOM-WALK rate implied by realised R:R")
    print("=" * 118)
    print("  WITHOUT the daily stop (per-trade expectancy is unaffected by it; "
          "confirmed in the next block)")
    print(f"\n  {'variant':<18}{'trades':>8}{'realised':>10}{'RW hit':>9}"
          f"{'observed':>10}{'gap':>9}{'z':>8}{'expR':>9}{'PF':>7}"
          f"{'t':>7}{'yrs+':>7}")
    print(f"  {'':<18}{'':>8}{'R:R':>10}{'rate %':>9}{'rate %':>10}"
          f"{'pts':>9}")
    for tr_, tg, fl in variants:
        k = f"{tr_} {tg} f{fl:.2f}"
        T, _ = res[(False, k)]
        if T.empty:
            continue
        st = stats(T, len(S))
        yp = sum(1 for y in years if st["yr"].get(y, -1) > 0)
        print(f"  {k:<18}{st['n']:>8,}{st['rr']:>10.2f}{st['rw']:>9.1f}"
              f"{st['win']:>10.1f}{st['gap']:>+9.1f}{st['z']:>+8.2f}"
              f"{st['exp']:>+9.3f}{st['pf']:>7.2f}{st['t']:>+7.2f}"
              f"{yp:>5}/{len(years)}")
    print("\n  CLAIMED for comparison:  R:R 1.87   RW rate 34.8%   "
          "observed 77.0%   gap +42.2   z +4.93  (n=31)")

    print("\n" + "=" * 118)
    print("  DOES THE DAILY STOP CHANGE PER-TRADE EXPECTANCY? "
          "(it cannot; this confirms rather than assumes)")
    print("=" * 118)
    print(f"  {'variant':<18}{'trades off':>12}{'trades on':>11}"
          f"{'expR off':>11}{'expR on':>10}{'diff':>9}"
          f"{'win% off':>11}{'win% on':>10}")
    for tr_, tg, fl in variants:
        k = f"{tr_} {tg} f{fl:.2f}"
        A, _ = res[(False, k)]
        B, _ = res[(True, k)]
        if A.empty or B.empty:
            continue
        a, b = stats(A, len(S)), stats(B, len(S))
        print(f"  {k:<18}{a['n']:>12,}{b['n']:>11,}{a['exp']:>+11.3f}"
              f"{b['exp']:>+10.3f}{b['exp'] - a['exp']:>+9.3f}"
              f"{a['win']:>11.1f}{b['win']:>10.1f}")

    print("\n" + "=" * 118)
    print("  HONEST FILL BESIDE THE NAIVE ONE — the correction the manual "
          "replay would not have applied")
    print("=" * 118)
    print(f"  {'variant':<18}{'gapped%':>10}{'mean slip R':>13}"
          f"{'HONEST expR':>13}{'NAIVE expR':>12}{'phantom':>10}"
          f"{'HONEST win%':>13}")
    for tr_, tg, fl in variants:
        k = f"{tr_} {tg} f{fl:.2f}"
        T, _ = res[(False, k)]
        if T.empty:
            continue
        st = stats(T, len(S))
        print(f"  {k:<18}{st['gapd']:>9.1f}%{st['slip']:>+13.3f}"
              f"{st['exp']:>+13.3f}{st['naive']:>+12.3f}"
              f"{st['naive'] - st['exp']:>+10.3f}{st['win']:>12.1f}%")

    print("\n" + "=" * 118)
    print("  BY YEAR — mean R, without the daily stop")
    print("=" * 118)
    print(f"  {'variant':<18}" + "".join(f"{y:>11}" for y in years))
    for tr_, tg, fl in variants:
        k = f"{tr_} {tg} f{fl:.2f}"
        T, _ = res[(False, k)]
        if T.empty:
            continue
        yr = stats(T, len(S))["yr"]
        print(f"  {k:<18}" + "".join(
            f"{yr[y]:>+11.3f}" if y in yr.index else f"{'--':>11}"
            for y in years))

    print("\n" + "=" * 118)
    print("  P1 vs P2 — is the levels story doing any work?")
    print("=" * 118)
    print(f"  {'trend':<8}{'floor':>7}{'P1 expR':>10}{'P2 expR':>10}"
          f"{'P1-P2':>9}{'P1 win%':>10}{'P2 win%':>10}{'P1 R:R':>9}"
          f"{'P2 R:R':>9}")
    for tr_, fl in product(G_TREND, G_FLOOR):
        A, _ = res[(False, f"{tr_} P1 f{fl:.2f}")]
        B, _ = res[(False, f"{tr_} P2 f{fl:.2f}")]
        if A.empty or B.empty:
            continue
        a, b = stats(A, len(S)), stats(B, len(S))
        print(f"  {tr_:<8}{fl:>7.2f}{a['exp']:>+10.3f}{b['exp']:>+10.3f}"
              f"{a['exp'] - b['exp']:>+9.3f}{a['win']:>10.1f}{b['win']:>10.1f}"
              f"{a['rr']:>9.2f}{b['rr']:>9.2f}")

    print("\n" + "=" * 118)
    print("  REJECTION CRITERIA, APPLIED (pre-registered; all must pass)")
    print("=" * 118)
    print(f"  {'variant':<18}{'expR>0':>8}{'sess>=15':>10}{'PF>=1.15':>10}"
          f"{'ex-top1%>0':>12}{'yrs+>=4':>9}{'t>3':>7}{'beats RW':>10}"
          f"{'SURVIVES':>10}")
    survivors = []
    for tr_, tg, fl in variants:
        k = f"{tr_} {tg} f{fl:.2f}"
        T, _ = res[(False, k)]
        if T.empty:
            continue
        st = stats(T, len(S))
        yp = sum(1 for y in years if st["yr"].get(y, -1) > 0)
        c = [st["exp"] > 0, st["sess"] >= 15, st["pf"] >= 1.15,
             st["ex1"] > 0, yp >= 4, st["t"] > 3, st["z"] > 2.73]
        ok = all(c)
        if ok:
            survivors.append(k)
        print(f"  {k:<18}" + "".join(
            f"{('yes' if x else 'NO'):>{w}}" for x, w in
            zip(c, (8, 10, 10, 12, 9, 7, 10)))
            + f"{('YES' if ok else 'no'):>10}")

    print("\n" + "=" * 118)
    print("  VERDICT")
    print("=" * 118)
    G = [stats(res[(False, f'{a} {b} f{c:.2f}')][0], len(S))
         for a, b, c in variants
         if not res[(False, f'{a} {b} f{c:.2f}')][0].empty]
    gaps = np.array([g["gap"] for g in G])
    print(f"  variants surviving all seven criteria: "
          f"{len(survivors)} of {len(variants)}")
    print(f"  hit-rate gap over the random-walk rate, across 8 variants:")
    print(f"      mean {gaps.mean():+.2f} pts   range "
          f"{gaps.min():+.2f} to {gaps.max():+.2f} pts")
    print(f"  the claim needs                        +42.2 pts")
    print(f"  total trades across the grid: {sum(g['n'] for g in G):,} "
          f"against the claim's 31")
    if survivors:
        print("\n  SURVIVORS: " + ", ".join(survivors))
    else:
        print("\n  NOTHING SURVIVES. The mechanised rule does not beat the "
              "random-walk rate its own")
        print("  realised reward:risk implies. The reported figure was method, "
              "not market.")
    print("\n  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
