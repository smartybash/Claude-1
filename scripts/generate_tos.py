"""Generate a COMPLETE, ready-to-paste thinkScript for each instrument
(MNQ, QQQ, MES, SPY) with that symbol's confluence zones baked in.
Standard rerun step: refresh data, run, and COPY EACH BOX PRINTED TO STDOUT
straight into ThinkOrSwim (Studies > Create). No files are written — the
scripts appear inline in the terminal/chat, delimited by clear markers.

The "live price" for each symbol is taken from the last close in that
symbol's 30-min file, so a data refresh is the only thing needed to keep the
zones and price anchored to the latest bar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.backtest_confluence as bt
import scripts.gamma_context as gc

DATE = __import__("datetime").date.today().isoformat()
INST = [   # (symbol label, 30-min file, is_futures) — price derived from data
    ("MNQ", "nq_30min_eth.json", True),
    ("QQQ", "qqq_30m_live.json", False),
    ("MES", "es_30m_live.json",  True),
    ("SPY", "spy_30m_live.json", False),
]

TEMPLATE = r"""# =====================================================================
# __SYM__ FVG Continuation (ThinkOrSwim)   __DATE__      price __PX__
#
#   Apply to a 5-MIN __SYM__ chart. This is the exact rule set backtested in
#   scripts/backtest_tos_fvg.py on 273 QQQ sessions (2025-07..2026-07):
#
#     entry        3-bar FVG -> price retraces to the gap's NEAR EDGE, taken
#                  only WITH session VWAP (long above / short below), one per gap
#     stop         structure: swing low/high of the last `stopLookback` bars
#     risk filter  skip signals whose stop is wider than `maxStopATR` x ATR
#     skip         09:30-10:30 ET (worst window out-of-sample)
#     exit         3R target, or trail the prior bar's swing (both plotted)
#
#   MEASURED (chart logic, maxStopATR 2.5): fixed 3R = +0.190R/trade over 479
#   trades, +91R total. Trailing the swing = +0.162R with the steadiest curve
#   (t 5.8). Tighter cap raises mean R but halves the trade count.
#   Works in BOTH gamma regimes (neg +0.274R / pos +0.234R) — the walls tell
#   you how far price travels, not whether the setup is valid.
#
#   Deliberately minimal: VWAP, the FVGs, buy/sell arrows, live stop/target,
#   and the dealer-gamma lines. Zones + expected-move are OFF by default.
#   Paste the WHOLE box.
# =====================================================================
declare upper;

# ---- the tested setup (values chosen from the backtest, not taste) ----
input minGapPct     = 0.03;   # min FVG size as % of price
input stopLookback  = 5;      # structure stop = swing of last N bars
input atrLen        = 14;
input maxStopATR    = 2.5;    # skip wide-stop signals (0 = no filter)
input targetR       = 3.0;    # plotted target, in R
input skipFirstHour = yes;    # no entries 09:30-10:30 ET
input rthVWAPonly   = yes;    # anchor VWAP to 09:30 RTH (matches the backtest)

# ---- what to draw ----
input showFVG     = yes;
input showSignals = yes;
input showExits   = yes;      # live stop + target while a signal is running
input showBubbles = yes;
input showGL      = yes;      # dealer gamma: flip + call/put walls
input showZones   = no;       # confluence zones (off = clean chart)
input showEM      = no;       # expected-move band (off = clean chart)

# ---- session VWAP (the direction filter) ----
def inRTH   = SecondsFromTime(0930) >= 0 and SecondsTillTime(1600) > 0;
def newSess = if rthVWAPonly then (inRTH and !inRTH[1]) else (GetDay() != GetDay()[1]);
def acc     = if rthVWAPonly then inRTH else yes;
def vSum    = if newSess then volume else if acc then vSum[1] + volume else vSum[1];
def pvSum   = if newSess then volume * hlc3 else if acc then pvSum[1] + volume * hlc3 else pvSum[1];
def vwapVal = if vSum > 0 then pvSum / vSum else close;
plot SessVWAP = vwapVal;
SessVWAP.SetDefaultColor(Color.CYAN);
SessVWAP.SetLineWeight(2);

# ---- FAIR VALUE GAPS (3-bar, same definition as the backtest) ----
def mg      = minGapPct / 100;
def newBull = low > high[2] and (low - high[2]) / close >= mg;
def newBear = high < low[2] and (low[2] - high) / close >= mg;

