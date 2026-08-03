# =====================================================================
# MES Confluence — 3-filter + clean structure (ThinkOrSwim)   2026-08-03
#   Zones baked in for MES @ 7599.2. Apply to a 30-min MES chart.
#   thinkScript identifiers are CASE-INSENSITIVE; "VWAP" is reserved (plot=SessVWAP).
#   Paste the WHOLE box.
# =====================================================================
declare upper;

input kStretch      = 0.5;
input chanLen       = 60;
input chanDev       = 2.0;
input showChannel   = yes;
input showVWAPbands = yes;

# ---- ZONES (MES 2026-08-03): hi / lo / is-resistance ----
input z1_hi = 7524.8;  input z1_lo = 7482.8;  input z1_resist = no;
input z2_hi = 7427.5;  input z2_lo = 7427.5;  input z2_resist = no;
input z3_hi = 7404.3;  input z3_lo = 7368.0;  input z3_resist = no;
input z4_hi = 7404.3;  input z4_lo = 7368.0;  input z4_resist = no;

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

Alert(fadeShort, "MES FADE-short", Alert.BAR, Sound.Ring);
Alert(fadeLong,  "MES FADE-long",  Alert.BAR, Sound.Ring);
Alert(brkShort,  "MES BREAK-short", Alert.BAR, Sound.Bell);
Alert(brkLong,   "MES BREAK-long",  Alert.BAR, Sound.Bell);

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
AddLabel(yes, "MES Macro " + (if bias > 0 then "UP" else if bias < 0 then "DOWN" else "MIXED"),
         if bias < 0 then Color.RED else if bias > 0 then Color.GREEN else Color.GRAY);
AddLabel(yes, "Stretch " + Round(stretch, 1) + "s",
         if AbsValue(stretch) >= kStretch then Color.YELLOW else Color.GRAY);
AddLabel(yes, "VWAP " + Round(vwapVal, 2), Color.CYAN);
AddLabel(showStructure, "Struct " + (if dir > 0 then "BULL" else "BEAR"),
         if dir > 0 then Color.GREEN else Color.RED);
