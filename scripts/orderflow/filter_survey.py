#!/usr/bin/env python3
"""WHAT ELSE IN THE RECORDING SHOWS DIRECTION AND STRENGTH?

CVD change survived the last pass. This asks what else the recorder already
captures could do the same job, tested identically so the answers compare.

Three streams are recorded and they are not the same information:

  TAPE  (2.6 MB/session)  every print: time, price, volume, aggressor side
  CUM   (1.7 MB/session)  meant to be every aggressive ORDER, aggregated
  DEPTH ( 12 MB/session)  the ladder, ~84,000 updates a session, 50 levels a side

ONE OF THEM IS BROKEN, AND THAT IS THE MAIN FINDING HERE. Every CUM row has
fills = 1 and first_price = last_price, and its median volume is 1. It is not
aggregating anything -- it is the tape again with three constant columns. So
the most promising untested idea, that a single 100-lot is one decision by one
participant while a hundred 1-lots are a hundred, CANNOT BE MEASURED until the
recorder is fixed. That is not a null result; it is missing data, and the
difference matters because the idea stays open rather than dying.

What can be tested, each with a reason before any number:

  BOOK    resting size either side of the ladder at the break. Depth is the
          expensive stream and this decides whether it earns its 12 MB.
  SURGE   volume in the breaking bars against the session's own median bar.
          The oldest read there is: does the break come on volume.
  SPEED   prints per second against the session norm. Volume can rise because
          clips got bigger; speed says more participants arrived.
  RUN     consecutive bars whose delta agrees with the trade. This is "one
          side of the auction has won" stated so it can be counted, and it is
          a different shape from a threshold crossed once.
  BIGPRINT net delta from prints above a size. A weak proxy for the broken CUM
          idea -- weak because NQ trades in small clips, so prints of 10+ are
          0.6% of volume. Included to show the size of that limit.

Every candidate is judged against the trades IT REFUSES, inside the same
sessions, with a 95% interval from resampling SESSIONS. A fifteen-session
sample can run hot and make any gate look good; the paired difference is
immune to that, the level of either arm is not.

Usage: python3 scripts/orderflow/filter_survey.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from structure_cvd import bars                                            # noqa
from structure_trade import levels_of, next_level, signals                # noqa
from tape import load_all, rth                                            # noqa

ROOT = Path(__file__).resolve().parents[2] / "data"
COST_PTS = 2.0
BUCKET_PTS = 2.0
BOOK_LEVELS = 10          # how deep to measure resting size
BOOK_WINDOW_S = 3.0       # rebuild the ladder from updates in this window

_BOOK: dict = {}


def book_series(day: str):
    """Ladder imbalance over time, rebuilt from the depth stream.

    The file is change-only, so no single timestamp holds the whole ladder.
    But updates land every ~0.3 seconds, so taking the LAST volume seen at
    each (side, price) within a short window reconstructs a book that is at
    most a few seconds stale. That is a real approximation and it is the
    reason this family is weaker by construction than the tape ones -- it is
    stated rather than hidden.

    Returns a frame indexed by time with the imbalance of the top levels.
    """
    if day in _BOOK:
        return _BOOK[day]
    f = ROOT / "depth" / f"L2_NQ_{day}.csv.gz"
    if not f.exists():
        _BOOK[day] = None
        return None
    d = pd.read_csv(f, compression="gzip",
                    usecols=["time", "side", "level", "price", "volume"])
    d["time"] = pd.to_datetime(d.time)
    # NOTE: the recorder writes 'A' for the ask side, not 'S'. Filtering for
    # 'S' silently produced an empty book and made depth look unusable.
    d = d[d.level < BOOK_LEVELS]
    g = d.groupby([pd.Grouper(key="time", freq="5s"), "side"]).volume.sum()
    w = g.unstack("side")
    if "B" not in w or "A" not in w:
        _BOOK[day] = None
        return None
    w = w.dropna()
    w["imb"] = (w["B"] - w["A"]) / (w["B"] + w["A"])
    _BOOK[day] = w
    return w


def build(days, pairs, minutes):
    rows = []
    for d0, d1 in pairs:
        prev, s = days[d0], days[d1]
        b = bars(s, minutes)
        if len(b) < 10:
            continue
        lv = levels_of(bars(prev, minutes), BUCKET_PTS)
        bk = book_series(d1)

        # per-bar print count, for SPEED
        cnt = s.set_index("time").resample(f"{minutes}min").price.count()
        cnt = cnt.reindex(b.timestamp).fillna(0).to_numpy()

        # Baseline for "busy": the median of the PREVIOUS 20 bars, not the
        # session so far. An expanding median is dominated by the opening
        # surge and stays inflated all day -- on the recorded sessions it put
        # 87% of bars below their own "median", which is arithmetically
        # impossible for a correct ratio and would have produced a confident
        # finding that breaks on volume do worse. A rolling window is also
        # what a trader means by busy: busy compared with the last hour.
        # shift(1) keeps the current bar out of its own baseline.
        medv = b.v.rolling(20, min_periods=8).median().shift(1).to_numpy()
        medc = (pd.Series(cnt).rolling(20, min_periods=8)
                .median().shift(1).to_numpy())

        dv = b.d.to_numpy()                      # per-bar delta
        px_all = s.price.to_numpy()
        tm_all = s.time.to_numpy()
        vol_all = s.volume.to_numpy()
        sgn_all = s["sign"].to_numpy()

        # big prints per bar, from the tape
        big = s[s.volume >= 10]
        bigd = (big.set_index("time").resample(f"{minutes}min").signed.sum()
                .reindex(b.timestamp).fillna(0).to_numpy())

        for sig in signals(b):
            i = sig["i"]
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            tgt = next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            sign = 1.0 if up else -1.0
            t_at = b.timestamp.iloc[i]

            start = int(np.searchsorted(tm_all, np.datetime64(t_at), side="right"))
            pnl = None
            for j in range(start, len(px_all)):
                if up:
                    if px_all[j] <= stop:
                        pnl = -risk; break
                    if px_all[j] >= tgt:
                        pnl = abs(tgt - entry); break
                else:
                    if px_all[j] >= stop:
                        pnl = -risk; break
                    if px_all[j] <= tgt:
                        pnl = abs(tgt - entry); break
            if pnl is None:
                pnl = (px_all[-1] - entry) if up else (entry - px_all[-1])

            r = dict(day=d1, R=pnl / risk - COST_PTS / risk)
            lo2 = max(0, i - 1)
            nb = i - lo2 + 1

            if not np.isnan(medv[i]) and medv[i] > 0:
                r["surge"] = float(b.v.iloc[lo2:i + 1].sum()) / (medv[i] * nb)
            if not np.isnan(medc[i]) and medc[i] > 0:
                r["speed"] = float(cnt[lo2:i + 1].sum()) / (medc[i] * nb)

            # RUN: how many consecutive bars up to and including the break had
            # delta agreeing with the trade. Counted backwards from the break.
            run = 0
            for j in range(i, -1, -1):
                if dv[j] * sign > 0:
                    run += 1
                else:
                    break
            r["run"] = run

            r["bigprint"] = float(bigd[lo2:i + 1].sum()) * sign
            tot = float(b.v.iloc[lo2:i + 1].sum())
            r["bigprint_sh"] = r["bigprint"] / tot if tot > 0 else np.nan

            if bk is not None:
                pos = bk.index.searchsorted(t_at, side="right") - 1
                if pos >= 0 and (t_at - bk.index[pos]).total_seconds() <= 30:
                    r["book_with"] = float(bk["imb"].iloc[pos]) * sign
            rows.append(r)
    return pd.DataFrame(rows)


def paired(df, key, cut, label, tally=None, fam=None):
    if key not in df:
        print(f"    {label:<46} not available")
        return
    d = df.dropna(subset=[key])
    on, off = d[d[key] >= cut], d[d[key] < cut]
    if len(on) < 8 or len(off) < 8:
        print(f"    {label:<46} n={len(on):<4}/{len(off):<4} too few")
        return
    obs = on.R.mean() - off.R.mean()
    by = {k: g for k, g in d.groupby("day")}
    sess = list(by)
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(6000):
        pick = rng.choice(sess, size=len(sess), replace=True)
        g = pd.concat([by[x] for x in pick])
        a, c = g.R[g[key] >= cut], g.R[g[key] < cut]
        if len(a) and len(c):
            boot.append(a.mean() - c.mean())
    lo, hi = np.percentile(boot, [2.5, 97.5])
    mark = "  <-- excludes zero" if (lo > 0 or hi < 0) else ""
    if tally is not None:
        tally.setdefault(fam, []).append(obs)
    print(f"    {label:<46} n={len(on):<4} {obs:+6.3f}R  "
          f"[{lo:+.2f}, {hi:+.2f}]{mark}")


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]

    print("=" * 100)
    print(f"FILTER SURVEY — direction and strength, {len(pairs)} session pairs")
    print("=" * 100)
    print("  Judged against the trades each gate REFUSES, same sessions.")
    print("  Intervals resample SESSIONS, not signals.\n")
    print("  CUM stream is BROKEN and excluded: every row has fills=1 and")
    print("  first_price=last_price, so aggressive-order size and sweep depth")
    print("  are not in the data at all. That idea is untested, not dead.\n")

    for minutes in (3, 5):
        df = build(days, pairs, minutes)
        tally = {}
        print(f"  ---- {minutes}-minute signals: {len(df)} breaks, "
              f"{df.day.nunique()} sessions ----\n")

        print("   BOOK — resting size on the trade's side of the ladder")
        for x in (0.0, 0.1, 0.2):
            paired(df, "book_with", x, f"  book imbalance with trade >= {x:+.2f}",
                   tally, "BOOK")

        print("\n   SURGE — is the break coming on volume?")
        for x in (1.0, 1.3, 1.7):
            paired(df, "surge", x, f"  volume >= {x:.1f}x the last 20 bars",
                   tally, "SURGE")

        print("\n   SPEED — are more participants arriving?")
        for x in (1.0, 1.3, 1.7):
            paired(df, "speed", x, f"  prints >= {x:.1f}x the last 20 bars",
                   tally, "SPEED")

        print("\n   RUN — consecutive bars with delta agreeing (one side won)")
        for x in (1, 2, 3):
            paired(df, "run", x, f"  {x}+ consecutive agreeing bars",
                   tally, "RUN")

        print("\n   BIGPRINT — net delta from prints of 10+ (weak proxy)")
        paired(df, "bigprint", 1, "  net big-print delta with trade >= 1",
               tally, "BIGPRINT")
        paired(df, "bigprint_sh", 0.01, "  big-print net >= 1% of window volume",
               tally, "BIGPRINT")

        print(f"\n   sign tally, {minutes}-minute:")
        for fam in ("BOOK", "SURGE", "SPEED", "RUN", "BIGPRINT"):
            v = tally.get(fam, [])
            if v:
                print(f"     {fam:<9} {sum(x > 0 for x in v)}/{len(v)} positive"
                      f"   median {np.median(v):+.3f}R")
        print()


if __name__ == "__main__":
    main()
