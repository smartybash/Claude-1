"""Live three-filter read: LOCATION + DIRECTION + EXTENSION.

For each pre-open confluence zone near price, show all three gates and only flag
TAKE when they align:
  1. LOCATION  - A+/DENSE confluence zone (score>=8, >=2 distinct sources)
  2. DIRECTION - the fade agrees with the macro daily trend (10/20 SMA + slope)
  3. EXTENSION - price is >= 0.5 session-sigma from VWAP toward the zone
The extension uses the CURRENT session's VWAP (overnight Globex now; it resets at
the 9:30 RTH open - the stretch is a live trigger, re-read intraday).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
from scripts.sim_15day import macro_bias, WIN_F

ET = "America/New_York"
LIVE_PX = 28431.25   # snapshot last
K_STRETCH = 0.5


def sess_split(df):
    s = pd.Series(df.index.date, index=df.index)
    ev = df.index.hour >= 18
    s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def build_daily():
    """macro daily closes: real dailies (Apr-Jul2) + July session RTH closes."""
    r = json.loads((ROOT / "data" / "nq_daily_3m.json").read_text())
    dd = pd.Series(r["close"], index=pd.to_datetime(r["time"], utc=True).tz_convert(ET).date)
    df = bt.load("nq_30min_eth.json")
    df, ids, bysess = sess_split(df)
    sc = {}
    for s in ids:
        rth = bysess[s][(bysess[s].index.time >= pd.Timestamp("09:30").time()) &
                        (bysess[s].index.time < pd.Timestamp("16:00").time())]
        if len(rth):
            sc[pd.Timestamp(s).date()] = float(rth["close"].iloc[-1])
    sc = pd.Series(sc)
    daily = pd.concat([dd[dd.index < sc.index.min()], sc]).sort_index()
    return daily[~daily.index.duplicated(keep="last")], df, ids, bysess


def main():
    daily, df, ids, bysess = build_daily()
    cur_sess = ids[-1]                      # current (Jul 31) Globex session, RTH not open
    cur_date = pd.Timestamp(cur_sess).date()
    px = LIVE_PX

    # macro DIRECTION
    bias = macro_bias(daily, cur_date)
    bias_txt = {1: "UP", -1: "DOWN", 0: "MIXED"}[bias]

    # LOCATION: pre-open zones from all bars up to now
    hist = df[df["sess"] < cur_sess]        # completed sessions
    prior = bysess[ids[-2]]
    zs, _ = bt.build(hist, prior, 13)
    # display the real structure within 1.5% (w>=6 or >=3 sources); TAKE still needs w>=8
    az = [z for z in zs if (z["w"] >= 6 or z["nt"] >= 3) and abs(z["price"] - px) <= 0.015 * px]
    az.sort(key=lambda z: z["price"], reverse=True)

    # EXTENSION: current Globex session VWAP + sigma (live)
    g = bysess[cur_sess]
    tp = (g["high"] + g["low"] + g["close"]) / 3
    v = g["volume"].clip(lower=1e-9)
    cv = v.cumsum()
    vwap = float(((tp * v).cumsum() / cv).iloc[-1])
    sd = float(np.sqrt(((tp - vwap) ** 2 * v).cumsum().iloc[-1] / cv.iloc[-1]))
    stretch = (px - vwap) / sd if sd else 0.0

    print(f"NQ three-filter read — {cur_date} PRE-OPEN (overnight Globex)   price {px:.0f}")
    print(f"  prior RTH close 28238   overnight range 28300-28572   +193 (+0.69%)\n")
    print(f"FILTER 2 DIRECTION : macro daily bias = {bias_txt}  "
          f"-> only {'SHORT resistance' if bias<0 else ('LONG support' if bias>0 else 'stand aside')} fades\n")
    print(f"FILTER 3 EXTENSION : session VWAP {vwap:.0f}  sigma {sd:.0f}  "
          f"price stretch = {stretch:+.2f}sigma  (need |>=|{K_STRETCH} toward the zone)")
    print(f"  (overnight VWAP now; RESETS at 9:30 RTH open - re-read intraday)\n")
    print("FILTER 1 LOCATION  - A+/DENSE zones in play, with the full gate:\n")
    hdr = f"  {'zone':17s} {'grade':6s} {'side':5s} {'dir?':5s} {'stretch?':9s}  VERDICT"
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    for z in az:
        dense = z["nt"] >= 4
        grade = ("DENSE" if dense else "A+") if z["w"] >= 8 else "wk"
        side = "short" if z["price"] > px else "long"
        dir_ok = (side == "short" and bias < 0) or (side == "long" and bias > 0)
        # stretch toward THIS zone: for a short you want price stretched UP (stretch>0)
        toward = stretch if side == "short" else -stretch
        str_ok = toward >= K_STRETCH
        verdict = "TAKE" if (dir_ok and str_ok and z["w"] >= 8) else "wait"
        why = []
        if not dir_ok: why.append("vs trend")
        if not str_ok: why.append(f"not stretched ({toward:+.1f}s)")
        tag = verdict + ("" if verdict == "TAKE" else "  (" + ", ".join(why) + ")")
        print(f"  {z['lo']:.0f}-{z['hi']:.0f} @{z['price']:.0f}  {grade:6s} {side:5s} "
              f"{'yes' if dir_ok else 'no':5s} {'yes' if str_ok else 'no':9s}  {tag}")

    _chart(g, az, px, vwap, sd, bias, cur_date)


def _chart(g, az, px, vwap, sd, bias, cur_date):
    a = g.reset_index()
    fig, ax = plt.subplots(figsize=(13, 7))
    for i, r in a.iterrows():
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.8)
        ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6,
                               abs(r["close"] - r["open"]) + 0.5, facecolor=c, edgecolor=c))
    m = len(a)
    for z in az:
        side = "short" if z["price"] > px else "long"
        dir_ok = (side == "short" and bias < 0) or (side == "long" and bias > 0)
        toward = ((px - vwap) / sd) * (1 if side == "short" else -1)
        take = dir_ok and toward >= K_STRETCH and z["w"] >= 8
        col = "#d32f2f" if side == "short" else "#2e7d32"
        ax.add_patch(Rectangle((0, z["lo"]), m + 3, max(z["hi"] - z["lo"], 8), facecolor=col,
                               alpha=0.28 if take else 0.10, edgecolor=col,
                               lw=2.4 if take else 1.0, ls="-" if take else "--"))
        lab = f"{z['price']:.0f} {'DENSE' if z['nt']>=4 else 'A+'}" + ("  ★TAKE" if take else "")
        ax.text(m + 3.3, z["price"], lab, color=col, fontsize=8,
                va="center", fontweight="bold" if take else "normal")
    ax.axhline(px, color="#000", lw=1.4)
    ax.text(m + 3.3, px, f"px {px:.0f}", fontsize=8, va="center", fontweight="bold")
    ax.axhline(vwap, color="#1565c0", lw=1.2, ls="--")
    ax.text(-1.5, vwap, f"VWAP {vwap:.0f}", color="#1565c0", fontsize=8, va="center", ha="right")
    for s_ in (1, 2):
        for sign in (1, -1):
            ax.axhline(vwap + sign * s_ * sd, color="#90a4ae", lw=0.7, ls=":")
    ax.text(-1.5, vwap + sd, f"+1σ {vwap+sd:.0f}", color="#607d8b", fontsize=6.5, va="center", ha="right")
    bt_txt = {1: "UP", -1: "DOWN", 0: "MIXED"}[bias]
    ax.set_title(f"NQ {cur_date} pre-open (overnight Globex) — three-filter gate  "
                 f"[macro {bt_txt} → short-only; ★=all 3 align]", fontsize=11, fontweight="bold")
    ax.set_xticks([]); ax.margins(x=0.02)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_three_filter_today.png"
    plt.savefig(out, dpi=110, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
