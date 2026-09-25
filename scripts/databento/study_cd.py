#!/usr/bin/env python3
"""Studies (c) and (d), pre-registered at reports/db_cd_preregistration.md
(commit e68b18c) before either rule touched any data.

IMPLEMENTATION (fixed before this script first ran):
  (c) A decision at mark M (10:00 ... 15:30) uses the close of the bar that ENDS at
      M (the bar starting at M-1) and executes at the open of the bar starting at M,
      or the next existing bar. sigma(t) needs >= 10 of the prior 14 sessions to
      exist at that minute; otherwise no decision is taken at that mark. A reversal
      pays one exit and one entry. Random-direction null: every trade keeps its
      entry and exit times and has its sign flipped with probability 1/2 (the
      trailing-stop path itself depends on direction, so this null is
      conservative toward the rule).
  (d) The "previous bar" for the 09:30 sweep test is the last overnight bar of the
      same session. Random-direction null: the mirror trade (same entry, stop and
      2R target reflected) is simulated on the same bars, and each trade is
      replaced by its mirror with probability 1/2.
  Both: a tradeable session is a full session whose RTH is one contract.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data/clean"
OUT = ROOT / "reports"
SEED = 20260925
N_SIM = 5000
REG = pd.Timestamp("2026-09-25")
TICK = 0.25
SPEC = {"NQ": (20.0, 2 * (2.25 + 5.00), 2.0, 2 * (0.62 + 0.50)),
        "ES": (50.0, 2 * (2.25 + 12.50), 5.0, 2 * (0.62 + 1.25))}
BLOCKS = [("2010-2020 [never used for this hypothesis; read by other studies, incl. study (b)] -- DECISIVE",
           pd.Timestamp("2010-01-01"), pd.Timestamp("2020-12-31")),
          ("2021-registration [seen; not decisive]", pd.Timestamp("2021-01-01"), REG - pd.Timedelta(days=1))]
L = []
p = L.append


def sessions(sym):
    fs = sorted(glob.glob(str(CLEAN / f"bars_1m/{sym}_*.parquet")))
    b = pd.concat([pd.read_parquet(f) for f in fs]).sort_values("ts_et")
    b["m"] = (b.ts_et.dt.hour * 60 + b.ts_et.dt.minute) - 570
    D = pd.read_parquet(CLEAN / f"daily/{sym}_daily.parquet").set_index("session")
    return b, D


# ------------------------------------------------------------------ (c) -----
def run_c(sym):
    b, D = sessions(sym)
    r = b[b.rth]
    full = [s for s in D.index if not D.at[s, "half_day"]]
    mov, meta = {}, {}
    for s, g in r.groupby("session"):
        if s not in D.index or D.at[s, "half_day"] or g.instrument_id.nunique() != 1:
            continue
        m = g.m.to_numpy()
        if m.min() > 4 or m.max() < 389:
            continue
        o = g.open.to_numpy()[0]
        arr = np.full(390, np.nan)
        arr[m] = np.abs(g.close.to_numpy() / o - 1)
        mov[s] = arr
        meta[s] = g
    days = sorted(mov)
    trades = []
    prev_close, prev_id = None, None
    for i, s in enumerate(days):
        g = meta[s]
        hist = [mov[d] for d in days[max(0, i - 14):i]]
        if len(hist) < 14:
            prev_close, prev_id = g.close.to_numpy()[-1], g.instrument_id.iloc[0]
            continue
        H = np.vstack(hist)
        cnt = np.sum(~np.isnan(H), axis=0)
        sig = np.where(cnt >= 10, np.nanmean(H, axis=0), np.nan)
        m = g.m.to_numpy()
        o_, h_, l_, c_, v_ = (g[x].to_numpy() for x in ("open", "high", "low", "close", "volume"))
        op = o_[0]
        pc = prev_close if prev_id == g.instrument_id.iloc[0] else op
        tp = (h_ + l_ + c_) / 3
        cumv = np.cumsum(v_)
        vwap = np.cumsum(tp * v_) / np.maximum(cumv, 1)
        idx_of = {mm: k for k, mm in enumerate(m)}
        pos, entry, etime = 0, None, None
        for mark in range(30, 361, 30):
            kb = idx_of.get(mark - 1)
            if kb is None or np.isnan(sig[mark - 1]):
                continue
            ub = max(op, pc) * (1 + sig[mark - 1])
            lb = min(op, pc) * (1 - sig[mark - 1])
            cl = c_[kb]
            ke = next((k for k in range(kb + 1, len(m)) if m[k] >= mark), None)
            if ke is None:
                break
            px = o_[ke]
            if pos == 1 and cl < max(ub, vwap[kb]):
                trades.append((s, 1, entry, px, etime, m[ke])); pos = 0
            elif pos == -1 and cl > min(lb, vwap[kb]):
                trades.append((s, -1, entry, px, etime, m[ke])); pos = 0
            if pos == 0:
                if cl > ub:
                    pos, entry, etime = 1, px, m[ke]
                elif cl < lb:
                    pos, entry, etime = -1, px, m[ke]
        if pos != 0:
            trades.append((s, pos, entry, c_[-1], etime, m[-1]))
        prev_close, prev_id = c_[-1], g.instrument_id.iloc[0]
    T = pd.DataFrame(trades, columns=["session", "side", "entry", "exit", "t_in", "t_out"])
    T["pts"] = T.side * (T.exit - T.entry)
    return T, D, days


# ------------------------------------------------------------------ (d) -----
def exit_path(o, h, l, c, i0, side, stop, target):
    for k in range(i0, len(o)):
        if side > 0:
            if o[k] <= stop: return o[k], k
            if l[k] <= stop: return stop, k
            if h[k] >= target: return target, k
        else:
            if o[k] >= stop: return o[k], k
            if h[k] >= stop: return stop, k
            if l[k] <= target: return target, k
    return c[-1], len(o) - 1


def run_d(sym="NQ"):
    b, D = sessions(sym)
    rows = []
    days = []
    prev = None
    for s, g in b.groupby("session"):
        if s not in D.index:
            continue
        rt = g[g.rth]
        ov = g[(~g.rth) & (g.m < 0)]          # 18:00 prior day -> 09:29
        if D.at[s, "half_day"] or rt.empty or rt.instrument_id.nunique() != 1:
            prev = (rt, s) if not rt.empty else prev
            continue
        iid = rt.instrument_id.iloc[0]
        lv = {}
        if prev is not None and not prev[0].empty and prev[0].instrument_id.iloc[-1] == iid:
            lv["PDH"], lv["PDL"] = prev[0].high.max(), prev[0].low.min()
        ov = ov[ov.instrument_id == iid]
        if len(ov):
            lv["ONH"], lv["ONL"] = ov.high.max(), ov.low.min()
        days.append(s)
        seq = pd.concat([ov.tail(1), rt])          # last overnight bar precedes 09:30
        o, h, l, c = (seq[x].to_numpy() for x in ("open", "high", "low", "close"))
        m = seq.m.to_numpy()
        cand = []
        for name, level in lv.items():
            high = name in ("PDH", "ONH")
            for j in range(1, len(o)):
                if not (0 <= m[j] < 330):
                    continue
                if high and h[j] >= level + TICK and c[j - 1] < level:
                    break
                if (not high) and l[j] <= level - TICK and c[j - 1] > level:
                    break
            else:
                continue
            k = next((k for k in range(j, min(j + 5, len(o))) if (c[k] < level if high else c[k] > level)), None)
            if k is None or k + 1 >= len(o):
                continue
            side = -1 if high else 1
            e = o[k + 1]
            stop = (h[j:k + 1].max() + TICK) if high else (l[j:k + 1].min() - TICK)
            risk = (stop - e) if high else (e - stop)
            if risk <= 0:
                continue
            tgt = e + side * 2 * risk
            px, kx = exit_path(o, h, l, c, k + 1, side, stop, tgt)
            ms, mt = e - side * risk, e - side * 2 * risk
            mpx, _ = exit_path(o, h, l, c, k + 1, -side, ms, mt)
            cand.append((k + 1, kx, name, side, side * (px - e), -side * (mpx - e)))
        last = -1
        for ein, ex, name, side, pts, mpts in sorted(cand):
            if ein > last:
                rows.append((s, name, side, pts, mpts))
                last = ex
        prev = (rt, s)
    T = pd.DataFrame(rows, columns=["session", "level", "side", "pts", "mir_pts"])
    return T, D, days


# ------------------------------------------------------------------ stats ---
def evaluate(T, D, days, sym, a, bnd, mirror=None, rng=None):
    mult, rt, mm, mrt = SPEC[sym]
    idx = pd.Index([d for d in days if a <= d <= bnd])
    X = T[(T.session >= a) & (T.session <= bnd)]
    def daily(pts, mult_, rt_):
        v = pd.Series(pts * mult_ - rt_, index=X.session.values)
        return v.groupby(level=0).sum().reindex(idx, fill_value=0.0)
    pnl = daily(X.pts.to_numpy(), mult, rt)
    pnm = daily(X.pts.to_numpy(), mm, mrt)
    tr = X.pts.to_numpy() * mult - rt
    sh = pnl.mean() / pnl.std(ddof=1) * np.sqrt(252)
    pf = tr[tr > 0].sum() / -tr[tr < 0].sum()
    close = D.close.reindex(idx).shift(1) * mult
    cagr = np.prod(1 + (pnl / close).fillna(0)) ** (252 / len(pnl)) - 1
    dd = lambda s: float((s.cumsum().cummax() - s.cumsum()).max())
    sims = np.empty(N_SIM)
    alt = X[mirror].to_numpy() if mirror else -X.pts.to_numpy()
    pos = idx.get_indexer(X.session.values)
    base = X.pts.to_numpy()
    for i in range(N_SIM):
        flip = rng.random(len(base)) < 0.5
        v = np.where(flip, alt, base) * mult - rt
        arr = np.zeros(len(idx)); np.add.at(arr, pos, v)
        sims[i] = arr.mean() / arr.std(ddof=1) * np.sqrt(252)
    pv = (1 + (sims >= sh).sum()) / (N_SIM + 1)
    yr = pnl.groupby(pnl.index.year).sum()
    return dict(sharpe=sh, pf=pf, cagr=cagr, n=len(X), dd=dd(pnl), dd_m=dd(pnm),
                total=float(pnl.sum()), p=pv, p95=np.percentile(sims, 95), yr=yr,
                win=float((tr > 0).mean()))


def report(title, runs, rng):
    p(f"=== {title} ===")
    res = {}
    for key, (T, D, days, sym, mir) in runs.items():
        for lab, a, bnd in BLOCKS:
            r = evaluate(T, D, days, sym, a, bnd, mirror=mir, rng=rng)
            res[(key, lab[:4])] = r
            micro = "MNQ" if sym == "NQ" else "MES"
            p(f"  {key} | {lab}")
            p(f"    Sharpe {r['sharpe']:+.2f}  CAGR {100*r['cagr']:.2f}%  PF {r['pf']:.2f}  trades {r['n']}"
              f"  win {100*r['win']:.1f}%  maxDD ${r['dd']:,.0f}/{sym} ${r['dd_m']:,.0f}/{micro}  total ${r['total']:,.0f}")
            p(f"    random-direction null: 95th pct {r['p95']:+.2f}, p = {r['p']:.4f}")
            p("    per year $: " + "  ".join(f"{y}:{v:+,.0f}" for y, v in r["yr"].items()))
    return res


def holm(ps):
    order = sorted(ps.items(), key=lambda t: t[1])
    out, run = {}, 0.0
    for i, (k, v) in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * v))
        out[k] = run
    return out


def main():
    rng = np.random.default_rng(SEED)
    p("STUDIES (c) AND (d) -- pre-registered e68b18c. Costs per side: NQ/ES $2.25 + 1 tick,")
    p("MNQ/MES $0.62 + 1 tick. Entry next bar open; honest stop fills; stop first.")
    p("")
    runs_c = {}
    for sym in ("ES", "NQ"):
        T, D, days = run_c(sym)
        runs_c[f"(c) {sym}"] = (T, D, days, sym, None)
    rc = report("(c) NOISE-BOUNDARY INTRADAY MOMENTUM (Zarattini, Aziz & Barbon 2024)", runs_c, rng)
    hc = holm({k: rc[(k, "2010")]["p"] for k in runs_c})
    p("")
    T, D, days = run_d("NQ")
    rd = report("(d) LIQUIDITY SWEEP -- PDH/PDL/ONH/ONL, fade the reclaim, 2R", {"(d) NQ": (T, D, days, "NQ", "mir_pts")}, rng)
    p("  (d) by level, decisive block, $ per NQ trade after costs:")
    X = T[(T.session <= pd.Timestamp("2020-12-31"))]
    for lv, g in X.groupby("level"):
        v = g.pts * SPEC["NQ"][0] - SPEC["NQ"][1]
        p(f"    {lv}: n {len(g)}  mean ${v.mean():+.1f}  win {100*(v>0).mean():.1f}%")
    p("")
    p("=== KILL CRITERIA, 2010-2020 block (Sharpe >= 0.8, PF >= 1.3, null Holm p <= 0.05) ===")
    for k in runs_c:
        r = rc[(k, "2010")]
        ok = [r["sharpe"] >= 0.8, r["pf"] >= 1.3, hc[k] <= 0.05]
        p(f"  {k}: Sharpe {r['sharpe']:+.2f} {'PASS' if ok[0] else 'FAIL'} | PF {r['pf']:.2f} "
          f"{'PASS' if ok[1] else 'FAIL'} | Holm p {hc[k]:.4f} {'PASS' if ok[2] else 'FAIL'}"
          f"  => {'SURVIVES (forward data required)' if all(ok) else 'KILLED'}")
    r = rd[("(d) NQ", "2010")]
    ok = [r["sharpe"] >= 0.8, r["pf"] >= 1.3, r["p"] <= 0.05]
    p(f"  (d) NQ: Sharpe {r['sharpe']:+.2f} {'PASS' if ok[0] else 'FAIL'} | PF {r['pf']:.2f} "
      f"{'PASS' if ok[1] else 'FAIL'} | p {r['p']:.4f} {'PASS' if ok[2] else 'FAIL'}"
      f"  => {'SURVIVES (forward data required)' if all(ok) else 'KILLED'}")
    txt = "\n".join(L)
    print(txt)
    (OUT / "db_cd_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
