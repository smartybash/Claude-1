#!/usr/bin/env python3
"""A+ v2 — why the expanded spec broke, and what actually survives.

backtest_aplus.py widened the validated VA fade in four ways at once and the
edge vanished. This isolates them. The validated trade (backtest_va_fade.py,
+0.334R / PF 2.20 / t=+3.80 over 139 days) is specifically:

    SHORT only, at prior-day VAH, on days that OPEN BELOW VAH,
    first rejection after 10:00, stop 0.25% above VAH, target prior-day POC.

Four things were changed. Each is switched back on here, one at a time:

  A  LEVEL      pdVAH only  ->  every fixed level
  B  SIDE       short only  ->  symmetric (long at lower levels too)
  C  OPEN LOC   must open on the approach side  ->  no condition
  D  STOP/TGT   fixed % beyond the level / prior-day POC
                            ->  trigger-bar extreme / developing POC

Everything keeps the validated conventions unless the test says otherwise, so
any drop is attributable to the single change being made.

Delta remains a PROXY on QQQ bars: ((close-open)/(high-low)) * volume. Any
result under a flow filter inherits that approximation.

Usage: python3 scripts/backtest_aplus2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import backtest_tos_fvg as F
from backtest_aplus import (build_levels, bar_delta, session_profile, summ,
                            COMPOSITE_N)

STOP_PCT = 0.0025      # validated convention: stop this far beyond the level
SKIP = "10:00"
REARM = 0.0015         # price must pull this far off the level to re-arm

UPPER = ("pdVAH", "pdHigh", "cVAH", "nPOCup")
LOWER = ("pdVAL", "pdLow", "cVAL", "nPOCdn")


def trade_at_level(b, L, side, target, cfg):
    """First rejection of level L after SKIP. side=-1 short, +1 long."""
    h, l, c = (b[x].values for x in ("high", "low", "close"))
    idx = b.index
    d = bar_delta(b)
    dv, cv, vol = d.values, d.cumsum().values, b["volume"].values
    n = len(b)
    tol = 0.0006 * L
    stop = L * (1 + STOP_PCT) if side < 0 else L * (1 - STOP_PCT)
    risk = abs(stop - L)
    if risk <= 0:
        return None
    if (side < 0 and target >= L) or (side > 0 and target <= L):
        return None
    attempts, armed = 0, True
    for i in range(n):
        if idx[i].strftime("%H:%M") < SKIP:
            continue
        if side < 0:
            if l[i] < L * (1 - REARM):
                armed = True
            tagged, rejected = h[i] >= L - tol, c[i] < L
        else:
            if h[i] > L * (1 + REARM):
                armed = True
            tagged, rejected = l[i] <= L + tol, c[i] > L
        if not (tagged and armed):
            continue
        attempts += 1
        armed = False
        if not rejected:
            continue
        if cfg.get("flow") and np.sign(cv[i]) != side:
            continue
        if cfg.get("bar_delta", 0) > 0:
            if vol[i] <= 0 or abs(dv[i]) / vol[i] < cfg["bar_delta"] \
               or np.sign(dv[i]) != side:
                continue
        rr = abs(L - target) / risk
        r = np.nan
        for j in range(i + 1, n):
            if side < 0:
                if h[j] >= stop:
                    r = -1.0; break
                if l[j] <= target:
                    r = rr; break
            else:
                if l[j] <= stop:
                    r = -1.0; break
                if h[j] >= target:
                    r = rr; break
        if not np.isfinite(r):
            r = ((L - c[n - 1]) if side < 0 else (c[n - 1] - L)) / risk
        return dict(r=r, rr=rr, attempt=attempts, ts=idx[i])
    return None


def run(sess, days, ibmap, cfg, label, levels_used, sides, open_cond):
    rows = []
    for i, d in enumerate(days):
        if i < COMPOSITE_N + 1:
            continue
        b = sess[d]
        op = float(b["open"].iloc[0])
        lv = build_levels(sess, days, i, op)
        if not lv or "pdPOC" not in lv:
            continue
        if cfg.get("wide_ib") and not ibmap.get(d, False):
            continue
        best = None
        for name in levels_used:
            if name not in lv:
                continue
            L = lv[name]
            side = -1 if name in UPPER else +1
            if side not in sides:
                continue
            if open_cond:
                if side < 0 and op > L:      # must open below an upper level
                    continue
                if side > 0 and op < L:      # must open above a lower level
                    continue
            t = trade_at_level(b, L, side, lv["pdPOC"], cfg)
            if t and (best is None or t["ts"] < best["ts"]):
                t.update(level=name, side=side, day=d)
                best = t
        if best:
            rows.append(best)
    T = pd.DataFrame(rows)
    nd = len(days) - COMPOSITE_N - 1
    print(f"{label:46s} {summ(T.r) if len(T) else 'n=0':52s} "
          f"{len(T)/nd*5:.1f}/wk")
    return T


def main():
    sess = F.load_sessions()
    days = sorted(sess)

    tr, prev_c = {}, None
    for d in days:
        b = sess[d]
        h, l, c = float(b.high.max()), float(b.low.min()), float(b.close.iloc[-1])
        tr[d] = max(h - l, abs(h - prev_c), abs(l - prev_c)) if prev_c else h - l
        prev_c = c
    atr = pd.Series(tr).rolling(14).mean()
    w = {}
    for d in days:
        b = sess[d]
        ib = b[b.index.strftime("%H:%M") < "10:00"]
        a = atr.get(d, np.nan)
        w[d] = ((float(ib.high.max()) - float(ib.low.min())) / a
                if len(ib) >= 4 and pd.notna(a) and a > 0 else np.nan)
    s = pd.Series(w)
    med = s.expanding(40).median().shift(1)
    ibmap = {d: bool(pd.notna(med[d]) and pd.notna(s[d]) and s[d] > med[d]) for d in days}

    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")
    print("stop = 0.25% beyond the level · target = prior-day POC · "
          "first rejection after 10:00\n")
    hdr = f"{'':46s} {'':52s} freq"
    print(hdr)
    print("-" * 108)

    base = dict(flow=False, bar_delta=0.0, wide_ib=False)

    print("BASELINE — the validated trade")
    run(sess, days, ibmap, base, "  pdVAH short, opens below VAH",
        ("pdVAH",), (-1,), True)

    print("\nCHANGE ONE THING AT A TIME")
    run(sess, days, ibmap, base, "  A  all upper levels (still short-only)",
        UPPER, (-1,), True)
    run(sess, days, ibmap, base, "  B  + long side at lower levels",
        UPPER + LOWER, (-1, 1), True)
    run(sess, days, ibmap, base, "  C  drop the open-location condition",
        ("pdVAH",), (-1,), False)

    print("\nLONG SIDE ALONE (the mirror of the validated trade)")
    run(sess, days, ibmap, base, "  pdVAL long, opens above VAL",
        ("pdVAL",), (1,), True)
    run(sess, days, ibmap, base, "  all lower levels, long-only",
        LOWER, (1,), True)

    print("\nEACH LEVEL ON ITS OWN (open-location enforced)")
    for nm in UPPER + LOWER:
        sd = -1 if nm in UPPER else 1
        run(sess, days, ibmap, base, f"  {nm}", (nm,), (sd,), True)

    print("\nBEST LEVEL SET + FILTERS")
    for lbl, cfg, lvs, sds in [
        ("  short-only, all upper levels", base, UPPER, (-1,)),
        ("  + wide IB", dict(base, wide_ib=True), UPPER, (-1,)),
        ("  + flow agrees (proxy)", dict(base, wide_ib=True, flow=True), UPPER, (-1,)),
        ("  + bar delta >=10%", dict(base, wide_ib=True, flow=True, bar_delta=0.10),
         UPPER, (-1,)),
    ]:
        run(sess, days, ibmap, cfg, lbl, lvs, sds, True)


if __name__ == "__main__":
    main()
