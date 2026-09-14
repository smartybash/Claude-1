"""Does a VWAP σ-stretch confluence point raise the win rate?

Quant-desk hypothesis: our zones give LOCATION and the macro filter gives
DIRECTION, but we never require price to be statistically EXTENDED when it tags
the level. Add one gate: at the fade trigger bar, price must be >= K session-σ
from the session VWAP (a genuine deviation), in the direction of the fade.

Layer it on the already-validated WITH-trend-gate trades, pooled across
NQ+ES+QQQ+SPY / 1h+30m, and sweep K. Report win% / expectancy / n at each K so
we can see the win-rate lift and the sample cost. No lookahead: VWAP & σ are
cumulative within the session up to the trigger bar only.
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

ET = "America/New_York"
KS = [0.0, 0.5, 1.0, 1.5, 2.0]


def session_stretch(rth):
    """signed (close - vwap) / sigma per RTH bar, cumulative, no lookahead."""
    tp = (rth["high"] + rth["low"] + rth["close"]) / 3
    v = rth["volume"].clip(lower=1e-9)
    cv = v.cumsum()
    vwap = (tp * v).cumsum() / cv
    var = ((tp - vwap) ** 2 * v).cumsum() / cv
    sd = np.sqrt(var).replace(0, np.nan)
    return ((rth["close"] - vwap) / sd).fillna(0.0).values


def fades(rth, az, px, stretch):
    """WITH-gate fades, returning (R, entry_stretch_abs, side) per trade."""
    buf = BUF_F * px
    arr = rth.reset_index(drop=True)
    out, used = [], set()
    for i in range(len(arr) - 1):
        h, l, c = arr["high"][i], arr["low"][i], arr["close"][i]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            lo, hi = z["lo"], z["hi"]
            if h >= lo and c < lo and z["bias"] < 0:            # short resistance (down tape)
                t = _run(arr, i, i + 1, c, hi + buf, _opp(az, z, "down", c, hi + buf), -1, z)
                s = stretch[i]                                   # want price ABOVE vwap: s>0
                used.add(zi)
                if t: out.append((t["R"], s, -1))
            elif l <= hi and c > hi and z["bias"] > 0:          # long support (up tape)
                t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
                s = stretch[i]                                   # want price BELOW vwap: s<0
                used.add(zi)
                if t: out.append((t["R"], s, 1))
    return out


def main():
    rows = []  # (R, directional_stretch)
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
            opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            hist = df[df.index < opent]
            rth = rth_of(bysess[s])
            if len(hist) < 60 or len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0])
            zs, px = bt.build(hist, bysess[ids[i - 1]], bps)
            az = [dict(z, bias=bias) for z in zs
                  if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            st = session_stretch(rth)
            for R, s_signed, side in fades(rth, az, px, st):
                # directional stretch: positive = price extended in the fade's favour
                dstretch = s_signed if side < 0 else -s_signed
                rows.append((R, dstretch))

    a = np.array([r[0] for r in rows])
    ds = np.array([r[1] for r in rows])

    def stat(mask):
        g = a[mask]
        if len(g) == 0:
            return "   (no trades)"
        w = (g > 0).mean(); se = g.std(ddof=1) / len(g) ** 0.5 if len(g) > 1 else 0
        return f"n={len(g):4d}  win={w:4.0%}  netR={g.sum():+6.1f}  exp={g.mean():+.2f}R (±{1.96*se:.2f})"

    print("VWAP σ-STRETCH FILTER on WITH-trend-gate fades — pooled NQ+ES+QQQ+SPY, 1h+30m\n")
    print(f"baseline (all WITH-gate trades):  {stat(np.ones_like(a, bool))}\n")
    print("require price >= K session-σ from VWAP in the fade's direction at entry:")
    for k in KS:
        print(f"  K={k:>3.1f}σ : {stat(ds >= k)}")
    print("\ncontrast — fades taken with LITTLE/NO stretch (price near VWAP):")
    for k in [0.5, 1.0]:
        print(f"  |stretch| < {k:.1f}σ : {stat(ds < k)}")

    _chart(a, ds)


def _chart(a, ds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    wins, exps, ns, errs = [], [], [], []
    for k in KS:
        g = a[ds >= k]
        wins.append((g > 0).mean() * 100 if len(g) else np.nan)
        exps.append(g.mean() if len(g) else np.nan)
        ns.append(len(g))
        errs.append(1.96 * g.std(ddof=1) / len(g) ** 0.5 if len(g) > 1 else 0)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.plot(KS, wins, "-o", color="#1a237e", lw=2)
    for k, w, n in zip(KS, wins, ns):
        ax1.annotate(f"{w:.0f}%\nn={n}", (k, w), textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=8, fontweight="bold")
    ax1.axhline(50, color="#999", ls="--", lw=1)
    ax1.set_xlabel("min σ-stretch from VWAP at entry (K)"); ax1.set_ylabel("win %")
    ax1.set_title("Win rate vs stretch threshold\nmore stretch = higher hold rate (fewer trades)", fontsize=10)
    c2 = ["#2e7d32" if e > 0 else "#c62828" for e in exps]
    ax2.bar(range(len(KS)), exps, yerr=errs, capsize=5, color=c2, alpha=0.85, edgecolor="#333")
    ax2.axhline(0, color="#000", lw=0.8)
    for i, (e, n) in enumerate(zip(exps, ns)):
        ax2.text(i, e, f"{e:+.2f}R\nn={n}", ha="center",
                 va="bottom" if e >= 0 else "top", fontsize=8, fontweight="bold")
    ax2.set_xticks(range(len(KS))); ax2.set_xticklabels([f"{k:.1f}σ" for k in KS])
    ax2.set_ylabel("expectancy (avg R)")
    ax2.set_title("Expectancy vs stretch threshold (95% CI)", fontsize=10)
    fig.suptitle("Adding a VWAP σ-stretch confluence point to the trend-gated fade", fontsize=12, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "stretch_filter.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
