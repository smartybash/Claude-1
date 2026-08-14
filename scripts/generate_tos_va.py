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
def shortSig = showSignals and reject and pokeN >= minAttempt;

plot Sell = if shortSig then VAH else Double.NaN;
Sell.SetPaintingStrategy(PaintingStrategy.BOOLEAN_ARROW_DOWN);
Sell.SetDefaultColor(Color.RED);  Sell.SetLineWeight(5);

def stop = VAH * (1 + stopBufPct / 100);
# keep the bubble WELL CLEAR of the candles: anchor it 3xATR above the bar's
# high (not on the price), so it never sits on the action.
def atr = Average(TrueRange(high, close, low), 14);
AddChartBubble(showBubbles and shortSig, high + 3 * atr,
    "SHORT #" + pokeN + "  stop " + Round(stop, 2)
        + "  POC " + Round(POC, 2) + "  VAL " + Round(VAL, 2), Color.RED, yes);
Alert(shortSig, "VAH rejection short", Alert.BAR, Sound.Ring);

# ---- dealer gamma (call wall = VAH confluence; flip = regime) ----
__GAMMALEVELS__

# ---- regime-aware target guidance (validated) ----
def posGamma = showGL and !IsNaN(GFlip) and close > GFlip;
AddLabel(!IsNaN(VAH),
    "VA FADE | VAH " + Round(VAH, 2) + " POC " + Round(POC, 2) + " VAL " + Round(VAL, 2)
        + (if posGamma then "  | POS gamma: target POC (pins), don't chase VAL"
           else "  | NEG gamma: let it run POC -> VAL -> breakout"),
    if posGamma then Color.LIGHT_GRAY else Color.YELLOW);
AddLabel(showGL and !IsNaN(CWall),
    "call wall " + Round(CWall, 2)
        + (if !IsNaN(VAH) and AbsValue(VAH - CWall) / VAH < 0.004
           then "  == VAH (A+ fade confluence)" else ""),
    Color.RED);
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
    if a.sym == "MNQ":
        import scripts.gamma_context as gc
        nq = gc.load_gamma_levels("NQ") or {}
        if "FOP" in str(nq.get("_source", "")):
            native = {t: nq[k] for k, t in (("gamma_flip", "GF"), ("call_wall", "CW"),
                                            ("put_wall", "PW")) if nq.get(k) is not None}
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
