"""Generate a COMPLETE, ready-to-paste thinkScript for each instrument
(MNQ, QQQ, MES, SPY) with that symbol's confluence zones baked in.
Standard rerun step: refresh data + PRICES, run, paste each full box on its chart.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt

DATE = "2026-08-03"
INST = [   # (symbol label, 30-min file, is_futures, live price)
    ("MNQ", "nq_30min_eth.json", True, 28578.0),
    ("QQQ", "qqq_30m_live.json", False, 692.34),
    ("MES", "es_30m_live.json",  True, 7587.75),
    ("SPY", "spy_30m_live.json", False, 753.62),
]

TEMPLATE = r"""# =====================================================================
# __SYM__ Confluence — 3-filter + clean structure (ThinkOrSwim)   __DATE__
#   Zones baked in for __SYM__ @ __PX__. Apply to a 30-min __SYM__ chart.
#   thinkScript identifiers are CASE-INSENSITIVE; "VWAP" is reserved (plot=SessVWAP).
#   Paste the WHOLE box.
# =====================================================================
declare upper;

input kStretch      = 0.5;
input chanLen       = 60;
input chanDev       = 2.0;
input showChannel   = yes;
input showVWAPbands = yes;

# ---- ZONES (__SYM__ __DATE__): hi / lo / is-resistance ----
input z1_hi = __Z1HI__;  input z1_lo = __Z1LO__;  input z1_resist = __Z1R__;
input z2_hi = __Z2HI__;  input z2_lo = __Z2LO__;  input z2_resist = __Z2R__;
input z3_hi = __Z3HI__;  input z3_lo = __Z3LO__;  input z3_resist = __Z3R__;
input z4_hi = __Z4HI__;  input z4_lo = __Z4LO__;  input z4_resist = __Z4R__;

# ---- FILTER 2: macro DIRECTION (daily 10/20 SMA) ----
def dClose = close(period = AggregationPeriod.DAY);
def sma10  = Average(dClose, 10);
def sma20  = Average(dClose, 20);
def bias   = if sma10 > sma20 and dClose > sma20 then 1
             else if sma10 < sma20 and dClose < sma20 then -1 else 0;

# ---- FILTER 3: session VWAP + sigma stretch ----
def newDay  = GetDay() != GetDay()[1];
def vSum    = if newDay then volume else vSum[1] + volume;
def pvSum   = if newDay then volume * hlc3 else pvSum[1] + volume * hlc3;
def vwapVal = pvSum / vSum;
def varSum  = if newDay then volume * Sqr(hlc3 - vwapVal) else varSum[1] + volume * Sqr(hlc3 - vwapVal);
def sigma   = Sqrt(varSum / vSum);
def stretch = if sigma > 0 then (close - vwapVal) / sigma else 0;

plot SessVWAP = vwapVal;
SessVWAP.SetDefaultColor(Color.CYAN);
plot BandUp = if showVWAPbands then vwapVal + kStretch * sigma else Double.NaN;
plot BandDn = if showVWAPbands then vwapVal - kStretch * sigma else Double.NaN;
BandUp.SetDefaultColor(Color.DARK_GRAY);  BandUp.SetStyle(Curve.SHORT_DASH);
BandDn.SetDefaultColor(Color.DARK_GRAY);  BandDn.SetStyle(Curve.SHORT_DASH);

# ---- FILTER 1: LOCATION zones (red = resistance, green = support) ----
AddCloud(z1_hi, z1_lo, if z1_resist then Color.RED else Color.GREEN, if z1_resist then Color.RED else Color.GREEN);
AddCloud(z2_hi, z2_lo, if z2_resist then Color.RED else Color.GREEN, if z2_resist then Color.RED else Color.GREEN);
AddCloud(z3_hi, z3_lo, if z3_resist then Color.RED else Color.GREEN, if z3_resist then Color.RED else Color.GREEN);
AddCloud(z4_hi, z4_lo, if z4_resist then Color.RED else Color.GREEN, if z4_resist then Color.RED else Color.GREEN);

# ---- regression channel ----
def regVal = Inertia(close, chanLen);
def rStd   = StDev(close - regVal, chanLen);
plot ChMid = if showChannel then regVal else Double.NaN;
plot ChUp  = if showChannel then regVal + chanDev * rStd else Double.NaN;
plot ChLo  = if showChannel then regVal - chanDev * rStd else Double.NaN;
ChMid.SetDefaultColor(Color.VIOLET);
ChUp.SetDefaultColor(Color.VIOLET);  ChUp.SetStyle(Curve.SHORT_DASH);
ChLo.SetDefaultColor(Color.VIOLET);  ChLo.SetStyle(Curve.SHORT_DASH);

# ---- SIGNALS (trend-aligned, across all 4 zones) ----
def fadeShort = bias < 0 and stretch >= kStretch and (
    (z1_resist and high >= z1_lo and close < z1_lo) or
    (z2_resist and high >= z2_lo and close < z2_lo) or
    (z3_resist and high >= z3_lo and close < z3_lo) or
    (z4_resist and high >= z4_lo and close < z4_lo));
def fadeLong = bias > 0 and stretch <= -kStretch and (
    (!z1_resist and low <= z1_hi and close > z1_hi) or
    (!z2_resist and low <= z2_hi and close > z2_hi) or
    (!z3_resist and low <= z3_hi and close > z3_hi) or
    (!z4_resist and low <= z4_hi and close > z4_hi));
