#!/usr/bin/env python3
"""RP-012A Stage 1 -- DISCOVERY ONLY, 2021-01-04 .. 2023-12-29. DESCRIPTIVE.

Pre-registered at reports/rp012a_stage0.md (commit 3816474); construction in
rp012a_common.py, unchanged. No entry, stop, target, expectancy or prop
simulation is constructed. 2024-2025 is NOT opened by this script: the loader
filter below is the only date filter and it ends at DISCOVERY[1].

Instruments: QQQ, SPY, IWM primary. EFA lower-liquidity control only, never in
the pooled primary. IJH excluded.

GATE: test_platform.py must pass; the count is printed first. The six Stage 0
count conditions are re-checked here, and the script STOPS before computing a
single forward return if any fails.

FORWARD PATH (frozen):
  entry  P0 = open of the first one-minute bar of the NEXT window (minute
         m_end). If that bar is missing, the next bar at m_end+1; else no
         outcome (counted).
  exit   close of the last bar at or before minute m_end+h-1
  eligible at horizon h only if m_end + h <= 390 (no truncation)
  r_h    direction-adjusted: sign(window displacement) * 1e4 * ln(exit / P0), bps
  MFE/MAE over the bars [m_end, m_end+h), direction-adjusted, bps
  The event window's own displacement never enters a forward quantity.

DECLARED BEFORE THE RUN -- definitions the brief leaves open:
  continuation / reversal frequency   share with r_15 > 0 / < 0
  time to continuation / reversal     first minute at which favourable / adverse
                                      excursion reaches ONE TYPICAL 5-MINUTE
                                      MOVE of that bucket (the window's own
                                      trailing median |displacement|, abs_med),
                                      searched over the 30-minute path
  return to origin                    price trades back to C_{k-1}, the level
                                      the event window started from, within
                                      the horizon
  break of the event extreme          high above the window high (buy) / low
                                      below the window low (sell) within the
                                      horizon
  "materially outperforms"            date-clustered paired difference, A minus
                                      control, at 15 min: mean >= the
                                      instrument's round-trip cost AND t >= 2.0
  "similar" (kill)                    A minus control < 1 round-trip cost
  zero / missing volume               a missing one-minute bar is NO TRADING:
                                      it contributes nothing and is never
                                      substituted. A window with < 4 bars is
                                      invalid -- never an event, control, or
                                      lookback observation. A same-bucket
                                      median of zero voids RV for that window.

CONTROLS (all on the same windows, same horizon, date-clustered):
  1 DISPLACEMENT ONLY   state-C windows (RV p25-p75) with RD >= block p80,
                        directly standardised onto A's (block x RD-quintile)
                        mix. The primary comparison.
  2 VOLUME ONLY         state B, and abnormal-volume windows at RD p50-p80
  3 MATCHED ORDINARY    all state-C windows, standardised onto A's (block x
                        local-volatility quintile) mix
  4 ABSOLUTE VOLUME     A's construction with RAW window volume >= a causal
                        p90 pooled across the day, same RD rule, same cooldown
  5 RANDOM DIRECTION    A's magnitudes with 1,000 random sign draws
  6 EFA                 the identical construction on EFA
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataquality as DQ                                            # noqa: E402
import rp012a_common as C                                           # noqa: E402

OUT = C.ROOT / "reports"
PRIMARY = ("QQQ", "SPY", "IWM")
CONTROL = ("EFA",)
HURDLE = {"QQQ": 1.515, "SPY": 1.213, "IWM": 2.653}     # 3x RT, discovery px
SEED = 20260923
L = []
p = L.append


def gate():
    r = subprocess.run([sys.executable, str(HERE / "test_platform.py")],
                       capture_output=True, text=True)
    line = [x for x in r.stdout.splitlines() if "PASS " in x and "FAIL" in x]
    line = line[-1].strip() if line else "(no summary)"
    if r.returncode != 0:
        print(f"PLATFORM TESTS FAILED -- {line}")
        sys.exit(2)
    return line


# ------------------------------------------------------------ build ---------
def build(sym):
    d, _ = C.load(sym)
    lo, hi = (pd.Timestamp(x) for x in C.DISCOVERY)
    d = d[(d["day"] >= lo) & (d["day"] <= hi)]
    assert d["day"].max() <= hi, "validation data leaked into discovery"
    early = C.early_close_days(d)
    W = C.features(C.windows(d, early))
    W, T = C.label(W)
    W = C.cooldown(W)
    W["block"] = (W["m_end"] - C.WIN_MIN).map(C.block_of)
    W["year"] = W["day"].dt.year
    W["sym"] = sym
    # thresholds of the window's own (day, block), for the controls
    W = W.merge(T.rename(columns={"block": "block"}), on=["day", "block"],
                how="left")
    # absolute-volume arm: RAW window volume against a causal p90 pooled
    # across the whole day over the prior 20 sessions (the construction the
    # study rejects), same RD rule, same cooldown
    days = sorted(W["day"].unique())
    di = W["day"].map({x: i for i, x in enumerate(days)})
    abs_thr = {}
    for i, dd in enumerate(days):
        hist = W[(di >= i - C.THR_SESS) & (di < i) & W["feat_ok"]]
        if hist["day"].nunique() >= C.THR_SESS:
            abs_thr[dd] = np.percentile(hist["vol"], C.Q_ABN)
    W["vol_abs_thr"] = W["day"].map(abs_thr)
    lab = W["state"] != "WARMUP"
    W["abs_cand"] = (lab & W["feat_ok"] & (W["vol"] >= W["vol_abs_thr"])
                     & (W["rd"] >= W["rd_mat"]) & (W["side"] != "flat"))
    W["abs_event"] = cool_mask(W, W["abs_cand"].to_numpy())
    DQ.assert_safe_columns(W, f"RP-012A {sym} stage1 frame")
    return d[~d["day"].isin(early)], W, len(early)


def cool_mask(W, cand):
    """The frozen 15-minute cooldown applied to an arbitrary candidate mask."""
    keep = np.zeros(len(W), bool)
    day, m_end = W["day"].to_numpy(), W["m_end"].to_numpy()
    last_day, last_end = None, -1e9
    for i in np.flatnonzero(cand):
        if day[i] != last_day:
            last_day, last_end = day[i], -1e9
        if m_end[i] - C.WIN_MIN - last_end < C.COOLDOWN_MIN:
            continue
        keep[i] = True
        last_end = m_end[i]
    return keep


# ------------------------------------------------------------ outcomes ------
def outcomes(bars, W):
    """Forward paths for every labelled, valid, directional window."""
    B = bars[(bars["m"] >= 0) & (bars["m"] < 390)]
    need = W[(W["state"] != "WARMUP") & W["feat_ok"] & (W["side"] != "flat")]
    cols = {f"r{h}": np.nan for h in C.HORIZONS}
    cols.update({f"mfe{h}": np.nan for h in C.HORIZONS})
    cols.update({f"mae{h}": np.nan for h in C.HORIZONS})
    cols.update({f"orig{h}": np.nan for h in C.HORIZONS})
    cols.update({f"brk{h}": np.nan for h in C.HORIZONS})
    cols.update(t_cont=np.nan, t_rev=np.nan, p0=np.nan)
    res = {k: np.full(len(W), v) for k, v in cols.items()}
    for day, g in need.groupby("day"):
        x = B[B["day"] == day]
        O = np.full(390, np.nan); H = O.copy(); Lo = O.copy(); Cl = O.copy()
        mm = x["m"].to_numpy()
        O[mm], H[mm], Lo[mm], Cl[mm] = (x["open"].to_numpy(), x["high"].to_numpy(),
                                         x["low"].to_numpy(), x["close"].to_numpy())
        for i, r in zip(g.index, g.itertuples()):
            m0 = int(r.m_end)
            if m0 < 390 and not np.isnan(O[m0]):
                p0 = O[m0]
            elif m0 + 1 < 390 and not np.isnan(O[m0 + 1]):
                p0 = O[m0 + 1]
            else:
                continue
            sg = 1.0 if r.side == "buy" else -1.0
            res["p0"][i] = p0
            for h in C.HORIZONS:
                if m0 + h > 390:
                    continue
                seg_c = Cl[m0:m0 + h]
                ok = ~np.isnan(seg_c)
                if not ok.any():
                    continue
                ex = seg_c[ok][-1]
                res[f"r{h}"][i] = sg * 1e4 * np.log(ex / p0)
                hh, ll = np.nanmax(H[m0:m0 + h]), np.nanmin(Lo[m0:m0 + h])
                fav = (hh if sg > 0 else ll)
                adv = (ll if sg > 0 else hh)
                res[f"mfe{h}"][i] = sg * 1e4 * np.log(fav / p0)
                res[f"mae{h}"][i] = -sg * 1e4 * np.log(adv / p0)
                res[f"orig{h}"][i] = float((ll <= r.c_prev) if sg > 0
                                           else (hh >= r.c_prev))
                res[f"brk{h}"][i] = float((hh > r.hi) if sg > 0 else (ll < r.lo))
            # time to one typical 5-minute move, over the 30-minute path
            thr = 1e4 * r.abs_med
            hz = min(30, 390 - m0)
            for j in range(hz):
                if np.isnan(H[m0 + j]):
                    continue
                f = sg * 1e4 * np.log((H[m0 + j] if sg > 0 else Lo[m0 + j]) / p0)
                a = -sg * 1e4 * np.log((Lo[m0 + j] if sg > 0 else H[m0 + j]) / p0)
                if np.isnan(res["t_cont"][i]) and f >= thr:
                    res["t_cont"][i] = j + 1
                if np.isnan(res["t_rev"][i]) and a >= thr:
                    res["t_rev"][i] = j + 1
    for k, v in res.items():
        W[k] = v
    W["rt_bps"] = C.rt_cost_bps(W["p0"])
    return W


# ------------------------------------------------------------ statistics ----
def clus(df, col="r15"):
    s = df.groupby("day")[col].mean().dropna()
    if len(s) < 3:
        return np.nan, np.nan, len(s), s
    return s.mean(), s.mean() / (s.std(ddof=1) / np.sqrt(len(s))), len(s), s


def paired(a, b, col="r15"):
    """Date-clustered paired difference: per-date means, dates in both."""
    sa = a.groupby("day")[col].mean()
    sb = b.groupby("day")[col].mean()
    j = pd.concat([sa, sb], axis=1, keys=["a", "b"], sort=True).dropna()
    dd = j["a"] - j["b"]
    if len(dd) < 3:
        return np.nan, np.nan, len(dd)
    return dd.mean(), dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd))), len(dd)


def standardise(ev, pool, keys, col="r15"):
    """Direct standardisation of the pool onto the events' strata mix."""
    w = ev.groupby(keys).size() / len(ev)
    m = pool.groupby(keys)[col].mean()
    j = pd.concat([w, m], axis=1, keys=["w", "m"]).dropna()
    cover = j["w"].sum()
    return (j["w"] * j["m"]).sum() / cover, cover


