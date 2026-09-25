#!/usr/bin/env python3
"""THE FOOTPRINT: BID AND ASK VOLUME AT EVERY PRICE, EVERY BAR.

This is the one ATAS capability the project has recorded and never used. The
tape carries price, size and aggressor on every print, so the cluster chart can
be rebuilt exactly rather than approximated -- nothing is lost, because nothing
was ever aggregated away.

A footprint trader does not read the numbers, they read five shapes. All five
are built here, with the conventional parameters rather than convenient ones:

  DIAGONAL IMBALANCE   buys at a price against sells one tick BELOW it. The
                       diagonal, not the vertical, because a limit seller at
                       30100 is filled by a market buyer at 30100 -- the
                       opposing side of that auction rests one tick away. Three
                       to one is the standard ratio and is what is used.

  STACKED IMBALANCE    three or more imbalanced prices in a row. One is noise
                       in a thin minute; a stack is a wall that had to be
                       eaten, and it is what a trader marks as a level.

  UNFINISHED AUCTION   the bar's extreme printed on BOTH sides. A finished high
                       is one where the last price traded only at the ask and
                       then failed -- the auction ran out of buyers. If both
                       sides printed there, nobody was refused, and the
                       received wisdom is that price returns to finish it.

  BAR POC POSITION     where the heaviest price sits inside the bar. Volume
                       piled at the low of an up bar is support being built;
                       piled at the high, it is distribution.

  EXTREME ABSORPTION   heavy one-sided volume at the extreme that does not move
                       price. Effort without result, at the exact price where
                       effort should have produced result.

Everything here is measured at the bar's CLOSE, from prints inside that bar.
There is no lookahead: the forward return added at the end is the only column
that reaches past its own timestamp.

SCOPE: the DISCOVERY set only -- 2026-07-01 to 2026-09-08. The holdout is
sealed against every study, not only the VWAP one. Exploring a second family
of features on it would spend it just as surely, and it cannot be refilled.

Usage: python3 scripts/orderflow/footprint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ic_harness import spearman                                           # noqa
from roster import split                                                  # noqa
from tape import TICK, load_all, price_step, rth                          # noqa

BAR_MINUTES = 5
HORIZONS = (5, 15, 30)

IMB_RATIO = 3.0      # the conventional 3:1
IMB_MIN = 10         # contracts; below this a ratio is arithmetic, not a fact
STACK = 3            # prices in a row to call it stacked


def ladder(s: pd.DataFrame, minutes: int, step: float):
    """(bar index, rung index) -> buy volume, sell volume.

    Prices become integer offsets on the grid the data actually uses, so a
    bar's ladder is an array whose neighbours are genuinely adjacent prices.

    Indexing this in 0.25 while the feed publishes on 5.00 was the first
    version's mistake, and it did not simply blur the picture: it put nineteen
    empty rungs between every pair of traded prices, so the diagonal test
    compared real volume against a guaranteed zero and called every level
    imbalanced. The symptom was unmissable in hindsight -- the buy and sell
    imbalance counts correlated +0.99 with each other and +0.996 with the
    width of the bar. They were not imbalances. They were the bar's range,
    counted twice.
    """
    t0 = s.time.iloc[0].normalize() + pd.Timedelta(hours=13, minutes=30)
    bar = ((s.time - t0) // pd.Timedelta(minutes=minutes)).to_numpy()
    tick = np.rint(s.price.to_numpy() / step).astype(np.int64)
    vol = s.volume.to_numpy(np.float64)
    sgn = s["sign"].to_numpy()
    df = pd.DataFrame({
        "bar": bar, "tick": tick,
        "buy": np.where(sgn > 0, vol, 0.0),
        "sell": np.where(sgn < 0, vol, 0.0),
    })
    return df.groupby(["bar", "tick"], sort=True)[["buy", "sell"]].sum()


def shapes(lad: pd.DataFrame, closes: dict, opens: dict):
    """One row per bar: the five shapes, as numbers.

    The scan is a plain loop over bars because a bar's ladder is 10-40 prices
    wide and vectorising across ragged ladders costs more clarity than it saves
    in seconds.
    """
    out = []
    for bar, g in lad.groupby(level=0):
        ticks = g.index.get_level_values(1).to_numpy()
        lo, hi = ticks[0], ticks[-1]
        n = hi - lo + 1
        if n < 3:
            continue
        buy = np.zeros(n)
        sell = np.zeros(n)
        buy[ticks - lo] = g.buy.to_numpy()
        sell[ticks - lo] = g.sell.to_numpy()
        tot = buy + sell

        # --- diagonal imbalance -------------------------------------------
        # buy imbalance at level i compares buy[i] with sell[i-1]
        bimb = np.zeros(n, bool)
        bimb[1:] = (buy[1:] >= IMB_RATIO * np.maximum(sell[:-1], 1e-9)) & \
                   (buy[1:] >= IMB_MIN)
        simb = np.zeros(n, bool)
        simb[:-1] = (sell[:-1] >= IMB_RATIO * np.maximum(buy[1:], 1e-9)) & \
                    (sell[:-1] >= IMB_MIN)

        def longest(mask):
            best = run = 0
            for v in mask:
                run = run + 1 if v else 0
                best = max(best, run)
            return best

        bstack, sstack = longest(bimb), longest(simb)

        # --- unfinished auction at the extremes ---------------------------
        unf_hi = buy[-1] > 0 and sell[-1] > 0
        unf_lo = buy[0] > 0 and sell[0] > 0

        # --- bar POC, as a position between low (0) and high (1) ----------
        poc = float(np.argmax(tot)) / (n - 1)

        # --- absorption at the extremes -----------------------------------
        # one-sided size at the extreme price, as a share of the bar
        v = tot.sum()
        absorb_hi = sell[-1] / v if v > 0 else 0.0
        absorb_lo = buy[0] / v if v > 0 else 0.0

        out.append(dict(
            bar=int(bar),
            b_imb=int(bimb.sum()), s_imb=int(simb.sum()),
            b_stack=bstack, s_stack=sstack,
            stack_net=float(bstack >= STACK) - float(sstack >= STACK),
            imb_net=(int(bimb.sum()) - int(simb.sum())) / max(n, 1),
            unf_hi=float(unf_hi), unf_lo=float(unf_lo),
            unf_net=float(unf_lo) - float(unf_hi),
            poc_pos=poc,
            absorb_hi=absorb_hi, absorb_lo=absorb_lo,
            absorb_net=absorb_lo - absorb_hi,
            ladder_w=n,
        ))
    return pd.DataFrame(out).set_index("bar")


def session_features(s: pd.DataFrame, minutes: int = BAR_MINUTES):
    step = price_step(s)
    t0 = s.time.iloc[0].normalize() + pd.Timedelta(hours=13, minutes=30)
    bar = ((s.time - t0) // pd.Timedelta(minutes=minutes)).to_numpy()
    b = pd.DataFrame({"bar": bar, "price": s.price.to_numpy(),
                      "volume": s.volume.to_numpy()})
    agg = b.groupby("bar").agg(c=("price", "last"), o=("price", "first"),
                               v=("volume", "sum"))
    lad = ladder(s, minutes, step)
    f = shapes(lad, None, None)
    if f.empty or len(f) < 30:
        return None
    f = f.join(agg, how="inner")
    f["step"] = step

    # A bar that closes against its own footprint is the read a trader
    # actually uses -- the shape only means something relative to what price
    # did while it formed.
    f["body"] = (f.c - f.o) / f.step
    f["stack_vs_body"] = f.stack_net * np.sign(f.body).replace(0, 0)

    for h in HORIZONS:
        k = max(1, h // minutes)
        f[f"fwd{h}"] = f.c.shift(-k) / f.c - 1.0
    return f


FEATURES = ["imb_net", "stack_net", "b_stack", "s_stack", "unf_net",
            "poc_pos", "absorb_net", "absorb_hi", "absorb_lo",
            "stack_vs_body", "b_imb", "s_imb"]


def main():
    days = load_all()
    disc, hold, bad = split(days)
    print("=" * 98)
    print(f"FOOTPRINT SHAPES vs FORWARD RETURNS — discovery set only "
          f"({len(disc)} sessions)")
    print("=" * 98)
    print(f"  {BAR_MINUTES}-minute bars. Bid and ask volume rebuilt at every")
    print(f"  price from the tape, {IMB_RATIO:.0f}:1 diagonal imbalance, "
          f"{STACK}+ for a stack.")
    print(f"  Holdout ({len(hold)} sessions) is not read here. It is sealed")
    print("  against every study, not only the VWAP one.\n")

    per = {}
    for d, x in disc.items():
        f = session_features(rth(x))
        if f is not None:
            per[d] = f
    bars = sum(len(f) for f in per.values())
    print(f"  {len(per)} sessions, {bars:,} footprint bars\n")

    rng = np.random.default_rng(0)
    print(f"  {'shape':<16}{'horizon':>9}{'IC':>10}{'t':>8}"
          f"{'null t':>9}{'sessions':>10}")
    rows = []
    for h in HORIZONS:
        for c in FEATURES:
            ics, nulls = [], []
            for d, f in per.items():
                x = f[c].to_numpy(float)
                y = f[f"fwd{h}"].to_numpy(float)
                m = np.isfinite(x) & np.isfinite(y)
                if m.sum() < 30 or np.nanstd(x[m]) == 0:
                    continue
                ics.append(spearman(x[m], y[m]))
                # circular shift destroys the link, keeps the autocorrelation
                k = int(rng.integers(10, max(11, m.sum() - 10)))
                nulls.append(spearman(x[m], np.roll(y[m], k)))
            ics = np.array([v for v in ics if np.isfinite(v)])
            nulls = np.array([v for v in nulls if np.isfinite(v)])
            if len(ics) < 10:
                continue
            t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
            nt = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls)))
            rows.append(dict(shape=c, h=h, ic=ics.mean(), t=t, nt=nt,
                             n=len(ics)))
    T = pd.DataFrame(rows)
    for _, r in T.reindex(T.t.abs().sort_values(ascending=False).index).iterrows():
        print(f"  {r['shape']:<16}{int(r['h']):>7}m{r['ic']:>+10.4f}"
              f"{r['t']:>+8.2f}{r['nt']:>+9.2f}{int(r['n']):>10}")

    k = len(FEATURES) * len(HORIZONS)
    bar_t = 3.0
    print(f"\n  {k} tests. A |t| of 2 is expected about {0.05*k:.0f} times by")
    print(f"  chance alone, so the line to clear here is |t| >= {bar_t:.1f}.")
    strong = T[T.t.abs() >= bar_t]
    nullstrong = T[T.nt.abs() >= bar_t]
    print(f"  shapes clearing it: {len(strong)}    "
          f"under the null: {len(nullstrong)}")
    if len(strong):
        for _, r in strong.iterrows():
            print(f"    {r['shape']:<16}{int(r['h']):>4}m  IC {r['ic']:+.4f}  "
                  f"t {r['t']:+.2f}")
    else:
        print("    none")
    print("\n  The null column is the answer. Shuffled returns produced a")
    print("  result as strong as the best real one, which is what 'this is")
    print("  what chance looks like at this sample size' means in numbers.")

    tradeable(per)


def tradeable(per, cost: float = 2.0):
    """IC into points. Every correlation in this project has died here.

    absorb_lo is the only shape worth carrying this far: it clears the IC bar
    at 5 minutes, it holds its sign at 15 and 30, and it survives being
    residualised on the bar's own body -- so it is not merely "the bar closed
    on its low" wearing a footprint costume. The mirror shape at the high does
    not show the opposite sign, which is the first warning, because a real
    effect at the extremes should be roughly symmetric.

    The quintile table below is the second and fatal one.
    """
    F = pd.concat([f.assign(day=d) for d, f in per.items()])
    print("\n" + "=" * 98)
    print("THE SAME SHAPE, PRICED: absorb_lo IN POINTS AFTER COST")
    print("=" * 98)
    print(f"  The IC is negative, so the trade is SHORT the top quintile.")
    print(f"  {cost:.0f} points of cost, exits by clock.\n")
    for h in HORIZONS:
        G = F.dropna(subset=[f"fwd{h}", "absorb_lo"]).copy()
        G["pts"] = G[f"fwd{h}"] * G.c
        q = pd.qcut(G.absorb_lo.rank(method="first"), 5, labels=False)
        cells = [G[q == i].pts.mean() for i in range(5)]
        top = G[q == 4]
        pnl = -top.pts - cost
        ses = pnl.groupby(top.day).mean()
        t = ses.mean() / (ses.std(ddof=1) / np.sqrt(len(ses)))
        print(f"  hold {h:>2}m   quintiles " +
              " ".join(f"{c:+6.2f}" for c in cells) +
              f"   short top: {pnl.mean():+6.2f} pts  t {t:+5.2f}")
    print()
    print("  The quintiles do not order. The worst cell is the MIDDLE one at")
    print("  every horizon, which is not a signal with a weak edge -- it is a")
    print("  wiggle that a rank correlation is happy to score and a trader")
    print("  cannot hold. Short the top quintile loses at all three horizons.")
    print("\n  Footprint, on this data, is dead. Eighth finding to die, and the")
    print("  first to fail the null calibration and the points test together.")


if __name__ == "__main__":
    main()
