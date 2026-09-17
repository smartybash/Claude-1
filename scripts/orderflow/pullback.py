#!/usr/bin/env python3
"""PULLBACK CONTINUATION, MECHANICAL, UNDER THE TRADER'S CONSTRAINTS.

Implements exactly the rule pre-registered in
`reports/pullback_preregistration.md`, committed at 7f19544 before this file
existed. Nothing here is a parameter that was chosen after seeing a result.

THE CONSTRAINTS, AS CODE

  at most two trades per session        MAX_TRADES, a hard counter
  never two positions at once           the state machine has one IN state and
                                        nothing can arm while it is occupied
  a second setup arms only after the
  first closes                          state returns to SCAN at the exit index
  hard stop fixed at entry              stop is computed at the trigger print
  flat by 22:30 Dubai                   HARD_FLAT = 18:30 UTC, market exit
  costs                                 COST_PTS charged on every round turn
  no unavailable information            every input is a running statistic over
                                        seconds already elapsed

THE BAR GRID

Ticks are collapsed to ONE-SECOND high/low bars. The state machine needs
extremes, not every print, and 400,000 prints a session across twenty sessions
and twelve variants is not a loop worth writing in Python. One second is finer
than any decision here and the loss is confined to ordering two events inside
the same second -- which is resolved pessimistically: **the stop is checked
before the target**, so a second that could have hit both is recorded as a
loss. Assuming otherwise is how the impossible fill got into this project.

Usage: python3 scripts/orderflow/pullback.py
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from roster import split                                                  # noqa
from tape import load_all, price_step, rth, session_day                    # noqa

TICK = 0.25

# --- fixed constants, from the pre-registration ---------------------------
RTH_OPEN_H, RTH_OPEN_M = 13, 30
BREAK_TICKS = 2
PB_LO, PB_HI = 0.25, 0.75
REJ_TICKS = 4
STOP_TICKS = 4
MAX_MIN = 60
LAST_ENTRY_H, LAST_ENTRY_M = 18, 0
HARD_FLAT_H, HARD_FLAT_M = 18, 30      # 22:30 Dubai, UTC+4
COST_PTS = 2.0
MAX_TRADES = 2

# --- the declared grid: 2 x 2 x 3 = 12 ------------------------------------
GRID_OR_MIN = (15, 30)
GRID_EXC = (0.5, 1.0)
GRID_TGT_R = (1.0, 1.5, 2.0)


def second_bars(s: pd.DataFrame):
    """(t, high, low) per second of the cash session, as numpy arrays."""
    d = session_day(s)
    open_t = d + pd.Timedelta(hours=RTH_OPEN_H, minutes=RTH_OPEN_M)
    flat_t = d + pd.Timedelta(hours=HARD_FLAT_H, minutes=HARD_FLAT_M)
    w = s[(s.time >= open_t) & (s.time <= flat_t)]
    if len(w) < 5000:
        return None
    g = w.set_index("time").price.resample("1s")
    hi = g.max().dropna()
    lo = g.min().reindex(hi.index)
    return (hi.index.to_numpy(), hi.to_numpy(np.float64),
            lo.to_numpy(np.float64), open_t, flat_t)


def run_session(bars, or_min: float, exc: float, tgt_r: float):
    """The pre-registered state machine. Returns a list of closed trades."""
    t, hi, lo, open_t, flat_t = bars
    or_end = open_t + pd.Timedelta(minutes=or_min)
    last_entry = (open_t.normalize() +
                  pd.Timedelta(hours=LAST_ENTRY_H, minutes=LAST_ENTRY_M))

    n = len(t)
    or_mask = t < np.datetime64(or_end)
    if or_mask.sum() < 30 or or_mask.all():
        return []
    orh = float(hi[or_mask].max())
    orl = float(lo[or_mask].min())
    orr = orh - orl
    if orr <= 0:
        return []

    brk = BREAK_TICKS * TICK
    rej = REJ_TICKS * TICK
    stp = STOP_TICKS * TICK

    trades = []
    state = "SCAN"
    i = int(np.searchsorted(t, np.datetime64(or_end), "left"))
    direction = 0
    edge = extreme = zone_far = zone_near = pb_ext = 0.0
    entry = stop = target = 0.0
    expires = None

    while i < n and len(trades) < MAX_TRADES:
        h, l, now = hi[i], lo[i], t[i]

        if state == "SCAN":
            if h >= orh + brk:
                direction, edge, extreme = 1, orh, h
                state = "EXTEND"
            elif l <= orl - brk:
                direction, edge, extreme = -1, orl, l
                state = "EXTEND"
            i += 1
            continue

        if state == "EXTEND":
            extreme = max(extreme, h) if direction > 0 else min(extreme, l)
            if abs(extreme - edge) >= exc * orr:
                move = abs(extreme - edge)
                zone_far = extreme - direction * PB_LO * move
                zone_near = extreme - direction * PB_HI * move
                state = "WAIT"
            else:
                back = l if direction > 0 else h
                if direction * (back - edge) < -brk:
                    state = "SCAN"
            i += 1
            continue

        if state == "WAIT":
            reached = l <= zone_far if direction > 0 else h >= zone_far
            if reached:
                pb_ext = l if direction > 0 else h
                state = "ARMED"
            else:
                beyond = l if direction > 0 else h
                if direction * (beyond - zone_near) < 0 or \
                   direction * (beyond - edge) < 0:
                    state = "SCAN"
            i += 1
            continue

        if state == "ARMED":
            pb_ext = min(pb_ext, l) if direction > 0 else max(pb_ext, h)
            if direction * (pb_ext - edge) < 0:
                state = "SCAN"
                i += 1
                continue
            trigger = pb_ext + direction * rej
            hit = h >= trigger if direction > 0 else l <= trigger
            if hit and now < np.datetime64(last_entry):
                entry = trigger
                stop = pb_ext - direction * stp
                risk = abs(entry - stop)
                if risk <= 0:
                    state = "SCAN"
                    i += 1
                    continue
                target = entry + direction * tgt_r * risk
                expires = now + np.timedelta64(MAX_MIN, "m")
                state = "IN"
                entry_i = i
            i += 1
            continue

        if state == "IN":
            # stop before target on the same second, deliberately pessimistic
            stopped = l <= stop if direction > 0 else h >= stop
            hit_tgt = h >= target if direction > 0 else l <= target
            exit_px = None
            if stopped:
                exit_px, why = stop, "stop"
            elif hit_tgt:
                exit_px, why = target, "target"
            elif now >= expires:
                exit_px, why = (h + l) / 2.0, "expiry"
            elif i == n - 1:
                exit_px, why = (h + l) / 2.0, "flat"
            if exit_px is None:
                i += 1
                continue
            pnl = direction * (exit_px - entry) - COST_PTS
            trades.append(dict(dir=direction, entry=entry, stop=stop,
                               target=target, exit=exit_px, why=why,
                               pnl=pnl, risk=abs(entry - stop),
                               bars_held=i - entry_i))
            state = "SCAN"
            i += 1
            continue

    return trades


def sessions():
    days = load_all()
    disc, hold, bad = split(days)
    out = {}
    for d in sorted(disc):
        if price_step(disc[d]) >= 1.0:
            continue
        b = second_bars(rth(disc[d]))
        if b is not None:
            out[d] = b
    return out


def evaluate(per, or_min, exc, tgt_r):
    rows = []
    for d, bars in per.items():
        for tr in run_session(bars, or_min, exc, tgt_r):
            rows.append({**tr, "day": d})
    return pd.DataFrame(rows)


def metrics(T, days_all, cost_extra=0.0):
    if T.empty:
        return None
    pnl = T.pnl - cost_extra
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 \
        else float("inf")
    per = pnl.groupby(T.day).sum()
    per = per.reindex(days_all).fillna(0.0)
    t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 2 else 0.0
    top5 = pnl.sort_values(ascending=False).head(5).sum()
    return dict(
        n=len(T), sessions=T.day.nunique(), exp=pnl.mean(), win=100 * (pnl > 0).mean(),
        pf=pf, avg_win=wins.mean() if len(wins) else 0.0,
        avg_loss=losses.mean() if len(losses) else 0.0, worst=pnl.min(),
        total=pnl.sum(), ex_top5=pnl.sum() - top5,
        sess_mean=per.mean(), sess_t=t, sess_pos=int((per > 0).sum()),
        sess_n=len(per))


def main():
    per = sessions()
    days_all = sorted(per)
    half = len(days_all) // 2
    first, second = set(days_all[:half]), set(days_all[half:])

    print("=" * 100)
    print("PULLBACK CONTINUATION — 12 PRE-REGISTERED VARIANTS")
    print("=" * 100)
    print(f"  sessions ({len(days_all)}): {' '.join(d[4:] for d in days_all)}")
    print(f"  0.25 grid, discovery pile only. Sealed days not read.")
    print(f"  flat 18:30 UTC (22:30 Dubai)   last entry 18:00 UTC   "
          f"cost {COST_PTS} pts/round turn")
    print(f"  max {MAX_TRADES} trades/session, never concurrent\n")

    results = {}
    print("  TRADE COUNTS FIRST, before any performance number:\n")
    print(f"  {'variant':<22}{'trades':>8}{'sessions':>10}{'trades/sess':>13}")
    for or_min, exc, tgt in product(GRID_OR_MIN, GRID_EXC, GRID_TGT_R):
        key = f"OR{or_min} EXC{exc} R{tgt}"
        T = evaluate(per, or_min, exc, tgt)
        results[key] = T
        ns = T.day.nunique() if not T.empty else 0
        print(f"  {key:<22}{len(T):>8}{ns:>10}"
              f"{(len(T)/ns if ns else 0):>13.2f}")

    print("\n" + "=" * 100)
    print("  PER TRADE")
    print("=" * 100)
    print(f"  {'variant':<22}{'n':>5}{'exp':>8}{'win%':>7}{'PF':>7}"
          f"{'avgW':>8}{'avgL':>8}{'worst':>8}{'ex-top5':>9}")
    M = {}
    for key, T in results.items():
        m = metrics(T, days_all)
        M[key] = m
        if m is None:
            print(f"  {key:<22}  no trades")
            continue
        print(f"  {key:<22}{m['n']:>5}{m['exp']:>+8.2f}{m['win']:>7.1f}"
              f"{m['pf']:>7.2f}{m['avg_win']:>+8.2f}{m['avg_loss']:>+8.2f}"
              f"{m['worst']:>+8.2f}{m['ex_top5']:>+9.1f}")

    print("\n" + "=" * 100)
    print("  PER SESSION  (t across sessions; two trades in a day are not independent)")
    print("=" * 100)
    print(f"  {'variant':<22}{'sess w/ trade':>14}{'mean/sess':>11}{'t':>8}"
          f"{'sess +ve':>10}{'half1':>8}{'half2':>8}")
    for key, T in results.items():
        m = M[key]
        if m is None:
            continue
        h1 = T[T.day.isin(first)].pnl.sum()
        h2 = T[T.day.isin(second)].pnl.sum()
        print(f"  {key:<22}{m['sessions']:>14}{m['sess_mean']:>+11.2f}"
              f"{m['sess_t']:>+8.2f}{m['sess_pos']:>4}/{m['sess_n']:<5}"
              f"{h1:>+8.1f}{h2:>+8.1f}")

    print("\n" + "=" * 100)
    print("  REJECTION CRITERIA, FIXED IN ADVANCE")
    print("=" * 100)
    print("  1 expectancy <= 0   2 fewer than 15 sessions traded   3 PF < 1.15")
    print("  4 removing best 5 trades leaves total <= 0   5 either half negative\n")
    survivors = []
    for key, T in results.items():
        m = M[key]
        if m is None:
            print(f"  {key:<22} REJECT  no trades")
            continue
        h1 = T[T.day.isin(first)].pnl.sum()
        h2 = T[T.day.isin(second)].pnl.sum()
        fails = []
        if m["exp"] <= 0:
            fails.append("1 expectancy")
        if m["sessions"] < 15:
            fails.append(f"2 only {m['sessions']} sessions")
        if m["pf"] < 1.15:
            fails.append(f"3 PF {m['pf']:.2f}")
        if m["ex_top5"] <= 0:
            fails.append("4 top-5 dependent")
        if h1 <= 0 or h2 <= 0:
            fails.append("5 split-half")
        if fails:
            print(f"  {key:<22} REJECT  {'; '.join(fails)}")
        else:
            survivors.append(key)
            print(f"  {key:<22} survives")

    print(f"\n  survivors: {len(survivors)} of 12")
    if survivors:
        print("\n  ROBUSTNESS at 3.0 points of cost instead of 2.0:")
        for key in survivors:
            m3 = metrics(results[key], days_all, cost_extra=1.0)
            print(f"  {key:<22}exp {m3['exp']:>+6.2f}  PF {m3['pf']:>5.2f}  "
                  f"sess t {m3['sess_t']:>+5.2f}")
        print("\n  A SURVIVOR IS NOT A FINDING. The cap of two trades a session")
        print("  means these rest on a few dozen trades at most. Surviving the")
        print("  criteria means not yet killed; it is not evidence of an edge.")


if __name__ == "__main__":
    main()