def quint(x):
    return pd.qcut(x, 5, labels=False, duplicates="drop")


# ------------------------------------------------------------ main ----------
def main():
    line = gate()
    p("RP-012A STAGE 1 -- DISCOVERY ONLY, 2021-01-04 .. 2023-12-29")
    p("  Descriptive. No entry, stop, target, expectancy or prop simulation.")
    p("  2024-2025 NOT opened.")
    p("")
    p(f"PLATFORM GATE: {line}")
    p("")
    frames, bars, n_half = {}, {}, {}
    for s in PRIMARY + CONTROL:
        bars[s], frames[s], n_half[s] = build(s)

    # ================================================ COUNTS BEFORE OUTCOMES
    p("=== 1. COUNTS, BEFORE ANY FORWARD RETURN ===")
    p("  blocks (frozen, from rp012a_common.BLOCKS): opening 09:35-10:00,")
    p("  morning 10:00-11:30, midday 11:30-14:00, closing 14:00-15:50")
    p("")
    p(f"  {'instr':<6}{'avail':>7}{'half':>6}{'used':>6}{'warmup':>8}{'labelled':>9}"
      f"{'no-valid':>9}{'elig win':>10}")
    for s, W in frames.items():
        n = W["day"].nunique()
        labd = W[W["state"] != "WARMUP"]
        nv = int((W.groupby("day")["valid"].sum() == 0).sum())
        p(f"  {s:<6}{n + n_half[s]:>7}{n_half[s]:>6}{n:>6}"
          f"{n - labd['day'].nunique():>8}{labd['day'].nunique():>9}{nv:>9}"
          f"{int(labd['feat_ok'].sum()):>10}")
    p("  'no-valid' = sessions excluded for missing data (no valid window at all)")
    p("  zero / missing volume: a missing bar is no trading, never substituted;")
    p("  < 4 bars voids a window everywhere; a zero median voids its RV")
    p("")
    p(f"  {'instr':<6}{'A cand':>8}{'A ev':>7}{'B cand':>8}{'B ev':>7}{'C obs':>8}"
      f"{'cooled%':>9}{'ev/sess':>9}{'ev/month':>10}")
    for s, W in frames.items():
        l = W[W["state"] != "WARMUP"]
        ns = l["day"].nunique()
        mo = l["day"].dt.to_period("M").nunique()
        cand = l["state"].isin(["A", "B"]) & (l["side"] != "flat")
        ev = l[l["event"]]
        p(f"  {s:<6}{int((l.state=='A').sum()):>8}{int((ev.state=='A').sum()):>7}"
          f"{int((l.state=='B').sum()):>8}{int((ev.state=='B').sum()):>7}"
          f"{int((l.state=='C').sum()):>8}"
          f"{100*(1-len(ev)/cand.sum()):>8.1f}%{len(ev)/ns:>9.2f}{len(ev)/mo:>10.1f}")
    p("")
    ALL = pd.concat(frames.values(), ignore_index=True)
    ev = ALL[(ALL["state"] != "WARMUP") & ALL["event"]]
    p("  events by year, block and sign:")
    for s in frames:
        e = ev[ev.sym == s]
        for st in ("A", "B"):
            x = e[e.state == st]
            yr = " ".join(f"{y}:{n}" for y, n in x.year.value_counts().sort_index().items())
            bl = " ".join(f"{b[2]}:{int((x.block==b[2]).sum())}" for b in C.BLOCKS)
            p(f"    {s:<4}{st}  sessions {x['day'].nunique():>3}  +{int((x.side=='buy').sum()):>4}"
              f" -{int((x.side=='sell').sum()):>4}  | {yr} | {bl}")
    pe = ev[ev.sym.isin(PRIMARY)]
    co = pe.groupby(["day", "k"]).sym.nunique()
    p(f"  simultaneous cross-instrument events: {int((co>=2).sum())} slots, "
      f"{100*(pe.set_index(['day','k']).index.map(co)>=2).mean():.1f}% of primary events")
    p("")

    # six Stage 0 conditions, re-checked
    conds = []
    s1 = min(ev[(ev.sym == s) & (ev.state == st)]["day"].nunique()
             for s in PRIMARY for st in ("A", "B"))
    conds.append(("1 A and B each in >= 30 sessions", s1 >= 30, f"min {s1}"))
    ws = {b: (hi - lo) / (C.LAST_MIN - C.FIRST_MIN) for lo, hi, b in C.BLOCKS}
    sh = [ev[ev.sym == s].block.value_counts(normalize=True).get(b, 0) / ws[b]
          for s in PRIMARY for b in ws]
    conds.append(("2 block share 0.5-2.0x window share",
                  all(0.5 <= x <= 2 for x in sh), f"{min(sh):.2f}-{max(sh):.2f}x"))
    emp = [(s, st, b) for s in PRIMARY for st in ("A", "B") for b in ws
           if not len(ev[(ev.sym == s) & (ev.state == st) & (ev.block == b)])]
    conds.append(("3 every block has A and B", not emp, f"{emp}"))
    bsh = [100 * (ev[(ev.sym == s) & (ev.state == st)].side == "buy").mean()
           for s in PRIMARY for st in ("A", "B")]
    conds.append(("4 buy share 40-60%", all(40 <= x <= 60 for x in bsh),
                  f"{min(bsh):.1f}-{max(bsh):.1f}%"))
    rr = []
    for s in PRIMARY:
        l = ALL[(ALL.sym == s) & (ALL.state != "WARMUP") & ALL.feat_ok]
        abn = l.state.isin(["A", "B", "ABN_MID"])
        rr += [abn[l.block == b].mean() / abn.mean() for b in ws]
    conds.append(("5 abnormal rate 0.5-2.0x per block",
                  all(0.5 <= x <= 2 for x in rr), f"{min(rr):.2f}-{max(rr):.2f}x"))
    miss = [(s, st, y) for s in PRIMARY for st in ("A", "B") for y in (2021, 2022, 2023)
            if not len(ev[(ev.sym == s) & (ev.state == st) & (ev.year == y)])]
    conds.append(("6 every year in every cell", not miss, f"{miss}"))
    for n, ok, dtl in conds:
        p(f"  [{'PASS' if ok else 'FAIL'}] {n:<40}{dtl}")
    if not all(c[1] for c in conds):
        p("\n  COUNT CONDITION FAILED -- STOPPING BEFORE ANY OUTCOME.")
        (OUT / "rp012a_stage1_output.txt").write_text("\n".join(L))
        print("\n".join(L))
        return 3
    p("  all six Stage 0 count conditions remain satisfied")
    p("")

    # ================================================ OUTCOMES
    for s in frames:
        frames[s] = outcomes(bars[s], frames[s])
    ALL = pd.concat(frames.values(), ignore_index=True)
    ALL.to_parquet(OUT / "rp012a_stage1_windows.parquet")
    lab = ALL[(ALL["state"] != "WARMUP") & ALL["feat_ok"] & (ALL["side"] != "flat")]
    ev = lab[lab["event"]]
    nopath = int(ev["p0"].isna().sum())
    p(f"  events with no entry bar (no outcome): {nopath}")
    p("")
    p("=== 2. FORWARD OUTCOMES -- direction-adjusted bps, strictly after the window ===")
    for s in PRIMARY + CONTROL:
        for st in ("A", "B"):
            g = ev[(ev.sym == s) & (ev.state == st)]
            p(f"  {s} state {st}  (n={len(g)}, {g['day'].nunique()} sessions)")
            p(f"    {'h':<5}{'mean':>8}{'median':>8}{'MFE':>8}{'MAE':>8}{'cont%':>7}"
              f"{'rev%':>7}{'orig%':>7}{'brk%':>7}{'clus':>8}{'t':>7}")
            for h in C.HORIZONS:
                r = g[f"r{h}"].dropna()
                m, t, _, _ = clus(g, f"r{h}")
                p(f"    {str(h)+'m':<5}{r.mean():>+8.3f}{r.median():>+8.3f}"
                  f"{g[f'mfe{h}'].mean():>8.2f}{g[f'mae{h}'].mean():>8.2f}"
                  f"{100*(r>0).mean():>7.1f}{100*(r<0).mean():>7.1f}"
                  f"{100*g[f'orig{h}'].mean():>7.1f}{100*g[f'brk{h}'].mean():>7.1f}"
                  f"{m:>+8.3f}{t:>+7.2f}")
            p(f"    median minutes to one typical 5-min move: continue "
              f"{g.t_cont.median():.0f} ({100*g.t_cont.notna().mean():.0f}% reach), "
              f"reverse {g.t_rev.median():.0f} ({100*g.t_rev.notna().mean():.0f}%)")
    p("")
    p("  positive and negative displacement separately, 15 min:")
    p(f"  {'instr':<6}{'st':<4}{'buy n':>7}{'buy':>9}{'sell n':>8}{'sell':>9}")
    for s in PRIMARY + CONTROL:
        for st in ("A", "B"):
            g = ev[(ev.sym == s) & (ev.state == st)]
            b, sl = g[g.side == "buy"], g[g.side == "sell"]
            p(f"  {s:<6}{st:<4}{len(b):>7}{b.r15.mean():>+9.3f}{len(sl):>8}"
              f"{sl.r15.mean():>+9.3f}")
    p("")
    p("  by year, 15 min (event mean):")
    p("  " + ev[ev.sym.isin(PRIMARY + CONTROL)].pivot_table(
        index=["sym", "state"], columns="year", values="r15", aggfunc="mean")
      .round(3).to_string().replace("\n", "\n  "))
    p("")
    p("  by block, 15 min (event mean):")
    p("  " + ev[ev.sym.isin(PRIMARY + CONTROL)].pivot_table(
        index=["sym", "state"], columns="block", values="r15", aggfunc="mean")
      [[b[2] for b in C.BLOCKS]].round(3).to_string().replace("\n", "\n  "))
    p("")

    # ================================================ CONTROLS
    p("=== 3. LOAD-BEARING CONTROLS, 15 min ===")
    p("  'material' = date-clustered paired diff >= 1 RT cost AND t >= 2.0")
    p("")
    rng = np.random.default_rng(SEED)
    verdict = {}
    for s in PRIMARY + CONTROL:
        l = lab[lab.sym == s].copy()
        A = ev[(ev.sym == s) & (ev.state == "A")].copy()
        rt = A["rt_bps"].mean()
        mat = l[l.state == "C"]
        mat = mat[mat.rd >= mat.rd_mat].copy()
        # RD quintiles on the material range, shared cut points
        cuts = np.nanquantile(pd.concat([A.rd, mat.rd]), [.2, .4, .6, .8])
        for x in (A, mat):
            x["rdq"] = np.searchsorted(cuts, x["rd"])
        disp_std, disp_cov = standardise(A, mat, ["block", "rdq"])
        dd, dt, dn = paired(A, mat)
        B = ev[(ev.sym == s) & (ev.state == "B")]
        mid = l[l.state == "ABN_MID"]
        Cc = l[l.state == "C"].copy()
        vcuts = np.nanquantile(pd.concat([A.abs_med, Cc.abs_med]), [.2, .4, .6, .8])
        A["vq"] = np.searchsorted(vcuts, A["abs_med"])
        Cc["vq"] = np.searchsorted(vcuts, Cc["abs_med"])
        ord_std, ord_cov = standardise(A, Cc, ["block", "vq"])
        od, ot, _ = paired(A, Cc)
        AB = l[l.abs_event]
        ad, at_, _ = paired(A, AB)
        bd, bt, _ = paired(A, B)
        raw = (A["r15"] * np.where(A.side == "buy", 1, -1)).dropna().to_numpy()
        draws = np.array([np.mean(raw * rng.choice([-1, 1], len(raw)))
                          for _ in range(1000)])
        am = A.r15.mean()
        p(f"  {s}  state A mean {am:+.3f} bps (n {A.r15.notna().sum()}), RT {rt:.3f}")
        p(f"    1 displacement only, C & RD>=p80    n {len(mat):>6}  mean "
          f"{mat.r15.mean():+.3f}  standardised {disp_std:+.3f} (cover {100*disp_cov:.0f}%)"
          f"  | A-minus paired {dd:+.3f} t {dt:+.2f} ({dn} dates)")
        p(f"    2 volume only: state B              n {len(B):>6}  mean "
          f"{B.r15.mean():+.3f}  | A-minus paired {bd:+.3f} t {bt:+.2f}")
        p(f"      volume only: abnormal RV, RD p50-80 n {len(mid):>5}  mean "
          f"{mid.r15.mean():+.3f}")
        p(f"    3 ordinary, vol x block matched     n {len(Cc):>6}  mean "
          f"{Cc.r15.mean():+.3f}  standardised {ord_std:+.3f} (cover {100*ord_cov:.0f}%)"
          f"  | A-minus paired {od:+.3f} t {ot:+.2f}")
        p(f"    4 absolute volume, cooled           n {len(AB):>6}  mean "
          f"{AB.r15.mean():+.3f}  | A-minus paired {ad:+.3f} t {at_:+.2f}  "
          f"overlap with A {100*AB.index.isin(A.index).mean():.0f}%")
        p(f"    5 random direction, 1000 draws      mean {draws.mean():+.3f}  "
          f"95% [{np.percentile(draws,2.5):+.3f}, {np.percentile(draws,97.5):+.3f}]  "
          f"A's rank {100*(draws<am).mean():.1f}th pct")
        verdict[s] = dict(A=am, rt=rt, disp_d=dd, disp_t=dt, B_d=bd, B_t=bt,
                          abs_d=ad, abs_t=at_, ord_d=od, ord_t=ot, abs_m=AB.r15.mean(),
                          disp_m=mat.r15.mean(), disp_std=disp_std)
    p("")

    # ================================================ INDEPENDENCE
    p("=== 4. INDEPENDENCE AND CONCENTRATION, state A, 15 min ===")
    p(f"  {'set':<9}{'event':>8}{'clus':>8}{'t':>7}{'dates':>7}{'dates+':>8}"
      f"{'LOO min':>9}{'LOO max':>9}{'-best1':>8}{'-best5':>8}{'best5 sh':>10}")
    conc = {}
    sets = {s: ev[(ev.sym == s) & (ev.state == "A")] for s in PRIMARY + CONTROL}
    sets["POOLED"] = ev[ev.sym.isin(PRIMARY) & (ev.state == "A")]
    for nm, g in sets.items():
        m, t, n, sd = clus(g)
        o = sd.sort_values(ascending=False)
        loo = [(sd.sum() - v) / (len(sd) - 1) for v in sd]
        b1 = sd.drop(o.index[:1]).mean()
        b5 = sd.drop(o.index[:5]).mean()
        share = 100 * o.iloc[:5].sum() / sd.sum() if sd.sum() != 0 else np.nan
        conc[nm] = dict(m=m, t=t, b5=b5, share=share, pos=int((sd > 0).sum()), n=n)
        p(f"  {nm:<9}{g.r15.mean():>+8.3f}{m:>+8.3f}{t:>+7.2f}{n:>7}{int((sd>0).sum()):>8}"
          f"{min(loo):>+9.3f}{max(loo):>+9.3f}{b1:>+8.3f}{b5:>+8.3f}{share:>9.1f}%")
    p("  POOLED = QQQ+SPY+IWM, one observation per DATE (38.6% of events co-occur)")
    p("")
    p("  state A by month, pooled primary, date-clustered mean (bps):")
    mo = sets["POOLED"].groupby(sets["POOLED"]["day"].dt.to_period("M"))["r15"].mean()
    p("  " + "  ".join(f"{str(k)[2:]}:{v:+.1f}" for k, v in mo.items()))
    p(f"  months positive: {int((mo>0).sum())} of {len(mo)}")
    p("")

    # ================================================ COMMERCIAL
    p("=== 5. COMMERCIAL HURDLE, state A, 15 min ===")
    inv = pd.read_csv(OUT / "rp012a_stage0_inventory.csv")
    inv = inv[inv["period"] == "discovery 2021-2023"].set_index("instr")
    p(f"  {'instr':<6}{'gross':>8}{'median':>8}{'RT':>7}{'net':>8}{'hurdle':>8}"
      f"{'clears':>8}{'1.2ATR':>8}{'gross/cont':>11}{'cost/risk':>10}{'trades/mo':>10}")
    for s in PRIMARY + CONTROL:
        g = sets[s]
        cont = 1.2 * float(inv.loc[s, "atr1m_bps"])
        gr, rt = g.r15.mean(), g.rt_bps.mean()
        hur = HURDLE.get(s, 3 * rt)
        mo_ = g["day"].dt.to_period("M").nunique()
        p(f"  {s:<6}{gr:>+8.3f}{g.r15.median():>+8.3f}{rt:>7.3f}{gr-rt:>+8.3f}"
          f"{hur:>8.3f}{('YES' if gr >= hur else 'no'):>8}{cont:>8.2f}"
          f"{gr/cont:>+11.3f}{100*rt/cont:>9.1f}%{len(g)/mo_/3:>10.1f}")
    p("  trades/mo = state-A events per month x one-third confirmation retention")
    p("")

    txt = "\n".join(L)
    print(txt)
    (OUT / "rp012a_stage1_output.txt").write_text(txt)
    pd.DataFrame(verdict).T.to_csv(OUT / "rp012a_stage1_controls.csv")
    pd.DataFrame(conc).T.to_csv(OUT / "rp012a_stage1_concentration.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
