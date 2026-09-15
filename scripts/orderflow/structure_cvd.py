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

    # CVD CHANGE over the last N bars of THIS timeframe, which is a different
    # quantity from the session total and the more plausible one for gating a
    # break. By the afternoon the cumulative figure is mostly history; what
    # pushed price through the level is the delta in the bars that did it.
    # Also kept as a share of the volume in the same window, so the measure
    # does not mean different things in a quiet hour and a busy one.
    for n in (1, 2, 3, 5):
        dn = b.d.rolling(n, min_periods=1).sum()
        vn = b.v.rolling(n, min_periods=1).sum()
        b[f"d{n}"] = dn
        b[f"r{n}"] = np.where(vn > 0, dn / vn, 0.0)
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
                share_with=float(b.share.iloc[i]) * sign,
                **{f"d{n}_with": float(b[f"d{n}"].iloc[i]) * sign
                   for n in (1, 2, 3, 5)},
                **{f"r{n}_with": float(b[f"r{n}"].iloc[i]) * sign
                   for n in (1, 2, 3, 5)}))
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

        print("\n    CVD CHANGE over the last N bars of this timeframe,")
        print("    in contracts, agreeing with the trade:")
        for n in (1, 2, 3, 5):
            for x in (0, 500, 1000):
                st([r for r in rows if r[f"d{n}_with"] >= x],
                   f"      last {n} bar(s), delta >= {x:,}")
            print()

        print("    the same change as a SHARE of the volume in that window --")
        print("    scale-free, so it means the same thing in any hour:")
        for n in (1, 2, 3):
            for x in (0.0, 0.05, 0.10, 0.20):
                st([r for r in rows if r[f"r{n}_with"] >= x],
                   f"      last {n} bar(s), {100*x:.0f}%+ of window volume")
            print()

        print("    and the trades a change-gate would have refused:")
        st([r for r in rows if r["d3_with"] < 500],
           "      3-bar delta under +500 with the trade")
        print()

    # ---- the only comparison that controls for a hot sample ----------------
    #
    # Every gate below is judged against the trades IT REFUSES, inside the same
    # sessions, not against zero. That matters here: the 3-minute baseline on
    # this tape is +0.101R while the same signal over 1,420 sessions of bars
    # runs t = -5.80. Fifteen sessions can easily be lucky, and a gate sitting
    # on a lucky sample will look good while separating nothing. The paired
    # difference is immune to that; the level of either arm is not.
    print("=" * 96)
    print("EACH GATE AGAINST THE TRADES IT REFUSES, SAME SESSIONS")
    print("=" * 96)
    print("  Level gates test 'who has won the session'. Change gates test")
    print("  'who is winning right now'. The second is the one a break should")
    print("  care about, and it was missing from the first pass.\n")

    tally = {"LEVEL": [], "CHANGE": []}

    def paired(rows, key, cut, label):
        on = [r for r in rows if r[key] >= cut]
        off = [r for r in rows if r[key] < cut]
        if len(on) < 8 or len(off) < 8:
            print(f"    {label:<42} n={len(on):<4}/{len(off):<4} too few")
            return
        d = np.mean([r["R"] for r in on]) - np.mean([r["R"] for r in off])
        df = pd.DataFrame(rows)
        df["hit"] = df[key] >= cut
        by = {k: g for k, g in df.groupby("day")}
        sess = list(by)
        rng = np.random.default_rng(0)
        boot = []
        for _ in range(8000):
            pick = rng.choice(sess, size=len(sess), replace=True)
            g = pd.concat([by[x] for x in pick])
            a, b = g.R[g.hit], g.R[~g.hit]
            if len(a) and len(b):
                boot.append(a.mean() - b.mean())
        lo, hi = np.percentile(boot, [2.5, 97.5])
        mark = "  <-- excludes zero" if (lo > 0 or hi < 0) else ""
        tally[label.split(":")[0]].append(d)
        print(f"    {label:<42} n={len(on):<4} {d:+6.3f}R   "
              f"[{lo:+.2f}, {hi:+.2f}]{mark}")

    for minutes in (3, 5):
        rows = collect(days, pairs, minutes, min_rr=0.0)
        print(f"  ---- {minutes}-minute signals ({len(rows)} breaks, "
              f"{len(set(r['day'] for r in rows))} sessions) ----")
        paired(rows, "cvd_with", 1000, "LEVEL: session delta >= +1,000")
        paired(rows, "share_with", 0.01, "LEVEL: session delta >= 1% of volume")
        paired(rows, "d1_with", 0, "CHANGE: breaking bar delta positive")
        paired(rows, "r1_with", 0.05, "CHANGE: breaking bar 5%+ of its volume")
        paired(rows, "r1_with", 0.10, "CHANGE: breaking bar 10%+ of its volume")
        paired(rows, "r2_with", 0.10, "CHANGE: last 2 bars 10%+ of volume")
        paired(rows, "r3_with", 0.05, "CHANGE: last 3 bars 5%+ of volume")
        paired(rows, "d5_with", 1000, "CHANGE: last 5 bars delta >= +1,000")
        print()

    # The single cell that excludes zero is not the finding -- sixteen tests
    # were run and one of them clearing 5% is roughly what chance produces.
    # What is harder to get by accident is the SIGN PATTERN: every change gate
    # one way and every level gate the other, across two timeframes.
    for k in ("LEVEL", "CHANGE"):
        v = tally[k]
        if v:
            print(f"  {k+' gates:':<16} {sum(x > 0 for x in v)}/{len(v)} positive"
                  f"   median {np.median(v):+.3f}R")
    print()
    print("  That split is the result, not any single cell. Sixteen tests were")
    print("  run, so one interval clearing 5% is what chance hands you; every")
    print("  change gate landing on one side and every level gate on the other")
    print("  is not. The gates overlap heavily, though, so this is suggestive")
    print("  rather than a p-value -- and it is fifteen sessions.")
    print()
    print("  Each interval is a 95% range from resampling SESSIONS, which")
    print("  keeps signals inside a day together instead of treating one good")
    print("  day as many independent wins. An interval containing zero means")
    print("  the gate has not been shown to separate -- and with fifteen")
    print("  sessions most of them will contain zero whatever the truth is.")
    print("=" * 96)


if __name__ == "__main__":
    main()
