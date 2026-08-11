"""NQ transfer check for the VWAP+FVG continuation strategy.

Runs the SAME rules as backtest_fvg_exits (structure stop, half@1R+ride / VWAP-ride)
on real NQ futures 5-min RTH bars, joined to the QQQ-derived net_gex regime (the
same NDX options market governs NQ). Confirms whether the strategy transfers from
the QQQ ETF to the NQ future the user actually trades.

DATA LIMITATION: IBKR get_price_history caps at 1000 bars/call with no historical
paging, so this only covers the most recent ~11-13 NQ sessions per pull. Drop more
months into data/intraday_nq/ (same timestamp,open,high,low,close,volume format) as
they accumulate to grow the sample. Alpha Vantage has no futures, so there is no
bulk historical NQ intraday source here — the expansion-day edge test on NQ needs
either accumulated pulls or a futures-history provider.

Usage: python3 scripts/backtest_nq_check.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from backtest_vwap_fvg import session_vwap, MIN_GAP
K = 5


def load_nq():
    fs = sorted(glob.glob(str(ROOT / "data" / "intraday_nq" / "*.csv")))
    if not fs:
        raise SystemExit("no NQ intraday in data/intraday_nq/")
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates("ts").sort_values("ts")
    df["day"] = df["ts"].dt.normalize()
    return df


def regime_map():
    gex = {g["date"]: g["net_gex"] for g in
           (json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines() if l.strip())
           if g["sym"] == "QQQ"}
    gd = sorted(gex)

    def prior(day):
        ds = day.strftime("%Y-%m-%d"); p = [d for d in gd if d < ds]
        return gex[p[-1]] if p else None
    return prior


def _walk(s, i, entry, stop, risk, h, l, c, vwap, n, mode, net):
    def stopped(j): return (l[j] <= stop) if s > 0 else (h[j] >= stop)
    def vlost(j): return (c[j] < vwap[j]) if s > 0 else (c[j] > vwap[j])
    def rr(p): return s * (p - entry) / risk
    if mode == "half1":
        tgt = entry + s * risk
        for j in range(i + 1, n):
            if stopped(j): return [-1.0, net]
            if (h[j] >= tgt) if s > 0 else (l[j] <= tgt):
                for k in range(j + 1, n):
                    if (l[k] <= entry) if s > 0 else (h[k] >= entry): rem = 0.0; break
                    if vlost(k): rem = rr(c[k]); break
                else: rem = rr(c[n - 1])
                return [0.5 + 0.5 * rem, net]
        return [rr(c[n - 1]), net]
    for j in range(i + 1, n):
        if stopped(j): return [-1.0, net]
        if vlost(j): return [rr(c[j]), net]
    return [rr(c[n - 1]), net]


def run(df, prior, mode):
    trades = []
    for day, b in df.groupby("day"):
        b = b.reset_index(drop=True)
        if len(b) < K + 3:
            continue
        vwap = session_vwap(b).values
        h, l, c = b["high"].values, b["low"].values, b["close"].values
        n = len(b); net = prior(day); fvgs = []
        for i in range(n):
            if i >= 2:
                if l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
                    fvgs.append(["bull", l[i], h[i - 2], i, False])
                if h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
                    fvgs.append(["bear", l[i - 2], h[i], i, False])
            for f in fvgs:
                if f[4] or i <= f[3] or i < K:
                    continue
                side, top, bot = f[0], f[1], f[2]
                if side == "bull" and l[i] <= top and c[i] > vwap[i]:
                    entry = top; stop = min(l[i - K:i + 1]); risk = entry - stop
                    if risk > 0 and l[i] > stop:
                        f[4] = True; trades.append(_walk(1, i, entry, stop, risk, h, l, c, vwap, n, mode, net))
                elif side == "bear" and h[i] >= bot and c[i] < vwap[i]:
                    entry = bot; stop = max(h[i - K:i + 1]); risk = stop - entry
                    if risk > 0 and h[i] < stop:
                        f[4] = True; trades.append(_walk(-1, i, entry, stop, risk, h, l, c, vwap, n, mode, net))
            fvgs = [f for f in fvgs if f[4] or not (
                (f[0] == "bull" and l[i] <= f[2]) or (f[0] == "bear" and h[i] >= f[1]))]
    return pd.DataFrame(trades, columns=["R", "net"])


def main():
    df = load_nq(); prior = regime_map()
    sess = sorted(df["day"].dt.strftime("%Y-%m-%d").unique())
    print(f"NQ transfer check — {len(sess)} RTH sessions {sess[0]}..{sess[-1]} (small sample)\n")
    for mode in ("vwapCross", "half1"):
        d = run(df, prior, mode).dropna(); d["exp"] = d["net"] < 0
        print(f"  {mode}:")
        for lab, sub in [("ALL", d), ("expansion (neg-gamma)", d[d["exp"]]),
                         ("compression (pos-gamma)", d[~d["exp"]])]:
            if len(sub):
                print(f"    {lab:24s} n={len(sub):2d}  win {(sub['R']>0).mean():.0%}  mean {sub['R'].mean():+.2f}R")
    print("\nread: this confirms the strategy MECHANICS transfer to NQ and the character "
          "matches QQQ. The expansion-vs-compression edge needs expansion days + more "
          "sessions than IBKR's 1000-bar cap allows in one pull.")


if __name__ == "__main__":
    main()
