#!/usr/bin/env python3
"""THE GAP TRADE — gap at the open, structure turns, price travels back.

Annotated on a live chart: gap down at the open, a 5-minute fair value gap that
holds as a higher low rather than breaking, a second higher low, a break of
structure, then enter toward the gap level.

Every element of that is definable, so it can be measured instead of admired:

    gap          RTH open minus the previous RTH close
    gap level    the previous close -- what "filling the gap" means
    swing        a pivot low or high, lower/higher than N bars either side
    HL           a swing low above the previous swing low
    FVG          a three-bar imbalance: bar i's low above bar i-2's high
    BOS          a close through the most recent swing high

The order of questions matters. Before asking whether the entry technique adds
anything, ask whether the destination is reachable at all: **how often does the
gap actually fill during the session?** If that base rate is 55%, no amount of
structure reading turns it into a trade. If it is 85%, the entry is the only
open question.

Recorded sessions carry full overnight tape, so the previous close and the
opening gap are exact rather than inferred from bars.

Usage: python3 scripts/orderflow/gapfill.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import RTH_CLOSE, RTH_OPEN, _at, load_all, rth                 # noqa

POINT_USD = 20.0
COST_PTS = 2.0
PIVOT = 2            # bars either side that define a swing
MIN_GAP = 10.0       # points; below this there is no gap to trade
DAILY = Path(__file__).resolve().parents[2] / "data" / "daily_long"


def daily_base_rate():
    """The base rate on 27 years of daily bars, not 15 recorded sessions.

    Fifteen sessions cannot answer "how often does a gap fill" -- the answer
    would carry an error bar of +/-13 points of probability and every bucket
    would hold two or three days. The daily files hold 6,600 sessions each of
    QQQ and SPY going back to 1999, and a gap is fully defined by four numbers
    that a daily bar already contains: previous close, open, high, low. So the
    question can be answered at 400x the sample size, on the same instrument
    family, before spending any of the tick data on it.

    Gaps are measured in PERCENT here rather than points, because a 100-point
    gap in 2026 and a 100-point gap in 2010 are not the same event.

    The second table is the one that decides the trade. "Filled" is a yes/no
    on the whole gap; what an entry actually needs to know is how far toward
    the gap level price travels on the days it does not fill, because that is
    where the target has to sit.
    """
    print("=" * 92)
    print("0  THE BASE RATE ON 27 YEARS — 13,000 sessions, not 15")
    print("=" * 92)
    if not DAILY.exists():
        print("  no daily data")
        return
    buckets = ((0, .0015, "under 0.15%"), (.0015, .003, "0.15 to 0.3%"),
               (.003, .005, "0.3 to 0.5%"), (.005, .01, "0.5 to 1%"),
               (.01, .02, "1 to 2%"), (.02, 9.9, "over 2%"))
    for sym in ("QQQ", "SPY"):
        f = DAILY / f"{sym}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f, parse_dates=["timestamp"]).sort_values("timestamp")
        d["pc"] = d.close.shift(1)
        d = d.dropna(subset=["pc"])
        d["gap"] = (d.open - d.pc) / d.pc
        down = d.gap < 0
        d["filled"] = np.where(down, d.high >= d.pc, d.low <= d.pc)
        # share of the gap closed at the day's best excursion toward it
        reach = np.where(down, d.high - d.open, d.open - d.low)
        d["closed"] = (reach / (d.pc - d.open).abs()).clip(0, 2)
        d["ag"] = d.gap.abs()

        print(f"\n  {sym}  {len(d):,} sessions, "
              f"{d.timestamp.iloc[0]:%Y-%m-%d} to {d.timestamp.iloc[-1]:%Y-%m-%d}")
        print(f"    {'gap size':<16}{'n':>7}{'fills':>8}"
              f"{'median % of gap closed':>26}")
        for lo, hi, lbl in buckets:
            g = d[(d.ag >= lo) & (d.ag < hi)]
            if len(g) < 20:
                continue
            print(f"    {lbl:<16}{len(g):>7}{100*g.filled.mean():>7.0f}%"
                  f"{100*g.closed.median():>25.0f}%")
        print(f"    {'ALL':<16}{len(d):>7}{100*d.filled.mean():>7.0f}%"
              f"{100*d.closed.median():>25.0f}%")
    print("\n  Scale for NQ at 29,400:  1% = 294 pts,  0.3% = 88 pts,"
          "  0.15% = 44 pts.")

    # The fix the first table implies. On big gaps the median day still closes
    # ~78% of the gap -- price goes nearly all the way and turns. A target AT
    # the gap level converts those days into losses for the sake of the last
    # fifth of the move, so ask the same question at shorter targets.
    print("\n  How often does price reach PART of the way back?  (QQQ + SPY)")
    both = []
    for sym in ("QQQ", "SPY"):
        f = DAILY / f"{sym}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f, parse_dates=["timestamp"]).sort_values("timestamp")
        d["pc"] = d.close.shift(1)
        d = d.dropna(subset=["pc"])
        d["gap"] = (d.open - d.pc) / d.pc
        down = d.gap < 0
        reach = np.where(down, d.high - d.open, d.open - d.low)
        d["closed"] = reach / (d.pc - d.open).abs()
        # and how far it ran the OTHER way -- the stop's side of the bar
        away = np.where(down, d.open - d.low, d.high - d.open)
        d["adverse"] = away / (d.pc - d.open).abs()
        d["ag"] = d.gap.abs()
        both.append(d[["ag", "closed", "adverse"]])
    if not both:
        return
    A = pd.concat(both)
    head = "".join(f"{str(int(100*t)) + '% back':>10}"
                   for t in (0.33, 0.5, 0.75, 1.0))
    print(f"    {'gap size':<16}{'n':>7}{head}")
    for lo, hi, lbl in buckets:
        g = A[(A.ag >= lo) & (A.ag < hi)]
        if len(g) < 40:
            continue
        row = "".join(f"{100*(g.closed >= t).mean():>9.0f}%"
                      for t in (0.33, 0.5, 0.75, 1.0))
        print(f"    {lbl:<16}{len(g):>7}{row}")
    print("\n  Those are BEST-CASE excursions, not win rates. They say the")
    print("  target is reachable; they say nothing about what price did first.")
    print("  So put a stop on it. 'unknown' is the share of days that touched")
    print("  the target AND the stop -- a daily bar cannot order them, so both")
    print("  bounds are given. Where worst and best agree in sign, the")
    print("  ambiguity is not load-bearing and the verdict is settled.\n")

    # Enter at the open toward the gap, target the gap level, stop the same
    # distance the other way -- one to one, so the win rate IS the edge.
    #
    # A daily bar cannot say whether the high or the low came first, so days
    # that touched both are genuinely unknown. Rather than quietly assign them,
    # both bounds are shown: every ambiguous day a loss, and every ambiguous
    # day a win. The truth is between, and if BOTH bounds point the same way
    # the ambiguity does not matter.
    for t, tag in ((1.0, "target the gap level"), (0.5, "target half the gap")):
        print(f"    --- {tag}, stop the same distance away, 1:1 ---")
        print(f"    {'gap size':<16}{'n':>7}{'clean win':>11}{'clean loss':>12}"
              f"{'unknown':>10}{'worst':>9}{'best':>8}")
        for lo, hi, lbl in buckets:
            g = A[(A.ag >= lo) & (A.ag < hi)]
            if len(g) < 40:
                continue
            hit = (g.closed >= t).to_numpy()
            adv = (g.adverse >= t).to_numpy()
            both_t = hit & adv
            win, loss = hit & ~adv, ~hit
            w, l, u = win.mean(), loss.mean(), both_t.mean()
            print(f"    {lbl:<16}{len(g):>7}{100*w:>10.0f}%{100*l:>11.0f}%"
                  f"{100*u:>9.0f}%{w - l - u:>8.2f}R{w + u - l:>7.2f}R")
        print()


def bars5(s: pd.DataFrame) -> pd.DataFrame:
    b = s.set_index("time").resample("5min").agg(
        o=("price", "first"), h=("price", "max"),
        l=("price", "min"), c=("price", "last"),
        v=("volume", "sum"), d=("signed", "sum"))
    return b.dropna(subset=["c"])


def swings(b: pd.DataFrame, k: int = PIVOT):
    """Indices of pivot lows and highs. A pivot is confirmed k bars later, so
    nothing here can be known before bar i+k -- which is where the entry logic
    must start looking, not at bar i."""
    lo, hi = [], []
    L, H = b.l.to_numpy(), b.h.to_numpy()
    for i in range(k, len(b) - k):
        if L[i] == L[i - k:i + k + 1].min():
            lo.append(i)
        if H[i] == H[i - k:i + k + 1].max():
            hi.append(i)
    return lo, hi


def stat(x, cost=COST_PTS):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 4:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    return dict(n=len(x), mean=x.mean(), win=100 * (x > 0).mean(),
                t=x.mean() / (sd / np.sqrt(len(x))) if sd > 0 and len(x) > 1 else 0.0,
                total=x.sum())


def show(lbl, r):
    if r is None:
        print(f"    {lbl:<46} too few")
        return
    print(f"    {lbl:<46} n={r['n']:<4} {r['mean']:+7.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:4.1f}%  "
          f"t={r['t']:+5.2f}  total {r['total']*POINT_USD:+,.0f}$")


def main():
    daily_base_rate()
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]

    rows = []
    for prev_d, d in pairs:
        prev, cur = days[prev_d], days[d]
        prev_close = float(prev.price.iloc[-1])
        open_px = float(cur.price.iloc[0])
        gap = open_px - prev_close
        rows.append(dict(day=d, prev_close=prev_close, open=open_px, gap=gap,
                         hi=float(cur.price.max()), lo=float(cur.price.min()),
                         close=float(cur.price.iloc[-1])))
    G = pd.DataFrame(rows)
    G["filled"] = np.where(G.gap < 0, G.hi >= G.prev_close, G.lo <= G.prev_close)
    G["absgap"] = G.gap.abs()

    print("=" * 92)
    print(f"1  THE BASE RATE — does the gap fill at all?   ({len(G)} sessions)")
    print("=" * 92)
    print("  Before asking whether the entry is clever, ask whether the target")
    print("  is reachable. 'Filled' means price traded back to the previous")
    print("  close at any point in the cash session.\n")
    big = G[G.absgap >= MIN_GAP]
    print(f"  {'gap size':<22}{'sessions':>9}{'filled':>9}{'rate':>8}")
    for lo, hi, lbl in ((0, 10, "under 10 pts"), (10, 25, "10 to 25"),
                        (25, 50, "25 to 50"), (50, 1e9, "over 50")):
        g = G[(G.absgap >= lo) & (G.absgap < hi)]
        if len(g) == 0:
            continue
        print(f"  {lbl:<22}{len(g):>9}{int(g.filled.sum()):>9}"
              f"{100*g.filled.mean():>7.0f}%")
    print(f"  {'ALL with gap >= 10':<22}{len(big):>9}{int(big.filled.sum()):>9}"
          f"{100*big.filled.mean() if len(big) else 0:>7.0f}%")

    print("\n  every gap session:")
    print(f"    {'day':<10}{'gap':>9}{'filled':>8}{'high':>11}{'low':>11}")
    for _, r in G.sort_values("absgap", ascending=False).iterrows():
        print(f"    {r.day:<10}{r.gap:>+9.1f}{'yes' if r.filled else 'NO':>8}"
              f"{r.hi:>11,.0f}{r.lo:>11,.0f}")

    # ---------------------------------------------------------------- trade
    print("\n" + "=" * 92)
    print("2  THE TRADE — wait for structure, then go for the gap")
    print("=" * 92)
    print("  Long after a gap DOWN, short after a gap UP. Entry on the close of")
    print("  the bar that breaks the last swing high (or low), only once a")
    print("  higher low (or lower high) is already in place. Stop beyond that")
    print("  swing, target the previous close. Pivots are confirmed two bars")
    print("  late, so nothing is known before it could have been.\n")

    trades = []
    for _, r in G.iterrows():
        if r.absgap < MIN_GAP:
            continue
        s = days[r.day]
        b = bars5(s)
        if len(b) < 20:
            continue
        lo_i, hi_i = swings(b)
        up = r.gap < 0                       # gap down -> look to buy
        C = b.c.to_numpy()
        L, H = b.l.to_numpy(), b.h.to_numpy()

        pivots = lo_i if up else hi_i
        opp = hi_i if up else lo_i
        entry = None
        for j in range(1, len(pivots)):
            p0, p1 = pivots[j - 1], pivots[j]
            better = (L[p1] > L[p0]) if up else (H[p1] < H[p0])
            if not better:
                continue
            # the structure break must come AFTER the pivot is confirmed
            ready = p1 + PIVOT
            prior = [q for q in opp if q < p1]
            if not prior:
                continue
            level = H[prior[-1]] if up else L[prior[-1]]
            for i in range(ready, len(b)):
                broke = C[i] > level if up else C[i] < level
                if broke:
                    entry = (i, float(C[i]), float(L[p1] if up else H[p1]))
                    break
            if entry:
                break
        if not entry:
            continue

        i, px, swing = entry
        stop = swing
        target = r.prev_close
        risk = abs(px - stop)
        if risk < 2 or risk > 60:
            continue
        # walk forward bar by bar; a bar that touches both is counted a loss
        out = None
        for k in range(i + 1, len(b)):
            if up:
                if L[k] <= stop:
                    out = -risk
                    break
                if H[k] >= target:
                    out = target - px
                    break
            else:
                if H[k] >= stop:
                    out = -risk
                    break
                if L[k] <= target:
                    out = px - target
                    break
        if out is None:
            out = (C[-1] - px) if up else (px - C[-1])
        trades.append(dict(day=r.day, gap=r.gap, pts=out, risk=risk,
                           r=out / risk))

    T = pd.DataFrame(trades)
    if T.empty:
        print("  no qualifying setups")
        return
    print(f"  {len(T)} setups over {len(big)} gap sessions\n")
    show("all gap setups", stat(T.pts.values))
    show("  gap 10-25 pts", stat(T[T.gap.abs() < 25].pts.values))
    show("  gap over 25 pts", stat(T[T.gap.abs() >= 25].pts.values))
    show("  gap down only (long)", stat(T[T.gap < 0].pts.values))
    show("  gap up only (short)", stat(T[T.gap > 0].pts.values))
    print(f"\n  in R terms: mean {T.r.mean():+.2f}R  median {T.r.median():+.2f}R"
          f"  median risk {T.risk.median():.0f} pts")
    print("\n  per session:")
    for _, r in T.iterrows():
        print(f"    {r.day:<10} gap {r.gap:+7.1f}  risk {r.risk:5.1f}  "
              f"{r.pts - COST_PTS:+7.1f}pt  {(r.pts-COST_PTS)*POINT_USD:+8.0f}$")


if __name__ == "__main__":
    main()
