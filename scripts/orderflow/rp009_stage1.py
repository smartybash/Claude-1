#!/usr/bin/env python3
"""RP-009 Stage 1 -- time-of-day opportunity map. BARRIER GEOMETRY ONLY.

Pre-registered at 04d8d4b (reports/rp009_stage1_proposal.md).

NO strategy P&L. No expectancy, profit factor, win rate, drawdown, allocator,
entry pattern, directional rule or prop-evaluation simulation. No strategy
module is imported. Sealed NQ dates are never read; 2016-2020 is never opened.

QQQ is the PRIMARY long-sample evidence. NQ (44 full 0.25 sessions) is
EXPLORATORY instrument-native confirmation and tick-order calibration only;
it cannot support a standalone commercial verdict, and QQQ cannot validate an
MNQ strategy.

FROZEN:
    timestamps  09:30 09:45 10:00 10:30 11:00 11:30 12:00 12:30 13:00 13:30
                14:00 14:30 15:00 15:30 ET
    horizons    15 30 60 120 minutes, and hold-to-cash-close
    containers  10 / 20 / 30 NQ points  and  0.5 / 1.0 / 1.5 x ATR1m
    multiples   1.0R 1.5R 2.0R
    cost        NQ 2.0 points round turn = 0.68 bps at the measured 29,460
    convention  both barriers in one bar -> ADVERSE first; ambiguity reported
    entry       close of the timestamp bar; path starts on the NEXT bar
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports"
QQQ = ROOT / "data/intraday_long/QQQ_1m.parquet"

TS = [("09:30", 0, "open"), ("09:45", 15, "open"),
      ("10:00", 30, "morning"), ("10:30", 60, "morning"),
      ("11:00", 90, "morning"),
      ("11:30", 120, "midday"), ("12:00", 150, "midday"),
      ("12:30", 180, "midday"), ("13:00", 210, "midday"),
      ("13:30", 240, "midday"),
      ("14:00", 270, "close"), ("14:30", 300, "close"),
      ("15:00", 330, "close"), ("15:30", 360, "close")]
HZ = [15, 30, 60, 120]
EXC = (0.5, 1.0, 1.5, 2.0)
MULT = (1.0, 1.5, 2.0)
NQ_PX = 29460.0                    # measured mean over the 44 fine sessions
NQ_COST_PTS = 2.0
COST_BPS = 1e4 * NQ_COST_PTS / NQ_PX          # 0.679 bps
FIXED_PTS = (10.0, 20.0, 30.0)
FIXED_BPS = tuple(1e4 * p / NQ_PX for p in FIXED_PTS)
ATR_MULT = (0.5, 1.0, 1.5)


def containers(atr_bps):
    """(label, kind, size in bps) for one session's ATR expressed in bps."""
    out = [(f"{int(p)}NQpt", "fixed", b) for p, b in zip(FIXED_PTS, FIXED_BPS)]
    out += [(f"{m}ATR", "atr", m * atr_bps) for m in ATR_MULT]
    return out


def first_true(a):
    """Index of the first True, or -1."""
    j = int(np.argmax(a)) if a.any() else -1
    return j


def walk(H, L, p0, stop_d, tgt_d, direction):
    """First-barrier resolution under the ADVERSE-FIRST convention.

    Returns (outcome, bar, ambiguous) where outcome is +1 target, -1 stop,
    0 unresolved; bar is the resolving bar index within the forward slice.
    """
    if direction > 0:
        hit_s = L <= p0 - stop_d
        hit_t = H >= p0 + tgt_d
    else:
        hit_s = H >= p0 + stop_d
        hit_t = L <= p0 - tgt_d
    js, jt = first_true(hit_s), first_true(hit_t)
    if js < 0 and jt < 0:
        return 0, -1, False
    if js < 0:
        return 1, jt, False
    if jt < 0:
        return -1, js, False
    if js == jt:
        return -1, js, True              # adverse first, flagged
    return (-1, js, False) if js < jt else (1, jt, False)


