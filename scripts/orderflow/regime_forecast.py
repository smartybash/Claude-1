#!/usr/bin/env python3
"""STAGE 1 — IS THE SESSION REGIME FORECASTABLE AT THE DECISION TIMESTAMP?

Pre-registered at `43ab596` (`reports/regime_forecastability_preregistration.md`)
before this ran. Descriptive. No rule is traded here and no expectancy is
computed; stage 2 exists only if this passes.

THE QUESTION

The regime hypothesis says continuation rules win in trending sessions and lose
in choppy ones. That is untestable unless the regime can be called BEFORE the
trade. The whole-session efficiency ratio measured earlier cannot do it: it
reads bars from after the decision timestamp. So the prior question is whether
anything available at the decision timestamp predicts what the rest of the
session does.

THE ONE CONSTRAINT THAT MATTERS

  predictor window ends at or before D  |  outcome window starts at D
                          they share no bars

D = session open + OR_MIN. Trailing-history terms are shifted one session, so no
session is classified using its own data or anything after it.

PASS REQUIRES ALL THREE, fixed in advance:
  |Spearman rho| >= 0.10, p < 0.00357 (Bonferroni over 14), decile spread >= 0.020

POSITIVE CONTROL

Later realised volatility is carried as a second outcome throughout. It is not
part of the hypothesis. It is there so that a null on efficiency can be
distinguished from a broken pipeline: volatility clustering is well established,
so if the machinery works, `rv_open` must predict `rv_later` strongly.

Sealed NQ days are not read: this script never opens the NQ tape.

Usage: python3 scripts/orderflow/regime_forecast.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"

FLAT_UTC = (18, 30)
MIN_BARS = 360
G_OR = (15, 30)
TRAIL_N = 20

N_TESTS = 14
ALPHA = 0.05
P_BAR = ALPHA / N_TESTS
RHO_BAR = 0.10
SPREAD_BAR = 0.020

PRED = ["or_ratio", "rv_open", "eff_open", "gap", "prior_range", "or_pos",
        "vol_ratio"]


def et_wall(day, hh, mm):
    u = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=dt.timezone.utc)
    return pd.Timestamp(u.astimezone(ET).replace(tzinfo=None))


# ------------------------------------------------------------------ build --

def sessions():
    d = pd.read_parquet(SRC)
    d["day"] = d.timestamp.dt.date
    out, rejected = {}, 0
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            rejected += 1
            continue
        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        flat_t = et_wall(day, *FLAT_UTC)
        if g.timestamp.iloc[0] > open_t or g.timestamp.iloc[-1] < flat_t:
            rejected += 1
            continue
        out[day] = g[(g.timestamp >= open_t) & (g.timestamp <= flat_t)]
    return out, rejected


def eff_and_rv(cl):
    """Efficiency ratio and realised vol over a closing-price path."""
    r = np.diff(np.log(cl))
    r = r[np.isfinite(r)]
    path = float(np.abs(r).sum())
    net = float(abs(np.log(cl[-1] / cl[0])))
    rv = float(np.sqrt((r ** 2).sum()))
    return (net / path if path > 0 else np.nan), 1e4 * rv, 1e4 * path, len(r)


def measure(S, or_min):
    """One row per session: predictors at D, outcomes after D. No shared bars."""
    days = sorted(S)
    prev_close, prev_range = None, None
    rows = []
    for day in days:
        g = S[day]
        t = g.timestamp.to_numpy()
        hi = g.high.to_numpy(float)
        lo = g.low.to_numpy(float)
        cl = g.close.to_numpy(float)
        vol = g.volume.to_numpy(float)
        open_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        D = np.datetime64(open_t + pd.Timedelta(minutes=or_min))

        pre = t < D
        post = t >= D
        px = float(g.open.iloc[0])
        day_range = 1e4 * (hi.max() - lo.min()) / px
        this_close = float(cl[-1])

        if pre.sum() >= 3 and post.sum() >= 30:
            orh, orl = float(hi[pre].max()), float(lo[pre].min())
            eo, rvo, patho, _ = eff_and_rv(cl[pre])
            el, rvl, pathl, nl = eff_and_rv(cl[post])
            rows.append(dict(
                day=day, px=px,
                # ---- predictors, bars <= D only -------------------------
                or_h=1e4 * (orh - orl) / px,
                rv_open_raw=rvo,
                eff_open=eo,
                gap_raw=(1e4 * abs(px - prev_close) / prev_close
                         if prev_close else np.nan),
                prior_range_raw=prev_range if prev_range else np.nan,
                or_pos=(abs(2 * (float(cl[pre][-1]) - orl) / (orh - orl) - 1)
                        if orh > orl else np.nan),
                vol_open_raw=float(vol[pre].sum()),
                # ---- outcomes, bars >= D only ---------------------------
                eff_later=el, rv_later=rvl, n_later=nl,
            ))
        prev_close, prev_range = this_close, day_range

    F = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)

    # Trailing normalisation, shifted: no session uses its own data.
    def trail(col):
        s = F[col]
        return s / s.rolling(TRAIL_N, min_periods=TRAIL_N).mean().shift(1)

    F["or_ratio"] = trail("or_h")
    F["rv_open"] = trail("rv_open_raw")
    F["gap"] = trail("gap_raw")
    F["prior_range"] = trail("prior_range_raw")
    F["vol_ratio"] = trail("vol_open_raw")
    F["year"] = pd.to_datetime(F.day).dt.year
    return F


# ----------------------------------------------------------- statistics --

def spearman(a, b):
    ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
    return float(np.corrcoef(ra, rb)[0, 1])


def pearson(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def pval(rho, n):
    """Two-sided p for a correlation, via the t transform."""
    if n < 5 or not np.isfinite(rho) or abs(rho) >= 1:
        return np.nan
    t = rho * np.sqrt((n - 2) / (1 - rho ** 2))
    try:
        from scipy import stats
        return float(2 * stats.t.sf(abs(t), n - 2))
    except Exception:
        from math import erfc, sqrt
        return float(erfc(abs(t) / sqrt(2)))


def deciles(x, y, k=10):
    """Mean outcome by decile of the predictor. Returns the ladder and spread."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10 * k:
        return None
    d["b"] = pd.qcut(d.x.rank(method="first"), k, labels=False)
    g = d.groupby("b").y.agg(["mean", "count"])
    return g, float(g["mean"].iloc[-1] - g["mean"].iloc[0])


