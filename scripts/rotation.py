"""Sector-rotation / breadth read — MAGS (Mag-7) vs SMH (semis) vs IGV (software),
benchmarked to QQQ. Normalized %-change overlay of the last RTH session, the way
Flow Zone Trader uses it for live trend/leadership detection.

Read: when the tech leaders line up GREEN and rising together (esp. SMH semis
leading), that's broad risk-on -> supports NQ/QQQ trend-up. When they diverge
(e.g. MAGS up but SMH red) the move is narrow/suspect -> caution / mean-revert.
This is CONTEXT/confirmation, not a standalone trigger.

Symbols are a one-line config — swap IGV for XLK/IYW/IGM etc. if you prefer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ET = "America/New_York"

# label -> data file. Edit this list to change the basket.
SYMS = [
    ("MAGS", "mags_5m.json", "#e0e0e0"),   # Roundhill Mag-7
    ("SMH",  "smh_5m.json",  "#26a69a"),   # VanEck semis
    ("IGV",  "igv_5m.json",  "#42a5f5"),   # iShares expanded tech-software
    ("QQQ",  "qqq_5min.json", "#f9a825"),  # benchmark
]
BENCH = "QQQ"


def load(fname):
    r = json.loads((ROOT / "data" / fname).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def last_rth(df):
    t = df.index.time
    rth = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]
    if rth.empty:
        return rth
    last_day = rth.index.normalize().max()
    return rth[rth.index.normalize() == last_day]


def pct_series(fname):
    g = last_rth(load(fname))
    if g.empty:
        return None
    base = float(g["open"].iloc[0])
    return (g["close"] / base - 1.0) * 100.0


def main():
    series = {}
    for lab, fname, _ in SYMS:
        try:
            s = pct_series(fname)
            if s is not None and len(s) > 1:
                series[lab] = s
        except FileNotFoundError:
            pass
    if not series:
        print("rotation: no data"); return

    day = max(s.index[-1] for s in series.values()).strftime("%a %m-%d")
    tnow = max(s.index[-1] for s in series.values()).strftime("%H:%M")
    finals = {k: float(v.iloc[-1]) for k, v in series.items()}
    ranked = sorted(finals.items(), key=lambda kv: -kv[1])
    leaders = [t[0] for t in SYMS if t[0] != BENCH]
    bench = finals.get(BENCH, 0.0)

    # RECENT leg (last hour = 12x 5-min bars): the move OVER the window, so a
    # sector that was red all day but ripping the last hour shows up as leading NOW.
    W = 12
    def recent(k):
        s = series[k]
        if len(s) < 2:
            return 0.0
        j = min(W, len(s) - 1)            # bars back (<= last hour)
        return float(s.iloc[-1] - s.iloc[-1 - j])
    rec = {k: recent(k) for k in series}
    bench_rec = rec.get(BENCH, 0.0)

    print(f"SECTOR ROTATION / BREADTH — {day} {tnow} ET")
    print(f"  {'sym':5s} {'since-open':>10s} {'last-1h':>8s} {'vs QQQ(1h)':>11s}")
    for k, v in ranked:
        rs = rec.get(k, 0.0) - bench_rec
        tag = "" if k == BENCH else f"{rs:+.2f}%"
        print(f"  {k:5s} {v:+9.2f}% {rec.get(k,0.0):+7.2f}% {tag:>11s}")

    greens = [k for k in leaders if finals.get(k, 0) > 0]              # since open
    beat = [k for k in leaders if finals.get(k, 0) > bench]
    rising = [k for k in leaders if rec.get(k, 0) > 0]                # last hour
    beat_now = [k for k in leaders if rec.get(k, 0) > bench_rec]

    lead_day = max(leaders, key=lambda k: finals.get(k, -9))
    lead_now = max(leaders, key=lambda k: rec.get(k, -9))
    semis_now = rec.get("SMH", 0.0)

    # rotation read driven by the LIVE (last-hour) breadth, not the whole day
    if len(rising) == len(leaders) and lead_now == "SMH":
        call = "BROAD RISK-ON right now, semis-led -> supports NQ/QQQ trend-UP"
    elif len(rising) == len(leaders):
        call = "broad risk-on right now (all tech rising) -> supports trend-UP"
    elif len(rising) == 0:
        call = "BROAD RISK-OFF right now (all tech falling) -> supports trend-DOWN"
    else:
        call = ("NARROW / DIVERGENT right now -> move suspect, favour mean-revert / "
                "wait for alignment")
    print(f"  breadth since-open: {len(greens)}/{len(leaders)} green, {len(beat)}/{len(leaders)} beat {BENCH}"
          f"   |   last-1h: {len(rising)}/{len(leaders)} rising, {len(beat_now)}/{len(leaders)} beat {BENCH}")
    if lead_now != lead_day:
        print(f"  ** ROTATION SHIFT: {lead_day} led the day but {lead_now} is leading the last hour "
              f"-> leadership is rotating, weight the NOW read **")
    print(f"  ROTATION READ (live): {call}  [CONTEXT, not a trigger]")

    _chart(series, day)


def _chart(series, day):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {lab: c for lab, _, c in SYMS}
    fig, ax = plt.subplots(figsize=(13, 7))
    for lab, s in series.items():
        x = range(len(s))
        style = "--" if lab == BENCH else "-"
        lw = 1.4 if lab == BENCH else 2.0
        ax.plot(list(x), s.values, style, color=colors.get(lab, "#888"),
                lw=lw, label=f"{lab} {s.iloc[-1]:+.2f}%")
        ax.text(len(s) - 1, float(s.iloc[-1]), f" {lab} {s.iloc[-1]:+.2f}%",
                color=colors.get(lab, "#888"), va="center", fontsize=9, fontweight="bold")
    ax.axhline(0, color="#888", lw=0.8, alpha=0.6)
    ref = next(iter(series.values()))
    n = len(ref)
    if n > 13:                                    # shade the last hour (the "NOW" read window)
        ax.axvspan(n - 1 - 12, n - 1, color="#ffffff", alpha=0.06)
        ax.axvline(n - 1 - 12, color="#888", lw=0.8, ls=":", alpha=0.5)
        ax.text(n - 1 - 12, ax.get_ylim()[1], " last 1h", color="#aaa", va="top", fontsize=8)
    tk = list(range(0, n, max(1, n // 10)))
    ax.set_xticks(tk); ax.set_xticklabels([ref.index[i].strftime("%H:%M") for i in tk], fontsize=8)
    ax.set_title(f"Sector rotation — MAGS / SMH / IGV vs QQQ — normalized %chg, RTH {day}", fontsize=11)
    ax.set_ylabel("% change from session open"); ax.grid(alpha=0.15)
    ax.legend(loc="upper left", fontsize=9)
    fig.patch.set_facecolor("#0e0e12"); ax.set_facecolor("#0e0e12")
    ax.tick_params(colors="#ccc"); ax.yaxis.label.set_color("#ccc"); ax.title.set_color("#eee")
    for sp in ax.spines.values():
        sp.set_color("#333")
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "rotation.png"
    plt.savefig(out, dpi=110, facecolor=fig.get_facecolor())
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