def session_rows(day, yr, m, H, L, C, atr_px, px, inst_tag):
    """Excursion and barrier rows for one session. No P&L anywhere."""
    exc_rows, bar_rows = [], []
    n = len(C)
    atr_bps = 1e4 * atr_px / px
    for lab, mm, blk in TS:
        i = int(np.searchsorted(m, mm, "left"))
        if i >= n - 1 or m[i] != mm:
            continue
        p0 = float(C[i])
        fH, fL = H[i + 1:], L[i + 1:]
        avail = len(fH)
        if avail < 1:
            continue
        # ---------- excursion, per horizon (no truncation substitution)
        for h in HZ + ["close"]:
            if h == "close":
                k, hl = avail, "close"
            else:
                if avail < h:
                    exc_rows.append(dict(day=day, yr=yr, ts=lab, blk=blk,
                                         hz=str(h), avail=avail, ok=False))
                    continue
                k, hl = h, str(h)
            sH, sL = fH[:k], fL[:k]
            up = 1e4 * (sH.max() - p0) / p0
            dn = 1e4 * (p0 - sL.min()) / p0
            exc_rows.append(dict(
                day=day, yr=yr, ts=lab, blk=blk, hz=hl, avail=avail, ok=True,
                atr_bps=atr_bps,
                L_mfe=up, L_mae=dn, S_mfe=dn, S_mae=up,
                L_mfe_a=up / atr_bps, L_mae_a=dn / atr_bps,
                S_mfe_a=dn / atr_bps, S_mae_a=up / atr_bps))
        # ---------- time to excursion, to the cash close
        for e in EXC:
            d = e * atr_bps * p0 / 1e4
            ju = first_true(fH >= p0 + d)
            jd = first_true(fL <= p0 - d)
            exc_rows.append(dict(day=day, yr=yr, ts=lab, blk=blk,
                                 hz=f"exc{e}", avail=avail, ok=True,
                                 atr_bps=atr_bps,
                                 t_up=(ju + 1) if ju >= 0 else np.nan,
                                 t_dn=(jd + 1) if jd >= 0 else np.nan,
                                 up_first=(ju >= 0 and (jd < 0 or ju < jd)),
                                 dn_first=(jd >= 0 and (ju < 0 or jd < ju)),
                                 up_any=ju >= 0, dn_any=jd >= 0))
        # ---------- barrier geometry
        for clab, kind, size_bps in containers(atr_bps):
            R = size_bps * p0 / 1e4
            cost_pct_risk = 100.0 * COST_BPS / size_bps
            for M in MULT:
                for dcode, dname in ((1, "long"), (-1, "short")):
                    o, j, amb = walk(fH, fL, p0, R, M * R, dcode)
                    bar_rows.append(dict(
                        day=day, yr=yr, ts=lab, blk=blk, cont=clab, kind=kind,
                        M=M, dir=dname, out=o, bar=(j + 1) if j >= 0 else -1,
                        amb=amb, risk_bps=size_bps, cost_pct=cost_pct_risk,
                        avail=avail))
    return exc_rows, bar_rows