def block(F, or_min, outcome, label, results):
    print("\n" + "=" * 108)
    print(f"  OUTCOME: {label}   |   DECISION TIMESTAMP D = open + {or_min} min")
    print("=" * 108)
    print(f"  {'predictor':<14}{'n':>7}{'Spearman':>10}{'p':>12}"
          f"{'Pearson':>10}{'bottom d1':>11}{'top d10':>10}{'spread':>10}"
          f"{'verdict':>10}")
    for p in PRED:
        d = F[[p, outcome]].dropna()
        n = len(d)
        if n < 100:
            print(f"  {p:<14}{n:>7}      insufficient")
            continue
        rho = spearman(d[p], d[outcome])
        pr = pearson(d[p], d[outcome])
        pv = pval(rho, n)
        dec = deciles(d[p], d[outcome])
        lad, spread = dec if dec else (None, np.nan)
        d1 = lad["mean"].iloc[0] if lad is not None else np.nan
        d10 = lad["mean"].iloc[-1] if lad is not None else np.nan
        ok = (abs(rho) >= RHO_BAR and pv < P_BAR
              and abs(spread) >= SPREAD_BAR)
        if outcome == "eff_later":
            results.append(dict(pred=p, or_min=or_min, n=n, rho=rho, p=pv,
                                pearson=pr, spread=spread, passes=ok,
                                ladder=lad))
        fmt = "{:>11.4f}{:>10.4f}{:>10.4f}" if outcome == "eff_later" \
            else "{:>11.2f}{:>10.2f}{:>10.2f}"
        print(f"  {p:<14}{n:>7,}{rho:>+10.3f}{pv:>12.2e}{pr:>+10.3f}"
              + fmt.format(d1, d10, spread)
              + ("{:>10}".format("PASS" if ok else "--")))
    return results


def ladder_print(r):
    print(f"\n  DECILE LADDER — {r['pred']} at OR{r['or_min']}, "
          f"outcome eff_later   (spread {r['spread']:+.4f})")
    lad = r["ladder"]
    print("    decile " + "".join(f"{i + 1:>8}" for i in range(len(lad))))
    print("    mean   " + "".join(f"{v:>8.4f}" for v in lad["mean"]))
    print("    n      " + "".join(f"{v:>8,}" for v in lad["count"]))


