#!/usr/bin/env python3
"""CHOP-ZONE (range-compression) BREAKOUT study — a DAILY MNQ chart.

Motivation (user, 2026-08-13): the fade-at-the-call-wall failed. Price had
compressed on a daily basis for several days, then broke out and RAN. Fading
the edge was the wrong trade; the edge was the break of the multi-day range.
This chart trades that mechanically, both sides.

TESTED (QQQ daily, 5y, backtest_range_breakout.py) — these are THIS chart's
own rule, not a proxy. thinkScript cannot compute a rolling quantile, so the
compression test the chart ships is box height <= k*ATR(14). The daily
backtest proves that ATR rule keeps the edge:

    N=5, box<=2.0*ATR   n=252   3R exit +0.362R/trade  t=3.04   (measured +0.190R)
    N=5, box<=2.5*ATR   n=424   3R exit +0.254R/trade  t=2.83

  False-breakout rate ~55% (price closes back inside the box within 3 days).
  That is the whole character of the trade: you are WRONG more than half the
  time, but the winners run 3x the risk. It is the OPPOSITE psychology to the
  fade — small frequent losses, occasional large win. If you cannot sit through
  a 55% miss rate, do not trade this.

  Compression does NOT predict expansion (compressed next-day range 1.64% vs
  1.93% normal, Welch t=-4.99). The tight box is not a "coiled spring" — it is
  only a place to put a clean stop. The BREAK is the trigger, nothing else.

GAMMA SQUEEZE — read this before trusting the squeeze label:
  The theory is that a breakout in NEGATIVE gamma / through a wall forces
  dealers to chase and the move accelerates. Our data does NOT confirm it. On
  the 53 breakouts with a prior option read, negative-gamma breakouts made
  -0.09R while positive-gamma ones made +0.16R — the wrong way, on a sample
  far too small to trust either direction. So the chart draws the squeeze
  CONDITION as a neutral context label, NOT a buy signal. Take the break on
  its own merits; let the gamma note inform size, not entry.

Entry  : today breaks beyond a compressed N-day box (long above / short below).
Stop   : the opposite side of the box (risk = box height).
Targets: measured move (1x box height) and 3R (the tested runner).
Use it : as the higher-timeframe range trade to sit alongside the 5-min FVG
         chart and the daily FVG context chart.

Usage:  python3 scripts/generate_tos_breakout.py [--sym MNQ] [--days 120]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.gamma_context as gc          # noqa: E402
import scripts.gex_daily_levels as gdl      # noqa: E402
from scripts.generate_tos import validate, DATE   # noqa: E402

TEMPLATE = r"""# =====================================================================
# __SYM__ CHOP-ZONE BREAKOUT   __DATE__
#
#   Apply to a DAILY __SYM__ chart. Mechanical both-side breakout of a
#   compressed multi-day range — the trade for the day a coiled range finally
#   lets go, when fading the edge is the losing side.
#
#   TESTED (QQQ daily, 5y) — THIS chart's exact rule (box <= k*ATR), from
#   backtest_range_breakout.py:
#     N=5, box<=2.0*ATR   n=252   3R exit +0.362R/trade  t=3.04
#     measured move (1x box)      +0.190R/trade
#   False-breakout rate ~55%: you are wrong more often than right, but winners
#   run 3x risk. Small frequent losses, occasional big win. Do NOT trade this
#   if you cannot sit through a >50% miss rate.
#
#   DIRECTION MATTERS (tested, QQQ daily 5y): the edge is long-biased.
#     LONG break  n=140  3R +0.807R (t 4.79)  -> LET IT RUN to 3R
#     SHORT break n=127  3R -0.195R (t -1.37) but measured +0.172R (t 1.97)
#       -> shorts only reach the 1x-box pop then get bought back; TAKE MEASURED,
#          do not hold a short for 3R. (Caveat: 5y of a bull tape, so the long
#          bias is partly drift; treat shorts as lower-conviction on NQ too.)
#     A failed poke on one side does NOT make the other side's break stronger
#     (primed +0.24R vs un-primed +0.36R) — that filter was tested and dropped.
#
#   NOTE the box does not predict the break (compression does NOT forecast
#   expansion, t=-4.99). The tight range is only a clean place for a stop; the
#   BREAK is the trigger. And the "gamma squeeze" label below is UNVALIDATED
#   (n=53, pointed the wrong way) — context for sizing, never an entry.
#
#   Entry  : today trades beyond a compressed N-day box.
#   Stop   : the opposite side of the box (risk = box height).
#   Target : measured move (1x box) and 3R (the tested runner).
# =====================================================================
declare upper;

