# =====================================================================
# NQ Confluence — three-filter system + market structure (ThinkOrSwim)
#   FILTER 1 LOCATION  : A+/DENSE zones (edit the ZONE inputs daily)
#   FILTER 2 DIRECTION : macro bias from the daily 10/20 SMA
#   FILTER 3 EXTENSION : session VWAP +/- sigma stretch
#   + regression channel + trend-aligned fade / break signals & alerts
#   + MARKET STRUCTURE : swings (HH/HL/LH/LL), BOS, CHoCH  <-- put a copy
#     of this study on a 15-MIN chart for the 15-min structure the video uses.
#
# NOTE: thinkScript identifiers are CASE-INSENSITIVE, so every def and plot
# name here is distinct; "VWAP" is reserved so the plot is named SessVWAP.
# Paste into Studies > Create > thinkScript Editor.
# =====================================================================
declare upper;

input kStretch      = 0.5;   # min |VWAP sigma| for the EXTENSION filter
input chanLen       = 60;    # regression-channel lookback (bars)
input chanDev       = 2.0;   # channel half-width in residual sigma
input showChannel   = yes;
input showVWAPbands = yes;

# ---- ZONES (edit daily): hi / lo / is-resistance ----
input z1_hi = 28763.0;  input z1_lo = 28701.0;  input z1_resist = yes;   # A+ breakdown shelf
input z2_hi = 28254.0;  input z2_lo = 28178.0;  input z2_resist = no;    # DENSE support
input z3_hi = 28111.0;  input z3_lo = 27990.0;  input z3_resist = no;    # DENSE support

# ---- FILTER 2: macro DIRECTION (daily 10/20 SMA + position) ----
def dClose = close(period = AggregationPeriod.DAY);
def sma10  = Average(dClose, 10);
def sma20  = Average(dClose, 20);
def bias   = if sma10 > sma20 and dClose > sma20 then 1
             else if sma10 < sma20 and dClose < sma20 then -1 else 0;

# ---- FILTER 3: session VWAP + sigma, stretch = (close-VWAP)/sigma ----
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
AddCloud(z1_hi, z1_lo, if z1_resist then Color.RED else Color.GREEN,
                       if z1_resist then Color.RED else Color.GREEN);
AddCloud(z2_hi, z2_lo, if z2_resist then Color.RED else Color.GREEN,
                       if z2_resist then Color.RED else Color.GREEN);
AddCloud(z3_hi, z3_lo, if z3_resist then Color.RED else Color.GREEN,
                       if z3_resist then Color.RED else Color.GREEN);

# ---- regression channel (trailing linreg + residual sigma) ----
def regVal = Inertia(close, chanLen);
def rStd   = StDev(close - regVal, chanLen);
plot ChMid = if showChannel then regVal else Double.NaN;
plot ChUp  = if showChannel then regVal + chanDev * rStd else Double.NaN;
plot ChLo  = if showChannel then regVal - chanDev * rStd else Double.NaN;
ChMid.SetDefaultColor(Color.VIOLET);
ChUp.SetDefaultColor(Color.VIOLET);  ChUp.SetStyle(Curve.SHORT_DASH);
ChLo.SetDefaultColor(Color.VIOLET);  ChLo.SetStyle(Curve.SHORT_DASH);

# =====================================================================
# SIGNALS — trend-aligned only (matches the backtested rules)
#   FADE  : tag a trend-aligned zone + >= kStretch sigma  (mean-reversion)
#   BREAK : 30m close THROUGH a trend-aligned level, with trend (continuation)
# =====================================================================
def fadeShort = bias < 0 and z1_resist and high >= z1_lo and close < z1_lo and stretch >= kStretch;
def fadeLong  = bias > 0 and !z1_resist and low  <= z1_hi and close > z1_hi and stretch <= -kStretch;

def brkShort  = bias < 0 and ((!z2_resist and close < z2_lo and close[1] >= z2_lo) or
                              (!z3_resist and close < z3_lo and close[1] >= z3_lo));
def brkLong   = bias > 0 and ((z2_resist and close > z2_hi and close[1] <= z2_hi) or
                              (z3_resist and close > z3_hi and close[1] <= z3_hi));

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

