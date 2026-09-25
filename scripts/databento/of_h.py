#!/usr/bin/env python3
"""OF-1..OF-4 on the Databento DISCOVERY ticks (provisional).

Implements reports/orderflow_h_preregistration.md (665c1e4) exactly. The holdout
is not loaded by this script (the tape adapter holds discovery sessions only).

IMPLEMENTATION CHOICES, fixed before this first ran (the pre-registration left
these mechanical details open):
  * feature minutes are ic_harness.features' 1-minute grid (bar label = minute
    start); the signal is known at the minute's close; entry = last trade price
    in that minute; exit = last trade price before entry time + 15 minutes.
  * eligible entry minutes: 10:00 <= minute start < 15:40 ET (first 30, last 20
    excluded); thresholds = 95th / 5th percentile of the feature over the same
    eligible minutes of the prior 10 sessions (the first 10 sessions are warm-up).
  * OF-3 uses the 5-minute sweep net share (C1) exactly as in the T15 port; the
    signal is known at the 5-minute bar's close.
  * OF-4: gap = first RTH print minus the prior trading day's last RTH print
    (consecutive trading days only); early share = signed / volume over
    09:30-10:00; entry = last print before 10:00; if price has already reached
    the prior close by then, no trade; ticks walked forward to the stop (30 pt)
    or the target (prior close), else exit at the last print before 16:00.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "step4"))
import tape_lib as TL                                              # noqa: E402
C = TL.C
import tape                                                        # noqa: E402
from ic_harness import features                                    # noqa: E402

COST = 2.0
HOLD = pd.Timedelta(minutes=15)
T_FIRST, T_LAST = 14 * 60, 19 * 60 + 40          # adapter clock: 10:00 and 15:40 ET
OUT = C.ROOT / "reports"


def eligible(idx):
    m = idx.hour * 60 + idx.minute
    return (m >= T_FIRST) & (m < T_LAST)


def last_before(tm, px, t):
    i = int(np.searchsorted(tm, np.datetime64(t), "left")) - 1
    return (px[i], i) if i >= 0 else (np.nan, -1)


def fade_trades(D, series, keys):
    """series[k] = pd.Series of the feature on eligible signal times (bar close
    time) for session k. Fade beyond prior-10-session 95th/5th percentiles."""
    rows = []
    for n, k in enumerate(keys):
        if n < 10:
            continue
        hist = pd.concat([series[j] for j in keys[n - 10:n]]).dropna()
        if len(hist) < 100:
            continue
        hi, lo = np.percentile(hist, 95), np.percentile(hist, 5)
        s = D[k]
        tm, px = s.time.to_numpy(), s.price.to_numpy()
        busy = None
        for t, v in series[k].dropna().items():
            if busy is not None and t < busy:
                continue
            if v > hi:
                side = -1
            elif v < lo:
                side = 1
            else:
                continue
            e, _ = last_before(tm, px, t)
            x, _ = last_before(tm, px, t + HOLD)
            if not (np.isfinite(e) and np.isfinite(x)):
                continue
            rows.append((k, side * (x - e)))
            busy = t + HOLD
    return rows


def of4(D, keys):
    rows = []
    for a, b in zip(keys, keys[1:]):
        if len(pd.bdate_range(a, b)) != 2:
            continue
        prev, s = D[a], D[b]
        pc, op = float(prev.price.iloc[-1]), float(s.price.iloc[0])
        gap = op - pc
        if abs(gap) < 10:
            continue
        up = gap < 0
        t10 = s.time.iloc[0].normalize() + pd.Timedelta(hours=14)
        early = s[s.time < t10]
        if early.volume.sum() == 0:
            continue
        share = early.signed.sum() / early.volume.sum()
        if np.sign(share) != (1 if up else -1):
            continue
        tm, px = s.time.to_numpy(), s.price.to_numpy()
        e, i = last_before(tm, px, t10)
        if i < 0 or (up and e >= pc) or (not up and e <= pc):
            continue
        stop, tgt = (e - 30.0, pc) if up else (e + 30.0, pc)
        t16 = t10 + pd.Timedelta(hours=6)
        out = None
        for j in range(i + 1, len(px)):
            if tm[j] >= np.datetime64(t16):
                break
            if (up and px[j] <= stop) or (not up and px[j] >= stop):
                out = -30.0
                break
            if (up and px[j] >= tgt) or (not up and px[j] <= tgt):
                out = abs(tgt - e)
                break
        if out is None:
            x, _ = last_before(tm, px, t16)
            out = (x - e) if up else (e - x)
        rows.append((b, out))
    return rows


def main():
    D = TL.days()
    keys = sorted(D)
    f1, f2, f3 = {}, {}, {}
    import g1_tape_e as E
    for k in keys:
        f = features(D[k])
        close_t = f.index + pd.Timedelta(minutes=1)
        el = eligible(f.index)
        f1[k] = pd.Series(f.vwap_disp.to_numpy()[el], index=close_t[el])
        f2[k] = pd.Series(f.cvd_share.to_numpy()[el], index=close_t[el])
        cf = E.c_features(k, D)
        t0 = tape.session_day(D[k]) + pd.Timedelta(hours=13, minutes=30)
        ct = t0 + (cf.index.to_numpy() + 1) * pd.Timedelta(minutes=5)
        ci = pd.DatetimeIndex(ct)
        el3 = eligible(ci - pd.Timedelta(minutes=5))
        f3[k] = pd.Series(cf.C1.to_numpy()[el3], index=ci[el3])
    res = {"OF-1 VWAP reversion": fade_trades(D, f1, keys),
           "OF-2 CVD reversion": fade_trades(D, f2, keys),
           "OF-3 sweep reversal": fade_trades(D, f3, keys),
           "OF-4 opening flow, gap days": of4(D, keys)}
    ev = {k: TL.cell_eval(v, COST, keys) for k, v in res.items()}
    raw = [ev[k]["p_one"] if np.isfinite(ev[k]["p_one"]) else 1.0 for k in ev]
    ph = C.holm(raw)
    L = ["OF-1..OF-4 -- DISCOVERY (PROVISIONAL; data-inspired; the holdout is not read)",
         f"sessions {len(keys)} (first 10 are warm-up for OF-1..3); cost {COST} pt round trip", ""]
    rows = []
    for (k, r), p in zip(ev.items(), ph):
        ok = bool(r["net_pts_mean"] > 0 and p <= 0.05)
        L.append(f"  {k:<28} {C.fmt(r)}  Holm p {p:.4f}  -> "
                 f"{'passes discovery (goes to the holdout read)' if ok else 'fails discovery'}")
        rows.append(dict(hypothesis=k, n=r["n"], net_pts=r["net_pts_mean"], sharpe=r["sharpe"],
                         dd_nq=r["dd_NQ"], dd_mnq=r["dd_MNQ"], t_daily=r["t"], p_holm=p, passes=ok))
    txt = "\n".join(L)
    print(txt)
    (OUT / "of_h_discovery_output.txt").write_text(txt)
    pd.DataFrame(rows).to_csv(OUT / "of_h_discovery_results.csv", index=False)


if __name__ == "__main__":
    main()
