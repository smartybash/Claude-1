"""Regime-adaptive intraday engine.

The overnight-VP fade levels only work on BALANCE days. On TREND days price
leaves value at the open and never returns, so fading is useless (this week).
This engine reads the REGIME first, then gives the matching playbook + the
levels that actually matter intraday: VWAP (+bands), opening range, prior-day
H/L/close, developing session H/L, round numbers - not just the static
overnight value area.

Regime (efficiency ratio er = |net move| / sum|bar-to-bar move|, side = % bars above VWAP):
  TREND UP   : er>=0.40 and side>=0.66      -> ride pullbacks to VWAP/OR, target higher
  TREND DOWN : er>=0.40 and side<=0.34      -> ride pullbacks to VWAP/OR, target lower
  BALANCE    : otherwise                    -> fade the day's edges / VWAP bands back to VWAP

We read regime on TWO clocks so it stays close to live action:
  SESSION = all RTH bars since 9:30 (the day's character)
  NOW     = just the last hour (12x 5-min bars) + VWAP slope
When NOW disagrees with SESSION we flag a REGIME SHIFT (e.g. AM trend rolling over
into a PM fade) instead of staying anchored to the morning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import round_numbers, round_step

ET = "America/New_York"


def load5() -> pd.DataFrame:
    r = json.loads((ROOT / "data" / "nq_5min_eth_live.json").read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def regime_of(closes: pd.Series, vwap: pd.Series):
    """(label, arrow, er, side) for a slice of bars vs the session VWAP over that
    slice. er = net travel / gross travel; side = share of bars closing > VWAP."""
    gross = closes.diff().abs().sum()
    er = abs(float(closes.iloc[-1]) - float(closes.iloc[0])) / gross if gross else 0.0
    side = float((closes.values > vwap.values).mean())
    if er >= 0.40 and side >= 0.66:
        return "TREND UP", "up", er, side
    if er >= 0.40 and side <= 0.34:
        return "TREND DOWN", "down", er, side
    return "BALANCE", "chop", er, side


def main():
    df = load5()
    now = df.index[-1]
    cur = now.normalize()
    rth = df[(df.index >= cur.replace(hour=9, minute=30)) &
             (df.index < cur.replace(hour=16)) & (df.index.normalize() == cur)]
    if len(rth) < 2:
        print("session not open yet / too few bars"); return

    tp = (rth["high"] + rth["low"] + rth["close"]) / 3
    cum_v = rth["volume"].cumsum()
    vwap = (tp * rth["volume"]).cumsum() / cum_v
    # volume-weighted std for bands
    var = ((tp - vwap) ** 2 * rth["volume"]).cumsum() / cum_v
    sd = np.sqrt(var)
    vwap_now = float(vwap.iloc[-1]); sd_now = float(sd.iloc[-1])
    px = float(rth["close"].iloc[-1])

    # opening range (first 30 min = 6 bars)
    orb = rth.iloc[:6]
    orh, orl = float(orb["high"].max()), float(orb["low"].min())
    # developing session H/L
    dh, dl = float(rth["high"].max()), float(rth["low"].min())
    # prior-day H/L/C
    prth = df[(df.index >= (cur - pd.Timedelta(days=1)).replace(hour=9, minute=30)) &
              (df.index < (cur - pd.Timedelta(days=1)).replace(hour=16))]
    # fall back to most recent prior RTH date if yesterday was a holiday/thin
    if len(prth) < 10:
        days = sorted({d for d in df.index.normalize().unique() if d < cur})
        for d in reversed(days):
            g = df[(df.index >= d.replace(hour=9, minute=30)) & (df.index < d.replace(hour=16))]
            if len(g) >= 10:
                prth = g; break
    pdh, pdl, pdc = float(prth["high"].max()), float(prth["low"].min()), float(prth["close"].iloc[-1])

    # regime on two clocks: whole session, and just the last hour (12x 5-min)
    regime, arrow, er, side = regime_of(rth["close"], vwap)
    W = 12
    if len(rth) >= W + 2:
        rc, rv = rth["close"].iloc[-W:], vwap.iloc[-W:]
        nregime, narrow, ner, nside = regime_of(rc, rv)
        vwap_slope = float(vwap.iloc[-1] - vwap.iloc[-W])   # VWAP drift over the hour
        recent_move = px - float(rth["close"].iloc[-W])
    else:
        nregime, narrow, ner, nside = regime, arrow, er, side
        vwap_slope = float(vwap.iloc[-1] - vwap.iloc[0])
        recent_move = px - float(rth["close"].iloc[0])
    shift = nregime != regime
    # what to actually trade off = the live (NOW) regime once enough bars exist
    live = nregime if len(rth) >= W + 2 else regime
    live_arrow = narrow if len(rth) >= W + 2 else arrow

    rn = round_numbers(px, round_step(px))

    print(f"NQ intraday engine — {now:%a %m-%d %H:%M} ET   price {px:.0f}")
    print(f"REGIME  session: {regime}  (er {er:.2f}, {side:.0%} bars>VWAP)   "
          f"NOW/last-1h: {nregime}  (er {ner:.2f}, {nside:.0%} bars>VWAP, "
          f"VWAP {'rising' if vwap_slope>0 else 'falling' if vwap_slope<0 else 'flat'} "
          f"{vwap_slope:+.0f}, {recent_move:+.0f} pt)")
    if shift:
        print(f"  ** REGIME SHIFT: session says {regime} but the last hour is {nregime} "
              f"-> trade the NOW read, the morning character is stale **")
    regime, arrow = live, live_arrow   # playbook below follows the live regime
    print(f"VWAP {vwap_now:.0f}  bands +-1sd [{vwap_now-sd_now:.0f} / {vwap_now+sd_now:.0f}]  "
          f"+-2sd [{vwap_now-2*sd_now:.0f} / {vwap_now+2*sd_now:.0f}]")
    print(f"opening range {orl:.0f}-{orh:.0f} | day {dl:.0f}-{dh:.0f} | PDH {pdh:.0f} PDL {pdl:.0f} PDC {pdc:.0f}")
    print(f"round #s near: {', '.join(f'{x:.0f}' for x in rn)}")
    print()
    print("PLAYBOOK:")
    if regime == "TREND UP":
        print(f"  Long-only. Ride it. Buy PULLBACKS to VWAP {vwap_now:.0f} or OR-high {orh:.0f} (now support)")
        print(f"  that hold with a bullish candle. Stop below the pullback low / VWAP-1sd {vwap_now-sd_now:.0f}.")
        tgts = [x for x in ([pdh] + rn + [vwap_now+2*sd_now]) if x > px]
        print(f"  Targets up: {', '.join(f'{t:.0f}' for t in sorted(tgts)[:4])}. Do NOT short / do NOT fade the highs.")
        print(f"  Invalidation: sustained close back BELOW VWAP {vwap_now:.0f}.")
    elif regime == "TREND DOWN":
        print(f"  Short-only. Sell RALLIES to VWAP {vwap_now:.0f} or OR-low {orl:.0f} (now resistance)")
        print(f"  that reject with a bearish candle. Stop above the rally high / VWAP+1sd {vwap_now+sd_now:.0f}.")
        tgts = [x for x in ([pdl] + rn + [vwap_now-2*sd_now]) if x < px]
        print(f"  Targets down: {', '.join(f'{t:.0f}' for t in sorted(tgts, reverse=True)[:4])}. Do NOT buy the dips.")
        print(f"  Invalidation: sustained close back ABOVE VWAP {vwap_now:.0f}.")
    else:
        print(f"  Two-sided fade. Short the +2sd band {vwap_now+2*sd_now:.0f} / day-high area, "
              f"long the -2sd band {vwap_now-2*sd_now:.0f} / day-low, both back to VWAP {vwap_now:.0f}.")
        print(f"  Need a rejection candle at the band. Stop just beyond the band. Overnight VAH/VAL fades OK here.")
        print(f"  Invalidation: acceptance outside the bands = regime flipping to trend, stand down.")


if __name__ == "__main__":
    main()
