#!/usr/bin/env python3
"""VALUE-AREA FADE — the Flow-Zone setup, mechanised and tested.

The trade (user's spec, positive-gamma day):
  * price makes >=1-2 attempts at the PRIOR session's Value-Area High (VAH) —
    which on a positive-gamma day is also ~the call wall — and FAILS to hold
    above it -> SHORT the rejection.
  * targets: POC (T1) then VAL (T2). Stop just above VAH.
  * this is the range/fade playbook that positive gamma is supposed to reward.

Tested on QQQ 5-min RTH, ~2 years (data/intraday). Prior-session value area from
the volume profile (sweeplib.volume_profile, 70% VA). Gamma regime + call wall
from the prior option read (gex_history, carry-forward). No FVG/confluence
clutter — just: was price at VAH, did it reject, did it walk down to POC / VAL.

Usage: python3 scripts/backtest_va_fade.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from sweeplib.levels import volume_profile          # (POC, VAH, VAL)
import backtest_tos_fvg as F                         # load_sessions()
import backtest_range_breakout as BR                 # gamma_reads / gamma_lookup

TOL = 0.0006      # "at VAH" = within 0.06% of price
STOP_BUF = 0.0025  # stop = VAH * (1 + 0.25%)
SKIP_OPEN = "10:00"   # let the VA form / skip the first 30m noise


def prior_va(sessions, days, i):
    """Value area (poc, vah, val) of the session before days[i]."""
    if i == 0:
        return None
    prof = volume_profile(sessions[days[i - 1]], 50)
    if not prof:
        return None
    poc, vah, val = prof
    if not (val < poc < vah):
        return None
    return poc, vah, val


def simulate(b, vah, poc, val):
    """ONE trade per day: the FIRST VAH rejection after SKIP_OPEN. A 'distinct
    attempt' is a VAH tag separated from the previous one by price first pulling
    >=0.15% below VAH (so intraday chop at the level isn't over-counted). Returns
    a single-element list (or empty) with `attempt` = how many distinct pokes
    happened up to and including the entry."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    n = len(b)
    tol = TOL * vah
    entry_stop = vah * (1 + STOP_BUF)
    risk = entry_stop - vah
    attempts = 0
    armed = True                     # ready to count a fresh poke
    for i in range(n):
        if idx[i].strftime("%H:%M") < SKIP_OPEN:
            continue
        if l[i] < vah * (1 - 0.0015):   # pulled away -> re-arm for a new attempt
            armed = True
        tagged = h[i] >= vah - tol
        if tagged and armed:
            attempts += 1
            armed = False
            if c[i] < vah:               # rejection -> take the short here
                hit_poc = hit_val = stopped = False
                exit_c = c[n - 1]
                for j in range(i + 1, n):
                    if h[j] >= entry_stop:
                        stopped = True; break
                    if not hit_poc and l[j] <= poc:
                        hit_poc = True
                    if l[j] <= val:
                        hit_val = True; break
                r_poc = (vah - poc) / risk if hit_poc else (-1 if stopped else (vah - exit_c) / risk)
                r_val = (vah - val) / risk if hit_val else (-1 if stopped else (vah - exit_c) / risk)
                return [dict(attempt=attempts, hit_poc=hit_poc, hit_val=hit_val,
                             stopped=stopped, r_poc=r_poc, r_val=r_val)]
    return []


def summ(x, key):
    x = [r[key] for r in x]
    a = np.array(x, float)
    if len(a) == 0:
        return "n=0"
    return f"n={len(a):4d}  mean {a.mean():+.2f}R  win {100*(a>0).mean():3.0f}%"


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    reads = BR.gamma_reads("QQQ")
    rows = []
    for i, d in enumerate(days):
        va = prior_va(sess, days, i)
        if not va:
            continue
        poc, vah, val = va
        g = BR.gamma_lookup(reads, pd.Timestamp(d))
        net = g.get("net_gex") if g else None
        cw = g.get("call_wall") if g else None
        vah_at_cw = (cw is not None and abs(vah - cw) / vah < 0.004)
        b = sess[d]
        # only meaningful if the day actually opens below VAH (room to fade down)
        if float(b["open"].iloc[0]) > vah:
            continue
        for r in simulate(b, vah, poc, val):
            r.update(day=d, net=net, vah_at_cw=vah_at_cw)
            rows.append(r)
    T = pd.DataFrame(rows)
    if T.empty:
        print("no signals"); return

    print(f"=== VALUE-AREA FADE (short VAH -> POC/VAL) — QQQ 5-min, "
          f"{T.day.nunique()} days, {len(T)} attempts ===\n")

    def block(title, sub):
        if len(sub) == 0:
            print(f"{title}: n=0"); return
        pocR = summ(sub.to_dict('records'), 'r_poc')
        valR = summ(sub.to_dict('records'), 'r_val')
        print(f"{title}:")
        print(f"   reach POC {100*sub.hit_poc.mean():3.0f}%  reach VAL "
              f"{100*sub.hit_val.mean():3.0f}%  stopped {100*sub.stopped.mean():3.0f}%")
        print(f"   target POC -> {pocR}")
        print(f"   target VAL -> {valR}")

    block("ALL attempts", T)
    G = T.dropna(subset=["net"])
    if len(G):
        block("POSITIVE gamma (the intended regime)", G[G.net > 0])
        block("NEGATIVE gamma (should be worse)", G[G.net < 0])
    block("1st attempt at VAH", T[T.attempt == 1])
    block(">=2nd attempt (the '2 pokes then fail')", T[T.attempt >= 2])
    if "vah_at_cw" in T:
        block("POS gamma & VAH ~ call wall (the exact setup)",
              T[(T.net > 0) & (T.vah_at_cw)])


if __name__ == "__main__":
    main()
