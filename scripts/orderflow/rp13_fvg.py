#!/usr/bin/env python3
"""RP-13 -- FVG family, multi-timeframe. DISCOVERY. No OOS block exists.

Pre-registered at reports/rp13_fvg_preregistration.md, commit adb6226, BEFORE
this file existed. Every [FROZEN READING] there is implemented here unchanged.

Data: QQQ 1-minute RTH 2016-01-04 .. 2026-08-31 (2,680 sessions), declared
substitute for NQ. Resampled in-script to 2, 3, 5, 15, 30, 60 minutes.

Order of work, as registered: gate -> counts before R -> cost/risk rejection ->
grid demotion -> primary R -> mechanism control (STOP if it fails at all four)
-> placebo, timing, iFVG -> max-statistic permutation -> promotion table.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dataquality as DQ                                            # noqa: E402
import holdout as HO                                                # noqa: E402,F401
import sessioncal as SC                                             # noqa: E402

OUT = ROOT / "reports"
PRIMARY = (1, 2, 3, 5)
DIAG = (15, 30, 60)
ATR_N = 14
GAP_ATR, DISP_ATR = 1.0, 1.5
SWEEP_BARS = 5
TICK = 0.01
TARGET_R = 2.0
COST_BPS = 0.667
MAX_COST_RISK = 0.10
MIN_SETUPS_MONTH = 12
N_PERM = 10_000
SEED = 20260925
KILLZONE = (0, 90)        # 09:30-11:00 ET, minutes after the open
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


# ---------------------------------------------------------------- data ------
def load():
    d = pd.concat([pd.read_parquet(ROOT / "data/intraday_long/QQQ_1m_holdout.parquet"),
                   pd.read_parquet(ROOT / "data/intraday_long/QQQ_1m.parquet")],
                  ignore_index=True)
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    d["day"] = d["timestamp"].dt.normalize()
    d["m"] = d["timestamp"].dt.hour * 60 + d["timestamp"].dt.minute - 570
    half = {pd.Timestamp(x) for x in SC.early_closes(d, ts_col="timestamp", clock="ET")}
    close_m = np.where(d["day"].isin(half), 210, 390)
    d = d[(d["m"] >= 0) & (d["m"] < close_m)].reset_index(drop=True)
    # prior-session RTH high/low, half days included as the prior session
    dh = d.groupby("day").agg(H=("high", "max"), Lo=("low", "min"))
    dh["PDH"], dh["PDL"] = dh["H"].shift(1), dh["Lo"].shift(1)
    d = d[~d["day"].isin(half)].reset_index(drop=True)
    d = d.merge(dh[["PDH", "PDL"]], left_on="day", right_index=True, how="left")
    d = d[d["PDH"].notna()].reset_index(drop=True)
    DQ.assert_safe_columns(d, "RP-13 bars")
    return d, half


def resample(d, tf):
    if tf == 1:
        b = d.copy()
        b["bi"] = b["m"]
    else:
        b = d.assign(bi=d["m"] // tf)
        b = b.groupby(["day", "bi"]).agg(open=("open", "first"), high=("high", "max"),
                                         low=("low", "min"), close=("close", "last"),
                                         m=("m", "first"), PDH=("PDH", "first"),
                                         PDL=("PDL", "first")).reset_index()
    b = b.sort_values(["day", "bi"]).reset_index(drop=True)
    new = b["day"].ne(b["day"].shift()).to_numpy()
    pc = b["close"].shift(1).to_numpy()
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    tr = np.where(new, h - l, np.maximum(h, pc) - np.minimum(l, pc))
    b["atr"] = pd.Series(tr).rolling(ATR_N).mean().to_numpy()
    # raid bars: fresh excursion beyond PDH / PDL within the session
    ph = np.where(new, -np.inf, np.r_[np.nan, h[:-1]])
    pl = np.where(new, np.inf, np.r_[np.nan, l[:-1]])
    b["raid_hi"] = (h > b["PDH"].to_numpy()) & ~(ph > b["PDH"].to_numpy())
    b["raid_lo"] = (l < b["PDL"].to_numpy()) & ~(pl < b["PDL"].to_numpy())
    b["sess"] = np.cumsum(new) - 1
    return b


# ---------------------------------------------------------------- patterns --
def detect(b, filtered=True):
    """Three-candle gaps with the sweep prerequisite; ATR filters optional."""
    s = b["sess"].to_numpy()
    h, l, atr = b["high"].to_numpy(), b["low"].to_numpy(), b["atr"].to_numpy()
    n = len(b)
    i = np.arange(2, n)
    same = (s[i] == s[i - 2])
    a1 = atr[i - 2]
    disp = h[i - 1] - l[i - 1]
    # most recent raid bar index at or before each bar, within session
    def last_raid(flag):
        idx = np.where(flag, np.arange(n), -10**9)
        idx = np.maximum.accumulate(idx)
        ss = np.where(idx >= 0, s[np.clip(idx, 0, None)], -1)
        return idx, ss
    rl, rls = last_raid(b["raid_lo"].to_numpy())
    rh, rhs = last_raid(b["raid_hi"].to_numpy())
    out = []
    for side in (1, -1):
        if side == 1:
            g = l[i] - h[i - 2]
            ok = same & (g > 0) & (rls[i] == s[i]) & (i - rl[i] <= SWEEP_BARS)
            top, bot = l[i], h[i - 2]
        else:
            g = l[i - 2] - h[i]
            ok = same & (g > 0) & (rhs[i] == s[i]) & (i - rh[i] <= SWEEP_BARS)
            top, bot = l[i - 2], h[i]
        if filtered:
            ok = ok & np.isfinite(a1) & (g >= GAP_ATR * a1) & (disp >= DISP_ATR * a1)
        k = np.flatnonzero(ok)
        out.append(pd.DataFrame({"c3": i[k], "side": side, "top": top[k],
                                 "bot": bot[k], "gap": g[k], "atr": a1[k]}))
    F = pd.concat(out, ignore_index=True).sort_values("c3").reset_index(drop=True)
    F["sess"] = s[F["c3"].to_numpy()]
    return F


# ---------------------------------------------------------------- trading ---
def session_end(b):
    s = b["sess"].to_numpy()
    last = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    return last[s]


def sim_exit(o, h, l, c, start, end, side, entry, stop, target):
    """Stop-first, honest stop fills, targets at the target, time stop at end."""
    for k in range(start, end + 1):
        if side == 1:
            if o[k] <= stop:
                return o[k], k
            if l[k] <= stop:
                return stop, k
            if h[k] >= target:
                return target, k
        else:
            if o[k] >= stop:
                return o[k], k
            if h[k] >= stop:
                return stop, k
            if l[k] <= target:
                return target, k
    return c[end], end


def trades(b, F, kind="fvg"):
    """Candidate trade per pattern, then one open position at a time."""
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    mm = b["m"].to_numpy()
    days = b["day"].to_numpy()
    se = session_end(b)
    rows = []
    for r in F.itertuples():
        start, end = int(r.c3) + 1, se[int(r.c3)]
        side, top, bot = r.side, r.top, r.bot
        if kind == "ifvg":
            # inversion: a later close through the far side flips direction
            seg = c[start:end + 1]
            inv = np.flatnonzero(seg < bot) if side == 1 else np.flatnonzero(seg > top)
            if not len(inv):
                continue
            start = start + int(inv[0]) + 1
            side = -side
        if start > end:
            continue
        seg_l, seg_h = l[start:end + 1], h[start:end + 1]
        if side == 1:
            t = np.flatnonzero(seg_l <= top)
            stop = bot - TICK
        else:
            t = np.flatnonzero(seg_h >= bot)
            stop = top + TICK
        if not len(t):
            continue
        j = start + int(t[0])
        if j + 1 > end:
            continue
        e = o[j + 1]
        risk = (e - stop) if side == 1 else (stop - e)
        # "at or beyond the stop", float-safe: prices carry sub-penny prints, so a
        # half-cent risk is real, but 1e-13 is floating-point noise for zero
        if risk <= 1e-9:
            rows.append(dict(c3=r.c3, touch=j, entry_i=j + 1, void=True))
            continue
        tgt = e + side * TARGET_R * risk
        res = {}
        for tag, s0 in (("x", j + 2), ("inc", j + 1)):
            if s0 > end:
                px, k = c[end], end
            else:
                px, k = sim_exit(o, h, l, c, s0, end, side, e, stop, tgt)
            res[tag] = (px, k)
        # mirror trade for the permutation: same entry and distances, opposite side
        ms, mt = e + side * risk, e - side * TARGET_R * risk
        mpx, mk = (c[end], end) if j + 2 > end else \
            sim_exit(o, h, l, c, j + 2, end, -side, e, ms, mt)
        cost = COST_BPS * 1e-4 * e / risk
        rows.append(dict(c3=r.c3, touch=j, entry_i=j + 1, void=False, side=side,
                         day=days[j + 1], m_entry=mm[j + 1], entry=e, risk=risk,
                         cost_r=cost,
                         R=side * (res["x"][0] - e) / risk - cost, exit_i=res["x"][1],
                         R_gross=side * (res["x"][0] - e) / risk,
                         R_inc=side * (res["inc"][0] - e) / risk - cost,
                         R_mir=-side * (mpx - e) / risk - cost))
    T = pd.DataFrame(rows)
    if not len(T):
        return T, 0, 0
    voids = int(T["void"].sum())
    T = T[~T["void"]].sort_values("entry_i").reset_index(drop=True)
    keep, last = [], -1
    for r in T.itertuples():
        if r.entry_i > last:
            keep.append(True)
            last = r.exit_i
        else:
            keep.append(False)
    skipped = int((~np.array(keep)).sum())
    T = T[np.array(keep)].reset_index(drop=True)
    DQ.assert_safe_columns(T, f"RP-13 {kind} trades")
    return T, voids, skipped


def placebo(b, F, rng):
    """Random three-candle windows, same session, same ATR-width, same side."""
    s = b["sess"].to_numpy()
    h, l, atr = b["high"].to_numpy(), b["low"].to_numpy(), b["atr"].to_numpy()
    first = np.r_[0, np.flatnonzero(np.diff(s)) + 1]
    se = session_end(b)
    rows = []
    for r in F.itertuples():
        lo = first[r.sess] + 5
        hi = se[int(r.c3)]
        if hi - lo < 3:
            continue
        c3 = int(rng.integers(lo, hi))
        a = atr[c3 - 2]
        if not np.isfinite(a):
            continue
        w = (r.gap / r.atr) * a
        if r.side == 1:
            top, bot = l[c3], l[c3] - w
        else:
            bot, top = h[c3], h[c3] + w
        rows.append(dict(c3=c3, side=r.side, top=top, bot=bot, gap=w, atr=a,
                         sess=r.sess))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- stats -----
def summ(T, col="R"):
    if col not in getattr(T, "columns", []):
        return dict(n=0, mean=np.nan, t=np.nan, lo90=np.nan, ct=np.nan)
    x = T[col].dropna().to_numpy()
    n = len(x)
    if n < 2:
        return dict(n=n, mean=np.nan, t=np.nan, lo90=np.nan, ct=np.nan)
    se = x.std(ddof=1) / np.sqrt(n)
    dm = T.groupby("day")[col].sum()
    ct = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
    return dict(n=n, mean=x.mean(), t=x.mean() / se, lo90=x.mean() - 1.645 * se,
                ct=ct, sd=x.std(ddof=1))


def maxdd(x):
    eq = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq)) if len(x) else 0.0


# ---------------------------------------------------------------- main ------
def main():
    line = gate()
    p("RP-13 -- FVG FAMILY, MULTI-TIMEFRAME -- DISCOVERY (no OOS block)")
    p("  pre-registered at adb6226; QQQ 1m 2016-2026 substituting for NQ")
    p("")
    p(f"PLATFORM GATE: {line}")
    p("")
    d, half = load()
    nsess = d["day"].nunique()
    months = d["day"].dt.to_period("M").nunique()
    p("=== 1. DATA ===")
    p(f"  sessions used {nsess}  (half days excluded {len(half)})  months {months}")
    p(f"  span {d['day'].min().date()} -> {d['day'].max().date()}  "
      f"1-minute bars {len(d):,}")
    p("")

    B, F, Fc = {}, {}, {}
    for tf in PRIMARY + DIAG:
        B[tf] = resample(d, tf)
        F[tf] = detect(B[tf], True)
        Fc[tf] = detect(B[tf], False)

    # ---------------------------------------------- counts before R
    p("=== 2. COUNTS BEFORE ANY R ===")
    p(f"  {'TF':<5}{'bars':>10}{'3-bar gaps+sweep':>18}{'valid FVG':>11}"
      f"{'valid/mo':>10}{'prior/mo':>10}{'trades':>8}{'voids':>7}{'skipped':>9}"
      f"{'trades/mo':>11}")
    prior = {1: "50-100", 2: "30-60", 3: "20-40", 5: "12-25", 15: "5-12",
             30: "3-6", 60: "1-4"}
    T, meta = {}, {}
    for tf in PRIMARY + DIAG:
        T[tf], v, sk = trades(B[tf], F[tf])
        meta[tf] = dict(valid_mo=len(F[tf]) / months, trades_mo=len(T[tf]) / months)
        p(f"  {str(tf)+'m':<5}{len(B[tf]):>10,}{len(Fc[tf]):>18,}{len(F[tf]):>11,}"
          f"{len(F[tf])/months:>10.1f}{prior[tf]:>10}{len(T[tf]):>8}{v:>7}{sk:>9}"
          f"{len(T[tf])/months:>11.1f}")
    p("")
    p("  valid FVGs by side (bull / bear):  " + "  ".join(
        f"{tf}m {int((F[tf].side==1).sum())}/{int((F[tf].side==-1).sum())}"
        for tf in PRIMARY + DIAG))
    p("")
    primary = [tf for tf in PRIMARY if meta[tf]["valid_mo"] >= MIN_SETUPS_MONTH]
    demoted = [tf for tf in PRIMARY if tf not in primary]
    p(f"  GRID RULE (frozen): primary TFs below {MIN_SETUPS_MONTH} valid setups/month")
    p(f"  are demoted to diagnostic BEFORE any R. Demoted: "
      f"{[str(t)+'m' for t in demoted] or 'none'}.  Primary set now: "
      f"{[str(t)+'m' for t in primary] or 'EMPTY'}")
    if not primary:
        p("  -> NO PRIMARY TIMEFRAME REMAINS. Nothing below is promotable; every")
        p("     R is descriptive.")
    p("")

    # ---------------------------------------------- cost gate
    p("=== 3. COST / RISK, before expectancy ===")
    rejected = []
    for tf in PRIMARY + DIAG:
        if not len(T[tf]):
            p(f"  {tf}m: no trades")
            rejected.append(tf)
            continue
        cr = T[tf]["cost_r"].median()
        rej = cr > MAX_COST_RISK
        if rej:
            rejected.append(tf)
        p(f"  {str(tf)+'m':<5} median risk {1e4*(T[tf].risk/T[tf].entry).median():6.2f} bps"
          f"  median cost/risk {100*cr:5.1f}%  {'REJECTED -- R not computed' if rej else 'ok'}")
    p("")

    # ---------------------------------------------- primary R
    p("=== 4. PRIMARY R (net of cost) ===")
    p(f"  {'TF':<5}{'role':<11}{'n':>6}{'mean R':>9}{'90% lo':>9}{'t':>7}{'day t':>7}"
      f"{'incl.entry-bar':>16}{'win%':>7}{'maxDD':>7}")
    stats = {}
    for tf in PRIMARY + DIAG:
        if tf in rejected:
            continue
        role = "PRIMARY" if tf in primary else "diagnostic"
        st = summ(T[tf])
        si = summ(T[tf], "R_inc")
        stats[tf] = st
        p(f"  {str(tf)+'m':<5}{role:<11}{st['n']:>6}{st['mean']:>+9.3f}{st['lo90']:>+9.3f}"
          f"{st['t']:>+7.2f}{st['ct']:>+7.2f}{si['mean']:>+16.3f}"
          f"{100*(T[tf].R>0).mean():>7.1f}{maxdd(T[tf].R.to_numpy()):>7.1f}")
    p("  incl.entry-bar = declared sensitivity: entry bar in the exit search, stop first")
    p("")
    p("  by side:")
    for tf in stats:
        g = T[tf]
        p(f"    {tf}m  long n {int((g.side==1).sum())} {g[g.side==1].R.mean():+.3f}   "
          f"short n {int((g.side==-1).sum())} {g[g.side==-1].R.mean():+.3f}")
    p("  by year (mean R):")
    for tf in stats:
        yr = T[tf].groupby(pd.to_datetime(T[tf].day).dt.year).R.mean()
        p(f"    {tf}m  " + "  ".join(f"{y}:{v:+.2f}" for y, v in yr.items()))
    p("")

    # ---------------------------------------------- mechanism control
    p("=== 5. MECHANISM CONTROL -- no ATR filters, sweep kept ===")
    p("  REGISTERED test: fails at a TF if the control's NET expectancy >= the")
    p("  primary's. Unfiltered gaps can be a cent wide, so the control is")
    p("  cost-dominated and the net test is biased toward PASS. The GROSS line is")
    p("  a diagnostic added after the first run, and is not the registered test.")
    mech = {}
    for tf in PRIMARY + DIAG:
        if tf in rejected:
            continue
        Tc, _, _ = trades(B[tf], Fc[tf])
        sc = summ(Tc)
        passed = stats[tf]["mean"] > sc["mean"]
        mech[tf] = passed
        pg, cg = summ(T[tf], "R_gross"), summ(Tc, "R_gross")
        p(f"  {str(tf)+'m':<5} NET primary {stats[tf]['mean']:+.3f} (n {stats[tf]['n']})  "
          f"control {sc['mean']:+.3f} (n {sc['n']}, med cost/risk "
          f"{100*Tc.cost_r.median():.0f}%)  -> {'PASS' if passed else 'FAIL'}"
          f"{'' if tf in primary else '  [diagnostic]'}")
        p(f"        GROSS primary {pg['mean']:+.3f}  control {cg['mean']:+.3f}  "
          f"-> {'primary better' if pg['mean'] > cg['mean'] else 'CONTROL AS GOOD OR BETTER'}"
          f"   [gross: diagnostic added after the first run]")
    prim_eval = [tf for tf in PRIMARY if tf in mech]
    all_fail = all(not mech[tf] for tf in prim_eval) if prim_eval else True
    p("")
    if all_fail:
        p("  MECHANISM CONTROL FAILS AT EVERY PRIMARY TIMEFRAME EVALUATED.")
        p("  Per the pre-registration: mechanism dead. STOP. Placebo, timing,")
        p("  iFVG and the permutation are not run.")
        finish()
        return 0

    # ---------------------------------------------- other controls
    rng = np.random.default_rng(SEED)
    p("=== 6. PLACEBO, TIMING, iFVG ===")
    for tf in PRIMARY + DIAG:
        if tf in rejected:
            continue
        Tp, _, _ = trades(B[tf], placebo(B[tf], F[tf], rng))
        Ti, _, _ = trades(B[tf], F[tf], kind="ifvg")
        kz = T[tf][(T[tf].m_entry >= KILLZONE[0]) & (T[tf].m_entry < KILLZONE[1])]
        rest = T[tf][~T[tf].index.isin(kz.index)]
        p(f"  {str(tf)+'m':<5} primary {stats[tf]['mean']:+.3f} | placebo "
          f"{summ(Tp)['mean']:+.3f} (n {len(Tp)}) | iFVG {summ(Ti)['mean']:+.3f} "
          f"(n {len(Ti)}) | 09:30-11:00 {kz.R.mean():+.3f} (n {len(kz)}) vs rest "
          f"{rest.R.mean():+.3f} (n {len(rest)})")
    p("")

    # ---------------------------------------------- permutation
    perm_tfs = [tf for tf in primary if tf in stats]
    p("=== 7. MAX-STATISTIC PERMUTATION, random direction, 10,000 draws ===")
    if not perm_tfs:
        p("  no primary timeframe to test")
        pval = np.nan
    else:
        obs = max(abs(stats[tf]["t"]) for tf in perm_tfs)
        arrs = [(T[tf].R.to_numpy(), T[tf].R_mir.to_numpy()) for tf in perm_tfs]
        mx = np.empty(N_PERM)
        for k in range(N_PERM):
            best = 0.0
            for a, m_ in arrs:
                flip = rng.random(len(a)) < 0.5
                x = np.where(flip, m_, a)
                best = max(best, abs(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))))
            mx[k] = best
        pval = (1 + (mx >= obs).sum()) / (N_PERM + 1)
        p(f"  timeframes {[str(t)+'m' for t in perm_tfs]}  observed max|t| {obs:.2f}  "
          f"null 95th pct {np.percentile(mx,95):.2f}  p = {pval:.4f}")
    p("")

    # ---------------------------------------------- promotion
    p("=== 8. PROMOTION TABLE (primary timeframes only) ===")
    for tf in PRIMARY:
        if tf not in stats:
            p(f"  {tf}m: not evaluated ({'cost-rejected' if tf in rejected else 'no trades'})")
            continue
        st, fm = stats[tf], meta[tf]["trades_mo"]
        c = [st["mean"] >= 0.10 and st["lo90"] > 0, fm >= 12, fm * st["mean"] >= 2.0,
             False, None, tf not in rejected, mech.get(tf, False),
             (pval < 0.05) if tf in perm_tfs else False]
        p(f"  {tf}m {'[demoted]' if tf in demoted else ''}  1:{c[0]} 2:{c[1]} 3:{c[2]} "
          f"4:False(no OOS) 5:not run 6:{c[5]} 7:{c[6]} 8:{c[7]}")
    finish()
    return 0


def finish():
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp13_fvg_output.txt").write_text(txt)


if __name__ == "__main__":
    sys.exit(main())
