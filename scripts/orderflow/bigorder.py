#!/usr/bin/env python3
"""DOES ORDER SIZE SAY ANYTHING CVD CANNOT?

CVD counts a single 100-lot and a hundred separate 1-lots identically: same
contracts, same delta. One is a participant with conviction, the other is a
hundred small decisions, and a trader watching the tape sees the difference
instantly. The cumulative stream is the only recording that preserves it,
because ATAS aggregates an aggressive order sweeping several price levels into
one row with its total size and price range.

That stream was broken until it was fixed, so this has never been testable.
Thirteen July session pairs now carry a working one.

Two families, both signed so positive means "agrees with the trade":

  BIG     net delta counting only aggressive orders at or above a size
  SWEEP   net delta from orders whose last fill price differs from their
          first -- somebody paid up through resting liquidity

The size thresholds are not free parameters. A single session already showed
what tracks plain CVD and what does not: at 5 lots the correlation is +0.94
and at 10 it is +0.88, so those cannot add anything at any sample size. It
falls to +0.65 at 25 lots, +0.46 at 50, and sweep delta sits at +0.53. Only
the last three are tested here, and that choice was made before any outcome
was computed.

Method is the one the CVD gates used: each gate judged against THE TRADES IT
REFUSES inside the same sessions, with a 95% interval from resampling
SESSIONS. Levels of either arm are not trusted -- a small sample can run hot
and flatter any gate sitting on it.

Usage: python3 scripts/orderflow/bigorder.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from structure_cvd import bars                                            # noqa
from structure_trade import levels_of, next_level, signals                # noqa
from tape import load_all, rth                                            # noqa

ROOT = Path(__file__).resolve().parents[2] / "data"
COST_PTS = 2.0
BUCKET_PTS = 2.0
TICK = 0.25
SIZES = (25, 50)


def cum_ok(day: str):
    """The cumulative file for a day, or None if it predates the fix.

    A degenerate file is recognisable without knowing when it was recorded:
    every order has exactly one fill, which is the signature of writing the
    row when the order started rather than when it finished.
    """
    f = ROOT / "cum" / f"CUM_NQ_{day}.csv.gz"
    if not f.exists():
        return None
    c = pd.read_csv(f, compression="gzip")
    # Recorder 2026-09-16.o added a sequence number, a row kind and per-fill
    # rows. Orders are kind "O"; the "F" rows are the individual fills of the
    # order above them and would be counted twice by anything summing volume.
    if "kind" in c.columns:
        c = c[c.kind == "O"].drop(columns=["kind"])
    if c.empty or c.fills.max() <= 1:
        return None
    c["time"] = pd.to_datetime(c.time)
    c["sign"] = np.where(c.aggressor.astype(str).str.upper().str[0] == "B", 1, -1)
    c["signed"] = c["sign"] * c.volume
    c["sweep"] = (c.last_price - c.first_price).abs() / TICK
    return c


def per_bar(c, index, minutes):
    """CUM aggregates on the same grid as the signal bars."""
    edges = list(index) + [index.iloc[-1] + pd.Timedelta(minutes=minutes)]
    idx = pd.cut(c.time, bins=edges, right=False, labels=False)
    c = c.assign(bar=idx).dropna(subset=["bar"])
    c["bar"] = c.bar.astype(int)
    out = pd.DataFrame(index=range(len(index)))
    out["vol"] = c.groupby("bar").volume.sum()
    for lim in SIZES:
        m = c[c.volume >= lim]
        out[f"big{lim}"] = m.groupby("bar").signed.sum()
    sw = c[c.sweep >= 1]
    out["swp"] = sw.groupby("bar").signed.sum()
    return out.fillna(0.0)


def collect(days, pairs, minutes):
    rows = []
    for d0, d1 in pairs:
        prev, s = days[d0], days[d1]
        c = cum_ok(d1)
        if c is None:
            continue
        b = bars(s, minutes)
        if len(b) < 10:
            continue
        lv = levels_of(bars(prev, minutes), BUCKET_PTS)
        cf = per_bar(c, b.timestamp, minutes)

        px_all = s.price.to_numpy()
        tm_all = s.time.to_numpy()

        for sig in signals(b):
            i = sig["i"]
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            tgt = next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            sign = 1.0 if up else -1.0
            t_at = b.timestamp.iloc[i]
            start = int(np.searchsorted(tm_all, np.datetime64(t_at), side="right"))
            pnl = None
            for j in range(start, len(px_all)):
                if up:
                    if px_all[j] <= stop:
                        pnl = -risk; break
                    if px_all[j] >= tgt:
                        pnl = abs(tgt - entry); break
                else:
                    if px_all[j] >= stop:
                        pnl = -risk; break
                    if px_all[j] <= tgt:
                        pnl = abs(tgt - entry); break
            if pnl is None:
                pnl = (px_all[-1] - entry) if up else (entry - px_all[-1])

            lo2 = max(0, i - 1)
            w = cf.iloc[lo2:i + 1]
            tot = float(w["vol"].sum())
            r = dict(day=d1, R=pnl / risk - COST_PTS / risk)
            for lim in SIZES:
                net = float(w[f"big{lim}"].sum()) * sign
                r[f"big{lim}"] = net
                r[f"big{lim}_sh"] = net / tot if tot > 0 else np.nan
            net = float(w["swp"].sum()) * sign
            r["swp"] = net
            r["swp_sh"] = net / tot if tot > 0 else np.nan
            rows.append(r)
    return pd.DataFrame(rows)


def paired(df, key, cut, label, tally=None, draws=8000):
    if key not in df:
        print(f"    {label:<46} not available")
        return
    d = df.dropna(subset=[key])
    hit = (d[key] >= cut).to_numpy()
    R = d.R.to_numpy()
    if hit.sum() < 8 or (~hit).sum() < 8:
        print(f"    {label:<46} n={int(hit.sum()):<4}/{int((~hit).sum()):<4} too few")
        return
    obs = R[hit].mean() - R[~hit].mean()
    codes, _ = pd.factorize(d.day)
    k = codes.max() + 1
    on_s = np.bincount(codes[hit], R[hit], minlength=k)
    on_n = np.bincount(codes[hit], minlength=k).astype(float)
    off_s = np.bincount(codes[~hit], R[~hit], minlength=k)
    off_n = np.bincount(codes[~hit], minlength=k).astype(float)
    rng = np.random.default_rng(0)
    pick = rng.integers(0, k, size=(draws, k))
    a_s, a_n = on_s[pick].sum(1), on_n[pick].sum(1)
    b_s, b_n = off_s[pick].sum(1), off_n[pick].sum(1)
    ok = (a_n > 0) & (b_n > 0)
    boot = a_s[ok] / a_n[ok] - b_s[ok] / b_n[ok]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    mark = "  <-- excludes zero" if (lo > 0 or hi < 0) else ""
    if tally is not None:
        tally.append(obs)
    print(f"    {label:<46} n={int(hit.sum()):<4} {obs:+6.3f}R  "
          f"[{lo:+.2f}, {hi:+.2f}]{mark}")


def main():
    full = load_all()
    days = {d: rth(x) for d, x in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    ks = sorted(days)
    pairs = [(a, b) for a, b in zip(ks, ks[1:])
             if len(pd.bdate_range(a, b)) == 2]

    print("=" * 100)
    print("ORDER SIZE AND SWEEP AS GATES ON THE STRUCTURE BREAK")
    print("=" * 100)
    print("  Only sessions whose cumulative stream actually aggregates are")
    print("  used. Each gate is judged against the trades it refuses, inside")
    print("  the same sessions; intervals resample sessions.\n")

    for minutes in (3, 5):
        df = collect(days, pairs, minutes)
        if df.empty:
            print(f"  {minutes}-minute: no usable sessions\n")
            continue
        tally = []
        print(f"  ---- {minutes}-minute signals: {len(df)} breaks, "
              f"{df.day.nunique()} sessions ----")
        for lim in SIZES:
            paired(df, f"big{lim}", 1, f"  {lim}+ lot net delta with the trade",
                   tally)
            paired(df, f"big{lim}_sh", 0.02,
                   f"  {lim}+ lot net >= 2% of window volume", tally)
        paired(df, "swp", 1, "  sweep delta with the trade", tally)
        paired(df, "swp_sh", 0.02, "  sweep net >= 2% of window volume", tally)
        if tally:
            print(f"\n    sign tally: {sum(x > 0 for x in tally)}/{len(tally)} "
                  f"positive, median {np.median(tally):+.3f}R")
        print()

    print("=" * 100)
    print("  A single cell clearing zero is what a handful of tests produces by")
    print("  chance. What would matter is the same sign across both timeframes,")
    print("  which is the pattern that made CVD change worth recording.")


if __name__ == "__main__":
    main()
