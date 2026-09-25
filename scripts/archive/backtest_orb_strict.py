"""Stricter ORB test — the Concretum / Zarattini-Aziz spec, not a flat 2R.

The first pass fed ORB a fixed 2R target and no filter, which strips exactly the
parts that make the published edge work. This restores them:

  DIRECTION  : sign of the opening-range (OR) bar sets the side (Concretum's
               "first candle" rule), and price must then BREAK the OR extreme.
  STOP       : volatility-scaled — a fraction of the 14-session daily ATR,
               not the other side of the range.
  EXIT       : END OF DAY (last RTH bar) or stop. No fixed profit target.
  FILTER     : relative volume — OR-bar volume vs its own trailing average;
               the paper only takes days with elevated opening participation.

Measured in R (PnL / initial risk) so position sizing is out of scope. Compared
to a matched random-side null on the same entry bars + same stop + same EOD exit,
so we isolate whether the first-candle DIRECTION actually carries information.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt

RNG = np.random.default_rng(20260803)
STOP_ATR = 0.10        # stop distance = 10% of 14-session daily ATR (Concretum)
RELVOL_THR = 1.20      # "elevated" opening participation = OR vol >= 1.2x its avg
RELVOL_LB = 20         # trailing window for the OR-volume average
ATR_LB = 14
WARMUP = 20
SERIES = [
    ("qqq_30min.json", False), ("spy_30min.json", False),
    ("es_30min.json", True),   ("nq_30min_eth.json", True),
    ("qqq_30m_live.json", False), ("spy_30m_live.json", False),
]
OPEN = pd.Timestamp("09:30").time(); CLOSE = pd.Timestamp("16:00").time()


def sess_ids(df, fut):
    s = pd.Series(df.index.date, index=df.index)
    if fut:
        ev = df.index.hour >= 18
        s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    return pd.to_datetime(s.values)


def eod_run(h, l, c, start, entry, stop, side):
    """Walk from `start` to the last bar. Stop -> -1R, else mark to EOD close."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for j in range(start, len(c)):
        if side > 0 and l[j] <= stop:
            return -1.0
        if side < 0 and h[j] >= stop:
            return -1.0
    return (c[-1] - entry) / risk * side


def orb_strict(h, l, c, atr, relvol, want_filter):
    """OR = first RTH bar. Direction = its sign. Enter on the break of the OR
    extreme in that direction; stop = STOP_ATR * daily ATR; exit EOD."""
    if want_filter and relvol < RELVOL_THR:
        return None
    orh, orl, oro, orc = h[0], l[0], c[0], c[0]      # bar close already in c[0]
    up = orc >= oro                                   # bullish opening bar?
    stopd = STOP_ATR * atr
    if stopd <= 0:
        return None
    for i in range(1, len(c) - 1):
        if up and h[i] >= orh:                        # long only on bullish OR
            return eod_run(h, l, c, i + 1, orh, orh - stopd, +1)
        if (not up) and l[i] <= orl:                  # short only on bearish OR
            return eod_run(h, l, c, i + 1, orl, orl + stopd, -1)
    return None


def null_match(h, l, c, atr):
    """Random side, entry at a random bar, same ATR stop, same EOD exit."""
    stopd = STOP_ATR * atr
    if stopd <= 0 or len(c) < 3:
        return None
    i = int(RNG.integers(0, len(c) - 1))
    side = int(RNG.choice([-1, 1]))
    entry = c[i]
    return eod_run(h, l, c, i + 1, entry, entry - side * stopd, side)


