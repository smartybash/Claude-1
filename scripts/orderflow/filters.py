#!/usr/bin/env python3
"""Would clusters, CVD or delta at the level improve the trade?

The honest answer so far has been "the filters I tested did not help", but the
ones tested were windowed: aggression in the sixty seconds before the touch,
volume in that window, tape speed. Three things ATAS puts on the screen were
NOT tested and are the obvious ones a trader would look at:

  1  SESSION CVD at the moment of touch. Not divergence at an extreme, which
     was tested and died, but the plain question: does fading with the day's
     cumulative delta behind you beat fading against it?

  2  DELTA AT THE LEVEL PRICE ITSELF, accumulated across the whole session.
     This is what a footprint column at that price shows. A level that has
     absorbed net selling all day is a different object from one that has
     absorbed net buying, and nothing so far has measured it.

  3  VOLUME AT THE LEVEL TODAY before the touch. The weight rule uses
     YESTERDAY's volume. Today's own volume at that price is a separate number
     and might say the level is already being worked.

Each is applied to the frozen rule's light-level trades, split into terciles,
and judged the same way everything else here is: the split has to survive per
session, and a filter that only helps in one bucket of one parameterisation is
noise.

A filter that does not separate is not a neutral addition. Every one of these
is a reason to override the rule in the moment, and an override that carries no
information is a way to talk yourself out of winners.

Usage: python3 scripts/orderflow/filters.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from level_weight import COST_PTS, STOP, TARGET, build                  # noqa
from sweep2 import trade                                                # noqa
from tape import load_all, rth                                          # noqa

POINT_USD = 20.0


def stat(v, minn=12):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if len(v) < minn:
        return None
    v = v - COST_PTS
    sd = v.std(ddof=1)
    return dict(n=len(v), mean=v.mean(), win=100 * (v > 0).mean(),
                t=v.mean() / (sd / np.sqrt(len(v))) if sd > 0 else 0.0)


def show(lbl, r):
    if r is None:
        print(f"    {lbl:<40} too few")
        return
    print(f"    {lbl:<40} n={r['n']:<4} {r['mean']:+7.2f}pt "
          f"{r['mean']*POINT_USD:+8.0f}$  win {r['win']:4.1f}%  t={r['t']:+5.2f}")


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]
    T = build(days, pairs).reset_index(drop=True)
    T = T[T.light].reset_index(drop=True)

    # --- the three features, all backward looking at the touch instant -------
    cvd, lvl_delta, lvl_vol_today, local_delta = [], [], [], []
    for _, r in T.iterrows():
        s = days[r.day]
        i = int(r.idx)
        past = s.iloc[:i]
        if len(past) < 200:
            cvd.append(np.nan); lvl_delta.append(np.nan)
            lvl_vol_today.append(np.nan); local_delta.append(np.nan)
            continue

        cvd.append(float(past.signed.sum()))

        near = past[(past.price - r.price).abs() <= 2.0]
        lvl_delta.append(float(near.signed.sum()))
        lvl_vol_today.append(float(near.volume.sum()))

        t0 = s.time.iloc[i] - pd.Timedelta(minutes=5)
        w = past[past.time >= t0]
        local_delta.append(float(w.signed.sum()))

    T["cvd"] = cvd
    T["lvl_delta"] = lvl_delta
    T["lvl_vol_today"] = lvl_vol_today
    T["local_delta"] = local_delta
    # Signed so positive always means "the flow agrees with the trade".
    # A buy wants selling to have been absorbed, so a negative delta helps it.
    sign = np.where(T.Buy if "Buy" in T else (T.from_above), 1.0, -1.0)
    T["cvd_with"] = -T.cvd * sign
    T["lvl_delta_with"] = -T.lvl_delta * sign
    T["local_with"] = -T.local_delta * sign

    base = trade(days, T, STOP, TARGET, True, np.ones(len(T), bool))
    print("=" * 84)
    print("DO ATAS'S OWN READS IMPROVE THE TRADE?")
    print("=" * 84)
    print(f"  the rule as it stands, light levels only, stop=target={STOP:.0f}")
    show("no filter at all", stat(base))
    print("\n  Each feature is signed so POSITIVE means the flow agrees with")
    print("  the trade the rule wants. If any of these carry information, the")
    print("  top tercile beats the bottom by more than noise.\n")

    for col, label in (("cvd_with", "session CVD behind the trade"),
                       ("lvl_delta_with", "delta AT the level, all session"),
                       ("local_with", "delta in the last 5 minutes"),
                       ("lvl_vol_today", "volume at the level TODAY")):
        v = T[col]
        if v.isna().all():
            continue
        try:
            q = pd.qcut(v.rank(method="first"), 3, labels=False)
        except ValueError:
            continue
        print(f"  --- {label} ---")
        means = []
        for i, tag in enumerate(("bottom third", "middle", "top third")):
            r = stat(trade(days, T, STOP, TARGET, True, (q == i).values))
            show(tag, r)
            means.append(r["mean"] if r else np.nan)
        spread = means[2] - means[0]
        print(f"    spread top minus bottom: {spread:+.2f}pt "
              f"{'— worth having' if abs(spread) > 6 else '— nothing'}\n")

    print("=" * 84)
    print("WHAT THIS MEANS FOR THE CHART")
    print("=" * 84)
    print("  A filter is only worth showing if acting on it beats not acting.")
    print("  Anything with a flat spread is a reason to override the rule that")
    print("  carries no information, which in practice means a way to skip the")
    print("  winners that look frightening.")


if __name__ == "__main__":
    main()
