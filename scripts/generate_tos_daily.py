#!/usr/bin/env python3
"""DAILY MNQ study — higher-timeframe FVG context to sit alongside the 5-min
signal chart. Emits a ready-to-paste thinkScript box.

Tested first (QQQ daily, 5 years, 1253 bars) rather than assumed:
  * daily FVG CONTINUATION (with the 20SMA trend): +0.161R/trade, 38% win,
    n=203, t=+2.95 — a real edge, on par with the 5-min version
  * daily FVG FADE: -0.244R, t=-4.38 — losing, and more conclusively than
    intraday. So the arrows are continuation-only here too.
  * daily gaps fill in a median of 4 bars but the mean is 22 (long tail), and
    a median of 22 gaps are open at once (max 50). Drawing them all would be
    unusable, so the chart tracks the 3 most recent unfilled gaps per side —
    the ones nearest the action.

Difference from the backtest, stated plainly: the test allowed an entry from
ANY open gap; thinkScript cannot hold an unbounded list, so the chart watches
the 3 most recent per side. Older gaps still matter as magnets but will not
fire an arrow.

Usage:  python3 scripts/generate_tos_daily.py [--sym MNQ] [--days 120]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.gamma_context as gc          # noqa: E402
import scripts.gex_daily_levels as gdl      # noqa: E402
from scripts.generate_tos import validate, DATE, REGIME   # noqa: E402

TEMPLATE = r"""# =====================================================================
# __SYM__ DAILY FVG context   __DATE__
#
#   Apply to a DAILY __SYM__ chart. Companion to the 5-min signal study —
#   this one is for structure: which higher-timeframe gaps are still open,
#   where the daily trend is, and where the dealer walls sit.
#
#   TESTED (QQQ daily, 5y, 1253 bars) — these are THIS chart's own numbers,
#   from simulating the exact 3-slot + first-touch logic below:
#     this chart          +0.406R/trade, 47% win, n=118, t=+3.53, +47.9R
#     unlimited open gaps +0.161R/trade, 38% win, n=203, t=+2.95, +32.8R
#     fading these gaps   -0.244R/trade, t=-4.38            <- never fade
#   Capping at 3 slots and demanding a FIRST touch (price arriving from
#   outside the gap) filters quality: fewer trades, far better each. About 24
#   signals a year — this is a slow, structural chart, not a signal machine.
#   Daily gaps fill in a median of 4 bars but average 22 (long tail), and a
#   median of 22 sit open at once, which is why only 3 per side are drawn.
#   Older gaps remain magnets but will not fire an arrow.
#
#   Entry  : price retraces into an open daily gap's near edge, WITH the
#            20SMA trend (long above / short below). First touch only.
#   Stop   : swing low/high of the last `stopLookback` daily bars.
#   Use it : as context for the 5-min chart — an intraday long into an open
#            daily bear gap overhead is fighting structure.
# =====================================================================
declare upper;

input minGapPct    = 0.03;   # min gap size as % of price (same as 5-min study)
input trendLen     = 20;     # daily trend filter (the tested one)
input stopLookback = 5;
input showFVG      = yes;
input showSignals  = yes;
input showBubbles  = yes;
input showGL       = yes;    # dealer gamma walls, per day

# ---- daily trend filter ----
plot Trend = Average(close, trendLen);
Trend.SetDefaultColor(Color.CYAN);
Trend.SetLineWeight(2);
def up = close > Trend;

# ---- 3-bar FVGs ----
def mg      = minGapPct / 100;
def newBull = low > high[2] and (low - high[2]) / close >= mg;
def newBear = high < low[2] and (low[2] - high) / close >= mg;

#   slot 1 = newest. On a new gap each slot shifts down one. A slot empties
#   when price fully fills that gap.
rec b1bot = if newBull then high[2]
            else if IsNaN(b1bot[1]) then Double.NaN
            else if low <= b1bot[1] then Double.NaN
            else b1bot[1];
rec b1top = if newBull then low
            else if IsNaN(b1bot) then Double.NaN
            else b1top[1];
rec b2bot = if newBull then b1bot[1]
            else if IsNaN(b2bot[1]) then Double.NaN
            else if low <= b2bot[1] then Double.NaN
            else b2bot[1];
