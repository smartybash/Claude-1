#!/usr/bin/env python3
"""THE LEVEL RULES, re-opened on 1,421 sessions of 1-minute bars.

These were rejected on 198 touches and 51 out-of-sample trades. That sample
was what existed at the time; it is not what exists now. Every claim that can
be rebuilt from price and volume alone is re-tested here at roughly twenty
times the size, with the same de-overlapping and the same controls.

What is being re-opened:

    do levels hold?      the original 53-56% of touches, measured on 198
    heavy levels break   fading a level carrying 10,000+ contracts lost 12
                         points a trade at 33% -- the claim that half the
                         split has a mechanism behind it
    the fade trade       enter at the level, stop and target both 30 NQ points

What CANNOT be re-opened here, and why: everything needing the aggressor side
of each trade -- the CVD filter, CVD divergence, absorption, book imbalance.
cvd_proxy.py tests whether bars can stand in for CVD and the answer is no
(path correlation 0.33, wrong sign on 4 of 18 sessions). Those rules stay
where they are, tested on the tape sessions and nothing more, and no amount
of bar data changes that.

Levels are built from the PREVIOUS session only, so every level is known
before the session it is traded in:

    POC / VAH / VAL   volume profile of the prior cash session, each bar's
                      volume spread across its own range rather than dumped
                      on the close
    PDH / PDL / PDC   prior high, low, close

Prices are QQQ; stops and targets are converted from NQ points at the day's
own price, so a 30-point NQ stop stays a 30-point NQ stop across five years
of a quadrupling index rather than drifting into a different trade.

Usage: python3 scripts/orderflow/levels_long.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BARS = Path(__file__).resolve().parents[2] / "data" / "intraday_long" / "QQQ_1m.parquet"

NQ_PRICE = 29_400.0
STOP_NQ = 30.0          # frozen from the original work
TARGET_NQ = 30.0
COST_NQ = 2.0
BAND_NQ = 2.0           # how close counts as a touch
BUCKET_NQ = 2.0         # volume-profile resolution
VALUE_AREA = 0.70


def sessions() -> dict:
    d = pd.read_parquet(BARS).sort_values("timestamp").reset_index(drop=True)
    d = d.rename(columns={"open": "o", "high": "h", "low": "l",
                          "close": "c", "volume": "v"})
    d["day"] = d.timestamp.dt.date
    return {day: g.reset_index(drop=True)
            for day, g in d.groupby("day", sort=True) if len(g) >= 300}


def profile(b: pd.DataFrame, bucket: float):
    """Volume by price, spreading each bar's volume across its own range.

    Assigning a bar's whole volume to its close puts a minute's trade on one
    price it may barely have touched. Spreading it over the range is the
    standard approximation and is what makes a POC from bars resemble a POC
    from the tape.
    """
    lo, hi, v = b.l.to_numpy(), b.h.to_numpy(), b.v.to_numpy()
    base = np.floor(lo.min() / bucket) * bucket
    n = int(np.ceil((hi.max() - base) / bucket)) + 1
    acc = np.zeros(n)
    i0 = np.floor((lo - base) / bucket).astype(int)
    i1 = np.floor((hi - base) / bucket).astype(int)
    for a, z, vol in zip(i0, i1, v):
        span = z - a + 1
        acc[a:z + 1] += vol / span
    price = base + (np.arange(n) + 0.5) * bucket
    return price, acc


def value_area(price, acc, frac=VALUE_AREA):
    """POC, then expand to the higher-volume neighbour until frac is covered."""
    poc = int(acc.argmax())
    lo = hi = poc
    have, want = acc[poc], acc.sum() * frac
    while have < want and (lo > 0 or hi < len(acc) - 1):
        up = acc[hi + 1] if hi < len(acc) - 1 else -1
        dn = acc[lo - 1] if lo > 0 else -1
        if up >= dn:
            hi += 1
            have += up
        else:
            lo -= 1
            have += dn
    return price[poc], price[hi], price[lo]


def levels_from(prev: pd.DataFrame, bucket: float):
    price, acc = profile(prev, bucket)
    poc, vah, val = value_area(price, acc)
    out = {
        "POC": poc, "VAH": vah, "VAL": val,
        "PDH": float(prev.h.max()), "PDL": float(prev.l.min()),
        "PDC": float(prev.c.iloc[-1]),
    }
    # weight: volume that traded within the band of each level yesterday
    wt = {}
    for k, p in out.items():
        m = (price >= p - bucket) & (price <= p + bucket)
        wt[k] = float(acc[m].sum())
    return out, wt


def first_touches(b: pd.DataFrame, lv: dict, band: float):
    """The first bar each level is touched, and which side price came from."""
    H, L, O = b.h.to_numpy(), b.l.to_numpy(), b.o.to_numpy()
    open_px = float(O[0])
    hits = []
    for name, p in lv.items():
        inside = (L <= p + band) & (H >= p - band)
        idx = np.flatnonzero(inside)
        if len(idx) == 0 or idx[0] == 0:
            continue                      # no touch, or gapped onto it
        i = int(idx[0])
        hits.append(dict(name=name, price=p, i=i, from_above=open_px > p))
    return hits


def walk(b, i, entry, stop, target, up):
    """Forward from bar i+1. A bar touching both is a loss, and flagged."""
    H, L, C = b.h.to_numpy(), b.l.to_numpy(), b.c.to_numpy()
    for k in range(i + 1, len(b)):
        if up:
            s, t = L[k] <= stop, H[k] >= target
        else:
            s, t = H[k] >= stop, L[k] <= target
        if s and t:
            return -abs(entry - stop), True
        if s:
            return -abs(entry - stop), False
        if t:
            return abs(target - entry), False
    return ((C[-1] - entry) if up else (entry - C[-1])), False


def stat(rows, label, key="nq"):
    if len(rows) < 15:
        print(f"    {label:<44} n={len(rows):<5} too few")
        return None
    x = np.array([r[key] for r in rows], float)
    ak = "gamb" if key == "go" else "amb"
    sd = x.std(ddof=1)
    t = x.mean() / (sd / np.sqrt(len(x))) if sd > 0 else 0.0
    amb = 100 * np.mean([r[ak] for r in rows])
    print(f"    {label:<44} n={len(x):<5} {x.mean():+7.2f} NQ pts  "
          f"win {100*(x > 0).mean():4.1f}%  t={t:+5.2f}  amb {amb:3.0f}%")
    return dict(n=len(x), mean=x.mean(), t=t, win=100 * (x > 0).mean())


def main():
    days = sessions()
    keys = sorted(days)
    print("=" * 100)
    print(f"THE LEVEL RULES — {len(keys):,} sessions, {keys[0]} to {keys[-1]}, "
          f"1-minute bars")
    print("=" * 100)
    print("  Originally measured on 198 touches. Stops and targets are 30 NQ")
    print("  points converted at each day's own price, net of 2 points cost.\n")

    rows = []
    for d0, d1 in zip(keys, keys[1:]):
        prev, b = days[d0], days[d1]
        px = float(b.o.iloc[0])
        k = px / NQ_PRICE                     # NQ points -> QQQ points
        bucket, band = BUCKET_NQ * k, BAND_NQ * k
        stop_d, tgt_d = STOP_NQ * k, TARGET_NQ * k
        lv, wt = levels_from(prev, bucket)

        for h in first_touches(b, lv, band):
            up = not h["from_above"]          # approached from below -> fade = short
            # Fade: sell a level approached from below, buy one from above.
            # Entry AT the level -- no tolerance. An entry a point inside the
            # band is a free point the market never offered, and that error
            # moved the original hold rate from 58% to 53.7%.
            entry = h["price"]
            buy = h["from_above"]
            stop = entry - stop_d if buy else entry + stop_d
            target = entry + tgt_d if buy else entry - tgt_d
            pnl, amb = walk(b, h["i"], entry, stop, target, buy)

            # The opposite trade is NOT the fade's result with a minus sign:
            # cost is paid either way, so flipping a -4.60 does not give
            # +4.60, it gives +0.60. Run it as its own trade.
            g_stop = entry + stop_d if buy else entry - stop_d
            g_tgt = entry - tgt_d if buy else entry + tgt_d
            gp, gamb = walk(b, h["i"], entry, g_stop, g_tgt, not buy)

            rows.append(dict(day=d1, name=h["name"], weight=wt[h["name"]],
                             nq=pnl / px * NQ_PRICE - COST_NQ, amb=amb,
                             go=gp / px * NQ_PRICE - COST_NQ, gamb=gamb,
                             hold=pnl > 0, i=h["i"], buy=buy))

    R = pd.DataFrame(rows)
    print(f"  {len(R):,} first touches across {R.day.nunique():,} sessions "
          f"({len(R)/max(1,R.day.nunique()):.1f} per session)\n")

    print("1  DO LEVELS HOLD?  (original claim: 53-56% of touches)")
    print("-" * 100)
    print("  'Hold' means the 30-point reversal came before the 30-point")
    print("  continuation. At 1:1 the hold rate IS the edge.\n")
    all_rows = R.to_dict("records")
    stat(all_rows, "every level, faded")
    print()
    for name in ("POC", "VAH", "VAL", "PDH", "PDL", "PDC"):
        stat([r for r in all_rows if r["name"] == name], f"{name}")

    print("\n2  HEAVY VS LIGHT — the split that was the whole rule")
    print("-" * 100)
    print("  Weight is volume traded within the band of the level yesterday,")
    print("  as a percentile within its own session so the measure does not")
    print("  drift as volumes grow over five years.\n")
    R["pct"] = R.groupby("day").weight.rank(pct=True)
    for lo, hi, lbl in ((0, .34, "lightest third"), (.34, .67, "middle third"),
                        (.67, 1.01, "HEAVIEST third")):
        sel = R[(R.pct >= lo) & (R.pct < hi)].to_dict("records")
        stat(sel, f"fade the {lbl}")

    print("\n  and the other side -- GO WITH the break instead of fading it.")
    print("  Cost is paid in both directions, so this is run as its own trade")
    print("  rather than as the fade with a minus sign in front of it.\n")
    stat(all_rows, "break every level, go with it", key="go")
    for name in ("PDH", "PDL", "POC", "PDC"):
        stat([r for r in all_rows if r["name"] == name],
             f"  go with the {name} break", key="go")

    print("\n3  BY ERA — one regime, or all of them?")
    print("-" * 100)
    R["year"] = pd.to_datetime(R.day).dt.year
    light = R[R.pct < .34]
    for y in sorted(R.year.unique()):
        stat(light[light.year == y].to_dict("records"), f"lightest third, {y}")

    print("\n4  DE-OVERLAPPED — one trade per session, first touch only")
    print("-" * 100)
    print("  Touches inside one session share the day's move, so counting six")
    print("  of them as six independent observations inflates every t. This")
    print("  keeps the earliest touch per session and nothing else.\n")
    firsts = R.sort_values("i").groupby("day").head(1)
    stat(firsts.to_dict("records"), "first touch of the day, any level")
    stat(firsts[firsts.pct < .34].to_dict("records"), "  when it is a light level")
    stat(firsts[firsts.pct >= .67].to_dict("records"), "  when it is a heavy level")
    print()
    stat(firsts.to_dict("records"), "go-with, first touch of the day", key="go")
    pdhl = firsts[firsts.name.isin(["PDH", "PDL"])]
    stat(pdhl.to_dict("records"), "  go-with, and it is PDH or PDL", key="go")

    print("\n5  THE ONE THING WITH A REAL t — PDH/PDL, checked properly")
    print("-" * 100)
    print("  Fading PDH and PDL lost with t=-3.65 and t=-3.92 on 1,044")
    print("  touches: prior-day extremes BREAK. Going with the break is the")
    print("  same fact traded the right way round, and it has to clear the")
    print("  same bars everything else was held to.\n")
    pd_all = [r for r in all_rows if r["name"] in ("PDH", "PDL")]
    stat(pd_all, "go with the PDH/PDL break, all touches", key="go")
    stat([r for r in pd_all if r["name"] == "PDH"], "  PDH only", key="go")
    stat([r for r in pd_all if r["name"] == "PDL"], "  PDL only", key="go")
    print()
    pdf = pd.DataFrame(pd_all)
    pdf["year"] = pd.to_datetime(pdf.day).dt.year
    for y in sorted(pdf.year.unique()):
        stat(pdf[pdf.year == y].to_dict("records"), f"  {y}", key="go")
    print()
    d1 = pdf.sort_values("i").groupby("day").head(1)
    stat(d1.to_dict("records"), "de-overlapped: one PDH/PDL trade a session",
         key="go")


if __name__ == "__main__":
    main()
