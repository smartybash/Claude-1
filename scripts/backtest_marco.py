"""Backtest of the Marco Trades liquidity-trap playbook, mechanized.

Setup (long side; shorts mirrored at the prior-day high):
  level      prior-day low, only if "respected": prior close >= 0.15 ATR away
  return     session must OPEN above the level (a gap through consumes it)
  sweep      first RTH bar trading below the level
  entries    zone: resting limit at level - 0.05 ATR (fills into the sweep)
             trap: market at the first bar CLOSE back above the level
  stop       zone: level - 0.30 ATR
             trap: sweep extreme so far - 0.05 ATR (skip if that is already
                   deeper than 0.45 ATR below the level - trap invalidated)
  targets    pc   : prior close (nearest big pool)
             ext  : 0.40 ATR beyond the level
             far  : opposite prior-day extreme
             (otherwise exit MOC; conservative stop-first intrabar ordering)
  costs      0.02 ATR round trip
One trade per side per day. Universes: pooled QQQ+SPY 30-min (~154 sessions)
and pooled QQQ+SPY 15-min (~76 sessions). Regime gating compared after the
11:00 read (no-lookahead: gated results use only trades entered after 11:00).
"""

import sys
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json, rth_only
from regime.indicators import atr

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 220)
COST = 0.02


def regime_call(fh_hi, fh_lo, p_dec, o, a, path):
    rng = fh_hi - fh_lo
    r = rng / a
    pos = (p_dec - fh_lo) / rng if rng > 0 else 0.5
    er = abs(p_dec - o) / path if path > 0 else np.nan
    if r < 0.35 or (er < 0.40 and 0.20 < pos < 0.80):
        return "CHOP"
    if r >= 0.55 and (pos >= 0.75 or pos <= 0.25):
        return "TREND"
    return "NEUTRAL"


def sessions(sym: str, intra_file: str):
    daily = load_ibkr_json(DATA / f"{sym}_daily_5y.json")
    a20 = atr(daily, 20).shift(1)
    idx = pd.to_datetime(daily.index.date)
    a20.index = idx
    pdh = daily["high"].shift(1); pdh.index = idx
    pdl = daily["low"].shift(1); pdl.index = idx
    pc = daily["close"].shift(1); pc.index = idx

    bars = rth_only(load_ibkr_json(DATA / intra_file))
    dates = pd.to_datetime(pd.Series(bars.index.date, index=bars.index))
    for date, day in bars.groupby(dates):
        if day.index[0].time() != dtime(9, 30) or date not in a20.index or np.isnan(a20[date]):
            continue
        fh = day[day.index.time < dtime(11, 0)]
        o = float(fh["open"].iloc[0])
        closes = fh["close"]
        path = float(closes.diff().abs().sum() + abs(closes.iloc[0] - o))
        call = regime_call(float(fh["high"].max()), float(fh["low"].min()),
                           float(closes.iloc[-1]), o, float(a20[date]), path)
        yield {
            "date": date, "day": day, "atr": float(a20[date]),
            "pdh": float(pdh[date]), "pdl": float(pdl[date]), "pc": float(pc[date]),
            "call": call,
        }


def trade_long(s, entry_mode, target_mode):
    """Returns (pnl, entry_ts) or None. Shorts run via the mirrored frame."""
    a, lvl = s["atr"], s["pdl"]
    day = s["day"]
    if abs(s["pc"] - lvl) < 0.15 * a:          # not a respected level
        return None
    if float(day["open"].iloc[0]) <= lvl:      # gap through: level consumed
        return None
    swept = day[day["low"] < lvl]
    if swept.empty:
        return None
    t0 = swept.index[0]

    if entry_mode == "zone":
        limit = lvl - 0.05 * a
        fillable = day.loc[t0:][day.loc[t0:]["low"] <= limit]
        if fillable.empty:
            return None
        e_ts, entry = fillable.index[0], limit
        stop = lvl - 0.30 * a
    else:  # trap: first close back above the level after the sweep
        after = day.loc[t0:]
        rec = after[after["close"] > lvl]
        if rec.empty:
            return None
        e_ts = rec.index[0]
        entry = float(rec["close"].iloc[0])
        sweep_ext = float(day.loc[t0:e_ts]["low"].min())
        if sweep_ext < lvl - 0.45 * a:         # trap invalidated, too deep
            return None
        stop = sweep_ext - 0.05 * a

    tgt = {"pc": s["pc"], "ext": lvl + 0.40 * a, "far": s["pdh"]}[target_mode]
    if tgt <= entry:
        return None
    rest = day.loc[e_ts:]
    first = True
    for ts, b in rest.iterrows():
        lo_hit = b["low"] <= stop if not (first and entry_mode == "trap") else b["low"] <= stop
        if first and entry_mode == "zone":
            lo_hit = b["low"] <= stop  # same bar can stop out after the fill
        if lo_hit:
            return (stop - entry) / a - COST, e_ts
        if b["high"] >= tgt and not (first and entry_mode == "zone" and b["open"] < tgt <= entry):
            return (tgt - entry) / a - COST, e_ts
        first = False
    return (float(rest["close"].iloc[-1]) - entry) / a - COST, e_ts


def mirror(s):
    """Mirror the session so trade_long handles the short at the prior-day high."""
    day = s["day"]
    m = pd.DataFrame({
        "open": -day["open"], "high": -day["low"], "low": -day["high"], "close": -day["close"],
    }, index=day.index)
    return {**s, "day": m, "pdl": -s["pdh"], "pdh": -s["pdl"], "pc": -s["pc"]}


def run(universe, label):
    print(f"\n================ {label} ({len(universe)} sessions)")
    rows = []
    for em in ["zone", "trap"]:
        for tm in ["pc", "ext", "far"]:
            recs = []
            for s in universe:
                for side, ss in [("long", s), ("short", mirror(s))]:
                    r = trade_long(ss, em, tm)
                    if r is not None:
                        recs.append({"pnl": r[0], "ts": r[1], "call": s["call"], "date": s["date"]})
            if len(recs) < 8:
                continue
            t = pd.DataFrame(recs)
            after11 = t[t["ts"].dt.time >= dtime(11, 0)]
            chop_a11 = after11[after11["call"] == "CHOP"]
            noTrend_a11 = after11[after11["call"] != "TREND"]
            t_s = t.sort_values("date")
            mid = t_s["date"].iloc[len(t_s) // 2]
            rows.append({
                "entry": em, "target": tm, "n": len(t),
                "win%": round((t["pnl"] > 0).mean(), 3),
                "avg": round(t["pnl"].mean(), 4),
                "H1": round(t_s[t_s["date"] < mid]["pnl"].mean(), 3),
                "H2": round(t_s[t_s["date"] >= mid]["pnl"].mean(), 3),
                "n_11+": len(after11),
                "avg_11+": round(after11["pnl"].mean(), 4) if len(after11) else np.nan,
                "n_chop11": len(chop_a11),
                "avg_chop11": round(chop_a11["pnl"].mean(), 4) if len(chop_a11) else np.nan,
                "avg_noTrend11": round(noTrend_a11["pnl"].mean(), 4) if len(noTrend_a11) else np.nan,
            })
    print(pd.DataFrame(rows).sort_values("avg", ascending=False).to_string(index=False))


u30 = list(sessions("qqq", "qqq_30min.json")) + list(sessions("spy", "spy_30min.json"))
u15 = list(sessions("qqq", "qqq_15min.json")) + list(sessions("spy", "spy_15min.json"))
run(u30, "30-min bars, Mar-Jul 2026")
run(u15, "15-min bars, May-Jul 2026")
