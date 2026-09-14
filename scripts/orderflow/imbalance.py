#!/usr/bin/env python3
"""ORDER BOOK IMBALANCE — the first test the depth recording makes possible.

Nothing in this project has been able to ask this before. Bars cannot see
resting size, and the earlier recording was ruined by a 5-point price grid.
Four clean sessions at a 0.25 tick now exist, so the question is finally
answerable: does the size resting on each side of the book predict where price
goes next?

The measure is the standard one, computed at every snapshot:

    imbalance = (bid size - ask size) / (bid size + ask size)

over the ten levels the feed provides, running from -1 (all the size is on the
offer) to +1 (all of it is on the bid). Naively, size on the bid should support
price. The opposite is also arguable: visible size is the size that wants to be
seen, and the real seller does not advertise.

Every guard that killed the earlier findings is applied from the start:

  * entry at the close of a window, on information available at that instant
  * mid price, so the spread cannot manufacture a result
  * one trade per signal episode -- overlapping holds inflated a t of +1.00
    to +5.12 last time and that must not happen twice
  * four separate days reported individually; pooling two days hid a sign flip
  * a control of every window, and a dose-response across deciles, because a
    real mechanism should scale with the dose rather than appear in one cell
  * costs charged at 2 points round trip

Usage: python3 scripts/imbalance.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DEPTH = ROOT / "data" / "depth"

TICK = 0.25
POINT_USD = 20.0
COST_PTS = 2.0
BAR_T = 3.0


def snapshots(path: Path) -> pd.DataFrame:
    """One row per book snapshot: touch prices and resting size per side."""
    df = pd.read_csv(path, encoding="utf-8-sig",
                     dtype={"side": "string", "level": np.int32,
                            "price": np.float64, "volume": np.float64})
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    # 09-01 was recorded twice into the same file; without this every resting
    # size on that day doubles.
    df = df.drop_duplicates(subset=["time", "side", "price"], keep="first")
    df = df[df.level >= 0]

    size = df.pivot_table(index="time", columns="side", values="volume",
                          aggfunc="sum")
    touch = df[df.level == 0].pivot_table(index="time", columns="side",
                                          values="price", aggfunc="first")
    s = pd.DataFrame({
        "bid_sz": size.get("B"), "ask_sz": size.get("A"),
        "bid": touch.get("B"), "ask": touch.get("A"),
    }).dropna()
    s = s[s.ask > s.bid]
    s["mid"] = (s.bid + s.ask) / 2.0
    s["imb"] = (s.bid_sz - s.ask_sz) / (s.bid_sz + s.ask_sz)
    return s


def windows(s: pd.DataFrame, secs: int) -> pd.DataFrame:
    g = s.resample(f"{secs}s")
    w = pd.DataFrame({
        "imb": g.imb.mean(),          # mean over the window, not a single tick
        "mid": g.mid.last(),
        "bid_sz": g.bid_sz.mean(),
        "ask_sz": g.ask_sz.mean(),
        "n": g.mid.count(),
    })
    return w[w.n > 0].dropna()


def stat(x, cost=0.0):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 25:
        return None
    x = x - cost
    sd = x.std(ddof=1)
    return dict(n=len(x), mean=x.mean(), win=100 * (x > 0).mean(),
                t=x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0)


def show(lbl, r, mark=True):
    if r is None:
        print(f"  {lbl:<40} too few")
        return
    star = " **" if (mark and abs(r["t"]) >= BAR_T) else ""
    print(f"  {lbl:<40} n={r['n']:<6} {r['mean']:+6.3f}pt "
          f"{r['mean']*POINT_USD:+7.1f}$  win {r['win']:3.0f}%  "
          f"t={r['t']:+6.2f}{star}")


def deoverlap(w, sel, k):
    """Signal rows with no re-entry until a hold has expired."""
    idx, block = [], -1
    hits = np.flatnonzero(sel.to_numpy())
    for i in hits:
        if i < block or i + k >= len(w):
            continue
        idx.append(i)
        block = i + k
    return np.array(idx, dtype=int)


def main():
    files = sorted(DEPTH.glob("L2_*.csv*"))
    S = {}
    for p in files:
        day = p.name.split("_")[-1].split(".")[0]
        S[day] = snapshots(p)

    print("=" * 88)
    print("ORDER BOOK IMBALANCE")
    print(f"{len(S)} sessions   ten levels per side   cost {COST_PTS} pts   "
          f"bar |t| >= {BAR_T}")
    print("=" * 88)
    for d, s in S.items():
        print(f"  {d}  {len(s):,} snapshots   "
              f"resting size per side: bid {s.bid_sz.median():.0f} "
              f"ask {s.ask_sz.median():.0f} (median)   "
              f"imbalance sd {s.imb.std():.3f}")

    SECS = 10
    W = {d: windows(s, SECS) for d, s in S.items()}

    print("\n" + "=" * 88)
    print(f"1  DOSE-RESPONSE — forward mid move by imbalance decile "
          f"({SECS}s windows)")
    print("=" * 88)
    print("  Decile 1 = most size on the offer, decile 10 = most on the bid.")
    print("  A real mechanism trends across the row. Numbers are points.\n")
    for hold in (1, 3, 6, 30):
        print(f"  --- hold {SECS*hold}s ---")
        for d, w in W.items():
            f = w.mid.shift(-hold) - w.mid
            q = pd.qcut(w.imb, 10, labels=False, duplicates="drop")
            cells = [f[q == i].mean() for i in range(10)]
            print(f"    {d}  " + " ".join(f"{c:+6.2f}" for c in cells))
        print("       decile " + " ".join(f"{i+1:>6}" for i in range(10)))

    print("\n" + "=" * 88)
    print("2  EXTREMES, DE-OVERLAPPED, PER DAY")
    print("=" * 88)
    print("  Buy when the bid is stacked (top decile), sell when the offer is.")
    print("  Sign convention: positive = trading WITH the visible size pays.\n")

    for hold in (3, 6, 30):
        k = hold
        pooled, signs = [], []
        print(f"  --- hold {SECS*hold}s ---")
        for d, w in W.items():
            f = (w.mid.shift(-k) - w.mid).to_numpy()
            hi = w.imb >= w.imb.quantile(0.90)
            lo = w.imb <= w.imb.quantile(0.10)
            ih = deoverlap(w, hi, k)
            il = deoverlap(w, lo, k)
            v = np.concatenate([f[ih], -f[il]])
            r = stat(v, COST_PTS)
            show(f"    {d}", r, mark=False)
            if r:
                signs.append(np.sign(r["mean"]))
            pooled.append(v)
        agree = len(set(signs)) == 1 if signs else False
        show(f"    POOLED  [{'all days agree' if agree else 'days disagree'}]",
             stat(np.concatenate(pooled), COST_PTS))

    print("\n" + "=" * 88)
    print("3  CONTROL — what a random entry earns over the same horizon")
    print("=" * 88)
    for hold in (3, 6, 30):
        pooled = []
        for d, w in W.items():
            pooled.append((w.mid.shift(-hold) - w.mid).to_numpy())
        show(f"  long every window, hold {SECS*hold}s",
             stat(np.concatenate(pooled)), mark=False)

    print("\n" + "=" * 88)
    print("4  GROSS, BEFORE COSTS — is there signal even if it is untradeable?")
    print("=" * 88)
    print("  A gross edge smaller than the spread is still a real finding about")
    print("  the market; it just cannot be traded this way.\n")
    for hold in (1, 3, 6):
        pooled = []
        for d, w in W.items():
            f = (w.mid.shift(-hold) - w.mid).to_numpy()
            hi = w.imb >= w.imb.quantile(0.90)
            lo = w.imb <= w.imb.quantile(0.10)
            ih, il = deoverlap(w, hi, hold), deoverlap(w, lo, hold)
            pooled.append(np.concatenate([f[ih], -f[il]]))
        show(f"  hold {SECS*hold}s, gross", stat(np.concatenate(pooled)))


if __name__ == "__main__":
    main()
