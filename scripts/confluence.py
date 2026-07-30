"""Confluence engine — HTF-anchored, scored support/resistance zones.

Standalone overnight VAH/VAL is noise. A level matters where MANY independent
things agree. This gathers levels from every timeframe/type, clusters them into
zones, scores each zone by the weight of what stacks there, and prints the
strong support (long) zones below price and resistance (short) zones above.

Inputs (all cached): 1h ETH (-> resampled to 4h for major swings), 30-min
(composite value + weekly), 5-min (VWAP, overnight, prior-day, OR, round #s).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import round_numbers, round_step, volume_profile

ET = "America/New_York"


def load(name: str) -> pd.DataFrame:
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def resample(df, rule):
    o = df.resample(rule, label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna()


def swings(df, k, recent):
    """Fractal swing highs/lows: extreme vs k bars each side. Return the most
    recent `recent` bars' pivots as (price, kind)."""
    h, l = df["high"].values, df["low"].values
    n = len(df)
    out = []
    for i in range(k, n - k):
        if h[i] == max(h[i - k:i + k + 1]):
            out.append((float(h[i]), i))
        if l[i] == min(l[i - k:i + k + 1]):
            out.append((float(l[i]), i))
    return [p for p, i in out if i >= n - recent]


def main():
    h1 = load("nq_1h_eth.json")
    h4 = resample(h1, "4h")
    m30 = load("nq_30min_eth.json")
    m5 = load("nq_5min_eth_live.json")
    px = float(m5["close"].iloc[-1])
    now = m5.index[-1]

    levels = []  # (price, label, weight)

    for p in swings(h4, 2, 60):
        levels.append((p, "4h swing", 3.0))
    for p in swings(h1, 3, 90):
        levels.append((p, "1h swing", 2.0))

    # composite value (multi-week) from 30m
    poc, vah, val = volume_profile(m30, 80)
    levels += [(vah, "cVAH", 2.5), (poc, "cPOC", 2.5), (val, "cVAL", 2.5)]

    # weekly H/L (prior + current) from 30m
    iso = m30.index.isocalendar()
    m30w = m30.assign(wk=iso["year"].astype(str) + iso["week"].astype(str))
    wks = list(dict.fromkeys(m30w["wk"]))
    for wk in wks[-2:]:
        g = m30w[m30w["wk"] == wk]
        levels += [(float(g["high"].max()), "wkH", 2.5), (float(g["low"].min()), "wkL", 2.5)]

    # prior day H/L/C and today OR / dev H/L / overnight from 5m
    cur = now.normalize()
    days = sorted({d for d in m5.index.normalize().unique() if d < cur})
    if days:
        pg = m5[(m5.index >= days[-1].replace(hour=9, minute=30)) & (m5.index < days[-1].replace(hour=16))]
        if len(pg) > 10:
            levels += [(float(pg["high"].max()), "PDH", 2.0), (float(pg["low"].min()), "PDL", 2.0),
                       (float(pg["close"].iloc[-1]), "PDC", 1.5)]
    rth = m5[(m5.index >= cur.replace(hour=9, minute=30)) & (m5.index.normalize() == cur)]
    if len(rth) >= 2:
        tp = (rth["high"] + rth["low"] + rth["close"]) / 3
        vwap = float((tp * rth["volume"]).cumsum().iloc[-1] / rth["volume"].cumsum().iloc[-1])
        levels.append((vwap, "VWAP", 1.5))
        orb = rth.iloc[:6]
        levels += [(float(orb["high"].max()), "ORH", 1.0), (float(orb["low"].min()), "ORL", 1.0)]
        levels += [(float(rth["high"].max()), "dayH", 1.5), (float(rth["low"].min()), "dayL", 1.5)]
    on = m5[(m5.index >= (cur - pd.Timedelta(days=1)).replace(hour=18)) & (m5.index < cur.replace(hour=9, minute=30))]
    if len(on) >= 10:
        opoc, ovah, oval = volume_profile(on, 50)
        levels += [(ovah, "onVAH", 1.0), (oval, "onVAL", 1.0)]  # demoted
    for p in round_numbers(px, round_step(px), 3):
        levels.append((p, "round", 1.0))

    # cluster into zones
    tol = 0.0018 * px  # ~50 pt on NQ
    levels.sort()
    zones = []
    cluster = [levels[0]]
    for lv in levels[1:]:
        if lv[0] - cluster[-1][0] <= tol:
            cluster.append(lv)
        else:
            zones.append(cluster); cluster = [lv]
    zones.append(cluster)

    def zinfo(z):
        w = sum(x[2] for x in z)
        price = sum(x[0] * x[2] for x in z) / w
        lo, hi = min(x[0] for x in z), max(x[0] for x in z)
        labs = ", ".join(dict.fromkeys(x[1] for x in z))
        return price, lo, hi, w, labs

    zi = [zinfo(z) for z in zones]
    above = sorted([z for z in zi if z[0] > px], key=lambda x: x[0])
    below = sorted([z for z in zi if z[0] <= px], key=lambda x: -x[0])

    print(f"NQ CONFLUENCE MAP — {now:%a %m-%d %H:%M} ET   price {px:.0f}")
    print(f"(zone = levels within ~{tol:.0f}pt; score = summed weight; >=5 = strong, >=8 = A+)\n")
    # learned filter (backtest_confluence.py): only score>=8 is tradeable;
    # zones stacking composite-value / PDH / HTF-swing held ~best -> star them.
    TOP = {"cVAH", "cVAL", "cPOC", "PDH", "4h swing", "1h swing"}

    def grade(w, labs):
        if w >= 8:
            return "TOP" if (set(labs.replace(" ", "").split(",")) & {t.replace(" ", "") for t in TOP}) else "A+ "
        return "   "  # below A+ = not tradeable, shown greyed for context only

    print("RESISTANCE above (short zones):")
    for price, lo, hi, w, labs in above[:5][::-1]:
        print(f"  {grade(w,labs)} {lo:.0f}-{hi:.0f}  score {w:.1f}  [{labs}]")
    print(f"  ------ price {px:.0f} ------")
    print("SUPPORT below (long zones):")
    for price, lo, hi, w, labs in below[:5]:
        print(f"  {grade(w,labs)} {lo:.0f}-{hi:.0f}  score {w:.1f}  [{labs}]")

    # tradeable = A+ (score>=8) ONLY (learned: <8 holds far less reliably)
    sa = next((z for z in above if z[3] >= 8), None)
    sb = next((z for z in below if z[3] >= 8), None)
    print("\nTRADEABLE (A+ only, score>=8):")
    if sb: print(f"  LONG off support {sb[1]:.0f}-{sb[2]:.0f} (score {sb[3]:.1f}) -> target {sa[1]:.0f}" if sa else f"  LONG off {sb[1]:.0f}-{sb[2]:.0f}")
    if sa: print(f"  SHORT off resistance {sa[1]:.0f}-{sa[2]:.0f} (score {sa[3]:.1f}) -> target {sb[2]:.0f}" if sb else f"  SHORT off {sa[1]:.0f}-{sa[2]:.0f}")
    if not sa and not sb: print("  none in range - stand aside")

    _chart(m5, above, below, px, now, zi)


