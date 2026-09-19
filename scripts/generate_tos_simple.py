"""CLEAN MODE — a minimal 'VWAP + FVG' ThinkOrSwim study per instrument
(MNQ, QQQ, MES, SPY), the way the reference chart trades: bias off VWAP, enter at
fair-value-gap zones. Runs ALONGSIDE the full confluence/gamma study.

What's on it, and nothing else:
  - session VWAP (white line)
  - Fair Value Gaps: the most recent UNFILLED bullish (green) and bearish (red)
    3-bar imbalance, drawn as a shaded zone that auto-clears when price fills it
    (native thinkScript, updates live)
  - the two context bits that survived backtesting: the gamma-scaled EM range band
    (yellow) and a one-word regime tag

FVG (3-bar imbalance): bullish = low > high[2] (gap left below), zone [high[2]..low];
bearish = high < low[2], zone [high..low[2]]. "Filled" clears the zone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.gamma_context as gc

DATE = "2026-08-11"
INST = [
    ("MNQ", "nq_30min_eth.json", True),
    ("QQQ", "qqq_30m_live.json", False),
    ("MES", "es_30m_live.json",  True),
    ("SPY", "spy_30m_live.json", False),
]

TEMPLATE = r"""# =====================================================================
# __SYM__ CLEAN — VWAP + FVG (ThinkOrSwim)   __DATE__
#   Bias off VWAP; trade the fair-value-gap zones. Apply to a 1-5 min __SYM__ chart.
#   Paste the WHOLE box. (Runs alongside the full confluence study.)
# =====================================================================
declare upper;

# ---- session VWAP ----
def newDay  = GetDay() != GetDay()[1];
def vSum    = if newDay then volume else vSum[1] + volume;
def pvSum   = if newDay then volume * hlc3 else pvSum[1] + volume * hlc3;
plot VWAPln = pvSum / vSum;
VWAPln.SetDefaultColor(Color.WHITE);  VWAPln.SetLineWeight(2);

# ---- Fair Value Gaps (most recent UNFILLED each side) ----
input showFVG = yes;
def bull = low > high[2];            # bullish 3-bar gap (support below)
def bear = high < low[2];            # bearish 3-bar gap (resistance above)

# bullish zone [bLo..bUp]; both edges clear together once price fills it (low <= bLo)
def bUp = if bull then low
          else if IsNaN(bLo[1]) then Double.NaN
          else if low <= bLo[1] then Double.NaN
          else bUp[1];
def bLo = if bull then high[2]
          else if IsNaN(bLo[1]) then Double.NaN
          else if low <= bLo[1] then Double.NaN
          else bLo[1];
# bearish zone [rLo..rUp]; both edges clear together once price fills it (high >= rUp)
def rUp = if bear then low[2]
          else if IsNaN(rUp[1]) then Double.NaN
          else if high >= rUp[1] then Double.NaN
          else rUp[1];
def rLo = if bear then high
          else if IsNaN(rUp[1]) then Double.NaN
          else if high >= rUp[1] then Double.NaN
          else rLo[1];

plot BullTop = if showFVG then bUp else Double.NaN;
plot BullBot = if showFVG then bLo else Double.NaN;
plot BearTop = if showFVG then rUp else Double.NaN;
plot BearBot = if showFVG then rLo else Double.NaN;
BullTop.Hide(); BullBot.Hide(); BearTop.Hide(); BearBot.Hide();
AddCloud(BullTop, BullBot, Color.DARK_GREEN, Color.DARK_GREEN);   # bullish FVG = support
AddCloud(BearTop, BearBot, Color.DARK_RED,   Color.DARK_RED);     # bearish FVG = resistance

# ---- context (kept): gamma-scaled EM band + regime ----
input showCtx = yes;
input emUpV = __EMUP__;   input emDnV = __EMDN__;
plot EMup = if showCtx then emUpV else Double.NaN;
plot EMdn = if showCtx then emDnV else Double.NaN;
EMup.SetDefaultColor(Color.YELLOW);  EMup.SetStyle(Curve.LONG_DASH);
EMdn.SetDefaultColor(Color.YELLOW);  EMdn.SetStyle(Curve.LONG_DASH);

AddLabel(showCtx, "EM +/-__EMADJ__ (x__EMMULT__)", Color.YELLOW);
AddLabel(showCtx, "__REGIME__", Color.__GCOLOR__);
AddLabel(showFVG, "FVG: green=support  red=resistance", Color.GRAY);
"""


def load_any(name):
    import json
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("close",)},
                      index=pd.to_datetime(r["time"], utc=True))
    return df[~df.index.duplicated(keep="last")].sort_index()


def main():
    GCOLOR = {"VOL-CALM": "GREEN", "VOL-STRESSED": "ORANGE", "VOL-NEUTRAL": "GRAY"}
    for sym, fname, fut in INST:
        px = float(load_any(fname)["close"].iloc[-1])
        d = 2 if px < 2000 else 1
        ctx = gc.context(px, sym)
        s = (TEMPLATE.replace("__SYM__", sym).replace("__DATE__", DATE)
             .replace("__EMUP__", f"{ctx['up']:.{d}f}").replace("__EMDN__", f"{ctx['dn']:.{d}f}")
             .replace("__EMADJ__", f"{ctx['em_adj']:.{d}f}").replace("__EMMULT__", f"{ctx['em_mult']:.2f}")
             .replace("__REGIME__", ctx["regime"]).replace("__GCOLOR__", GCOLOR[ctx["regime"]]))
        print(f"\n===== COPY BELOW into ThinkOrSwim — {sym} CLEAN study ({DATE}) =====")
        print(s.rstrip())
        print(f"===== END {sym} CLEAN study =====")


if __name__ == "__main__":
    main()
