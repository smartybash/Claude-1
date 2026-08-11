"""Gamma/GEX context layer — the honest, backtest-supported slice of Alex's read.

We CANNOT compute a true dealer-GEX (no option OI/greeks history in IBKR MCP or
FMP). What survives honest testing / is model-free:
  1. EXPECTED MOVE (VIX-implied): the day's 1-sigma envelope = the practical
     "gamma walls" / expected range. Model-free, reliable.
  2. VOL REGIME (VIX vs its own 20d trend): a *descriptive* context tilt.
     Backtest (backtest_gex_proxy.py) found the naive "pos-gamma=mean-revert"
     story does NOT hold as a mechanical switch on our sample — one leg
     sign-flipped across halves. The one consistent tendency: on ELEVATED-VIX
     days the morning move tends to get faded in the afternoon (two-way),
     while calm-VIX days grind. So we surface regime as CONTEXT, not a trigger.
  3. GAMMA PIN: the nearest big round strike — the crudest "cool wall" magnet
     proxy (real walls need OI we don't have).

All numbers are baked into the ToS study at generation time and printed in the
confluence read, so every rerun carries them without any live options calls.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRADING_DAYS = 252


def load_vix() -> tuple[float, float]:
    """(last VIX close, its 20-day SMA)."""
    r = json.loads((ROOT / "data" / "vix_daily_5y.json").read_text())
    v = pd.Series(r["close"], index=pd.to_datetime([t[:10] for t in r["time"]]))
    v = v[~v.index.duplicated(keep="last")].sort_index()
    return float(v.iloc[-1]), float(v.tail(20).mean())


def regime(vix: float, sma20: float) -> tuple[str, str]:
    """(label, one-line context note). Descriptive vol state, not a trigger."""
    if vix < sma20 and vix < 20:
        return "VOL-CALM", "low/falling VIX: grind/one-way tendency, EM band tends to hold"
    if vix > sma20 or vix >= 22:
        return "VOL-STRESSED", "elevated/rising VIX: 2-way whip, morning move often faded pm, EM can break"
    return "VOL-NEUTRAL", "VIX mid-range: no strong regime tilt"


def gamma_em_mult(net_gex: float | None, sign: str | None = None) -> tuple[float, str]:
    """Scale the EM band by the dealer-gamma regime.

    Backtest (backtest_gex_features.py, QQQ n=31) found a clean dose-response:
    next-day RANGE rose monotonically as net GEX got more negative
    (most-negative tercile 1.85% / middle 1.55% / most-positive 1.24%; overall
    1.54%). So we widen the VIX EM band on negative-gamma days and tighten it on
    positive-gamma days by the ratio of each tercile's realized range to the
    overall mean, rounded to simple factors: 1.20 / 1.00 / 0.80.

    Terciles are taken live from data/gex_history.jsonl so the breakpoints track
    the actual sample. When net_gex is given (in OUR computed $ units) we use the
    tercile bucket. When only the SIGN is known (a manual read gives a +/-gamma
    zone or a GEX in a provider's own units that isn't comparable to our terciles),
    pass sign='pos'/'neg' to apply the tercile-edge factor by sign as a proxy.
    Returns (multiplier, label); (1.0, ...) if nothing usable.
    """
    if net_gex is None:
        if sign == "pos":
            return 0.80, "POSITIVE gamma (sign only) -> TIGHTER expected range (x0.80)"
        if sign == "neg":
            return 1.20, "NEGATIVE gamma (sign only) -> WIDER expected range (x1.20)"
        return 1.0, "no net-GEX -> VIX EM unscaled (x1.00)"
    f = ROOT / "data" / "gex_history.jsonl"
    vals = []
    if f.exists():
        for ln in f.read_text().splitlines():
            if not ln.strip():
                continue
            try:
                g = json.loads(ln)
            except Exception:
                continue
            if g.get("sym") == "QQQ" and g.get("net_gex") is not None:
                vals.append(float(g["net_gex"]))
    if len(vals) < 9:
        return 1.0, "gamma history too thin -> VIX EM unscaled (x1.00)"
    s = pd.Series(vals)
    lo, hi = s.quantile(1 / 3), s.quantile(2 / 3)
    if net_gex <= lo:
        return 1.20, "most-NEGATIVE gamma tercile -> WIDER expected range (x1.20)"
    if net_gex >= hi:
        return 0.80, "most-POSITIVE gamma tercile -> TIGHTER expected range (x0.80)"
    return 1.00, "middle gamma tercile -> normal expected range (x1.00)"


def earnings_mult(today: str | None = None) -> tuple[float, str]:
    """Widen the EM band when today's session reacts to a mega-cap earnings report.

    Backtest (backtest_earnings_range.py, AAPL/MSFT/NVDA vs QQQ): the session that
    trades a mega-cap report ran ~1.21x wider range than a normal day (Welch t
    +2.70, stable both halves). So on a reaction day we widen the band x1.20.

    Reaction days come from data/earnings_calendar.json (refresh via
    earnings_cal.py). Returns (multiplier, label); (1.0, ...) when today is not a
    reaction day or the calendar is missing.
    """
    import datetime as _dt
    day = today or _dt.date.today().strftime("%Y-%m-%d")
    f = ROOT / "data" / "earnings_calendar.json"
    if not f.exists():
        return 1.0, ""
    try:
        blob = json.loads(f.read_text())
    except Exception:
        return 1.0, ""
    hits = [e for e in blob.get("events", []) if e.get("reaction_day") == day]
    if not hits:
        return 1.0, ""
    m = float(blob.get("widen_mult", 1.20))
    names = "/".join(sorted({e["sym"] for e in hits}))
    return m, f"EARNINGS NIGHT ({names}) -> WIDER expected range (x{m:.2f})"


def expected_move(px: float, vix: float, mult: float = 1.0) -> dict:
    """VIX-implied 1-sigma expected move for one price.

    `mult` scales the band width by the dealer-gamma regime (see gamma_em_mult).
    `em` is the raw VIX 1-sigma; `em_adj` and the up/dn band carry the scaling.
    """
    day = px * vix / 100 * math.sqrt(1 / TRADING_DAYS)
    wk = px * vix / 100 * math.sqrt(5 / TRADING_DAYS)
    adj = day * mult
    return {"em": day, "em_adj": adj, "em_mult": mult,
            "up": px + adj, "dn": px - adj, "weekly": wk}


def pin_step(px: float) -> float:
    """Round-strike granularity for the 'gamma pin' magnet proxy."""
    if px >= 20000:   # NQ
        return 100.0
    if px >= 3000:    # ES
        return 25.0
    if px >= 300:     # SPY/QQQ-ish
        return 5.0
    return 1.0


def gamma_pin(px: float) -> float:
    step = pin_step(px)
    return round(px / step) * step


def load_gamma_levels(sym: str) -> dict | None:
    """User-supplied dealer-gamma levels read off WealthCharts (or any provider),
    from data/gamma_levels.json. Returns {gamma_flip, call_wall, put_wall,
    zero_gamma} for `sym` (only the non-null keys), or None if absent.

    WealthCharts gives LIVE chain+greeks, not history — so these are typed/pasted
    in each morning. Schema (see data/gamma_levels.example.json):
      {"date": "...", "source": "WealthCharts",
       "levels": {"NQ": {"gamma_flip": 29850, "call_wall": 30200,
                          "put_wall": 29400, "zero_gamma": 29850}, ...}}
    Symbol aliases: MNQ->NQ, MES->ES (futures micros share the level set).
    """
    f = ROOT / "data" / "gamma_levels.json"
    if not f.exists():
        return None
    try:
        blob = json.loads(f.read_text())
    except Exception:
        return None
    alias = {"MNQ": "NQ", "MES": "ES"}
    key = alias.get(sym, sym)
    lv = (blob.get("levels") or {}).get(key)
    if not lv:
        return None
    fields = ("gamma_flip", "call_wall", "put_wall", "zero_gamma", "net_gex", "dealer_delta")
    out = {k: float(v) for k, v in lv.items() if k in fields and v is not None}
    if out:
        out["_date"] = blob.get("date", "")
        out["_source"] = blob.get("source", "")
    return out or None


def gamma_read(px: float, gl: dict | None) -> dict:
    """The explicit dealer-gamma regime call at the current price.

    Primary signal = the SIGN of net GEX if provided (negative => dealers short
    gamma => they buy strength / sell weakness => moves EXTEND => trend/'long
    day'; positive => they fade both ways => range/chop). If net_gex isn't given,
    fall back to spot vs the gamma flip / zero-gamma level (below flip = negative
    gamma). Returns {state, note, basis} or state='UNKNOWN' when nothing loaded.
    """
    if not gl:
        return {"state": "UNKNOWN",
                "note": "no dealer-gamma data loaded (fill net_gex or gamma_flip from WealthCharts)",
                "basis": None}
    flip = gl.get("gamma_flip", gl.get("zero_gamma"))
    ng = gl.get("net_gex")
    neg = None
    basis = None
    if ng is not None:
        neg = ng < 0
        basis = f"net GEX {ng/1e9:+.2f}B ({'NEGATIVE' if neg else 'positive'})"
    elif flip is not None:
        neg = px < flip
        basis = f"spot {px:.0f} {'BELOW' if neg else 'above'} flip {flip:.0f}"
    if neg is None:
        return {"state": "UNKNOWN", "note": "gamma level present but not usable", "basis": None}
    if neg:
        note = ("NEGATIVE GAMMA -> dealers amplify moves. Expect a BIGGER-RANGE / "
                "EXPANSION day: give trades room, fades get run further. (Backtest: "
                "neg-gamma ran ~0.36%/day wider range on QQQ, stable both halves; a "
                "cleaner one-way TREND is NOT confirmed -- it's a range switch, not direction.)")
        state = "NEGATIVE"
    else:
        note = ("POSITIVE GAMMA -> dealers dampen moves. Expect a TIGHTER / RANGE day: "
                "mean-reversion at the edges more reliable, breakouts tend to stall.")
        state = "POSITIVE"
    dd = gl.get("dealer_delta")
    if dd is not None:
        lean = "up (dealers must BUY dips)" if dd > 0 else "down (dealers must SELL rallies)" if dd < 0 else "flat"
        note += f" Dealer delta {dd/1e6:+.1f}M -> directional lean {lean}."
    return {"state": state, "note": note, "basis": basis}


def context(px: float, sym: str | None = None) -> dict:
    vix, sma = load_vix()
    lab, note = regime(vix, sma)
    gl = load_gamma_levels(sym) if sym else None
    net_gex = gl.get("net_gex") if gl else None
    # sign fallback when no comparable net_gex magnitude: spot vs flip (above=+gamma)
    sign = None
    if gl:
        flip = gl.get("gamma_flip", gl.get("zero_gamma"))
        if flip is not None:
            sign = "pos" if px >= flip else "neg"
    gmult, gmult_note = gamma_em_mult(net_gex, sign)
    emult, emult_note = earnings_mult()
    mult = gmult * emult
    em = expected_move(px, vix, mult)
    d = {"vix": vix, "vix_sma20": sma, "regime": lab, "note": note,
         "pin": gamma_pin(px), "gamma_mult": gmult, "gamma_mult_note": gmult_note,
         "earn_mult": emult, "earn_mult_note": emult_note,
         "em_mult_note": gmult_note + (f" | {emult_note}" if emult_note else ""), **em}
    if gl:
        d["gamma_levels"] = gl
    return d


if __name__ == "__main__":
    vix, sma = load_vix()
    lab, note = regime(vix, sma)
    print(f"VIX {vix:.2f} (20d SMA {sma:.2f}) -> {lab}: {note}")
    for name, p in [("SPY", 774.35), ("QQQ", 723.77), ("ES", 7795.5), ("NQ", 29854.0)]:
        c = context(p, name)
        print(f"  {name:4s} @ {p:>9.2f}  EM +/-{c['em']:.2f} x{c['em_mult']:.2f}"
              f" = +/-{c['em_adj']:.2f}  band [{c['dn']:.2f}, {c['up']:.2f}]"
              f"  pin {gamma_pin(p):.0f}  ({c['em_mult_note']})")
