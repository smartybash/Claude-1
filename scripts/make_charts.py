"""Report figures. Static matplotlib renders of the study's key results."""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from study_filter import classify
from study_intraday import session_table, DEC_BARS

DATA = Path(__file__).resolve().parents[1] / "data"
IMG = Path(__file__).resolve().parents[1] / "reports" / "img"
IMG.mkdir(parents=True, exist_ok=True)

# palette (validated): blue = trend, red = chop, neutral gray for context
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BLUE = "#2a78d6"
RED = "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "sans-serif", "text.color": INK,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
})


def load_pooled():
    qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
    spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")
    parts = []
    for fn, d in [("qqq_1h.json", qqq_d), ("spy_1h.json", spy_d)]:
        intra = load_ibkr_json(DATA / fn)
        parts.append(session_table(intra, d, 2))
    t = pd.concat(parts)
    t["call"] = classify(t)
    t["call3"] = t["call"].str.replace("TREND_UP|TREND_DOWN", "TREND", regex=True)
    return t


t = load_pooled()
base_trend = (t["day_type"] == "TREND").mean()
base_chop = (t["day_type"] == "CHOP").mean()

# ---------------------------------------------------------------- fig 1
order = ["CHOP", "NEUTRAL", "TREND"]
g = t.groupby("call3")
p_trend = g["day_type"].apply(lambda s: (s == "TREND").mean()).reindex(order)
p_chop = g["day_type"].apply(lambda s: (s == "CHOP").mean()).reindex(order)
n = g.size().reindex(order)

fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150)
x = np.arange(3)
w = 0.34
b1 = ax.bar(x - w / 2 - 0.01, p_trend, w, color=BLUE, label="P(trend day)")
b2 = ax.bar(x + w / 2 + 0.01, p_chop, w, color=RED, label="P(chop day)")
ax.axhline(base_trend, color=BLUE, lw=1.2, ls=(0, (4, 3)), alpha=0.55)
ax.axhline(base_chop, color=RED, lw=1.2, ls=(0, (4, 3)), alpha=0.55)
ax.text(2.52, base_trend, f"base {base_trend:.0%}", color=BLUE, fontsize=8.5, va="bottom", ha="right", alpha=0.9)
ax.text(2.52, base_chop, f"base {base_chop:.0%}", color=RED, fontsize=8.5, va="bottom", ha="right", alpha=0.9)
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.012,
                f"{r.get_height():.0%}", ha="center", fontsize=9, color=INK2)
ax.set_xticks(x, [f"{c}\n(n={n[c]})" for c in order])
ax.set_ylim(0, 0.85)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_axisbelow(True)
ax.grid(axis="x", visible=False)
ax.set_title("What the day became, given the 11:00 ET filter call", fontsize=12, color=INK, loc="left", pad=14)
ax.text(0, 1.015, "QQQ + SPY pooled, 306 sessions, Nov 2025 – Jul 2026", transform=ax.transAxes,
        fontsize=9, color=INK2)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(IMG / "fig1_call_vs_outcome.png", facecolor=SURFACE)

# ---------------------------------------------------------------- fig 2
fig, ax = plt.subplots(figsize=(8, 4.8), dpi=150)
# decision regions
ax.axvspan(0, 0.35, color=RED, alpha=0.07, lw=0)
ax.add_patch(plt.Rectangle((0.55, 0.8), 1.65, 0.2, color=BLUE, alpha=0.09, lw=0))
ax.add_patch(plt.Rectangle((0.55, 0.0), 1.65, 0.2, color=BLUE, alpha=0.09, lw=0))
colors = {"TREND": BLUE, "CHOP": RED, "NEUTRAL": MUTED}
for dt in ["NEUTRAL", "CHOP", "TREND"]:
    s = t[t["day_type"] == dt]
    ax.scatter(s["fh_range_atr"], s["fh_pos"], s=26, c=colors[dt],
               edgecolors=SURFACE, linewidths=0.8, alpha=0.9 if dt != "NEUTRAL" else 0.55,
               label=f"{dt.title()} day")
ax.text(0.175, 1.06, "CHOP call", color=RED, fontsize=9.5, ha="center", fontweight="bold")
ax.text(1.35, 1.06, "TREND call (close pinned to extreme)", color=BLUE, fontsize=9.5, ha="center", fontweight="bold")
ax.set_xlim(0, 2.2)
ax.set_ylim(-0.04, 1.12)
ax.set_xlabel("First-90-min range / daily ATR(20)")
ax.set_ylabel("Close position in first-90-min range")
ax.set_axisbelow(True)
ax.set_title("Where each session sat at 11:00 ET, colored by what it became", fontsize=12, color=INK, loc="left", pad=14)
ax.text(0, 1.015, "QQQ + SPY pooled hourly sessions; shaded areas are the filter's decision regions",
        transform=ax.transAxes, fontsize=9, color=INK2)
ax.legend(frameon=False, fontsize=9, loc="center right")
fig.tight_layout()
fig.savefig(IMG / "fig2_decision_map.png", facecolor=SURFACE)

# ---------------------------------------------------------------- fig 3
# robustness of the chop veto across instruments/samples
from regime.data import overnight_stats

rows = []
qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")
samples = [
    ("QQQ 1h", "qqq_1h.json", qqq_d, 2),
    ("SPY 1h", "spy_1h.json", spy_d, 2),
    ("QQQ 30m", "qqq_30min.json", qqq_d, 2),
    ("SPY 30m", "spy_30min.json", spy_d, 2),
    ("NQ fut", "nq_1h.json", None, 2),
    ("ES fut", "es_1h.json", None, 2),
]
for name, fn, d, k in samples:
    tt = session_table(load_ibkr_json(DATA / fn), d, k)
    m = tt["fh_range_atr"] < 0.35
    rows.append({
        "sample": name,
        "cond": (tt.loc[m, "day_type"] == "CHOP").mean(),
        "base": (tt["day_type"] == "CHOP").mean(),
        "n": int(m.sum()),
    })
rob = pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
x = np.arange(len(rob))
w = 0.34
ax.bar(x - w / 2 - 0.01, rob["base"], w, color="#c3c2b7", label="base P(chop day)")
bars = ax.bar(x + w / 2 + 0.01, rob["cond"], w, color=RED, label="P(chop day | compressed first hour)")
for r, nn in zip(bars, rob["n"]):
    ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.015, f"{r.get_height():.0%}",
            ha="center", fontsize=9, color=INK2)
ax.set_xticks(x, [f"{s}\n(n={nn})" for s, nn in zip(rob["sample"], rob["n"])], fontsize=9)
ax.set_ylim(0, 1.3)
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_axisbelow(True)
ax.grid(axis="x", visible=False)
ax.set_title("The chop veto holds everywhere: compressed first hour → chop day", fontsize=12, color=INK, loc="left", pad=14)
ax.text(0, 1.015, "First-hour range < 0.35× daily ATR(20); n = sessions triggering the veto in each sample",
        transform=ax.transAxes, fontsize=9, color=INK2)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(IMG / "fig3_chop_veto_robustness.png", facecolor=SURFACE)

print("wrote", sorted(p.name for p in IMG.glob("*.png")))
