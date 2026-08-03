"""Live three-filter read: LOCATION + DIRECTION + EXTENSION — on ROLL-CONSISTENT
continuous futures data.

NQ auto-rolls quarterly (Mar/Jun/Sep/Dec). On 2026-07-31 the liquid front month
is Sep'26 (exp 2026-09-18); Dec'26 is the back month; next roll ~Sep 10. All
history here is taken on the SEP contract's own basis (single-basis = no roll
gap), spanning May->Jul, rather than a thin single-session pull. Prior fronts
(Jun/Mar) trade ~cost-of-carry below Sep and would need back-adjustment to
splice; we don't mix bases.

Three gates, TAKE only when all align:
  1. LOCATION  - A+/DENSE confluence zone (score>=8, >=2 distinct sources)
  2. DIRECTION - fade agrees with macro daily trend (10/20 SMA + slope), Sep basis
  3. EXTENSION - price >= 0.5 session-sigma from VWAP toward the zone (live; the
     overnight Globex VWAP now, resets at the 9:30 RTH open)
"""

from __future__ import annotations

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
from scripts.sim_15day import macro_bias, WIN_F, BUF_F

ET = "America/New_York"
LIVE_PX = 28570.5
K_STRETCH = 0.5
CHART_SESSIONS = 6


def sess_split(df):
    s = pd.Series(df.index.date, index=df.index)
    ev = df.index.hour >= 18
    s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def rth(g):
    return g[(g.index.time >= pd.Timestamp("09:30").time()) &
             (g.index.time < pd.Timestamp("16:00").time())]


def channel_fit(close, lookback=150, k=2.0, min_len=14):
    """Linear-regression channel over the CURRENT leg (objective, no lookahead).
    Anchor at the leg origin (window min for an up-leg / max for a down-leg),
    regress closes to now, rails = fit +/- k*residual-sigma. Returns anchor index,
    slope, and (mid, upper, lower) evaluated per bar from anchor to end."""
    n = len(close)
    lb = min(lookback, n)
    w = close[-lb:]; base = n - lb
    anchor = base + (int(np.argmin(w)) if close[-1] >= w[0] else int(np.argmax(w)))
    if n - anchor < min_len:                     # leg too short -> widen to window
        anchor = base
    x = np.arange(anchor, n)
    y = close[anchor:]
    slope, intercept = np.polyfit(x, y, 1)
    mid = slope * x + intercept
    sd = (y - mid).std()
    return anchor, slope, mid, mid + k * sd, mid - k * sd, sd


def macro_daily():
    """Sep-basis daily RTH closes from the 1h continuous front-month file."""
    df, ids, bysess = sess_split(bt.load("nq_1h_eth.json"))
    d = {pd.Timestamp(s).date(): float(rth(bysess[s])["close"].iloc[-1])
         for s in ids if len(rth(bysess[s]))}
    return pd.Series(d).sort_index()


