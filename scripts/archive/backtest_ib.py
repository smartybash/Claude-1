"""Initial-Balance (60-min) break-and-hold backtest — Flow-Zone-Trader style.

Alex's one endorsed intraday trade: after the first hour's range (Initial
Balance) is set, price breaks it, PULLS BACK and HOLDS the IB edge, then
continues to a measured-move target. Honest, null-baselined test in the repo
style.

DEFINITION (pre-registered):
  * IB = the first 60 min of the RTH session (09:30-10:30 ET).
  * After 10:30, the first bar to CLOSE beyond an IB edge = the break.
  * HOLD confirmation: the very next bar must NOT close back inside the IB
    (acceptance). Entry at that confirmation bar's close.
  * Long on an upside break, short on a downside break.
  * Stop = the opposite IB edge (risk R = IB range). Symmetric outcome:
    reach +1R before -1R within the session = WIN. Expectancy also at the
    measured-move targets 1x / 1.5x / 2x the IB range (same 1R stop).
  * One trade per session (first confirmed break only). Resolves intraday.

NULL: identical break/hold/target mechanic anchored on a RANDOM intraday level
(a random post-10:30 bar's close as the "edge", same-width band) on the same
sessions. Isolates whether the IB structure adds anything over "break of some
level + acceptance".

Scope: NQ/ES/QQQ/SPY, 5-min and 30-min RTH windows (~1 month each) -> a real
but short, correlated-instrument sample. Costs/slippage not modelled.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ET = "America/New_York"
HOLD = 40          # max bars after entry to reach +1R/-1R
RNG = np.random.default_rng(20260805)

SERIES = [
    ("nq_5min_rth.json", "NQ", "5m"), ("es_5min_rth.json", "ES", "5m"),
    ("qqq_5min_rth.json", "QQQ", "5m"), ("spy_5min_rth.json", "SPY", "5m"),
    ("nq_30min.json", "NQ", "30m"), ("es_30min.json", "ES", "30m"),
    ("qqq_30min.json", "QQQ", "30m"), ("spy_30min.json", "SPY", "30m"),
]


def load(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def rth_sessions(df):
    t = df.index.time
    df = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]
    for d, g in df.groupby(df.index.date):
        yield g


def resolve(entry, stop, direction, hi, lo, i0, targets):
    """From bar i0 (entry bar), resolve win/loss at each target with a 1R stop."""
    risk = abs(entry - stop)
    out = {}
    for name, k in targets.items():
        tgt = entry + direction * k * risk
        stp = entry - direction * risk
        res = None
        for j in range(i0, min(i0 + HOLD, len(hi))):
            hit_stop = lo[j] <= stp if direction > 0 else hi[j] >= stp
            hit_tgt = hi[j] >= tgt if direction > 0 else lo[j] <= tgt
            if hit_stop:
                res = False; break
            if hit_tgt:
                res = True; break
        out[name] = res
    return out


def ib_trade(g, level_hi, level_lo, start_i):
    """Find first post-start break+hold of the [level_lo, level_hi] band; return
    (direction, entry_idx, entry_price, stop). Break = close beyond edge; hold =
    next bar closes still beyond. Stop = opposite edge."""
    o, h, l, c = (g[x].values for x in ("open", "high", "low", "close"))
    n = len(g)
    for i in range(start_i, n - 1):
        if c[i] > level_hi and c[i + 1] > level_hi:            # up break + hold
            return +1, i + 1, c[i + 1], level_lo
        if c[i] < level_lo and c[i + 1] < level_lo:            # down break + hold
            return -1, i + 1, c[i + 1], level_hi
    return None


def run(collect_null=True):
    targets = {"1R": 1.0, "1.5R": 1.5, "2R": 2.0}
    ev, nl = [], []
    for fname, inst, tf in SERIES:
        try:
            df = load(fname)
        except FileNotFoundError:
            continue
        ibn = 2 if tf == "30m" else 12          # bars in first 60 min
        for g in rth_sessions(df):
            g = g.reset_index(drop=True)
            if len(g) < ibn + 6:
                continue
            ib = g.iloc[:ibn]
            ib_hi, ib_lo = float(ib["high"].max()), float(ib["low"].min())
            if ib_hi <= ib_lo:
                continue
            hi, lo = g["high"].values, g["low"].values
            t = ib_trade(g, ib_hi, ib_lo, ibn)
            if t:
                d, i0, entry, stop = t
                r = resolve(entry, stop, d, hi, lo, i0, targets)
                ev.append({"dir": d, **r})
            # null: random level inside the day's post-IB range, same band width
            if collect_null:
                width = (ib_hi - ib_lo)
                post = g.iloc[ibn:]
                if len(post) > 5:
                    mid = float(RNG.uniform(post["low"].min() + width, post["high"].max() - width)) \
                        if post["high"].max() - post["low"].min() > 2 * width else float(post["close"].iloc[0])
                    t2 = ib_trade(g, mid + width / 2, mid - width / 2, ibn)
                    if t2:
                        d, i0, entry, stop = t2
                        r = resolve(entry, stop, d, hi, lo, i0, targets)
                        nl.append({"dir": d, **r})
    return ev, nl


def wr(events, key):
    v = [e[key] for e in events if e[key] is not None]
    return (sum(v) / len(v) if v else float("nan")), len(v)


def exp_r(events, key, k):
    if not events:
        return float("nan")
    tot = sum(k if e[key] is True else (-1.0 if e[key] is False else 0.0) for e in events)
    return tot / len(events)


def main():
    ev, nl = run()
    print("INITIAL-BALANCE (60-min) BREAK-AND-HOLD — pooled NQ/ES/QQQ/SPY (5m+30m RTH)")
    print("break = close beyond IB edge + next bar holds; stop = opposite edge (risk=IB range);")
    print("symmetric +1R-before--1R = win. NULL = same mechanic on a random intraday level.\n")
    p, n = wr(ev, "1R"); pn, nn = wr(nl, "1R")
    se = (p * (1 - p) / n) ** 0.5 if n else 0
    print(f"IB break-hold: win@1R {p:.0%} +/-{1.96*se:.0%} (n={n})   "
          f"E[R] @1R/1.5R/2R = {exp_r(ev,'1R',1):+.2f} / {exp_r(ev,'1.5R',1.5):+.2f} / {exp_r(ev,'2R',2):+.2f}")
    print(f"NULL (random level): win@1R {pn:.0%} (n={nn})   "
          f"E[R] @1R/1.5R/2R = {exp_r(nl,'1R',1):+.2f} / {exp_r(nl,'1.5R',1.5):+.2f} / {exp_r(nl,'2R',2):+.2f}")
    print(f"\nedge vs null (win@1R): {p-pn:+.0%}pts")
    # by direction
    for d, lab in ((1, "long"), (-1, "short")):
        g = [e for e in ev if e["dir"] == d]
        pp, gn = wr(g, "1R")
        if gn:
            print(f"  {lab:5s}: win@1R {pp:.0%} (n={gn})")
    best = max(exp_r(ev, "1R", 1), exp_r(ev, "1.5R", 1.5), exp_r(ev, "2R", 2))
    print("\nVERDICT:", "EDGE — worth a forward test" if (p - pn >= 0.05 and n >= 40 and best > 0.05)
          else "no clear edge vs the null on this sample")


if __name__ == "__main__":
    main()
