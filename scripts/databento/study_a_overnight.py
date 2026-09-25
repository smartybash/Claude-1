#!/usr/bin/env python3
"""Study (a) -- overnight drift overlay. Pre-registered at
reports/db_a_overnight_drift_prereg.md (commit 7cf6513) before any Databento data
was requested. Implemented exactly as registered; the implementation choices the
spec left open are listed in IMPLEMENTATION below and printed with the results.

IMPLEMENTATION (fixed before this script first ran):
  * The SMA history uses full sessions only. `half_day` covers both NYSE half
    days and CME's abbreviated sessions on stock-market holidays; the spec skips
    those nights in every arm, and they are not stock trading days.
  * The signal price (close of the 15:58 bar) is converted to back-adjusted units
    with its session's adjustment factor before it is compared with the SMA of
    back-adjusted closes.
  * A night is attributed to its exit session's date in the daily P&L series.
  * Buy and hold = overnight P&L on eligible nights + RTH open->close P&L on every
    full session whose RTH is one contract, with one round trip charged per roll.
  * The registration date is 2026-09-25 and the data ends 2026-09-24, so the
    forward block is empty today.
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
SPEC = {  # multiplier $/pt, commission/side, tick $ (slippage 1 tick per side)
    "NQ": dict(mult=20.0, comm=2.25, tick=5.00, micro="MNQ", m_mult=2.0, m_comm=0.62, m_tick=0.50),
    "ES": dict(mult=50.0, comm=2.25, tick=12.50, micro="MES", m_mult=5.0, m_comm=0.62, m_tick=1.25),
}
L = []
p = L.append


def minute_prices(sym):
    """Per session: 15:58 close, 15:59 close, 09:30 open (first bar 09:30-09:34),
    each with its instrument_id."""
    fs = sorted(glob.glob(str(CLEAN / f"bars_1m/{sym}_*.parquet")))
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "session", "instrument_id",
                                               "open", "close"]) for f in fs])
    m = b.ts_et.dt.hour * 60 + b.ts_et.dt.minute
    s958 = b[m == 958].groupby("session").agg(p958=("close", "last"), id958=("instrument_id", "last"))
    s959 = b[m == 959].groupby("session").agg(p_close=("close", "last"), mid_close=("instrument_id", "last"))
    op = b[(m >= 570) & (m <= 574)].sort_values("ts_et").groupby("session").agg(
        p_open=("open", "first"), mid_open=("instrument_id", "first"))
    return s958.join(s959, how="outer").join(op, how="outer")


def build(sym):
    D = pd.read_parquet(CLEAN / f"daily/{sym}_daily.parquet").set_index("session")
    P = minute_prices(sym)
    X = D.join(P, how="left")
    X = X[X.n_rth_bars.notna()].copy()
    full = X[~X.half_day].copy()
    full["sma200"] = full.close_adj.rolling(200).mean().shift(1)
    full["sig_px_adj"] = full.p958 * full.adj_factor
    full["signal"] = full.sig_px_adj > full.sma200
    X = X.join(full[["sma200", "signal"]], how="left")
    # nights: entry at session t close, exit at session t+1 open
    X["nx_session"] = pd.Series(X.index, index=X.index).shift(-1)
    for c in ("p_open", "mid_open", "half_day"):
        X["nx_" + c] = X[c].shift(-1)
    X["night_ok"] = (~X.half_day & ~X.nx_half_day.astype(bool) & X.p_close.notna()
                     & X.nx_p_open.notna() & (X.mid_close == X.nx_mid_open))
    X["night_pts"] = X.nx_p_open - X.p_close
    X["intra_ok"] = ~X.half_day & X.p_open.notna() & X.p_close.notna() & (X.mid_open == X.mid_close)
    X["intra_pts"] = X.p_close - X.p_open
    X["roll_event"] = X.mid_close.notna() & (X.mid_close != X.mid_close.ffill().shift(1)) & X.mid_close.shift(1).notna()
    return X


def daily_pnl(X, arm, s, micro=False):
    k = SPEC[s]
    mult = k["m_mult"] if micro else k["mult"]
    rt = 2 * ((k["m_comm"] + k["m_tick"]) if micro else (k["comm"] + k["tick"]))
    nights = X[X.night_ok].copy()
    if arm == "overlay":
        nights = nights[nights.signal == True]                     # noqa: E712
    pnl = pd.Series(0.0, index=X.nx_session.dropna().values)
    trades = []
    if arm in ("overlay", "always"):
        v = nights.night_pts * mult - rt
        trades = v.to_numpy()
        pnl = pd.Series(v.to_numpy(), index=nights.nx_session.values)
    elif arm == "bh":
        on = X[X.night_ok]
        a = pd.Series(on.night_pts.to_numpy() * mult, index=on.nx_session.values)
        it = X[X.intra_ok]
        b = pd.Series(it.intra_pts.to_numpy() * mult, index=it.index)
        rolls = X[X.roll_event].index
        c = pd.Series(-rt, index=rolls)
        pnl = pd.concat([a, b, c]).groupby(level=0).sum()
        trades = np.array([])
    idx = X.index
    pnl = pnl.groupby(level=0).sum().reindex(idx, fill_value=0.0)
    return pnl, np.asarray(trades)


def metrics(pnl, trades, X, s, micro=False):
    k = SPEC[s]
    mult = k["m_mult"] if micro else k["mult"]
    sd = pnl.std(ddof=1)
    sharpe = pnl.mean() / sd * np.sqrt(252) if sd > 0 else np.nan
    notional = (X.close.shift(1) * mult).reindex(pnl.index)
    r = (pnl / notional).fillna(0.0)
    yrs = len(pnl) / 252
    cagr = float(np.prod(1 + r) ** (1 / yrs) - 1) if yrs > 0 else np.nan
    eq = pnl.cumsum()
    mdd = float((eq.cummax() - eq).max())
    pf = (trades[trades > 0].sum() / -trades[trades < 0].sum()) if len(trades) and (trades < 0).any() else np.nan
    return dict(sharpe=sharpe, cagr=cagr, mdd=mdd, n=len(trades), pf=pf, total=float(pnl.sum()))


def null_p(X, s, obs_sharpe, n_hold, rng):
    k = SPEC[s]
    rt = 2 * (k["comm"] + k["tick"])
    el = X[X.night_ok]
    v = el.night_pts.to_numpy() * k["mult"] - rt
    ex = el.nx_session.values
    idx = X.index
    pos = pd.Index(idx).get_indexer(ex)
    sims = np.empty(N_SIM)
    for i in range(N_SIM):
        pick = rng.choice(len(v), size=n_hold, replace=False)
        arr = np.zeros(len(idx))
        np.add.at(arr, pos[pick], v[pick])
        sd = arr.std(ddof=1)
        sims[i] = arr.mean() / sd * np.sqrt(252) if sd > 0 else 0
    return (1 + (sims >= obs_sharpe).sum()) / (N_SIM + 1), np.percentile(sims, 95)


def main():
    rng = np.random.default_rng(SEED)
    p("STUDY (a) -- OVERNIGHT DRIFT OVERLAY (pre-registered, commit 7cf6513)")
    p("  Databento GLBX.MDP3 ohlcv-1m, NQ.v.0 / ES.v.0 continuous, unadjusted prices;")
    p("  SMA on ratio back-adjusted RTH closes; every traded return within one contract.")
    p("  Costs per side: NQ/ES $2.25 + 1 tick; MNQ/MES $0.62 + 1 tick.")
    p("")
    blocks = {}
    res_rows = []
    for s in ("NQ", "ES"):
        X = build(s)
        first_sig = X[X.sma200.notna()].index.min()
        blocks[s] = [("2010-2020 [never used for this hypothesis; read by other daily "
                      "studies, incl. overnight gap base rates]", first_sig,
                      pd.Timestamp("2020-12-31")),
                     ("2021-registration [seen; not decisive]", pd.Timestamp("2021-01-01"),
                      REG - pd.Timedelta(days=1))]
        p(f"=== {s}  (first signal {first_sig.date()}; sessions {len(X)}; "
          f"eligible nights {int(X.night_ok.sum())}; roll/half-day nights skipped "
          f"{int((~X.night_ok).sum())}) ===")
        for lab, a, b in blocks[s]:
            Xb = X[(X.index >= a) & (X.index <= b)]
            p(f"  -- {lab}: {a.date()} -> {b.date()}, {len(Xb)} sessions")
            p(f"     {'arm':<18}{'Sharpe':>8}{'CAGR':>8}{'PF':>7}{'trades':>8}"
              f"{'maxDD $/'+s:>12}{'maxDD $/'+SPEC[s]['micro']:>13}{'total $':>11}")
            M = {}
            for arm in ("overlay", "always", "bh"):
                pn, tr = daily_pnl(Xb, arm, s)
                pm, trm = daily_pnl(Xb, arm, s, micro=True)
                m = metrics(pn, tr, Xb, s)
                mm = metrics(pm, trm, Xb, s, micro=True)
                M[arm] = m
                p(f"     {arm:<18}{m['sharpe']:>+8.2f}{100*m['cagr']:>7.2f}%"
                  f"{m['pf']:>7.2f}{m['n']:>8}{m['mdd']:>12,.0f}{mm['mdd']:>13,.0f}"
                  f"{m['total']:>11,.0f}")
            pv, p95 = null_p(Xb, s, M["overlay"]["sharpe"], M["overlay"]["n"], rng)
            p(f"     null (random nights, same count {M['overlay']['n']}, 5,000 sims): "
              f"95th pct Sharpe {p95:+.2f}, overlay p = {pv:.4f}")
            res_rows.append(dict(sym=s, block=lab[:9], **{f"ov_{k}": v for k, v in M["overlay"].items()},
                                 bh_sharpe=M["bh"]["sharpe"], always_sharpe=M["always"]["sharpe"],
                                 p_raw=pv))
        # per-year overlay table
        pn, _ = daily_pnl(X, "overlay", s)
        yr = pn.groupby(pn.index.year).agg(["sum", "std", "mean"])
        yr["sharpe"] = yr["mean"] / yr["std"] * np.sqrt(252)
        p("  per-year overlay (NQ/ES $ per contract, Sharpe):")
        p("   " + "  ".join(f"{y}:{r['sum']:+,.0f}({r['sharpe']:+.2f})" for y, r in yr.iterrows()))
        p("")
    R = pd.DataFrame(res_rows)
    # Holm across the two primary tests (NQ, ES) on the 2010-2020 block
    prim = R[R.block.str.startswith("2010")].sort_values("p_raw").reset_index(drop=True)
    m = len(prim)
    adj, run = [], 0.0
    for i, pv in enumerate(prim.p_raw):
        run = max(run, min(1.0, (m - i) * pv))
        adj.append(run)
    prim["p_holm"] = adj
    p("=== KILL CRITERIA, 2010-2020 block (all must hold) ===")
    for r in prim.itertuples():
        c1, c2 = r.ov_sharpe >= 0.8, r.ov_pf >= 1.3
        c3, c4 = r.p_holm <= 0.05, r.ov_sharpe >= r.bh_sharpe
        p(f"  {r.sym}: Sharpe {r.ov_sharpe:+.2f} {'PASS' if c1 else 'FAIL'} | PF "
          f"{r.ov_pf:.2f} {'PASS' if c2 else 'FAIL'} | null Holm p {r.p_holm:.4f} "
          f"{'PASS' if c3 else 'FAIL'} | vs B&H {r.bh_sharpe:+.2f} {'PASS' if c4 else 'FAIL'}"
          f"  => {'SURVIVES (forward data required)' if all([c1,c2,c3,c4]) else 'KILLED'}")
    p("")
    p("  Forward block (after 2026-09-25): empty today. Nothing is promoted on backtest.")
    txt = "\n".join(L)
    print(txt)
    (OUT / "db_a_overnight_drift_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
