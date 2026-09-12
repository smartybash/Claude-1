"""Does the S/R FLIP (break-and-retest) add edge? Pooled NQ+ES+QQQ+SPY 1h+30m.

Once price closes decisively THROUGH a zone, the zone flips polarity: a broken
support becomes resistance (and vice-versa). The trend-aligned play is to fade
the RETEST of the flipped level in the continuation direction:
  * macro DOWN: close below support -> it becomes resistance -> when price rallies
    back into it and closes back below -> SHORT (continuation).
  * macro UP: mirror (close above resistance -> retest -> LONG).
entry = rejection close, stop = far side of the zone, target = next A+ zone in
trend (else 1.5R). One entry per zone. No lookahead.

Compare FADE vs BREAK vs FLIP (all trend-aligned) to see if the flip-retest is a
distinct, positive setup worth arming.
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
MARG_F = 0.0005


def fade_wg(rth, az, px):
    buf = BUF_F * px; arr = rth.reset_index(drop=True); out, used = [], set()
    for i in range(len(arr) - 1):
        h, l, c = arr["high"][i], arr["low"][i], arr["close"][i]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            if h >= z["lo"] and c < z["lo"] and z["bias"] < 0:
                t = _run(arr, i, i + 1, c, z["hi"] + buf, _opp(az, z, "down", c, z["hi"] + buf), -1, z); used.add(zi)
                if t: out.append(t["R"])
            elif l <= z["hi"] and c > z["hi"] and z["bias"] > 0:
                t = _run(arr, i, i + 1, c, z["lo"] - buf, _opp(az, z, "up", c, z["lo"] - buf), 1, z); used.add(zi)
                if t: out.append(t["R"])
    return out


def break_wt(rth, az, px, bias):
    buf = BUF_F * px; marg = MARG_F * px; arr = rth.reset_index(drop=True); out, used = [], set()
    for i in range(1, len(arr) - 1):
        c, cp = arr["close"][i], arr["close"][i - 1]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            if bias < 0 and cp >= z["lo"] and c < z["lo"] - marg:
                t = _run(arr, i, i + 1, c, z["hi"] + buf, _opp(az, z, "down", c, z["hi"] + buf), -1, z); used.add(zi)
                if t: out.append(t["R"])
            elif bias > 0 and cp <= z["hi"] and c > z["hi"] + marg:
                t = _run(arr, i, i + 1, c, z["lo"] - buf, _opp(az, z, "up", c, z["lo"] - buf), 1, z); used.add(zi)
                if t: out.append(t["R"])
    return out


def flip_retest(rth, az, px, bias):
    """Break a zone, then fade its retest in the trend direction."""
    buf = BUF_F * px; marg = MARG_F * px; arr = rth.reset_index(drop=True); out = []
    for z in az:
        lo, hi = z["lo"], z["hi"]
        broke = -1
        for i in range(1, len(arr)):
            c, cp = arr["close"][i], arr["close"][i - 1]
            if bias < 0:
                if broke < 0 and cp >= lo and c < lo - marg:
                    broke = i                                   # support broken -> now resistance
                elif broke >= 0 and i > broke and arr["high"][i] >= lo and c < lo:
                    t = _run(arr, i, i + 1, c, hi + buf, _opp(az, z, "down", c, hi + buf), -1, z)
                    if t: out.append((t["R"], z["rail"]));
                    break
            else:
                if broke < 0 and cp <= hi and c > hi + marg:
                    broke = i                                   # resistance broken -> now support
                elif broke >= 0 and i > broke and arr["low"][i] <= hi and c > hi:
                    t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
                    if t: out.append((t["R"], z["rail"]));
                    break
    return out


def main():
    fade, brk, flip = [], [], []
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
            hist = df[df.index < opent]; rth = rth_of(bysess[s])
            if len(hist) < 60 or len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0]); zs, px = bt.build(hist, bysess[ids[i - 1]], bps)
            hc = hist["close"].values
            az = [dict(z, bias=bias, rail=bt.zone_rail_conf(hc, z["price"], len(rth), RAIL_TOL_F * px))
                  for z in zs if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            fade.extend(fade_wg(rth, az, px))
            brk.extend(break_wt(rth, az, px, bias))
            flip.extend(flip_retest(rth, az, px, bias))

    fa = np.array(fade); br = np.array(brk)
    fl = np.array([t[0] for t in flip]); flrail = np.array([t[1] for t in flip], bool)

    def stat(a):
        if len(a) == 0:
            return "      (none)"
        se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return f"n={len(a):4d}  win={(a>0).mean():4.0%}  netR={a.sum():+6.1f}  exp={a.mean():+.2f}R (±{1.96*se:.2f})"

    print("S/R FLIP (break-and-retest) vs FADE vs BREAK — pooled NQ+ES+QQQ+SPY 1h+30m, trend-aligned\n")
    print(f"  FADE  (tag + reject)     : {stat(fa)}")
    print(f"  BREAK (close thru)       : {stat(br)}")
    print(f"  FLIP  (break + retest)   : {stat(fl)}   <- new")
    print(f"      FLIP @ rail+level    : {stat(fl[flrail])}")
    print(f"      FLIP @ non-rail      : {stat(fl[~flrail])}")

    _chart(fa, br, fl, flrail)


def _chart(fa, br, fl, flrail):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cuts = [("FADE", fa), ("BREAK", br), ("FLIP\n(retest)", fl),
            ("FLIP\n@rail", fl[flrail]), ("FLIP\n@non-rail", fl[~flrail])]
    exps = [a.mean() if len(a) else 0 for _, a in cuts]
    wins = [(a > 0).mean() * 100 if len(a) else 0 for _, a in cuts]
    err = [1.96 * a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0 for _, a in cuts]
    ns = [len(a) for _, a in cuts]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
    cols = ["#2e7d32" if e > 0 else "#c62828" for e in exps]
    ax1.bar(range(len(cuts)), exps, yerr=err, capsize=5, color=cols, alpha=0.85, edgecolor="#333")
    ax1.axhline(0, color="#000", lw=0.8)
    for i, (e, n) in enumerate(zip(exps, ns)):
        ax1.text(i, e, f"{e:+.2f}R\nn={n}", ha="center", va="bottom" if e >= 0 else "top", fontsize=8, fontweight="bold")
    ax1.set_xticks(range(len(cuts))); ax1.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax1.set_ylabel("expectancy (avg R / trade)")
    ax1.set_title("Expectancy — FADE vs BREAK vs FLIP-retest (95% CI)", fontsize=10)
    ax2.bar(range(len(cuts)), wins, color="#1565c0", alpha=0.8, edgecolor="#333")
    ax2.axhline(50, color="#999", ls="--", lw=1)
    for i, (w, n) in enumerate(zip(wins, ns)):
        ax2.text(i, w + 0.6, f"{w:.0f}%\nn={n}", ha="center", fontsize=8, fontweight="bold")
    ax2.set_xticks(range(len(cuts))); ax2.set_xticklabels([c[0] for c in cuts], fontsize=8)
    ax2.set_ylabel("win %"); ax2.set_ylim(0, 80)
    ax2.set_title("Win rate — FADE vs BREAK vs FLIP-retest", fontsize=10)
    fig.suptitle("S/R flip (break-and-retest) backtest — pooled NQ+ES+QQQ+SPY, 1h+30m, trend-aligned", fontsize=11, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "flip_retest.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
