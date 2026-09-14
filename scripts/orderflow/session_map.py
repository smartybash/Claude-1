#!/usr/bin/env python3
"""Per-session structure from the tick tape: profile, IB, CVD, and the levels.

Everything here is built from actual traded volume at price rather than from
bar highs and lows, which is the one real upgrade the recording bought. A
5-minute bar says the session traded between two prices; the tape says how many
contracts changed hands at each of them, and which side was the aggressor.

Times are UTC, which is what the recorder writes. RTH is 13:30-20:00.

Usage: python3 scripts/session_map.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tape import (IB_END, RTH_CLOSE, RTH_OPEN, _at, load_all, rth,
                  volume_profile)


def cvd(df: pd.DataFrame) -> pd.Series:
    """Cumulative volume delta, reset at the cash open.

    The reset matters: a CVD carried through the overnight session measures a
    different, thinner market and buries the RTH signal under a constant.
    """
    return pd.Series(df.signed.cumsum().to_numpy(), index=df.time)


def describe(date: str, full: pd.DataFrame) -> dict:
    s = rth(full)
    if len(s) < 5000:
        print(f"  {date}: only {len(s)} RTH trades, skipping")
        return {}

    p = volume_profile(s)
    ib = s[s.time < _at(s.time.iloc[0], IB_END)]
    c = cvd(s)

    o, cl = s.price.iloc[0], s.price.iloc[-1]
    hi, lo = s.price.max(), s.price.min()

    print(f"\n  {date[:4]}-{date[4:6]}-{date[6:]}   "
          f"{len(s):,} RTH trades, {s.volume.sum():,} contracts")
    print(f"     open {o:>9,.0f}   close {cl:>9,.0f}   "
          f"{cl - o:+.0f} pts   range {hi - lo:.0f}")
    print(f"     VAH  {p['vah']:>9,.0f}   POC   {p['poc']:>9,.0f}   "
          f"VAL {p['val']:,.0f}    (width {p['vah'] - p['val']:.0f} pts)")
    print(f"     IB   {ib.price.min():,.0f} to {ib.price.max():,.0f}   "
          f"({ib.price.max() - ib.price.min():.0f} pts, "
          f"{100 * ib.volume.sum() / s.volume.sum():.0f}% of RTH volume)")
    print(f"     CVD  close {c.iloc[-1]:+,.0f}   "
          f"high {c.max():+,.0f}   low {c.min():+,.0f}")

    # Where the aggression actually was, by price. A level that absorbed heavy
    # selling and held is the thing worth finding, and it is invisible on bars.
    g = s.groupby("price").agg(vol=("volume", "sum"), dlt=("signed", "sum"))
    g = g.sort_values("vol", ascending=False).head(6)
    print("     heaviest prices        volume     delta")
    for price, row in g.iterrows():
        tag = "  <- POC" if price == p["poc"] else ""
        print(f"        {price:>9,.0f}   {int(row.vol):>9,}  {int(row.dlt):>+8,}{tag}")

    return dict(date=date, poc=p["poc"], vah=p["vah"], val=p["val"],
                high=hi, low=lo, close=cl, open=o,
                ib_high=ib.price.max(), ib_low=ib.price.min())


def main():
    days = load_all()
    print("=" * 78)
    print("RTH SESSION MAP  (13:30-20:00 UTC = 09:30-16:00 New York)")
    print("=" * 78)

    out = [describe(d, df) for d, df in sorted(days.items())]
    out = [r for r in out if r]

    if len(out) < 2:
        return
    print("\n" + "=" * 78)
    print("LEVELS CARRIED FORWARD")
    print("=" * 78)
    print("  Each session's profile becomes the next session's fixed levels.")
    print("  These are known before the open and do not move, which is the")
    print("  only kind of level worth trading against.\n")
    for prev, nxt in zip(out, out[1:]):
        print(f"  into {nxt['date']}, from {prev['date']}:")
        for k, lbl in (("vah", "pdVAH"), ("poc", "pdPOC"), ("val", "pdVAL"),
                       ("high", "pdHIGH"), ("low", "pdLOW")):
            lv = prev[k]
            touched = nxt["low"] <= lv <= nxt["high"]
            print(f"     {lbl:<7} {lv:>9,.0f}   "
                  f"{'TOUCHED' if touched else 'not reached'}")


if __name__ == "__main__":
    main()