#   only the most recent gap each side stays live; it dies when price fills it.
#   (this is what the backtest measured — it beats tracking every open gap)
rec bBot = if newBull then high[2]
           else if IsNaN(bBot[1]) then Double.NaN
           else if low <= bBot[1] then Double.NaN
           else bBot[1];
rec bTop = if newBull then low
           else if IsNaN(bBot[1]) then Double.NaN
           else if low <= bBot[1] then Double.NaN
           else bTop[1];
rec rTop = if newBear then low[2]
           else if IsNaN(rTop[1]) then Double.NaN
           else if high >= rTop[1] then Double.NaN
           else rTop[1];
rec rBot = if newBear then high
           else if IsNaN(rTop[1]) then Double.NaN
           else if high >= rTop[1] then Double.NaN
           else rBot[1];

plot BullTop = if showFVG then bTop else Double.NaN;
plot BullBot = if showFVG then bBot else Double.NaN;
plot BearTop = if showFVG then rTop else Double.NaN;
plot BearBot = if showFVG then rBot else Double.NaN;
BullTop.SetDefaultColor(Color.DARK_GREEN);  BullTop.SetStyle(Curve.SHORT_DASH);
BullBot.SetDefaultColor(Color.DARK_GREEN);  BullBot.SetStyle(Curve.SHORT_DASH);
BearTop.SetDefaultColor(Color.DARK_RED);    BearTop.SetStyle(Curve.SHORT_DASH);
BearBot.SetDefaultColor(Color.DARK_RED);    BearBot.SetStyle(Curve.SHORT_DASH);
AddCloud(BullTop, BullBot, Color.DARK_GREEN, Color.DARK_GREEN);
AddCloud(BearTop, BearBot, Color.DARK_RED,   Color.DARK_RED);

# ---- structure stop + ATR risk filter ----
def atrVal    = Average(TrueRange(high, close, low), atrLen);
def longStop  = Lowest(low,   stopLookback + 1);
def shortStop = Highest(high, stopLookback + 1);
def longRiskOK  = maxStopATR <= 0 or (bTop - longStop)  <= maxStopATR * atrVal;
def shortRiskOK = maxStopATR <= 0 or (shortStop - rBot) <= maxStopATR * atrVal;

# ---- entry trigger: retrace into the gap edge, WITH vwap ----
def timeOK    = if skipFirstHour then SecondsFromTime(1030) >= 0 else yes;
def bullTouch = !IsNaN(bTop) and !newBull and low <= bTop and close > vwapVal;
def bearTouch = !IsNaN(rBot) and !newBear and high >= rBot and close < vwapVal;

#   a touch consumes the gap even if the risk filter vetoes the trade
rec bUsed = if newBull then 0
            else if IsNaN(bTop) then 0
            else if bullTouch and timeOK and bUsed[1] == 0 then 1
            else bUsed[1];
rec rUsed = if newBear then 0
            else if IsNaN(rBot) then 0
            else if bearTouch and timeOK and rUsed[1] == 0 then 1
            else rUsed[1];

def buySig  = showSignals and bullTouch and timeOK and bUsed[1] == 0 and longRiskOK;
def sellSig = showSignals and bearTouch and timeOK and rUsed[1] == 0 and shortRiskOK;

# ---- BUY / SELL markers ----
plot Buy = if buySig then low else Double.NaN;
Buy.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
Buy.SetDefaultColor(Color.GREEN);   Buy.SetLineWeight(5);
plot Sell = if sellSig then high else Double.NaN;
Sell.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
Sell.SetDefaultColor(Color.RED);    Sell.SetLineWeight(5);

AddChartBubble(showBubbles and buySig, low,
    "BUY " + Round(bTop, 2) + "  stop " + Round(longStop, 2), Color.GREEN, no);
AddChartBubble(showBubbles and sellSig, high,
    "SELL " + Round(rBot, 2) + "  stop " + Round(shortStop, 2), Color.RED, yes);

Alert(buySig,  "FVG continuation LONG",  Alert.BAR, Sound.Chimes);
Alert(sellSig, "FVG continuation SHORT", Alert.BAR, Sound.Bell);

