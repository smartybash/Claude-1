"""Test the one NEW idea from the ICT video: the Fair Value Gap (FVG).

FVG = 3-candle imbalance: bullish when high[i-2] < low[i] (gap up), bearish when
low[i-2] > high[i] (gap down). ICT claim: price retraces to the 50% midpoint and
continues in the displacement direction. We test it TREND-ALIGNED (the video's
'range' step = our macro bias):
  * macro DOWN + bearish FVG -> SHORT at the midpoint on the pull-back up,
    stop above the gap, target a fixed R.  (macro UP + bullish FVG mirror.)

Reports, pooled NQ+ES+QQQ+SPY 1h+30m:
  * FILL rate  - how often price even returns to the midpoint (you get filled),
  * expectancy/win at target 1:1.5 / 1:2.5 / 1:4 (his number),
  * vs a NULL (random midpoints, same test) - is the FVG special or just any level?
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
from scripts.backtest_trend_only import SERIES, split_sessions, rth_of
from scripts.sim_15day import _run, BUF_F, macro_bias

RNG = np.random.default_rng(20260803)
TARGETS = [1.5, 2.5, 4.0]
MIN_GAP_F = 0.0006     # ignore micro-gaps smaller than this fraction of price


def fvgs(arr, bias):
    """Trend-aligned FVGs as (mid, far_edge) — far_edge = stop side."""
    out = []
    h, l = arr["high"].values, arr["low"].values
    for i in range(2, len(arr)):
        if bias < 0 and l[i - 2] > h[i]:                    # bearish gap (down displacement)
            top, bot = l[i - 2], h[i]
            if top - bot >= MIN_GAP_F * top:
                out.append((i, (top + bot) / 2, top))       # mid, stop-edge (top)
        elif bias > 0 and h[i - 2] < l[i]:                  # bullish gap (up displacement)
            bot, top = h[i - 2], l[i]
            if top - bot >= MIN_GAP_F * top:
                out.append((i, (top + bot) / 2, bot))       # mid, stop-edge (bot)
    return out


def run_fvg(arr, form_i, mid, stop, side, px):
    """Fill at midpoint on the pull-back, then outcome at each fixed-R target."""
    buf = BUF_F * px
    stop = stop + (buf if side < 0 else -buf)
    fill_j = None
    for j in range(form_i + 1, len(arr)):
        if (side < 0 and arr["high"].values[j] >= mid) or (side > 0 and arr["low"].values[j] <= mid):
            fill_j = j; break
    if fill_j is None:
        return None                                          # never filled
    risk = abs(mid - stop)
    res = {}
    for R in TARGETS:
        tgt = mid + side * R * risk
        t = _run(arr, fill_j, fill_j + 1, mid, stop, tgt, side, None)
        res[R] = t["R"] if t else 0.0
    return res


def main():
    real = {R: [] for R in TARGETS}; null = {R: [] for R in TARGETS}
    n_fvg = 0; n_fill = 0
    for fname, fut, bps in SERIES:
        try:
            df = bt.load(fname)
        except FileNotFoundError:
            continue
        df, ids, bysess = split_sessions(df, fut)
        dclose = {pd.Timestamp(s).date(): float(rth_of(bysess[s])["close"].iloc[-1])
                  for s in ids if len(rth_of(bysess[s]))}
        daily = pd.Series(dclose).sort_index()
        for idx, s in enumerate(ids):
            if idx < 20:
                continue
            date = pd.Timestamp(s).date()
            opent = pd.Timestamp(s).tz_localize("America/New_York").replace(hour=9, minute=30)
            hist = df[df.index < opent]; rth = rth_of(bysess[s])
            if len(hist) < 60 or len(rth) < 6:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            arr = rth.reset_index(drop=True); px = float(rth["close"].iloc[0])
            side = -1 if bias < 0 else 1
            lo_rng, hi_rng = arr["low"].min(), arr["high"].max()
            for form_i, mid, edge in fvgs(arr, bias):
                n_fvg += 1
                r = run_fvg(arr, form_i, mid, edge, side, px)
                if r is not None:
                    n_fill += 1
                    for R in TARGETS: real[R].append(r[R])
                # null: random midpoint in the day's range, same displacement side/stop-dist
                rmid = RNG.uniform(lo_rng, hi_rng)
                redge = rmid + (edge - mid)          # same stop offset as the real gap
                rn = run_fvg(arr, form_i, rmid, redge, side, px)
                if rn is not None:
                    for R in TARGETS: null[R].append(rn[R])

    def stat(a):
        a = np.array(a)
        if len(a) == 0:
            return "      (none)"
        se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return f"n={len(a):4d}  win={(a>0).mean():4.0%}  exp={a.mean():+.2f}R (±{1.96*se:.2f})  netR={a.sum():+6.1f}"

    print("FAIR VALUE GAP (ICT) — trend-aligned, pooled NQ+ES+QQQ+SPY 1h+30m\n")
    print(f"FVGs formed: {n_fvg}   filled to midpoint: {n_fill}  ({n_fill/n_fvg:.0%} fill rate)\n")
    print("FVG midpoint entry, by target:")
    for R in TARGETS:
        print(f"  1:{R}   {stat(real[R])}")
    print("\nNULL (random midpoints, same test):")
    for R in TARGETS:
        print(f"  1:{R}   {stat(null[R])}")
    print(f"\nEDGE vs null @1:2.5 = {np.mean(real[2.5]) - np.mean(null[2.5]):+.2f}R")

    _chart(real, null)


def _chart(real, null):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = np.arange(len(TARGETS)); w = 0.38
    rexp = [np.mean(real[R]) for R in TARGETS]; rerr = [1.96 * np.std(real[R], ddof=1) / len(real[R]) ** 0.5 for R in TARGETS]
    nexp = [np.mean(null[R]) for R in TARGETS]; nerr = [1.96 * np.std(null[R], ddof=1) / len(null[R]) ** 0.5 for R in TARGETS]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.bar(x - w / 2, rexp, w, yerr=rerr, capsize=4, color="#2e7d32", alpha=0.85, label="FVG midpoint", edgecolor="#333")
    ax.bar(x + w / 2, nexp, w, yerr=nerr, capsize=4, color="#9e9e9e", alpha=0.8, label="random null", edgecolor="#333")
    ax.axhline(0, color="#000", lw=0.8)
    for i, R in enumerate(TARGETS):
        ax.text(i - w / 2, rexp[i], f"{rexp[i]:+.2f}\nn={len(real[R])}", ha="center",
                va="bottom" if rexp[i] >= 0 else "top", fontsize=7.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([f"1:{R}" for R in TARGETS])
    ax.set_ylabel("expectancy (avg R / trade)"); ax.set_xlabel("target R:R")
    ax.legend(); ax.set_title("Fair Value Gap midpoint entry (trend-aligned) vs random null\n"
                              "pooled NQ+ES+QQQ+SPY, 1h+30m", fontsize=10)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "fvg_backtest.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
