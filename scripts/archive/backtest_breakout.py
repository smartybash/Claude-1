"""Test the natural home for rail+level: BREAKOUTS, not fades.

Hypothesis from the filter-stack backtest: a channel rail is where trends
project, so rail+level is a BREAK spot, not a reversal spot. So trade WITH the
break in the macro-trend direction:
  * macro DOWN -> SHORT a 30m close BELOW an A+ support level (breakdown)
  * macro UP   -> LONG  a 30m close ABOVE an A+ resistance level (breakout)
entry=breakout close, stop=back inside the level, target=next A+ zone in trend
(else 1.5R). Fresh breaks only (prior bar was on the other side). No lookahead.

Compare, pooled NQ+ES+QQQ+SPY 1h+30m:
  FADE @ rail+level  vs  BREAKOUT @ rail+level  vs  BREAKOUT @ non-rail  vs  BREAKOUT all
If rail+level really is a break signal, BREAKOUT@rail should beat both FADE@rail
and BREAKOUT@non-rail.
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
from scripts.sim_15day import _run, _opp, macro_bias, BUF_F, WIN_F

RAIL_TOL_F = 0.003
MARG_F = 0.0005     # close must clear the level by this fraction to count as a break


def fade_with_gate(rth, az, px):
    buf = BUF_F * px
    arr = rth.reset_index(drop=True)
    out, used = [], set()
    for i in range(len(arr) - 1):
        h, l, c = arr["high"][i], arr["low"][i], arr["close"][i]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            lo, hi = z["lo"], z["hi"]
            if h >= lo and c < lo and z["bias"] < 0:
                t = _run(arr, i, i + 1, c, hi + buf, _opp(az, z, "down", c, hi + buf), -1, z)
                used.add(zi)
                if t: out.append((t["R"], z["rail"]))
            elif l <= hi and c > hi and z["bias"] > 0:
                t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
                used.add(zi)
                if t: out.append((t["R"], z["rail"]))
    return out


def breakout_with_trend(rth, az, px, bias):
    buf = BUF_F * px; marg = MARG_F * px
    arr = rth.reset_index(drop=True)
    out, used = [], set()
    for i in range(1, len(arr) - 1):
        c, cprev = arr["close"][i], arr["close"][i - 1]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            lo, hi = z["lo"], z["hi"]
            if bias < 0 and cprev >= lo and c < lo - marg:          # fresh breakdown -> short
                t = _run(arr, i, i + 1, c, hi + buf, _opp(az, z, "down", c, hi + buf), -1, z)
                used.add(zi)
                if t: out.append((t["R"], z["rail"]))
            elif bias > 0 and cprev <= hi and c > hi + marg:        # fresh breakout -> long
                t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
                used.add(zi)
                if t: out.append((t["R"], z["rail"]))
    return out


def main():
    fade, bko = [], []
    for fname, fut, bps in SERIES:
        try:
            df = bt.load(fname)
        except FileNotFoundError:
            continue
        df, ids, bysess = split_sessions(df, fut)
        dclose = {pd.Timestamp(s).date(): float(rth_of(bysess[s])["close"].iloc[-1])
                  for s in ids if len(rth_of(bysess[s]))}
        daily = pd.Series(dclose).sort_index()
        for i, s in enumerate(ids):
            if i < 20:
                continue
            date = pd.Timestamp(s).date()
            opent = pd.Timestamp(s).tz_localize("America/New_York").replace(hour=9, minute=30)
            hist = df[df.index < opent]
            rth = rth_of(bysess[s])
            if len(hist) < 60 or len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0])
            zs, px = bt.build(hist, bysess[ids[i - 1]], bps)
            hc = hist["close"].values
            az = [dict(z, bias=bias, rail=bt.zone_rail_conf(hc, z["price"], len(rth), RAIL_TOL_F * px))
                  for z in zs if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            fade.extend(fade_with_gate(rth, az, px))
            bko.extend(breakout_with_trend(rth, az, px, bias))

    fR = np.array([t[0] for t in fade]); frail = np.array([t[1] for t in fade], bool)
    bR = np.array([t[0] for t in bko]); brail = np.array([t[1] for t in bko], bool)

    def stat(a, m):
        g = a[m]
        if len(g) == 0:
            return "      (none)"
        se = g.std(ddof=1) / len(g) ** 0.5 if len(g) > 1 else 0
        return f"n={len(g):4d}  win={(g>0).mean():4.0%}  netR={g.sum():+6.1f}  exp={g.mean():+.2f}R (±{1.96*se:.2f})"

    print("BREAKOUT vs FADE at rail+level — pooled NQ+ES+QQQ+SPY 1h+30m (trend-aligned)\n")
    print(f"  FADE     @ rail+level : {stat(fR, frail)}")
    print(f"  BREAKOUT @ rail+level : {stat(bR, brail)}   <- hypothesis: best")
    print(f"  BREAKOUT @ non-rail   : {stat(bR, ~brail)}")
    print(f"  BREAKOUT @ all zones  : {stat(bR, np.ones_like(bR, bool))}")
    print(f"\n  (context) FADE @ all  : {stat(fR, np.ones_like(fR, bool))}")

    _chart(fR, frail, bR, brail)


def _chart(fR, frail, bR, brail):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cuts = [("FADE\n@rail+level", fR, frail),
            ("BREAKOUT\n@rail+level", bR, brail),
            ("BREAKOUT\n@non-rail", bR, ~brail),
            ("BREAKOUT\n@all", bR, np.ones_like(bR, bool))]
    exps = [a[m].mean() if m.sum() else 0 for _, a, m in cuts]
    wins = [(a[m] > 0).mean() * 100 if m.sum() else 0 for _, a, m in cuts]
    err = [1.96 * a[m].std(ddof=1) / m.sum() ** 0.5 if m.sum() > 1 else 0 for _, a, m in cuts]
    ns = [int(m.sum()) for _, _, m in cuts]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    cols = ["#2e7d32" if e > 0 else "#c62828" for e in exps]
    ax1.bar(range(len(cuts)), exps, yerr=err, capsize=5, color=cols, alpha=0.85, edgecolor="#333")
    ax1.axhline(0, color="#000", lw=0.8)
    for i, (e, n) in enumerate(zip(exps, ns)):
        ax1.text(i, e, f"{e:+.2f}R\nn={n}", ha="center",
                 va="bottom" if e >= 0 else "top", fontsize=8, fontweight="bold")
    ax1.set_xticks(range(len(cuts))); ax1.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax1.set_ylabel("expectancy (avg R / trade)")
    ax1.set_title("Expectancy: breakout vs fade at rail+level (95% CI)", fontsize=10)
    ax2.bar(range(len(cuts)), wins, color="#1565c0", alpha=0.8, edgecolor="#333")
    ax2.axhline(50, color="#999", ls="--", lw=1)
    for i, (w, n) in enumerate(zip(wins, ns)):
        ax2.text(i, w + 0.6, f"{w:.0f}%\nn={n}", ha="center", fontsize=8, fontweight="bold")
    ax2.set_xticks(range(len(cuts))); ax2.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax2.set_ylabel("win %"); ax2.set_ylim(0, 80)
    ax2.set_title("Win rate: breakout vs fade at rail+level", fontsize=10)
    fig.suptitle("Rail+level is a BREAK signal, not a fade — trend-aligned breakout backtest "
                 "(pooled NQ+ES+QQQ+SPY, 1h+30m)", fontsize=11, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "breakout_rail.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
