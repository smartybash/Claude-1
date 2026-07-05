"""Visual guide to the liquidity-trap setup — storyboard style, one idea per
panel, minimal text. Three images:
  guide1: 4-step storyboard of the buy setup
  guide2: the three "skip it" cases
  guide3: the real July 1 ES trade, simplified, with the day's check-ins
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

IMG = Path(__file__).resolve().parents[1] / "reports" / "img"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, GREEN, RED = "#2a78d6", "#008300", "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "sans-serif", "text.color": INK, "axes.grid": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
})


def smooth(keys, n=160):
    """Smooth line path through (x, y) key points."""
    kx, ky = zip(*keys)
    x = np.linspace(kx[0], kx[-1], n)
    y = np.interp(x, kx, ky)
    k = 9
    pad = np.r_[np.full(k // 2, y[0]), y, np.full(k // 2, y[-1])]
    return x, np.convolve(pad, np.ones(k) / k, "valid")


def clean(ax):
    ax.set_xticks([])
    ax.set_yticks([])


LVL = 100

# ------------------------------------------------------------ guide 1
fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), dpi=150)
titles = [
    "1)  Find a low the market bounced hard from",
    "2)  Price comes back and dips below it",
    "3)  It pops back above  →  that's your BUY",
    "4)  Stop under the dip · sell at the next level up",
]

# panel 1: bounce away
ax = axes[0, 0]
x, y = smooth([(0, 112), (2, 105), (4, 100.3), (6, 108), (9, 116), (12, 114)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.text(6, 96.5, "sellers' stops pile up under this low", fontsize=11.5, color=BLUE, ha="center")
ax.set_ylim(92, 121)

# panel 2: return + dip below
ax = axes[0, 1]
x, y = smooth([(0, 116), (3, 110), (6, 104), (8, 100.5), (9.5, 97), (10.5, 96), (12, 98.5)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.scatter([10.3], [96.1], s=380, facecolor="none", edgecolor=RED, lw=2.5, zorder=5)
ax.text(7.0, 90.5, "stops get taken  (don't buy yet!)", fontsize=11.5, color=RED, ha="center")
ax.set_ylim(86, 121)

# panel 3: reclaim = entry
ax = axes[1, 0]
x, y = smooth([(0, 104), (2, 100.5), (3.5, 96.5), (5, 96), (6.5, 99), (7.5, 102.5), (9, 104), (12, 108)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.scatter([7.5], [102.5], marker="^", s=340, color=GREEN, zorder=5)
ax.text(8.2, 92.6, "wait for a 15-min candle to CLOSE\nback above the line — then buy",
        fontsize=11.5, color=GREEN, ha="center")
ax.set_ylim(87.5, 113)

# panel 4: the bracket
ax = axes[1, 1]
ax.hlines(96, 1, 11, color=RED, lw=3)
ax.hlines(102.5, 1, 11, color=INK, lw=2, ls=(0, (4, 3)))
ax.hlines(114, 1, 11, color=GREEN, lw=3)
ax.scatter([2.2], [102.5], marker="^", s=300, color=GREEN, zorder=5)
ax.text(11.4, 96, "STOP — just under the dip", fontsize=11.5, color=RED, va="center")
ax.text(11.4, 102.5, "your entry", fontsize=11.5, color=INK2, va="center")
ax.text(11.4, 114, "TARGET — the next level above\n(yesterday's close or high)", fontsize=11.5, color=GREEN, va="center")
ax.set_xlim(0, 26)
ax.set_ylim(90, 120)

for ax, t in zip(axes.flat, titles):
    ax.set_title(t, fontsize=13, loc="left", color=INK, pad=10)
    clean(ax)
fig.suptitle("The liquidity-trap BUY  (selling works the same way, flipped at a high)",
             fontsize=15, x=0.02, ha="left", color=INK, y=0.99)
fig.text(0.02, 0.005, "risk small: position size = your risk ÷ (entry − stop) · always out by 15:59 ET",
         fontsize=11, color=INK2)
fig.tight_layout(rect=[0, 0.03, 1, 0.94])
fig.savefig(IMG / "guide1_anatomy.png", facecolor=SURFACE)

# ------------------------------------------------------------ guide 2
fig, axes = plt.subplots(1, 3, figsize=(12, 4.0), dpi=150)

ax = axes[0]
x, y = smooth([(0, 96), (3, 93), (6, 95), (9, 92), (12, 93.5)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.set_ylim(86, 108)
ax.set_title("✗  Day OPENED below the level", fontsize=12.5, loc="left", color=RED, pad=10)
ax.text(0, -0.04, "stops already taken overnight —\nnothing left to trap", transform=ax.transAxes,
        fontsize=11, color=INK2, va="top")

ax = axes[1]
x, y = smooth([(0, 108), (3, 103), (5, 99), (7, 92), (9, 83), (12, 76)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.set_ylim(68, 114)
ax.set_title("✗  Dipped WAY below and stayed", fontsize=12.5, loc="left", color=RED, pad=10)
ax.text(0, -0.04, "real breakdown, not a stop-run —\ndon't catch it", transform=ax.transAxes,
        fontsize=11, color=INK2, va="top")

ax = axes[2]
x, y = smooth([(0, 118), (3, 112), (6, 104), (8, 99), (10, 93), (12, 88)])
ax.plot(x, y, color=INK, lw=2.6)
ax.hlines(LVL, 0, 12, color=BLUE, lw=3)
ax.set_ylim(80, 124)
ax.set_title("✗  It's a TREND day", fontsize=12.5, loc="left", color=RED, pad=10)
ax.text(0, -0.04, "the 11:00 read says TREND —\nonly trade traps on chop days", transform=ax.transAxes,
        fontsize=11, color=INK2, va="top")

for ax in axes:
    clean(ax)
fig.suptitle("Skip the trade when…", fontsize=15, x=0.02, ha="left", color=INK)
fig.tight_layout(rect=[0, 0.10, 1, 0.90])
fig.savefig(IMG / "guide2_no_trade.png", facecolor=SURFACE)

# ------------------------------------------------------------ guide 3
es = load_ibkr_json(Path(__file__).resolve().parents[1] / "data" / "es_5min_live.json")
day = es[(pd.Series(es.index.date, index=es.index) == pd.Timestamp("2026-07-01").date())
         & (es.index.time >= dtime(9, 30)) & (es.index.time < dtime(16, 0))]
LVL3, ENT3, STP3, TGT3 = 7567.75, 7559.75, 7584.72, 7550.75

fig, ax = plt.subplots(figsize=(11, 6.2), dpi=150)
ax.plot(range(len(day)), day["close"].values, color=INK, lw=1.8)
n = len(day)
ax.hlines(LVL3, 0, n, color=BLUE, lw=3)
ax.hlines(STP3, 0, n, color=RED, lw=2, ls=(0, (5, 3)))
ax.hlines(TGT3, 0, n, color=GREEN, lw=3)
ax.text(n + 1, LVL3, "yesterday's high\n(the level)", color=BLUE, fontsize=12, va="center")
ax.text(n + 1, STP3, "stop", color=RED, fontsize=12, va="center")
ax.text(n + 1, TGT3, "target = next level below", color=GREEN, fontsize=12, va="center")

x_of = {ts: i for i, ts in enumerate(day.index)}
sweep_x = x_of[day[day["high"] >= 7578].index[0]]
ent_x = x_of[[ts for ts in day.index if ts.time() == dtime(12, 45)][0]]
tgt_ts = day.index[(day.index > day.index[ent_x]) & (day["low"] <= TGT3)][0]
tgt_x = x_of[tgt_ts]

ax.scatter([sweep_x], [7579], s=500, facecolor="none", edgecolor=RED, lw=2.5, zorder=5)
ax.annotate("1) buyers' stops above\nyesterday's high get taken", xy=(sweep_x, 7580.5),
            xytext=(sweep_x - 26, 7588), fontsize=12, color=RED,
            arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))
ax.scatter([ent_x], [ENT3], marker="v", s=340, color=RED, zorder=5)
ax.annotate("2) price falls back under the line\n→ SELL 7,559.75", xy=(ent_x, ENT3),
            xytext=(ent_x + 8, 7572), fontsize=12, color=INK,
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6))
ax.annotate("3) target hit  +9 pts", xy=(tgt_x, TGT3), xytext=(tgt_x - 6, 7541),
            fontsize=12, color=GREEN, arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.6))

ticks = [i for i, ts in enumerate(day.index) if ts.minute == 0 and ts.hour in (10, 12, 14)]
ax.set_xticks(ticks, [day.index[i].strftime("%H:%M") for i in ticks], fontsize=11)
ax.set_xlim(-1, n + 22)
ax.set_ylim(7495, 7596)
ax.set_yticks([])
ax.set_title("A real one — ES, July 1: sell the trap at yesterday's high", fontsize=15, loc="left", color=INK, pad=12)
fig.text(0.02, 0.10, "What our system said that day:", fontsize=11.5, color=INK)
fig.text(0.02, 0.015,
         "10:33  not a quiet day — trading allowed        11:07  reading: NEUTRAL → traps allowed\n"
         "13:33  this short flagged and working              16:07  day ended as chop — call was right · trade +9 pts",
         fontsize=11, color=INK2)
fig.tight_layout(rect=[0, 0.13, 1, 1])
fig.savefig(IMG / "guide3_real_trade.png", facecolor=SURFACE)

print("wrote", sorted(p.name for p in IMG.glob("guide*.png")))
