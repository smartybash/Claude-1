#!/usr/bin/env python3
"""PULLED OR FILLED — the measurement that needs both recordings at once.

When resting size at the bid disappears, exactly one of two things happened,
and they mean opposite things:

    it was FILLED   someone sold into it. The bid absorbed real supply.
    it was PULLED   nobody traded. The buyer simply cancelled and left.

A depth file alone cannot tell them apart: size drops either way. A tape file
alone cannot see resting size at all. Put the two together, and the difference
is exactly computable -- match each trade to the book interval it printed in,
and whatever size vanished beyond what the trades consumed was cancelled.

That distinction is the whole content of "absorption". A level that keeps
refilling as it is hit is a buyer who wants the inventory. A level that
evaporates untouched is a buyer who never intended to be there. Every screen
read in this project has been an eyeball estimate of this quantity; here it is
measured.

Per interval between consecutive snapshots, at the touch price:

    filled   = contracts that traded at that price with the aggressor
               hitting that side
    delta    = resting size after minus resting size before
    net_add  = delta + filled

net_add is the size added or removed by cancellation and new orders alone,
with trading stripped out. Negative is pulling, positive is replenishment.

Guards, all of them, because this project has produced three findings that
looked real and were not: entry on the window close, mid price, de-overlapped
trades, every session reported separately, a control, a dose-response, and
costs charged.

Usage: python3 scripts/pull_vs_fill.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEPTH = ROOT / "data" / "depth"
TAPE = ROOT / "data" / "tape"

TICK = 0.25
POINT_USD = 20.0
COST_PTS = 2.0
BAR_T = 3.0
SECS = 10


def touch_frames(path: Path):
    df = pd.read_csv(path, encoding="utf-8-sig",
                     dtype={"side": "string", "level": np.int32,
                            "price": np.float64, "volume": np.float64})
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    df = df.drop_duplicates(subset=["time", "side", "price"], keep="first")
    t0 = df[(df.level == 0)]
    b = t0[t0.side == "B"].drop_duplicates("time", keep="last")
    a = t0[t0.side == "A"].drop_duplicates("time", keep="last")
    return (b[["time", "price", "volume"]].reset_index(drop=True),
            a[["time", "price", "volume"]].reset_index(drop=True))


def trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig",
                     dtype={"price": np.float64, "volume": np.float64,
                            "aggressor": "string"})
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    # A day recorded twice appends the whole session again; the clock stepping
    # backwards is the signature, and only the first run is kept.
    back = np.flatnonzero(df.time.values[1:] < df.time.values[:-1])
    if len(back):
        df = df.iloc[: back[0] + 1]
    return df.reset_index(drop=True)


def decompose(book: pd.DataFrame, tr: pd.DataFrame, hit_side: str):
    """Split the change in resting size into trading and cancellation.

    hit_side is the aggressor that consumes this side of the book: sellers hit
    the bid, buyers lift the offer.
    """
    bt = book.time.values.astype("datetime64[ns]").astype(np.int64)
    bp = book.price.to_numpy()
    bv = book.volume.to_numpy()

    m = tr.aggressor == hit_side
    tt = tr.time.values[m].astype("datetime64[ns]").astype(np.int64)
    tp = tr.price.to_numpy()[m]
    tv = tr.volume.to_numpy()[m]

    # Interval i is (book_time[i], book_time[i+1]]. A trade at exactly a
    # snapshot time is credited to the interval that just closed.
    idx = np.searchsorted(bt, tt, side="left") - 1
    ok = (idx >= 0) & (idx < len(bt) - 1)
    idx, tp, tv = idx[ok], tp[ok], tv[ok]
    # Only trades at the price that was resting count as consuming that level.
    same = np.isclose(tp, bp[idx])
    idx, tv = idx[same], tv[same]

    filled = np.zeros(len(bt) - 1)
    np.add.at(filled, idx, tv)

    held = bp[1:] == bp[:-1]          # the touch price did not move
    delta = np.where(held, bv[1:] - bv[:-1], np.nan)
    net_add = delta + filled

    return pd.DataFrame({
        "time": book.time.values[:-1],
        "price": bp[:-1],
        "size": bv[:-1],
        "filled": filled,
        "net_add": np.where(held, net_add, np.nan),
    })


def build(day: str) -> pd.DataFrame:
    b, a = touch_frames(next(DEPTH.glob(f"L2_*{day}*")))
    tr = trades(next(TAPE.glob(f"TAPE_*{day}*")))

    bid = decompose(b, tr, "S")       # sellers hit the bid
    ask = decompose(a, tr, "B")       # buyers lift the offer

    mid = pd.DataFrame({
        "time": b.time, "bp": b.price,
    }).merge(pd.DataFrame({"time": a.time, "ap": a.price}),
             on="time", how="inner")
    mid["mid"] = (mid.bp + mid.ap) / 2.0

    x = (bid.set_index("time")[["filled", "net_add", "size"]]
         .rename(columns=lambda c: "b_" + c)
         .join(ask.set_index("time")[["filled", "net_add", "size"]]
               .rename(columns=lambda c: "a_" + c), how="outer")
         .join(mid.set_index("time")["mid"], how="outer"))
    x["mid"] = x["mid"].ffill()
    return x.dropna(subset=["mid"])


def windows(x: pd.DataFrame) -> pd.DataFrame:
    g = x.resample(f"{SECS}s")
    w = pd.DataFrame({
        "mid": g.mid.last(),
        "b_filled": g.b_filled.sum(), "a_filled": g.a_filled.sum(),
        "b_add": g.b_net_add.sum(), "a_add": g.a_net_add.sum(),
        "b_size": g.b_size.mean(), "a_size": g.a_size.mean(),
        "n": g.mid.count(),
    })
    w = w[w.n > 0].dropna()
    # Absorption score: the bid took supply and refilled anyway, while the
    # offer did not. Positive means the bid is the stronger side.
    w["absorb"] = ((w.b_filled + w.b_add) - (w.a_filled + w.a_add))
    return w


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
        print(f"  {lbl:<42} too few")
        return
    star = " **" if (mark and abs(r["t"]) >= BAR_T) else ""
    print(f"  {lbl:<42} n={r['n']:<6} {r['mean']:+6.3f}pt "
          f"{r['mean']*POINT_USD:+7.1f}$  win {r['win']:3.0f}%  "
          f"t={r['t']:+6.2f}{star}")


def deoverlap(n, sel, k):
    idx, block = [], -1
    for i in np.flatnonzero(sel):
        if i < block or i + k >= n:
            continue
        idx.append(i)
        block = i + k
    return np.array(idx, dtype=int)


def main():
    days = sorted(p.name.split("_")[-1].split(".")[0]
                  for p in DEPTH.glob("L2_*.csv*"))
    W = {}
    for d in days:
        W[d] = windows(build(d))

    print("=" * 90)
    print("PULLED OR FILLED — decomposing the change in resting size")
    print(f"{len(W)} sessions, {SECS}s windows, cost {COST_PTS} pts, "
          f"bar |t| >= {BAR_T}")
    print("=" * 90)

    print("\n1  HOW MUCH OF THE BOOK'S MOVEMENT IS TRADING vs CANCELLING?")
    print("   If cancellation dwarfs trading, then most of what looks like")
    print("   absorption on a screen is orders being moved, not filled.\n")
    for d, w in W.items():
        f = w.b_filled.sum() + w.a_filled.sum()
        c = w.b_add.abs().sum() + w.a_add.abs().sum()
        print(f"   {d}  filled {f:>11,.0f} contracts   "
              f"cancelled or added {c:>12,.0f}   ratio {c/max(f,1):.1f}x")

    print("\n" + "=" * 90)
    print("2  DOSE-RESPONSE — forward mid move by absorption decile")
    print("=" * 90)
    print("   Decile 1 = offer is the stronger side, 10 = bid is. Points.\n")
    for hold in (3, 6, 30):
        print(f"   --- hold {SECS*hold}s ---")
        for d, w in W.items():
            fwd = w.mid.shift(-hold) - w.mid
            q = pd.qcut(w.absorb, 10, labels=False, duplicates="drop")
            print(f"     {d}  " +
                  " ".join(f"{fwd[q == i].mean():+6.2f}" for i in range(10)))
        print("        decile " + " ".join(f"{i+1:>6}" for i in range(10)))

    print("\n" + "=" * 90)
    print("3  EXTREMES, DE-OVERLAPPED, PER SESSION")
    print("=" * 90)
    print("   Long when the bid absorbed and refilled, short when the offer")
    print("   did. Positive = the absorption read pays.\n")
    for hold in (3, 6, 30):
        pooled, signs = [], []
        print(f"   --- hold {SECS*hold}s ---")
        for d, w in W.items():
            fwd = (w.mid.shift(-hold) - w.mid).to_numpy()
            hi = (w.absorb >= w.absorb.quantile(0.90)).to_numpy()
            lo = (w.absorb <= w.absorb.quantile(0.10)).to_numpy()
            ih = deoverlap(len(w), hi, hold)
            il = deoverlap(len(w), lo, hold)
            v = np.concatenate([fwd[ih], -fwd[il]])
            r = stat(v, COST_PTS)
            show(f"     {d}", r, mark=False)
            if r:
                signs.append(np.sign(r["mean"]))
            pooled.append(v)
        agree = len(set(signs)) == 1 if signs else False
        show(f"     POOLED [{'all agree' if agree else 'DAYS DISAGREE'}]",
             stat(np.concatenate(pooled), COST_PTS))

    print("\n" + "=" * 90)
    print("4  GROSS, AND THE PURE-CANCELLATION VARIANT")
    print("=" * 90)
    print("   Trading stripped out entirely: only who pulled and who added.\n")
    for hold in (3, 6, 30):
        pooled, pooled_c = [], []
        for d, w in W.items():
            fwd = (w.mid.shift(-hold) - w.mid).to_numpy()
            hi = (w.absorb >= w.absorb.quantile(0.90)).to_numpy()
            lo = (w.absorb <= w.absorb.quantile(0.10)).to_numpy()
            pooled.append(np.concatenate([
                fwd[deoverlap(len(w), hi, hold)],
                -fwd[deoverlap(len(w), lo, hold)]]))
            c = w.b_add - w.a_add
            hi2 = (c >= c.quantile(0.90)).to_numpy()
            lo2 = (c <= c.quantile(0.10)).to_numpy()
            pooled_c.append(np.concatenate([
                fwd[deoverlap(len(w), hi2, hold)],
                -fwd[deoverlap(len(w), lo2, hold)]]))
        show(f"   absorption, hold {SECS*hold}s, gross",
             stat(np.concatenate(pooled)))
        show(f"   cancellation only, hold {SECS*hold}s, gross",
             stat(np.concatenate(pooled_c)))


if __name__ == "__main__":
    main()
