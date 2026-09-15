"""Refine the trend trigger and backtest entry/stop/exit rules on TREND calls.

Universe: pooled QQQ+SPY hourly RTH sessions (every session IBKR intraday
history reaches: Nov 2025 - Jul 2026, 306 sessions). All PnL in ATR20 units
so results translate directly to NQ/ES points.

Trade template (long shown; shorts mirrored):
  signal   11:00 ET TREND_UP per the filter, thresholds (R*, POS*) on a grid
  entry    E_mkt: market at the 11:00 print
           E_pb : limit at the opening-range high, GTC until 15:00, else no trade
  stop     S_mid: opening-range midpoint
           S_or : opposite opening-range extreme
           S_atr: entry - 0.30 x ATR20
  exit     stop hit (conservative: stop assumed filled before any favorable
           move within the same hourly bar) or market-on-close
  costs    0.02 x ATR round trip (~15 NQ pts / ~2.3 ES pts at current ATR;
           deliberately fat to absorb slippage on stop fills)
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

COST_ATR = 0.02  # round-trip, in ATR units


def build_sessions(sym: str) -> list[dict]:
    daily = load_ibkr_json(DATA / f"{sym}_daily_5y.json")
    a20 = atr(daily, 20).shift(1)
    a20.index = pd.to_datetime(a20.index.date)

    bars = rth_only(load_ibkr_json(DATA / f"{sym}_1h.json"))
    dates = pd.to_datetime(pd.Series(bars.index.date, index=bars.index))
    out = []
    for date, day in bars.groupby(dates):
        if len(day) < 6 or day.index[0].time() != dtime(9, 30):
            continue
        if date not in a20.index or np.isnan(a20[date]):
            continue
        fh = day[day.index.time < dtime(11, 0)]
        rest = day[day.index.time >= dtime(11, 0)]
        o = float(fh["open"].iloc[0])
        closes = fh["close"]
        path = float(closes.diff().abs().sum() + abs(closes.iloc[0] - o))
        fh_hi, fh_lo = float(fh["high"].max()), float(fh["low"].min())
        out.append({
            "sym": sym, "date": date, "atr": float(a20[date]), "open": o,
            "fh_hi": fh_hi, "fh_lo": fh_lo, "p_dec": float(closes.iloc[-1]),
            "er": abs(float(closes.iloc[-1]) - o) / path if path > 0 else np.nan,
            "rest": rest[["open", "high", "low", "close"]],
        })
    return out


def signal(s: dict, r_min: float, pos_min: float) -> int:
    """+1 TREND_UP, -1 TREND_DOWN, 0 no trade. Includes the chop vetoes."""
    rng = s["fh_hi"] - s["fh_lo"]
    r = rng / s["atr"]
    pos = (s["p_dec"] - s["fh_lo"]) / rng if rng > 0 else 0.5
    if r < 0.35 or r < r_min:
        return 0
    if pos >= pos_min:
        return 1
    if pos <= 1 - pos_min:
        return -1
    return 0


def simulate(s: dict, d: int, entry_mode: str, stop_mode: str) -> float | None:
    """Signed PnL in ATR units, or None if no fill. d = +1 long / -1 short."""
    a = s["atr"]
    or_far = s["fh_lo"] if d > 0 else s["fh_hi"]   # opposite OR extreme
    or_near = s["fh_hi"] if d > 0 else s["fh_lo"]  # OR extreme in trade direction
    mid = 0.5 * (s["fh_hi"] + s["fh_lo"])
    rest = s["rest"]

    if entry_mode == "mkt":
        entry, active = s["p_dec"], rest
    else:  # pullback to the OR edge, only fills if price comes back
        touched = None
        for ts, b in rest.iterrows():
            if ts.time() >= dtime(15, 0):
                break
            if (d > 0 and b["low"] <= or_near) or (d < 0 and b["high"] >= or_near):
                touched = ts
                break
        if touched is None:
            return None
        entry, active = or_near, rest.loc[touched:]

    stop = {"mid": mid, "or": or_far, "atr": entry - d * 0.30 * a}[stop_mode]
    if (d > 0 and stop >= entry) or (d < 0 and stop <= entry):
        return None  # degenerate geometry (pullback fill below the stop)

    for _, b in active.iterrows():
        if d > 0 and b["low"] <= stop:
            return (stop - entry) / a - COST_ATR
        if d < 0 and b["high"] >= stop:
            return (entry - stop) / a - COST_ATR
    return d * (float(rest["close"].iloc[-1]) - entry) / a - COST_ATR


def run_grid(sessions, label):
    print(f"\n================ {label} ({len(sessions)} sessions)")
    rows = []
    for r_min in [0.45, 0.55, 0.65]:
        for pos_min in [0.75, 0.80, 0.85]:
            for em in ["mkt", "pb"]:
                for sm in ["mid", "or", "atr"]:
                    pnl = []
                    for s in sessions:
                        d = signal(s, r_min, pos_min)
                        if d == 0:
                            continue
                        p = simulate(s, d, em, sm)
                        if p is not None:
                            pnl.append(p)
                    if len(pnl) < 5:
                        continue
                    pnl = np.array(pnl)
                    rows.append({
                        "R*": r_min, "POS*": pos_min, "entry": em, "stop": sm,
                        "n": len(pnl), "win%": (pnl > 0).mean().round(3),
                        "avg": pnl.mean().round(4), "med": np.median(pnl).round(4),
                        "total": pnl.sum().round(2),
                        "worst": pnl.min().round(3),
                    })
    df = pd.DataFrame(rows).sort_values("avg", ascending=False)
    print(df.to_string(index=False))
    return df


def main():
    sessions = build_sessions("qqq") + build_sessions("spy")
    sessions.sort(key=lambda s: s["date"])
    mid = sessions[len(sessions) // 2]["date"]
    train = [s for s in sessions if s["date"] < mid]
    test = [s for s in sessions if s["date"] >= mid]

    df_tr = run_grid(train, f"TRAIN  (to {mid.date()})")
    df_te = run_grid(test, f"TEST   (from {mid.date()})")

    # the config chosen on train, shown on test explicitly
    best = df_tr.iloc[0]
    m = (df_te["R*"] == best["R*"]) & (df_te["POS*"] == best["POS*"]) & \
        (df_te["entry"] == best["entry"]) & (df_te["stop"] == best["stop"])
    print("\nTrain-selected config on TEST:")
    print(df_te[m].to_string(index=False) if m.any() else "  (fewer than 5 trades on test)")

    run_grid(sessions, "FULL SAMPLE (in-sample reference)")


if __name__ == "__main__":
    main()