def main():
    daily = macro_daily()
    df30, ids, bysess = sess_split(bt.load("nq_30min_eth.json"))
    cur_sess = ids[-1]
    cur_date = pd.Timestamp(cur_sess).date()
    px = LIVE_PX

    bias = macro_bias(daily, cur_date)
    bias_txt = {1: "UP", -1: "DOWN", 0: "MIXED"}[bias]
    s10 = daily.iloc[-10:].mean(); s20 = daily.iloc[-20:].mean()

    hist = df30[df30["sess"] < cur_sess]
    zs, _ = bt.build(hist, bysess[ids[-2]], 13)
    az = [z for z in zs if (z["w"] >= 6 or z["nt"] >= 3) and abs(z["price"] - px) <= 0.015 * px]
    az.sort(key=lambda z: z["price"], reverse=True)

    g = bysess[cur_sess]
    tp = (g["high"] + g["low"] + g["close"]) / 3
    v = g["volume"].clip(lower=1e-9); cv = v.cumsum()
    vwap = float(((tp * v).cumsum() / cv).iloc[-1])
    sd = float(np.sqrt(((tp - vwap) ** 2 * v).cumsum().iloc[-1] / cv.iloc[-1]))
    stretch = (px - vwap) / sd if sd else 0.0

    print(f"NQ three-filter read — {cur_date} PRE-OPEN (overnight)   price {px:.0f}")
    print(f"  CONTRACT: front Sep'26 (exp 09-18)  |  back Dec'26  |  next roll ~Sep 10  |  basis: Sep, single")
    print(f"  o/n range 28537-28698   +166 (+0.59%)  [new session Mon Aug 3, zones rebuilt]")
    print(f"  macro series: {len(daily)} Sep-basis daily closes {daily.index[0]}..{daily.index[-1]}\n")
    print(f"FILTER 2 DIRECTION : macro bias {bias_txt}  (10d SMA {s10:.0f} vs 20d SMA {s20:.0f}) "
          f"-> {'SHORT resistance only' if bias<0 else ('LONG support only' if bias>0 else 'stand aside')}\n")
    print(f"FILTER 3 EXTENSION : session VWAP {vwap:.0f}  sigma {sd:.0f}  stretch {stretch:+.2f}sigma "
          f"(need >={K_STRETCH} toward zone; RESETS 9:30)\n")
    # regression channel on the current leg (breakout / tap-retrace context)
    bars6 = pd.concat([bysess[s] for s in ids[-CHART_SESSIONS:]])
    cc = bars6["close"].values
    _, cslope, cmid, cup, clo, _ = channel_fit(cc)
    up_now, lo_now, mid_now = float(cup[-1]), float(clo[-1]), float(cmid[-1])
    pos = (px - lo_now) / (up_now - lo_now) if up_now > lo_now else 0.5
    where = "AT upper rail" if pos >= 0.85 else ("AT lower rail" if pos <= 0.15 else f"{pos:.0%} up-channel")
    print(f"CHANNEL (current leg, {'up' if cslope>0 else 'down'}): rails {lo_now:.0f} / {up_now:.0f}  "
          f"mid {mid_now:.0f}  -> price {where}")
    print(f"  breakout = 30m close beyond a rail; tap-retrace = wick to rail + close back in. "
          f"Best when a rail meets a level.\n")
    print("FILTER 1 LOCATION  - structure in play + full gate:\n")
    hdr = f"  {'zone':18s} {'grade':6s} {'side':5s} {'dir?':5s} {'stretch?':9s} {'rail?':6s}  VERDICT"
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    signals = []
    buf = BUF_F * px
    for z in az:
        grade = ("DENSE" if z["nt"] >= 4 else "A+") if z["w"] >= 8 else "wk"
        side = "short" if z["price"] > px else "long"
        dir_ok = (side == "short" and bias < 0) or (side == "long" and bias > 0)
        toward = stretch if side == "short" else -stretch
        str_ok = toward >= K_STRETCH
        rail_ok = bt.zone_rail_conf(cc, z["price"], 13, 0.003 * px)
        tagged = (px >= z["lo"]) if side == "short" else (px <= z["hi"])
        take = dir_ok and str_ok and z["w"] >= 8 and tagged
        why = []
        if not dir_ok: why.append("vs trend")
        if z["w"] < 8: why.append("not A+")
        if not tagged: why.append("untagged")
        if not str_ok: why.append(f"flat {toward:+.1f}s")
        tag = "TAKE" if take else "wait  (" + ", ".join(why) + ")"
        # rail+level is a BREAK signal, not a fade (backtest: break@rail +0.15R/69%
        # vs fade@rail -0.01R). Flag the trend-aligned break: support break in a
        # down tape / resistance break in an up tape.
        brk = (bias < 0 and side == "long") or (bias > 0 and side == "short")
        if rail_ok and brk:
            edge = z["lo"] if bias < 0 else z["hi"]
            tag += f"  [rail+level BREAK: {'short' if bias<0 else 'long'} on 30m close thru {edge:.0f}]"
        elif rail_ok:
            tag += "  [rail: break-risk]"
        print(f"  {z['lo']:.0f}-{z['hi']:.0f} @{z['price']:.0f}  {grade:6s} {side:5s} "
              f"{'yes' if dir_ok else 'no':5s} {'yes' if str_ok else 'no':9s} "
              f"{'YES' if rail_ok else 'no':6s}  {tag}")
        # ---- arm signals ----
        if dir_ok and z["w"] >= 8:                          # FADE (trend-aligned A+)
            sgn = -1 if side == "short" else 1
            entry = z["lo"] if side == "short" else z["hi"]
            stop = (z["hi"] + buf) if side == "short" else (z["lo"] - buf)
            signals.append(_mk("FADE", side, z, entry, stop, sgn, az,
                               f"price tags {entry:.0f} + >={K_STRETCH}sigma from RTH VWAP + rejection candle"))
        if rail_ok and brk:                                 # BREAK (rail+level, with trend)
            sgn = -1 if bias < 0 else 1
            edge = z["lo"] if bias < 0 else z["hi"]
            stop = (z["hi"] + buf) if bias < 0 else (z["lo"] - buf)
            signals.append(_mk("BREAK", "short" if bias < 0 else "long", z, edge, stop, sgn, az,
                               f"30m close thru {edge:.0f}"))

    print("\nARMED SIGNALS (trigger -> stop -> target; RTH session):")
    if not signals:
        print("  none — no trend-aligned A+ setup in range")
    for s in signals:
        print(f"  [{s['kind']:5s}] {s['side'].upper():5s} {s['zlabel']}")
        print(f"      trigger : {s['cond']}")
        print(f"      entry ~{s['entry']:.0f}   stop {s['stop']:.0f} ({s['risk']:.0f}pt)   "
              f"target {s['tgt']:.0f}   = {s['R']:.1f}R")
        print(f"      status  : {s['status']}")

    _chart(df30, ids, bysess, az, px, vwap, sd, bias, cur_date, signals)


