#!/usr/bin/env python3
"""Annotated pre-open levels chart: last ~2 sessions of 5-min/30-min bars with
the dealer-gamma flip / call wall / put wall and the prior-day value area drawn
on, one panel per instrument. Pure visualisation of what the ToS study plots."""
from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parent.parent
ET = "America/New_York"

# instrument -> (price file, gamma slot key, VA(vah,poc,val), label)
def load(f):
    d = json.load(open(ROOT / "data" / f))
    cols = [k for k in ("open", "high", "low", "close", "volume") if k in d]
    s = pd.DataFrame({k: d[k] for k in cols},
                     index=pd.to_datetime(d["time"], utc=True).tz_convert(ET)).sort_index()
    if "volume" not in s:
        s["volume"] = 1.0
    return s[~s.index.duplicated(keep="last")]

gl = json.load(open(ROOT / "data" / "gamma_levels.json"))["levels"]
# VA (today's prior-session) from the generated studies' baked value — recompute here
sys.path.insert(0, str(ROOT))
from sweeplib.levels import volume_profile

def prior_va(s):
    rth = s[(s.index.strftime("%H:%M") >= "09:30") & (s.index.strftime("%H:%M") <= "16:00")]
    days = sorted({d for d in rth.index.strftime("%Y-%m-%d")})
    prev = days[-2] if len(days) >= 2 else days[-1]
    bars = rth[rth.index.strftime("%Y-%m-%d") == prev]
    return volume_profile(bars, 50)   # (poc, vah, val)

PANELS = [
    ("MNQ / NQ", "nq_5min_eth_live.json", "NQ"),
    ("QQQ",       "qqq_5min.json",         "QQQ"),
    ("MES / ES",  "es_30m_live.json",      None),   # ES uses SPY-scaled slot
    ("SPY",       "spy_30m_live.json",     "SPY"),
]
ES_SPY = 10.0531

fig, axes = plt.subplots(2, 2, figsize=(15, 9))
fig.suptitle("Pre-open dealer-gamma map — Tue 2026-08-18  (all four gapped BELOW flip = negative-gamma open)",
             fontsize=13, fontweight="bold")

for ax, (title, pf, slot) in zip(axes.flat, PANELS):
    s = load(pf)
    s = s[s.index >= s.index[-1] - pd.Timedelta(days=3)]
    x = mdates.date2num(s.index.to_pydatetime())
    # candles
    for xi, (_, r) in zip(x, s.iterrows()):
        up = r.close >= r.open
        ax.plot([xi, xi], [r.low, r.high], color="#888", lw=0.5, zorder=1)
        ax.plot([xi, xi], [r.open, r.close], color=("#26a69a" if up else "#ef5350"), lw=2.2, zorder=2)
    poc, vah, val = prior_va(s)
    if slot == "SPY" or title.startswith("MES"):
        g = gl["SPY"]; m = ES_SPY if title.startswith("MES") else 1.0
        flip, cw, pw = g["gamma_flip"]*m, g["call_wall"]*m, g["put_wall"]*m
    else:
        g = gl[slot]; flip, cw, pw = g["gamma_flip"], g["call_wall"], g["put_wall"]
    px = s.close.iloc[-1]
    for y, c, ls, lbl in [(cw, "#ef5350", "--", f"call wall {cw:,.0f}"),
                          (flip, "white", "-", f"gamma flip {flip:,.0f}"),
                          (pw, "#26a69a", "--", f"put wall {pw:,.0f}")]:
        ax.axhline(y, color=c, ls=ls, lw=1.6, zorder=3)
        ax.text(x[-1], y, f" {lbl}", va="center", ha="left", fontsize=8, color=c, fontweight="bold")
    # prior-day value area band
    ax.axhspan(val, vah, color="#42a5f5", alpha=0.10, zorder=0)
    for y, lbl in [(vah, f"VAH {vah:,.1f}"), (poc, f"POC {poc:,.1f}"), (val, f"VAL {val:,.1f}")]:
        ax.axhline(y, color="#42a5f5", ls=":", lw=1.0, zorder=2)
        ax.text(x[0], y, f"{lbl} ", va="center", ha="right", fontsize=7, color="#42a5f5")
    ax.axhline(px, color="#ffd54f", lw=1.0, alpha=0.7)
    ax.text(x[-1], px, f" px {px:,.1f}", va="bottom", ha="right", fontsize=8, color="#ffd54f", fontweight="bold")
    reg = "BELOW flip -> NEG gamma / trend-down" if px < flip else "above flip -> range/fade"
    ax.set_title(f"{title}   {px:,.1f}   ({reg})", fontsize=10, fontweight="bold",
                 color=("#ef5350" if px < flip else "#26a69a"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M", tz=s.index.tz))
    ax.tick_params(labelsize=7); ax.margins(x=0.02)
    ax.set_facecolor("#1a1a1a"); ax.grid(True, alpha=0.12)

for ax in axes.flat: ax.set_facecolor("#1a1a1a")
fig.patch.set_facecolor("#0e0e0e")
for ax in axes.flat:
    ax.tick_params(colors="#aaa"); [sp.set_color("#444") for sp in ax.spines.values()]
plt.tight_layout(rect=[0, 0, 1, 0.96])
out = ROOT / "reports" / "img" / "gamma_levels_map.png"
plt.savefig(out, dpi=120, facecolor=fig.get_facecolor())
print("wrote", out)
