"""Stream 2 - multi-day / multi-week composite level map.

Stream 1 (overnight_setup.py) reads ONE session's overnight value area for the
intraday failed-auction trade. This stream zooms out: it builds the LARGER
levels that form over many sessions - the levels a swing decision sits inside.

Same fixed-window discipline as everything else (levels come from the data, not
from a viewport). Judgement call on span: it composites the last `--sessions`
RTH days (default: all available in the file) and reports the exact span used.

Built from the 30-min ETH cache (data/nq_30min_eth.json ~ 1 month), so the
composite is a genuine multi-week balance, not a single night.

Outputs:
  * composite value area over the whole span:  cVAH / cPOC / cVAL
  * per-week high/low (this week + prior weeks)
  * per-session POCs (the stacked daily magnets; untested = 'naked')
  * round numbers near price
  * a chart on the expanded timeline with the big levels drawn
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import volume_profile, round_numbers, round_step

ET = ZoneInfo("America/New_York")


def load(path: Path) -> pd.DataFrame:
    r = json.loads(path.read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def session_of(ts: pd.DatetimeIndex) -> pd.Series:
    """CME session date: bars from 18:00 ET belong to the next day's session."""
    d = pd.Series(ts.date, index=ts)
    ev = ts.hour >= 18
    d[ev] = (ts[ev] + pd.Timedelta(days=1)).date
    return pd.to_datetime(d.values)


