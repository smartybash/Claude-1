#!/usr/bin/env python3
"""Audit the recorded Level 2 depth before any strategy is built on it.

The question this answers is not "did files arrive" but "does this data support
the measurement we want to make". The intended measurement is resting size at a
fixed price level in the seconds before price arrives there, and whether that
size is pulled or replenished. That needs four things to be true, and each one
is checked here rather than assumed:

  1  the book is not crossed and not stale -- a best bid above the best ask, or
     a ladder that stops updating, means the snapshot logic is wrong
  2  the recording covers the whole cash session without holes
  3  the ladder is deep enough to see a level BEFORE price reaches it. Ten
     levels at a 0.25 tick is 2.5 points of visibility, which may be far too
     little notice to be useful, and this is the one that decides whether the
     twenty-session run is worth doing as configured
  4  nothing is duplicated

Usage: python3 scripts/depth_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DEPTH = ROOT / "data" / "depth"

TICK = 0.25


sys.path.insert(0, str(Path(__file__).resolve().parent))
from tape import read_maybe_truncated                      # noqa: E402


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(read_maybe_truncated(path), encoding="utf-8-sig",
                     dtype={"side": "string", "level": np.int32,
                            "price": np.float64, "volume": np.float64})
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    return df


def load_clean(path: Path) -> pd.DataFrame:
    """Deduplicated. One recorded day arrived with every row present exactly
    twice, which would double every resting size if left alone."""
    df = load(path)
    return df.drop_duplicates(subset=["time", "side", "price"], keep="first")


def touch_series(df: pd.DataFrame) -> pd.DataFrame:
    """Best bid and best ask at every snapshot, by rebuilding the ladder.

    The obvious shortcut -- take the rows where level == 0 -- is wrong for the
    change-only format, and wrong in a way that looks like a data defect. A row
    is written only when that PRICE's resting size changes, so a price that was
    level 0 stays marked level 0 in the file while price moves away from it and
    it becomes level 3. Reading those rows and forward-filling pairs a stale bid
    against a fresh ask and reports crossed books that never happened: 2.4% of
    one session, against 0.0000% once rebuilt properly.
    """
    t = df.time.to_numpy()
    side = df.side.to_numpy()
    price = df.price.to_numpy(dtype=np.float64)
    vol = df.volume.to_numpy(dtype=np.float64)

    bids, asks = {}, {}
    stamps, bb, aa = [], [], []
    i, n = 0, len(df)
    while i < n:
        j = i
        while j < n and t[j] == t[i]:
            j += 1
        for k in range(i, j):
            book = bids if side[k] == "B" else asks
            if vol[k] <= 0:
                book.pop(price[k], None)
            else:
                book[price[k]] = vol[k]
        if bids and asks:
            stamps.append(t[i])
            bb.append(max(bids))
            aa.append(min(asks))
        i = j
    return pd.DataFrame({"bid": bb, "ask": aa}, index=pd.DatetimeIndex(stamps))


def main():
    files = sorted(DEPTH.glob("L2_*.csv*"))
    print("=" * 86)
    print("DEPTH AUDIT")
    print("=" * 86)

    for p in files:
        df = load(p)
        day = p.name.split("_")[-1].split(".")[0]
        n = len(df)
        stamps = df.time.nunique()
        span = df.time.max() - df.time.min()

        print(f"\n  ── {day} " + "─" * 66)
        print(f"     {n:>10,} rows   {stamps:>9,} snapshots   "
              f"{df.time.min().time()} to {df.time.max().time()}")

        # ---- duplication ------------------------------------------------
        dup = df.duplicated().sum()
        exact = df.duplicated(subset=["time", "side", "price"]).sum()
        print(f"     duplicate rows {dup:,}   "
              f"same time+side+price twice {exact:,}")

        # ---- format ------------------------------------------------------
        removals = int((df.level == -1).sum())
        lv = df[df.level >= 0]
        print(f"     removal rows (level -1) {removals:,}"
              f"   {'change-only format' if removals else 'FULL LADDER every snapshot'}")

        # ---- tick grid ---------------------------------------------------
        off = int((np.abs(np.round(df.price / TICK) - df.price / TICK) > 1e-6).sum())
        print(f"     off-tick prices {off}   "
              f"distinct prices {df.price.nunique():,}")

        # ---- ladder depth --------------------------------------------------
        print(f"     deepest level index  bid "
              f"{int(lv.loc[lv.side == 'B', 'level'].max())}"
              f"   ask {int(lv.loc[lv.side == 'A', 'level'].max())}")

        # ---- the touch -----------------------------------------------------
        t = touch_series(df)
        spread = (t.ask - t.bid) / TICK
        crossed = int((t.ask <= t.bid).sum())
        print(f"     spread in ticks  median {spread.median():.0f}   "
              f"p95 {spread.quantile(.95):.0f}   "
              f"crossed/locked books {crossed:,} "
              f"({100*crossed/len(t):.2f}%)")

        # ---- visibility window ---------------------------------------------
        # How far from the touch does the ladder reach? That distance is how
        # much warning we get before price arrives at a level.
        g = lv.groupby(["time", "side"]).price.agg(["min", "max"])
        spans = (g["max"] - g["min"])
        depth_pts = spans.to_numpy()
        if len(depth_pts):
            print(f"     ladder reach from touch  median "
                  f"{np.median(depth_pts):.2f} pts   "
                  f"max {depth_pts.max():.2f} pts")

        # ---- continuity ------------------------------------------------------
        u = pd.Series(sorted(df.time.unique()))
        gaps = u.diff().dt.total_seconds().dropna()
        big = gaps[gaps > 5]
        print(f"     snapshot interval  median {1000*gaps.median():.0f} ms   "
              f"p99 {1000*gaps.quantile(.99):.0f} ms")
        print(f"     gaps over 5s: {len(big)}"
              + (f"   worst {big.max():.0f}s" if len(big) else ""))
        covered = (u.iloc[-1] - u.iloc[0]).total_seconds()
        print(f"     covers {covered/3600:.2f}h of the 6.50h cash session"
              f"   ({100*covered/23400:.0f}%)")


if __name__ == "__main__":
    main()
