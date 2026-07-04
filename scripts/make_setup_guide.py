"""Visual guide to the (gated) liquidity-trap setup. Three figures:
  1. anatomy of the long setup, every rule annotated
  2. the three no-trade cases
  3. the real journaled trade (ES 2026-07-01) on actual 5-min bars
"""

import sys
from datetime import time as dtime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from regime.data import load_ibkr_json

IMG = Path(__file__).resolve().parents[1] / "reports" / "img"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, GREEN, RED, VIOLET = "#2a78d6", "#008300", "#e34948", "#4a3aa7"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "sans-serif", "text.color": INK,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
})


def candles(ax, o, h, l, c, x0=0, alpha=1.0, w=0.62):
    for i, (oo, hh, ll, cc) in enumerate(zip(o, h, l, c)):
        x = x0 + i
        up = cc >= oo
        col = GREEN if up else RED
        ax.vlines(x, ll, hh, color=col, lw=1.1, alpha=alpha, zorder=3)
        lo, hi = (oo, cc) if up else (cc, oo)
        ax.add_patch(Rectangle((x - w / 2, lo), w, max(hi - lo, 0.15),
                               facecolor=col, edgecolor="none", alpha=alpha, zorder=4))


def path_to_ohlc(pts, spread=1.6, seed=7):
    rng = np.random.default_rng(seed)
    o = np.array(pts[:-1], float)
    c = np.array(pts[1:], float)
    h = np.maximum(o, c) + rng.uniform(0.2, spread, len(o))
    l = np.minimum(o, c) - rng.uniform(0.2, spread, len(o))
    return o, h, l, c


# ------------------------------------------------------------------ fig 1
LVL, EXT, ENT, STP, TGT = 100.0, 93.0, 103.5, 88.0, 126.0
pts = [118, 112, 107, 102, 100.5, 108, 115, 122, 128, 126, 121, 116, 111, 106,
       102, 101, 96, 94.5, 97, 103.5, 107, 112, 117, 121, 126]
o, h, l, c = path_to_ohlc(pts, seed=3)
l[3] = 100.2; l[4] = LVL + 0.1          # the respected touch stays above
h[16] = LVL - 0.5; h[17] = LVL - 1.0    # sweep bars stay below the level
l[16] = 94.0; l[17] = EXT               # sweep extreme
c[18] = LVL - 0.6; h[18] = LVL - 0.2    # stall below
o[19] = 99.0; c[19] = ENT               # reclaim close = entry bar

fig, ax = plt.subplots(figsize=(10.5, 6.0), dpi=150)
candles(ax, o, h, l, c)
n = len(o)
ax.hlines(LVL, -1, n + 8, color=BLUE, lw=1.6)
ax.text(n + 8.2, LVL, "respected low\n(stops rest below)", color=BLUE, fontsize=9, va="center")
ax.hlines(STP, 14, n + 8, color=RED, lw=1.6, ls=(0, (5, 3)))
ax.text(n + 8.2, STP, "STOP  88.0\nbeyond sweep low − buffer", color=RED, fontsize=9, va="center")
ax.hlines(TGT, 14, n + 8, color=GREEN, lw=1.6, ls=(0, (5, 3)))
ax.text(n + 8.2, TGT, "TARGET  126.0\nnearest resting liquidity\n(prior close / respected high)", color=GREEN, fontsize=9, va="center")

steps = [
    (3.5, 96.0, "1  respected low: touched, moved\n    firmly away — liquidity builds below", "center"),
    (15.0, 119.5, "2  the return — do NOT buy\n    here in anticipation", "center"),
    (13.5, 89.5, "3  sweep: stops below the low get run\n    (must stay < 0.45×ATR deep)", "center"),
    (24.5, 96.5, "4  trap confirmed: 15-min bar CLOSES\n    back above the level → ENTER 103.5", "center"),
    (7.0, 131.5, "5  ride to the opposite pool", "center"),
]
for x, y, txt, ha in steps:
    ax.text(x, y, txt, fontsize=9, color=INK, ha=ha,
            bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.35"))
ax.annotate("", xy=(19.4, ENT - 0.6), xytext=(22.2, 97.8),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
ax.set_xlim(-1.5, n + 21)
ax.set_ylim(84, 136)
ax.set_yticks([])
ax.set_xticks([])
ax.set_title("The liquidity-trap BUY setup — sell setup is the exact mirror at a respected high",
             fontsize=12.5, loc="left", color=INK, pad=14)
ax.text(0, 1.015, "gate: only after the 11:00 ET regime read, only on CHOP/NEUTRAL days · risk = entry − stop · flat by 15:59",
        transform=ax.transAxes, fontsize=9.5, color=INK2)
fig.tight_layout()
fig.savefig(IMG / "guide1_anatomy.png", facecolor=SURFACE)

# ------------------------------------------------------------------ fig 2
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.4), dpi=150)

