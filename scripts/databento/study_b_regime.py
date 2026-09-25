#!/usr/bin/env python3
"""Study (b) -- regime switch, strict one-shot replication. Pre-registered at
reports/db_b_regime_switch_prereg.md (commit 7cf6513) before any Databento data
was requested. One frozen specification, run once.

IMPLEMENTATION (fixed before this script first ran):
  * Indicators use RTH daily bars with high, low and close multiplied by the
    session's back-adjust factor. Short sessions and roll days stay in the
    indicator history; they are only excluded from trading.
  * A day's label uses indicators through the PRIOR session's close.
  * Wilder smoothing for ADX; Choppiness = 100*log10(sum TR14 / (maxH14 - minL14))
    / log10(14); efficiency ratio over 10 closes.
  * Entry at the next bar's open after the trigger close. The entry bar's range
    lies after the fill, so it IS searched for exits, stop first -- the honest
    choice. The spec did not exclude it.
  * A tradeable day = full session, one contract through RTH, complete opening
    range (bars in 09:30-09:59), and a trigger bar starting 10:00-14:59.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data/clean"
OUT = ROOT / "reports"
SEED = 20260925
N_SIM = 5000
REG = pd.Timestamp("2026-09-25")
MULT, RT = 20.0, 2 * (2.25 + 5.00)          # NQ: $/pt, round-trip cost incl. 1 tick/side
MMULT, MRT = 2.0, 2 * (0.62 + 0.50)        # MNQ
L = []
p = L.append


# ------------------------------------------------------------------ regime ---
def labels():
    D = pd.read_parquet(CLEAN / "daily/NQ_daily.parquet").sort_values("session")
    D = D[D.n_rth_bars.notna()].reset_index(drop=True)
    h, l, c = D.high * D.adj_factor, D.low * D.adj_factor, D.close * D.adj_factor
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    w = lambda x: pd.Series(x).ewm(alpha=1 / 14, adjust=False).mean()   # Wilder
    atr = w(tr)
    pdi, mdi = 100 * w(pdm) / atr, 100 * w(mdm) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    adx = w(dx)
    er = (c - c.shift(10)).abs() / c.diff().abs().rolling(10).sum()
    chop = 100 * np.log10(tr.rolling(14).sum() / (h.rolling(14).max() - l.rolling(14).min())) / np.log10(14)
    tv = (adx > 25).astype(int) + (er >= 0.30).astype(int) + (chop < 38.2).astype(int)
    cv = (adx < 20).astype(int) + (er < 0.30).astype(int) + (chop > 61.8).astype(int)
    lab = np.where(tv >= 2, "TREND", np.where(cv >= 2, "CHOP", "NEUTRAL"))
    ok = adx.notna() & er.notna() & chop.notna() & (np.arange(len(D)) >= 30)
    D["label_today"] = np.where(ok, lab, "WARMUP")
    D["label"] = D["label_today"].shift(1)          # known at the prior close
    return D.set_index("session")


# ------------------------------------------------------------------ trades ---
def exit_path(o, h, l, c, i0, side, stop, target):
    for k in range(i0, len(o)):
        if side > 0:
            if o[k] <= stop: return o[k]
            if l[k] <= stop: return stop
            if target is not None and h[k] >= target: return target
        else:
            if o[k] >= stop: return o[k]
            if h[k] >= stop: return stop
            if target is not None and l[k] <= target: return target
    return c[-1]


def day_trades(g):
    """Both responses to the day's trigger, and their mirrors (for the null)."""
    m = (g.ts_et.dt.hour * 60 + g.ts_et.dt.minute).to_numpy()
    o, h, l, c = (g[x].to_numpy() for x in ("open", "high", "low", "close"))
    orng = (m >= 570) & (m < 600)
    if orng.sum() < 25 or m.max() < 959:
        return None
    orh, orl = h[orng].max(), l[orng].min()
    height, mid = orh - orl, (orh + orl) / 2
    cand = np.flatnonzero((m >= 600) & (m < 900) & ((c > orh) | (c < orl)))
    if not len(cand) or cand[0] + 1 >= len(o):
        return None
    j = cand[0]
    up = c[j] > orh
    e = o[j + 1]
    res = {}
    # breakout: direction of the break, stop opposite side, exit at 15:59
    bs = 1 if up else -1
    bstop = orl if up else orh
    res["brk"] = bs * (exit_path(o, h, l, c, j + 1, bs, bstop, None) - e)
    res["brk_mir"] = -bs * (exit_path(o, h, l, c, j + 1, -bs, e + (e - bstop), None) - e)
    # fade: against the break, stop at break-side edge + one height, target mid
    fs = -bs
    fstop = orh + height if up else orl - height
    res["fade"] = fs * (exit_path(o, h, l, c, j + 1, fs, fstop, mid) - e)
    res["fade_mir"] = -fs * (exit_path(o, h, l, c, j + 1, -fs, e + (e - fstop),
                                        e + (e - mid)) - e)
    res["trig_min"] = int(m[j])
    return res


