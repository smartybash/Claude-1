"""What target R:R maximises expectancy? Sweep a fixed R target for FADE and
BREAK, keeping the structural stop (zone far edge +/- buffer). Pooled
NQ+ES+QQQ+SPY 1h+30m, trend-aligned, no lookahead.

For each qualifying signal we compute the outcome at every target: +R if the
R-multiple target is hit first, -1 if stopped, or the realised fraction if flat
at the close. Report win% and expectancy(avg R) per target so the peak of the
expectancy curve = the ideal R:R.  FADE (mean-reversion) and BREAK (continuation)
are reported separately - they should peak at different R:R.
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
from scripts.backtest_trend_only import SERIES, split_sessions, rth_of
from scripts.sim_15day import _run, BUF_F, WIN_F, macro_bias
from scripts.stretch_filter_test import session_stretch

K = 0.5
MARG_F = 0.0005
TARGETS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]


def outcomes_at_targets(arr, i, entry, stop, side):
    """R outcome for each fixed-R target from a signal at bar i (entry next bar)."""
    risk = abs(entry - stop)
    res = []
    for R in TARGETS:
        tgt = entry + (side * R * risk)
        t = _run(arr, i, i + 1, entry, stop, tgt, side, None)
        res.append(t["R"] if t else 0.0)
    return res


def main():
    fade = defaultdict(list)   # target -> list of R
    brk = defaultdict(list)
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
            if len(hist) < 60 or len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0]); zs, px = bt.build(hist, bysess[ids[idx - 1]], bps)
            az = [dict(z, bias=bias) for z in zs
                  if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            buf = BUF_F * px; marg = MARG_F * px
            arr = rth.reset_index(drop=True); st = session_stretch(rth)
            usedF, usedB = set(), set()
            for i in range(1, len(arr) - 1):
                h, l, c, cp = arr["high"][i], arr["low"][i], arr["close"][i], arr["close"][i - 1]
                for zi, z in enumerate(az):
                    lo, hi = z["lo"], z["hi"]
                    # FADE (stretched, trend-aligned)
                    if zi not in usedF:
                        if bias < 0 and h >= lo and c < lo and st[i] >= K:
                            for R, r in zip(TARGETS, outcomes_at_targets(arr, i, c, hi + buf, -1)): fade[R].append(r)
                            usedF.add(zi)
                        elif bias > 0 and l <= hi and c > hi and -st[i] >= K:
                            for R, r in zip(TARGETS, outcomes_at_targets(arr, i, c, lo - buf, 1)): fade[R].append(r)
                            usedF.add(zi)
                    # BREAK (with trend)
                    if zi not in usedB:
                        if bias < 0 and cp >= lo and c < lo - marg:
                            for R, r in zip(TARGETS, outcomes_at_targets(arr, i, c, hi + buf, -1)): brk[R].append(r)
                            usedB.add(zi)
                        elif bias > 0 and cp <= hi and c > hi + marg:
                            for R, r in zip(TARGETS, outcomes_at_targets(arr, i, c, lo - buf, 1)): brk[R].append(r)
                            usedB.add(zi)

    def row(d, R):
        a = np.array(d[R]); se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return f"R:R 1:{R:<3}  win={(a>0).mean():4.0%}  exp={a.mean():+.2f}R (±{1.96*se:.2f})  netR={a.sum():+6.1f}"

    n_f = len(fade[TARGETS[0]]); n_b = len(brk[TARGETS[0]])
    print(f"IDEAL R:R SWEEP — structural stop (zone edge), fixed R target. "
          f"Pooled NQ+ES+QQQ+SPY 1h+30m\n")
    print(f"FADE (stretched >= {K}sigma, trend-aligned)   n={n_f} signals")
    best_f = max(TARGETS, key=lambda R: np.mean(fade[R]))
    for R in TARGETS:
        print(("  * " if R == best_f else "    ") + row(fade, R))
    print(f"  -> peak expectancy at 1:{best_f}\n")
    print(f"BREAK (close-thru, trend-aligned)          n={n_b} signals")
    best_b = max(TARGETS, key=lambda R: np.mean(brk[R]))
    for R in TARGETS:
        print(("  * " if R == best_b else "    ") + row(brk, R))
    print(f"  -> peak expectancy at 1:{best_b}")

    _chart(fade, brk, best_f, best_b)


def _chart(fade, brk, best_f, best_b):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fexp = [np.mean(fade[R]) for R in TARGETS]; ferr = [1.96 * np.std(fade[R], ddof=1) / len(fade[R]) ** 0.5 for R in TARGETS]
    bexp = [np.mean(brk[R]) for R in TARGETS]; berr = [1.96 * np.std(brk[R], ddof=1) / len(brk[R]) ** 0.5 for R in TARGETS]
    fwin = [(np.array(fade[R]) > 0).mean() * 100 for R in TARGETS]
    bwin = [(np.array(brk[R]) > 0).mean() * 100 for R in TARGETS]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
    ax1.errorbar(TARGETS, fexp, yerr=ferr, marker="o", lw=2, capsize=4, color="#c62828", label="FADE (mean-rev)")
    ax1.errorbar(TARGETS, bexp, yerr=berr, marker="s", lw=2, capsize=4, color="#1565c0", label="BREAK (continuation)")
    ax1.axhline(0, color="#000", lw=0.8)
    ax1.scatter([best_f], [np.mean(fade[best_f])], s=180, facecolor="none", edgecolor="#c62828", lw=2, zorder=5)
    ax1.scatter([best_b], [np.mean(brk[best_b])], s=180, facecolor="none", edgecolor="#1565c0", lw=2, zorder=5)
    ax1.set_xlabel("target R:R (1 : x)"); ax1.set_ylabel("expectancy (avg R / trade)")
    ax1.set_title("Expectancy vs target R:R — peak = ideal (95% CI)", fontsize=10); ax1.legend(fontsize=9)
    ax2.plot(TARGETS, fwin, "-o", color="#c62828", lw=2, label="FADE")
    ax2.plot(TARGETS, bwin, "-s", color="#1565c0", lw=2, label="BREAK")
    ax2.axhline(50, color="#999", ls="--", lw=1)
    ax2.set_xlabel("target R:R (1 : x)"); ax2.set_ylabel("win %"); ax2.set_ylim(0, 90)
    ax2.set_title("Win rate vs target R:R (falls as target widens)", fontsize=10); ax2.legend(fontsize=9)
    fig.suptitle("Ideal R:R — fixed-target sweep, structural stop (pooled NQ+ES+QQQ+SPY, 1h+30m)", fontsize=11, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "ideal_rr.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