# (a) gap through
pts_a = [96, 94, 92.5, 94.5, 93, 91, 92.5, 90.5, 92, 90]
o2, h2, l2, c2 = path_to_ohlc(pts_a, spread=1.0, seed=5)
axes[0].hlines(100, -1, len(o2) + 0.5, color=BLUE, lw=1.6)
candles(axes[0], o2, h2, l2, c2)
axes[0].set_ylim(85, 107)
axes[0].text(len(o2) / 2, 102.2, "level 100 — session OPENED below it",
             fontsize=9, ha="center", color=INK)
axes[0].set_title("NO TRADE: gap through the level", fontsize=10.5, loc="left", color=RED, pad=12)
axes[0].text(0, -0.06, "stops were consumed on the gap —\nno liquidity left to trap",
             transform=axes[0].transAxes, fontsize=9, color=INK2, va="top")

# (b) too deep
pts_b = [108, 104, 101, 99, 95, 88, 79, 70, 62, 56, 52]
o2, h2, l2, c2 = path_to_ohlc(pts_b, spread=1.4, seed=8)
axes[1].hlines(100, -1, len(o2) + 0.5, color=BLUE, lw=1.6)
axes[1].hlines(55, -1, len(o2) + 0.5, color=RED, lw=1.2, ls=(0, (4, 3)))
candles(axes[1], o2, h2, l2, c2)
axes[1].set_ylim(40, 122)
axes[1].text(len(o2) / 2, 113, "swept, kept going: > 0.45×ATR below", fontsize=9, ha="center", color=INK)
axes[1].text(len(o2) / 2, 46, "0.45×ATR invalidation line", fontsize=8.5, ha="center", color=RED)
axes[1].set_title("NO TRADE: sweep too deep — breakdown", fontsize=10.5, loc="left", color=RED, pad=12)
axes[1].text(0, -0.06, "a trap stalls just past the level;\nacceptance beyond it = real move",
             transform=axes[1].transAxes, fontsize=9, color=INK2, va="top")

# (c) trend day
pts_c = [116, 112, 108, 103, 99, 96, 92, 88, 85, 81, 78]
o2, h2, l2, c2 = path_to_ohlc(pts_c, spread=1.2, seed=11)
axes[2].hlines(100, -1, len(o2) + 0.5, color=BLUE, lw=1.6)
candles(axes[2], o2, h2, l2, c2)
axes[2].set_ylim(68, 128)
axes[2].text(len(o2) / 2, 121, "11:00 read said TREND_DOWN", fontsize=9, ha="center", color=INK)
axes[2].set_title("NO TRADE: trend-day sweep = run", fontsize=10.5, loc="left", color=RED, pad=12)
axes[2].text(0, -0.06, "on trend days the sweep IS the move —\nfading it funded the other side (Jul 2 NQ: −170 more pts)",
             transform=axes[2].transAxes, fontsize=9, color=INK2, va="top")

for a in axes:
    a.set_xticks([]); a.set_yticks([])
fig.suptitle("The three filters that make the setup tradeable — each one is backtest-verified",
             fontsize=12, x=0.01, ha="left", color=INK)
fig.tight_layout(rect=[0, 0.09, 1, 0.94])
fig.savefig(IMG / "guide2_no_trade.png", facecolor=SURFACE)

# ------------------------------------------------------------------ fig 3: the real trade
es = load_ibkr_json(Path(__file__).resolve().parents[1] / "data" / "es_5min_live.json")
day = es[(pd.Series(es.index.date, index=es.index) == pd.Timestamp("2026-07-01").date())
         & (es.index.time >= dtime(9, 30)) & (es.index.time < dtime(16, 0))]
LVL3, EXT3, ENT3, STP3, TGT3 = 7567.75, 7579.00, 7559.75, 7584.72, 7550.75

fig, ax = plt.subplots(figsize=(10.5, 5.6), dpi=150)
candles(ax, day["open"].values, day["high"].values, day["low"].values, day["close"].values, w=0.55)
n = len(day)
for y, txt, col, ls in [
    (LVL3, f"prior-day high {LVL3:,.2f} (respected level)", BLUE, "solid"),
    (STP3, f"stop {STP3:,.2f}", RED, (0, (5, 3))),
    (TGT3, f"target {TGT3:,.2f} = overnight high (nearest pool)", GREEN, (0, (5, 3))),
]:
    ax.hlines(y, -1, n + 2, color=col, lw=1.5, ls=ls)
    ax.text(n + 2.5, y, txt, color=col, fontsize=9, va="center")