# ---- live trade management: trailing stop + R target ----
#   Two self-contained state machines (long / short) so every `rec` only
#   references itself or something declared above it — thinkScript requires
#   declaration before use. The TRAIL is the exit rule (best t-stat, +0.162R);
#   the target line is the 3R reference. Trail updates, then tests, exactly
#   like the backtest: ts = max(ts, low[-1]); exit if low <= ts.
rec Lstop = if buySig then longStop
            else if IsNaN(Lstop[1]) then Double.NaN
            else if low <= Max(Lstop[1], low[1]) then Double.NaN
            else Max(Lstop[1], low[1]);
rec Lentry = if buySig then bTop
             else if IsNaN(Lstop) then Double.NaN else Lentry[1];
rec Lrisk  = if buySig then bTop - longStop
             else if IsNaN(Lstop) then Double.NaN else Lrisk[1];

rec Sstop = if sellSig then shortStop
            else if IsNaN(Sstop[1]) then Double.NaN
            else if high >= Min(Sstop[1], high[1]) then Double.NaN
            else Min(Sstop[1], high[1]);
rec Sentry = if sellSig then rBot
             else if IsNaN(Sstop) then Double.NaN else Sentry[1];
rec Srisk  = if sellSig then shortStop - rBot
             else if IsNaN(Sstop) then Double.NaN else Srisk[1];

plot TrailStop = if !showExits then Double.NaN
                 else if !IsNaN(Lstop) then Lstop
                 else if !IsNaN(Sstop) then Sstop else Double.NaN;
TrailStop.SetDefaultColor(Color.ORANGE);  TrailStop.SetStyle(Curve.SHORT_DASH);
TrailStop.SetLineWeight(2);

plot Target = if !showExits then Double.NaN
              else if !IsNaN(Lentry) then Lentry + targetR * Lrisk
              else if !IsNaN(Sentry) then Sentry - targetR * Srisk else Double.NaN;
Target.SetDefaultColor(Color.LIGHT_GRAY);  Target.SetStyle(Curve.SHORT_DASH);

def exitNow = (IsNaN(Lstop) and !IsNaN(Lstop[1])) or (IsNaN(Sstop) and !IsNaN(Sstop[1]));
plot ExitX = if showExits and exitNow then close else Double.NaN;
ExitX.SetPaintingStrategy(PaintingStrategy.POINTS);
ExitX.SetDefaultColor(Color.YELLOW);  ExitX.SetLineWeight(4);

# ---- DEALER GAMMA (walls = how far price can travel) ----
__GAMMALEVELS__

# ---- confluence zones (optional, default OFF) ----
input z1_hi = __Z1HI__;  input z1_lo = __Z1LO__;  input z1_resist = __Z1R__;
input z2_hi = __Z2HI__;  input z2_lo = __Z2LO__;  input z2_resist = __Z2R__;
AddCloud(if showZones then z1_hi else Double.NaN, if showZones then z1_lo else Double.NaN,
         if z1_resist then Color.RED else Color.GREEN, if z1_resist then Color.RED else Color.GREEN);
AddCloud(if showZones then z2_hi else Double.NaN, if showZones then z2_lo else Double.NaN,
         if z2_resist then Color.RED else Color.GREEN, if z2_resist then Color.RED else Color.GREEN);

# ---- expected move (optional, default OFF) ----
input emUpV = __EMUP__;   input emDnV = __EMDN__;
plot EMup = if showEM then emUpV else Double.NaN;
plot EMdn = if showEM then emDnV else Double.NaN;
EMup.SetDefaultColor(Color.YELLOW);  EMup.SetStyle(Curve.LONG_DASH);
EMdn.SetDefaultColor(Color.YELLOW);  EMdn.SetStyle(Curve.LONG_DASH);

# ---- one status label ----
AddLabel(yes, "__SYM__ FVG cont | __REGIME__ | " +
    (if skipFirstHour then "skip 09:30-10:30" else "all session") +
    (if maxStopATR > 0 then " | maxStop " + maxStopATR + "xATR" else ""), Color.__GCOLOR__);
__EARNLABEL__
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
    # Validity = >=2 distinct sources (the refined-filter rule: lone levels held
    # 64% vs 94% for >=2), same bar the confluence A+ map uses. Take the NEAREST
    # 2 valid zones ABOVE and 2 BELOW price so the box always carries the live
    # overhead resistance AND underlying support (not just whichever side has the
    # heaviest structure). 5% window.
    valid = [z for z in zs if z["nt"] >= 2 and abs(z["price"] - px) <= 0.05 * px]
    above = sorted([z for z in valid if z["price"] > px], key=lambda z: z["price"] - px)[:2]
    below = sorted([z for z in valid if z["price"] <= px], key=lambda z: px - z["price"])[:2]
    az = above + below
    # if one side is empty, backfill from the other so all 4 slots stay useful
    extra = sorted([z for z in valid if z not in az], key=lambda z: abs(z["price"] - px))
    az += extra[: max(0, 4 - len(az))]
    az.sort(key=lambda z: z["price"], reverse=True)
    while len(az) < 4 and az:          # pad to 4 valid inputs with the farthest zone
        az.append(az[-1])
    return az


