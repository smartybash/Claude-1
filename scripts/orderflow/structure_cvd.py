"""CVD IN THE TRADE'S DIRECTION, THEN A BREAK — does the gate help?

The proposal, in full: wait until one side of the auction has clearly won --
cumulative delta running hard one way -- and only then take a break of
structure in that same direction, targeting the next level of confluence.

The structure half was settled at size in structure_trade.py: 1,420 sessions,
every timeframe. It is flat at best and only after refusing the setups whose
target is nearer than their stop. So the question here is precise: does
requiring flow to agree turn a flat trade into a positive one?

Only the recorded tape can answer it. cvd_proxy.py showed that CVD rebuilt
from bars correlates 0.33 with the truth and points the WRONG WAY on four of
eighteen sessions, so the 1,420-session bar set is useless for this and the
sample here is 18 sessions. That is not enough to conclude with, and the
output says so in the places where it matters.

Two forms of the threshold, because raw contracts are not comparable across a
session -- the same +1,000 means one thing twenty minutes in and another six
hours in:

    contracts   net delta since the open, as the platform shows it
    share       the same number over the session's volume so far

Usage: python3 scripts/orderflow/structure_cvd.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from structure_trade import levels_of, next_level, signals                # noqa
from tape import load_all, prefix_sums, rth                               # noqa

POINT_USD = 20.0
COST_PTS = 2.0
BUCKET_PTS = 2.0


def bars(s: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """OHLCV plus true cumulative delta at the CLOSE of each bar.

    The CVD attached to a bar is the value as of that bar's close, which is
    the only value a live rule could have acted on when the bar completed.
    """
    g = s.set_index("time").resample(f"{minutes}min")
    b = g.agg(o=("price", "first"), h=("price", "max"), l=("price", "min"),
              c=("price", "last"), v=("volume", "sum"),
              d=("signed", "sum")).dropna(subset=["c"])
    b["cvd"] = b.d.cumsum()
    b["cum_v"] = b.v.cumsum()
    b["share"] = np.where(b.cum_v > 0, b.cvd / b.cum_v, 0.0)
    return b.reset_index().rename(columns={"time": "timestamp"})


def walk(s, t_from, entry, stop, target, up):
    """Outcome on the raw tape -- every trade, so fills are exact."""
    px = s.price.to_numpy()
    tm = s.time.to_numpy()
    start = int(np.searchsorted(tm, t_from, side="right"))
    for i in range(start, len(px)):
        if up:
            if px[i] <= stop:
                return -abs(entry - stop)
            if px[i] >= target:
                return abs(target - entry)
        else:
            if px[i] >= stop:
                return -abs(entry - stop)
            if px[i] <= target:
                return abs(target - entry)
    return (px[-1] - entry) if up else (entry - px[-1])


def st(rows, label, minn=10):
    if len(rows) < minn:
        print(f"    {label:<40} n={len(rows):<5} too few")
        return None
    R = np.array([r["R"] for r in rows])
    p = np.array([r["pts"] for r in rows])
    sd = R.std(ddof=1)
    t = R.mean() / (sd / np.sqrt(len(R))) if sd > 0 else 0.0
    print(f"    {label:<40} n={len(R):<5} {R.mean():+6.3f}R  "
          f"{p.mean():+7.1f}pt  win {100*(R > 0).mean():4.1f}%  t={t:+5.2f}")
    return dict(n=len(R), R=R.mean(), t=t)


def collect(days, pairs, minutes, min_rr):
    out = []
    for d0, d1 in pairs:
        prev, s = days[d0], days[d1]
        pb = bars(prev, minutes)
        lv = levels_of(pb, BUCKET_PTS)
        b = bars(s, minutes)
        if len(b) < 10:
            continue
        for sig in signals(b):
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            tgt = next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            rr = abs(tgt - entry) / risk
            if rr < min_rr:
                continue
            i = sig["i"]
            pnl = walk(s, np.datetime64(b.timestamp.iloc[i]),
                       entry, stop, tgt, up)
            sign = 1.0 if up else -1.0
            out.append(dict(
                day=d1, kind=sig["kind"], rr=rr,
                pts=pnl - COST_PTS, R=pnl / risk - COST_PTS / risk,
                # flow AS OF the breaking bar's close, signed so positive
                # means it agrees with the trade
                cvd_with=float(b.cvd.iloc[i]) * sign,
                share_with=float(b.share.iloc[i]) * sign))
    return out


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]

    print("=" * 96)
    print(f"CVD GATE ON THE STRUCTURE BREAK — {len(days)} recorded sessions, "
          f"{len(pairs)} pairs")
    print("=" * 96)
    print("  Real signed volume. Eighteen sessions is the whole of the")
    print("  available evidence, so treat every number here as a direction.\n")

    for minutes in (3, 5):
        # min_rr is 0 here on purpose. The R:R >= 2 filter that mattered at
        # scale leaves 14 signals across these 15 sessions -- not enough to
        # split on anything. Testing the flow gate needs the signals back, and
        # the cost is that this is NOT the filtered trade from
        # structure_trade.py, it is every break.
        rows = collect(days, pairs, minutes, min_rr=0.0)
        print(f"  ---- {minutes}-minute signals, every break ----")
        st(rows, "every break, no flow gate")
        if len(rows) < 12:
            print("    too few signals at this timeframe to split\n")
            continue

        print("\n    gate on CONTRACTS of delta in the trade's direction:")
        for x in (0, 1000, 2000, 4000):
            st([r for r in rows if r["cvd_with"] >= x],
               f"      delta with the trade >= {x:,}")

        print("\n    gate on delta as a SHARE of session volume:")
        for x in (0.0, 0.005, 0.01, 0.02):
            st([r for r in rows if r["share_with"] >= x],
               f"      share with the trade >= {100*x:.1f}%")

        print("\n    and the trades the gate would have refused:")
        st([r for r in rows if r["cvd_with"] < 1000],
           "      delta under +1,000 with the trade")
        print()

    # The headline comparison, at the user's own number.
    rows = collect(days, pairs, 5, min_rr=0.0)
    a = [r for r in rows if r["cvd_with"] >= 1000]
    b = [r for r in rows if r["cvd_with"] < 1000]
    print("=" * 96)
    print("IS THE GATE DOING ANYTHING, OR IS IT THE SAMPLE?")
    print("=" * 96)
    if len(a) < 8 or len(b) < 8:
        print("  Not enough signals on both sides to test.")
        return
    obs = np.mean([r["R"] for r in a]) - np.mean([r["R"] for r in b])

    # Bootstrap over SESSIONS, not signals. Signals inside one session share
    # that session's move, so resampling them individually would treat one
    # good day as many independent wins -- the exact inflation that turned a
    # t of +5.12 into +1.00 earlier in this project. Resampling whole days
    # keeps that dependence intact.
    df = pd.DataFrame(rows)
    df["hit"] = df.cvd_with >= 1000
    sess = df.day.unique()
    by_day = {d: g for d, g in df.groupby("day")}
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(20_000):
        pick = rng.choice(sess, size=len(sess), replace=True)
        g = pd.concat([by_day[d] for d in pick])
        on, off = g.R[g.hit], g.R[~g.hit]
        if len(on) == 0 or len(off) == 0:
            continue
        diffs.append(on.mean() - off.mean())
    diffs = np.array(diffs)
    lo, hi = np.percentile(diffs, [2.5, 97.5])

    print(f"  gate on:  n={len(a):<4} {np.mean([r['R'] for r in a]):+.3f}R")
    print(f"  gate off: n={len(b):<4} {np.mean([r['R'] for r in b]):+.3f}R")
    print(f"  difference {obs:+.3f}R")
    print(f"  95% interval by session bootstrap: {lo:+.3f}R to {hi:+.3f}R")
    print(f"  {'EXCLUDES' if lo > 0 or hi < 0 else 'INCLUDES'} zero"
          f"   ({df.day.nunique()} sessions, {len(df)} signals)")
    print()
    print("  The interval is what matters, not the point estimate. With this")
    print("  many sessions it will be wide whatever the answer is, and a wide")
    print("  interval straddling zero means the gate has not been shown to do")
    print("  anything -- not that it does nothing.")
    print("=" * 96)


if __name__ == "__main__":
    main()
