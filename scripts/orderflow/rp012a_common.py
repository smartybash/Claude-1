#!/usr/bin/env python3
"""RP-012A shared construction -- ONE loader, ONE window builder, ONE feature
builder, used by Stage 0 and by any future Stage 1. Nothing here computes a
forward return.

Intraday relative volume and price-impact persistence on liquid ETFs.
Proposal: reports/rp012a_stage0.md.

Every constant below is FROZEN at Stage 0. None may be changed after a forward
outcome is viewed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import dataquality as DQ                                            # noqa: E402
import sessioncal as SC                                             # noqa: E402

# ------------------------------------------------------------- instruments --
INSTR = ("QQQ", "SPY", "IWM", "IJH", "EFA")
PATH = {"QQQ": ROOT / "data/intraday_long/QQQ_1m.parquet",
        **{s: ROOT / f"data/related/{s}_1m.parquet"
           for s in ("SPY", "IWM", "IJH", "EFA")}}

# ------------------------------------------------------------- data roles ---
# Every period below has been READ by earlier families (IB 1R, ORB-Fib and IB
# pullback on the related instruments over 2021-2025; RP-005 validation on
# QQQ 2024-2025; dozens of QQQ-wide scripts with no date filter). NONE has had
# an RP-012A outcome inspected. None is pristine.
DISCOVERY = ("2021-01-04", "2023-12-29")
INTERNAL_VALIDATION = ("2024-01-02", "2025-12-31")
# secondary validation: 2026 data -- NEWLY ACQUIRED for SPY/IWM/IJH/EFA (not on
# disk, never read); QQQ 2026-01..08 is on disk and EXAMINED. Final untouched
# OOS: NQ 1-minute acquired or forward-recorded after the full freeze.

# ------------------------------------------------------------- construction -
BAR_MIN = 1
WIN_MIN = 5                       # non-overlapping five-minute windows
FIRST_MIN = 5                     # exclude 09:30-09:35
LAST_MIN = 380                    # exclude 15:50-16:00; last window 15:45-15:50
N_WIN = (LAST_MIN - FIRST_MIN) // WIN_MIN          # 75
MIN_BARS = 4                      # a window needs >= 4 of its 5 one-minute bars
LOOKBACK = 20                     # prior ELIGIBLE sessions, same clock bucket
MIN_LOOKBACK_OBS = 15             # valid same-bucket observations required
THR_SESS = 20                     # prior eligible sessions for the percentiles
Q_ABN = 90.0                      # abnormal relative volume
Q_ORD = (25.0, 75.0)              # ordinary relative volume band (control pool)
Q_MAT = 80.0                      # material displacement
Q_LIM = 50.0                      # limited displacement
COOLDOWN_MIN = 15                 # == primary horizon: primary paths never overlap
HORIZONS = (5, 15, 30)            # minutes after the window closes
PRIMARY_H = 15

# ------------------------------------------------------------- costs --------
TICK = 0.01                       # assumed spread: one tick. NOT measured --
COMMISSION = 0.0035               # no ETF quote data exists on disk
RT_PER_SHARE = TICK + 2 * COMMISSION              # $0.017, project convention
NQ_RT_POINTS = 2.0
HURDLE_X_COST = 3.0


def rt_cost_bps(price):
    return 1e4 * RT_PER_SHARE / np.asarray(price, float)


# ------------------------------------------------------------- loading ------
def detect_splits(day_close: pd.Series, tol=0.02):
    """MEASURE corporate splits from the session-close series. A split is a
    session-to-session ratio within 2% of an integer 2..10. Never remembered."""
    out = []
    for i, prev, cur, ratio in DQ.split_scan(day_close.to_numpy(), thresh=0.5):
        k = round(ratio)
        if 2 <= k <= 10 and abs(ratio / k - 1) < tol:
            out.append((day_close.index[i], k, float(prev), float(cur)))
    return out


def load(sym, adjust=True):
    """One-minute RTH bars, naive ET timestamps, split-adjusted to the LATEST
    share basis (prices / k, volumes * k before the split date)."""
    d = pd.read_parquet(PATH[sym])
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["day"] = d["timestamp"].dt.normalize()
    splits = detect_splits(d.groupby("day")["close"].last())
    if adjust:
        for sd, k, _, _ in splits:
            pre = d["day"] < sd
            for c in ("open", "high", "low", "close"):
                d.loc[pre, c] = d.loc[pre, c] / k
            d.loc[pre, "volume"] = d.loc[pre, "volume"] * k
    # minute of the session, owned by the calendar (ET bar file)
    d["m"] = (d["timestamp"].dt.hour * 60 + d["timestamp"].dt.minute
              - (SC.CASH_OPEN_ET.hour * 60 + SC.CASH_OPEN_ET.minute))
    DQ.assert_safe_columns(d, f"RP-012A {sym} bars")
    return d, splits


def early_close_days(d):
    return {pd.Timestamp(x).normalize()
            for x in SC.early_closes(d, ts_col="timestamp", clock="ET")}


# ------------------------------------------------------------- windows ------
def windows(d, early):
    """Seventy-five 5-minute windows per FULL session. Early closes excluded.

    Displacement is close-to-close: ln(C_k / C_{k-1}), with C_{-1} the close
    of the 09:34 bar. Causal, and robust to a missing first bar.
    """
    d = d[~d["day"].isin(early)]
    d = d[(d["m"] >= FIRST_MIN - 1) & (d["m"] < LAST_MIN)].copy()
    ref = d[d["m"] == FIRST_MIN - 1].set_index("day")["close"]
    b = d[d["m"] >= FIRST_MIN].copy()
    b["k"] = (b["m"] - FIRST_MIN) // WIN_MIN
    g = b.groupby(["day", "k"])
    W = pd.DataFrame({"vol": g["volume"].sum(), "n_bars": g["m"].size(),
                      "c_end": g["close"].last(),
                      "hi": g["high"].max(), "lo": g["low"].min()}).reset_index()
    # full 75-window grid per session so that a missing window is VISIBLE
    days = sorted(b["day"].unique())
    grid = pd.MultiIndex.from_product([days, range(N_WIN)], names=["day", "k"])
    W = W.set_index(["day", "k"]).reindex(grid).reset_index()
    W["n_bars"] = W["n_bars"].fillna(0).astype(int)
    W["vol"] = W["vol"].fillna(0.0)
    prev = W.groupby("day")["c_end"].shift(1)
    first = W["k"] == 0
    prev[first] = W.loc[first, "day"].map(ref).to_numpy()
    W["c_prev"] = prev
    W["r"] = np.log(W["c_end"] / W["c_prev"])
    W["valid"] = (W["n_bars"] >= MIN_BARS) & W["r"].notna()
    W["m_end"] = FIRST_MIN + WIN_MIN * (W["k"] + 1)
    DQ.assert_safe_columns(W, "RP-012A windows")
    return W


def features(W):
    """Relative volume and relative displacement against the SAME bucket over
    the prior LOOKBACK eligible sessions. Nothing is pooled across the clock.
    """
    W = W.sort_values(["k", "day"]).copy()

    def trail_median(s):
        return s.shift(1).rolling(LOOKBACK, min_periods=MIN_LOOKBACK_OBS).median()

    v = W["vol"].where(W["valid"])
    a = W["r"].abs().where(W["valid"])
    W["vol_med"] = v.groupby(W["k"]).transform(trail_median)
    W["abs_med"] = a.groupby(W["k"]).transform(trail_median)
    W["rv"] = W["vol"] / W["vol_med"]
    W["rd"] = W["r"].abs() / W["abs_med"]
    bad = (W["vol_med"] <= 0) | (W["abs_med"] <= 0)
    W.loc[bad, ["rv", "rd"]] = np.nan
    W["feat_ok"] = W["valid"] & W["rv"].notna() & W["rd"].notna()
    DQ.assert_safe_columns(W, "RP-012A features")
    return W.sort_values(["day", "k"]).reset_index(drop=True)


def label(W):
    """Causal percentile thresholds from the prior THR_SESS eligible sessions,
    computed SEPARATELY WITHIN EACH TIME BLOCK.

    REVISED AT STAGE 0, BEFORE ANY OUTCOME. The first version pooled the
    percentiles across all 75 buckets on the argument that rv and rd are
    already bucket-normalised. The counts refuted it: normalising by the
    same-bucket MEDIAN fixes each bucket's level but not its SPREAD. Opening
    volume is high every day, so opening RV varies less, and a pooled p90 caught
    only 0.47-0.71x the average abnormal rate in the opening block. That is
    RP-011's pooled-threshold defect one step removed. Block-specific
    percentiles make each block judge itself.
    """
    days = sorted(W["day"].unique())
    state = np.array(["WARMUP"] * len(W), dtype=object)
    di = {d: i for i, d in enumerate(days)}
    W = W.assign(di=W["day"].map(di),
                 blk=(W["m_end"] - WIN_MIN).map(block_of))
    thr = []
    rv, rd = W["rv"].to_numpy(), W["rd"].to_numpy()
    for i, d in enumerate(days):
        prior = W[(W["di"] >= i - THR_SESS) & (W["di"] < i) & W["feat_ok"]]
        if prior["day"].nunique() < THR_SESS:
            continue
        cur_day = (W["day"] == d).to_numpy()
        st = np.where(~W["feat_ok"].to_numpy(), "INVALID", "OTHER").astype(object)
        for _lo, _hi, b in BLOCKS:
            hist = prior[prior["blk"] == b]
            if len(hist) < 50:
                continue
            rv_abn = np.percentile(hist["rv"], Q_ABN)
            rv_lo, rv_hi = np.percentile(hist["rv"], Q_ORD)
            rd_mat = np.percentile(hist["rd"], Q_MAT)
            rd_lim = np.percentile(hist["rd"], Q_LIM)
            thr.append(dict(day=d, block=b, rv_abn=rv_abn, rv_lo=rv_lo,
                            rv_hi=rv_hi, rd_mat=rd_mat, rd_lim=rd_lim))
            ok = cur_day & W["feat_ok"].to_numpy() & (W["blk"] == b).to_numpy()
            abn = ok & (rv >= rv_abn)
            st[abn & (rd >= rd_mat)] = "A"
            st[abn & (rd <= rd_lim)] = "B"
            st[abn & (rd > rd_lim) & (rd < rd_mat)] = "ABN_MID"
            st[ok & (rv >= rv_lo) & (rv <= rv_hi)] = "C"
        state[cur_day] = st[cur_day]
    W = W.assign(state=state).drop(columns=["di", "blk"])
    W["side"] = np.where(W["r"] > 0, "buy", np.where(W["r"] < 0, "sell", "flat"))
    return W, pd.DataFrame(thr)


def cooldown(W):
    """Fifteen minutes after every retained A or B event, per instrument. No
    session cap -- RP-010's cap was a first-come filter. Flat windows carry no
    direction and are never events."""
    W = W.sort_values(["day", "k"]).reset_index(drop=True)
    ev = np.zeros(len(W), bool)
    why = np.array([""] * len(W), dtype=object)
    for _, g in W.groupby("day"):
        last_end = -1e9
        for i in g.index:
            if W.at[i, "state"] not in ("A", "B"):
                continue
            if W.at[i, "side"] == "flat":
                why[i] = "flat"
                continue
            start = W.at[i, "m_end"] - WIN_MIN
            if start - last_end < COOLDOWN_MIN:
                why[i] = "cooldown"
                continue
            ev[i] = True
            why[i] = "event"
            last_end = W.at[i, "m_end"]
    return W.assign(event=ev, drop_reason=why)


BLOCKS = [(5, 30, "opening"), (30, 120, "morning"),
          (120, 270, "midday"), (270, 380, "closing")]


def block_of(m_start):
    for lo, hi, lab in BLOCKS:
        if lo <= m_start < hi:
            return lab
    return "outside"