input boxLen    = 5;     # N-day range (tested)
input atrLen    = 14;
input atrK      = 2.0;   # box counts as "compressed" if height <= atrK * ATR
input showBox   = yes;
input showSignals = yes;
input showBubbles = yes;
input showTargets = yes;
input showGL      = yes;  # dealer gamma walls, per day

# ---- the N-day box, from the PRIOR bars only (no lookahead) ----
def boxHi = Highest(high[1], boxLen);
def boxLo = Lowest(low[1], boxLen);
def boxH  = boxHi - boxLo;
def a     = ATR(length = atrLen);
def compressed = boxH > 0 and boxH <= atrK * a;

plot BoxHi = if showBox and compressed then boxHi else Double.NaN;
plot BoxLo = if showBox and compressed then boxLo else Double.NaN;
BoxHi.SetDefaultColor(Color.GRAY);  BoxHi.SetStyle(Curve.SHORT_DASH);  BoxHi.SetLineWeight(2);
BoxLo.SetDefaultColor(Color.GRAY);  BoxLo.SetStyle(Curve.SHORT_DASH);  BoxLo.SetLineWeight(2);
AddCloud(BoxHi, BoxLo, Color.DARK_GRAY, Color.DARK_GRAY);

# ---- the break ----
def brkUp = compressed and high > boxHi;
def brkDn = compressed and low  < boxLo;
def buySig  = showSignals and brkUp;
def sellSig = showSignals and brkDn;

# entry at the box edge, stop the far side, risk = box height
def entryL = boxHi;   def stopL = boxLo;
def entryS = boxLo;   def stopS = boxHi;

plot Buy = if buySig then boxHi else Double.NaN;
Buy.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_UP);
Buy.SetDefaultColor(Color.GREEN);  Buy.SetLineWeight(5);
plot Sell = if sellSig then boxLo else Double.NaN;
Sell.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
Sell.SetDefaultColor(Color.RED);   Sell.SetLineWeight(5);

# ---- targets & stop, held from the breakout bar ----
def dir = if buySig then 1 else if sellSig then -1 else dir[1];
def rk  = if buySig then boxH else if sellSig then boxH else rk[1];
def ent = if buySig then entryL else if sellSig then entryS else ent[1];
def stp = if buySig then stopL  else if sellSig then stopS  else stp[1];
def tMeas = if dir > 0 then ent + boxH else if dir < 0 then ent - boxH else Double.NaN;
def t3R   = if dir > 0 then ent + 3 * rk else if dir < 0 then ent - 3 * rk else Double.NaN;

plot Stop  = if showTargets and !IsNaN(dir) then stp   else Double.NaN;
plot TMeas = if showTargets and !IsNaN(dir) then tMeas else Double.NaN;
plot T3R   = if showTargets and !IsNaN(dir) then t3R   else Double.NaN;
Stop.SetDefaultColor(Color.RED);      Stop.SetStyle(Curve.LONG_DASH);
TMeas.SetDefaultColor(Color.YELLOW);  TMeas.SetStyle(Curve.SHORT_DASH);
T3R.SetDefaultColor(Color.CYAN);      T3R.SetStyle(Curve.SHORT_DASH);