rec b2top = if newBull then b1top[1]
            else if IsNaN(b2bot) then Double.NaN
            else b2top[1];
rec b3bot = if newBull then b2bot[1]
            else if IsNaN(b3bot[1]) then Double.NaN
            else if low <= b3bot[1] then Double.NaN
            else b3bot[1];
rec b3top = if newBull then b2top[1]
            else if IsNaN(b3bot) then Double.NaN
            else b3top[1];

rec r1top = if newBear then low[2]
            else if IsNaN(r1top[1]) then Double.NaN
            else if high >= r1top[1] then Double.NaN
            else r1top[1];
rec r1bot = if newBear then high
            else if IsNaN(r1top) then Double.NaN
            else r1bot[1];
rec r2top = if newBear then r1top[1]
            else if IsNaN(r2top[1]) then Double.NaN
            else if high >= r2top[1] then Double.NaN
            else r2top[1];
rec r2bot = if newBear then r1bot[1]
            else if IsNaN(r2top) then Double.NaN
            else r2bot[1];
rec r3top = if newBear then r2top[1]
            else if IsNaN(r3top[1]) then Double.NaN
            else if high >= r3top[1] then Double.NaN
            else r3top[1];
rec r3bot = if newBear then r2bot[1]
            else if IsNaN(r3top) then Double.NaN
            else r3bot[1];

plot B1t = if showFVG then b1top else Double.NaN;
plot B1b = if showFVG then b1bot else Double.NaN;
plot B2t = if showFVG then b2top else Double.NaN;
plot B2b = if showFVG then b2bot else Double.NaN;
plot B3t = if showFVG then b3top else Double.NaN;
plot B3b = if showFVG then b3bot else Double.NaN;
plot R1t = if showFVG then r1top else Double.NaN;
plot R1b = if showFVG then r1bot else Double.NaN;
plot R2t = if showFVG then r2top else Double.NaN;
plot R2b = if showFVG then r2bot else Double.NaN;
plot R3t = if showFVG then r3top else Double.NaN;
plot R3b = if showFVG then r3bot else Double.NaN;
B1t.SetDefaultColor(Color.DARK_GREEN);  B1t.SetStyle(Curve.SHORT_DASH);
B1b.SetDefaultColor(Color.DARK_GREEN);  B1b.SetStyle(Curve.SHORT_DASH);
B2t.SetDefaultColor(Color.DARK_GREEN);  B2t.SetStyle(Curve.SHORT_DASH);
B2b.SetDefaultColor(Color.DARK_GREEN);  B2b.SetStyle(Curve.SHORT_DASH);
B3t.SetDefaultColor(Color.DARK_GREEN);  B3t.SetStyle(Curve.SHORT_DASH);
B3b.SetDefaultColor(Color.DARK_GREEN);  B3b.SetStyle(Curve.SHORT_DASH);
R1t.SetDefaultColor(Color.DARK_RED);    R1t.SetStyle(Curve.SHORT_DASH);
R1b.SetDefaultColor(Color.DARK_RED);    R1b.SetStyle(Curve.SHORT_DASH);
R2t.SetDefaultColor(Color.DARK_RED);    R2t.SetStyle(Curve.SHORT_DASH);
R2b.SetDefaultColor(Color.DARK_RED);    R2b.SetStyle(Curve.SHORT_DASH);
R3t.SetDefaultColor(Color.DARK_RED);    R3t.SetStyle(Curve.SHORT_DASH);
R3b.SetDefaultColor(Color.DARK_RED);    R3b.SetStyle(Curve.SHORT_DASH);
AddCloud(B1t, B1b, Color.DARK_GREEN, Color.DARK_GREEN);
AddCloud(B2t, B2b, Color.DARK_GREEN, Color.DARK_GREEN);
AddCloud(B3t, B3b, Color.DARK_GREEN, Color.DARK_GREEN);
AddCloud(R1t, R1b, Color.DARK_RED,   Color.DARK_RED);
AddCloud(R2t, R2b, Color.DARK_RED,   Color.DARK_RED);
AddCloud(R3t, R3b, Color.DARK_RED,   Color.DARK_RED);

