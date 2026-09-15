#!/usr/bin/env python3
"""GO WITH THE BREAK, TARGET THE NEXT LEVEL — and on which timeframe?

The proposal: once one side of the auction has won, a break of structure or a
change of character says so, and the trade is to go WITH it toward the next
level of confluence rather than to fade anything.

That is a different trade from everything tested so far here, and the
difference matters. Every losing version in this project was a FADE -- betting
that a level holds. This bets that structure continues, and the target is not a
fixed number of points but the next reference price in the way. Whether the
reward is worth the risk is therefore decided by where the levels happen to
sit, which is the market's choice rather than a parameter.

Two events, deliberately kept apart because they are not the same thing:

    BOS    a close through the last swing high while already making higher
           highs and higher lows -- continuation, the trend keeps going
    CHoCH  a close through the last swing high while making LOWER highs and
           lower lows -- the first crack in the other direction, a reversal

The timeframe question is the other half of the request, and it is answerable
at size: 5-minute bars produce a lot of labels and most of them may be noise.
Every timeframe below is run identically, and the table reports how many
signals each produces as well as what they are worth, so "too many labels" and
"worth trading" can be told apart.

Signals are computed on the resampled timeframe. Outcomes are simulated on
1-MINUTE bars regardless, so a stop and a target inside one 15-minute bar are
ordered correctly rather than guessed at.

Levels for the target come from the previous cash session, exactly as in
levels_long.py: high, low, close, VAH, POC, VAL.

Usage: python3 scripts/orderflow/structure_trade.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BARS = Path(__file__).resolve().parents[2] / "data" / "intraday_long" / "QQQ_1m.parquet"

NQ_PRICE = 29_400.0
COST_NQ = 2.0
PIVOT = 2
BUCKET_NQ = 2.0
VALUE_AREA = 0.70
TIMEFRAMES = [1, 3, 5, 15, 30]


def sessions() -> dict:
    d = pd.read_parquet(BARS).sort_values("timestamp").reset_index(drop=True)
    d = d.rename(columns={"open": "o", "high": "h", "low": "l",
                          "close": "c", "volume": "v"})
    d["day"] = d.timestamp.dt.date
    return {day: g.reset_index(drop=True)
            for day, g in d.groupby("day", sort=True) if len(g) >= 300}


def resample(b: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes == 1:
        return b.reset_index(drop=True)
    g = b.set_index("timestamp").resample(f"{minutes}min")
    r = g.agg(o=("o", "first"), h=("h", "max"), l=("l", "min"),
              c=("c", "last"), v=("v", "sum")).dropna(subset=["c"])
    return r.reset_index()


def profile(b, bucket):
    lo, hi, v = b.l.to_numpy(), b.h.to_numpy(), b.v.to_numpy()
    base = np.floor(lo.min() / bucket) * bucket
    n = int(np.ceil((hi.max() - base) / bucket)) + 1
    acc = np.zeros(n)
    i0 = np.floor((lo - base) / bucket).astype(int)
    i1 = np.floor((hi - base) / bucket).astype(int)
    for a, z, vol in zip(i0, i1, v):
        acc[a:z + 1] += vol / (z - a + 1)
    return base + (np.arange(n) + 0.5) * bucket, acc


def value_area(price, acc, frac=VALUE_AREA):
    poc = int(acc.argmax())
    lo = hi = poc
    have, want = acc[poc], acc.sum() * frac
    while have < want and (lo > 0 or hi < len(acc) - 1):
        up = acc[hi + 1] if hi < len(acc) - 1 else -1
        dn = acc[lo - 1] if lo > 0 else -1
        if up >= dn:
            hi += 1; have += up
        else:
            lo -= 1; have += dn
    return price[poc], price[hi], price[lo]


def levels_of(prev, bucket):
    price, acc = profile(prev, bucket)
    poc, vah, val = value_area(price, acc)
    return sorted([poc, vah, val, float(prev.h.max()),
                   float(prev.l.min()), float(prev.c.iloc[-1])])


def signals(b: pd.DataFrame, k: int = PIVOT):
    """Every BOS and CHoCH in the session, with the swing that defines the stop.

    Trend state is carried forward from confirmed swings only. A pivot at bar i
    is not knowable until bar i+k, so the break scan at bar j only considers
    swings with bar + k <= j. Without that guard the test would be reading a
    high that had not finished forming.
    """
    H, L, C = b.h.to_numpy(), b.l.to_numpy(), b.c.to_numpy()
    n = len(b)
    piv = []                                  # (bar, price, is_high)
    for i in range(k, n - k):
        w = slice(i - k, i + k + 1)
        if H[i] == H[w].max():
            piv.append((i, H[i], True))
        if L[i] == L[w].min():
            piv.append((i, L[i], False))

    out = []
    trend = 0                                  # +1 up, -1 down, 0 unknown
    last_hi = last_lo = None                   # most recent confirmed swings
    prev_hi = prev_lo = None
    used_hi = used_lo = None                   # levels already broken
    pi = 0
    for j in range(n):
        while pi < len(piv) and piv[pi][0] + k <= j:
            bar, px, is_high = piv[pi]
            if is_high:
                prev_hi, last_hi = last_hi, (bar, px)
            else:
                prev_lo, last_lo = last_lo, (bar, px)
            # trend is set by the classic pair: higher high AND higher low
            if last_hi and prev_hi and last_lo and prev_lo:
                if last_hi[1] > prev_hi[1] and last_lo[1] > prev_lo[1]:
                    trend = 1
                elif last_hi[1] < prev_hi[1] and last_lo[1] < prev_lo[1]:
                    trend = -1
            pi += 1

        if last_hi and C[j] > last_hi[1] and used_hi != last_hi[0] and last_lo:
            used_hi = last_hi[0]
            out.append(dict(i=j, up=True, price=float(C[j]),
                            stop=float(last_lo[1]),
                            kind="BOS" if trend >= 0 else "CHoCH"))
        if last_lo and C[j] < last_lo[1] and used_lo != last_lo[0] and last_hi:
            used_lo = last_lo[0]
            out.append(dict(i=j, up=False, price=float(C[j]),
                            stop=float(last_hi[1]),
                            kind="BOS" if trend <= 0 else "CHoCH"))
    return out


def next_level(levels, px, up, min_gap):
    """The nearest reference price beyond the entry, in the trade's direction."""
    if up:
        ahead = [l for l in levels if l > px + min_gap]
        return min(ahead) if ahead else None
    ahead = [l for l in levels if l < px - min_gap]
    return max(ahead) if ahead else None


