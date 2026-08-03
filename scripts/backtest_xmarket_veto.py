"""Cross-market breakout VETO on our stretched fades.

The Aug-3 NQ fade-short at 28,726 got run over because the S&P complex (ES/SPY)
was breaking out risk-on at the same moment — we faded the laggard into a
tape-wide breakout. This tests one rule:

    Skip a fade when the correlated LEADER is breaking out AGAINST it.
      follower NQ  <- leader ES
      follower QQQ <- leader SPY

Fade set = exactly our live setup: trend-gated fade at an A+ zone, with the
follower price stretched >= 0.5 session-sigma from VWAP in the fade's favour
(the same gate stretch_filter_test validated). Then, at the trigger bar's
timestamp, look at the leader:

    LEADER breaking out UP  (new session-high close, or leader >= +0.5 sigma)  -> veto a fade-SHORT
    LEADER breaking out DOWN (new session-low  close, or leader <= -0.5 sigma) -> veto a fade-LONG

No lookahead: leader state uses only bars up to the same timestamp. We then
compare the fades we KEEP vs the ones we SKIP vs the un-filtered baseline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
from scripts.backtest_trend_only import split_sessions, rth_of
from scripts.sim_15day import _run, _opp, macro_bias, BUF_F, WIN_F
from scripts.stretch_filter_test import session_stretch

ET = "America/New_York"
K_STRETCH = 0.5          # our live fade gate (follower must be extended)
K_LEADER = 0.5           # leader "risk-on/off" stretch threshold for the veto
PAIRS = [   # (follower_file, fut, leader_file, fut, bps)  — all matched timeframes
    ("nq_30min_eth.json", True,  "es_30min.json",    True,  13),
    ("nq_1h_eth.json",    True,  "es_1h.json",       True,  13),
    ("qqq_30min.json",    False, "spy_30min.json",   False, 13),
    ("qqq_1h.json",       False, "spy_1h.json",      False, 13),
    ("qqq_15min.json",    False, "spy_15min.json",   False, 13),
    ("qqq_30m_live.json", False, "spy_30m_live.json", False, 13),
]

# zone gates: strict = our live A+; broad = the wider "levels in range" set
GATES = {"A+ strict (w>=8 & nt>=2)": lambda z: z["w"] >= 8 and z["nt"] >= 2,
         "broad (w>=6 or nt>=3)":    lambda z: z["w"] >= 6 or z["nt"] >= 3}


def leader_state(lrth):
    """Per RTH bar: new-session-high-close, new-session-low-close, and stretch —
    all causal (bar j uses only bars 0..j)."""
    lh, ll, lc = lrth["high"].values, lrth["low"].values, lrth["close"].values
    n = len(lc); bu = np.zeros(n, bool); bd = np.zeros(n, bool)
    for j in range(1, n):
        bu[j] = lc[j] > lh[:j].max()
        bd[j] = lc[j] < ll[:j].min()
    lst = session_stretch(lrth)
    return bu, bd, lst


def collect(gate):
    rows = []   # (R, side, vetoed, by_break, by_stretch)
    for ffile, ffut, lfile, lfut, bps in PAIRS:
        try:
            fdf = bt.load(ffile); ldf = bt.load(lfile)
        except FileNotFoundError:
            continue
        fdf, fids, fby = split_sessions(fdf, ffut)
        ldf, lids, lby = split_sessions(ldf, lfut)
        dclose = {pd.Timestamp(s).date(): float(rth_of(fby[s])["close"].iloc[-1])
                  for s in fids if len(rth_of(fby[s]))}
        daily = pd.Series(dclose).sort_index()
        lset = set(lids)
        for i, s in enumerate(fids):
            if i < 20 or s not in lset:
                continue
            date = pd.Timestamp(s).date()
            opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            hist = fdf[fdf.index < opent]
            rth = rth_of(fby[s]); lrth = rth_of(lby[s])
            if len(hist) < 60 or len(rth) < 5 or len(lrth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0])
            zs, px = bt.build(hist, fby[fids[i - 1]], bps)
            az = [dict(z, bias=bias) for z in zs
                  if gate(z) and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            st = session_stretch(rth)
            ts = list(rth.index)
            bu, bd, lst = leader_state(lrth)
            lpos = {t: j for j, t in enumerate(lrth.index)}
            arr = rth.reset_index(drop=True)
            used = set()
            for bi in range(len(arr) - 1):
                h, l, c = arr["high"][bi], arr["low"][bi], arr["close"][bi]
                for zi, z in enumerate(az):
                    if zi in used:
                        continue
                    lo, hi = z["lo"], z["hi"]
                    side = 0
                    if h >= lo and c < lo and z["bias"] < 0:
                        side = -1; stop = hi + BUF_F * px
                        t = _run(arr, bi, bi + 1, c, stop, _opp(az, z, "down", c, stop), -1, z)
                    elif l <= hi and c > hi and z["bias"] > 0:
                        side = 1; stop = lo - BUF_F * px
                        t = _run(arr, bi, bi + 1, c, stop, _opp(az, z, "up", c, stop), 1, z)
                    else:
                        continue
                    used.add(zi)
                    if not t:
                        continue
                    dstretch = st[bi] if side < 0 else -st[bi]
                    if dstretch < K_STRETCH:              # our live setup requires extension
                        continue
                    j = lpos.get(ts[bi])
                    by_break = by_stretch = False
                    if j is not None:
                        if side < 0:                      # fade-short: leader breaking UP vetoes
                            by_break = bool(bu[j])
                            by_stretch = lst[j] >= K_LEADER
                        else:                             # fade-long: leader breaking DOWN vetoes
                            by_break = bool(bd[j])
                            by_stretch = lst[j] <= -K_LEADER
                    vetoed = by_break or by_stretch
                    rows.append((t["R"], side, vetoed, by_break, by_stretch))
    return rows


def stat(g):
    g = np.asarray(g)
    if len(g) == 0:
        return "   (no trades)"
    w = (g > 0).mean(); se = g.std(ddof=1) / len(g) ** 0.5 if len(g) > 1 else 0
    return f"n={len(g):4d}  win={w:4.0%}  exp={g.mean():+.2f}R (±{1.96*se:.2f})  netR={g.sum():+6.1f}"


def main():
    print("CROSS-MARKET BREAKOUT VETO on stretched fades — follower NQ<-ES, QQQ<-SPY")
    print("(fade only if follower >= +0.5s from VWAP; skip if leader breaks against it)\n")
    keep_broad = None
    for label, gate in GATES.items():
        rows = collect(gate)
        R = np.array([r[0] for r in rows])
        veto = np.array([r[2] for r in rows], bool)
        brk = np.array([r[3] for r in rows], bool)
        strc = np.array([r[4] for r in rows], bool)
        print(f"===== zone gate: {label} =====")
        if len(R) == 0:
            print("  (no fades)\n"); continue
        print(f"  BASELINE all stretched fades : {stat(R)}")
        print(f"  KEEP  leader not against it  : {stat(R[~veto])}")
        print(f"  SKIP  leader breaking against: {stat(R[veto])}")
        if (~veto).any():
            print(f"    -> filter lift = {R[~veto].mean() - R.mean():+.2f}R  (drops {veto.mean():.0%} of fades)")
        print(f"    veto by new-extreme break : {stat(R[brk])}")
        print(f"    veto by leader >={K_LEADER:.1f}s   : {stat(R[strc])}\n")
        if label.startswith("broad"):
            keep_broad = (R, veto)
    if keep_broad:
        _chart(*keep_broad)


def _chart(R, veto):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = [("all fades\n(baseline)", np.ones_like(R, bool), "#607d8b"),
              ("KEEP\n(leader agrees/quiet)", ~veto, "#2e7d32"),
              ("SKIP\n(leader breaking\nagainst us)", veto, "#c62828")]
    exps = [R[m].mean() if m.any() else 0 for _, m, _ in groups]
    errs = [1.96 * R[m].std(ddof=1) / m.sum() ** 0.5 if m.sum() > 1 else 0 for _, m, _ in groups]
    ns = [int(m.sum()) for _, m, _ in groups]
    cols = [c if (e >= 0 or i == 2) else c for i, ((_, _, c), e) in enumerate(zip(groups, exps))]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.bar(x, exps, 0.6, yerr=errs, capsize=6, color=[g[2] for g in groups], edgecolor="#333")
    ax.axhline(0, color="#000", lw=0.8)
    for i, e in enumerate(exps):
        ax.text(i, e, f"{e:+.2f}R\nn={ns[i]}", ha="center",
                va="bottom" if e >= 0 else "top", fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylabel("expectancy (avg R / fade)")
    ax.set_title("Cross-market breakout veto on our stretched fades\n"
                 "follower NQ<-ES, QQQ<-SPY — skip fades when the leader breaks against us",
                 fontsize=10)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "xmarket_veto.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
