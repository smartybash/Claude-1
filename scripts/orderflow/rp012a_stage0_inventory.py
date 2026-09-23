#!/usr/bin/env python3
"""RP-012A Stage 0 -- per-instrument DATA-QUALITY inventory. NO OUTCOMES.

Reads prices and volumes to measure coverage, missing bars, staleness, splits,
activity and cost. Computes no forward return and no event outcome. The only
return-like quantities are UNCONDITIONAL volatility scales (ATR1m and the median
absolute 15-minute move), which are properties of the instrument, not of any
state.

EXCLUSION RULE, DECLARED BEFORE MEASURING. An instrument is excluded from the
PRIMARY screen if, on the discovery block, any of:
  C1  more than 5% of valid 5-minute windows show zero close-to-close change
  C2  more than 2% of 5-minute windows have fewer than 4 of their 5 bars
  C3  more than 1% of 1-minute bars carry zero volume
An excluded instrument may still serve as the LOWER-LIQUIDITY CONTROL only if it
passes C2 and C3 (the relative-volume signal must at least be computable).

SPLIT RULE. Splits are MEASURED from the session-close series
(`rp012a_common.detect_splits`), never remembered. The IJH five-for-one is
verified here, and its effect on an UNADJUSTED relative-volume series is
quantified -- volume only, no outcome -- so that the adjustment is resolved
before any period including 2024-02-22 is opened.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rp012a_common as C                                           # noqa: E402

OUT = C.ROOT / "reports"
L = []
p = L.append

PERIODS = {"discovery 2021-2023": C.DISCOVERY,
           "int. validation 2024-2025": C.INTERNAL_VALIDATION,
           "QQQ 2026 on disk": ("2026-01-01", "2026-12-31")}


def per_period(d, early, lo, hi, raw):
    """`raw` is the UNADJUSTED series. Cost is charged on the price the
    instrument actually traded at: a one-cent spread on IJH at $250 in 2022 is
    0.4 bps, not the 1.9 bps its split-adjusted $50 would imply."""
    x = d[(d["day"] >= lo) & (d["day"] <= hi)]
    if not len(x):
        return None
    days = x["day"].unique()
    n_early = sum(1 for dd in days if dd in early)
    full = [dd for dd in days if dd not in early]
    # count bars only inside each day's ACTUAL session: on a half day the
    # QQQ/SPY files carry after-hours prints to 15:59, which are not RTH bars
    close_m = x["day"].map(lambda dd: 210 if dd in early else 390)
    rth = x[(x["m"] >= 0) & (x["m"] < close_m)]
    expected = 390 * len(full) + 210 * n_early
    rth_full = rth[rth["day"].isin(full)]
    # 1-minute staleness
    same = rth_full.groupby("day")["close"].diff() == 0
    flat = (rth_full["high"] == rth_full["low"])
    # longest run of unchanged closes, per session
    runs = []
    for _, g in rth_full.groupby("day"):
        z = (g["close"].diff() == 0).to_numpy()
        best = cur = 0
        for v in z:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        runs.append(best)
    # 5-minute windows
    W = C.windows(x, early)
    valid = W[W["valid"]]
    # true range, bps
    pc = rth_full.groupby("day")["close"].shift(1)
    tr = np.maximum(rth_full["high"], pc) - np.minimum(rth_full["low"], pc)
    tr_bps = 1e4 * tr / rth_full["close"]
    atr = tr_bps.groupby(rth_full["day"]).mean().median()
    # unconditional |15-minute move|, non-overlapping, bps
    c15 = rth_full[rth_full["m"] % 15 == 14].copy()
    c15["r15"] = c15.groupby("day")["close"].transform(
        lambda s: np.log(s).diff())
    mv15 = 1e4 * c15["r15"].abs().median()
    xr = raw[(raw["day"] >= lo) & (raw["day"] <= hi)]
    px = float(xr[(xr["m"] >= 0) & (xr["m"] < 390)]["close"].median())
    return dict(
        first=str(x["timestamp"].min())[:16], last=str(x["timestamp"].max())[:16],
        sessions=len(days), early=n_early,
        missing_bars=int(expected - len(rth)),
        missing_pct=100 * (expected - len(rth)) / expected,
        zero_change_1m=100 * float(same.mean()),
        flat_1m=100 * float(flat.mean()),
        max_run_med=float(np.median(runs)),
        zero_change_5m=100 * float((valid["r"] == 0).mean()),
        short_5m=100 * float((W["n_bars"] < C.MIN_BARS).mean()),
        med_vol_1m=float(rth_full["volume"].median()),
        med_vol_5m=float(valid["vol"].median()),
        zero_vol_1m=100 * float((rth_full["volume"] == 0).mean()),
        nan_vol=int(rth_full["volume"].isna().sum()),
        px=px, spread_bps=1e4 * C.TICK / px,
        comm_bps=1e4 * 2 * C.COMMISSION / px,
        rt_bps=float(C.rt_cost_bps(px)),
        atr1m_bps=float(atr), mv15_bps=float(mv15))


def main():
    p("RP-012A STAGE 0 -- DATA-QUALITY INVENTORY")
    p("  No forward return, no event outcome. Volatility scales are")
    p("  unconditional properties of each instrument.")
    p("")
    res, splits_all = {}, {}
    for s in C.INSTR:
        d, splits = C.load(s, adjust=True)
        raw, _ = C.load(s, adjust=False)
        early = C.early_close_days(d)
        splits_all[s] = splits
        for lab, (lo, hi) in PERIODS.items():
            if lab.startswith("QQQ") and s != "QQQ":
                continue
            r = per_period(d, early, pd.Timestamp(lo), pd.Timestamp(hi), raw)
            if r:
                res[(s, lab)] = r
    R = pd.DataFrame(res).T
    R.index.names = ["instr", "period"]

    p("=== 1. COVERAGE ===")
    p(f"  {'instr':<6}{'period':<28}{'first':>18}{'last':>18}{'sess':>6}{'early':>7}")
    for (s, lab), r in R.iterrows():
        p(f"  {s:<6}{lab:<28}{r.first:>18}{r['last']:>18}{r.sessions:>6}{r.early:>7}")
    p("  early closes are MEASURED by sessioncal.early_closes: afternoon bar")
    p("  coverage and median afternoon/morning minute volume. All five files")
    p("  return the same ten NYSE half days 2021-2025. They are EXCLUDED from")
    p("  events and from every lookback.")
    p("")
    p("=== 2. MISSING BARS, STALENESS, ACTIVITY ===")
    p(f"  {'instr':<6}{'period':<28}{'miss%':>7}{'0chg1m%':>9}{'flat1m%':>9}"
      f"{'run med':>8}{'0chg5m%':>9}{'<4bar5m%':>10}{'medvol1m':>10}"
      f"{'0vol1m%':>9}{'NaNvol':>8}")
    for (s, lab), r in R.iterrows():
        p(f"  {s:<6}{lab:<28}{r.missing_pct:>7.2f}{r.zero_change_1m:>9.2f}"
          f"{r.flat_1m:>9.2f}{r.max_run_med:>8.0f}{r.zero_change_5m:>9.2f}"
          f"{r.short_5m:>10.2f}{r.med_vol_1m:>10,.0f}{r.zero_vol_1m:>9.2f}"
          f"{r.nan_vol:>8}")
    p("  run med = median over sessions of the longest run of unchanged 1-min closes")
    p("")
    p("=== 3. SPLITS AND CORPORATE ACTIONS (measured) ===")
    for s in C.INSTR:
        sp = splits_all[s]
        if not sp:
            p(f"  {s:<5} no split detected 2021-{'2026' if s=='QQQ' else '2025'}")
        for sd, k, prev, cur in sp:
            p(f"  {s:<5} SPLIT {k}-for-1 effective {sd.date()}: last pre-split "
              f"close {prev:.2f} -> first post-split close {cur:.2f} "
              f"(ratio {prev/cur:.4f})")
    p("  Dividends are not adjusted. They move the OVERNIGHT price only; every")
    p("  RP-012A window and horizon lies inside one cash session, so a dividend")
    p("  cannot enter any RP-012A quantity.")
    p("")
    # IJH split -- VOLUME ONLY, the effect on relative volume
    raw, sp = C.load("IJH", adjust=False)
    adj, _ = C.load("IJH", adjust=True)
    sd = sp[0][0]
    early = C.early_close_days(raw)
    days = sorted(raw["day"].unique())
    i0 = days.index(sd)
    win = days[i0 - 40:i0 + 20]
    p("  IJH SPLIT RESOLUTION -- volume only, no outcome")
    for tag, dd in (("UNADJUSTED", raw), ("ADJUSTED  ", adj)):
        W = C.features(C.windows(dd[dd["day"].isin(win)], early))
        post = W[(W["day"] >= sd) & W["feat_ok"]]
        pre = W[(W["day"] < sd) & (W["day"] >= days[i0 - 20]) & W["feat_ok"]]
        p(f"    {tag}: median RV 20 sessions BEFORE {pre.rv.median():.2f}, "
          f"20 sessions AFTER {post.rv.median():.2f}; "
          f"post-split windows with RV >= 2: {100*(post.rv>=2).mean():.1f}%")
    p("    Unadjusted, every post-split window reads as ~5x normal volume for")
    p("    twenty sessions -- an entire month of spurious 'abnormal volume'.")
    p("    RP-012A uses the ADJUSTED series: pre-split prices / 5, volumes x 5.")
    p("")
    p("=== 4. COST ASSUMPTIONS ===")
    p("  spread: ONE TICK ($0.01), an ASSUMPTION -- no ETF quote data exists on")
    p("  disk. commission: $0.0035/share each way. Round trip $0.017/share.")
    p("  Optimistic for IJH after the split and for EFA, where a one-cent")
    p("  spread is a larger fraction of price and is less often the touch.")
    p("")
    p("  med px is the ACTUAL traded price (unadjusted) -- cost is charged there")
    p(f"  {'instr':<6}{'period':<28}{'med px':>9}{'spread bps':>11}{'comm bps':>10}"
      f"{'RT bps':>8}{'ATR1m bps':>11}{'|15m| bps':>11}{'RT/1.2ATR':>11}"
      f"{'3xRT bps':>10}")
    for (s, lab), r in R.iterrows():
        p(f"  {s:<6}{lab:<28}{r.px:>9.2f}{r.spread_bps:>11.3f}{r.comm_bps:>10.3f}"
          f"{r.rt_bps:>8.3f}{r.atr1m_bps:>11.2f}{r.mv15_bps:>11.2f}"
          f"{100*r.rt_bps/(1.2*r.atr1m_bps):>10.1f}%{3*r.rt_bps:>10.3f}")
    p("")
    p("=== 5. EXCLUSION RULE (declared in the docstring before measuring) ===")
    disc = R.xs("discovery 2021-2023", level="period")
    verdict = {}
    for s, r in disc.iterrows():
        c1 = r.zero_change_5m <= 5.0
        c2 = r.short_5m <= 2.0
        c3 = r.zero_vol_1m <= 1.0
        role = ("PRIMARY" if c1 and c2 and c3 else
                "LOWER-LIQUIDITY CONTROL ONLY" if c2 and c3 else "EXCLUDED")
        verdict[s] = role
        p(f"  {s:<5} C1 {'pass' if c1 else 'FAIL'} ({r.zero_change_5m:.2f}%)  "
          f"C2 {'pass' if c2 else 'FAIL'} ({r.short_5m:.2f}%)  "
          f"C3 {'pass' if c3 else 'FAIL'} ({r.zero_vol_1m:.2f}%)  -> {role}")
    p("")
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp012a_stage0_inventory.txt").write_text(txt)
    R.to_csv(OUT / "rp012a_stage0_inventory.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
