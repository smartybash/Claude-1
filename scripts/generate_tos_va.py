#!/usr/bin/env python3
"""VALUE-AREA FADE study — the ONLY setup on this chart. No FVG, no confluence
clutter. Just: prior VAH / POC / VAL, the dealer call wall, and a SHORT signal
when price rejects VAH (2nd attempt) on a fade day.

Tested (backtest_va_fade.py, QQQ 5-min 139 days): short the 2nd VAH rejection
after 10:00 ET -> target POC +0.68R (73% win); reaches POC 67%. Positive gamma
pins at POC (target POC), negative gamma runs to VAL/breakout (let it run).

Prior-session value area (70% volume profile) is computed in PYTHON from the
30-min data and baked per-day (robust — no ThinkScript VolumeProfile builtin to
mis-compile). Today's line is the prior session's VA (what you have at the open).

Usage: python3 scripts/generate_tos_va.py [--sym MNQ] [--days 90]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import volume_profile               # (POC, VAH, VAL)
import scripts.gex_daily_levels as gdl                   # call wall / flip per day
from scripts.generate_tos import validate, DATE          # noqa

INTRADAY = {"MNQ": ("nq_30min_eth.json", True), "MES": ("es_30m_live.json", True),
            "QQQ": ("qqq_30m_live.json", False), "SPY": ("spy_30m_live.json", False)}
ET = "America/New_York"


def per_day_va(sym, ndays, today):
    """[(YYYYMMDD of session, (poc,vah,val) from the PRIOR session)]."""
    fname, _fut = INTRADAY[sym]
    import json
    d = json.load(open(ROOT / "data" / fname))
    df = pd.DataFrame({k: d[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(d["time"], utc=True).tz_convert(ET)).sort_index()
    rth = df[(df.index.time >= pd.Timestamp("09:30").time()) &
             (df.index.time < pd.Timestamp("16:00").time())]
    va = {}                                       # session date -> (poc,vah,val)
    for day, bars in rth.groupby(rth.index.normalize()):
        if len(bars) >= 6:
            prof = volume_profile(bars, 50)
            if prof and prof[2] < prof[0] < prof[1]:
                va[day.strftime("%Y%m%d")] = prof
    keys = sorted(va)
    rows = []                                     # session -> PRIOR session VA
    for prev, cur in zip(keys, keys[1:]):
        rows.append((cur, va[prev]))
    if today and keys:
        td = today.replace("-", "")
        if td > keys[-1]:
            rows.append((td, va[keys[-1]]))
    return rows[-ndays:]


def va_block(rows):
    L = ["# ---- PRIOR-DAY VALUE AREA (from that day's prior session, baked) ----",
         "def vad = GetYYYYMMDD();"]
    for tag, ix, col, style in (("VAH", 1, "Color.RED", "Curve.LONG_DASH"),
                                ("POC", 0, "Color.YELLOW", "Curve.SHORT_DASH"),
                                ("VAL", 2, "Color.GREEN", "Curve.LONG_DASH")):
        terms = [f"if vad == {d} then {v[ix]:.2f}" for d, v in rows]
        expr = " else ".join(terms) + " else Double.NaN"
        L.append(f"def {tag} = {expr};")
        L.append(f"plot p{tag} = {tag};  p{tag}.SetDefaultColor({col});  "
                 f"p{tag}.SetStyle({style});  p{tag}.SetLineWeight(2);")
    return "\n".join(L)


TEMPLATE = r"""# =====================================================================
# __SYM__ VALUE-AREA FADE   __DATE__
#   The ONLY setup here: SHORT the rejection of prior VAH (= call wall on a
#   fade day), 2nd attempt, after 10:00 ET. Targets POC then VAL.
#
#   TESTED (backtest_va_fade.py, QQQ 5-min, 139 days):
#     short the 2nd VAH rejection -> target POC +0.68R (73% win), reaches POC 67%.
#     POSITIVE gamma: price PINS at POC -> take POC, don't chase VAL.
#     NEGATIVE gamma: runs POC -> VAL -> breakout -> let it run.
#   Stop just above VAH. 1st-poke rejections are weaker (+0.23R) — wait for #2.
# =====================================================================
declare upper;

input minAttempt   = 2;      # take the Nth rejection (2 = the tested edge)
input skipUntil    = 1000;   # ignore VAH pokes before 10:00 ET
input stopBufPct   = 0.25;   # stop = VAH * (1 + 0.25%)
input showSignals  = yes;
input showBubbles  = yes;
input showGL       = yes;    # dealer call wall / flip (VAH ~ call wall)
input useBreadth   = no;     # sector-leadership veto (MAGS/SMH/IGV) -- OFF: backtest
                             # showed blocking shorts into rising leaders was
                             # backwards (blocked trades won MORE). Kept as a
                             # context label; flip to yes only to experiment.
input breadthLen   = 6;      # momentum lookback (6 bars ~ 30m on 5-min)

# ---- prior-day value area (baked per day, Python-computed) ----
__VABLOCK__

def rth  = SecondsFromTime(0930) >= 0 and SecondsTillTime(1600) > 0;
def newD = GetDay() != GetDay()[1];
def afterOpen = SecondsFromTime(skipUntil) >= 0;
def tol  = 0.0006 * VAH;

