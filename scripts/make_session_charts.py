"""Annotated intraday session charts: the levels behind the 11:00 ET read.

Usage: python3 scripts/make_session_charts.py [YYYY-MM-DD]

Draws 5-min candles from the prior evening's Globex open through the RTH
close, dims everything after the 11:00 decision, and marks the levels the
filter actually keys off: prior-day RTH high/low/close, overnight high/low,
and the 9:30-11:00 opening range.
"""

import sys
from datetime import time as dtime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from regime.filter import read_1100
from regime.indicators import atr

DATA = Path(__file__).resolve().parents[1] / "data"
IMG = Path(__file__).resolve().parents[1] / "reports" / "img"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BLUE = "#2a78d6"
GREEN = "#008300"
RED = "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "sans-serif", "text.color": INK,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
})


def candles(ax, df, alpha=1.0):
    x = df["x"].values
    up = df["close"] >= df["open"]
    ax.vlines(x, df["low"], df["high"], color=np.where(up, GREEN, RED),
              lw=0.9, alpha=alpha, zorder=3)
    for xi, o, c, isup in zip(x, df["open"], df["close"], up):
        lo, hi = (o, c) if c >= o else (c, o)
        ax.add_patch(Rectangle((xi - 0.38, lo), 0.76, max(hi - lo, 1e-9),
                               facecolor=GREEN if isup else RED, edgecolor="none",
                               alpha=alpha, zorder=4))


def level(ax, y, x0, x1, label, color, ls, n_all):
    ax.hlines(y, x0, x1, color=color, lw=1.2, ls=ls, alpha=0.9, zorder=2)
    ax.text(n_all + 4, y, f"{label}  {y:,.2f}", color=color, fontsize=8.5,
            va="center", ha="left")


def make_chart(name, fn, date, atr20, out):
    df = load_ibkr_json(DATA / fn)
    prior = date - pd.offsets.BDay(1)

    prior_rth = df[(pd.Series(df.index.date, index=df.index) == prior.date())
                   & (df.index.time >= dtime(9, 30)) & (df.index.time < dtime(16, 0))]
    globex_open = pd.Timestamp(f"{prior.date()} 18:00", tz="America/New_York")
    rth_open = pd.Timestamp(f"{date.date()} 09:30", tz="America/New_York")
    on = df[(df.index >= globex_open) & (df.index < rth_open)]
    rth = df[(pd.Series(df.index.date, index=df.index) == date.date())
             & (df.index.time >= dtime(9, 30)) & (df.index.time < dtime(16, 0))]

    plot = pd.concat([on, rth]).copy()
    plot["x"] = np.arange(len(plot))
    n_all = len(plot)
    dec_ts = plot.index.searchsorted(pd.Timestamp(f"{date.date()} 11:00", tz="America/New_York"))
    rth_x0 = plot["x"].iloc[len(on)]

    fh = rth[rth.index.time < dtime(11, 0)]
    o = float(fh["open"].iloc[0])
    # ER on 30-min closes, matching the validated spec (ER is granularity-sensitive)
    closes = fh["close"].resample("30min", origin=rth_open).last().dropna()
    path = float(closes.diff().abs().sum() + abs(closes.iloc[0] - o))
    or_hi, or_lo = float(fh["high"].max()), float(fh["low"].min())
    r = read_1100(atr20, o, or_hi, or_lo, float(closes.iloc[-1]), fh_path=path)

    fig, ax = plt.subplots(figsize=(10.5, 5.4), dpi=150)
    candles(ax, plot.iloc[:dec_ts])
    candles(ax, plot.iloc[dec_ts:], alpha=0.25)
    ax.axvline(dec_ts - 0.5, color=INK, lw=1.1, ls=(0, (2, 2)), alpha=0.8)
    ax.text(dec_ts + 1, ax.get_ylim()[0], "", fontsize=8)

    # opening-range band across the emphasized RTH portion
    ax.add_patch(Rectangle((rth_x0 - 0.5, or_lo), n_all - rth_x0, or_hi - or_lo,
                           facecolor=BLUE, alpha=0.08, edgecolor="none", zorder=1))

    level(ax, prior_rth["high"].max(), 0, n_all, "prior day high", INK2, (0, (5, 3)), n_all)
    level(ax, prior_rth["low"].min(), 0, n_all, "prior day low", INK2, (0, (5, 3)), n_all)
    level(ax, prior_rth["close"].iloc[-1], 0, n_all, "prior close", MUTED, (0, (1, 2)), n_all)
    level(ax, on["high"].max(), 0, n_all, "overnight high", "#4a3aa7", (0, (3, 3)), n_all)
    level(ax, on["low"].min(), 0, n_all, "overnight low", "#4a3aa7", (0, (3, 3)), n_all)
    level(ax, or_hi, rth_x0, n_all, "OR high (9:30-11:00)", BLUE, "solid", n_all)
    level(ax, or_lo, rth_x0, n_all, "OR low (9:30-11:00)", BLUE, "solid", n_all)

    # hour ticks
    ticks = [i for i, ts in enumerate(plot.index) if ts.minute == 0 and ts.hour % 2 == 0]
    ax.set_xticks(ticks, [plot.index[i].strftime("%H:%M") for i in ticks], fontsize=8.5)
    ax.set_xlim(-2, n_all + 34)
    ax.margins(y=0.10)

    need = 0.55 * atr20
    got = or_hi - or_lo
    verdict = r.state
    box = (f"11:00 ET read: {verdict}  (score {r.score}/100)\n"
           f"first-90-min range {got:,.0f} pts = {r.range_atr:.2f}x ATR20 ({atr20:,.0f})\n"
           f"trend call needs ≥ 0.55x ATR = {need:,.0f} pts\n"
           f"close position {r.pos:.2f} | efficiency {r.er:.2f}")
    ax.text(0.012, 0.975, box, transform=ax.transAxes, fontsize=9, va="top",
            color=INK, bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.45"))
    ax.text(dec_ts - 0.5, ax.get_ylim()[1], " 11:00 decision ", fontsize=8.5,
            color=INK, ha="left", va="top")

    ax.set_title(f"{name} — {date.date()}: overnight + RTH, dimmed after the 11:00 read",
                 fontsize=12, loc="left", color=INK, pad=12)
    ax.set_ylabel("price")
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    print("wrote", out.name, "|", verdict, f"OR {got:,.0f} pts ({r.range_atr:.2f} ATR)")


def main():
    date = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-07-01")
    qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
    spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")

    for name, fn, etf_d, etf_file in [("NQ Sep26", "nq_5min.json", qqq_d, "qqq_daily_5y.json"),
                                      ("ES Sep26", "es_5min.json", spy_d, "spy_daily_5y.json")]:
        idx = pd.to_datetime(etf_d.index.date)
        i = idx.get_loc(date)
        a20_etf = float(atr(etf_d, 20).shift(1).iloc[i])
        etf_prior_close = float(etf_d["close"].iloc[i - 1])
        fut = load_ibkr_json(DATA / fn)
        prior = date - pd.offsets.BDay(1)
        fut_prior = fut[(pd.Series(fut.index.date, index=fut.index) == prior.date())
                        & (fut.index.time >= dtime(9, 30)) & (fut.index.time < dtime(16, 0))]
        scale = float(fut_prior["close"].iloc[-1]) / etf_prior_close
        out = IMG / f"session_{date.date().strftime('%Y%m%d')}_{fn.split('_')[0]}.png"
        make_chart(name, fn, date, a20_etf * scale, out)


if __name__ == "__main__":
    main()