def walk(m1, t_from, entry, stop, target, up):
    """Outcome on 1-minute bars. A bar touching both is a loss, and flagged."""
    H, L, C = m1.h.to_numpy(), m1.l.to_numpy(), m1.c.to_numpy()
    T = m1.timestamp.to_numpy()
    start = int(np.searchsorted(T, t_from, side="right"))
    for j in range(start, len(m1)):
        if up:
            s, t = L[j] <= stop, H[j] >= target
        else:
            s, t = H[j] >= stop, L[j] <= target
        if s and t:
            return -abs(entry - stop), True
        if s:
            return -abs(entry - stop), False
        if t:
            return abs(target - entry), False
    return ((C[-1] - entry) if up else (entry - C[-1])), False


def run_tf(days, keys, minutes, kinds=("BOS", "CHoCH"), retest=False):
    rows = []
    for d0, d1 in zip(keys, keys[1:]):
        prev, m1 = days[d0], days[d1]
        px0 = float(m1.o.iloc[0])
        k = px0 / NQ_PRICE
        lv = levels_of(prev, BUCKET_NQ * k)
        b = resample(m1, minutes)
        if len(b) < 10:
            continue
        for s in signals(b):
            if s["kind"] not in kinds:
                continue
            entry, stop, up = s["price"], s["stop"], s["up"]
            risk = abs(entry - stop)
            if risk <= 0 or risk / entry > 0.02:
                continue
            tgt = next_level(lv, entry, up, 2.0 * k)
            if tgt is None:
                continue
            rr = abs(tgt - entry) / risk
            t_from = b.timestamp.iloc[s["i"]] if "timestamp" in b else None
            if t_from is None:
                continue
            pnl, amb = walk(m1, np.datetime64(t_from), entry, stop, tgt, up)
            rows.append(dict(day=d1, tf=minutes, kind=s["kind"],
                             nq=pnl / entry * NQ_PRICE - COST_NQ,
                             R=pnl / risk - COST_NQ / (risk / entry * NQ_PRICE),
                             rr=rr, amb=amb, up=up))
    return rows