def qqq():
    d = pd.read_parquet(QQQ, columns=["timestamp", "high", "low", "close"])
    d["ts"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("ts").reset_index(drop=True)
    d["day"] = d.ts.dt.normalize()
    d["m"] = (d.ts.dt.hour * 60 + d.ts.dt.minute) - 570
    days = sorted(d.day.unique())
    byday = {k: g for k, g in d.groupby("day")}
    E, B = [], []
    prev = None
    skipped = dict(short=0, no_prior=0)
    for k, day in enumerate(days):
        g = byday[day]
        if len(g) < 300:
            skipped["short"] += 1
            prev = (day, g)
            continue
        if prev is None:
            skipped["no_prior"] += 1
            prev = (day, g)
            continue
        pg = prev[1]
        pH, pL, pC = (pg["high"].to_numpy(float), pg["low"].to_numpy(float),
                      pg["close"].to_numpy(float))
        pc = np.concatenate([[pC[0]], pC[:-1]])
        atr = float(np.maximum(pH - pL, np.maximum(np.abs(pH - pc),
                                                   np.abs(pL - pc))).mean())
        if not np.isfinite(atr) or atr <= 0:
            skipped["no_prior"] += 1
            prev = (day, g)
            continue
        e, b = session_rows(day, day.year, g["m"].to_numpy(),
                            g["high"].to_numpy(float), g["low"].to_numpy(float),
                            g["close"].to_numpy(float), atr,
                            float(g["close"].mean()), "QQQ")
        E += e
        B += b
        if k % 300 == 0:
            print(f"  QQQ {k}/{len(days)} rows={len(E)}", flush=True)
        prev = (day, g)
    return pd.DataFrame(E), pd.DataFrame(B), skipped, len(days)


def nq():
    """44 full NQ sessions at 0.25, plus exact tick-order calibration."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from tape import load_all, price_step, rth, is_full_session   # noqa

    days = load_all()
    keep = [(d, x) for d, x in sorted(days.items())
            if price_step(x) <= 1 and is_full_session(x)]
    E, B, TK = [], [], []
    prev_atr = None
    for idx, (d, x) in enumerate(keep):
        s = rth(x).sort_values("time")
        t = s["time"].to_numpy()
        px = s["price"].to_numpy(float)
        bars = (s.set_index("time")["price"]
                .resample("1min").agg(["max", "min", "last"]).dropna())
        bars.columns = ["high", "low", "close"]
        # DEFECT FIXED BEFORE READING THE NQ ARM: the recorder writes the ATAS
        # platform clock, which is UTC. The cash open is 13:30 UTC, not 09:30,
        # so minutes-after-open is (h*60+m) - 810 here and - 570 on QQQ. The
        # first run labelled every NQ timestamp four hours late.
        mm = (bars.index.hour * 60 + bars.index.minute).to_numpy() - 810
        H = bars["high"].to_numpy(float)
        L = bars["low"].to_numpy(float)
        C = bars["close"].to_numpy(float)
        pc = np.concatenate([[C[0]], C[:-1]])
        atr = float(np.maximum(H - L, np.maximum(np.abs(H - pc),
                                                 np.abs(L - pc))).mean())
        use_atr = prev_atr if prev_atr is not None else atr
        prev_atr = atr
        day = pd.Timestamp(str(d)[:4] + "-" + str(d)[4:6] + "-" + str(d)[6:])
        e, b = session_rows(day, day.year, mm, H, L, C, use_atr,
                            float(C.mean()), "NQ")
        E += e
        B += b
        # ---- tick-order calibration: exact first barrier from the tape
        mt = ((pd.DatetimeIndex(t).hour * 60
               + pd.DatetimeIndex(t).minute).to_numpy() - 810)
        atr_bps = 1e4 * use_atr / float(C.mean())
        for lab, mmv, blk in TS:
            i = int(np.searchsorted(mm, mmv, "left"))
            if i >= len(C) - 1 or mm[i] != mmv:
                continue
            p0 = float(C[i])
            tick_mask = mt > mmv
            tp = px[tick_mask]
            if len(tp) < 10:
                continue
            fH, fL = H[i + 1:], L[i + 1:]
            for clab, kind, size_bps in containers(atr_bps):
                R = size_bps * p0 / 1e4
                for M in MULT:
                    for dcode, dname in ((1, "long"), (-1, "short")):
                        ob, jb, ab = walk(fH, fL, p0, R, M * R, dcode)
                        if dcode > 0:
                            js = first_true(tp <= p0 - R)
                            jt = first_true(tp >= p0 + M * R)
                        else:
                            js = first_true(tp >= p0 + R)
                            jt = first_true(tp <= p0 - M * R)
                        if js < 0 and jt < 0:
                            ot = 0
                        elif js < 0:
                            ot = 1
                        elif jt < 0:
                            ot = -1
                        else:
                            ot = -1 if js < jt else 1
                        TK.append(dict(day=day, ts=lab, blk=blk, cont=clab,
                                       M=M, dir=dname, bar_out=ob,
                                       tick_out=ot, amb=ab))
        print(f"  NQ {idx+1}/{len(keep)} {d}", flush=True)
    return pd.DataFrame(E), pd.DataFrame(B), pd.DataFrame(TK), len(keep)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("qqq", "both"):
        E, B, sk, nd = qqq()
        E.to_parquet(OUT / "rp009_qqq_exc.parquet")
        B.to_parquet(OUT / "rp009_qqq_bar.parquet")
        print("QQQ exc", E.shape, "bar", B.shape, "skipped", sk,
              "calendar days", nd)
    if which in ("nq", "both"):
        E, B, T, nn = nq()
        E.to_parquet(OUT / "rp009_nq_exc.parquet")
        B.to_parquet(OUT / "rp009_nq_bar.parquet")
        T.to_parquet(OUT / "rp009_nq_tick.parquet")
        print("NQ sessions", nn, "exc", E.shape, "bar", B.shape,
              "tick", T.shape)
