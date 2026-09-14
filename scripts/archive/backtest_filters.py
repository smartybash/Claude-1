"""Optimize the filter stack: does RAIL-confluence and/or VWAP-STRETCH add edge,
on top of the WITH-trend-gate confluence fade? Pooled NQ+ES+QQQ+SPY, 1h+30m.

Per WITH-gate fade we record: R, directional VWAP stretch at entry, and whether
the faded zone had a regression-channel RAIL sweeping through it (rail+level
confluence) - the channel fit on pre-open bars only (no lookahead). Then compare
expectancy / win% across the filter matrix:

    base | +rail | +stretch>=0.5 | +rail & stretch   (and the excluded halves)

so we can see which filter carries the edge and whether they stack.
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
from scripts.stretch_filter_test import session_stretch

K = 0.5
RAIL_TOL_F = 0.003


def fades_tagged(rth, az, px, stretch):
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
                if t: out.append((t["R"], stretch[i], z["rail"]))
            elif l <= hi and c > hi and z["bias"] > 0:
                t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
                used.add(zi)
                if t: out.append((t["R"], -stretch[i], z["rail"]))
    return out


def main():
    rows = []  # (R, dstretch, rail)
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
            az = []
            for z in zs:
                if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp:
                    z2 = dict(z, bias=bias,
                              rail=bt.zone_rail_conf(hc, z["price"], len(rth), RAIL_TOL_F * px))
                    az.append(z2)
            if not az:
                continue
            st = session_stretch(rth)
            rows.extend(fades_tagged(rth, az, px, st))

    R = np.array([r[0] for r in rows])
    ds = np.array([r[1] for r in rows])
    rail = np.array([r[2] for r in rows], bool)

    def stat(mask):
        g = R[mask]
        if len(g) == 0:
            return "      (none)"
        se = g.std(ddof=1) / len(g) ** 0.5 if len(g) > 1 else 0
        return f"n={len(g):4d}  win={(g>0).mean():4.0%}  netR={g.sum():+6.1f}  exp={g.mean():+.2f}R (±{1.96*se:.2f})"

    strong = ds >= K
    print("FILTER-STACK OPTIMISATION — WITH-gate fades, pooled NQ+ES+QQQ+SPY 1h+30m\n")
    print(f"  base (all)              : {stat(np.ones_like(R, bool))}")
    print(f"  + rail confluence       : {stat(rail)}")
    print(f"  + stretch >= {K}sigma      : {stat(strong)}")
    print(f"  + rail  AND  stretch    : {stat(rail & strong)}   <- full stack")
    print(f"  + rail  OR   stretch    : {stat(rail | strong)}\n")
    print("  isolating each filter's lift:")
    print(f"    rail only, NOT stretch: {stat(rail & ~strong)}")
    print(f"    stretch only, NOT rail: {stat(~rail & strong)}")
    print(f"    NEITHER (junk)        : {stat(~rail & ~strong)}")

    _chart(R, ds, rail, K)


def _chart(R, ds, rail, K):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    strong = ds >= K
    cuts = [("base\n(all)", np.ones_like(R, bool)), ("+rail", rail),
            (f"+stretch\n>={K}s", strong), ("+rail &\nstretch", rail & strong),
            ("NEITHER\n(junk)", ~rail & ~strong)]
    exps = [R[m].mean() if m.sum() else 0 for _, m in cuts]
    wins = [(R[m] > 0).mean() * 100 if m.sum() else 0 for _, m in cuts]
    err = [1.96 * R[m].std(ddof=1) / m.sum() ** 0.5 if m.sum() > 1 else 0 for _, m in cuts]
    ns = [int(m.sum()) for _, m in cuts]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
    cols = ["#2e7d32" if e > 0 else "#c62828" for e in exps]
    ax1.bar(range(len(cuts)), exps, yerr=err, capsize=5, color=cols, alpha=0.85, edgecolor="#333")
    ax1.axhline(0, color="#000", lw=0.8)
    for i, (e, n) in enumerate(zip(exps, ns)):
        ax1.text(i, e, f"{e:+.2f}R\nn={n}", ha="center",
                 va="bottom" if e >= 0 else "top", fontsize=8, fontweight="bold")
    ax1.set_xticks(range(len(cuts))); ax1.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax1.set_ylabel("expectancy (avg R / trade)")
    ax1.set_title("Expectancy by filter stack (95% CI)", fontsize=10)
    ax2.bar(range(len(cuts)), wins, color="#1565c0", alpha=0.8, edgecolor="#333")
    ax2.axhline(50, color="#999", ls="--", lw=1)
    for i, (w, n) in enumerate(zip(wins, ns)):
        ax2.text(i, w + 0.6, f"{w:.0f}%", ha="center", fontsize=8, fontweight="bold")
    ax2.set_xticks(range(len(cuts))); ax2.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax2.set_ylabel("win %"); ax2.set_ylim(0, 80)
    ax2.set_title("Win rate by filter stack", fontsize=10)
    fig.suptitle("Filter-stack optimisation — rail-confluence & VWAP-stretch on the trend-gated fade "
                 "(pooled NQ+ES+QQQ+SPY, 1h+30m)", fontsize=11, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "filter_stack.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