Alert(fadeShort, "NQ FADE-short: zone tag + stretch (with trend)", Alert.BAR, Sound.Ring);
Alert(fadeLong,  "NQ FADE-long: zone tag + stretch (with trend)",  Alert.BAR, Sound.Ring);
Alert(brkShort,  "NQ BREAK-short: 30m close thru support (with trend)", Alert.BAR, Sound.Bell);
Alert(brkLong,   "NQ BREAK-long: 30m close thru resistance (with trend)", Alert.BAR, Sound.Bell);

# =====================================================================
# MARKET STRUCTURE  — swings + BOS / CHoCH  (best on a 15-min chart)
#   Areas of significance = the last swing high / low (dashed gray lines):
#   that's the liquidity the trend must break. BOS = break WITH trend
#   (continuation); CHoCH = first break AGAINST trend (possible reversal).
# =====================================================================
input showStructure = yes;
input swingStrength = 5;     # bars each side of a swing pivot

def ph = high[swingStrength] == Highest(high, 2 * swingStrength + 1);
def pl = low[swingStrength]  == Lowest(low,  2 * swingStrength + 1);

def swHi  = if ph then high[swingStrength] else swHi[1];   # last confirmed swing high
def swLo  = if pl then low[swingStrength]  else swLo[1];   # last confirmed swing low
def pSwHi = if ph then swHi[1] else pSwHi[1];              # the one before it
def pSwLo = if pl then swLo[1] else pSwLo[1];

# structure direction: flips when a close breaks the last swing hi/lo
def dir = CompoundValue(1,
    if swHi > 0 and close > swHi then 1
    else if swLo > 0 and close < swLo then -1
    else dir[1], 0);

def brokeUp = swHi > 0 and close > swHi and close[1] <= swHi;
def brokeDn = swLo > 0 and close < swLo and close[1] >= swLo;
def bosUp   = brokeUp and dir[1] > 0;      # break up, already bullish -> continuation
def chochUp = brokeUp and dir[1] <= 0;     # break up, was bearish     -> character change
def bosDn   = brokeDn and dir[1] < 0;
def chochDn = brokeDn and dir[1] >= 0;

# swing tags (note: printed swingStrength bars after the pivot, once confirmed)
AddChartBubble(showStructure and ph and high[swingStrength] >  pSwHi, high[swingStrength], "HH", Color.GREEN, yes);
AddChartBubble(showStructure and ph and high[swingStrength] <= pSwHi, high[swingStrength], "LH", Color.RED,   yes);
AddChartBubble(showStructure and pl and low[swingStrength]  <  pSwLo, low[swingStrength],  "LL", Color.RED,   no);
AddChartBubble(showStructure and pl and low[swingStrength]  >= pSwLo, low[swingStrength],  "HL", Color.GREEN, no);

# BOS / CHoCH at the break bar
AddChartBubble(showStructure and (bosUp or bosDn),     close, "BOS",   Color.CYAN,   bosUp);
AddChartBubble(showStructure and (chochUp or chochDn), close, "CHoCH", Color.YELLOW, chochUp);

# the two areas of significance — last swing hi / lo (the liquidity levels)
plot SwingHi = if showStructure then swHi else Double.NaN;
plot SwingLo = if showStructure then swLo else Double.NaN;
SwingHi.SetDefaultColor(Color.GRAY);  SwingHi.SetStyle(Curve.LONG_DASH);
SwingLo.SetDefaultColor(Color.GRAY);  SwingLo.SetStyle(Curve.LONG_DASH);

Alert(showStructure and (bosUp or bosDn),     "NQ BOS (structure continuation)", Alert.BAR, Sound.Ding);
Alert(showStructure and (chochUp or chochDn), "NQ CHoCH (structure shift)",      Alert.BAR, Sound.Ding);

# ---- status labels ----
AddLabel(yes, "Macro " + (if bias > 0 then "UP" else if bias < 0 then "DOWN" else "MIXED"),
         if bias < 0 then Color.RED else if bias > 0 then Color.GREEN else Color.GRAY);
AddLabel(yes, "Stretch " + Round(stretch, 1) + "s",
         if AbsValue(stretch) >= kStretch then Color.YELLOW else Color.GRAY);
AddLabel(yes, "VWAP " + Round(vwapVal, 0), Color.CYAN);
AddLabel(showStructure, "Structure " + (if dir > 0 then "BULL (HH/HL)" else "BEAR (LH/LL)"),
         if dir > 0 then Color.GREEN else Color.RED);