# ---- first touch into an open gap, with the trend ----
def bT1 = !IsNaN(b1top) and low <= b1top and low[1] > b1top;
def bT2 = !IsNaN(b2top) and low <= b2top and low[1] > b2top;
def bT3 = !IsNaN(b3top) and low <= b3top and low[1] > b3top;
def rT1 = !IsNaN(r1bot) and high >= r1bot and high[1] < r1bot;
def rT2 = !IsNaN(r2bot) and high >= r2bot and high[1] < r2bot;
def rT3 = !IsNaN(r3bot) and high >= r3bot and high[1] < r3bot;

def buySig  = showSignals and up  and (bT1 or bT2 or bT3);
def sellSig = showSignals and !up and (rT1 or rT2 or rT3);

def longStop  = Lowest(low,   stopLookback + 1);
def shortStop = Highest(high, stopLookback + 1);

plot Buy = if buySig then low else Double.NaN;
Buy.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
Buy.SetDefaultColor(Color.GREEN);  Buy.SetLineWeight(5);
plot Sell = if sellSig then high else Double.NaN;
Sell.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
Sell.SetDefaultColor(Color.RED);   Sell.SetLineWeight(5);

AddChartBubble(showBubbles and buySig, low,
    "D-FVG BUY  stop " + Round(longStop, 2), Color.GREEN, no);
AddChartBubble(showBubbles and sellSig, high,
    "D-FVG SELL  stop " + Round(shortStop, 2), Color.RED, yes);

Alert(buySig,  "Daily FVG continuation LONG",  Alert.BAR, Sound.Chimes);
Alert(sellSig, "Daily FVG continuation SHORT", Alert.BAR, Sound.Bell);

# ---- open-gap context label ----
def nBull = (if !IsNaN(b1top) then 1 else 0) + (if !IsNaN(b2top) then 1 else 0)
          + (if !IsNaN(b3top) then 1 else 0);
def nBear = (if !IsNaN(r1top) then 1 else 0) + (if !IsNaN(r2top) then 1 else 0)
          + (if !IsNaN(r3top) then 1 else 0);
AddLabel(yes, "__SYM__ daily | trend " + (if up then "UP" else "DOWN") +
    " | open gaps: " + nBull + " bull / " + nBear + " bear",
    if up then Color.GREEN else Color.RED);

# ---- DEALER GAMMA (per day, from that morning's read) ----
__GAMMALEVELS__
__DEALERREGIME__
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="MNQ")
    ap.add_argument("--days", type=int, default=120)
    a = ap.parse_args()

    native = None
    if a.sym == "MNQ":
        nq = gc.load_gamma_levels("NQ") or {}
        if "FOP" in str(nq.get("_source", "")):
            native = {t: nq[k] for k, t in (("gamma_flip", "GF"), ("call_wall", "CW"),
                                            ("put_wall", "PW")) if nq.get(k) is not None}
    mode = "absolute" if a.sym == "QQQ" else "ratio"   # only QQQ has its own chain
    try:
        blk = gdl.block(a.sym, mode, a.days, DATE, native)
    except Exception as e:                       # never ship a broken block
        blk = f"# ---- dealer gamma unavailable: {e} ----"

    regime = REGIME if "plot GFlip" in blk else \
        "# ---- dealer-regime layer omitted: no gamma levels available ----"
    s = (TEMPLATE.replace("__SYM__", a.sym)
                 .replace("__DATE__", DATE)
                 .replace("__GAMMALEVELS__", blk)
                 .replace("__DEALERREGIME__", regime))

    errs = validate(a.sym + "-daily", s)
    if errs:
        print("!!! GENERATED STUDY FAILED VALIDATION — do not paste into ToS:",
              file=sys.stderr)
        for e in errs:
            print("   " + e, file=sys.stderr)
        raise SystemExit(1)

    print(f"\n===== COPY BELOW into ThinkOrSwim — {a.sym} DAILY study ({DATE}) =====")
    print(s.rstrip())
    print(f"===== END {a.sym} DAILY study =====")


if __name__ == "__main__":
    main()
