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
import scripts.gex_daily_levels as gdl

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
#   TRADE STYLE (tested, scripts/backtest_style_by_regime.py, 250 sessions):
#   Fading instead of continuing LOSES in both regimes (neg +0.110 vs +0.163,
#   pos +0.083 vs +0.115) — so the arrows stay continuation-only. The FVG
#   entry is already a pullback, not a breakout chase, which is why it holds
#   up when dealers dampen. What the regime changes is the EXIT: ride-it
#   exits decay hard in positive gamma (vwapCross +0.252 neg -> +0.009 pos),
#   while a fixed 2R is regime-neutral (+0.202 / +0.222). So autoTarget banks
#   2R in positive gamma and gives 3R + the trail room in negative gamma.
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
input targetR       = 3.0;    # manual target in R (used if autoTarget = no)
input autoTarget    = yes;    # pick the target from the gamma regime (see header)
input posGammaToday = __POSGAMMA__;   # baked from this morning's options read
input posTargetR    = 2.0;    # POSITIVE gamma: moves stall -> bank a fixed 2R
input negTargetR    = 3.0;    # NEGATIVE gamma: moves extend -> give it room
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

# ---- style by regime: direction stays CONTINUATION, only the EXIT changes ----
#   Measured (250 sessions): continuation beat fading in BOTH regimes, so the
#   arrows never flip. What DOES change with regime is how far a winner runs —
#   ride-it exits decay badly in positive gamma while a fixed 2R holds up.
def tgtR = if !autoTarget then targetR else if posGammaToday then posTargetR else negTargetR;

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
              else if !IsNaN(Lentry) then Lentry + tgtR * Lrisk
              else if !IsNaN(Sentry) then Sentry - tgtR * Srisk else Double.NaN;
Target.SetDefaultColor(Color.LIGHT_GRAY);  Target.SetStyle(Curve.SHORT_DASH);

def exitNow = (IsNaN(Lstop) and !IsNaN(Lstop[1])) or (IsNaN(Sstop) and !IsNaN(Sstop[1]));
plot ExitX = if showExits and exitNow then close else Double.NaN;
ExitX.SetPaintingStrategy(PaintingStrategy.POINTS);
ExitX.SetDefaultColor(Color.YELLOW);  ExitX.SetLineWeight(4);

# ---- DEALER GAMMA (walls = how far price can travel) ----
__GAMMALEVELS__
__DEALERREGIME__

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
AddLabel(yes, "__SYM__ FVG continuation | " +
    (if posGammaToday then "POS gamma: moves stall -> bank " + posTargetR + "R"
                      else "NEG gamma: moves extend -> ride the trail") +
    (if skipFirstHour then " | skip 09:30-10:30" else "") +
    (if maxStopATR > 0 then " | maxStop " + maxStopATR + "xATR" else ""),
    if posGammaToday then Color.LIGHT_GRAY else Color.YELLOW);
__EARNLABEL__
"""

# Live dealer-positioning read, injected after the wall plots (which define
# GFlip / CWall / PWall). Only included when those plots actually exist.
REGIME = r"""
# ---- DEALER-POSITIONING REGIME (live, read off the flip line) ----
#   Which side of the gamma flip price sits on IS the dealer regime, live and
#   bar by bar:
#     ABOVE flip = long / POSITIVE gamma -> dealers dampen -> RANGE day: moves
#                  stall, the walls tend to HOLD. Bank targets into a wall,
#                  don't chase; a fixed 2R beats a runner here.
#     BELOW flip = short / NEGATIVE gamma -> dealers amplify -> TREND day: moves
#                  extend, the walls tend to BREAK. Let winners run, don't fade.
#   VALIDATED as a range / target / sizing read (negative-gamma next-day
#   expansion, t=5.72). It does NOT flip the setup direction -- continuation
#   beat fading in BOTH regimes -- so there are NO fade arrows here. This tells
#   you how FAR to expect price to travel and where to bank, not which way to bet.
input showRegime = yes;
def haveFlip   = showRegime and !IsNaN(GFlip);
def longGamma  = haveFlip and close > GFlip;    # positive-gamma regime
def shortGamma = haveFlip and close < GFlip;    # negative-gamma regime