# ------------------------------------------------------------------- run --

def main():
    print("=" * 108)
    print("  STAGE 1 — DOES EARLY SESSION INFORMATION PREDICT WHETHER THE "
          "REMAINDER TRENDS OR CHOPS?")
    print("=" * 108)
    print("  Descriptive. No rule is traded, no expectancy is computed. "
          "Stage 2 runs only if this passes.")
    print(f"  Pass requires ALL THREE: |rho| >= {RHO_BAR}, "
          f"p < {P_BAR:.5f} (Bonferroni/{N_TESTS}), spread >= {SPREAD_BAR}")

    S, rejected = sessions()
    print(f"\n  sessions {len(S):,}   {min(S)} to {max(S)}   "
          f"rejected {rejected}")

    results = []
    for or_min in G_OR:
        F = measure(S, or_min)
        nl = F.n_later.median()
        rw = np.sqrt(2 / (np.pi * nl))
        print("\n" + "-" * 108)
        print(f"  OR_MIN {or_min}: {len(F):,} sessions measured, "
              f"median {nl:.0f} post-decision bars")
        print(f"  random-walk baseline for that length = {rw:.4f}   |   "
              f"observed median eff_later = {F.eff_later.median():.4f}")
        block(F, or_min, "eff_later", "EFFICIENCY RATIO AFTER D — "
              "THE REGIME, THE THING THE HYPOTHESIS NEEDS", results)
        block(F, or_min, "rv_later", "REALISED VOL AFTER D (bps) — "
              "POSITIVE CONTROL, NOT PART OF THE HYPOTHESIS", [])
        F.to_csv(ROOT / f"reports/regime_forecast_OR{or_min}.csv", index=False)

    print("\n" + "=" * 108)
    print("  VERDICT")
    print("=" * 108)
    R = pd.DataFrame([{k: v for k, v in r.items() if k != "ladder"}
                      for r in results])
    passed = R[R.passes]
    print(f"  14 predictor-window combinations tested against eff_later.")
    print(f"  cleared |rho| >= {RHO_BAR}:        "
          f"{int((R.rho.abs() >= RHO_BAR).sum()):>2} of 14")
    print(f"  cleared p < {P_BAR:.5f}:       "
          f"{int((R.p < P_BAR).sum()):>2} of 14")
    print(f"  cleared spread >= {SPREAD_BAR}:    "
          f"{int((R.spread.abs() >= SPREAD_BAR).sum()):>2} of 14")
    print(f"  cleared ALL THREE:            {len(passed):>2} of 14")
    print(f"\n  largest |rho| observed:    {R.rho.abs().max():.4f}  "
          f"({R.loc[R.rho.abs().idxmax(), 'pred']} "
          f"OR{R.loc[R.rho.abs().idxmax(), 'or_min']})")
    print(f"  largest |spread| observed: {R.spread.abs().max():.4f}  "
          f"({R.loc[R.spread.abs().idxmax(), 'pred']} "
          f"OR{R.loc[R.spread.abs().idxmax(), 'or_min']})   "
          f"bar is {SPREAD_BAR}")

    # ladders for the two strongest, whatever the verdict
    for idx in (R.spread.abs().idxmax(), R.rho.abs().idxmax()):
        ladder_print(results[idx])

    if passed.empty:
        print("\n" + "=" * 108)
        print("  NO CANDIDATE PREDICTS THE LATER REGIME. STOP.")
        print("=" * 108)
        print("  Stage 2 is NOT run. The pre-registered 6-variant budget is "
              "NOT spent.")
        print("  A regime-conditional strategy is impossible if the regime is "
              "not forecastable,")
        print("  and that is a complete answer to the hypothesis.")
    else:
        print("\n  CANDIDATES CLEARING ALL THREE:")
        print(passed.to_string(index=False))
        best = passed.iloc[passed.spread.abs().argmax()]
        print(f"\n  Stage 2 predictor by the declared rule "
              f"(largest spread, ties on |rho|): "
              f"{best.pred} at OR{best.or_min}, direction "
              f"{'HIGH' if best.rho > 0 else 'LOW'} = favourable")

    R.to_csv(ROOT / "reports/regime_forecast_summary.csv", index=False)
    print(f"\n  per-session values: reports/regime_forecast_OR{{15,30}}.csv")
    print("  Sealed NQ days were not read.")


if __name__ == "__main__":
    main()