# Direction-aware exit (tested): LONG breakouts RUN (3R, +0.81R); SHORT
# breakouts only reach the measured move then get bought back (3R loses -0.20R,
# measured +0.17R). So long -> hold for 3R, short -> take the 1x-box pop.
AddChartBubble(showBubbles and buySig, boxHi,
    "BREAKOUT LONG  stop " + Round(stopL, 2) + "  LET RUN -> 3R " + Round(boxHi + 3 * boxH, 2),
    Color.GREEN, no);
AddChartBubble(showBubbles and sellSig, boxLo,
    "BREAKOUT SHORT  stop " + Round(stopS, 2) + "  TAKE MEAS " + Round(boxLo - boxH, 2)
        + " (don't hold for 3R)",
    Color.RED, yes);

Alert(buySig,  "Chop-zone breakout LONG",  Alert.BAR, Sound.Chimes);
Alert(sellSig, "Chop-zone breakout SHORT", Alert.BAR, Sound.Bell);

# ---- state label: are we in a chop zone right now? ----
AddLabel(yes,
    (if compressed then "COMPRESSED box " + Round(boxLo, 2) + " - " + Round(boxHi, 2)
        + " (H " + Round(boxH, 2) + " <= " + atrK + "xATR)"
     else "no compression"),
    if compressed then Color.YELLOW else Color.GRAY);
AddLabel(yes, "false-breakout ~55% : winners run 3x, expect to be wrong > half",
    Color.GRAY);
AddLabel(yes, "LONG break -> let run to 3R  |  SHORT break -> take measured move "
    + "(shorts don't hold to 3R)", Color.LIGHT_GRAY);

# ---- DEALER GAMMA (per day, from that morning's read) ----
__GAMMALEVELS__
__SQUEEZE__
"""

SQUEEZE = r"""
# ---- GAMMA-SQUEEZE CONTEXT (UNVALIDATED — not a signal) ----
#   A break in negative gamma / punching through a wall is the classic squeeze.
#   Our data (n=53) did NOT confirm it and pointed the wrong way, so this is a
#   neutral context flag for SIZING, never an entry trigger.
def thruCall = buySig  and showGL and !IsNaN(CWall) and boxHi < CWall and high >= CWall;
def thruPut  = sellSig and showGL and !IsNaN(PWall) and boxLo > PWall and low  <= PWall;
def belowFlip = showGL and !IsNaN(GFlip) and close < GFlip;
AddLabel(thruCall or thruPut,
    "SQUEEZE CONTEXT: break through " + (if thruCall then "CALL" else "PUT")
        + " wall (unvalidated, size-only)", Color.MAGENTA);
AddLabel(belowFlip and (buySig or sellSig),
    "below gamma flip = short-gamma regime (context only)", Color.PLUM);"""


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
    mode = "absolute" if a.sym in ("QQQ", "SPY") else "ratio"
    try:
        blk = gdl.block(a.sym, mode, a.days, DATE, native)
    except Exception as e:                       # never ship a broken block
        blk = f"# ---- dealer gamma unavailable: {e} ----"

    # only wire the squeeze-context labels if the gamma block really defined
    # the GFlip/CWall/PWall plots they reference
    squeeze = SQUEEZE if ("plot CWall" in blk and "plot PWall" in blk
                          and "plot GFlip" in blk) else \
        "# ---- gamma-squeeze context omitted: no per-day walls available ----"

    s = (TEMPLATE.replace("__SYM__", a.sym)
                 .replace("__DATE__", DATE)
                 .replace("__GAMMALEVELS__", blk)
                 .replace("__SQUEEZE__", squeeze))

    errs = validate(a.sym + "-breakout", s)
    if errs:
        print("!!! GENERATED STUDY FAILED VALIDATION — do not paste into ToS:",
              file=sys.stderr)
        for e in errs:
            print("   " + e, file=sys.stderr)
        raise SystemExit(1)

    print(f"\n===== COPY BELOW into ThinkOrSwim — {a.sym} BREAKOUT study ({DATE}) =====")
    print(s.rstrip())
    print(f"===== END {a.sym} BREAKOUT study =====")


if __name__ == "__main__":
    main()