def build():
    D = labels()
    fs = sorted(glob.glob(str(CLEAN / "bars_1m/NQ_*.parquet")))
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "session", "instrument_id", "open",
                                               "high", "low", "close", "rth"]) for f in fs])
    b = b[b.rth].sort_values("ts_et")
    rows = {}
    for s, g in b.groupby("session"):
        if s not in D.index or D.at[s, "half_day"] or g.instrument_id.nunique() != 1:
            continue
        r = day_trades(g)
        if r is not None:
            rows[s] = r
    T = pd.DataFrame(rows).T
    return D.join(T, how="left")


# ------------------------------------------------------------------ stats ----
def strat_pnl(X, lab, key_t="brk", key_c="fade", mult=MULT, rt=RT):
    pts = np.where(lab == "TREND", X[key_t], np.where(lab == "CHOP", X[key_c], np.nan))
    traded = ~np.isnan(pts)
    pnl = np.where(traded, pts * mult - rt, 0.0)
    return pnl, traded


def stats(pnl, traded, close):
    sd = pnl.std(ddof=1)
    sh = pnl.mean() / sd * np.sqrt(252) if sd > 0 else np.nan
    tr = pnl[traded]
    pf = tr[tr > 0].sum() / -tr[tr < 0].sum() if (tr < 0).any() else np.nan
    notional = np.r_[np.nan, close[:-1]] * MULT
    r = np.nan_to_num(pnl / notional)
    cagr = np.prod(1 + r) ** (252 / len(r)) - 1
    eq = np.cumsum(pnl)
    mdd = float(np.max(np.maximum.accumulate(eq) - eq))
    return dict(sharpe=sh, pf=pf, n=int(traded.sum()), cagr=cagr, mdd=mdd, total=float(pnl.sum()))


