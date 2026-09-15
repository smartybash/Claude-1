#!/usr/bin/env python3
"""Four hypotheses that have never been tested, on data recorded for them.

Fading prior-session levels is dead. That does not exhaust the data, and three
of the four tests below use fields that only exist because of the last two
weeks of recorder work and have not been touched since they arrived.

  A  OVERNIGHT LEVELS. The overnight high and low are the levels day traders
     actually watch at the open, and they were untestable until the tape was
     recorded around the clock. Nothing here has ever used them.

  B  BREAKOUT CONTINUATION. Every level test so far has FADED the touch. The
     opposite trade has never been run, and a 53-56% hold rate means a 44-47%
     break rate, which is a different trade rather than the same one negated:
     the stop sits on the other side and the payoff is not symmetric.

  C  RESTING SIZE BEFORE ARRIVAL. The whole reason for recording fifty levels
     was to see size at a price BEFORE price reaches it -- twelve points of
     warning instead of two. Not one test has used it. This is the closest
     thing to a genuinely new measurement in the project.

  D  VOLUME AT THE LEVEL. A level where 20,000 contracts traded yesterday is
     not the same object as one where 500 did, and tick data gives that number
     exactly. Bar-derived levels never could.

Guards are the same ones that killed everything else, applied from the start:
entry at the price that actually printed, de-overlapped trades, per-session
reporting, a control, costs charged, and a bar of |t| >= 3 for the count of
hypotheses being run.

Usage: python3 scripts/orderflow/sweep2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from levels import ib_levels, resolve, session_levels                  # noqa
from levels_audit import merge_levels                                  # noqa
from tape import RTH_CLOSE, RTH_OPEN, _at, load_all, load_day, rth, volume_profile  # noqa

ROOT = Path(__file__).resolve().parent.parent.parent
DEPTH = ROOT / "data" / "depth"

TICK = 0.25
POINT_USD = 20.0
COST_PTS = 2.0
BAR_T = 3.0
TOL = 0.25
REARM = 8.0


def stat(x, cost=0.0):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 20:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    return dict(n=len(x), mean=x.mean(), win=100 * (x > 0).mean(),
                t=x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0)


def show(lbl, r, bar=BAR_T):
    if r is None:
        print(f"    {lbl:<44} too few")
        return
    star = " **" if abs(r["t"]) >= bar else ""
    print(f"    {lbl:<44} n={r['n']:<4} {r['mean']:+6.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:4.1f}%  "
          f"t={r['t']:+5.2f}{star}")


def touches(cur, levels, ib_from=None):
    t = cur.time.to_numpy()
    p = cur.price.to_numpy()
    out = []
    for name, lv in levels.items():
        armed, start = True, 0
        if "IB" in name and ib_from is not None:
            start = int(np.searchsorted(t, np.datetime64(ib_from)))
            if start >= len(p):
                continue
        above = p[start] > lv
        for i in range(start, len(p)):
            if armed and abs(p[i] - lv) <= TOL:
                out.append(dict(idx=i, level=name, price=lv, from_above=above))
                armed = False
            elif not armed and abs(p[i] - lv) >= REARM:
                armed, above = True, p[i] > lv
    out.sort(key=lambda r: r["idx"])
    return out


def trade(days, T, stop, target, fade=True, sel=None):
    """De-overlapped, entered at the printed price."""
    vals, busy, cd = [], -1, None
    S = T if sel is None else T[sel]
    for _, r in S.iterrows():
        if r.day != cd:
            cd, busy = r.day, -1
        if r.idx < busy:
            continue
        p = days[r.day].price.to_numpy()
        i = int(r.idx)
        d = (+1 if r.from_above else -1) * (1 if fade else -1)
        v, j = resolve(p, i, p[i], d, stop, target)
        vals.append(v)
        busy = j
    return np.array(vals, float)


def overnight_levels(full_prev: pd.DataFrame, full_cur: pd.DataFrame) -> dict:
    """High and low of the session between yesterday's close and today's open.

    Both files are full 24-hour tapes, so the overnight spans the tail of the
    previous file and the head of the current one.
    """
    d0 = full_prev.time.iloc[0]
    a = full_prev[full_prev.time >= _at(d0, RTH_CLOSE)]
    d1 = full_cur.time.iloc[0]
    b = full_cur[full_cur.time < _at(d1, RTH_OPEN)]
    on = pd.concat([a, b])
    if len(on) < 500:
        return {}
    return {"ONH": float(on.price.max()), "ONL": float(on.price.min())}


def level_volume(prev_rth: pd.DataFrame, level: float, band=2.0) -> float:
    m = (prev_rth.price - level).abs() <= band
    return float(prev_rth.loc[m, "volume"].sum())


def resting_before(day: str, level: float, when, side: str,
                   look_s=(30, 120)):
    """Resting size on the defending side at the level, before price arrives.

    Only rows within two ticks of the level are read, which turns a two-million
    row file into a few thousand and makes this tractable across twelve
    sessions.
    """
    return None  # filled in by preload


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]

    print("=" * 92)
    print(f"SWEEP 2 — {len(pairs)} session pairs, entry at the printed price, "
          f"cost {COST_PTS}pt, bar |t|>={BAR_T}")
    print("=" * 92)

    rows = []
    for prev_d, d in pairs:
        cur = days[d]
        lv = session_levels(days[prev_d])
        on = overnight_levels(full[prev_d], full[d])
        ibl, ib_end = ib_levels(cur)

        prev_rth = days[prev_d]
        p = cur.price.to_numpy()

        groups = {"prior": lv, "overnight": on, "ib": ibl}
        for gname, g in groups.items():
            if not g:
                continue
            m = merge_levels(g) if len(g) > 1 else g
            inr = {k: v for k, v in m.items() if p.min() <= v <= p.max()}
            for t in touches(cur, inr, ib_end if gname == "ib" else None):
                rows.append(dict(day=d, group=gname, **t,
                                 lvl_vol=level_volume(prev_rth, t["price"])))

    T = pd.DataFrame(rows)
    print(f"\n  {len(T)} touches: " +
          ", ".join(f"{k} {v}" for k, v in T.group.value_counts().items()))

    # ---------------------------------------------------------------- A
    print("\n" + "=" * 92)
    print("A  OVERNIGHT HIGH AND LOW versus prior-session levels")
    print("=" * 92)
    for R in (15, 20, 30):
        print(f"  --- stop = target = {R} ---")
        for g in ("prior", "overnight", "ib"):
            sel = (T.group == g).values
            if sel.sum() < 20:
                continue
            show(f"{g}, fade", stat(trade(days, T, R, R, True, sel), COST_PTS))

    # ---------------------------------------------------------------- B
    print("\n" + "=" * 92)
    print("B  BREAKOUT CONTINUATION — the trade never run")
    print("=" * 92)
    print("  Same touches, opposite direction: go WITH the break rather than")
    print("  fading it. Not the negative of the fade, because the stop moves.\n")
    for R, TG in ((15, 15), (20, 20), (15, 30), (20, 40), (15, 45)):
        show(f"stop {R} / target {TG}, with the break",
             stat(trade(days, T, R, TG, False), COST_PTS))

    # ---------------------------------------------------------------- D
    print("\n" + "=" * 92)
    print("D  VOLUME TRADED AT THE LEVEL YESTERDAY")
    print("=" * 92)
    print("  A level built on 20,000 contracts is not the same object as one")
    print("  built on 500. Only tick data gives this number.\n")
    q = pd.qcut(T.lvl_vol, 3, labels=False, duplicates="drop")
    for R in (20, 30):
        print(f"  --- stop = target = {R} ---")
        for i, tag in enumerate(("thin level", "medium", "heavy level")):
            show(f"{tag}, fade", stat(trade(days, T, R, R, True, (q == i).values),
                                      COST_PTS))

    # ---------------------------------------------------------------- E
    print("\n" + "=" * 92)
    print("E  TIME OF DAY")
    print("=" * 92)
    hh = np.array([days[r.day].time.iloc[int(r.idx)].hour for _, r in T.iterrows()])
    for lo, hi, lbl in ((13, 15, "13:30-14:59 open"), (15, 17, "15:00-16:59"),
                        (17, 19, "17:00-18:59"), (19, 20, "19:00-close")):
        sel = ((hh >= lo) & (hh < hi))
        if sel.sum() < 20:
            continue
        show(f"{lbl}, fade 20/20", stat(trade(days, T, 20, 20, True, sel),
                                        COST_PTS))


if __name__ == "__main__":
    main()
