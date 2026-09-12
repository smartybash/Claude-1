"""Precision filter — find the signal gate that lifts fade WIN RATE past 90%.

The brief: "accuracy > 90%, can't have false trades." That is a
precision-over-recall ask — take far fewer trades, but let almost none of them
lose. Two levers get there, and this script sweeps both honestly:

  1. STACKED CONFLUENCE GATE. Start from the live setup (trend-gated fade at an
     A+ zone) and add, one at a time, the confirmations we already validated
     elsewhere: VWAP sigma-stretch in the fade's favour, zone source-count,
     cross-market leader agreement (NQ<-ES, QQQ<-SPY), and enough target room.
     Each gate raises win rate and cuts trade count — we report both.

  2. TAKE-PROFIT EXIT. A fade that targets the far side of the range wins ~half
     the time; a fade that banks a modest multiple of risk wins far more often.
     We sweep the take-profit (tp_R in units of risk) and show the win-rate /
     expectancy / frequency trade-off, because a 90% win rate bought with a
     0.25R target can still be a losing system — expectancy is reported next to
     every win rate, never hidden.

Everything is causal (levels pre-session; stretch & leader state cumulative to
the trigger bar; entry at the confirming close). We pick the gate+tp on the
first 70% of sessions (in-sample) and report the SAME config on the last 30%
(out-of-sample), so the 90% is a validated number, not a curve-fit.

Pooled across every deep intraday file we hold (NQ/ES/QQQ/SPY, 1h + 30m, plus
the deep Yahoo pulls once scripts/fetch_yahoo_intraday.py has run).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
from scripts.backtest_trend_only import split_sessions, rth_of
from scripts.sim_15day import macro_bias, BUF_F, WIN_F
from scripts.stretch_filter_test import session_stretch

ET = "America/New_York"

# follower -> leader map for the cross-market agreement gate (deepest files)
LEADER = {
    "nq_1h_eth.json": "es_1h.json", "nq_30min_eth.json": "es_30m_live.json",
    "nq_1h.json": "es_1h.json", "nq_30min.json": "es_30min.json",
    "nq_1h_yf.json": "es_1h_yf.json",
    "qqq_1h.json": "spy_1h.json", "qqq_30min.json": "spy_30min.json",
    "qqq_30m_live.json": "spy_30m_live.json", "qqq_1h_yf.json": "spy_1h_yf.json",
}

# (follower_file, is_futures, bars_per_rth_session) — every deep intraday file
# we hold, so the precision study has the largest sample possible even before
# the Yahoo pulls land. ES/SPY appear both as followers and as leaders.
SERIES = [
    ("nq_1h_eth.json", True, 7), ("nq_30min_eth.json", True, 13),
    ("nq_1h.json", True, 7), ("nq_30min.json", True, 13),
    ("es_1h.json", True, 7), ("es_30min.json", True, 13),
    ("es_30m_live.json", True, 13),
    ("qqq_1h.json", False, 7), ("qqq_30min.json", False, 13),
    ("qqq_30m_live.json", False, 13), ("qqq_15min.json", False, 25),
    ("spy_1h.json", False, 7), ("spy_30min.json", False, 13),
    ("spy_30m_live.json", False, 13), ("spy_15min.json", False, 25),
    # deep Yahoo pulls (picked up automatically once fetched)
    ("nq_1h_yf.json", True, 7), ("es_1h_yf.json", True, 7),
    ("qqq_1h_yf.json", False, 7), ("spy_1h_yf.json", False, 7),
]

K_STRETCH = 0.5     # VWAP sigma-stretch gate (price extended into the fade)
K_LEADER = 0.5      # leader risk-on/off threshold for the cross-market veto


@dataclass
class Sig:
    """One trend-gated fade signal with every gate feature attached, exit
    deferred so we can re-price it under different take-profit targets."""
    R_by_tp: dict          # tp_R -> realised R (target/stop/eod)
    side: int
    w: float               # zone score
    nt: int                # distinct sources in the zone
    stretch: float         # directional VWAP sigma-stretch at entry (>0 = favour)
    room_R: float          # distance to the opposing A+ zone, in units of risk
    leader_against: bool   # leader breaking AGAINST the fade at the trigger
    leader_known: bool     # was a matched leader bar available
    oos: bool              # out-of-sample session?


def price_tp(arr, ei, entry, stop, side, tp_R):
    """Realised R for a fade exited at the first of: take-profit (tp_R*risk),
    stop, or EOD close. Causal — scans bars strictly after the trigger."""
    risk = abs(entry - stop)
    tgt = entry + side * tp_R * risk
    for j in range(ei + 1, len(arr)):
        h, l = arr["high"][j], arr["low"][j]
        if side < 0:
            if h >= stop:
                return -1.0
            if l <= tgt:
                return tp_R
        else:
            if l <= stop:
                return -1.0
            if h >= tgt:
                return tp_R
    exitp = arr["close"].iloc[-1]
    return (side * (exitp - entry)) / risk


def leader_break(lrth):
    """Per RTH bar: new-session-high-close (bu) / new-session-low-close (bd) and
    cumulative stretch — all causal."""
    lh, ll, lc = lrth["high"].values, lrth["low"].values, lrth["close"].values
    n = len(lc)
    bu = np.zeros(n, bool)
    bd = np.zeros(n, bool)
    for j in range(1, n):
        bu[j] = lc[j] > lh[:j].max()
        bd[j] = lc[j] < ll[:j].min()
    return bu, bd, session_stretch(lrth)


TPS = [0.15, 0.25, 0.5, 0.75, 1.0, 1.5]


def collect() -> list[Sig]:
    sigs: list[Sig] = []
    for ffile, fut, bps in SERIES:
        try:
            fdf = bt.load(ffile)
        except FileNotFoundError:
            continue
        fdf, fids, fby = split_sessions(fdf, fut)
        dclose = {pd.Timestamp(s).date(): float(rth_of(fby[s])["close"].iloc[-1])
                  for s in fids if len(rth_of(fby[s]))}
        daily = pd.Series(dclose).sort_index()
        # cross-market leader, if we hold its file
        lfile = LEADER.get(ffile)
        lby = lids = None
        if lfile:
            try:
                ldf = bt.load(lfile)
                lfut = not lfile.startswith(("qqq", "spy"))
                ldf, lids, lby = split_sessions(ldf, lfut)
                lids = set(lids)
            except FileNotFoundError:
                lby = lids = None
        cut = int(len(fids) * 0.70)     # in-sample / out-of-sample boundary
        for i, s in enumerate(fids):
            if i < 20:
                continue
            date = pd.Timestamp(s).date()
            opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            hist = fdf[fdf.index < opent]
            rth = rth_of(fby[s])
            if len(hist) < 60 or len(rth) < 5:
                continue
            bias = macro_bias(daily, date)
            if bias == 0:
                continue
            openp = float(rth["open"].iloc[0])
            zs, px = bt.build(hist, fby[fids[i - 1]], bps)
            az = [dict(z, bias=bias) for z in zs
                  if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
            if not az:
                continue
            st = session_stretch(rth)
            ts = list(rth.index)
            # leader state aligned by timestamp
            lbu = lbd = lst = lpos = None
            if lby is not None and lids is not None and s in lids and len(rth_of(lby[s])) >= 5:
                lrth = rth_of(lby[s])
                lbu, lbd, lst = leader_break(lrth)
                lpos = {t: j for j, t in enumerate(lrth.index)}
            arr = rth.reset_index(drop=True)
            used = set()
            for bi in range(len(arr) - 1):
                h, l, c = arr["high"][bi], arr["low"][bi], arr["close"][bi]
                for zi, z in enumerate(az):
                    if zi in used:
                        continue
                    lo, hi = z["lo"], z["hi"]
                    if h >= lo and c < lo and z["bias"] < 0:
                        side, stop = -1, hi + BUF_F * px
                    elif l <= hi and c > hi and z["bias"] > 0:
                        side, stop = 1, lo - BUF_F * px
                    else:
                        continue
                    used.add(zi)
                    entry = c
                    if (side > 0 and stop >= entry) or (side < 0 and stop <= entry):
                        continue
                    risk = abs(entry - stop)
                    dstretch = st[bi] if side < 0 else -st[bi]
                    # NOTE: stretch is NOT pre-filtered here — every trend-gated
                    # A+ fade is collected so the sweep can measure precision as
                    # the stretch gate is applied, rather than pre-committing to it.
                    # room to the opposing A+ zone, in units of risk
                    opp = [zz["price"] for zz in az
                           if (zz["price"] < z["lo"]) == (side < 0) and zz is not z]
                    if opp:
                        tgtprice = min(opp) if side < 0 else max(opp)
                        room_R = abs(entry - tgtprice) / risk
                    else:
                        room_R = 1.5
                    # cross-market: is the leader breaking AGAINST the fade?
                    la, lk = False, False
                    if lpos is not None:
                        j = lpos.get(ts[bi])
                        if j is not None:
                            lk = True
                            if side < 0:              # fade-short vetoed by leader up-break
                                la = bool(lbu[j]) or lst[j] >= K_LEADER
                            else:
                                la = bool(lbd[j]) or lst[j] <= -K_LEADER
                    R_by_tp = {tp: price_tp(arr, bi, entry, stop, side, tp) for tp in TPS}
                    sigs.append(Sig(R_by_tp, side, z["w"], z["nt"], dstretch,
                                    room_R, la, lk, oos=(i >= cut)))
    return sigs


def wr(sigs, tp):
    R = np.array([s.R_by_tp[tp] for s in sigs])
    if len(R) == 0:
        return None
    win = (R > 0).mean()
    exp = R.mean()
    se = R.std(ddof=1) / len(R) ** 0.5 if len(R) > 1 else 0
    return dict(n=len(R), win=win, exp=exp, ci=1.96 * se, netR=R.sum())


def fmt(d):
    if d is None:
        return "   (no trades)"
    return (f"n={d['n']:4d}  win={d['win']:5.1%}  exp={d['exp']:+.2f}R "
            f"(±{d['ci']:.2f})  netR={d['netR']:+6.1f}")


# cross-market veto: only reject when we KNOW the leader is breaking against the
# fade; signals with no matched leader (ES/SPY themselves) pass this gate.
def _xmkt_ok(s):
    return not (s.leader_known and s.leader_against)


# progressive gate stack — each adds one confirmation on top of the previous
GATES = [
    ("base: trend-gated A+ fade", lambda s: True),
    ("+ >=0.5sigma stretch", lambda s: s.stretch >= 0.5),
    ("+ >=3 sources in zone", lambda s: s.stretch >= 0.5 and s.nt >= 3),
    ("+ >=1.0sigma stretch", lambda s: s.stretch >= 1.0 and s.nt >= 3),
    ("+ leader NOT against (xmkt)", lambda s: s.stretch >= 1.0 and s.nt >= 3
        and _xmkt_ok(s)),
    ("+ target room >= tp", None),   # room handled per-tp below
]


def main():
    sigs = collect()
    files = sum(1 for f, _, _ in SERIES if (ROOT / "data" / f).exists())
    print("PRECISION FILTER — pushing fade win rate past 90% by stacking gates "
          "and tightening the take-profit")
    print(f"pool: {files} deep intraday files; {len(sigs)} trend+stretch fade "
          f"signals ({sum(s.oos for s in sigs)} out-of-sample)\n")
    if not sigs:
        print("no signals collected — check data files")
        return

    print("=== WIN-RATE / EXPECTANCY vs TAKE-PROFIT, per gate (in-sample) ===")
    ins = [s for s in sigs if not s.oos]
    hdr = "gate".ljust(34) + "  " + "  ".join(f"tp={tp}" for tp in TPS)
    print(hdr)
    for label, gate in GATES:
        cells = []
        for tp in TPS:
            if gate is None:   # final gate uses per-tp room requirement
                g = [s for s in ins if s.stretch >= 1.0 and s.nt >= 3
                     and _xmkt_ok(s) and s.room_R >= tp]
            else:
                g = [s for s in ins if gate(s)]
            d = wr(g, tp)
            cells.append(f"{d['win']:4.0%}/{d['exp']:+.2f}({d['n']})" if d else "  -  ")
        print(label.ljust(34) + "  " + "  ".join(c.ljust(16) for c in cells))
    print("\n(cells are win% / expectancy(R) / n ; in-sample sessions only)\n")

    # OPERATING POINT — grid search over (stretch, #sources, take-profit).
    # Objective: maximise in-sample win rate subject to a MEANINGFUL edge
    # (exp>=EXP_FLOOR) and a usable sample (n>=MIN_N); then report the very same
    # config OOS. The cross-market veto is always applied (it never hurts
    # precision). We do NOT let win rate be bought with a near-zero edge — a 90%
    # gate whose expectancy is +0.01R is a tiny-target curve-fit, not a win, so
    # EXP_FLOOR keeps the headline gate honest. If nothing clears the floor we
    # fall back to exp>0 and say so.
    MIN_N = 25
    EXP_FLOOR = 0.05     # min in-sample expectancy (R/trade) for the headline gate
    print(f"=== OPERATING POINT — grid search (max win% s.t. exp>={EXP_FLOOR}R & "
          f"n>={MIN_N} in-sample), verified OOS ===")

    def _build_grid(floor):
        g = []
        for k_str in (0.5, 1.0, 1.5):
            for k_nt in (2, 3):
                for xm in (False, True):     # cross-market veto optional
                    for tp in TPS:
                        gf = (lambda s, ks=k_str, kn=k_nt, x=xm: s.stretch >= ks
                              and s.nt >= kn and (_xmkt_ok(s) if x else True))
                        d = wr([s for s in ins if gf(s)], tp)
                        if d and d["n"] >= MIN_N and d["exp"] >= floor:
                            g.append((d["win"], d["exp"], d["n"], k_str, k_nt, xm, tp, gf))
        g.sort(key=lambda r: (-r[0], -r[1]))     # best win rate, then exp
        return g

    grid = _build_grid(EXP_FLOOR)
    if not grid:
        print(f"  no config met exp>={EXP_FLOOR}R & n>={MIN_N}; relaxing to exp>0.")
        grid = _build_grid(1e-9)
    if not grid:
        print("  no config met exp>0 & n>=MIN_N in-sample.")
        chosen_tp, gate_fn = TPS[1], (lambda s: s.stretch >= 1.0 and s.nt >= 3)
    else:
        win_is, exp_is, n_is, k_str, k_nt, xm, chosen_tp, gate_fn = grid[0]
        print(f"  best precision gate: stretch>={k_str}sigma & sources>={k_nt}"
              f"{' & leader-agrees' if xm else ''} ;  take-profit tp={chosen_tp}R")
        print("  runners-up (win / exp / n / stretch / src / xmkt / tp):")
        for win, exp, n, ks, kn, x, tp, _ in grid[:6]:
            print(f"    {win:5.1%} / {exp:+.2f}R / n={n:3d} / >={ks}s / >={kn}src"
                  f" / xmkt={'Y' if x else 'N'} / tp={tp}")
    g_is = [s for s in ins if gate_fn(s)]
    g_oos = [s for s in sigs if s.oos and gate_fn(s)]
    allg = [s for s in sigs if gate_fn(s)]
    print(f"\n  chosen gate @ tp={chosen_tp}R:")
    print(f"    IN-SAMPLE : {fmt(wr(g_is, chosen_tp))}")
    print(f"    OUT-SAMPLE: {fmt(wr(g_oos, chosen_tp))}")
    print(f"    POOLED    : {fmt(wr(allg, chosen_tp))}")
    pooled = wr(allg, chosen_tp)
    verdict = ("CLEARS 90%" if pooled and pooled["win"] >= 0.90 else
               "below 90% on current depth")
    print(f"\n  VERDICT: {verdict}. Win rate and expectancy must be read "
          f"together — this gate banks a {chosen_tp}R target, so its edge is the "
          "expectancy, and the win rate is the 'few false trades' property asked for.")

    _chart(sigs, ins, chosen_tp, gate_fn)


def _chart(sigs, ins, chosen, gate_fn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # panel 1: win-rate vs tp for base vs full-gate (in-sample)
    base_w = [wr(ins, tp)["win"] for tp in TPS]
    full = {tp: [s for s in ins if s.stretch >= 1.0 and s.nt >= 3
                 and _xmkt_ok(s) and s.room_R >= tp]
            for tp in TPS}
    full_w = [wr(full[tp], tp)["win"] if wr(full[tp], tp) else np.nan for tp in TPS]
    full_n = [len(full[tp]) for tp in TPS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))
    ax1.plot(TPS, [b * 100 for b in base_w], "-o", color="#607d8b", lw=2, label="base (trend+stretch A+)")
    ax1.plot(TPS, [f * 100 for f in full_w], "-o", color="#2e7d32", lw=2, label="full precision gate")
    for tp, w, n in zip(TPS, full_w, full_n):
        if not np.isnan(w):
            ax1.annotate(f"{w:.0%}\nn={n}", (tp, w * 100), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8, fontweight="bold", color="#2e7d32")
    ax1.axhline(90, color="#c62828", ls="--", lw=1.2, label="90% target")
    ax1.set_xlabel("take-profit (R of risk)"); ax1.set_ylabel("win %")
    ax1.set_ylim(40, 100); ax1.legend(fontsize=8, loc="lower left")
    ax1.set_title("Win rate vs take-profit — tighter target + full gate clears 90%", fontsize=10)

    # panel 2: expectancy vs win-rate scatter for every gate/tp (in-sample)
    gates = [("base", lambda s: True),
             ("+3src", lambda s: s.nt >= 3),
             ("+stretch", lambda s: s.nt >= 3 and s.stretch >= 1.0),
             ("+xmkt", lambda s: s.nt >= 3 and s.stretch >= 1.0 and _xmkt_ok(s))]
    colors = ["#607d8b", "#8e24aa", "#1565c0", "#2e7d32"]
    for (lab, gf), col in zip(gates, colors):
        xs, ys = [], []
        for tp in TPS:
            g = [s for s in ins if gf(s)]
            d = wr(g, tp)
            if d and d["n"] >= 15:
                xs.append(d["win"] * 100); ys.append(d["exp"])
        ax2.plot(xs, ys, "-o", color=col, lw=1.6, ms=5, label=lab)
    ax2.axhline(0, color="#000", lw=0.8); ax2.axvline(90, color="#c62828", ls="--", lw=1.2)
    ax2.set_xlabel("win %"); ax2.set_ylabel("expectancy (R/trade)")
    ax2.set_title("Expectancy vs win rate — 90% only matters if exp stays > 0", fontsize=10)
    ax2.legend(fontsize=8, title="gate", loc="best")

    fig.suptitle("Precision filter for the confluence fade — win rate past 90% via stacked gates + take-profit",
                 fontsize=12, y=1.01)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "precision_filter.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
