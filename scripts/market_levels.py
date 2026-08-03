"""Holistic market view — emits ToS zone-input blocks for MNQ, QQQ, MES, SPY.

MNQ shares NQ's price; MES shares ES's. Four price scales, one confluence engine.
Standard rerun step: refresh the 30-min data files + the PRICES below, then run.
Same nq_confluence.ts study goes on all four charts — only the zone inputs differ
(macro bias, VWAP, channel, structure are computed natively per symbol).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt

# (label, 30-min data file, is_futures, live price)  — update PRICES each rerun
INST = [
    ("MNQ  (NQ Sep'26)", "nq_30min_eth.json", True, 28578.0),
    ("QQQ",              "qqq_30m_live.json", False, 692.34),
    ("MES  (ES Sep'26)", "es_30m_live.json",  True, 7587.75),
    ("SPY",              "spy_30m_live.json", False, 753.62),
]


def load_any(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert("America/New_York"))
    return df[~df.index.duplicated(keep="last")].sort_index()


def split(df, fut):
    s = pd.Series(df.index.date, index=df.index)
    if fut:
        ev = df.index.hour >= 18
        s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def main():
    print("HOLISTIC MARKET LEVELS — paste each block into nq_confluence.ts on that symbol's chart\n")
    for name, fname, fut, px in INST:
        df = load_any(fname)
        df, ids, by = split(df, fut)
        cur = ids[-1]
        hist = df[df["sess"] < cur]
        zs, _ = bt.build(hist, by[ids[-2]], 13)
        az = [z for z in zs if (z["w"] >= 6 or z["nt"] >= 3) and abs(z["price"] - px) <= 0.015 * px]
        az.sort(key=lambda z: z["price"], reverse=True)
        d = 2 if px < 2000 else 1
        print(f"### {name}   px {px:.{d}f}   ({len(az)} zones in range)")
        for i, z in enumerate(az[:4], 1):
            res = "yes" if z["price"] > px else "no"
            g = "DENSE" if z["nt"] >= 4 else ("A+" if z["w"] >= 8 else "wk")
            print(f"  input z{i}_hi = {z['hi']:.{d}f};  input z{i}_lo = {z['lo']:.{d}f};  "
                  f"input z{i}_resist = {res};   # {z['price']:.{d}f} {g}")
        print()


if __name__ == "__main__":
    main()
