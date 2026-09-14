"""Backtest the credible, non-guru intraday strategies on OUR data, held to the
same bar as everything else (R-expectancy vs a random null).

  ORB          - Concretum Opening-Range Breakout: break of the first 30-min bar,
                 stop = other side of the OR, target 2R (else flat at session close).
  HOLY GRAIL   - Linda Raschke: ADX(14) > thr trend + pull-back to the 20-EMA,
                 enter on the break of the pull-back bar, stop = pull-back extreme.
  FAILURE TEST - Raschke 'Turtle Soup' / Grimes 'anti': new high/low beyond the
                 prior-day extreme that CLOSES back inside -> fade it.

Pooled NQ+ES+QQQ+SPY (30-min). One trade per setup per session, RTH only, target
2R / stop / session-close. NULL: matched random entries (same risk, random side).
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
TGT_R = 2.0
ADX_THR = 25.0
SERIES = [   # deepest 30-min files we hold
    ("qqq_30min.json", False), ("spy_30min.json", False),
    ("es_30min.json", True),   ("nq_30min_eth.json", True),
    ("qqq_30m_live.json", False), ("spy_30m_live.json", False),
]
OPEN = pd.Timestamp("09:30").time(); CLOSE = pd.Timestamp("16:00").time()


def indicators(df):
    c, h, l = df["close"], df["high"], df["low"]
    ema = c.ewm(span=20, adjust=False).mean()
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    up, dn = h.diff(), -l.diff()
    pdm = ((up > dn) & (up > 0)) * up
    mdm = ((dn > up) & (dn > 0)) * dn
    tr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / tr14
    mdi = 100 * mdm.ewm(alpha=1 / 14, adjust=False).mean() / tr14
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / 14, adjust=False).mean()
    return ema.values, adx.values


def sess_ids(df, fut):
    s = pd.Series(df.index.date, index=df.index)
    if fut:
        ev = df.index.hour >= 18
        s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    return pd.to_datetime(s.values)


def run(h, l, c, start, entry, stop, side):
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    tgt = entry + side * TGT_R * risk
    for j in range(start, len(c)):
        if side > 0:
            if l[j] <= stop: return -1.0
            if h[j] >= tgt: return TGT_R
        else:
            if h[j] >= stop: return -1.0
            if l[j] <= tgt: return TGT_R
    return (c[-1] - entry) / risk * side          # flat at close


def orb(h, l, c):
    orh, orl = h[0], l[0]
    for i in range(1, len(c) - 1):
        if h[i] >= orh:
            return run(h, l, c, i + 1, orh, orl, +1)
        if l[i] <= orl:
            return run(h, l, c, i + 1, orl, orh, -1)
    return None


def holy_grail(h, l, c, ema, adx):
    for i in range(2, len(c) - 1):
        if np.isnan(adx[i]) or adx[i] < ADX_THR:
            continue
        if c[i] > ema[i] and ema[i] > ema[i - 2] and l[i] <= ema[i] and h[i + 1] >= h[i]:
            return run(h, l, c, i + 2, h[i], l[i], +1)
        if c[i] < ema[i] and ema[i] < ema[i - 2] and h[i] >= ema[i] and l[i + 1] <= l[i]:
            return run(h, l, c, i + 2, l[i], h[i], -1)
    return None


def failure_test(h, l, c, pdh, pdl, px):
    buf = 0.0006 * px
    broke_up = broke_dn = False; hi = lo = 0.0
    for i in range(len(c) - 1):
        if h[i] > pdh:
            broke_up = True; hi = max(hi, h[i])
        if broke_up and c[i] < pdh:
            return run(h, l, c, i + 1, c[i], hi + buf, -1)
        if l[i] < pdl:
            broke_dn = True; lo = min(lo, l[i]) if lo else l[i]
        if broke_dn and c[i] > pdl:
            return run(h, l, c, i + 1, c[i], lo - buf, +1)
    return None


def main():
    R = {"ORB": [], "HOLY": [], "FAIL": []}
    N = {"ORB": [], "HOLY": [], "FAIL": []}
    for fname, fut in SERIES:
        try:
            df = bt.load(fname)
        except FileNotFoundError:
            continue
        ema, adx = indicators(df)
        df = df.assign(ema=ema, adx=adx, sess=sess_ids(df, fut))
        ids = sorted(df["sess"].unique())
        prev_rth = None
        for k, s in enumerate(ids):
            g = df[df["sess"] == s]
            rr = g[(g.index.time >= OPEN) & (g.index.time < CLOSE)]
            if k < 20 or len(rr) < 6:
                if len(rr) >= 4:
                    prev_rth = rr
                continue
            h, l, c = rr["high"].values, rr["low"].values, rr["close"].values
            emar, adxr = rr["ema"].values, rr["adx"].values
            px = float(c[0])
            res = {"ORB": orb(h, l, c), "HOLY": holy_grail(h, l, c, emar, adxr)}
            if prev_rth is not None:
                res["FAIL"] = failure_test(h, l, c, float(prev_rth["high"].max()),
                                           float(prev_rth["low"].min()), px)
            else:
                res["FAIL"] = None
            for name, r in res.items():
                if r is not None:
                    R[name].append(r)
                    # matched null: random entry bar, random side, same-ish risk
                    i = RNG.integers(0, len(c) - 1)
                    side = RNG.choice([-1, 1])
                    stopdist = 0.004 * px
                    stop = c[i] - side * stopdist
                    rn = run(h, l, c, i + 1, c[i], stop, side)
                    if rn is not None:
                        N[name].append(rn)
            prev_rth = rr

    def stat(a):
        a = np.array(a)
        if len(a) == 0:
            return "      (none)"
        se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return f"n={len(a):4d}  win={(a>0).mean():4.0%}  exp={a.mean():+.2f}R (±{1.96*se:.2f})  netR={a.sum():+6.1f}"

    print(f"CREDIBLE-STRATEGY BACKTEST — pooled NQ+ES+QQQ+SPY 30-min, target {TGT_R}R, ADX>{ADX_THR:.0f}\n")
    names = [("ORB  (Concretum opening-range break)", "ORB"),
             ("HOLY GRAIL (Raschke ADX + 20-EMA pullback)", "HOLY"),
             ("FAILURE TEST (Raschke/Grimes fade failed break)", "FAIL")]
    for label, key in names:
        print(f"{label}")
        print(f"    strategy : {stat(R[key])}")
        print(f"    null     : {stat(N[key])}")
        if R[key] and N[key]:
            print(f"    edge vs null = {np.mean(R[key]) - np.mean(N[key]):+.2f}R\n")
        else:
            print()

    _chart(R, N, names)


def _chart(R, N, names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = [k for _, k in names]; labels = ["ORB", "Holy Grail", "Failure Test"]
    x = np.arange(len(keys)); w = 0.38
    rexp = [np.mean(R[k]) if R[k] else 0 for k in keys]
    nexp = [np.mean(N[k]) if N[k] else 0 for k in keys]
    rerr = [1.96 * np.std(R[k], ddof=1) / len(R[k]) ** 0.5 if len(R[k]) > 1 else 0 for k in keys]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    b1 = ax.bar(x - w / 2, rexp, w, yerr=rerr, capsize=5, color=["#2e7d32" if e > 0 else "#c62828" for e in rexp],
                edgecolor="#333", label="strategy")
    ax.bar(x + w / 2, nexp, w, color="#9e9e9e", alpha=0.8, edgecolor="#333", label="random null")
    ax.axhline(0, color="#000", lw=0.8)
    for i, k in enumerate(keys):
        ax.text(i - w / 2, rexp[i], f"{rexp[i]:+.2f}R\nn={len(R[k])}", ha="center",
                va="bottom" if rexp[i] >= 0 else "top", fontsize=8, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("expectancy (avg R / trade)"); ax.legend()
    ax.set_title(f"Credible non-guru strategies on our data — expectancy vs null "
                 f"(pooled NQ+ES+QQQ+SPY 30m, {TGT_R}R target)", fontsize=10)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "pros_backtest.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
