#!/usr/bin/env python3
"""RP-004 Stage 1 — SPY -> EFA intraday lead-lag. FALSIFICATION STUDY.

No P&L, expectancy, profit factor, drawdown or pass probability.

Discovery 2021-2022 ONLY. 2023 and 2024-2025 are not read unless discovery
passes every declared condition.

Frozen: 1-minute log returns; lags 1, 2, 5, 10 minutes only; reverse direction
as the mechanism control; same-minute correlation is a CONTROL, not an edge.
Returns never cross a session boundary.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BLOCK = ("2021-01-04", "2022-12-31")
LAGS = (1, 2, 5, 10)
NBARS_MIN = 380
SEED = 20260923


def load():
    s = pd.read_parquet(ROOT / "data/related/SPY_1m.parquet")
    e = pd.read_parquet(ROOT / "data/related/EFA_1m.parquet")
    for d in (s, e):
        d["ts"] = pd.to_datetime(d["timestamp"])
        d["date"] = d["ts"].dt.normalize()
    s = s[(s["date"] >= BLOCK[0]) & (s["date"] <= BLOCK[1])]
    e = e[(e["date"] >= BLOCK[0]) & (e["date"] <= BLOCK[1])]
    return s, e


def alignment(s, e):
    print("=== 0. ALIGNMENT AND DATA QUALITY (before any measurement) ===")
    ss, es = set(s["ts"]), set(e["ts"])
    inter = ss & es
    print(f"  SPY bars {len(ss):,} | EFA bars {len(es):,} | "
          f"exact-timestamp intersection {len(inter):,}")
    print(f"  SPY-only {len(ss-es):,} ({100*len(ss-es)/len(ss):.2f}%) | "
          f"EFA-only {len(es-ss):,} ({100*len(es-ss)/len(es):.2f}%)")

    m = s[["ts", "close"]].merge(e[["ts", "close"]], on="ts", suffixes=("_s", "_e"))
    m["date"] = m["ts"].dt.normalize()
    per = m.groupby("date").size()
    print(f"  aligned bars/session: min {per.min()} | p1 {per.quantile(.01):.0f} | "
          f"median {per.median():.0f}")
    bad = per[per < NBARS_MIN]
    print(f"  sessions dropped (<{NBARS_MIN} aligned bars): {len(bad)} of {len(per)}")
    m = m[m["date"].isin(per[per >= NBARS_MIN].index)].sort_values("ts")

    print("\n  PRICE ADJUSTMENT CONSISTENCY")
    for c, lab in (("close_s", "SPY"), ("close_e", "EFA")):
        r = m.groupby("date")[c].first().pct_change().abs()
        print(f"    {lab}: session-open-to-open jumps >10% : {int((r > .10).sum())} "
              f"| max {100*r.max():.2f}%  (a split would show here)")

    print("\n  STALE / REPEATED 1-MINUTE CLOSES  <-- kill condition 7")
    for c, lab in (("close_s", "SPY"), ("close_e", "EFA")):
        d = m.groupby("date")[c].diff()
        zero = (d == 0).mean()
        run = m[c].groupby((m[c] != m[c].shift()).cumsum()).transform("size")
        print(f"    {lab}: zero-change bars {100*zero:.2f}% | "
              f"max repeat run {int(run.max())} bars | "
              f">=3-bar flat runs {100*(run >= 3).mean():.2f}% of bars")
    return m


def series(m):
    """Within-session 1-minute log returns; never crosses a session boundary."""
    rs, re, dates, tod = [], [], [], []
    for d, g in m.groupby("date"):
        g = g.sort_values("ts")
        rs.append(np.diff(np.log(g["close_s"].values)))
        re.append(np.diff(np.log(g["close_e"].values)))
        n = len(g) - 1
        dates.append(np.full(n, d))
        tod.append((g["ts"].dt.hour * 60 + g["ts"].dt.minute).values[1:])
    return (np.concatenate(rs), np.concatenate(re),
            np.concatenate(dates), np.concatenate(tod))


def pairs(x, y, dates, lag):
    """(x_t, y_{t+lag}, y_t) with both points inside the same session."""
    if lag == 0:
        ok = np.ones(len(x), bool)
        ok[0] = False
        ok &= dates == np.roll(dates, 1)
        return x[ok], y[ok], np.roll(y, 1)[ok]
    ok = np.zeros(len(x), bool)
    ok[: len(x) - lag] = dates[: len(x) - lag] == dates[lag:]
    ok[0] = False
    ok &= dates == np.roll(dates, 1)          # y_t (own prior) same session too
    idx = np.where(ok)[0]
    return x[idx], y[idx + lag], y[idx]


def inc_r2(xt, yf, yown):
    """R2 of own-prior alone, and with SPY added. Delta is the incremental value."""
    A = np.column_stack([np.ones_like(yown), yown])
    B = np.column_stack([np.ones_like(yown), yown, xt])
    def r2(M):
        b, *_ = np.linalg.lstsq(M, yf, rcond=None)
        res = yf - M @ b
        return 1 - res.var() / yf.var(), b
    ra, _ = r2(A)
    rb, bb = r2(B)
    return ra, rb, rb - ra, bb[2]


def row(lab, xt, yf, yown, sd_x):
    c = float(np.corrcoef(xt, yf)[0, 1])
    ra, rb, dr, b = inc_r2(xt, yf, yown)
    sign = float((np.sign(xt) == np.sign(yf)).mean())
    return dict(set=lab, n=len(xt), corr=round(c, 4),
                r2_own=round(100 * ra, 3), r2_both=round(100 * rb, 3),
                dR2=round(100 * dr, 4), beta=round(b, 4),
                sign_agree=round(100 * sign, 1),
                resp_1sd=round(1e4 * b * sd_x, 2))


def main() -> int:
    s, e = load()
    m = alignment(s, e)
    rs, re, dates, tod = series(m)
    sd_s = float(rs.std())
    px_e = float(m["close_e"].mean())
    months = len(pd.PeriodIndex(pd.DatetimeIndex(np.unique(dates)), freq="M").unique())
    print(f"\n  usable return observations {len(rs):,} over {months} months | "
          f"SPY 1-min sd {1e4*sd_s:.2f} bps | mean EFA price ${px_e:.2f}")

    print("\n=== 1. HEADLINE: SPY_t -> EFA_{t+lag}  (lag 0 is a CONTROL) ===")
    out = []
    for L in (0,) + LAGS:
        xt, yf, yown = pairs(rs, re, dates, L)
        out.append(row(f"lag {L}" + ("  <-CONTROL" if L == 0 else ""), xt, yf, yown, sd_s))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 2. CONTROL: REVERSE DIRECTION  EFA_t -> SPY_{t+lag} ===")
    out = []
    sd_e = float(re.std())
    for L in (0,) + LAGS:
        xt, yf, yown = pairs(re, rs, dates, L)
        out.append(row(f"lag {L}", xt, yf, yown, sd_e))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 3. CONTROL: TIME-SHUFFLED SPY (same year + time bucket) ===")
    rng = np.random.default_rng(SEED)
    yrs = pd.DatetimeIndex(dates).year.values
    buck = np.digitize(tod, [660, 840])
    shuf = rs.copy()
    for y in np.unique(yrs):
        for b in np.unique(buck):
            k = np.where((yrs == y) & (buck == b))[0]
            shuf[k] = rs[rng.permutation(k)]
    out = []
    for L in LAGS:
        xt, yf, yown = pairs(shuf, re, dates, L)
        out.append(row(f"lag {L}", xt, yf, yown, sd_s))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 4. CONTROL: SPY SIGN REVERSED, MAGNITUDE PRESERVED ===")
    out = []
    flip = rng.choice([-1.0, 1.0], size=len(rs))
    for L in LAGS:
        xt, yf, yown = pairs(rs * flip, re, dates, L)
        out.append(row(f"lag {L}", xt, yf, yown, sd_s))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 5. POSITIVE vs NEGATIVE SPY MOVES ===")
    out = []
    for L in LAGS:
        xt, yf, yown = pairs(rs, re, dates, L)
        for lab, k in (("SPY up", xt > 0), ("SPY down", xt < 0)):
            out.append(dict(lag=L, side=lab, n=int(k.sum()),
                            mean_EFA_bps=round(1e4 * yf[k].mean(), 3),
                            sign_agree=round(100 * float((np.sign(xt[k]) == np.sign(yf[k])).mean()), 1)))
    print(pd.DataFrame(out).to_string(index=False))

    print("\n=== 6. BY YEAR, AND BY TIME OF DAY ===")
    for L in LAGS:
        xt, yf, yown = pairs(rs, re, dates, L)
        idx = np.where(np.isin(np.arange(len(rs)), np.arange(len(rs))))[0]
        _, _, _ = xt, yf, yown
    for L in LAGS:
        ok = np.zeros(len(rs), bool)
        ok[: len(rs) - L] = dates[: len(rs) - L] == dates[L:]
        ok[0] = False
        ok &= dates == np.roll(dates, 1)
        i = np.where(ok)[0]
        yy = pd.DatetimeIndex(dates[i]).year.values
        bb = np.digitize(tod[i], [660, 840])
        line = [f"  lag {L:2d}"]
        for y in np.unique(yy):
            k = yy == y
            line.append(f"{y}: r={np.corrcoef(rs[i][k], re[i+L][k])[0,1]:+.4f}")
        for b, lab in ((0, "09:30-11:00"), (1, "11:00-14:00"), (2, "14:00-16:00")):
            k = bb == b
            line.append(f"{lab}: r={np.corrcoef(rs[i][k], re[i+L][k])[0,1]:+.4f}")
        print("  ".join(line))

    print("\n=== 7. EXECUTABILITY (declared before results) ===")
    spread = 1e4 * 0.01 / px_e
    slip = spread
    comm = 2 * 1e4 * 0.0035 / px_e
    cost = spread + slip + comm
    print(f"  EFA at ${px_e:.2f}: spread {spread:.2f} + 1 tick slippage {slip:.2f} "
          f"+ commission {comm:.2f} = ROUND TRIP {cost:.2f} bps")
    print(f"  REQUIRED: predicted EFA response > 3 x cost = {3*cost:.2f} bps\n")
    big = np.abs(rs) >= np.quantile(np.abs(rs), 0.90)
    for L in LAGS:
        xt, yf, yown = pairs(rs, re, dates, L)
        _, _, _, b = inc_r2(xt, yf, yown)
        r1 = 1e4 * b * sd_s
        ok = np.zeros(len(rs), bool)
        ok[: len(rs) - L] = dates[: len(rs) - L] == dates[L:]
        ok[0] = False
        ok &= dates == np.roll(dates, 1)
        i = np.where(ok & big)[0]
        r9 = 1e4 * b * float(np.abs(rs[i]).mean())
        print(f"  lag {L:2d}: response to 1-sd SPY move {r1:6.2f} bps "
              f"({r1/(3*cost):.2f}x bar) | to a top-decile SPY move {r9:6.2f} bps "
              f"({r9/(3*cost):.2f}x bar)")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
