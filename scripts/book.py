#!/usr/bin/env python3
"""Rebuild the order book from the change-only depth format, and prove it.

The recorder no longer writes a full ladder on every snapshot. It writes a
level only when that price's resting size changed, a row with volume 0 when a
price drops out of the top of the book, and a full ladder every KeyframeSeconds
so the state can be re-anchored. That cuts the file by roughly an order of
magnitude and makes it useless if the reconstruction is even slightly wrong.

So this module carries its own test. It simulates the C# writer's logic against
a synthetic book, reconstructs from the resulting rows, and asserts the rebuilt
book equals the true book at every single timestamp. Run it directly to see the
test pass before trusting any analysis built on top.

Usage: python3 scripts/book.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load_depth(path: Path) -> pd.DataFrame:
    # .csv and .csv.gz both work: pandas decompresses by extension.
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    return df.dropna(subset=["time"]).reset_index(drop=True)


def replay(df: pd.DataFrame):
    """Yield (timestamp, bids, asks) after every timestamp's rows are applied.

    bids and asks are {price: volume} with zero-volume prices removed, which is
    what "the level is gone" means. Rows carrying level == -1 are the removals
    the recorder writes when a price leaves the top of the book.
    """
    book = {"B": {}, "A": {}}
    t = df["time"].to_numpy()
    side = df["side"].to_numpy()
    price = df["price"].to_numpy(dtype=np.float64)
    vol = df["volume"].to_numpy(dtype=np.float64)

    i, n = 0, len(df)
    while i < n:
        j = i
        while j < n and t[j] == t[i]:
            j += 1
        for k in range(i, j):
            s = side[k]
            if vol[k] <= 0:
                book[s].pop(price[k], None)
            else:
                book[s][price[k]] = vol[k]
        yield pd.Timestamp(t[i]), dict(book["B"]), dict(book["A"])
        i = j


def top(side_book: dict, n: int, best_first_desc: bool):
    """The n prices nearest the touch, as (price, volume) pairs."""
    items = sorted(side_book.items(), key=lambda kv: kv[0],
                   reverse=best_first_desc)
    return items[:n]


# ---------------------------------------------------------------------------
# the test
# ---------------------------------------------------------------------------
def _simulate_writer(states, levels=10, keyframe_every=6):
    """Mirror of EmitSide in L2Recorder.cs, so the reader is tested against the
    writer's actual rules rather than against an idealised version of them."""
    rows = []
    written = {}
    for step, (stamp, bids, asks) in enumerate(states):
        keyframe = (step % keyframe_every == 0)
        seen = set()
        for s, book, desc in (("B", bids, True), ("A", asks, False)):
            for i, (p, v) in enumerate(top(book, levels, desc)):
                key = (s, p)
                seen.add(key)
                if not keyframe and written.get(key) == v:
                    continue
                written[key] = v
                rows.append((stamp, s, i, p, v))
        for key in [k for k in written if k not in seen]:
            rows.append((stamp, key[0], -1, key[1], 0))
            del written[key]
    return pd.DataFrame(rows,
                        columns=["time", "side", "level", "price", "volume"])


def _synthetic(n_steps=400, levels=10, seed=7):
    """A book that drifts, so prices enter and leave the top ten."""
    rng = np.random.default_rng(seed)
    mid = 29500.0
    states, truth = [], []
    vols = {}
    for step in range(n_steps):
        mid += rng.choice([-5.0, 0.0, 0.0, 5.0])
        bids, asks = {}, {}
        for i in range(levels):
            bp, ap = mid - 5 * (i + 1), mid + 5 * (i + 1)
            for p, side in ((bp, bids), (ap, asks)):
                if p not in vols or rng.random() < 0.25:
                    vols[p] = float(rng.integers(1, 500))
                side[p] = vols[p]
        stamp = pd.Timestamp("2026-09-14 13:30:00") + pd.Timedelta(seconds=step)
        states.append((stamp, bids, asks))
        truth.append((stamp, dict(bids), dict(asks)))
    return states, truth


def self_test():
    states, truth = _synthetic()
    rows = _simulate_writer(states)

    full = sum(len(b) + len(a) for _, b, a in states)
    print(f"  full-ladder rows would be   {full:,}")
    print(f"  change-only rows written    {len(rows):,}")
    print(f"  reduction                   {full / max(len(rows), 1):.1f}x")

    # A timestamp where nothing changed writes no rows at all, so the rebuilt
    # sequence is shorter than the true one by design: the book simply carries
    # forward. The test therefore compares the true book against the most
    # recent rebuilt state at or before that time, which is also exactly how
    # analysis will query it -- "what was resting when this trade printed".
    rebuilt = list(replay(rows))
    print(f"  timestamps carrying a change {len(rebuilt):,} "
          f"of {len(truth):,}")

    bad, r = 0, 0
    for ts_t, b_t, a_t in truth:
        while r + 1 < len(rebuilt) and rebuilt[r + 1][0] <= ts_t:
            r += 1
        _, b_r, a_r = rebuilt[r]
        exp_b = dict(top(b_t, 10, True))
        exp_a = dict(top(a_t, 10, False))
        if b_r != exp_b or a_r != exp_a:
            bad += 1
            if bad == 1:
                print(f"  MISMATCH at {ts_t}")
                print(f"    missing: {set(exp_b.items()) - set(b_r.items())}")
                print(f"    extra:   {set(b_r.items()) - set(exp_b.items())}")
    if bad:
        raise AssertionError(f"{bad} of {len(truth)} timestamps rebuilt wrong")
    print(f"  reconstruction exact at all {len(truth):,} timestamps  OK")


if __name__ == "__main__":
    print("Round-trip test: change-only writer -> reader")
    self_test()