# count distinct VAH pokes: re-arm after price pulls >=0.15% below VAH
def tagged = !IsNaN(VAH) and high >= VAH - tol;
def pulled = !IsNaN(VAH) and low  < VAH * (1 - 0.0015);
rec armed  = if newD then 1 else if pulled then 1 else if tagged and armed[1] == 1 then 0 else armed[1];
def newPoke = tagged and armed[1] == 1 and afterOpen and rth;
rec pokeN   = if newD then 0 else if newPoke then pokeN[1] + 1 else pokeN[1];
def reject  = newPoke and close < VAH;

# ---- SECTOR-LEADERSHIP breadth filter (MAGS / SMH / IGV) ----
#   Don't fade-short into rising leadership. Count how many leaders are up over
#   the last `breadthLen` bars; if >=2 are rising, risk appetite is on -> block
#   the short. BACKTESTED (backtest_breadth_filter.py, 67 signals / 12-mo leader
#   history): as a hard veto it did NOT help -- blocked shorts (leaders rising)
#   actually won more (72% vs 62%), because on a fade day the green leaders are
#   the pop that rotates back to POC. So this defaults OFF (context label only).
def upCount = (if close("MAGS") > close("MAGS")[breadthLen] then 1 else 0)
            + (if close("SMH")  > close("SMH")[breadthLen]  then 1 else 0)
            + (if close("IGV")  > close("IGV")[breadthLen]  then 1 else 0);
def leadersUp = upCount >= 2;
def breadthOK = !useBreadth or !leadersUp;      # ok to short when leaders NOT rising

def shortSig = showSignals and reject and pokeN >= minAttempt and breadthOK;

plot Sell = if shortSig then VAH else Double.NaN;
Sell.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
Sell.SetDefaultColor(Color.RED);  Sell.SetLineWeight(5);

def stop = VAH * (1 + stopBufPct / 100);
# keep the bubble WELL CLEAR of the candles: anchor it 3xATR above the bar's
# high (not on the price), so it never sits on the action.
def atr = Average(TrueRange(high, close, low), 14);
AddChartBubble(showBubbles and shortSig, high + 3 * atr,
    "SHORT #" + pokeN + " stop " + Round(stop, 2), Color.RED, yes);
Alert(shortSig, "VAH rejection short", Alert.BAR, Sound.Ring);

# ---- dealer gamma (call wall = VAH confluence; flip = regime) ----
__GAMMALEVELS__

# ---- compact labels (one short chip each, so the top row stays readable) ----
def posGamma = showGL and !IsNaN(GFlip) and close > GFlip;
AddLabel(!IsNaN(VAH),
    "VAH " + Round(VAH, 2) + "  POC " + Round(POC, 2) + "  VAL " + Round(VAL, 2),
    Color.WHITE);
AddLabel(!IsNaN(VAH),
    (if posGamma then "POS gamma -> target POC" else "NEG gamma -> run to VAL"),
    if posGamma then Color.LIGHT_GRAY else Color.YELLOW);
AddLabel(showGL and !IsNaN(CWall),
    "CW " + Round(CWall, 2)
        + (if !IsNaN(VAH) and AbsValue(VAH - CWall) / VAH < 0.004 then " =VAH" else ""),
    Color.RED);
AddLabel(showGL and !IsNaN(GFlip), "flip " + Round(GFlip, 2), Color.GRAY);
AddLabel(useBreadth, "leaders " + upCount + "/3 up",
    if leadersUp then Color.GREEN else Color.GRAY);
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="MNQ", choices=list(INTRADAY))
    ap.add_argument("--days", type=int, default=90)
    a = ap.parse_args()

    rows = per_day_va(a.sym, a.days, DATE)
    if not rows:
        print(f"no value-area history for {a.sym}", file=sys.stderr); raise SystemExit(1)

    native = None
    import scripts.gamma_context as gc
    # Fixed absolute gamma levels for TODAY (beats the ratio-mode line, which
    # re-anchors to live price and drifts intraday). MNQ <- NQ slot (QQQ-scaled
    # or native FOP); MES <- SPY native slot scaled by the ES/SPY close ratio;
    # SPY <- its own native slot.
    NATIVE_SRC = {"MNQ": ("NQ", 1.0), "MES": ("SPY", 10.0531), "SPY": ("SPY", 1.0)}
    if a.sym in NATIVE_SRC:
        slot, mult = NATIVE_SRC[a.sym]
        g = gc.load_gamma_levels(slot) or {}
        if g.get("gamma_flip") is not None:
            native = {t: round(g[k] * mult, 2)
                      for k, t in (("gamma_flip", "GF"), ("call_wall", "CW"), ("put_wall", "PW"))
                      if g.get(k) is not None}
    mode = "absolute" if a.sym == "QQQ" else "ratio"
    try:
        blk = gdl.block(a.sym, mode, a.days, DATE, native)
    except Exception as e:
        blk = f"# ---- dealer gamma unavailable: {e} ----"

    s = (TEMPLATE.replace("__SYM__", a.sym).replace("__DATE__", DATE)
                 .replace("__VABLOCK__", va_block(rows))
                 .replace("__GAMMALEVELS__", blk))
    errs = validate(a.sym + "-va", s)
    if errs:
        print("!!! FAILED VALIDATION:", file=sys.stderr)
        for e in errs:
            print("   " + e, file=sys.stderr)
        raise SystemExit(1)
    print(f"\n===== COPY BELOW into ThinkOrSwim — {a.sym} VALUE-AREA FADE ({DATE}) =====")
    print(s.rstrip())
    print(f"===== END {a.sym} VALUE-AREA FADE study =====")


if __name__ == "__main__":
    main()