def _mk(kind, side, z, entry, stop, sgn, az, cond):
    risk = abs(entry - stop)
    cands = [zz["price"] for zz in az if zz["w"] >= 8 and abs(zz["price"] - z["price"]) > 1
             and ((zz["price"] < entry) if sgn < 0 else (zz["price"] > entry))]
    tgt = (max(cands) if sgn < 0 else min(cands)) if cands else entry + sgn * 1.5 * risk
    R = abs(tgt - entry) / risk if risk else 0.0
    status = ("waiting for RTH VWAP" if kind == "FADE" else "armed — watching 30m closes")
    return dict(kind=kind, side=side, entry=entry, stop=stop, tgt=tgt, risk=risk, R=R,
                cond=cond, status=status, zlabel=f"{z['lo']:.0f}-{z['hi']:.0f} @{z['price']:.0f}",
                trigger=entry, sgn=sgn)


def _chart(df30, ids, bysess, az, px, vwap, sd, bias, cur_date, signals=()):
    show = ids[-CHART_SESSIONS:]
    bars = pd.concat([bysess[s] for s in show])
    a = bars.reset_index()
    fig, ax = plt.subplots(figsize=(15, 6.3))
    # session shading + dividers; build a real date/time timeline for the bottom axis
    xstart = 0
    xticks, xlabels = [], []
    ts = a["index"] if "index" in a.columns else a.iloc[:, 0]  # per-bar timestamp
    for k, s in enumerate(show):
        n = len(bysess[s])
        if k % 2 == 0:
            ax.axvspan(xstart - 0.5, xstart + n - 0.5, color="#f4f6f8", zorder=0)
        if k > 0:
            ax.axvline(xstart - 0.5, color="#cfd8dc", lw=0.8, zorder=0)
        # bottom tick at each session's RTH open (fallback: session start)
        gi = bysess[s]
        ropen = gi.index.get_indexer([gi[(gi.index.time >= pd.Timestamp("09:30").time())].index[0]])[0] \
            if len(gi[(gi.index.time >= pd.Timestamp("09:30").time())]) else 0
        d = pd.Timestamp(s)
        xticks.append(xstart + ropen)
        xlabels.append(d.strftime("%a %m-%d") + ("\n(pre-open)" if s == show[-1] else "\n09:30 ET"))
        xstart += n
    for i, row in a.iterrows():
        up = row["close"] >= row["open"]; c = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [row["low"], row["high"]], color=c, lw=0.7)
        ax.add_patch(Rectangle((i - 0.32, min(row["open"], row["close"])), 0.64,
                               abs(row["close"] - row["open"]) + 0.4, facecolor=c, edgecolor=c))
    m = len(a)
    proj = 8
    gx1, gx2, xr = m + proj + 1, m + proj + 9, m + proj + 18  # gutter cols: levels | signals | px/vwap
    # linear-regression channel on the current leg, projected forward
    anchor, slope, mid, up, lo, csd = channel_fit(a["close"].values)
    xs = np.arange(anchor, m)
    xf = np.arange(anchor, m + proj)
    midf = slope * xf + (mid[0] - slope * anchor)
    ax.plot(xf, midf, color="#5e35b1", lw=0.9, ls="-", zorder=3)
    ax.plot(xf, midf + (up - mid)[0], color="#5e35b1", lw=1.3, ls="--", zorder=3)
    ax.plot(xf, midf - (mid - lo)[0], color="#5e35b1", lw=1.3, ls="--", zorder=3)
    ax.fill_between(xf, midf - (mid - lo)[0], midf + (up - mid)[0],
                    color="#5e35b1", alpha=0.05, zorder=0)
    ax.plot([anchor], [a["close"].values[anchor]], marker="o", ms=6,
            mfc="none", mec="#5e35b1", mew=1.5, zorder=4)
    dirn = "up" if slope > 0 else "down"
    rail_now = slope * (m - 1) + (mid[0] - slope * anchor) + (up - mid)[0]  # upper rail at current bar (in view)
    ax.text(gx1, rail_now, f"chan {dirn} rail", color="#5e35b1",
            fontsize=7, va="center", ha="left", zorder=4, clip_on=True)
    for z in az:
        side = "short" if z["price"] > px else "long"
        dir_ok = (side == "short" and bias < 0) or (side == "long" and bias > 0)
        toward = ((px - vwap) / sd) * (1 if side == "short" else -1)
        tagged = (px >= z["lo"]) if side == "short" else (px <= z["hi"])
        take = dir_ok and toward >= K_STRETCH and z["w"] >= 8 and tagged
        col = "#d32f2f" if side == "short" else "#2e7d32"
        ax.add_patch(Rectangle((-0.5, z["lo"]), m + 3, max(z["hi"] - z["lo"], 8), facecolor=col,
                               alpha=0.24 if take else 0.09, edgecolor=col,
                               lw=2.2 if take else 1.0, ls="-" if take else "--", zorder=1))
        g = "DENSE" if z["nt"] >= 4 else ("A+" if z["w"] >= 8 else "wk")
        ax.text(gx1, z["price"], f"{z['price']:.0f} {g}" + ("  ★TAKE" if take else ""),
                color=col, fontsize=8, va="center", ha="left", fontweight="bold" if take else "normal")
    # armed-signal trigger + target in the far gutter column (dotted leader lines)
    for s in signals:
        tc = "#d32f2f" if s["side"] == "short" else "#2e7d32"
        ax.plot([m - 1, gx2], [s["trigger"], s["trigger"]], color=tc, lw=1.0, ls=":", zorder=4)
        ax.text(gx2, s["trigger"], f"{s['kind']} {s['side']} {s['trigger']:.0f}", color=tc,
                fontsize=6.5, va="center", ha="left")
        ax.plot([m - 1, gx2], [s["tgt"], s["tgt"]], color=tc, lw=0.9, ls=(0, (1, 2)), zorder=4)
        ax.text(gx2, s["tgt"], f"tgt {s['tgt']:.0f} ({s['R']:.1f}R)", color=tc, fontsize=6.5, va="center", ha="left")
    ax.axhline(px, color="#000", lw=1.4)
    ax.text(xr, px, f"px {px:.0f}", fontsize=8, va="center", ha="left", fontweight="bold", clip_on=True)
    ax.axhline(vwap, color="#1565c0", lw=1.0, ls="--")
    ax.text(xr, vwap, f"VWAP {vwap:.0f}", color="#1565c0", fontsize=7, va="center", ha="left", clip_on=True)
    bt_txt = {1: "UP", -1: "DOWN", 0: "MIXED"}[bias]
    ax.set_title(f"NQ Sep'26 — last {CHART_SESSIONS} sessions into {cur_date} (intraday)  "
                 f"[macro {bt_txt}; red=resist, green=support; ★=all 3 filters]", fontsize=11, fontweight="bold")
    ax.set_xticks(xticks); ax.set_xticklabels(xlabels, fontsize=8)
    ax.set_xlim(-2, xr + 22)                       # right gutter for labels
    ylo = min([a["low"].min()] + [z["lo"] for z in az])
    yhi = max([a["high"].max()] + [z["hi"] for z in az])
    pad = (yhi - ylo) * 0.04
    ax.set_ylim(ylo - pad, yhi + pad)              # tighten vertical whitespace
    ax.set_ylabel("NQ price (Sep'26 basis)")
    ax.set_xlabel("30-minute candles · ET · each shaded block = one CME session (18:00→16:00)", fontsize=9)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_three_filter_today.png"
    plt.savefig(out, dpi=110, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
