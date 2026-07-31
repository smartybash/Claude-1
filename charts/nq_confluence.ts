# =====================================================================
# NQ Confluence — three-filter system  (ThinkOrSwim / thinkScript)
#   FILTER 1 LOCATION  : A+/DENSE zones (edit the ZONE inputs daily)
#   FILTER 2 DIRECTION : macro bias from the daily 10/20 SMA
#   FILTER 3 EXTENSION : session VWAP +/- sigma stretch
#   + regression channel (breakout / tap-retrace context)
#   + fade / break signals & alerts, trend-aligned only
#
# NOTE: ThinkOrSwim uses thinkScript, NOT Pine. Paste this into
#   Studies > Create > thinkScript Editor. Apply to a 30-min NQ (/NQ or /MNQ)
#   chart. Update the ZONE inputs each morning from the three_filter_read output.
# =====================================================================
declare upper;

input kStretch     = 0.5;    # min |VWAP sigma| for the EXTENSION filter
input chanLen      = 60;     # regression-channel lookback (bars)
input chanDev      = 2.0;    # channel half-width in residual sigma
input showChannel  = yes;
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
def vwap    = pvSum / vSum;
def varSum  = if newDay then volume * Sqr(hlc3 - vwap) else varSum[1] + volume * Sqr(hlc3 - vwap);
def sigma   = Sqrt(varSum / vSum);
def stretch = if sigma > 0 then (close - vwap) / sigma else 0;

plot VWAP = vwap;
VWAP.SetDefaultColor(Color.CYAN);
plot VWAPup = if showVWAPbands then vwap + kStretch * sigma else Double.NaN;
plot VWAPdn = if showVWAPbands then vwap - kStretch * sigma else Double.NaN;
VWAPup.SetDefaultColor(Color.DARK_GRAY);  VWAPup.SetStyle(Curve.SHORT_DASH);
VWAPdn.SetDefaultColor(Color.DARK_GRAY);  VWAPdn.SetStyle(Curve.SHORT_DASH);

# ---- FILTER 1: LOCATION zones (red = resistance, green = support) ----
AddCloud(z1_hi, z1_lo, if z1_resist then Color.RED else Color.GREEN,
                       if z1_resist then Color.RED else Color.GREEN);
AddCloud(z2_hi, z2_lo, if z2_resist then Color.RED else Color.GREEN,
                       if z2_resist then Color.RED else Color.GREEN);
AddCloud(z3_hi, z3_lo, if z3_resist then Color.RED else Color.GREEN,
                       if z3_resist then Color.RED else Color.GREEN);

# ---- regression channel (trailing linreg + residual sigma) ----
def regMid = Inertia(close, chanLen);
def rstd   = StDev(close - regMid, chanLen);
plot RegMid = if showChannel then regMid else Double.NaN;
plot RegUp  = if showChannel then regMid + chanDev * rstd else Double.NaN;
plot RegLo  = if showChannel then regMid - chanDev * rstd else Double.NaN;
RegMid.SetDefaultColor(Color.VIOLET);
RegUp.SetDefaultColor(Color.VIOLET);  RegUp.SetStyle(Curve.SHORT_DASH);
RegLo.SetDefaultColor(Color.VIOLET);  RegLo.SetStyle(Curve.SHORT_DASH);

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

plot FadeShort = if fadeShort then high else Double.NaN;
FadeShort.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
FadeShort.SetDefaultColor(Color.RED);
plot FadeLong = if fadeLong then low else Double.NaN;
FadeLong.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
FadeLong.SetDefaultColor(Color.GREEN);
plot BrkShort = if brkShort then low else Double.NaN;
BrkShort.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
BrkShort.SetDefaultColor(Color.MAGENTA);
plot BrkLong = if brkLong then high else Double.NaN;
BrkLong.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
BrkLong.SetDefaultColor(Color.MAGENTA);

Alert(fadeShort, "NQ FADE-short: zone tag + stretch (with trend)", Alert.BAR, Sound.Ring);
Alert(fadeLong,  "NQ FADE-long: zone tag + stretch (with trend)",  Alert.BAR, Sound.Ring);
Alert(brkShort,  "NQ BREAK-short: 30m close thru support (with trend)", Alert.BAR, Sound.Bell);
Alert(brkLong,   "NQ BREAK-long: 30m close thru resistance (with trend)", Alert.BAR, Sound.Bell);

# ---- status labels ----
AddLabel(yes, "Macro " + (if bias > 0 then "UP" else if bias < 0 then "DOWN" else "MIXED"),
         if bias < 0 then Color.RED else if bias > 0 then Color.GREEN else Color.GRAY);
AddLabel(yes, "Stretch " + Round(stretch, 1) + "s",
         if AbsValue(stretch) >= kStretch then Color.YELLOW else Color.GRAY);
AddLabel(yes, "VWAP " + Round(vwap, 0), Color.CYAN);
