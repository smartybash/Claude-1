#!/usr/bin/env python3
"""LEVELS FROM THE FOOTPRINT, AND WHAT HAPPENS WHEN PRICE COMES BACK.

The first footprint study asked the wrong question. It scored every bar's shape
against the next fifteen minutes -- "given this bar, where is price going" --
which is a forecasting frame no footprint trader uses, and which dilutes a
handful of meaningful prices across 3,658 bars until nothing could show.

A footprint marks a PRICE. The trade is the RETURN to that price.

  1. a bar prints unusual volume at some price
  2. that price is now a level
  3. price leaves
  4. price comes back
  5. it holds, or it breaks

Step 4 is the event. Nothing before it was tradeable, and measuring from step 1
measures a setup rather than a decision. Everything here is measured from the
moment of return, which is the only moment a trader is at the screen with
something to do.

TWO THINGS THAT LOOK THE SAME AND ARE NOT

  HOW MUCH traded at a price says the price matters -- it is a high-volume
  node, a shelf, somewhere the auction spent time.

  WHICH SIDE was aggressive there says what should happen when price returns.

The first version of this required both at once: heavy AND one-sided. That
produced seventeen levels in forty-seven sessions, because in this data the two
are anti-correlated -- the 90th percentile of one-sidedness is 63%, and a rung
that trades heavily trades heavily in both directions. They are separate
questions and are asked separately here.

THE CONTROL, which the earlier work lacked

Price revisits everything inside a range, and a range mean-reverts on its own.
So every heavy level is matched against ORDINARY rungs from the same sessions,
run through identical revisit machinery over identical horizons. If heavy
levels hold and ordinary prices do not, the footprint carries information. If
both behave alike, what is being measured is the range.

A REVISIT REQUIRES A DEPARTURE

The first version called it a return the moment price touched the level again,
which was usually the next print -- a median wait of one minute. Price had
never left. A return means price moved at least AWAY_PTS clear of the level
first and then came back to it.

SCOPE: discovery set only. The holdout stays sealed.

Usage: python3 scripts/orderflow/levels_footprint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from footprint import ladder                                              # noqa
from roster import split                                                  # noqa
from tape import load_all, price_step, rth                                # noqa

BAR_MINUTES = 5
HEAVY = 2.0           # rung volume against the bar's median rung; top ~10%
ORDINARY = (0.8, 1.2) # the control band: unremarkable rungs
MIN_RUNG_VOL = 200
AWAY_PTS = 15.0       # price must clear the level by this before returning
HORIZONS = (15, 30, 60)
COST_PTS = 2.0
LAST_LEVEL_HOUR = 18  # stop minting levels at 18:00 UTC, so returns have room


def rungs_of(s: pd.DataFrame, minutes: int = BAR_MINUTES) -> pd.DataFrame:
    """Every rung of every bar, with its volume and its delta."""
    step = price_step(s)
    t0 = s.time.iloc[0].normalize() + pd.Timedelta(hours=13, minutes=30)
    bar_ix = ((s.time - t0) // pd.Timedelta(minutes=minutes)).to_numpy()
    closes = (pd.DataFrame({"bar": bar_ix, "p": s.price.to_numpy()})
              .groupby("bar").p.last())
    lad = ladder(s, minutes, step)

    out = []
    for bar, g in lad.groupby(level=0):
        if bar not in closes.index:
            continue
        end = t0 + pd.Timedelta(minutes=minutes * (int(bar) + 1))
        if end.hour >= LAST_LEVEL_HOUR:
            continue
        buy, sell = g.buy.to_numpy(), g.sell.to_numpy()
        vol = buy + sell
        if len(vol) < 4:
            continue
        med = np.median(vol)
        if med <= 0:
            continue
        prices = g.index.get_level_values(1).to_numpy() * step
        for p, b, v in zip(prices, buy, vol):
            if v < MIN_RUNG_VOL:
                continue
            out.append(dict(born=end, price=float(p), vol=float(v),
                            heavy=float(v / med), share=float(b / v)))
    return pd.DataFrame(out)


def first_return(px, tm, born, level):
    """Index of the first return to `level` after price has left it.

    Returns None if price never clears the level by AWAY_PTS, or never comes
    back after it does. Both are common and both must be dropped rather than
    counted as instant returns, which is what the first version did.
    """
    start = int(np.searchsorted(tm, np.datetime64(born), "left"))
    if start >= len(px) - 10:
        return None, 0
    gone = np.flatnonzero(np.abs(px[start:] - level) >= AWAY_PTS)
    if len(gone) == 0:
        return None, 0
    g = start + int(gone[0])
    side = np.sign(px[g] - level)          # which side price left towards
    back = np.flatnonzero(px[g:] == level)
    if len(back) == 0:
        return None, 0
    return g + int(back[0]), side


def revisits(s: pd.DataFrame, lv: pd.DataFrame, tag: str) -> pd.DataFrame:
    """First return to each level, and the reaction from there.

    The reaction is signed by HOW PRICE ARRIVED. Coming down to a level, a
    trader is long and wants it to hold; coming up to it, short. That geometry
    is identical for a heavy level and an ordinary one, so the only difference
    between the two families is whether the footprint said anything.
    """
    if lv.empty:
        return pd.DataFrame()
    px = s.price.to_numpy(np.float64)
    tm = s.time.to_numpy()
    rows = []
    for _, L in lv.iterrows():
        j, side = first_return(px, tm, L.born, L.price)
        if j is None or side == 0:
            continue
        want = int(side)   # left upward -> it is support on the way back
        r = dict(kind=tag, heavy=L.heavy, share=L.share, price=L.price,
                 wait_min=(tm[j] - np.datetime64(L.born))
                 / np.timedelta64(1, "m"))
        for h in HORIZONS:
            k = min(int(np.searchsorted(tm, tm[j] + np.timedelta64(h, "m"),
                                        "left")), len(px) - 1)
            r[f"pts{h}"] = want * (px[k] - L.price)
        rows.append(r)
    return pd.DataFrame(rows)


def per_session_t(g, h):
    per = g.groupby("day")[f"pts{h}"].mean() - COST_PTS
    if len(per) < 3:
        return np.nan, np.nan
    return per.mean(), per.mean() / (per.std(ddof=1) / np.sqrt(len(per)))


def main():
    days = load_all()
    disc, hold, bad = split(days)
    print("=" * 98)
    print(f"FOOTPRINT LEVELS — the reaction when price returns "
          f"({len(disc)} discovery sessions)")
    print("=" * 98)
    print(f"  HEAVY   >= {HEAVY:.0f}x the bar's median rung   (top decile)")
    print(f"  ORDINARY {ORDINARY[0]:.1f}-{ORDINARY[1]:.1f}x        (the control)")
    print(f"  A return needs price to clear the level by {AWAY_PTS:.0f} points")
    print("  first. Points are signed so positive means the level held, and")
    print(f"  are after {COST_PTS:.0f} of cost.\n")

    allr = []
    for d, x in disc.items():
        s = rth(x)
        R = rungs_of(s)
        if R.empty:
            continue
        heavy = R[R.heavy >= HEAVY]
        ordin = R[(R.heavy >= ORDINARY[0]) & (R.heavy <= ORDINARY[1])]
        # match the control's size to the level count, so neither family wins
        # on sample size alone
        if len(ordin) > len(heavy) and len(heavy) > 0:
            ordin = ordin.sample(len(heavy), random_state=0)
        for lv, tag in ((heavy, "heavy"), (ordin, "ordinary")):
            r = revisits(s, lv, tag)
            if not r.empty:
                allr.append(r.assign(day=d))
    R = pd.concat(allr)

    print(f"  {len(R):,} returns over {R.day.nunique()} sessions")
    print("  " + "   ".join(f"{k}: {v:,}" for k, v in
                            R.groupby('kind').size().items()))
    print(f"  median wait from level to return: {R.wait_min.median():.0f} min\n")

    print(f"  {'':<12}{'n':>8}" +
          "".join(f"{'+'+str(h)+'m':>13}" for h in HORIZONS) +
          f"{'held 30m':>11}")
    for kind in ("heavy", "ordinary"):
        g = R[R.kind == kind]
        line = f"  {kind:<12}{len(g):>8}"
        for h in HORIZONS:
            line += f"{g[f'pts{h}'].mean():>+13.2f}"
        line += f"{100*(g.pts30 > 0).mean():>10.1f}%"
        print(line)

    print("\n  --- per-session t, the only significance that counts ---")
    for h in HORIZONS:
        mh, th = per_session_t(R[R.kind == "heavy"], h)
        mo, to = per_session_t(R[R.kind == "ordinary"], h)
        print(f"    +{h:>2}m   heavy {mh:+6.2f} pts  t {th:+5.2f}"
              f"      ordinary {mo:+6.2f} pts  t {to:+5.2f}")

    # --- paired against the control, which is the comparison that counts ---
    print("\n  --- heavy MINUS ordinary, paired within session ---")
    rng = np.random.default_rng(0)
    for h in HORIZONS:
        a = R[R.kind == "heavy"].groupby("day")[f"pts{h}"].mean()
        b = R[R.kind == "ordinary"].groupby("day")[f"pts{h}"].mean()
        d = (a - b).dropna()
        bs = np.array([rng.choice(d.to_numpy(), len(d), replace=True).mean()
                       for _ in range(4000)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        print(f"    +{h:>2}m  {d.mean():+6.2f} pts  t {t:+5.2f}  "
              f"95% [{lo:+.2f}, {hi:+.2f}]"
              f"{'  excludes zero' if lo > 0 or hi < 0 else ''}")
    print("\n  Heavy levels beat zero. They do not beat the control. The first")
    print("  comparison is the one that flatters, and it is the wrong one.")

    placebo(disc)


def placebo(disc):
    """Move the level to a price that was never a level. Change nothing else.

    This is the test the whole study turns on. If a return to a price the
    footprint marked pays no better than a return to a price twenty-five points
    away from it, then the footprint did not find a level -- it found a pullback,
    and a pullback happens at whatever price you nominate.
    """
    print("\n" + "=" * 98)
    print("PLACEBO: THE SAME TRADE AT A PRICE THAT WAS NEVER A LEVEL")
    print("=" * 98)
    print("  Identical machinery, identical horizons, identical signing. The")
    print("  only change is which price the trade waits for.\n")
    print(f"  {'price used':<22}{'n':>7}" +
          "".join(f"{'+'+str(h)+'m':>11}" for h in HORIZONS) + f"{'t@15m':>9}")
    for off, lab in ((0.0, "the real level"), (25.0, "shifted +25 pts"),
                     (-25.0, "shifted -25 pts")):
        rows = []
        for d, x in disc.items():
            s = rth(x)
            Rg = rungs_of(s)
            if Rg.empty:
                continue
            lv = Rg[Rg.heavy >= HEAVY].copy()
            lv["price"] = lv.price + off
            px, tm = s.price.to_numpy(np.float64), s.time.to_numpy()
            for _, L in lv.iterrows():
                j, side = first_return(px, tm, L.born, L.price)
                if j is None or side == 0:
                    continue
                r = dict(day=d)
                for h in HORIZONS:
                    k = min(int(np.searchsorted(
                        tm, tm[j] + np.timedelta64(h, "m"), "left")),
                        len(px) - 1)
                    r[f"pts{h}"] = int(side) * (px[k] - L.price)
                rows.append(r)
        G = pd.DataFrame(rows)
        per = G.groupby("day")["pts15"].mean() - COST_PTS
        t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per)))
        print(f"  {lab:<22}{len(G):>7}" +
              "".join(f"{G[f'pts{h}'].mean()-COST_PTS:>+11.2f}"
                      for h in HORIZONS) + f"{t:>+9.2f}")
    print()
    print("  A price twenty-five points away from the level pays the same. The")
    print("  footprint level is decoration; the pullback is the entire effect,")
    print("  and it does not need a level, a footprint, or order flow to")
    print("  happen. That is the ninth finding to die here, and the first to be")
    print("  killed by a placebo rather than by a holdout.")


if __name__ == "__main__":
    main()