def brkShort = bias < 0 and (
    (!z1_resist and close < z1_lo and close[1] >= z1_lo) or
    (!z2_resist and close < z2_lo and close[1] >= z2_lo) or
    (!z3_resist and close < z3_lo and close[1] >= z3_lo) or
    (!z4_resist and close < z4_lo and close[1] >= z4_lo));
def brkLong = bias > 0 and (
    (z1_resist and close > z1_hi and close[1] <= z1_hi) or
    (z2_resist and close > z2_hi and close[1] <= z2_hi) or
    (z3_resist and close > z3_hi and close[1] <= z3_hi) or
    (z4_resist and close > z4_hi and close[1] <= z4_hi));

plot SigFadeShort = if fadeShort then high else Double.NaN;
SigFadeShort.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
SigFadeShort.SetDefaultColor(Color.RED);
plot SigFadeLong = if fadeLong then low else Double.NaN;
SigFadeLong.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
SigFadeLong.SetDefaultColor(Color.GREEN);
plot SigBrkShort = if brkShort then low else Double.NaN;
SigBrkShort.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
SigBrkShort.SetDefaultColor(Color.MAGENTA);
plot SigBrkLong = if brkLong then high else Double.NaN;
SigBrkLong.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
SigBrkLong.SetDefaultColor(Color.MAGENTA);

Alert(fadeShort, "__SYM__ FADE-short", Alert.BAR, Sound.Ring);
Alert(fadeLong,  "__SYM__ FADE-long",  Alert.BAR, Sound.Ring);
Alert(brkShort,  "__SYM__ BREAK-short", Alert.BAR, Sound.Bell);
Alert(brkLong,   "__SYM__ BREAK-long",  Alert.BAR, Sound.Bell);

# ---- STRUCTURE (clean): last swing hi/lo lines + BULL/BEAR label ----
input showStructure = yes;
input swingStrength = 5;
def ph = high[swingStrength] == Highest(high, 2 * swingStrength + 1);
def pl = low[swingStrength]  == Lowest(low,  2 * swingStrength + 1);
def swHi = if ph then high[swingStrength] else swHi[1];
def swLo = if pl then low[swingStrength]  else swLo[1];
def dir  = CompoundValue(1,
    if swHi > 0 and close > swHi then 1
    else if swLo > 0 and close < swLo then -1
    else dir[1], 0);
plot SwingHi = if showStructure then swHi else Double.NaN;
plot SwingLo = if showStructure then swLo else Double.NaN;
SwingHi.SetDefaultColor(Color.GRAY);  SwingHi.SetStyle(Curve.LONG_DASH);
SwingLo.SetDefaultColor(Color.GRAY);  SwingLo.SetStyle(Curve.LONG_DASH);

# ---- status labels ----
AddLabel(yes, "__SYM__ Macro " + (if bias > 0 then "UP" else if bias < 0 then "DOWN" else "MIXED"),
         if bias < 0 then Color.RED else if bias > 0 then Color.GREEN else Color.GRAY);
AddLabel(yes, "Stretch " + Round(stretch, 1) + "s",
         if AbsValue(stretch) >= kStretch then Color.YELLOW else Color.GRAY);
AddLabel(yes, "VWAP " + Round(vwapVal, 2), Color.CYAN);
AddLabel(showStructure, "Struct " + (if dir > 0 then "BULL" else "BEAR"),
         if dir > 0 then Color.GREEN else Color.RED);
"""


def load_any(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert("America/New_York"))
    return df[~df.index.duplicated(keep="last")].sort_index()


def split(df, fut):
    s = pd.Series(df.index.date, index=df.index)
    if fut:
        ev = df.index.hour >= 18
        s[ev] = (df.index[ev] + pd.Timedelta(days=1)).date
    df = df.assign(sess=pd.to_datetime(s.values))
    ids = sorted(df["sess"].unique())
    return df, ids, {i: df[df["sess"] == i] for i in ids}


def zones_for(fname, fut, px):
    df = load_any(fname)
    df, ids, by = split(df, fut)
    hist = df[df["sess"] < ids[-1]]
    zs, _ = bt.build(hist, by[ids[-2]], 13)
    az = [z for z in zs if (z["w"] >= 6 or z["nt"] >= 3) and abs(z["price"] - px) <= 0.03 * px]
    az.sort(key=lambda z: abs(z["price"] - px))
    az = az[:4]
    az.sort(key=lambda z: z["price"], reverse=True)
    while len(az) < 4 and az:          # pad to 4 valid inputs with the farthest zone
        az.append(az[-1])
    return az


def main():
    for sym, fname, fut, px in INST:
        d = 2 if px < 2000 else 1
        az = zones_for(fname, fut, px)
        s = TEMPLATE.replace("__SYM__", sym).replace("__DATE__", DATE).replace("__PX__", f"{px:.{d}f}")
        for i, z in enumerate(az, 1):
            res = "yes" if z["price"] > px else "no"
            s = (s.replace(f"__Z{i}HI__", f"{z['hi']:.{d}f}")
                  .replace(f"__Z{i}LO__", f"{z['lo']:.{d}f}")
                  .replace(f"__Z{i}R__", res))
        out = ROOT / "charts" / f"tos_{sym}.ts"
        out.write_text(s)
        print(f"wrote {out}  ({len(az)} zones)")


if __name__ == "__main__":
    main()
