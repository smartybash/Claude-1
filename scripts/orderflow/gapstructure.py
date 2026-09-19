#!/usr/bin/env python3
"""THE STRUCTURE TRADE, on 2,680 sessions of 5-minute bars.

The pattern as drawn on the chart: gap at the open, a fair value gap on the
5-minute that holds rather than breaking, a higher low, a second higher low, a
break of structure, then enter toward the gap level.

An earlier pass tested the BASE RATE on 13,500 daily bars and the STRUCTURE on
5 recorded sessions. Those two tests never met, and the objection to that is
correct: a daily bar holds four numbers and cannot express a higher low, so
nothing in it says whether reading structure adds anything. The open-entry
result says what a gap does to somebody who does not read structure. It is not
evidence about somebody who does.

This tests the structure itself, at size. Every term is defined causally --
nothing is used before the bar on which it could have been known:

    gap        RTH open minus previous RTH close
    pivot low  L[i] is the lowest of the k bars either side, so it is NOT
               known until bar i+k. Every search below starts at i+k.
    HL         a confirmed pivot low above the previous confirmed pivot low
    FVG        3-bar imbalance -- bullish when L[i] > H[i-2]
    FVG held   price traded back into the gap and left it without closing
               through the far side
    BOS        a CLOSE through the most recent confirmed pivot high
    entry      the close of the BOS bar
    stop       the higher low it was built on
    target     the gap level, or a share of it

The control is the point of the whole exercise. If structure reading adds
nothing, then entering at the open with the SAME stop distance and the SAME
target does as well. Run both on the same sessions and the difference is what
the structure is worth.

Results are reported in R (the trade risks 1R by construction) and converted to
NQ points at 29,400 so they mean something at the desk. Price levels come from
QQQ, which tracks the same index as NQ at about 1/41 of the scale; structure
percentages carry across, absolute point values are the conversion.

Usage: python3 scripts/orderflow/gapstructure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BARS = Path(__file__).resolve().parents[2] / "data" / "intraday_long" / "QQQ_5m.parquet"

PIVOT = 2                 # bars either side that confirm a swing
NQ_PRICE = 29_400.0       # for converting a percentage move into NQ points
COST_NQ = 2.0             # round-trip cost in NQ points
MIN_GAP_PCT = 0.0015      # below this there is no gap worth trading


def sessions() -> dict:
    d = pd.read_parquet(BARS).sort_values("timestamp").reset_index(drop=True)
    d["day"] = d.timestamp.dt.date
    out = {}
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < 60:          # half days and holiday stubs
            continue
        out[day] = g.reset_index(drop=True)
    return out


def pivots(L, H, k=PIVOT):
    """Confirmed swing lows and highs, as (index, confirmed_at) pairs."""
    lo, hi = [], []
    for i in range(k, len(L) - k):
        if L[i] == L[i - k:i + k + 1].min():
            lo.append((i, i + k))
        if H[i] == H[i - k:i + k + 1].max():
            hi.append((i, i + k))
    return lo, hi


def fvg_held(O, H, L, C, up, upto):
    """Was there a fair value gap before bar `upto` that price returned to and
    did not close through? That is the chart's "FVG didn't break, it was a HL"
    -- the imbalance acting as support rather than giving way."""
    for i in range(2, upto):
        if up:
            if L[i] <= H[i - 2]:
                continue
            top, bot = L[i], H[i - 2]          # the unfilled band
            for j in range(i + 1, upto):
                if L[j] <= top:                # came back into it
                    return not (C[j] < bot)    # held unless it closed through
        else:
            if H[i] >= L[i - 2]:
                continue
            bot, top = H[i], L[i - 2]
            for j in range(i + 1, upto):
                if H[j] >= bot:
                    return not (C[j] > top)
    return False


def find_entry(b, up, need_hl=1, need_fvg=False, last_bar=None,
               retest=None, wait=12):
    """retest: instead of taking the close of the break-of-structure bar, rest
    an order back at the level that was broken and take the trade only if price
    comes back to it within `wait` bars.

    This matters because of where the BOS close sits. The sequence is right
    about the turn -- the control proves that much -- but it confirms at the
    top of the leg, which is the worst price in it and the widest stop. A
    retest keeps the information and pays less for it. retest=0.0 rests at the
    broken level itself; 0.5 rests halfway back to the higher low.

    Returns the first bar where the whole sequence has completed, using only
    information available at that bar.
    """
    O, H, L, C = (b.open.to_numpy(), b.high.to_numpy(),
                  b.low.to_numpy(), b.close.to_numpy())
    n = len(b)
    last_bar = last_bar if last_bar is not None else n - 6
    lo, hi = pivots(L, H)
    piv = lo if up else hi
    opp = hi if up else lo

    hls = []                                    # confirmed higher lows so far
    for j in range(1, len(piv)):
        p0, p1 = piv[j - 1][0], piv[j][0]
        better = (L[p1] > L[p0]) if up else (H[p1] < H[p0])
        if not better:
            hls = []                            # sequence broken, start again
            continue
        hls.append(piv[j])
        if len(hls) < need_hl:
            continue

        ready = piv[j][1]                       # the HL is confirmed here
        prior = [q for q in opp if q[1] <= ready and q[0] < p1]
        if not prior:
            continue
        level = H[prior[-1][0]] if up else L[prior[-1][0]]

        for i in range(ready, min(n, last_bar + 1)):
            broke = C[i] > level if up else C[i] < level
            if not broke:
                continue
            if need_fvg and not fvg_held(O, H, L, C, up, i):
                break                           # this BOS fails the FVG test
            swing = float(L[p1] if up else H[p1])
            if retest is None:
                return i, float(C[i]), swing
            # rest an order between the broken level and the higher low
            want = level - retest * (level - swing) if up else \
                level + retest * (swing - level)
            for m in range(i + 1, min(n, i + 1 + wait)):
                # a limit fills only if price actually trades through it
                if (up and L[m] <= want) or (not up and H[m] >= want):
                    return m, float(want), swing
            break                               # never came back; no trade
        # no break came before the cut-off; keep extending the sequence
    return None


def run(b, up, entry_i, px, stop, target):
    """Walk forward bar by bar. A bar that touches both is counted a loss and
    also counted separately, so the size of that assumption is visible."""
    H, L, C = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy()
    risk = abs(px - stop)
    for k in range(entry_i + 1, len(b)):
        if up:
            hit_s, hit_t = L[k] <= stop, H[k] >= target
        else:
            hit_s, hit_t = H[k] >= stop, L[k] <= target
        if hit_s and hit_t:
            return -risk, True
        if hit_s:
            return -risk, False
        if hit_t:
            return (target - px) if up else (px - target), False
    out = (C[-1] - px) if up else (px - C[-1])
    return out, False


def stat(rows, label, show_amb=True):
    if len(rows) < 10:
        print(f"  {label:<40} n={len(rows):<5} too few")
        return None
    R = np.array([r["R"] for r in rows], float)
    nq = np.array([r["nq"] for r in rows], float)
    sd = R.std(ddof=1)
    t = R.mean() / (sd / np.sqrt(len(R))) if sd > 0 else 0.0
    amb = 100 * np.mean([r["amb"] for r in rows])
    tail = f"  amb {amb:3.0f}%" if show_amb else ""
    print(f"  {label:<40} n={len(R):<5} {R.mean():+6.3f}R  "
          f"win {100*(R > 0).mean():4.1f}%  t={t:+5.2f}  "
          f"{nq.mean():+7.1f} NQ pts{tail}")
    return dict(n=len(R), R=R.mean(), t=t, win=100 * (R > 0).mean(),
                nq=nq.mean())


def collect(days, keys, need_hl, need_fvg, target_share, control=False,
            only_days=None, fixed_risk=None, rr=None, min_rr=None,
            retest=None):
    """control=True enters blind at the open instead of after the sequence.

    Two things have to be right for that comparison to mean anything. The
    control must run on THE SAME sessions -- a structure trade is dropped when
    price has already reached the gap level by the time the sequence completes,
    and those days are not comparable. And its stop must not be the structure's
    own swing, which had not formed at the open: pass fixed_risk to use one
    constant width instead of peeking.
    """
    rows = []
    for d0, d1 in zip(keys, keys[1:]):
        if only_days is not None and d1 not in only_days:
            continue
        prev, b = days[d0], days[d1]
        pc = float(prev.close.iloc[-1])
        op = float(b.open.iloc[0])
        gap = (op - pc) / pc
        if abs(gap) < MIN_GAP_PCT:
            continue
        up = gap < 0
        got = find_entry(b, up, need_hl, need_fvg, retest=retest)
        if got is None:
            continue
        i, px, stop = got
        risk = abs(px - stop)
        if risk <= 0 or risk / px > 0.02:       # a 2%-wide stop is not a trade
            continue

        if control:
            px = float(b.open.iloc[0])
            risk = px * fixed_risk if fixed_risk else risk
            stop = px - risk if up else px + risk
            i = 0

        full = pc
        if rr is not None:
            # Target a fixed multiple of the risk instead of the gap level.
            # The gap level is wherever it happens to be -- some days that is
            # 0.6R away and some days 5R, and a trade whose reward is decided
            # by an accident of the open is not a trade with an edge, it is a
            # lottery over R:R. Fixing the multiple separates the two.
            target = px + rr * risk if up else px - rr * risk
        else:
            target = px + target_share * (full - px) if up else \
                px - target_share * (px - full)
        if (up and target <= px) or (not up and target >= px):
            continue
        avail = (full - px) / risk if up else (px - full) / risk
        if min_rr is not None and avail < min_rr:
            continue
        pnl, amb = run(b, up, i, px, stop, target)
        nq = pnl / px * NQ_PRICE - COST_NQ
        rows.append(dict(day=d1, gap=gap, R=pnl / risk - COST_NQ / (risk / px * NQ_PRICE),
                         nq=nq, amb=amb, risk_pct=risk / px, avail=avail,
                         hour=b.timestamp.iloc[i].hour))
    return rows


def main():
    days = sessions()
    keys = sorted(days)
    print("=" * 96)
    print(f"THE STRUCTURE TRADE — {len(keys):,} sessions, "
          f"{keys[0]} to {keys[-1]}, 5-minute bars")
    print("=" * 96)
    print("  R is net of a 2-point NQ round trip. 'amb' is the share of trades")
    print("  where one bar touched both target and stop -- those are counted")
    print("  LOSSES, so a low number means the result barely depends on it.\n")

    print("1  DOES THE STRUCTURE BEAT ENTERING BLIND?")
    print("-" * 96)
    print("  Identical sessions, identical risk, identical target. The only")
    print("  difference is whether the entry waited for the sequence.\n")
    base = collect(days, keys, 2, False, 1.0)
    same = {r["day"] for r in base}
    med = float(np.median([r["risk_pct"] for r in base]))
    ctrl = collect(days, keys, 2, False, 1.0, control=True,
                   only_days=same, fixed_risk=med)
    a = stat(base, "2 HLs + break of structure")
    c = stat(ctrl, f"control: open, fixed {100*med:.2f}% stop")
    if a and c:
        d = a["R"] - c["R"]
        se = np.sqrt(np.var([r["R"] for r in base], ddof=1) / a["n"] +
                     np.var([r["R"] for r in ctrl], ddof=1) / c["n"])
        print(f"\n  structure minus control: {d:+.3f}R  "
              f"({a['nq'] - c['nq']:+.1f} NQ pts a trade)  t={d/se:+.2f}")
        print(f"  same {len(same):,} sessions on both sides; the control's stop")
        print(f"  is one constant width, so it is not peeking at the swing.")

    print("\n2  MORE OF THE PATTERN — does each extra condition help?")
    print("-" * 96)
    stat(collect(days, keys, 1, False, 1.0), "1 higher low + BOS")
    stat(collect(days, keys, 2, False, 1.0), "2 higher lows + BOS  (as drawn)")
    stat(collect(days, keys, 3, False, 1.0), "3 higher lows + BOS")
    stat(collect(days, keys, 1, True, 1.0), "1 HL + BOS + an FVG that held")
    stat(collect(days, keys, 2, True, 1.0), "2 HLs + BOS + an FVG that held")

    print("\n3  THE TARGET — the gap level is the ambition, not the only choice")
    print("-" * 96)
    for share, lbl in ((1.0, "the gap level"), (0.75, "3/4 of the gap"),
                       (0.5, "half the gap"), (0.33, "a third of the gap")):
        stat(collect(days, keys, 2, False, share), f"2 HLs, target {lbl}")

    print("\n4  BY GAP SIZE — 2 HLs + BOS, target the gap level")
    print("-" * 96)
    rows = collect(days, keys, 2, False, 1.0)
    for lo, hi, lbl in ((.0015, .003, "0.15 to 0.3%"), (.003, .005, "0.3 to 0.5%"),
                        (.005, .01, "0.5 to 1%"), (.01, 9, "over 1%")):
        sel = [r for r in rows if lo <= abs(r["gap"]) < hi]
        stat(sel, f"gap {lbl}")

    print("\n4b  TARGET A MULTIPLE OF RISK, NOT THE GAP")
    print("-" * 96)
    print("  The gap level sits wherever the open put it -- 0.6R away on one")
    print("  day and 5R on another. Fixing the multiple asks whether the")
    print("  sequence predicts a MOVE, separately from where the gap happens")
    print("  to be.\n")
    for m in (1.0, 1.5, 2.0, 3.0):
        stat(collect(days, keys, 2, False, 1.0, rr=m), f"2 HLs, target {m:.1f}R")

    print("\n4c  ONLY WHEN THE GAP IS FAR ENOUGH TO BE WORTH IT")
    print("-" * 96)
    print("  Take the trade only when the gap level is at least N times the")
    print("  stop away. This is the filter a desk would actually apply, and")
    print("  it is known at the entry bar.\n")
    for m in (1.0, 1.5, 2.0, 3.0):
        stat(collect(days, keys, 2, False, 1.0, min_rr=m),
             f"2 HLs, gap at least {m:.1f}R away")

    print("\n4d  ENTER ON THE RETEST, NOT ON THE BREAK")
    print("-" * 96)
    print("  The break-of-structure close is the top of the leg: the worst")
    print("  price in the sequence and the widest stop. Rest the order back at")
    print("  the level instead and take the trade only if price returns to it")
    print("  within an hour. A limit fills only if price trades THROUGH it.\n")
    for rt, lbl in ((0.0, "at the broken level"),
                    (0.25, "a quarter back toward the HL"),
                    (0.5, "halfway back toward the HL")):
        stat(collect(days, keys, 2, False, 1.0, retest=rt),
             f"2 HLs, retest {lbl}")
    print()
    for rt in (0.0, 0.5):
        stat(collect(days, keys, 2, False, 1.0, retest=rt, rr=2.0),
             f"2 HLs, retest {rt:.2f}, target 2.0R")

    print("\n5  BY DIRECTION AND BY ERA — is it one regime or all of them?")
    print("-" * 96)
    stat([r for r in rows if r["gap"] < 0], "gap DOWN, long toward the gap")
    stat([r for r in rows if r["gap"] > 0], "gap UP, short toward the gap")
    print()
    for y0, y1 in ((2016, 2018), (2019, 2021), (2022, 2024), (2025, 2027)):
        sel = [r for r in rows if y0 <= r["day"].year <= y1]
        stat(sel, f"{y0}-{min(y1, 2026)}", show_amb=False)


if __name__ == "__main__":
    main()
