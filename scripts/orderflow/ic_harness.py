#!/usr/bin/env python3
"""FEATURE IC AGAINST FORWARD RETURNS — the efficient way to use 19 sessions.

Everything in this project so far has been scored on TRADE OUTCOMES: take the
signal, set a stop and a target, see what happened. That is how a trade is
judged, but it is a wasteful way to learn from a small sample. Nineteen
sessions produce about 60 structure signals, so every question ends up decided
by sixty numbers no matter how much tape sits behind them.

Scoring a feature against FORWARD RETURNS instead uses every bar. The same
nineteen sessions give roughly 7,400 one-minute observations -- more than a
hundred times the evidence about whether a feature carries information, with no
stop or target to argue about.

The statistic is the information coefficient: the rank correlation between the
feature now and the return over the next h minutes. Rank, not linear, because
one violent bar should not decide the answer.

SIGNIFICANCE IS COMPUTED ACROSS SESSIONS, NOT BARS. Bars inside a day share
that day's move; treating 7,400 of them as independent is exactly the error
that turned a t of +5.12 into +1.00 earlier in this project. So the IC is
computed once per session and the t-statistic comes from those nineteen
numbers.

AND EVERY RESULT IS CALIBRATED AGAINST A NULL. The same features are scored
against returns circularly shifted within each session, which destroys the
link while preserving the autocorrelation. The number of features that look
significant under that null is what "significant" is worth here. Run enough
features on nineteen sessions and some will always clear a threshold; the null
column says how many.

Features are computed FROM TICKS. Bars appear only as the evaluation grid --
the aggressor tag on every print is preserved into each feature, which is the
information that aggregation is usually accused of destroying.

Usage: python3 scripts/orderflow/ic_harness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import load_all, rth                                            # noqa

GRID = "1min"
HORIZONS = (1, 5, 15)
TICK = 0.25


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Rank correlation, without pulling in scipy for one function.

    Ranks are averaged over ties, which matters here: features like the count
    of stacked imbalances take few distinct values, and ranking ties
    arbitrarily would invent an ordering the data does not have.
    """
    def rank(v):
        order = v.argsort(kind="mergesort")
        r = np.empty(len(v), float)
        r[order] = np.arange(len(v), dtype=float)
        # average the ranks of equal values
        sv = v[order]
        i = 0
        while i < len(sv):
            j = i
            while j + 1 < len(sv) and sv[j + 1] == sv[i]:
                j += 1
            if j > i:
                r[order[i:j + 1]] = (i + j) / 2.0
            i = j + 1
        return r

    rx, ry = rank(x), rank(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return np.nan
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def features(s: pd.DataFrame) -> pd.DataFrame:
    """One row per grid bar, every column known at that bar's close.

    Nothing here looks forward. Rolling windows end on the current bar and the
    forward returns added later are the only thing that reaches ahead.
    """
    s = s.set_index("time")
    g = s.resample(GRID)
    b = g.agg(o=("price", "first"), h=("price", "max"), l=("price", "min"),
              c=("price", "last"), v=("volume", "sum"),
              d=("signed", "sum"), n=("price", "count")).dropna(subset=["c"])
    if len(b) < 60:
        return None

    # --- bid/ask volume at price, the footprint the platform draws ---------
    # Trades at bid are sells hitting the bid; trades at ask are buys lifting
    # it. Aggregating them per price per bar is what a cluster chart is.
    buy = s[s["sign"] > 0].resample(GRID).volume.sum().reindex(b.index).fillna(0)
    sell = s[s["sign"] < 0].resample(GRID).volume.sum().reindex(b.index).fillna(0)

    f = pd.DataFrame(index=b.index)
    px = b.c

    # --- flow --------------------------------------------------------------
    for w in (1, 5, 15):
        dw = b.d.rolling(w).sum()
        vw = b.v.rolling(w).sum()
        f[f"delta{w}"] = dw
        f[f"dshare{w}"] = dw / vw.replace(0, np.nan)
    f["cvd"] = b.d.cumsum()
    f["cvd_share"] = f.cvd / b.v.cumsum().replace(0, np.nan)
    f["ba_ratio"] = (buy - sell) / (buy + sell).replace(0, np.nan)

    # --- divergence: price one way, flow the other -------------------------
    ret5 = px.pct_change(5)
    z = lambda x: (x - x.rolling(60, min_periods=20).mean()) / \
                  x.rolling(60, min_periods=20).std().replace(0, np.nan)
    f["divergence5"] = z(ret5) - z(f["dshare5"])

    # --- absorption: volume arriving with no price result ------------------
    rng5 = (b.h.rolling(5).max() - b.l.rolling(5).min()) / TICK
    f["absorption5"] = b.v.rolling(5).sum() / rng5.replace(0, np.nan)
    f["effort_result"] = rng5 / b.v.rolling(5).sum().replace(0, np.nan)

    # --- VWAP displacement -------------------------------------------------
    vwap = (px * b.v).cumsum() / b.v.cumsum().replace(0, np.nan)
    sd = px.rolling(30, min_periods=10).std().replace(0, np.nan)
    f["vwap_disp"] = (px - vwap) / sd

    # --- profile migration: where volume is concentrating ------------------
    # Volume-weighted mean price of the last 30 bars against the 30 before it.
    vw30 = (px * b.v).rolling(30).sum() / b.v.rolling(30).sum().replace(0, np.nan)
    f["poc_shift"] = (vw30 - vw30.shift(30)) / sd

    # --- activity ----------------------------------------------------------
    f["surge"] = b.v / b.v.rolling(20, min_periods=8).median().shift(1).replace(0, np.nan)
    f["speed"] = b.n / b.n.rolling(20, min_periods=8).median().shift(1).replace(0, np.nan)
    f["clip"] = b.v / b.n.replace(0, np.nan)

    # --- exhaustion: a push that stops extending ---------------------------
    hi20 = b.h.rolling(20).max()
    lo20 = b.l.rolling(20).min()
    f["pos_in_range"] = (px - lo20) / (hi20 - lo20).replace(0, np.nan)
    f["ext_up"] = (px - hi20.shift(1)) / sd
    f["ext_dn"] = (lo20.shift(1) - px) / sd

    # --- opening drive: the first 30 minutes' direction, carried forward ---
    first30 = px.iloc[:30]
    drive = ((first30.iloc[-1] - first30.iloc[0]) / sd.iloc[29]
             if len(first30) >= 30 and not np.isnan(sd.iloc[29]) else np.nan)
    f["open_drive"] = drive

    # --- forward returns, the only thing that looks ahead ------------------
    for h in HORIZONS:
        f[f"fwd{h}"] = px.shift(-h) / px - 1.0
    return f


def main():
    full = load_all()
    days = {d: rth(x) for d, x in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}

    per = {}
    for d, s in days.items():
        f = features(s)
        if f is not None:
            per[d] = f
    cols = [c for c in next(iter(per.values())).columns
            if not c.startswith("fwd")]
    print("=" * 96)
    print(f"INFORMATION COEFFICIENT — {len(per)} sessions, "
          f"{sum(len(f) for f in per.values()):,} one-minute bars")
    print("=" * 96)
    print("  IC is the rank correlation between the feature now and the return")
    print("  over the next h minutes. Computed PER SESSION, then a t-statistic")
    print("  across sessions -- bars inside a day are not independent.")
    print()
    print("  The NULL column is the same test against returns circularly")
    print("  shifted within each session: the link is destroyed, the")
    print("  autocorrelation is kept. It is how many features look this good")
    print("  by chance, and it is the only thing that makes |t| interpretable.")
    print()

    rng = np.random.default_rng(0)
    rows = []
    for h in HORIZONS:
        for c in cols:
            ics, nulls = [], []
            for d, f in per.items():
                x = f[c].to_numpy(dtype=float)
                y = f[f"fwd{h}"].to_numpy(dtype=float)
                m = np.isfinite(x) & np.isfinite(y)
                if m.sum() < 50 or np.nanstd(x[m]) == 0:
                    continue
                ic = spearman(x[m], y[m])
                k = rng.integers(30, max(31, m.sum() - 30))
                nl = spearman(x[m], np.roll(y[m], k))
                if np.isfinite(ic) and np.isfinite(nl):
                    ics.append(ic)
                    nulls.append(nl)
            if len(ics) < 8:
                continue
            ics = np.array(ics, float)
            nulls = np.array(nulls, float)
            t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))) \
                if ics.std(ddof=1) > 0 else 0.0
            tn = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls))) \
                if nulls.std(ddof=1) > 0 else 0.0
            rows.append(dict(h=h, feature=c, ic=ics.mean(), t=t,
                             hit=100 * (np.sign(ics) == np.sign(ics.mean())).mean(),
                             null_t=tn, n=len(ics)))

    R = pd.DataFrame(rows)
    for h in HORIZONS:
        sub = R[R.h == h].reindex(R[R.h == h].t.abs().sort_values(
            ascending=False).index)
        print(f"  ---- forward {h} minute(s) ----")
        print(f"    {'feature':<16}{'IC':>8}{'t':>8}{'sessions agreeing':>20}"
              f"{'null t':>9}")
        for _, r in sub.head(8).iterrows():
            star = "  *" if abs(r.t) >= 3 else ""
            print(f"    {r.feature:<16}{r.ic:>+8.4f}{r.t:>+8.2f}"
                  f"{r.hit:>19.0f}%{r.null_t:>+9.2f}{star}")
        print()

    print("=" * 96)
    print("HOW MANY CLEAR THE BAR, AND HOW MANY DO SO BY CHANCE")
    print("=" * 96)
    for bar in (2.0, 3.0):
        real = int((R.t.abs() >= bar).sum())
        null = int((R.null_t.abs() >= bar).sum())
        print(f"  |t| >= {bar:.0f}:  real {real:>3} of {len(R)} feature-horizons"
              f"     null {null:>3}")
    print()
    print("  If the two columns are close, nothing here has been shown to")
    print("  carry information -- the real column is just what this many")
    print("  features produce against this many sessions.")


if __name__ == "__main__":
    main()