def main():
    rng = np.random.default_rng(SEED)
    X = build()
    X = X[X.label.notna() & (X.label != "WARMUP")]
    first = X.index.min()
    p("STUDY (b) -- REGIME SWITCH, strict one-shot replication (pre-registered 7cf6513)")
    p("  NQ only. Labels from indicators through the prior close. Published thresholds.")
    p("  Costs per side: NQ $2.25 + 1 tick; MNQ $0.62 + 1 tick.")
    p("")
    res = {}
    for lab_, a, bnd in (("2010-2020 [never used for this hypothesis; read by other daily "
                          "studies, incl. overnight gap base rates] -- DECISIVE", first,
                          pd.Timestamp("2020-12-31")),
                         ("2021-registration [seen; not decisive]", pd.Timestamp("2021-01-01"),
                          REG - pd.Timedelta(days=1))):
        Y = X[(X.index >= a) & (X.index <= bnd)]
        lab = Y.label.to_numpy()
        tradeable = Y.brk.notna().to_numpy()
        p(f"=== {lab_}: {a.date()} -> {bnd.date()} ===")
        vc = pd.Series(lab).value_counts().to_dict()
        p(f"  sessions {len(Y)}; labels {vc}; tradeable days (trigger present) {int(tradeable.sum())}")
        p(f"  traded: TREND {int(((lab=='TREND')&tradeable).sum())}, CHOP {int(((lab=='CHOP')&tradeable).sum())}")
        pnl, tr = strat_pnl(Y, lab)
        mp, _ = strat_pnl(Y, lab, mult=MMULT, rt=MRT)
        st = stats(pnl, tr, Y.close.to_numpy())
        mdd_m = float(np.max(np.maximum.accumulate(np.cumsum(mp)) - np.cumsum(mp)))
        p(f"  STRATEGY  Sharpe {st['sharpe']:+.2f}  CAGR {100*st['cagr']:.2f}%  PF {st['pf']:.2f}  "
          f"trades {st['n']}  maxDD ${st['mdd']:,.0f}/NQ ${mdd_m:,.0f}/MNQ  total ${st['total']:,.0f}")
        # four cells, descriptive
        for rule in ("brk", "fade"):
            for lb in ("TREND", "CHOP"):
                v = Y[rule][(Y.label == lb) & Y[rule].notna()].to_numpy(dtype=float) * MULT - RT
                p(f"    cell {rule:<4}|{lb:<5} n {len(v):>4}  mean ${v.mean() if len(v) else float('nan'):>+8.1f}"
                  f"  win {100*(v>0).mean() if len(v) else float('nan'):5.1f}%")
        # regime permutation: shuffle labels among labelled days, counts fixed
        perm = np.empty(N_SIM)
        for i in range(N_SIM):
            pl, t2 = strat_pnl(Y, rng.permutation(lab))
            sd = pl.std(ddof=1)
            perm[i] = pl.mean() / sd * np.sqrt(252) if sd > 0 else 0
        p_perm = (1 + (perm >= st["sharpe"]).sum()) / (N_SIM + 1)
        # random direction, same days, same geometry
        act = np.where(lab == "TREND", Y.brk, np.where(lab == "CHOP", Y.fade, np.nan)).astype(float)
        mir = np.where(lab == "TREND", Y.brk_mir, np.where(lab == "CHOP", Y.fade_mir, np.nan)).astype(float)
        rnd = np.empty(N_SIM)
        for i in range(N_SIM):
            flip = rng.random(len(act)) < 0.5
            pts = np.where(flip, mir, act)
            pl = np.where(np.isnan(pts), 0.0, pts * MULT - RT)
            sd = pl.std(ddof=1)
            rnd[i] = pl.mean() / sd * np.sqrt(252) if sd > 0 else 0
        p_rnd = (1 + (rnd >= st["sharpe"]).sum()) / (N_SIM + 1)
        p(f"  regime permutation: 95th pct {np.percentile(perm,95):+.2f}, p = {p_perm:.4f}")
        p(f"  random direction:   95th pct {np.percentile(rnd,95):+.2f}, p = {p_rnd:.4f}")
        order = sorted([("perm", p_perm), ("rnd", p_rnd)], key=lambda t: t[1])
        a1 = min(1.0, 2 * order[0][1])
        a2 = min(1.0, max(a1, order[1][1]))
        adj = {order[0][0]: a1, order[1][0]: a2}
        hp_perm, hp_rnd = adj["perm"], adj["rnd"]
        p(f"  Holm-adjusted: permutation {hp_perm:.4f}, random direction {hp_rnd:.4f}")
        yr = pd.Series(pnl, index=Y.index).groupby(Y.index.year).sum()
        p("  per year $/NQ: " + "  ".join(f"{y}:{v:+,.0f}" for y, v in yr.items()))
        p("")
        res[lab_[:4]] = dict(st=st, hp_perm=hp_perm, hp_rnd=hp_rnd)
    r = res["2010"]
    c = [r["st"]["sharpe"] >= 0.8, r["st"]["pf"] >= 1.3, r["hp_perm"] <= 0.05, r["hp_rnd"] <= 0.05]
    p("=== KILL CRITERIA, 2010-2020 block ===")
    p(f"  Sharpe {r['st']['sharpe']:+.2f} {'PASS' if c[0] else 'FAIL'} | PF {r['st']['pf']:.2f} "
      f"{'PASS' if c[1] else 'FAIL'} | permutation Holm p {r['hp_perm']:.4f} {'PASS' if c[2] else 'FAIL'}"
      f" | random-direction Holm p {r['hp_rnd']:.4f} {'PASS' if c[3] else 'FAIL'}")
    p(f"  => {'PASSES -- reconcile with trend_regime_study.md before anything else' if all(c) else 'FAILS -- closed permanently, no re-tuning'}")
    txt = "\n".join(L)
    print(txt)
    (OUT / "db_b_regime_switch_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