def run(path: Path, sessions: int | None, bins: int) -> None:
    df = load(path)
    df["session"] = session_of(df.index)
    all_sessions = sorted(df["session"].unique())
    use = all_sessions if not sessions else all_sessions[-sessions:]
    span = df[df["session"].isin(use)]
    cur_px = float(df["close"].iloc[-1])
    now = df.index[-1]

    # composite value area over the whole span
    cpoc, cvah, cval = volume_profile(span, bins)
    hi, lo = span["high"].max(), span["low"].min()

    print(f"=== NQ multi-day composite  |  as of {now:%a %Y-%m-%d %H:%M} ET ===")
    print(f"span: {len(use)} sessions {pd.Timestamp(use[0]).date()} -> {pd.Timestamp(use[-1]).date()} "
          f"({len(span)} bars @ {int((span.index[1]-span.index[0]).total_seconds()/60)}min)")
    print(f"COMPOSITE value area (multi-week balance):")
    print(f"  span High {hi:.0f} | cVAH {cvah:.0f} | cPOC {cpoc:.0f} | cVAL {cval:.0f} | span Low {lo:.0f}")
    loc = "ABOVE cVAH" if cur_px > cvah else "BELOW cVAL" if cur_px < cval else "INSIDE composite value"
    print(f"  now {cur_px:.0f} [{loc}]  to cVAH {cvah-cur_px:+.0f}  cPOC {cpoc-cur_px:+.0f}  cVAL {cval-cur_px:+.0f}")

    # weekly high/low
    span = span.copy()
    iso = span.index.isocalendar()
    span["wk"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    print("weekly high/low:")
    weeks = list(dict.fromkeys(span["wk"]))
    wk_levels = {}
    for wk in weeks[-4:]:
        g = span[span["wk"] == wk]
        tag = "THIS week" if wk == weeks[-1] else ("prior week" if wk == weeks[-2] else "")
        wk_levels[wk] = (g["high"].max(), g["low"].min())
        print(f"  {wk} {tag:11s}: H {g['high'].max():.0f}  L {g['low'].min():.0f}")

    # per-session POCs (daily magnets) + naked test
    print("per-session POC (daily magnet; 'naked' = not revisited since):")
    pocs = []
    for d in use[-8:]:
        g = span[span["session"] == d]
        if len(g) < 3:
            continue
        p, _, _ = volume_profile(g, 30)
        later = span[span["session"] > d]
        naked = not (((later["low"] <= p) & (later["high"] >= p)).any())
        pocs.append((pd.Timestamp(d).date(), p, naked))
        print(f"  {pd.Timestamp(d).date()}: POC {p:.0f}{'  <- NAKED (untested magnet)' if naked else ''}")

    rn = round_numbers(cur_px, round_step(cur_px))
    print(f"round numbers near price: {', '.join(f'{x:.0f}' for x in rn)}")

    _chart(df, span, use, cpoc, cvah, cval, hi, lo, wk_levels, pocs, cur_px, now, bins)


def _chart(df, span, use, cpoc, cvah, cval, hi, lo, wk_levels, pocs, cur_px, now, bins):
    plot = span
    fig, (axp, axv) = plt.subplots(1, 2, figsize=(17, 8),
                                   gridspec_kw={"width_ratios": [5, 1]}, sharey=True)
    for i, (ts, r) in enumerate(plot.iterrows()):
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        axp.plot([i, i], [r["low"], r["high"]], color=c, lw=0.5, zorder=2)
        axp.add_patch(Rectangle((i-0.3, min(r["open"], r["close"])), 0.6,
                                abs(r["close"]-r["open"]) + 0.2, facecolor=c, edgecolor=c, zorder=3))
    axp.axhspan(cval, cvah, color="#ab47bc", alpha=0.10, zorder=0)
    for lv, lab, col in [(cvah, "cVAH %.0f" % cvah, "#6a1b9a"), (cpoc, "cPOC %.0f" % cpoc, "#4a148c"),
                         (cval, "cVAL %.0f" % cval, "#6a1b9a")]:
        axp.axhline(lv, color=col, lw=2, zorder=5)
        axp.text(len(plot)+0.5, lv, lab, color=col, va="center", fontsize=10, fontweight="bold")
    # weekly H/L
    for wk, (h, l) in list(wk_levels.items())[-2:]:
        for lv in (h, l):
            axp.axhline(lv, color="#00838f", lw=0.8, ls="--", zorder=1)
        axp.text(len(plot)+0.5, h, f"{wk[-3:]}H {h:.0f}", color="#00838f", va="center", fontsize=7)
        axp.text(len(plot)+0.5, l, f"{wk[-3:]}L {l:.0f}", color="#00838f", va="center", fontsize=7)
    # naked POCs
    for d, p, naked in pocs:
        if naked:
            axp.axhline(p, color="#ef6c00", lw=0.8, ls=(0, (2, 2)), zorder=1)
            axp.text(0, p, f"nPOC {p:.0f}", color="#ef6c00", va="center", fontsize=6.5)
    # session dividers (RTH open marks)
    prev_s = None
    for i, ts in enumerate(plot.index):
        s = plot["session"].iloc[i]
        if s != prev_s:
            axp.axvline(i-0.5, color="#cfd8dc", lw=0.5, zorder=0)
            prev_s = s
    axp.scatter([len(plot)-1], [cur_px], marker="o", s=70, color="#1565c0", zorder=6)
    axp.text(len(plot)+0.5, cur_px, "NOW %.0f" % cur_px, color="#1565c0", va="center", fontsize=9, fontweight="bold")
    axp.set_title(f"NQ multi-day composite — {len(use)} sessions "
                  f"{pd.Timestamp(use[0]).date()} → {pd.Timestamp(use[-1]).date()}  (as of {now:%a %H:%M} ET)\n"
                  f"bold purple = composite value area (multi-week balance); teal dashed = weekly H/L; "
                  f"orange dotted = naked POCs", fontsize=10.5)
    tk = list(range(0, len(plot), max(1, len(plot)//14)))
    axp.set_xticks(tk); axp.set_xticklabels([plot.index[i].strftime("%m-%d") for i in tk], rotation=45, fontsize=7.5)
    axp.set_ylabel("NQ"); axp.set_xlim(-2, len(plot)+18); axp.grid(alpha=0.12)
    # composite VP side panel
    edges = np.linspace(lo, hi, bins+1); centers = (edges[:-1]+edges[1:])/2; vol = np.zeros(bins)
    for low, high, v in zip(span["low"], span["high"], span["volume"]):
        a = max(0, int(np.searchsorted(edges, low, "right"))-1)
        b = min(bins-1, int(np.searchsorted(edges, high, "right"))-1); vol[a:b+1] += v/(b-a+1)
    cols = ["#ce93d8" if cval <= c <= cvah else "#e0e0e0" for c in centers]
    axv.barh(centers, vol, height=(hi-lo)/bins, color=cols)
    axv.axhline(cpoc, color="#4a148c", lw=1.6); axv.axhline(cur_px, color="#1565c0", lw=1, ls=(0, (1, 1)))
    axv.set_title("composite\nvol by price", fontsize=9); axv.set_xticks([])
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_multiday_levels.png"
    plt.savefig(out, dpi=108, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "data" / "nq_30min_eth.json"))
    ap.add_argument("--sessions", type=int, default=0, help="0 = all available")
    ap.add_argument("--bins", type=int, default=80)
    a = ap.parse_args()
    run(Path(a.file), a.sessions or None, a.bins)
