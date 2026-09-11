#!/usr/bin/env python3
"""A+ SETUP — the fixed-level fade, tested end to end.

The spec under test (nothing here is a developing level; every price the trade
keys off is known before 09:30):

  LEVELS  prior-day VAH / POC / VAL, prior-day High / Low,
          composite VAH / POC / VAL (20 sessions), nearest naked POC above/below
  TRIGGER one 5-min bar that pokes THROUGH a level and CLOSES BACK on the
          original side (short if it pokes above and closes below, long if it
          pokes below and closes above)
  ENTRY   that bar's close
  STOP    that bar's extreme + buffer   (the structural invalidation)
  TARGET  (a) the session's DEVELOPING POC as at entry, or
          (b) the next fixed level in the trade's direction
  ONE trade per day: the first trigger that passes every active filter.

Filters are added cumulatively so each one's contribution is visible:
  WINDOW      only trigger inside a time window
  WIDE IB     Initial-Balance range / ATR14 above its running median
              (the only regime dial that survived earlier testing)
  FLOW        session cumulative delta agrees with the trade direction
  BAR DELTA   trigger bar's own delta opposes the poke, >=X% of its volume
  RR          target must be >= X times the stop distance

DELTA IS A PROXY.  QQQ 5-min bars carry no aggressor tag, so per-bar delta is
estimated as ((close-open)/(high-low)) * volume and accumulated for the session.
It correlates with true CVD but is NOT the same series; every number produced
under the FLOW / BAR DELTA filters inherits that approximation. Real order-flow
confirmation can only be validated on aggressor-tagged tick data.

Usage: python3 scripts/backtest_aplus.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from sweeplib.levels import volume_profile
import backtest_tos_fvg as F

POKE_TOL = 0.0002     # a "poke" must clear the level by >= 0.02%
CLOSE_TOL = 0.0002    # and close back by >= 0.02% (not a doji straddling it)
STOP_BUF = 0.0004     # stop sits this far beyond the trigger bar's extreme
COMPOSITE_N = 20      # sessions in the composite profile
LEVEL_TOL = 0.0015    # levels closer together than this are deduped


# ------------------------------- levels --------------------------------------
def session_profile(bars):
    p = volume_profile(bars, 50)
    if not p:
        return None
    poc, vah, val = p
    return (poc, vah, val) if val < poc < vah else None


def naked_pocs(sess, days, i):
    """POCs of earlier sessions that no later session has traded through."""
    out = []
    for j in range(max(0, i - 60), i):
        p = session_profile(sess[days[j]])
        if not p:
            continue
        poc = p[0]
        touched = False
        for k in range(j + 1, i):
            b = sess[days[k]]
            if float(b["low"].min()) <= poc <= float(b["high"].max()):
                touched = True
                break
        if not touched:
            out.append(poc)
    return out


def build_levels(sess, days, i, open_px):
    """Every fixed price for day i, all computed from sessions < i."""
    if i < COMPOSITE_N + 1:
        return {}
    lv = {}
    prev = sess[days[i - 1]]
    p = session_profile(prev)
    if not p:
        return {}
    lv["pdPOC"], lv["pdVAH"], lv["pdVAL"] = p
    lv["pdHigh"] = float(prev["high"].max())
    lv["pdLow"] = float(prev["low"].min())

    comp = pd.concat([sess[days[j]] for j in range(i - COMPOSITE_N, i)])
    c = session_profile(comp)
    if c:
        lv["cPOC"], lv["cVAH"], lv["cVAL"] = c

    nk = naked_pocs(sess, days, i)
    above = [x for x in nk if x > open_px]
    below = [x for x in nk if x < open_px]
    if above:
        lv["nPOCup"] = min(above)
    if below:
        lv["nPOCdn"] = max(below)
    return lv


# ------------------------------- flow proxy ----------------------------------
def bar_delta(b):
    rng = (b["high"] - b["low"]).replace(0, np.nan)
    d = ((b["close"] - b["open"]) / rng) * b["volume"]
    return d.fillna(0.0)


# ------------------------------- simulation ----------------------------------
def developing_poc(bars_so_far):
    p = volume_profile(bars_so_far, 40)
    return p[0] if p else None


def next_level(levels, price, direction):
    """Nearest fixed level in the direction of travel."""
    if direction < 0:
        c = [v for v in levels.values() if v < price]
        return max(c) if c else None
    c = [v for v in levels.values() if v > price]
    return min(c) if c else None


def simulate_day(b, levels, cfg, ib_ok):
    """Return the first qualifying trade of the day, or None."""
    if not levels:
        return None
    d = bar_delta(b)
    cum = d.cumsum()
    idx = b.index
    hi, lo, cl, op, vol = (b[x].values for x in ("high", "low", "close", "open", "volume"))
    dv, cv = d.values, cum.values
    n = len(b)
    t0, t1 = cfg["win"]

    for i in range(2, n):
        hhmm = idx[i].strftime("%H:%M")
        if hhmm < t0 or hhmm > t1:
            continue
        if cfg["wide_ib"] and not ib_ok:
            continue
        for name, L in levels.items():
            pk, ct = POKE_TOL * L, CLOSE_TOL * L
            if hi[i] >= L + pk and cl[i] <= L - ct:
                side = -1                      # poked above, closed back below
            elif lo[i] <= L - pk and cl[i] >= L + ct:
                side = +1
            else:
                continue

            if cfg["flow"] and np.sign(cv[i]) != side:
                continue
            if cfg["bar_delta"] > 0:
                if vol[i] <= 0 or abs(dv[i]) / vol[i] < cfg["bar_delta"]:
                    continue
                if np.sign(dv[i]) != side:
                    continue

            entry = cl[i]
            stop = (hi[i] * (1 + STOP_BUF)) if side < 0 else (lo[i] * (1 - STOP_BUF))
            risk = abs(stop - entry)
            if risk <= 0:
                continue

            tgt_poc = developing_poc(b.iloc[: i + 1])
            tgt_lev = next_level(levels, entry, side)
            targets = {"poc": tgt_poc, "lev": tgt_lev}
            out = {}
            ok_any = False
            for tname, T in targets.items():
                if T is None or (side < 0 and T >= entry) or (side > 0 and T <= entry):
                    out[f"r_{tname}"] = np.nan
                    continue
                rr = abs(entry - T) / risk
                if rr < cfg["min_rr"]:
                    out[f"r_{tname}"] = np.nan
                    continue
                ok_any = True
                r = np.nan
                for j in range(i + 1, n):
                    if side < 0:
                        if hi[j] >= stop:
                            r = -1.0; break
                        if lo[j] <= T:
                            r = rr; break
                    else:
                        if lo[j] <= stop:
                            r = -1.0; break
                        if hi[j] >= T:
                            r = rr; break
                if not np.isfinite(r):
                    r = (entry - cl[n - 1]) / risk * side * side if side < 0 else 0.0
                    r = ((entry - cl[n - 1]) if side < 0 else (cl[n - 1] - entry)) / risk
                out[f"r_{tname}"] = r
                out[f"rr_{tname}"] = rr
            if not ok_any:
                continue
            out.update(level=name, side=side, ts=idx[i], entry=entry, risk_pct=risk / entry)
            return out
    return None


# ------------------------------- stats ---------------------------------------
def summ(a):
    a = np.array([x for x in a if np.isfinite(x)], float)
    if len(a) == 0:
        return "n=0"
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    t = a.mean() / (sd / np.sqrt(len(a))) if sd > 0 else 0.0
    w, l = a[a > 0].sum(), -a[a < 0].sum()
    pf = w / l if l > 0 else float("inf")
    return (f"n={len(a):4d}  win {100*(a>0).mean():3.0f}%  mean {a.mean():+.3f}R  "
            f"PF {pf:4.2f}  t={t:+5.2f}")


def run(sess, days, ibmap, cfg, label):
    rows = []
    for i, d in enumerate(days):
        b = sess[d]
        lv = build_levels(sess, days, i, float(b["open"].iloc[0]))
        r = simulate_day(b, lv, cfg, ibmap.get(d, False))
        if r:
            r["day"] = d
            rows.append(r)
    T = pd.DataFrame(rows)
    n_days = len(days) - COMPOSITE_N - 1
    freq = len(T) / n_days * 5 if n_days else 0
    print(f"\n{label}")
    print(f"  signals {len(T):4d} over {n_days} sessions   "
          f"= {len(T)/n_days*100:.0f}% of days  ({freq:.1f} per week)")
    if len(T):
        print(f"  target = developing POC : {summ(T.r_poc)}")
        print(f"  target = next fixed lvl : {summ(T.r_lev)}")
    return T


def main():
    sess = F.load_sessions()
    days = sorted(sess)
    print(f"QQQ 5-min RTH — {len(days)} sessions, {days[0].date()} to {days[-1].date()}")

    # --- Initial Balance width vs ATR14, and whether it is above running median
    tr, ibw = {}, {}
    prev_c = None
    for d in days:
        b = sess[d]
        h, l, c = float(b.high.max()), float(b.low.min()), float(b.close.iloc[-1])
        tr[d] = max(h - l, abs(h - prev_c), abs(l - prev_c)) if prev_c else h - l
        prev_c = c
    atr = pd.Series(tr).rolling(14).mean()
    for ib_end, tag in ((("10:00"), "ib30"), (("10:30"), "ib60")):
        for d in days:
            b = sess[d]
            ib = b[b.index.strftime("%H:%M") < ib_end]
            a = atr.get(d, np.nan)
            ibw[(tag, d)] = ((float(ib.high.max()) - float(ib.low.min())) / a
                             if len(ib) >= 4 and pd.notna(a) and a > 0 else np.nan)
    ibmap = {}
    for tag in ("ib30", "ib60"):
        s = pd.Series({d: ibw[(tag, d)] for d in days})
        med = s.expanding(40).median().shift(1)      # no lookahead
        ibmap[tag] = {d: bool(s[d] > med[d]) if pd.notna(med[d]) and pd.notna(s[d])
                      else False for d in days}

    base = dict(win=("10:00", "11:30"), wide_ib=False, flow=False,
                bar_delta=0.0, min_rr=0.0)

    print("\n" + "=" * 78)
    print("CUMULATIVE FILTERS — window 10:00-11:30, IB measured 09:30-10:00")
    print("=" * 78)
    steps = [
        ("1  all day, no filters        ", dict(base, win=("09:30", "15:55")), "ib30"),
        ("2  + window 10:00-11:30       ", dict(base), "ib30"),
        ("3  + wide IB                  ", dict(base, wide_ib=True), "ib30"),
        ("4  + flow agrees (proxy CVD)  ", dict(base, wide_ib=True, flow=True), "ib30"),
        ("5  + bar delta >=10% vs poke  ", dict(base, wide_ib=True, flow=True,
                                               bar_delta=0.10), "ib30"),
        ("6  + R:R >= 2.0               ", dict(base, wide_ib=True, flow=True,
                                               bar_delta=0.10, min_rr=2.0), "ib30"),
    ]
    last = None
    for label, cfg, tag in steps:
        last = run(sess, days, ibmap[tag], cfg, label)

    print("\n" + "=" * 78)
    print("FULL-HOUR IB (09:30-10:30), window 10:30-12:00")
    print("=" * 78)
    b2 = dict(base, win=("10:30", "12:00"))
    run(sess, days, ibmap["ib60"], dict(b2, wide_ib=True), "   wide IB only          ")
    T60 = run(sess, days, ibmap["ib60"], dict(b2, wide_ib=True, flow=True,
                                              bar_delta=0.10, min_rr=2.0),
              "   full A+ spec          ")

    print("\n" + "=" * 78)
    print("WHICH LEVELS CARRY THE EDGE  (step 4: window + wide IB + flow)")
    print("=" * 78)
    T = run(sess, days, ibmap["ib30"], dict(base, wide_ib=True, flow=True),
            "   (regenerating)        ")
    if len(T):
        for lv, g in T.groupby("level"):
            print(f"  {lv:9s} {summ(g.r_poc)}")
        print("\n  by side:")
        for s, g in T.groupby("side"):
            print(f"  {'short' if s < 0 else 'long ':9s} {summ(g.r_poc)}")

    out = ROOT / "reports" / "aplus_backtest.txt"
    out.parent.mkdir(exist_ok=True)
    print(f"\n(write-up: {out})")


if __name__ == "__main__":
    main()
