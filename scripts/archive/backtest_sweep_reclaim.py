"""Sweep-and-reclaim of structural levels — the OHLC skeleton of Alex's read.

His sweep-and-bounce is order flow (Bookmap liquidity + footprint absorption) we
can't see on bars. But the setup leaves an OHLC fingerprint: price WICKS beyond a
key level (the stop-run / sweep) and CLOSES back on the other side (the reclaim).
This tests whether that fingerprint ALONE — no footprint confirmation — pays.

DEFINITION (pre-registered):
  Levels (known pre-session, no lookahead) = prior RTH session's HIGH (PDH), LOW
  (PDL), and VPOC (highest-volume price of the prior session).
  poke = 0.05 * prior-session range (the wick must clear the level by this much).
  LONG  (support sweep): a bar's LOW <= level-poke AND that bar or the next CLOSES
        >= level. Entry = reclaim close. Stop = the sweep wick low. Long.
  SHORT (resistance sweep): mirror above PDH / VPOC.
  Outcome: symmetric +1R-before--1R within HOLD bars (R = |entry-stop|); also E[R]
  at 1R/1.5R/2R with the same stop; MOC if neither. One trade per (session,level,
  dir), first occurrence.

NULL: same 1R geometry entered LONG/SHORT at a RANDOM session bar with a matched
stop distance (median sweep risk). Isolates whether the sweep-reclaim STRUCTURE
beats a coin-flip entry with the same risk profile.

Scope: pooled NQ/ES/QQQ/SPY 5m + 30m RTH (~1 month each), correlated + short.
Costs not modelled. PnL in R.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backtest_ib import HOLD, load, resolve, rth_sessions

RNG = np.random.default_rng(20260806)
TARGETS = {"1R": 1.0, "1.5R": 1.5, "2R": 2.0}

SERIES = [
    ("nq_5min_rth.json", "5m"), ("es_5min_rth.json", "5m"),
    ("qqq_5min_rth.json", "5m"), ("spy_5min_rth.json", "5m"),
    ("nq_30min.json", "30m"), ("es_30min.json", "30m"),
    ("qqq_30min.json", "30m"), ("spy_30min.json", "30m"),
]


def vpoc_of(g: pd.DataFrame) -> float:
    """Highest-volume price of a session (rounded price bins)."""
    px = g["close"]
    step = max((g["high"].max() - g["low"].min()) / 30, 1e-9)
    b = (px / step).round() * step
    return float(b.groupby(b).apply(lambda idx: g.loc[idx.index, "volume"].sum()).idxmax()) \
        if len(g) else float(px.iloc[-1])


def sweep_reclaim(g, level, poke, direction):
    """First sweep+reclaim of `level`. direction +1 = support (poke below, reclaim
    up), -1 = resistance. Returns (entry_idx, entry_price, stop) or None."""
    lo, hi, c = g["low"].values, g["high"].values, g["close"].values
    n = len(g)
    for i in range(n - 1):
        if direction > 0 and lo[i] <= level - poke:          # swept below support
            if c[i] >= level:                                 # reclaimed same bar
                return i, c[i], lo[i]
            if c[i + 1] >= level:                             # reclaimed next bar
                return i + 1, c[i + 1], min(lo[i], lo[i + 1])
        if direction < 0 and hi[i] >= level + poke:          # swept above resistance
            if c[i] <= level:
                return i, c[i], hi[i]
            if c[i + 1] <= level:
                return i + 1, c[i + 1], max(hi[i], hi[i + 1])
    return None


def run():
    ev = {k: [] for k in ("PDL", "PDH", "VPOC")}
    risks = []          # sweep risk sizes (for the null's matched stop)
    null_sessions = []
    for fname, tf in SERIES:
        try:
            df = load(fname)
        except FileNotFoundError:
            continue
        sess = [g.reset_index(drop=True) for g in rth_sessions(df)]
        for k in range(1, len(sess)):
            prior, g = sess[k - 1], sess[k]
            if len(prior) < 5 or len(g) < 6:
                continue
            pdh, pdl = float(prior["high"].max()), float(prior["low"].min())
            vpoc = vpoc_of(prior)
            rng = pdh - pdl
            if rng <= 0:
                continue
            poke = 0.05 * rng
            hi, lo = g["high"].values, g["low"].values
            for label, level, d in [("PDL", pdl, +1), ("PDH", pdh, -1),
                                    ("VPOC", vpoc, +1 if g["close"].iloc[0] < vpoc else -1)]:
                t = sweep_reclaim(g, level, poke, d)
                if not t:
                    continue
                i0, entry, stop = t
                if abs(entry - stop) < 1e-9:
                    continue
                r = resolve(entry, stop, d, hi, lo, i0, TARGETS)
                ev[label].append({"dir": d, **r})
                risks.append(abs(entry - stop))
            null_sessions.append((g, rng))

    # NULL: random-bar entry, matched stop distance = median sweep risk
    med_risk = float(np.median(risks)) if risks else 0.0
    nl = []
    for g, rng in null_sessions:
        hi, lo, c = g["high"].values, g["low"].values, g["close"].values
        n = len(g)
        if n < 6 or med_risk <= 0:
            continue
        i0 = int(RNG.integers(1, n - 2))
        d = 1 if RNG.random() < 0.5 else -1
        entry = c[i0]; stop = entry - d * med_risk
        nl.append({"dir": d, **resolve(entry, stop, d, hi, lo, i0, TARGETS)})
    return ev, nl


def wr(events, key="1R"):
    v = [e[key] for e in events if e[key] is not None]
    return (sum(v) / len(v) if v else float("nan")), len(v)


def exp_r(events, key, k):
    if not events:
        return float("nan")
    tot = sum(k if e[key] is True else (-1.0 if e[key] is False else 0.0) for e in events)
    return tot / len(events)


def line(name, ev):
    p, n = wr(ev)
    if n == 0:
        print(f"  {name:12s} n=0"); return
    se = (p * (1 - p) / n) ** 0.5
    print(f"  {name:12s} win@1R {p:.0%} +/-{1.96*se:.0%} (n={n:>3})  "
          f"E[R] 1R/1.5R/2R = {exp_r(ev,'1R',1):+.2f} / {exp_r(ev,'1.5R',1.5):+.2f} / {exp_r(ev,'2R',2):+.2f}")


def main():
    ev, nl = run()
    allev = ev["PDL"] + ev["PDH"] + ev["VPOC"]
    print("SWEEP-AND-RECLAIM of structural levels — pooled NQ/ES/QQQ/SPY (5m+30m RTH)")
    print("wick beyond level by 0.05*prior-range + close back across = entry; stop = wick;")
    print("symmetric +1R-before--1R. NULL = random-bar entry, matched stop.\n")
    line("ALL levels", allev)
    for k in ("PDL", "PDH", "VPOC"):
        line(k, ev[k])
    line("NULL(random)", nl)
    p, n = wr(allev); pn, _ = wr(nl)
    print(f"\nedge vs null (win@1R): {p-pn:+.0%}pts   best E[R] = "
          f"{max(exp_r(allev,'1R',1), exp_r(allev,'1.5R',1.5), exp_r(allev,'2R',2)):+.2f}")
    print("VERDICT:", "SIGNAL — worth the ToS trigger + a forward test"
          if (not np.isnan(p) and not np.isnan(pn) and p - pn >= 0.05 and n >= 40
              and max(exp_r(allev,'1R',1), exp_r(allev,'1.5R',1.5), exp_r(allev,'2R',2)) > 0.05)
          else "weak / no clear edge over the null on this sample (structure alone; needs order-flow confirm)")


if __name__ == "__main__":
    main()