# 1) the flip line itself carries the live regime: GREEN while we sit in long
#    gamma above it, RED once price drops into short gamma below it. The colour
#    flipping at the line IS the regime change -- no extra dots needed.
GFlip.AssignValueColor(if !haveFlip then Color.WHITE
                       else if longGamma then Color.GREEN else Color.RED);

# 2) wall reaction, read THROUGH the regime (first touch only, so it's rare):
def hitCall = haveFlip and !IsNaN(CWall) and high >= CWall and high[1] < CWall;
def hitPut  = haveFlip and !IsNaN(PWall) and low  <= PWall and low[1]  > PWall;
AddChartBubble(hitCall, high,
    (if longGamma then "CALL wall + long gamma: likely CAP -> bank longs, fade back inside"
                  else "CALL wall + short gamma: BREAK risk -> don't fade, ride through"),
    (if longGamma then Color.RED else Color.YELLOW), yes);
AddChartBubble(hitPut, low,
    (if longGamma then "PUT wall + long gamma: likely FLOOR -> bank shorts, expect bounce"
                  else "PUT wall + short gamma: BREAK risk -> don't fade, ride through"),
    (if longGamma then Color.GREEN else Color.YELLOW), no);

# 3) one LIVE regime label (moves with price, unlike the baked chain read above)
AddLabel(haveFlip,
    "DEALER REGIME NOW: " +
    (if longGamma  then "LONG gamma (above flip) -> range, walls hold, bank targets"
     else if shortGamma then "SHORT gamma (below flip) -> trend, walls break, let it run"
     else "at the flip -> transition, wait for a side"),
    (if longGamma then Color.GREEN else if shortGamma then Color.RED else Color.GRAY));"""


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



def validate(sym: str, script: str) -> list[str]:
    """Catch the thinkScript errors we cannot compile-test here.

    1. duplicate identifiers  -> "Identifier Already Used" (this shipped once,
       when a generated block re-declared an input the template already had)
    2. forward references     -> thinkScript needs declaration before use
    3. unresolved __PLACEHOLDER__ markers
    """
    import re
    problems = []
    body = [ln.split("#")[0] for ln in script.split("\n")]

    seen = {}
    for n, ln in enumerate(body):
        m = re.match(r"\s*(rec|def|plot|input)\s+([A-Za-z_][A-Za-z0-9_]*)", ln)
        if not m:
            continue
        name = m.group(2)
        if name in seen:
            problems.append(f"{sym}: duplicate identifier '{name}' "
                            f"(lines {seen[name]+1} and {n+1})")
        else:
            seen[name] = n

    for n, ln in enumerate(body):
        m = re.match(r"\s*(rec|def|plot|input)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)", ln)
        if not m:
            continue
        expr, j = m.group(3), n + 1
        while j < len(body) and body[j].strip() and not re.match(
                r"\s*(rec|def|plot|input|AddCloud|AddLabel|AddChartBubble|Alert|[A-Za-z_]+\.)",
                body[j]):
            expr += " " + body[j]; j += 1
        for name, dn in seen.items():
            if name != m.group(2) and dn > n and re.search(r"\b" + re.escape(name) + r"\b", expr):
                problems.append(f"{sym}: '{m.group(2)}' (line {n+1}) uses '{name}' "
                                f"declared later (line {dn+1})")

    for ph in sorted(set(re.findall(r"__[A-Z0-9]+__", script))):
        problems.append(f"{sym}: unresolved placeholder {ph}")
    return problems


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
        # PER-DAY gamma levels: each session shows the walls from the prior
        # session's chain (what was known pre-market). Falls back to the single
        # flat read for symbols with no option history.
        # QQQ chain drives every instrument. QQQ = absolute (its own price);
        # MNQ/MES/SPY = ratio (dimensionless wall/QQQ-spot x that instrument's
        # own prior daily close). MNQ is genuinely Nasdaq so the scaling is
        # clean; SPY/MES are S&P, so their scaled walls are ROUGH index-proxy
        # levels (they inherit QQQ's Nasdaq skew) until a native SPY chain is
        # available. Flagged on-chart in the block's own comments.
        _mode = {"MNQ": "ratio", "MES": "ratio", "QQQ": "absolute", "SPY": "ratio"}.get(sym)
        _KT = (("gamma_flip", "GF"), ("call_wall", "CW"), ("put_wall", "PW"))
        _native = None                                     # today's absolute walls, native read
        if sym == "MNQ":
            _nq = gc.load_gamma_levels("NQ") or {}
            if "FOP" in str(_nq.get("_source", "")):      # native /NQ read beats scaling
                _native = {t: _nq[k] for k, t in _KT if _nq.get(k) is not None}
        elif sym == "SPY":
            _spy = gc.load_gamma_levels("SPY") or {}
            if "AlphaVantage" in str(_spy.get("_source", "")):   # native SPY chain
                _native = {t: _spy[k] for k, t in _KT if _spy.get(k) is not None}
        elif sym == "MES":                                 # scale the NATIVE SPY read
            _spy = gc.load_gamma_levels("SPY") or {}       # (S&P underlying) to MES points
            _sp = _spy.get("spot")
            if "AlphaVantage" in str(_spy.get("_source", "")) and _sp:
                _native = {t: round(_spy[k] / _sp * px, 2) for k, t in _KT
                           if _spy.get(k) is not None}
        _blk = ""
        if sym in ("MNQ", "QQQ", "MES", "SPY"):           # QQQ chain drives the history
            try:
                _blk = gdl.block(sym, _mode, 120, DATE, _native)
                if sym in ("MES", "SPY") and _blk:         # provenance note
                    tag = ("today's walls = NATIVE S&P (SPY option chain); "
                           if _native else "")
                    _blk = (f"# NOTE: {tag}sessions BEFORE today are the QQQ "
                            "(Nasdaq) chain\n#   scaled onto this S&P instrument -- "
                            "rough proxies that inherit QQQ's skew, until an S&P\n"
                            "#   option history accumulates. Use older walls for "
                            "context, not to the tick.\n") + _blk
            except Exception:
                _blk = ""
        _gamma_txt = _blk or gamma_block(ctx.get("gamma_levels"), d)
        s = s.replace("__GAMMALEVELS__", _gamma_txt)
        # live dealer-regime layer only when the flip/wall plots actually exist
        s = s.replace("__DEALERREGIME__",
                      REGIME if "plot GFlip" in _gamma_txt else
                      "# ---- dealer-regime layer omitted: no gamma levels available ----")
        # regime for the auto-target: net GEX sign if we have it, else spot vs flip
        _gl = ctx.get("gamma_levels") or {}
        if _gl.get("net_gex") is not None:
            _pos = _gl["net_gex"] > 0
        elif _gl.get("gamma_flip") is not None:
            _pos = px > _gl["gamma_flip"]
        else:
            _pos = True          # no read -> assume dampened, bank the fixed target
        s = s.replace("__POSGAMMA__", "yes" if _pos else "no")
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
        errs = validate(sym, s)
        if errs:
            print("!!! GENERATED STUDY FAILED VALIDATION — do not paste into ToS:",
                  file=sys.stderr)
            for e in errs:
                print("   " + e, file=sys.stderr)
            raise SystemExit(1)
        print(f"\n===== COPY BELOW into ThinkOrSwim — {sym} study ({len(az)} zones, {DATE}) =====")
        print(s.rstrip())
        print(f"===== END {sym} study =====")


if __name__ == "__main__":
    main()