def main():
    R = {"all": [], "hv": []}; N = []
    for fname, fut in SERIES:
        try:
            df = bt.load(fname)
        except FileNotFoundError:
            continue
        df = df.assign(sess=sess_ids(df, fut))
        ids = sorted(df["sess"].unique())
        # per-session daily OHLC (RTH) for ATR, and OR-bar volume for rel-vol
        drows, orvol = [], []
        rth_by = {}
        for s in ids:
            g = df[df["sess"] == s]
            rr = g[(g.index.time >= OPEN) & (g.index.time < CLOSE)]
            rth_by[s] = rr
            if len(rr) >= 4:
                drows.append((s, rr["high"].max(), rr["low"].min(), rr["close"].iloc[-1]))
                orvol.append(rr["volume"].iloc[0])
            else:
                drows.append((s, np.nan, np.nan, np.nan)); orvol.append(np.nan)
        dd = pd.DataFrame(drows, columns=["sess", "H", "L", "C"]).set_index("sess")
        tr = pd.concat([dd.H - dd.L, (dd.H - dd.C.shift()).abs(),
                        (dd.L - dd.C.shift()).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / ATR_LB, adjust=False).mean()
        ovser = pd.Series(orvol, index=dd.index)
        ovavg = ovser.shift().rolling(RELVOL_LB, min_periods=5).mean()

        for k, s in enumerate(ids):
            if k < WARMUP:
                continue
            rr = rth_by[s]
            if len(rr) < 6:
                continue
            a = atr.iloc[k]
            if not np.isfinite(a) or a <= 0:
                continue
            h, l, c = rr["high"].values, rr["low"].values, rr["close"].values
            rv = ovser.iloc[k] / ovavg.iloc[k] if np.isfinite(ovavg.iloc[k]) and ovavg.iloc[k] > 0 else np.nan
            r_all = orb_strict(h, l, c, a, np.nan, False)
            if r_all is not None:
                R["all"].append(r_all)
                rn = null_match(h, l, c, a)
                if rn is not None:
                    N.append(rn)
            if np.isfinite(rv):
                r_hv = orb_strict(h, l, c, a, rv, True)
                if r_hv is not None:
                    R["hv"].append(r_hv)

    def stat(a):
        a = np.array(a)
        if len(a) == 0:
            return "      (none)"
        se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return (f"n={len(a):4d}  win={(a>0).mean():4.0%}  exp={a.mean():+.2f}R "
                f"(±{1.96*se:.2f})  netR={a.sum():+6.1f}")

    print(f"STRICT ORB — Concretum spec (EOD exit, {STOP_ATR:.0%} daily-ATR stop, "
          f"rel-vol>={RELVOL_THR:.2f}x), pooled NQ+ES+QQQ+SPY 30m\n")
    print("ORB-strict  (dir + breakout, ALL days)")
    print(f"    strategy : {stat(R['all'])}")
    print(f"    null     : {stat(N)}")
    if R["all"] and N:
        print(f"    edge vs null = {np.mean(R['all']) - np.mean(N):+.2f}R\n")
    print("ORB-strict  (+ elevated opening-volume filter)")
    print(f"    strategy : {stat(R['hv'])}")
    if R["hv"] and N:
        print(f"    edge vs null = {np.mean(R['hv']) - np.mean(N):+.2f}R\n")

    _chart(R, N)


def _chart(R, N):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = ["ORB-strict\n(all days)", "ORB-strict\n(+vol filter)", "random\nnull"]
    series = [R["all"], R["hv"], N]
    exp = [np.mean(a) if a else 0 for a in series]
    err = [1.96 * np.std(a, ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0 for a in series]
    cols = ["#2e7d32" if e > 0 else "#c62828" for e in exp[:2]] + ["#9e9e9e"]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.bar(x, exp, 0.6, yerr=err, capsize=6, color=cols, edgecolor="#333")
    ax.axhline(0, color="#000", lw=0.8)
    for i, a in enumerate(series):
        ax.text(i, exp[i], f"{exp[i]:+.2f}R\nn={len(a)}", ha="center",
                va="bottom" if exp[i] >= 0 else "top", fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("expectancy (avg R / trade, EOD exit)")
    ax.set_title("Strict ORB (Concretum spec) vs random null — pooled NQ+ES+QQQ+SPY 30m\n"
                 f"first-bar direction + break, {STOP_ATR:.0%} daily-ATR stop, exit at close",
                 fontsize=10)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "orb_strict_backtest.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
