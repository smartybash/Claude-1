"""Marco trap backtest v2 — his actual geometry.

Long side shown (shorts mirrored):
  sweep      respected prior-day low taken out (return, not gap-through)
  BOS        15-min close back above the level
  entry      E_bos:    at the BOS close (v1 baseline)
             E_retest: limit AT the level on the pullback after BOS
                       (valid until 15:00; no touch = no trade)
  stop       tight: sweep extreme - 0.05 ATR  (both entries)
  targets    T_far:   opposite prior-day extreme, all out (or MOC)
             T_split: half at nearest pool, stop to breakeven, half at far
             T_near:  nearest pool only (the v1 target, for comparison)
  metrics    R-multiples (R = entry - stop) and ATR units, costs 0.02 ATR
"""

import sys
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backtest_marco import sessions  # session builder incl. regime call

pd.set_option("display.width", 220)
COST = 0.02


def sim(s, entry_mode, target_mode):
    a, lvl, far, pc = s["atr"], s["pdl"], s["pdh"], s["pc"]
    day = s["day"]
    if abs(pc - lvl) < 0.15 * a or float(day["open"].iloc[0]) <= lvl:
        return None
    swept = day[day["low"] < lvl]
    if swept.empty:
        return None
    t0 = swept.index[0]
    after = day.loc[t0:]
    rec = after[after["close"] > lvl]
    if rec.empty:
        return None
    e_ts = rec.index[0]
    if e_ts.time() < dtime(11, 0):
        return None
    ext = float(day.loc[t0:e_ts]["low"].min())
    if ext < lvl - 0.45 * a:
        return None
    stop = ext - 0.05 * a

    if entry_mode == "bos":
        entry = float(rec["close"].iloc[0])
        live = day.loc[e_ts:].iloc[1:]
    else:  # retest: limit at the level on the pullback after the BOS close
        pull = day.loc[e_ts:].iloc[1:]
        pull = pull[pull.index.time < dtime(15, 0)]
        touch = pull[pull["low"] <= lvl]
        if touch.empty:
            return None
        f_ts = touch.index[0]
        # if the touching bar also breaks the stop, treat fill+stop same bar
        entry = lvl
        live = day.loc[f_ts:]

    r = entry - stop
    if r < 0.04 * a:
        return None
    near_pools = [p for p in (pc, s["on_hi_lo"][0] if s.get("on_hi_lo") else None)
                  if p is not None and p > entry + 0.05 * a]
    near = min(near_pools, key=lambda p: p - entry) if near_pools else None
    if far <= entry + 0.05 * a:
        return None

    def walk(bars, stop_px, tgt, entry_px):
        """Conservative walk: stop first within a bar. Returns pnl or None=MOC."""
        for _, b in bars.iterrows():
            if b["low"] <= stop_px:
                return stop_px - entry_px
            if tgt is not None and b["high"] >= tgt:
                return tgt - entry_px
        return None

    if target_mode == "far":
        res = walk(live, stop, far, entry)
        pnl = res if res is not None else float(day["close"].iloc[-1]) - entry
    elif target_mode == "near":
        if near is None:
            return None
        res = walk(live, stop, near, entry)
        pnl = res if res is not None else float(day["close"].iloc[-1]) - entry
    else:  # split: half at near, then stop->BE, half runs to far
        if near is None:
            return None
        pnl1 = pnl2 = None
        hit_near = False
        stop_px = stop
        for _, b in live.iterrows():
            if not hit_near:
                if b["low"] <= stop_px:
                    pnl1 = pnl2 = stop_px - entry
                    break
                if b["high"] >= near:
                    pnl1 = near - entry
                    hit_near = True
                    stop_px = entry  # breakeven
            else:
                if b["low"] <= stop_px:
                    pnl2 = stop_px - entry
                    break
                if b["high"] >= far:
                    pnl2 = far - entry
                    break
        moc = float(day["close"].iloc[-1]) - entry
        if pnl1 is None:
            pnl1 = moc
        if pnl2 is None:
            pnl2 = moc if not hit_near else max(moc, 0.0) if False else moc
        pnl = 0.5 * (pnl1 + pnl2)

    return {"pnl_atr": pnl / a - COST, "R": (pnl - COST * a) / r, "risk_atr": r / a,
            "call": s["call"], "date": s["date"]}


def mirror(s):
    day = s["day"]
    m = pd.DataFrame({"open": -day["open"], "high": -day["low"],
                      "low": -day["high"], "close": -day["close"]}, index=day.index)
    return {**s, "day": m, "pdl": -s["pdh"], "pdh": -s["pdl"], "pc": -s["pc"]}


def run(universe, label):
    print(f"\n================ {label} ({len(universe)} sessions)")
    rows = []
    for em in ["bos", "retest"]:
        for tm in ["far", "split", "near"]:
            recs = []
            for s in universe:
                for ss in (s, mirror(s)):
                    r = sim(ss, em, tm)
                    if r:
                        recs.append(r)
            if len(recs) < 6:
                continue
            t = pd.DataFrame(recs).sort_values("date")
            mid = t["date"].iloc[len(t) // 2]
            gated = t[t["call"] != "TREND"]
            rows.append({
                "entry": em, "target": tm, "n": len(t),
                "win%": round((t["pnl_atr"] > 0).mean(), 3),
                "avgR": round(t["R"].mean(), 3),
                "avg_atr": round(t["pnl_atr"].mean(), 4),
                "med_risk": round(t["risk_atr"].median(), 3),
                "H1_R": round(t[t["date"] < mid]["R"].mean(), 2),
                "H2_R": round(t[t["date"] >= mid]["R"].mean(), 2),
                "n_gate": len(gated),
                "avgR_gate": round(gated["R"].mean(), 3) if len(gated) else np.nan,
            })
    print(pd.DataFrame(rows).sort_values("avgR", ascending=False).to_string(index=False))


u30 = list(sessions("qqq", "qqq_30min.json")) + list(sessions("spy", "spy_30min.json"))
u15 = list(sessions("qqq", "qqq_15min.json")) + list(sessions("spy", "spy_15min.json"))
for s in u30 + u15:
    s["on_hi_lo"] = None
run(u30, "30-min bars, Mar-Jul 2026")
run(u15, "15-min bars, May-Jul 2026")
