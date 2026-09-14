"""Backtest the clean VWAP + FVG strategy on real 5-min QQQ (123 sessions), and
slice the results by filters (gamma regime, direction, time) to find no-go days.

PRE-REGISTERED RULES (one fixed spec, no tuning after the fact):
  bias    = sign(close - session VWAP)
  setup   = a 3-bar FVG in the direction of bias
              bullish FVG (support): low[i] > high[i-2], zone [high[i-2] .. low[i]]
              bearish FVG (resist) : high[i] < low[i-2], zone [high[i] .. low[i-2]]
  entry   = first time price retraces to the NEAR edge of an unfilled aligned FVG
            (long: bar low <= gap_top while close>VWAP -> fill limit at gap_top;
             short: bar high >= gap_bot while close<VWAP -> fill at gap_bot)
  stop    = far edge of the gap (gap fully filled = thesis dead)
  risk R  = gap height; target = entry +/- M*R (test M = 1.0 / 1.5 / 2.0)
  exit    = stop or target intrabar (stop checked first if both); else EOD at close
  filters = min gap 0.03% of price; one trade per FVG; RTH only; no costs modelled

Gamma regime for a session = sign of the prior session's net GEX (chain at close D
governs D+1), from gex_history.jsonl.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_GAP = 0.0003   # 0.03% of price


def load_intraday():
    frames = [pd.read_csv(f) for f in sorted(glob.glob(str(ROOT / "data" / "intraday" / "qqq_5m_*.csv")))]
    a = pd.concat(frames, ignore_index=True)
    a["ts"] = pd.to_datetime(a["timestamp"])
    a = a.drop_duplicates("ts").sort_values("ts").set_index("ts")
    a["day"] = a.index.normalize()
    return a


def regime_map(days):
    """session-day -> net_gex of the chain that governs it (prior session's chain)."""
    gex = sorted([json.loads(l) for l in (ROOT / "data" / "gex_history.jsonl").read_text().splitlines()
                  if l.strip()], key=lambda g: g["date"])
    gex = [g for g in gex if g["sym"] == "QQQ"]
    out = {}
    for g in gex:
        d0 = pd.Timestamp(g["date"]).normalize()
        after = [x for x in days if x > d0]
        if after:
            out[after[0]] = g["net_gex"]
    return out


def session_vwap(b):
    tp = (b["high"] + b["low"] + b["close"]) / 3
    return (tp * b["volume"]).cumsum() / b["volume"].cumsum()


def run(M, mode="edge"):
    """mode='edge': limit fill at the gap near-edge (no look-ahead on close).
       mode='confirm': enter at the CLOSE of the first bar that retraces into the
       gap AND closes in the trade direction (realistic confirmation candle)."""
    intr = load_intraday()
    days = sorted(intr["day"].unique())
    reg = regime_map(days)
    trades = []
    for day in days:
        b = intr[intr["day"] == day].reset_index()
        if len(b) < 6:
            continue
        vwap = session_vwap(b).values
        o, h, l, c = b["open"].values, b["high"].values, b["low"].values, b["close"].values
        n = len(b)
        net = reg.get(day)
        fvgs = []
        for i in range(n):
            if i >= 2:
                if l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bull", "top": l[i], "bot": h[i - 2], "formed": i, "used": False})
                if h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bear", "top": l[i - 2], "bot": h[i], "formed": i, "used": False})
            for f in fvgs:
                if f["used"] or i <= f["formed"]:
                    continue
                gap = f["top"] - f["bot"]
                if gap <= 0:
                    continue
                if f["side"] == "bull" and c[i] > vwap[i] and l[i] <= f["top"]:
                    if mode == "edge":
                        entry, stop = f["top"], f["bot"]; risk = gap
                        sbs = l[i] <= stop
                    else:  # confirm: need the bar to close green and above the gap floor
                        if not (c[i] > o[i] and c[i] > f["bot"]):
                            continue
                        entry, stop = c[i], f["bot"]; risk = entry - stop; sbs = False
                    f["used"] = True
                    ex = {"conf": c[i] > o[i], "gap": gap / entry * 100, "dv": abs(entry - vwap[i]) / entry * 100}
                    trades.append(_walk(b, i, "long", entry, stop, entry + M * risk, risk, net, day, sbs, ex))
                elif f["side"] == "bear" and c[i] < vwap[i] and h[i] >= f["bot"]:
                    if mode == "edge":
                        entry, stop = f["bot"], f["top"]; risk = gap
                        sbs = h[i] >= stop
                    else:
                        if not (c[i] < o[i] and c[i] < f["top"]):
                            continue
                        entry, stop = c[i], f["top"]; risk = stop - entry; sbs = False
                    f["used"] = True
                    ex = {"conf": c[i] < o[i], "gap": gap / entry * 100, "dv": abs(entry - vwap[i]) / entry * 100}
                    trades.append(_walk(b, i, "short", entry, stop, entry - M * risk, risk, net, day, sbs, ex))
            fvgs = [f for f in fvgs if f["used"] or not (
                (f["side"] == "bull" and l[i] <= f["bot"]) or
                (f["side"] == "bear" and h[i] >= f["top"]))]
    return pd.DataFrame([t for t in trades if t])


def _walk(b, i, dirn, entry, stop, tgt, risk, net, day, same_bar_stop, ex):
    h, l, c = b["high"].values, b["low"].values, b["close"].values
    n = len(b)
    hr = b["ts"].iloc[i].hour
    base = {"day": day, "dir": dirn, "net": net, "hour": hr, **ex}
    if same_bar_stop:                         # limit filled then blew through the stop same bar
        return {**base, "R": -1.0}
    for j in range(i + 1, n):
        if dirn == "long":
            if l[j] <= stop:
                r = -1.0; break
            if h[j] >= tgt:
                r = (tgt - entry) / risk; break
        else:
            if h[j] >= stop:
                r = -1.0; break
            if l[j] <= tgt:
                r = (entry - tgt) / risk; break
    else:
        r = ((c[-1] - entry) if dirn == "long" else (entry - c[-1])) / risk
    return {**base, "R": r}


def stats(df, label):
    if len(df) == 0:
        print(f"  {label:28s} n=0"); return
    print(f"  {label:28s} n={len(df):3d}  win {(df['R']>0).mean():.0%}  "
          f"avg {df['R'].mean():+.2f}R  total {df['R'].sum():+.0f}R")


def main():
    for M in (1.0, 1.5, 2.0):
        df = run(M)
        print(f"===== target = {M:.1f}R =====")
        stats(df, "ALL trades")
        if len(df):
            stats(df[df["dir"] == "long"], "longs")
            stats(df[df["dir"] == "short"], "shorts")
            stats(df[df["net"].notna() & (df["net"] < 0)], "NEGATIVE-gamma days")
            stats(df[df["net"].notna() & (df["net"] > 0)], "POSITIVE-gamma days")
            stats(df[df["hour"] < 11], "entry before 11:00 ET")
            stats(df[df["hour"] >= 11], "entry 11:00 ET or later")
        print()

    # LOOK-AHEAD CHECK: confirmation done properly (enter at the confirm bar's CLOSE)
    print("===== CONFIRMATION CANDLE, done right (enter at close, no look-ahead) =====")
    for M in (1.0, 1.5, 2.0):
        dfc = run(M, mode="confirm")
        stats(dfc, f"confirm-entry, target {M}R")
        if len(dfc):
            stats(dfc[dfc["net"].notna() & (dfc["net"] > 0)], f"  POS-gamma, {M}R")
            stats(dfc[dfc["net"].notna() & (dfc["net"] < 0)], f"  NEG-gamma, {M}R")
    print()

    # non-look-ahead filters on the edge-fill version (gap size, dist to vwap)
    M = 1.5
    df = run(M)
    print(f"===== non-look-ahead filters (edge fill, target {M}R, n={len(df)}) =====")
    for lab, q in [("gap smallest third", (0, 1/3)), ("gap middle third", (1/3, 2/3)),
                   ("gap largest third", (2/3, 1.0))]:
        lo, hi = df["gap"].quantile(q[0]), df["gap"].quantile(q[1])
        stats(df[(df["gap"] >= lo) & (df["gap"] <= hi)], lab)
    near = df["dv"].median()
    stats(df[df["dv"] <= near], "entry NEAR vwap")
    stats(df[df["dv"] > near], "entry FAR from vwap")
    print("\nread: 'edge is real' = avg R clearly > 0 with a sane win%. The confirmation "
          "number only counts if it SURVIVES entering at the close (no look-ahead).")


if __name__ == "__main__":
    main()
