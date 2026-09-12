#!/usr/bin/env python3
"""SECTOR-LEADERSHIP breadth filter — does it improve the VA-fade short?

The idea (user's spec): don't fade-short QQQ into rising leadership. The leaders
are MAGS (Mag-7 basket), SMH (semis), IGV (software). At each VA-fade SHORT
entry, count how many leaders are RISING over the last `breadthLen` bars
(30 min = 6 bars on 5-min). If >=2 are up, risk appetite is ON -> the filter
would BLOCK the short. We test whether the blocked shorts really are worse than
the shorts the filter would keep.

Method:
  * take the exact VA-fade short signals from backtest_va_fade (>=2nd VAH poke,
    after 10:00 ET, day opens below VAH) over the QQQ 2-y 5-min data.
  * for each signal's entry timestamp, read each leader's OWN 5-min series and
    compute up = close[t] > close[t - breadthLen]. upCount in {0..3}.
  * split the fade R (target POC, the tested edge) by:
        KEEP  (upCount < 2, leaders not rising -> filter allows the short)
        BLOCK (upCount >= 2, leaders rising     -> filter would veto the short)
  * a useful filter means KEEP >> BLOCK (we drop the bad ones).

Leaders only have deep intraday history for the recent ~12 months (2025-08 ->
2026-07 in data/intraday/{smh,igv,mags}_5m_*.csv), so the split is measured on
the QQQ signals that fall inside that window.

Usage: python3 scripts/backtest_breadth_filter.py [--breadth-len 6]
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F
import backtest_range_breakout as BR
import backtest_va_fade as VF

LEADERS = ("MAGS", "SMH", "IGV")


def load_leader(sym):
    """{sym} 5-min close series, tz-naive ET index (as stored)."""
    files = sorted(glob.glob(str(ROOT / f"data/intraday/{sym.lower()}_5m_*.csv")))
    if not files:
        return None
    df = pd.concat(pd.read_csv(f, parse_dates=["timestamp"]) for f in files)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["close"]


def leader_up(series, ts, n):
    """True if close at/just-before ts is above close n bars earlier. Uses the
    last bar at or before ts (forward-fill), so a leader with a missing bar is
    read at its most recent print."""
    if series is None:
        return None
    pos = series.index.searchsorted(ts, side="right") - 1
    if pos < n:
        return None
    return bool(series.iloc[pos] > series.iloc[pos - n])


def summ(r):
    a = np.asarray(r, float)
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    return f"n={len(a):3d}  mean {a.mean():+.2f}R  win {100*(a>0).mean():3.0f}%  t={t:+.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breadth-len", type=int, default=6, help="lookback bars (6=30min)")
    a = ap.parse_args()

    sess = F.load_sessions()
    days = sorted(sess)
    reads = BR.gamma_reads("QQQ")
    lead = {s: load_leader(s) for s in LEADERS}
    have = [s for s in LEADERS if lead[s] is not None]
    print(f"leaders with intraday history: {have}")
    for s in have:
        print(f"   {s}: {lead[s].index.min().date()} .. {lead[s].index.max().date()}  "
              f"({len(lead[s])} bars)")

    rows = []
    for i, d in enumerate(days):
        va = VF.prior_va(sess, days, i)
        if not va:
            continue
        poc, vah, val = va
        b = sess[d]
        if float(b["open"].iloc[0]) > vah:
            continue
        g = BR.gamma_lookup(reads, pd.Timestamp(d))
        net = g.get("net_gex") if g else None
        for r in VF.simulate(b, vah, poc, val):
            ts = r["entry_ts"]
            ups = {s: leader_up(lead[s], ts, a.breadth_len) for s in LEADERS}
            known = [v for v in ups.values() if v is not None]
            if not known:                       # no leader data at this ts
                continue
            up_count = sum(1 for v in known if v)
            rows.append(dict(day=d, net=net, r_poc=r["r_poc"], r_val=r["r_val"],
                             attempt=r["attempt"], up_count=up_count,
                             n_known=len(known), stopped=r["stopped"],
                             hit_poc=r["hit_poc"]))
    T = pd.DataFrame(rows)
    if T.empty:
        print("no overlapping signals"); return

    print(f"\n=== BREADTH FILTER on the VA-fade short (target POC) — "
          f"{T.day.nunique()} days with leader data, {len(T)} signals ===")
    print(f"    breadthLen = {a.breadth_len} bars (~{a.breadth_len*5} min)\n")

    T3 = T[T.n_known == 3]
    print(f"signals where all 3 leaders were readable: {len(T3)}")
    print(f"up-count distribution: " +
          "  ".join(f"{k}:{int((T3.up_count==k).sum())}" for k in range(4)))

    print("\n-- filter split (all attempts, target POC) --")
    keep = T[T.up_count < 2]
    block = T[T.up_count >= 2]
    print(f"  KEEP  (leaders NOT rising, <2 up): {summ(keep.r_poc)}")
    print(f"  BLOCK (leaders rising, >=2 up)   : {summ(block.r_poc)}")
    delta = keep.r_poc.mean() - block.r_poc.mean() if len(keep) and len(block) else float('nan')
    print(f"  edge from filtering (KEEP-BLOCK)  : {delta:+.2f}R")

    print("\n-- filter split (>=2nd VAH attempt = the tested edge) --")
    T2 = T[T.attempt >= 2]
    k2, b2 = T2[T2.up_count < 2], T2[T2.up_count >= 2]
    print(f"  KEEP : {summ(k2.r_poc)}")
    print(f"  BLOCK: {summ(b2.r_poc)}")

    print("\n-- by exact up-count (all attempts, target POC) --")
    for k in range(4):
        print(f"  {k} leaders up: {summ(T[T.up_count==k].r_poc)}")

    print("\n-- interaction with gamma regime (POS gamma, target POC) --")
    P = T.dropna(subset=["net"])
    P = P[P.net > 0]
    print(f"  POS gamma KEEP : {summ(P[P.up_count<2].r_poc)}")
    print(f"  POS gamma BLOCK: {summ(P[P.up_count>=2].r_poc)}")

    print("\n-- unfiltered baseline (what we have today) --")
    print(f"  ALL signals    : {summ(T.r_poc)}")


if __name__ == "__main__":
    main()
