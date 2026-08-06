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


def expected_move(px: float, vix: float) -> dict:
    """VIX-implied 1-sigma expected move for one price."""
    day = px * vix / 100 * math.sqrt(1 / TRADING_DAYS)
    wk = px * vix / 100 * math.sqrt(5 / TRADING_DAYS)
    return {"em": day, "up": px + day, "dn": px - day, "weekly": wk}


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
    out = {k: float(v) for k, v in lv.items()
           if k in ("gamma_flip", "call_wall", "put_wall", "zero_gamma") and v is not None}
    if out:
        out["_date"] = blob.get("date", "")
        out["_source"] = blob.get("source", "")
    return out or None


def context(px: float, sym: str | None = None) -> dict:
    vix, sma = load_vix()
    lab, note = regime(vix, sma)
    em = expected_move(px, vix)
    d = {"vix": vix, "vix_sma20": sma, "regime": lab, "note": note,
         "pin": gamma_pin(px), **em}
    if sym:
        gl = load_gamma_levels(sym)
        if gl:
            d["gamma_levels"] = gl
    return d


if __name__ == "__main__":
    vix, sma = load_vix()
    lab, note = regime(vix, sma)
    print(f"VIX {vix:.2f} (20d SMA {sma:.2f}) -> {lab}: {note}")
    for name, p in [("SPY", 774.35), ("QQQ", 723.77), ("ES", 7795.5), ("NQ", 29854.0)]:
        c = expected_move(p, vix)
        print(f"  {name:4s} @ {p:>9.2f}  EM +/-{c['em']:.2f}  band [{c['dn']:.2f}, {c['up']:.2f}]"
              f"  pin {gamma_pin(p):.0f}  weekly +/-{c['weekly']:.2f}")