def gamma_block(gl, d) -> str:
    """thinkScript block plotting dealer-gamma levels (from WealthCharts), or a
    placeholder comment when none are loaded for this symbol."""
    if not gl:
        return ("# ---- DEALER GAMMA LEVELS: none loaded ----\n"
                "#   Fill data/gamma_levels.json from WealthCharts to plot "
                "gamma-flip / call-wall / put-wall here.")
    spec = [("gamma_flip", "GFlip", "GammaFlip", "Color.WHITE", "Curve.FIRM", 2),
            ("call_wall",  "CWall", "CallWall",  "Color.RED",   "Curve.LONG_DASH", 3),
            ("put_wall",   "PWall", "PutWall",   "Color.GREEN", "Curve.LONG_DASH", 3),
            ("zero_gamma", "ZGam",  "ZeroGamma", "Color.GRAY",  "Curve.SHORT_DASH", 1)]
    # NOTE: showGL is declared once in the study's input block, not here.
    lines = [f"#   source: {gl.get('_source','provider')} {gl.get('_date','')}"]
    for key, plotn, lab, col, style, lw in spec:
        if key not in gl:
            continue
        # zero_gamma is the same number as gamma_flip in our reads — don't draw
        # a second line on top of the first.
        if key == "zero_gamma" and gl.get("gamma_flip") == gl[key]:
            continue
        v = f"{gl[key]:.{d}f}"
        lines.append(f"input {plotn}lvl = {v};")
        lines.append(f"plot {plotn} = if showGL then {plotn}lvl else Double.NaN;")
        lines.append(f"{plotn}.SetDefaultColor({col});  {plotn}.SetStyle({style});  {plotn}.SetLineWeight({lw});")
    return "\n".join(lines)


def main():
    GCOLOR = {"VOL-CALM": "GREEN", "VOL-STRESSED": "ORANGE", "VOL-NEUTRAL": "GRAY"}
    for sym, fname, fut in INST:
        px = float(load_any(fname)["close"].iloc[-1])  # live price = last cached close
        d = 2 if px < 2000 else 1
        az = zones_for(fname, fut, px)
        ctx = gc.context(px, sym)
        s = TEMPLATE.replace("__SYM__", sym).replace("__DATE__", DATE).replace("__PX__", f"{px:.{d}f}")
        s = (s.replace("__EMUP__", f"{ctx['up']:.{d}f}").replace("__EMDN__", f"{ctx['dn']:.{d}f}")
              .replace("__EMADJ__", f"{ctx['em_adj']:.{d}f}").replace("__EMMULT__", f"{ctx['em_mult']:.2f}")
              .replace("__PIN__", f"{ctx['pin']:.{d}f}")
              .replace("__REGIME__", ctx["regime"]).replace("__GCOLOR__", GCOLOR[ctx["regime"]]))
        s = s.replace("__GAMMALEVELS__", gamma_block(ctx.get("gamma_levels"), d))
        earn = (f'AddLabel(showGamma, "EARNINGS NIGHT (x{ctx["earn_mult"]:.2f})", Color.MAGENTA);'
                if ctx.get("earn_mult", 1.0) != 1.0 else "")
        s = s.replace("__EARNLABEL__", earn)
        for i, z in enumerate(az, 1):
            res = "yes" if z["price"] > px else "no"
            s = (s.replace(f"__Z{i}HI__", f"{z['hi']:.{d}f}")
                  .replace(f"__Z{i}LO__", f"{z['lo']:.{d}f}")
                  .replace(f"__Z{i}R__", res))
        # Emit as a copy-paste box to stdout (no file). Delimiters make it easy
        # to select the whole study for each instrument.
        print(f"\n===== COPY BELOW into ThinkOrSwim — {sym} study ({len(az)} zones, {DATE}) =====")
        print(s.rstrip())
        print(f"===== END {sym} study =====")


if __name__ == "__main__":
    main()