def stat(rows, label):
    if len(rows) < 20:
        print(f"    {label:<34} n={len(rows):<6} too few")
        return None
    R = np.array([r["R"] for r in rows])
    nq = np.array([r["nq"] for r in rows])
    sd = R.std(ddof=1)
    t = R.mean() / (sd / np.sqrt(len(R))) if sd > 0 else 0.0
    print(f"    {label:<34} n={len(R):<6} {R.mean():+6.3f}R  "
          f"{nq.mean():+7.1f} NQ  win {100*(R > 0).mean():4.1f}%  "
          f"t={t:+5.2f}  R:R {np.median([r['rr'] for r in rows]):4.1f}  "
          f"amb {100*np.mean([r['amb'] for r in rows]):3.0f}%")
    return dict(n=len(R), R=R.mean(), t=t, nq=nq.mean())


def main():
    days = sessions()
    keys = sorted(days)
    print("=" * 104)
    print(f"GO WITH THE BREAK, TARGET THE NEXT LEVEL — {len(keys):,} sessions, "
          f"{keys[0]} to {keys[-1]}")
    print("=" * 104)
    print("  Signals on the stated timeframe; outcomes always simulated on")
    print("  1-minute bars. Stop at the opposing confirmed swing, target the")
    print("  next prior-session level in the way. Net of 2 NQ points.\n")

    print("1  WHICH TIMEFRAME?  (both event types together)")
    print("-" * 104)
    cache = {}
    for tf in TIMEFRAMES:
        rows = run_tf(days, keys, tf)
        cache[tf] = rows
        per = len(rows) / max(1, len(keys))
        stat(rows, f"{tf:>2} min   ({per:4.1f} signals a session)")

    print("\n2  BOS vs CHoCH — continuation or reversal?")
    print("-" * 104)
    for tf in TIMEFRAMES:
        rows = cache[tf]
        b = [r for r in rows if r["kind"] == "BOS"]
        c = [r for r in rows if r["kind"] == "CHoCH"]
        print(f"  --- {tf} min ---")
        stat(b, "  BOS (continuation)")
        stat(c, "  CHoCH (reversal)")

    print("\n3  DOES A BIGGER TARGET HELP?  best timeframe, split by R:R offered")
    print("-" * 104)
    best = max(TIMEFRAMES, key=lambda t: (stat_quiet(cache[t]) or -9))
    rows = cache[best]
    print(f"  best by mean R: {best} min\n")
    for lo, hi, lbl in ((0, 1, "under 1R away"), (1, 2, "1 to 2R"),
                        (2, 4, "2 to 4R"), (4, 99, "over 4R")):
        sel = [r for r in rows if lo <= r["rr"] < hi]
        stat(sel, f"next level {lbl}")

    print("\n4  BY YEAR — best timeframe, both events")
    print("-" * 104)
    df = pd.DataFrame(rows)
    df["year"] = pd.to_datetime(df.day).dt.year
    for y in sorted(df.year.unique()):
        stat(df[df.year == y].to_dict("records"), f"{y}")

    print("\n5  THE R:R FILTER, SWEPT — the thread worth pulling")
    print("-" * 104)
    print("  The losses sit where the next level is CLOSER than the stop:")
    print("  those setups win 64.5% and still lose money, which is what a")
    print("  sub-1R target does to you. The reward-to-risk on offer is known")
    print("  at the entry bar, so refusing the bad ones is implementable.")
    print("  A bucket that looks good can be luck, so this sweeps a threshold")
    print("  and asks whether the improvement is a plateau or a spike.\n")
    for tf in (5, 15, 30):
        print(f"  --- {tf} min ---")
        rws = cache[tf]
        for x in (0.0, 1.0, 1.5, 2.0, 2.5, 3.0):
            sel = [r for r in rws if r["rr"] >= x]
            stat(sel, f"  next level at least {x:.1f}R away")
        print()

    print("  Pooled across 5, 15 and 30 minute signals, R:R >= 2 only:")
    pool = [r for tf in (5, 15, 30) for r in cache[tf] if r["rr"] >= 2.0]
    stat(pool, "  all years")
    pdf = pd.DataFrame(pool)
    pdf["year"] = pd.to_datetime(pdf.day).dt.year
    for y in sorted(pdf.year.unique()):
        stat(pdf[pdf.year == y].to_dict("records"), f"    {y}")
    print("\n  Same pool, de-overlapped to one trade a session:")
    first = pdf.sort_values("day").groupby("day").head(1)
    stat(first.to_dict("records"), "  first qualifying signal only")


def stat_quiet(rows):
    if len(rows) < 20:
        return None
    return float(np.mean([r["R"] for r in rows]))


if __name__ == "__main__":
    main()
