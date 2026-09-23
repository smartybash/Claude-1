#!/usr/bin/env python3
"""RP-008 Stage 1 -- regime validity. THE MARKET, NOT THE STRATEGIES.

Pre-registered at 4481bae (reports/rp008_stage1_preregistration.md), written and
committed before this script existed.

NO strategy P&L. NO strategy trade. NO conditional performance. NO allocator.
NO pairing. NO Monte Carlo. No strategy module is imported anywhere in this
file, and the NQ tape is never opened.

FROZEN, none varied here:
    instants     09:30 and 11:30 ET
    RV60         sd of 1-min log returns over the last 60 minutes of REGULAR
                 trading strictly before the instant (prior session 15:00-16:00
                 at the 09:30 instant)
    terciles     pooled over both instants, rolling causal 250-observation
                 history, boundaries at 33.3 / 66.7
    ATR1m        prior session's mean 1-minute true range
    horizon      60 minutes forward, classification bar excluded
    stops        {0.5, 1.0, 1.5, 2.0} x ATR1m
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RTH = ROOT / "data/intraday_long/QQQ_1m.parquet"
FOMC = ROOT / "data/events/fomc.csv"
OUT = ROOT / "reports"

INSTANTS = {"09:30": 0, "11:30": 120}          # minutes after the cash open
SECONDARY = {"10:00": 30, "14:00": 270}        # descriptive panel only
LOOKBACK = 60
HORIZON = 60
TERC_HIST = 250
TERC = (33.3, 66.7)
STOPS = (0.5, 1.0, 1.5, 2.0)
MIN_TO_CLOSE = {"09:30": 390, "11:30": 270, "10:00": 360, "14:00": 120}
LAB = ("LO", "NORMAL", "HI")


def load():
    d = pd.read_parquet(RTH, columns=["timestamp", "open", "high", "low",
                                      "close", "volume"])
    d["ts"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("ts").reset_index(drop=True)
    d["day"] = d.ts.dt.normalize()
    d["m"] = (d.ts.dt.hour * 60 + d.ts.dt.minute) - 570
    return d


def fomc_days():
    f = pd.read_csv(FOMC)
    return set(pd.to_datetime(f["date"]).dt.normalize())


def rv(c):
    """sd of 1-minute log returns, in bps. NaN below 10 returns."""
    if len(c) < 11:
        return np.nan
    r = np.diff(np.log(np.asarray(c, float)))
    return float(np.std(r) * 1e4)


def build():
    d = load()
    FOM = fomc_days()
    days = sorted(d.day.unique())
    byday = {k: g for k, g in d.groupby("day")}

    rows = []
    prev = None
    for day in days:
        g = byday[day]
        m = g["m"].to_numpy()
        H = g["high"].to_numpy(float)
        L = g["low"].to_numpy(float)
        C = g["close"].to_numpy(float)
        n = len(C)
        if n < 300 or prev is None:
            prev = (day, g)
            continue

        pg = prev[1]
        pm = pg["m"].to_numpy()
        pH, pL, pC = (pg["high"].to_numpy(float), pg["low"].to_numpy(float),
                      pg["close"].to_numpy(float))
        # causal volatility unit: prior session's mean 1-minute true range
        pc = np.concatenate([[pC[0]], pC[:-1]])
        atr = float(np.maximum(pH - pL, np.maximum(np.abs(pH - pc),
                                                   np.abs(pL - pc))).mean())
        if not np.isfinite(atr) or atr <= 0:
            prev = (day, g)
            continue
        # prior-session realised volatility, whole session (reported covariate)
        pd_rv = rv(pC)

        for lab, mm in {**INSTANTS, **SECONDARY}.items():
            i = int(np.searchsorted(m, mm, "left"))
            if i >= n - 2 or m[i] != mm:
                continue

            # ---- RV60: the last 60 minutes of REGULAR trading before `mm`
            if mm == 0:
                w = pC[pm >= 360]                      # prior 15:00-16:00
            else:
                w = C[(m >= mm - LOOKBACK) & (m < mm)]
            rv60 = rv(w)

            # ---- causal path efficiency to the instant (same session only)
            if mm == 0:
                eff_pre = np.nan
            else:
                seg = C[m <= mm]
                path = float(np.abs(np.diff(seg)).sum())
                eff_pre = (abs(float(seg[-1] - seg[0])) / path
                           if path > 0 else np.nan)

            # ---- causal session VWAP distance in ATR units
            if mm == 0:
                vw_d = np.nan
            else:
                sub = g[g["m"] <= mm]
                typ = (sub["high"] + sub["low"] + sub["close"]) / 3.0
                vol = sub["volume"].to_numpy(float)
                vw = (float((typ.to_numpy(float) * vol).sum() / vol.sum())
                      if vol.sum() > 0 else np.nan)
                vw_d = abs(float(C[i]) - vw) / atr if np.isfinite(vw) else np.nan

            # ---- FORWARD window: strictly after the classification bar
            j0, j1 = i + 1, min(i + 1 + HORIZON, n)
            if j1 - j0 < HORIZON // 2:
                continue
            fH, fL, fC = H[j0:j1], L[j0:j1], C[j0:j1]
            p0 = float(C[i])
            f_rv = rv(np.concatenate([[p0], fC]))
            f_rng = float(fH.max() - fL.min()) / atr
            f_mfe = float(fH.max() - p0) / atr
            f_mae = float(p0 - fL.min()) / atr
            seg = np.concatenate([[p0], fC])
            path = float(np.abs(np.diff(seg)).sum())
            f_eff = abs(float(seg[-1] - seg[0])) / path if path > 0 else np.nan

            r = dict(day=day, year=day.year, instant=lab, rv60=rv60,
                     atr=atr, pd_rv=pd_rv, eff_pre=eff_pre, vwap_d=vw_d,
                     fomc=int(day in FOM), to_close=MIN_TO_CLOSE[lab],
                     f_rv=f_rv, f_rng=f_rng, f_mfe=f_mfe, f_mae=f_mae,
                     f_eff=f_eff, bars=j1 - j0)
            for s in STOPS:
                r[f"dn{s}"] = bool(f_mae >= s)
                r[f"up{s}"] = bool(f_mfe >= s)
                r[f"ei{s}"] = bool(f_mae >= s or f_mfe >= s)
            rows.append(r)
        prev = (day, g)

    R = pd.DataFrame(rows).sort_values(["day", "instant"]).reset_index(drop=True)

    # ---- pooled rolling causal terciles over the PRIMARY instants only
    P = R[R.instant.isin(INSTANTS)].sort_values(["day", "instant"]).copy()
    v = P["rv60"].to_numpy(float)
    lab = np.array([None] * len(v), dtype=object)
    for k in range(len(v)):
        if k < TERC_HIST or not np.isfinite(v[k]):
            continue
        h = v[max(0, k - TERC_HIST):k]
        h = h[np.isfinite(h)]
        if len(h) < TERC_HIST // 2:
            continue
        lo, hi = np.percentile(h, TERC)
        lab[k] = "LO" if v[k] < lo else ("HI" if v[k] > hi else "NORMAL")
    P["vol"] = lab
    P["state"] = [f"{a} {b}" if b else None
                  for a, b in zip(P.instant, P.vol)]

    # BLOCK-RELATIVE terciles. Added at the COUNTS stage, before any forward
    # outcome was computed, because the pooled cell balance shows the two
    # instants do not draw from the same RV60 distribution -- the 09:30 instant
    # reads the prior session's closing hour and the 11:30 instant reads the
    # same session's 10:30-11:30. Pooled labels therefore partly encode WHICH
    # instant, which is the confound the pre-registration named. This variant
    # ranks each instant against its own history, so "HI" means high for that
    # time of day. It is a declared diagnostic, not a replacement: the pooled
    # labels remain the frozen primary.
    P["volrel"] = None
    for inst in INSTANTS:
        idx = np.flatnonzero((P.instant == inst).to_numpy())
        vv = P["rv60"].to_numpy(float)[idx]
        lb = np.array([None] * len(idx), dtype=object)
        for k in range(len(idx)):
            if k < TERC_HIST // 2 or not np.isfinite(vv[k]):
                continue
            h = vv[max(0, k - TERC_HIST):k]
            h = h[np.isfinite(h)]
            if len(h) < TERC_HIST // 4:
                continue
            lo, hi = np.percentile(h, TERC)
            lb[k] = "LO" if vv[k] < lo else ("HI" if vv[k] > hi else "NORMAL")
        P.iloc[idx, P.columns.get_loc("volrel")] = lb

    # neighbouring-threshold variants, for the robustness check only
    for name, cut in (("t3070", (30.0, 70.0)), ("t4060", (40.0, 60.0))):
        lb = np.array([None] * len(v), dtype=object)
        for k in range(len(v)):
            if k < TERC_HIST or not np.isfinite(v[k]):
                continue
            h = v[max(0, k - TERC_HIST):k]
            h = h[np.isfinite(h)]
            if len(h) < TERC_HIST // 2:
                continue
            lo, hi = np.percentile(h, cut)
            lb[k] = "LO" if v[k] < lo else ("HI" if v[k] > hi else "NORMAL")
        P[name] = lb
    return R, P


def overlap(a, b, lo=None, hi=None, nb=60):
    """Overlap coefficient of two samples: sum of min of the two histograms."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 20 or len(b) < 20:
        return np.nan
    lo = min(a.min(), b.min()) if lo is None else lo
    hi = max(np.percentile(a, 99.5), np.percentile(b, 99.5)) if hi is None else hi
    e = np.linspace(lo, hi, nb + 1)
    ha, _ = np.histogram(a, bins=e)
    hb, _ = np.histogram(b, bins=e)
    ha = ha / max(len(a), 1)
    hb = hb / max(len(b), 1)
    return float(np.minimum(ha, hb).sum())


if __name__ == "__main__":
    R, P = build()
    R.to_parquet(OUT / "rp008_stage1_obs.parquet")
    P.to_parquet(OUT / "rp008_stage1_states.parquet")
    print("observations", R.shape, "primary", P.shape,
          "labelled", int(P["vol"].notna().sum()))
    print(P.groupby(["instant", "vol"], dropna=True).size().to_string())
