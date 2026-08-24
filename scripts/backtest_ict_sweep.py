#!/usr/bin/env python3
"""ICT / "Tempa" liquidity-sweep reversal — the mechanical core, tested.

The claim (from the video): in the 9:30-11:00 ET window, wait for a SWEEP of a
prior-day liquidity level (prior-day high/low), a reversal back through it, enter
on the reclaim (their FVG/IFVG trigger), target the opposite side / the 50%-of-
range midpoint. Premium/discount = only long sweeps of the low, short sweeps of
the high.

We mechanise the bread-and-butter version on QQQ 5-min RTH, ~2 years:
  * levels = prior RTH session High (PDH) and Low (PDL); mid = (PDH+PDL)/2.
  * LONG: in-window, price LOW dips below PDL (sweep), then a later bar CLOSES
    back above PDL (reclaim) -> enter long at that close. Stop = the sweep low.
    Targets: mid (T1) and PDH (T2).  SHORT = mirror at PDH.
  * one trade/day (first sweep-reclaim, either side).
  * "reclaim close beyond the level" is our objective proxy for the discretionary
    FVG-inversion entry (we already validated FVG continuation separately).

We report win rate / expectancy for target=mid and target=opposite, a fixed-2R
exit, the time-of-day effect (their 9:30-11:00 vs our skip-first-hour), and a
gamma-regime split.

Usage: python3 scripts/backtest_ict_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F          # load_sessions(), regime_map()
import backtest_range_breakout as BR  # gamma_reads / gamma_lookup

BUF = 0.0005     # stop buffer beyond the sweep extreme (0.05%)


def simulate(prev, cur, win_start, win_end):
    """One sweep-reclaim trade for session `cur`, levels from `prev`. Window is
    [win_start, win_end) ET as 'HH:MM'. Returns dict or None."""
    PDH = float(prev["high"].max()); PDL = float(prev["low"].min())
    mid = (PDH + PDL) / 2.0
    h, l, c = (cur[x].values for x in ("high", "low", "close"))
    idx = cur.index
    n = len(cur)
    swept_lo = swept_hi = False
    lo_ext = np.inf; hi_ext = -np.inf
    for i in range(n):
        t = idx[i].strftime("%H:%M")
        if t < win_start:
            continue
        if t >= win_end:
            break
        # track sweeps
        if l[i] < PDL:
            swept_lo = True; lo_ext = min(lo_ext, l[i])
        if h[i] > PDH:
            swept_hi = True; hi_ext = max(hi_ext, h[i])
        # LONG: swept the low, now reclaim (close back above PDL), in discount
        if swept_lo and c[i] > PDL and c[i] < mid:
            entry = c[i]; stop = lo_ext * (1 - BUF); risk = entry - stop
            if risk <= 0:
                continue
            return _mgmt(1, i, entry, stop, risk, mid, PDH, h, l, c, n, idx)
        # SHORT: swept the high, now reclaim (close back below PDH), in premium
        if swept_hi and c[i] < PDH and c[i] > mid:
            entry = c[i]; stop = hi_ext * (1 + BUF); risk = stop - entry
            if risk <= 0:
                continue
            return _mgmt(-1, i, entry, stop, risk, mid, PDL, h, l, c, n, idx)
    return None


def _mgmt(s, i, entry, stop, risk, mid, opp, h, l, c, n, idx):
    def favor(j): return h[j] if s > 0 else l[j]
    def adverse(j): return l[j] if s > 0 else h[j]
    hit_mid = hit_opp = stopped = False
    for j in range(i + 1, n):
        if (adverse(j) <= stop) if s > 0 else (adverse(j) >= stop):
            stopped = True; break
        if not hit_mid and ((favor(j) >= mid) if s > 0 else (favor(j) <= mid)):
            hit_mid = True
        if (favor(j) >= opp) if s > 0 else (favor(j) <= opp):
            hit_opp = True; break
    exit_c = c[n - 1]
    r_mid = (abs(mid - entry) / risk) if hit_mid else (-1 if stopped else s * (exit_c - entry) / risk)
    r_opp = (abs(opp - entry) / risk) if hit_opp else (-1 if stopped else s * (exit_c - entry) / risk)
    # fixed 2R
    tgt2 = entry + s * 2 * risk
    r_2 = np.nan
    for j in range(i + 1, n):
        if (adverse(j) <= stop) if s > 0 else (adverse(j) >= stop):
            r_2 = -1.0; break
        if (favor(j) >= tgt2) if s > 0 else (favor(j) <= tgt2):
            r_2 = 2.0; break
    if np.isnan(r_2):
        r_2 = s * (exit_c - entry) / risk
    return dict(dir=s, entry_i=i, hit_mid=hit_mid, hit_opp=hit_opp, stopped=stopped,
                r_mid=r_mid, r_opp=r_opp, r_2R=r_2, entry_ts=idx[i])


def summ(x, key):
    a = np.array([r[key] for r in x], float) if x else np.array([])
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    return f"n={len(a):4d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  t={t:+.2f}"


def run(days, sess, win_start, win_end, reads):
    rows = []
    for p, c in zip(days, days[1:]):
        r = simulate(sess[p], sess[c], win_start, win_end)
        if r:
            g = BR.gamma_lookup(reads, pd.Timestamp(c))
            r["net"] = g.get("net_gex") if g else None
            r["day"] = c
            rows.append(r)
    return rows


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    reads = BR.gamma_reads("QQQ")
    print(f"=== ICT/Tempa liquidity-sweep reversal — QQQ 5-min, {len(days)} sessions "
          f"{days[0].date()}..{days[-1].date()} ===")
    print("prior-day High/Low swept then reclaimed; long sweeps of low (discount), "
          "short sweeps of high (premium)\n")

    for label, ws, we in (("their window 09:30-11:00", "09:30", "11:00"),
                          ("our window 10:30-16:00 (skip 1st hr)", "10:30", "16:00"),
                          ("full RTH 09:30-16:00", "09:30", "16:00")):
        rows = run(days, sess, ws, we, reads)
        print(f"--- {label}: {len(rows)} trades ({len(rows)/len(days):.2f}/day) ---")
        print(f"   reach mid {100*np.mean([r['hit_mid'] for r in rows]):.0f}%  "
              f"reach opposite {100*np.mean([r['hit_opp'] for r in rows]):.0f}%  "
              f"stopped {100*np.mean([r['stopped'] for r in rows]):.0f}%" if rows else "   (none)")
        print(f"   target 50% mid : {summ(rows, 'r_mid')}")
        print(f"   target opposite: {summ(rows, 'r_opp')}")
        print(f"   fixed 2R       : {summ(rows, 'r_2R')}")
        if rows:
            G = [r for r in rows if r.get("net") is not None]
            pos = [r for r in G if r["net"] > 0]; neg = [r for r in G if r["net"] < 0]
            print(f"   [gamma] POS target mid: {summ(pos, 'r_mid')}")
            print(f"   [gamma] NEG target mid: {summ(neg, 'r_mid')}")
        print()


if __name__ == "__main__":
    main()
