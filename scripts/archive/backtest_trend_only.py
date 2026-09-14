"""Proper multi-instrument backtest + logic stress test of the TREND-ONLY,
MACRO-DAILY-BIAS confluence fade — across as much history as we hold.

Pools NQ+ES (futures) and QQQ+SPY (proxies), 1h & 30m, ~Nov 2025 - Jul 2026,
i.e. multiple regimes (late-2025 grind up, early-2026 wobble, the Jun-Jul
sell-off). For every session after warmup:
  * derive a DAILY close series from the file's own session closes;
  * macro_bias as-of the open from the 10/20-day SMA + 20d slope of PRIOR
    daily closes only (no lookahead) -> up / down / flat;
  * build pre-open confluence zones from that instrument's prior bars;
  * take the mechanical fade on a 30-min/1h close back off an A+ zone.

LOGIC STRESS TEST — same zones, same triggers, three gates:
  (a) WITH the macro trend gate   (short resistance only in a down tape, etc.)
  (b) INVERTED gate               (counter-trend — should be worse if real)
  (c) NO gate (two-sided)         (the original book)
Reports expectancy (avg R), win%, net R for each, plus a random-LEVEL null,
broken out by bias-regime and by month. If (a) doesn't beat (b) and (c), the
trend filter isn't doing real work.
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
from scripts.sim_15day import _run, _opp, macro_bias, BUF_F, WIN_F

ET = "America/New_York"
RNG = np.random.default_rng(20260730)

# (file, is_futures, bars_per_rth_session)
SERIES = [
    ("qqq_1h.json", False, 7), ("spy_1h.json", False, 7),
    ("es_1h.json", True, 7), ("nq_1h_eth.json", True, 7),
    ("qqq_30min.json", False, 13), ("spy_30min.json", False, 13),
    ("es_30min.json", True, 13), ("nq_30min_eth.json", True, 13),
]


def split_sessions(df, fut):
    s = pd.Series(df.index.date, index=df.index)
    if fut:
        ev = df.index.hour >= 18
        s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def rth_of(g):
    return g[(g.index.time >= pd.Timestamp("09:30").time()) &
             (g.index.time < pd.Timestamp("16:00").time())]


def sim_gate(rth, az, gate, px):
    """gate: 'with' | 'inv' | 'both' vs the passed per-zone bias already in az.
    az items carry z['bias'] = macro bias for the session. Returns list of R."""
    buf = BUF_F * px
    arr = rth.reset_index(drop=True)
    out, used = [], set()
    for i in range(len(arr) - 1):
        h, l, c = arr["high"][i], arr["low"][i], arr["close"][i]
        for zi, z in enumerate(az):
            if zi in used:
                continue
            b = z["bias"] if gate == "with" else (-z["bias"] if gate == "inv" else None)
            lo, hi = z["lo"], z["hi"]
            if h >= lo and c < lo:                       # resistance -> short
                if gate != "both" and not (b < 0):
                    continue
                t = _run(arr, i, i + 1, c, hi + buf, _opp(az, z, "down", c, hi + buf), -1, z)
            elif l <= hi and c > hi:                     # support -> long
                if gate != "both" and not (b > 0):
                    continue
                t = _run(arr, i, i + 1, c, lo - buf, _opp(az, z, "up", c, lo - buf), 1, z)
            else:
                continue
            used.add(zi)
            if t:
                out.append(t)
    return out


def main():
    trades = {"with": [], "inv": [], "both": []}
    null_R = []
    n_sess = defaultdict(int)   # sessions by bias regime
    warmup = 20                 # sessions needed for the 20-day macro bias

    for fname, fut, bps in SERIES:
        try:
            df = bt.load(fname)
        except FileNotFoundError:
            continue
        df, ids, bysess = split_sessions(df, fut)
        # daily close series from this file's own session RTH closes
        dclose = {}
        for s in ids:
            r = rth_of(bysess[s])
            if len(r):
                dclose[pd.Timestamp(s).date()] = float(r["close"].iloc[-1])
        daily = pd.Series(dclose).sort_index()

        for i, s in enumerate(ids):
            if i < warmup:
                continue
            date = pd.Timestamp(s).date()
            opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            hist = df[df.index < opent]
            if len(hist) < 60:
                continue
            rth = rth_of(bysess[s])
            if len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            regime = {1: "up", -1: "down", 0: "flat"}[bias]
            n_sess[regime] += 1
            if bias == 0:
                continue  # stand aside, no trades this session
            openp = float(rth["open"].iloc[0])
            zs, px = bt.build(hist, bysess[ids[i - 1]], bps)
            az = [dict(z, bias=bias) for z in zs
                  if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            mon = f"{date:%Y-%m}"
            for t in sim_gate(rth, az, "with", px):
                trades["with"].append(dict(R=t["R"], regime=regime, mon=mon))
            for t in sim_gate(rth, az, "inv", px):
                trades["inv"].append(dict(R=t["R"], regime=regime, mon=mon))
            for t in sim_gate(rth, az, "both", px):
                trades["both"].append(dict(R=t["R"], regime=regime, mon=mon))
            # random-LEVEL null: same count as az, same trend gate ('with')
            rng_lo = hist["low"].iloc[-bps * 5:].min(); rng_hi = hist["high"].iloc[-bps * 5:].max()
            hw = 0.0009 * px
            nz = [dict(lo=(lvl := RNG.uniform(rng_lo, rng_hi)) - hw, hi=lvl + hw,
                       lo_=lvl - hw, price=lvl, bias=bias) for _ in range(len(az))]
            for z in nz:  # give null zones a real price/lo/hi so _opp works
                z["lo"], z["hi"] = z["lo"], z["hi"]
            for t in sim_gate(rth, nz, "with", px):
                null_R.append(t["R"])

    def stat(rs):
        if not rs:
            return "     (no trades)"
        a = np.array([r["R"] if isinstance(r, dict) else r for r in rs])
        w = (a > 0).mean()
        exp = a.mean()
        se = a.std(ddof=1) / len(a) ** 0.5 if len(a) > 1 else 0
        return f"n={len(a):4d}  win={w:3.0%}  netR={a.sum():+6.1f}  exp={exp:+.2f}R  (±{1.96*se:.2f})"

    print("TREND-ONLY MACRO-BIAS BACKTEST — pooled NQ+ES+QQQ+SPY, 1h+30m, ~Nov'25-Jul'26")
    print(f"sessions by macro bias:  down={n_sess['down']}  up={n_sess['up']}  flat/aside={n_sess['flat']}\n")
    print("LOGIC STRESS TEST (identical zones & triggers, gate swapped):")
    print(f"  (a) WITH trend gate : {stat(trades['with'])}")
    print(f"  (b) INVERTED gate   : {stat(trades['inv'])}   <- counter-trend, should be worst")
    print(f"  (c) NO gate (2-side): {stat(trades['both'])}")
    print(f"  random-LEVEL null   : {stat(null_R)}   <- zones replaced by random prices\n")

    print("(a) WITH gate — by bias regime the trade was taken under:")
    for reg in ("down", "up"):
        g = [t for t in trades["with"] if t["regime"] == reg]
        print(f"    {reg:5s}: {stat(g)}")
    print("\n(a) WITH gate — by month:")
    for mon in sorted({t["mon"] for t in trades["with"]}):
        g = [t for t in trades["with"] if t["mon"] == mon]
        print(f"    {mon}: {stat(g)}")

    _chart(trades, null_R)


def _chart(trades, null_R):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def arr(rs):
        return np.array([r["R"] if isinstance(r, dict) else r for r in rs])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.2))

    # panel 1: expectancy per variant with 95% CI  (the stress test)
    labels = ["WITH\ntrend gate", "two-sided\n(no gate)", "INVERTED\n(counter)", "random\nlevels"]
    data = [arr(trades["with"]), arr(trades["both"]), arr(trades["inv"]), arr(null_R)]
    exps = [d.mean() for d in data]
    err = [1.96 * d.std(ddof=1) / len(d) ** 0.5 for d in data]
    cols = ["#2e7d32" if e > 0 else "#c62828" for e in exps]
    ax1.bar(range(4), exps, yerr=err, capsize=6, color=cols, alpha=0.85, edgecolor="#333")
    ax1.axhline(0, color="#000", lw=0.8)
    for i, (e, d) in enumerate(zip(exps, data)):
        ax1.text(i, e + (0.008 if e >= 0 else -0.014), f"{e:+.2f}R\nn={len(d)}",
                 ha="center", va="bottom" if e >= 0 else "top", fontsize=8.5, fontweight="bold")
    ax1.set_xticks(range(4)); ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("expectancy (avg R / trade)")
    ax1.set_title("Logic stress test — expectancy by gate (95% CI)\n"
                  "ordering is right (with > none > counter > random) but all CIs straddle 0",
                  fontsize=10)

    # panel 2: monthly net R for the WITH-gate variant + cumulative
    mons = sorted({t["mon"] for t in trades["with"]})
    net = [sum(t["R"] for t in trades["with"] if t["mon"] == m) for m in mons]
    cum = np.cumsum(net)
    bc = ["#2e7d32" if v > 0 else "#c62828" for v in net]
    ax2.bar(range(len(mons)), net, color=bc, alpha=0.8, edgecolor="#333", label="monthly net R")
    ax2.plot(range(len(mons)), cum, "-o", color="#1a237e", lw=1.8, ms=4, label="cumulative R")
    ax2.axhline(0, color="#000", lw=0.8)
    ax2.set_xticks(range(len(mons))); ax2.set_xticklabels([m[2:] for m in mons], fontsize=8, rotation=45)
    ax2.set_ylabel("R"); ax2.legend(fontsize=8, loc="upper left")
    ax2.set_title("WITH-gate net R by month — the whole curve rests on April\n"
                  "(strip one month and it's flat-to-negative → not a robust edge)", fontsize=10)

    fig.suptitle("Trend-only macro-bias confluence fade — multi-instrument backtest (~Nov'25–Jul'26, NQ+ES+QQQ+SPY)",
                 fontsize=12, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "trend_only_backtest.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
