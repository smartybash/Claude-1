"""15-day walk-forward simulation of the confluence system on NQ 30-min.

For each of the last 15 sessions:
  * Build A+ / DENSE zones AS-OF the open from pre-open data only (swings,
    composite value, prior-day, round numbers) - the same graded pre-open map
    you'd have at 9:30, no lookahead. (5-min VWAP/OR not available this far
    back, and by design they don't affect the pre-open grade.)
  * Label regime (trend/balance) from the session's efficiency ratio.
  * Simulate the IDEAL mechanical trades: fade an A+ zone when a 30-min bar
    closes back off it, stop beyond the zone, target the opposite A+ zone (else
    1.5R). Trend gate: on a trend day skip fades AGAINST the trend.
  * Record which zones HELD vs BROKE, EoD close, and the reason a zone broke.

Outputs a per-day table + a 15-panel chart (each day: 30-min candles, pre-open
A+ zones, trade entries/exits, EoD close, broken zones X'd).
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
import scripts.backtest_confluence as bt  # build(), swings(), load()

ET = "America/New_York"
BUF_F = 0.0009      # stop buffer beyond zone (% of price)
WIN_F = 0.012       # only zones within 1.2% of open are in play


def sessions(df):
    s = pd.Series(df.index.date, index=df.index)
    ev = df.index.hour >= 18
    s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def daily_closes(df30, ids, bysess):
    """Continuous daily-close series for the MACRO trend filter: real dailies
    (nq_daily_3m.json) spliced with session closes derived from the 30-min data
    so the window through July is covered. Indexed by date."""
    import json
    r = json.loads((ROOT / "data" / "nq_daily_3m.json").read_text())
    dd = pd.Series(r["close"],
                   index=pd.to_datetime(r["time"], utc=True).tz_convert(ET).date)
    sc = {}
    for s in ids:
        rth = bysess[s][(bysess[s].index.time >= pd.Timestamp("09:30").time()) &
                        (bysess[s].index.time < pd.Timestamp("16:00").time())]
        if len(rth):
            sc[pd.Timestamp(s).date()] = float(rth["close"].iloc[-1])
    sc = pd.Series(sc)
    daily = pd.concat([dd[dd.index < sc.index.min()], sc]).sort_index()
    return daily[~daily.index.duplicated(keep="last")]


def macro_bias(daily, date):
    """Macro/HTF trend bias as-of `date`, from DAILY closes strictly before it
    (no lookahead): price vs 20d SMA, 10d-vs-20d SMA, and 20d slope must agree.
    +1 up / -1 down / 0 mixed. A daily filter, not an intraday SMA - it holds
    the macro regime instead of flipping on a one-day bounce."""
    prior = daily[daily.index < date]
    if len(prior) < 20:
        return 0
    px = float(prior.iloc[-1])
    s10, s20 = prior.iloc[-10:].mean(), prior.iloc[-20:].mean()
    slope = float(np.polyfit(range(20), prior.iloc[-20:].values, 1)[0])
    sc = (1 if px > s20 else -1) + (1 if s10 > s20 else -1) + (1 if slope > 0 else -1)
    return -1 if sc <= -2 else (1 if sc >= 2 else 0)


def simulate(rth, azones, bias, px):
    """TREND-ONLY: take only the fade aligned with the pre-open HTF bias.
    down-bias -> short resistance zones; up-bias -> long support zones."""
    buf = BUF_F * px
    arr = rth.reset_index(drop=True)
    trades, used = [], set()
    for i in range(len(arr) - 1):
        h, l, c = arr["high"][i], arr["low"][i], arr["close"][i]
        for zi, z in enumerate(azones):
            if zi in used:
                continue
            lo, hi = z["lo"], z["hi"]
            # resistance fade (short) — only WITH a down bias
            if h >= lo and c < lo:
                if bias >= 0:
                    continue  # not trend-aligned; leave zone live
                entry, stop = c, hi + buf
                tgt = _opp(azones, z, "down", entry, stop)
                trades.append(_run(arr, i, i + 1, entry, stop, tgt, -1, z))
                used.add(zi)
            # support fade (long) — only WITH an up bias
            elif l <= hi and c > hi:
                if bias <= 0:
                    continue
                entry, stop = c, lo - buf
                tgt = _opp(azones, z, "up", entry, stop)
                trades.append(_run(arr, i, i + 1, entry, stop, tgt, 1, z))
                used.add(zi)
    return [t for t in trades if t]


def _opp(azones, z, direction, entry, stop):
    risk = abs(entry - stop)
    cands = [zz["price"] for zz in azones if (zz["price"] < z["lo"]) == (direction == "down") and zz is not z]
    if cands:
        return max(cands) if direction == "up" else min(cands)
    return entry + (1.5 * risk if direction == "up" else -1.5 * risk)


def _run(arr, ei, start, entry, stop, tgt, side, z):
    for j in range(start, len(arr)):
        h, l = arr["high"][j], arr["low"][j]
        if side < 0:  # short
            if h >= stop: return dict(entry=entry, exit=stop, side=side, R=-1, res="stop", z=z, ei=ei, xi=j)
            if l <= tgt: return dict(entry=entry, exit=tgt, side=side,
                                     R=(entry - tgt) / (stop - entry), res="target", z=z, ei=ei, xi=j)
        else:
            if l <= stop: return dict(entry=entry, exit=stop, side=side, R=-1, res="stop", z=z, ei=ei, xi=j)
            if h >= tgt: return dict(entry=entry, exit=tgt, side=side,
                                     R=(tgt - entry) / (entry - stop), res="target", z=z, ei=ei, xi=j)
    exitp = arr["close"].iloc[-1]  # flat at close
    R = ((entry - exitp) if side < 0 else (exitp - entry)) / abs(entry - stop)
    return dict(entry=entry, exit=exitp, side=side, R=R, res="eod", z=z, ei=ei, xi=len(arr) - 1)


def main():
    df30 = bt.load("nq_30min_eth.json")
    df30, ids, bysess = sessions(df30)
    daily = daily_closes(df30, ids, bysess)
    rths = {}
    for s in ids:
        g = bysess[s]
        g = g[(g.index.time >= pd.Timestamp("09:30").time()) & (g.index.time < pd.Timestamp("16:00").time())]
        if len(g) >= 6:
            rths[s] = g
    days = [s for s in ids if s in rths][-15:]

    rows, allday = [], []
    for s in days:
        opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
        hist = df30[df30.index < opent]
        if len(hist) < 60:
            continue
        prior = bysess[ids[ids.index(s) - 1]]
        zs, px = bt.build(hist, prior, 13)
        rth = rths[s]
        openp = float(rth["open"].iloc[0]); closep = float(rth["close"].iloc[-1])
        bias = macro_bias(daily, s.date() if hasattr(s, "date") else s)
        regime = {1: "up", -1: "down", 0: "flat"}[bias]
        az = [z for z in zs if z["w"] >= 8 and z["nt"] >= 2 and abs(z["price"] - openp) <= WIN_F * openp]
        trades = simulate(rth, az, bias, px)
        # which zones broke by EoD
        broke = []
        for z in az:
            if closep > z["hi"] + 5 or closep < z["lo"] - 5:
                # only count zones price actually reached & closed beyond
                if rth["high"].max() >= z["lo"] and rth["low"].min() <= z["hi"]:
                    broke.append(z)
        netR = sum(t["R"] for t in trades)
        rows.append((s, regime, len(az), len(trades), netR, len(broke), openp, closep))
        allday.append((s, rth, az, trades, closep, broke, regime))

    print("15-DAY CONFLUENCE SIM — TREND-ONLY, MACRO DAILY BIAS (NQ 30-min, pre-open A+ zones, no lookahead)\n")
    print(f"{'date':12s} {'bias':6s} {'A+zones':7s} {'trades':6s} {'netR':6s} {'broke':5s}  O->C")
    tot = 0.0; nt = 0; nw = 0
    for s, reg, nz, ntr, netR, nb, o, c in rows:
        tot += netR; nt += ntr
        print(f"{s.date()!s:12s} {reg:6s} {nz:^7d} {ntr:^6d} {netR:+5.1f} {nb:^5d}  {o:.0f}->{c:.0f} ({c-o:+.0f})")
    wins = sum(1 for d in allday for t in d[3] if t["R"] > 0)
    wr = f"{wins/nt:.0%}" if nt else "n/a"
    print(f"\nTOTAL: {nt} trades, {wins} wins ({wr} win) , net {tot:+.1f}R over {len(rows)} sessions")
    _chart(allday)


def _chart(allday):
    n = len(allday)
    cols, rowsn = 5, (n + 4) // 5
    fig, axes = plt.subplots(rowsn, cols, figsize=(20, 3.4 * rowsn))
    axes = np.array(axes).reshape(-1)
    for ax in axes[n:]:
        ax.axis("off")
    for k, (s, rth, az, trades, closep, broke, regime) in enumerate(allday):
        ax = axes[k]
        a = rth.reset_index()
        for i, r in a.iterrows():
            up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
            ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.7)
            ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6,
                                   abs(r["close"] - r["open"]) + 0.3, facecolor=c, edgecolor=c))
        m = len(a)
        for z in az:
            brk = z in broke
            col = "#d32f2f" if z["price"] > rth["open"].iloc[0] else "#2e7d32"
            dense = z["nt"] >= 4
            ax.add_patch(Rectangle((0, z["lo"]), m + 2, max(z["hi"] - z["lo"], 6), facecolor=col,
                                   alpha=0.22 if not brk else 0.10, edgecolor=col,
                                   lw=1.8 if dense else 1.0, ls="-" if not brk else ":"))
            if brk:
                ax.plot([m - 1], [z["price"]], marker="x", ms=9, color=col, mew=2.5)
        for t in trades:
            ei, xi = t["ei"], t["xi"]
            win = t["R"] > 0
            tcol = "#1565c0" if win else "#b71c1c"
            # entry marker at the trigger bar, exit marker at the resolve bar, line between
            ax.scatter([ei], [t["entry"]], marker="^" if t["side"] > 0 else "v",
                       s=55, color=tcol, edgecolor="#fff", lw=0.6, zorder=7)
            ax.scatter([xi], [t["exit"]], marker="o", s=28, facecolor="none",
                       edgecolor=tcol, lw=1.6, zorder=7)
            ax.plot([ei, xi], [t["entry"], t["exit"]], color=tcol, lw=1.1,
                    ls="-" if win else "--", zorder=6)
            ax.text(ei, t["entry"], f" {t['R']:+.1f}R", color=tcol, fontsize=6,
                    va="bottom" if t["side"] < 0 else "top", fontweight="bold", zorder=8)
        ax.axhline(closep, color="#6a1b9a", lw=1.4, ls="-")  # EoD close
        ax.text(m + 2.5, closep, "EoD", color="#6a1b9a", fontsize=7, va="center", fontweight="bold")
        netR = sum(t["R"] for t in trades)
        ax.set_title(f"{s.date()}  [{regime}]  {len(trades)}tr {netR:+.1f}R  {len(broke)} broke",
                     fontsize=8.5, fontweight="bold")
        ax.set_xticks([]); ax.tick_params(labelsize=6); ax.margins(x=0.02)
    fig.suptitle("NQ 15-day confluence sim — TREND-ONLY, MACRO DAILY BIAS (fade only WITH the daily 10/20 trend) — "
                 "bands=pre-open A+ zones (faded+X=broke), purple=EoD, ▲/▼ entry→○ exit (blue=win, red=loss)",
                 fontsize=10, y=1.002)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_15day_sim.png"
    plt.savefig(out, dpi=95, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
