#!/usr/bin/env python3
"""FAMILIES A, B and E: the price ladder, on a grid that can finally carry them.

All three are defined one tick apart and were therefore untestable on a
five-point grid, where one rung held twenty real prices.

    A  diagonal imbalance    buys at a price against sells one tick BELOW it
    B  stacked imbalance     three or more imbalanced prices in a row
    E  extreme absorption    one-sided volume at the bar's true high or low

A and B were classified never measured. E was killed, but on the coarse grid,
where "the bar's extreme price" was a five-point bucket and absorption at the
low shared a cell with continuation two points above it.

Definitions are exactly as pre-registered and the thresholds -- 3:1, ten
contracts, three in a row -- are the conventional footprint values, not
anything chosen from this data.

Scope: the explored-pile sessions at 0.25. Sealed dates are excluded when the
list is built, so there is no path by which one is read.

Usage: python3 scripts/orderflow/batch_ladder.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ic_harness import spearman                                           # noqa
from roster import split                                                  # noqa
from tape import load_all, price_step, rth, session_day                    # noqa

BAR_MIN = 5
HORIZON = 15
COST = 2.0
TICK = 0.25
RATIO = 3.0
MIN_VOL = 10
STACK = 3


def ladder_rows(s: pd.DataFrame, t0):
    """(bar, tick) -> buy, sell volume, on the real 0.25 grid."""
    bar = ((s.time - t0) // pd.Timedelta(minutes=BAR_MIN)).to_numpy()
    tick = np.rint(s.price.to_numpy() / TICK).astype(np.int64)
    vol = s.volume.to_numpy(np.float64)
    sgn = s["sign"].to_numpy()
    df = pd.DataFrame({"bar": bar, "tick": tick,
                       "buy": np.where(sgn > 0, vol, 0.0),
                       "sell": np.where(sgn < 0, vol, 0.0)})
    return df.groupby(["bar", "tick"], sort=True)[["buy", "sell"]].sum()


def shapes(lad):
    out = []
    for bar, g in lad.groupby(level=0):
        ticks = g.index.get_level_values(1).to_numpy()
        lo, hi = ticks[0], ticks[-1]
        n = hi - lo + 1
        if n < 4:
            continue
        buy = np.zeros(n); sell = np.zeros(n)
        buy[ticks - lo] = g.buy.to_numpy()
        sell[ticks - lo] = g.sell.to_numpy()
        tot = buy + sell
        v = tot.sum()
        if v <= 0:
            continue

        bimb = np.zeros(n, bool)
        bimb[1:] = (buy[1:] >= RATIO * np.maximum(sell[:-1], 1e-9)) & \
                   (buy[1:] >= MIN_VOL)
        simb = np.zeros(n, bool)
        simb[:-1] = (sell[:-1] >= RATIO * np.maximum(buy[1:], 1e-9)) & \
                    (sell[:-1] >= MIN_VOL)

        def longest(mask):
            best = run = 0
            for x in mask:
                run = run + 1 if x else 0
                best = max(best, run)
            return best
        bl, sl = longest(bimb), longest(simb)

        traded = int((tot > 0).sum())
        q = max(1, n // 4)
        top = int(bimb[-q:].sum()) - int(simb[-q:].sum())
        bot = int(bimb[:q].sum()) - int(simb[:q].sum())

        out.append(dict(
            bar=int(bar),
            A1=(int(bimb.sum()) - int(simb.sum())) / traded,
            A2=(top - bot) / traded,
            B1=float(bl >= STACK) - float(sl >= STACK),
            B2=float(bl - sl),
            E1=(buy[0] - sell[-1]) / v,
            E2=float(buy[0] > 0 and sell[0] > 0) -
               float(buy[-1] > 0 and sell[-1] > 0),
        ))
    return pd.DataFrame(out).set_index("bar")


def per_session():
    days = load_all()
    disc, hold, bad = split(days)
    out = {}
    for d in sorted(disc):
        if price_step(disc[d]) >= 1.0:
            continue
        s = rth(disc[d])
        if len(s) < 5000:
            continue
        t0 = session_day(s) + pd.Timedelta(hours=13, minutes=30)
        F = shapes(ladder_rows(s, t0))
        if F.empty or len(F) < 40:
            continue
        bar = ((s.time - t0) // pd.Timedelta(minutes=BAR_MIN))
        px = s.assign(bar=bar).groupby("bar").price.last()
        F = F.join(px.rename("px"), how="inner")
        k = max(1, HORIZON // BAR_MIN)
        F["fwd_pts"] = (F.px.shift(-k) / F.px - 1.0) * F.px
        out[d] = F.replace([np.inf, -np.inf], np.nan)
    return out


FEATS = {"A1": "diag imbalance", "A2": "diag at extremes",
         "B1": "stacked 3+", "B2": "stack run len",
         "E1": "absorb net", "E2": "unfinished net"}


def main():
    per = per_session()
    days = sorted(per)
    print("=" * 96)
    print("FAMILIES A, B, E — DIAGONAL, STACKED, EXTREME ABSORPTION")
    print("=" * 96)
    print(f"  sessions ({len(days)}): {' '.join(d[4:] for d in days)}")
    print(f"  resolution 0.25   bars {BAR_MIN}min   horizon {HORIZON}min")
    print(f"  {RATIO:.0f}:1 diagonal, >= {MIN_VOL} contracts, "
          f"{STACK}+ for a stack (pre-registered)\n")

    A = pd.concat([F.assign(day=d) for d, F in per.items()])
    print("  --- can the shapes form at all now? ---")
    print(f"  bars: {len(A):,}")
    print(f"  bars with any diagonal imbalance : "
          f"{100*(A.A1 != 0).mean():>5.1f}%")
    print(f"  bars with a 3+ stack             : "
          f"{100*(A.B1 != 0).mean():>5.1f}%   "
          f"(was 0.00% on the 5-point grid)")
    print(f"  longest run seen                 : {int(A.B2.abs().max())}\n")

    rng = np.random.default_rng(0)
    print(f"  {'feature':<10}{'':<20}{'IC':>10}{'t':>8}{'null t':>9}{'sess':>7}")
    rows = []
    for c, label in FEATS.items():
        ics, nulls = [], []
        for d, F in per.items():
            x = F[c].to_numpy(float); y = F.fwd_pts.to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 30 or np.nanstd(x[m]) == 0:
                continue
            ics.append(spearman(x[m], y[m]))
            k = int(rng.integers(5, max(6, m.sum() - 5)))
            nulls.append(spearman(x[m], np.roll(y[m], k)))
        ics = np.array([v for v in ics if np.isfinite(v)])
        nulls = np.array([v for v in nulls if np.isfinite(v)])
        if len(ics) < 5:
            print(f"  {c:<10}{label:<20}  too few sessions")
            continue
        t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
        nt = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls)))
        rows.append((c, t))
        print(f"  {c:<10}{label:<20}{ics.mean():>+10.4f}{t:>+8.2f}"
              f"{nt:>+9.2f}{len(ics):>7}")

    print(f"\n  bar: |t| >= 3.0.  clearing it: "
          f"{sum(1 for _, t in rows if abs(t) >= 3.0)} of {len(rows)}")

    print("\n  --- priced, top/bottom quintile, after cost ---")
    for c, label in FEATS.items():
        G = A.dropna(subset=[c, "fwd_pts"])
        if G[c].nunique() < 5:
            print(f"  {c:<10}{label:<20} too few distinct values to quintile")
            continue
        q = pd.qcut(G[c].rank(method="first"), 5, labels=False)
        lo, hi = G[q == 0], G[q == 4]
        pnl = np.concatenate([hi.fwd_pts.to_numpy(),
                              -lo.fwd_pts.to_numpy()]) - COST
        dd = np.concatenate([hi.day.to_numpy(), lo.day.to_numpy()])
        ses = pd.Series(pnl).groupby(dd).mean()
        tt = ses.mean() / (ses.std(ddof=1) / np.sqrt(len(ses)))
        print(f"  {c:<10}{label:<20}{pnl.mean():>+8.2f} pts  t {tt:>+5.2f}  "
              f"sessions positive {int((ses > 0).sum())}/{len(ses)}")


if __name__ == "__main__":
    main()