def _chart(m5, above, below, px, now, zi):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    plot = m5[m5.index >= now - pd.Timedelta(hours=20)]
    fig, ax = plt.subplots(figsize=(15, 8))
    for i, (ts, r) in enumerate(plot.iterrows()):
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.5, zorder=3)
        ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6,
                               abs(r["close"] - r["open"]) + 0.2, facecolor=c, edgecolor=c, zorder=4))
    n = len(plot)
    # confluence zones as shaded bands, colored by side, intensity by score
    for price, lo, hi, w, labs in zi:
        if hi < plot["low"].min() - 100 or lo > plot["high"].max() + 100:
            continue
        red = price > px
        col = "#d32f2f" if red else "#2e7d32"
        alpha = min(0.32, 0.06 + w / 60)
        band = max(hi - lo, 6)
        ax.add_patch(Rectangle((0, lo), n, band, facecolor=col, alpha=alpha, edgecolor="none", zorder=1))
        star = "A+" if w >= 8 else "**" if w >= 5 else ""
        ax.text(n + 0.5, price, f"{star} {lo:.0f}-{hi:.0f}  s{w:.0f}  [{labs[:38]}]",
                color=col, va="center", fontsize=7.5, fontweight="bold" if w >= 8 else "normal")
    ax.axhline(px, color="#1565c0", lw=1.3, zorder=5)
    ax.text(n + 0.5, px, f"PRICE {px:.0f}", color="#1565c0", va="center", fontsize=9, fontweight="bold")
    ax.set_title(f"NQ confluence map — {now:%a %m-%d %H:%M} ET   "
                 f"(red=resistance/short, green=support/long; darker=stronger; A+ >=8)", fontsize=11)
    tk = list(range(0, n, max(1, n // 12)))
    ax.set_xticks(tk); ax.set_xticklabels([plot.index[i].strftime("%m-%d %H:%M") for i in tk], rotation=45, fontsize=7.5)
    ax.set_xlim(0, n + 26); ax.set_ylabel("NQ"); ax.grid(alpha=0.12, zorder=0)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_confluence.png"
    plt.savefig(out, dpi=110, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
