"""'Trade the transition': compression near heavy gamma strikes, expansion once
price escapes into low-gamma gaps. Honest intraday test, no new fetches.

Data: gex_history.jsonl (flip, call_wall, put_wall per QQQ session) + 5-min RTH
bars in data/intraday/. Two claims:

  A) COMPRESSION near strikes: the closer price is to the nearest heavy gamma
     level (flip / call wall / put wall), the SMALLER the forward 30-min range.
     Test: pool intraday bars, corr(dist-to-nearest-level, forward range); and
     near-vs-far tercile means.

  B) EXPANSION on escape: when price CROSSES the gamma flip intraday (leaves the
     positive-gamma side into the low/negative-gamma side), realized range in the
     30 min AFTER the cross > the 30 min BEFORE. Event study, ratio post/pre,
     split by cross direction (down = into negative gamma = should expand most).
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
K = 6   # 30 min forward window


def load_intraday():
    frames = [pd.read_csv(f) for f in sorted(glob.glob(str(ROOT / "data" / "intraday" / "qqq_5m_*.csv")))]
    a = pd.concat(frames, ignore_index=True)
    a["ts"] = pd.to_datetime(a["timestamp"])
    a = a.drop_duplicates("ts").sort_values("ts").set_index("ts")
    a["day"] = a.index.normalize()
    return a


def main():
    intr = load_intraday()
    days = sorted(intr["day"].unique())
    gex = sorted([json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines()
                  if l.strip()], key=lambda g: g["date"])
    gex = [g for g in gex if g["sym"] == "QQQ"]

    dist_rows, fwd_rows = [], []
    pre_post = []   # (cross_dir, pre_range, post_range)
    for g in gex:
        d0 = pd.Timestamp(g["date"]).normalize()
        after = [x for x in days if x > d0]
        if not after:
            continue
        nd = after[0]
        b = intr[intr["day"] == nd]
        if len(b) < 2 * K + 2:
            continue
        flip, cw, pw = g["gamma_flip"], g["call_wall"], g["put_wall"]
        c = b["close"].values; h = b["high"].values; l = b["low"].values
        n = len(b)
        # A) compression: dist to nearest heavy level vs forward range
        for i in range(n - K):
            dist = min(abs(c[i] - flip), abs(c[i] - cw), abs(c[i] - pw)) / c[i] * 100
            frng = (h[i + 1:i + 1 + K].max() - l[i + 1:i + 1 + K].min()) / c[i] * 100
            dist_rows.append(dist); fwd_rows.append(frng)
        # B) escape: first flip cross, range K before vs K after
        side = np.sign(c - flip)
        cross = None
        for i in range(1, n):
            if side[i] != 0 and side[i - 1] != 0 and side[i] != side[i - 1]:
                cross = i; break
        if cross is not None and cross >= K and cross + K <= n:
            pre = (h[cross - K:cross].max() - l[cross - K:cross].min()) / c[cross] * 100
            post = (h[cross:cross + K].max() - l[cross:cross + K].min()) / c[cross] * 100
            direction = "down (into neg gamma)" if side[cross] < 0 else "up (into pos gamma)"
            pre_post.append((direction, pre, post))

    d = pd.DataFrame({"dist": dist_rows, "fwd": fwd_rows})
    print(f"A) COMPRESSION near heavy strikes  (pooled 5-min bars, n={len(d)})")
    print(f"   corr(dist-to-nearest-level, forward 30-min range) = {d['dist'].corr(d['fwd']):+.2f}")
    d["b"] = pd.qcut(d["dist"], 3, labels=["nearest", "mid", "farthest"])
    for lab, s in d.groupby("b", observed=True):
        print(f"   {lab:9s} to a level: forward range {s['fwd'].mean():.2f}%")
    print("   -> hypothesis: 'nearest' has the SMALLEST forward range, rising to 'farthest'.\n")

    pp = pd.DataFrame(pre_post, columns=["dir", "pre", "post"])
    print(f"B) EXPANSION on flip escape  (sessions with a flip cross, n={len(pp)})")
    if len(pp):
        print(f"   ALL crosses: pre-range {pp['pre'].mean():.2f}%  post-range {pp['post'].mean():.2f}%  "
              f"ratio {pp['post'].mean()/pp['pre'].mean():.2f}x  "
              f"({(pp['post']>pp['pre']).mean():.0%} expanded)")
        for dr, s in pp.groupby("dir"):
            print(f"   {dr:22s}: pre {s['pre'].mean():.2f}% post {s['post'].mean():.2f}%  "
                  f"ratio {s['post'].mean()/s['pre'].mean():.2f}x  n={len(s)}")
    print("   -> hypothesis: post/pre ratio > 1 (range expands after escaping the flip), "
          "biggest on DOWN crosses into negative gamma.")

    print("\nread: A confirms if forward range grows monotonically with distance from the "
          "nearest heavy strike; B confirms if the flip cross is followed by a clear "
          "range expansion. Ratios ~1 / flat bins = the transition edge isn't there.")


if __name__ == "__main__":
    main()
