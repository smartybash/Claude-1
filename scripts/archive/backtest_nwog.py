#!/usr/bin/env python3
"""New Week Opening Gap (NWOG) as a "draw on liquidity" — tested.

ICT/Dhesi claim: the weekend gap (Fri close -> Sun/Mon open) is a high-probability
magnet; price is drawn to FILL it, so an unfilled NWOG is a directional target.

Test on QQQ daily, 27y (data/qqq_daily_full.json). A "weekend/holiday gap" = the
open of the first session after a >=2-calendar-day break vs the prior close.
  * fill = price trades back to the prior close (gap up -> low <= prevclose;
    gap down -> high >= prevclose).
  * fill rate at horizons: same session, within 3, within 5 (the week).
  * "fade to fill" expectancy: at the gap open, target = prior close (the fill),
    stop = 1x the gap size beyond the open. R measured over the next 5 sessions.
  * gap size bucketed by % so we can see if big gaps (the ones ICT flags) behave
    differently from small noise gaps.

Usage: python3 scripts/backtest_nwog.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def load():
    d = json.load(open(ROOT / "data" / "qqq_daily_full.json"))
    rows = list(zip(d["time"], d["open"], d["high"], d["low"], d["close"]))
    out = []
    for t, o, h, l, c in rows:
        day = dt.date.fromisoformat(t[:10])
        out.append((day, float(o), float(h), float(l), float(c)))
    out.sort(key=lambda r: r[0])
    return out


def main():
    bars = load()
    gaps = []
    for i in range(1, len(bars)):
        (d0, *_p), (d1, o1, h1, l1, c1) = bars[i - 1], bars[i]
        prevclose = bars[i - 1][4]
        if (d1 - d0).days < 2:            # only gaps across a weekend/holiday break
            continue
        size = o1 - prevclose
        if abs(size) / prevclose < 0.0005:  # ignore ~flat opens (<0.05%)
            continue
        up = size > 0
        # fill search over next sessions (index i.. up to i+5)
        fill_h = None
        for k in range(0, 6):
            j = i + k
            if j >= len(bars):
                break
            hi, lo = bars[j][2], bars[j][3]
            filled = (lo <= prevclose) if up else (hi >= prevclose)
            if filled:
                fill_h = k
                break
        # fade-to-fill: enter at o1 toward prevclose, stop 1x gap beyond open
        s = -1 if up else 1               # gap up -> short toward fill
        entry = o1; target = prevclose
        stop = o1 + (1 if up else -1) * abs(size)   # 1x gap beyond the open
        risk = abs(entry - stop)
        r = None
        for k in range(0, 6):
            j = i + k
            if j >= len(bars):
                break
            hi, lo = bars[j][2], bars[j][3]
            hit_stop = (hi >= stop) if up else (lo <= stop)
            hit_tgt = (lo <= target) if up else (hi >= target)
            if hit_stop and hit_tgt:      # same-bar ambiguous -> assume stop (conservative)
                r = -1.0; break
            if hit_stop:
                r = -1.0; break
            if hit_tgt:
                r = abs(target - entry) / risk; break
        if r is None:
            r = s * (bars[min(i + 5, len(bars) - 1)][4] - entry) / risk
        gaps.append(dict(up=up, pct=abs(size) / prevclose * 100, fill_h=fill_h, r=r))

    n = len(gaps)
    def rate(cond):
        return 100 * np.mean([cond(g) for g in gaps])
    print(f"=== New Week Opening Gap fill — QQQ daily, {n} weekend/holiday gaps "
          f"({bars[0][0]}..{bars[-1][0]}) ===\n")
    print("FILL RATE (price returns to prior close):")
    for hz, lbl in ((0, "same session"), (2, "within 3 sessions"), (5, "within the week (5)")):
        print(f"   {lbl:22}: {rate(lambda g: g['fill_h'] is not None and g['fill_h'] <= hz):3.0f}%")
    print(f"   ever within 5           : {rate(lambda g: g['fill_h'] is not None):3.0f}%")

    print("\nby gap size:")
    for lo, hi, lbl in ((0, 0.5, "small <0.5%"), (0.5, 1.0, "0.5-1.0%"),
                        (1.0, 2.0, "1.0-2.0%"), (2.0, 99, "big >2.0%")):
        sub = [g for g in gaps if lo <= g["pct"] < hi]
        if not sub:
            continue
        fr = 100 * np.mean([g["fill_h"] is not None for g in sub])
        fr1 = 100 * np.mean([g["fill_h"] == 0 for g in sub])
        print(f"   {lbl:12} n={len(sub):4d}  fill same-day {fr1:3.0f}%  fill within week {fr:3.0f}%")

    r = np.array([g["r"] for g in gaps])
    sd = r.std(ddof=1)
    t = r.mean() / (sd / np.sqrt(len(r)))
    print(f"\nFADE-TO-FILL trade (enter gap open -> target prior close, stop 1x gap):")
    print(f"   n={len(r)}  win {100*(r>0).mean():.0f}%  mean {r.mean():+.3f}R  "
          f"total {r.sum():+.0f}R  t={t:+.2f}")
    big = np.array([g["r"] for g in gaps if g["pct"] >= 1.0])
    if len(big) > 20:
        tb = big.mean() / (big.std(ddof=1) / np.sqrt(len(big)))
        print(f"   big gaps >=1%: n={len(big)}  win {100*(big>0).mean():.0f}%  "
              f"mean {big.mean():+.3f}R  t={tb:+.2f}")


if __name__ == "__main__":
    main()