x_of = {ts: i for i, ts in enumerate(day.index)}
sweep_x = x_of[day[day["high"] >= EXT3].index[0]]
ent_ts = [ts for ts in day.index if ts.time() == dtime(12, 45)][0]
ent_x = x_of[ent_ts]
tgt_ts = day.index[(day.index > ent_ts) & (day["low"] <= TGT3)][0]
tgt_x = x_of[tgt_ts]

ax.annotate(f"sweep of the level\nruns to {EXT3:,.2f}", xy=(sweep_x, EXT3), xytext=(sweep_x - 14, EXT3 + 6),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2),
            bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.35"))
ax.annotate(f"12:45 — 15-min close back under the level\nSHORT {ENT3:,.2f}", xy=(ent_x, ENT3),
            xytext=(ent_x + 4, ENT3 + 14), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2),
            bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.35"))
ax.annotate(f"target hit {tgt_ts.strftime('%H:%M')}  (+9.00 pts, +0.08 ATR)", xy=(tgt_x, TGT3),
            xytext=(tgt_x - 26, TGT3 - 9), fontsize=9, color=GREEN,
            arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.2),
            bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.35"))

ticks = [i for i, ts in enumerate(day.index) if ts.minute == 0 and ts.hour % 1 == 0]
ax.set_xticks(ticks, [day.index[i].strftime("%H:%M") for i in ticks], fontsize=8.5)
ax.set_xlim(-1.5, n + 26)
ax.margins(y=0.30)

# ---- what the system said at each daily check-in (computed, not scripted)
A = 114.49  # Jul-1 ATR ref (ETF ATR scaled by prior close, as in the study)
pre1030 = day[day.index.time < dtime(10, 30)]
r1030 = float(pre1030["high"].max() - pre1030["low"].min())
fh = day[day.index.time < dtime(11, 0)]
p_dec = float(fh["close"].iloc[-1])
moc = float(day["close"].iloc[-1])
long_pnl = moc - p_dec
xform = ax.get_xaxis_transform()  # x in data, y in axes fraction
pos_v = (p_dec - float(fh["low"].min())) / (float(fh["high"].max()) - float(fh["low"].min()))
checkins = [
    (dtime(10, 30), 0.995,
     f"10:33 veto check\nrange {r1030:.0f} > {0.35 * A:.0f} pts\n→ not a compression day"),
    (dtime(11, 0), None, None),   # vline only; text goes in the bottom-left box
    (dtime(13, 30), 0.995,
     "13:33 scan\ntrap SHORT working\n(entered 12:45)"),
]
for tt, ytop, txt in checkins:
    xi = next(i for i, ts in enumerate(day.index) if ts.time() >= tt)
    ax.axvline(xi, color=MUTED, lw=1.0, ls=(0, (1, 2)), alpha=0.8, zorder=1)
    if txt:
        ax.text(xi + 0.6, ytop, txt, transform=xform, fontsize=8.2, color=INK2, va="top")
ax.text(0.015, 0.03,
        f"11:07 read: NEUTRAL (0.46 ATR, pos {pos_v:.2f}) → traps ON\n"
        f"band-long also fired @ {p_dec:,.2f}, exits MOC {long_pnl:+,.2f} pts\n"
        "(the losing side of the day — shown for honesty)",
        transform=ax.transAxes, fontsize=8.6, color=INK, ha="left", va="bottom",
        bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.4"))

ax.set_title("The setup on real price — ES, July 1 2026 (journaled trade #1)",
             fontsize=12.5, loc="left", color=INK, pad=14)
ax.text(0, 1.015, "sweep 11.25 pts = 0.10 ATR (valid, < 0.45) · reclaim after the 11:00 gate ✓",
        transform=ax.transAxes, fontsize=9.5, color=INK2)
ax.text(0.985, 0.02, f"16:07 close wrap: day graded CHOP(up) — regime call consistent\n"
        f"journal: trap short +9.00 pts · band long {long_pnl:+,.2f} pts",
        transform=ax.transAxes, fontsize=8.6, color=INK, ha="right", va="bottom",
        bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle="round,pad=0.4"))
fig.tight_layout()
fig.savefig(IMG / "guide3_real_trade.png", facecolor=SURFACE)

print("wrote", sorted(p.name for p in IMG.glob("guide*.png")))
