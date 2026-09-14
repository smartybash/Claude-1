"""Part B - the corrected same-day sweep/run test on real intraday bars.

Causal design (the fix for the daily-resolution bug that produced the absurd
88%-win / t=10 result before correction):
  levels fixed pre-session -> first bar trading through a level = touch ->
  K-bar confirmation window decides sweep (close back inside) vs run (still
  beyond at window end) -> ENTRY AT THE CLOSE OF THE CONFIRMING BAR, never at
  the touch, never using the session's own later close to define the event.

Pre-registered protocol (fixed before looking at any result; do not edit
after seeing OOS numbers):
  - variants: mode in {sweep-fade, run-follow} x K in {0, 1, 3}  (6 tests
    per instrument); exit = flat at end of day (simplest control), stop =
    touch-bar extreme (sweep) / the level (run); one entry per level per
    session, NO re-entry
  - anchored walk-forward: pick K in-sample per fold, lock, test next block;
    requires >= 5 folds with >= 10 test sessions each (>= ~60 sessions);
    if depth is insufficient the run is DIAGNOSTIC ONLY and the verdict is
    NOT VALIDATED regardless of the numbers
  - costs: conservative round-trip defaults (futures 1.0 bp, ETFs 0.5 bp of
    entry price), reported at 0.5x / 1x / 2x
  - null: 2000 resamples matched on trade count, holding-time (bars) and
    direction mix, entered at random causal bar positions
  - multiplicity: Bonferroni x6 within instrument (raw p also reported)
  - kill criteria: OOS Sharpe >= 0.8; corrected p <= 0.05; MaxDD <= same-span
    buy-and-hold MaxDD; consistent sign+significance on >= 3 of 4
    instruments; net CAGR > 0 at 1x cost
  - prior being updated: the daily-resolution version of this test was NOT
    significant (matched-null p = 0.179)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sweeplib import data as D
from sweeplib.engine import Trade, classify_session, simulate_trades
from sweeplib.levels import session_levels

SYMS = ["NQ", "ES", "QQQ", "SPY"]
K_GRID = [0, 1, 3]
MODES = ["sweep", "run"]
COST_RT_BP = {"NQ": 1.0, "ES": 1.0, "QQQ": 0.5, "SPY": 0.5}  # conservative
COST_MULTS = [0.5, 1.0, 2.0]
N_NULL = 2000
MIN_FOLDS, MIN_TEST_SESS = 5, 10
RNG = np.random.default_rng(20260706)

REPORT = ROOT / "reports" / "sweep_run_intraday_results.md"


def stats(daily_ret: pd.Series, periods_per_year: float = 252.0) -> dict:
    """Tot% / CAGR / Sharpe / MaxDD / CVaR(5%) - same style as the rest of
    the program."""
    if len(daily_ret) == 0:
        return {k: np.nan for k in ("tot", "cagr", "sharpe", "maxdd", "cvar")}
    eq = (1 + daily_ret).cumprod()
    tot = eq.iloc[-1] - 1
    yrs = len(daily_ret) / periods_per_year
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    sd = daily_ret.std(ddof=1)
    sharpe = daily_ret.mean() / sd * np.sqrt(periods_per_year) if sd > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    q = daily_ret.quantile(0.05)
    cvar = daily_ret[daily_ret <= q].mean() if (daily_ret <= q).any() else np.nan
    return {"tot": tot, "cagr": cagr, "sharpe": sharpe, "maxdd": dd, "cvar": cvar}


@dataclass
class Prepared:
    sym: str
    sessions: dict          # date -> RTH bars
    daily: pd.DataFrame
    touches_by_k: dict      # K -> {date: [Touch]}


def prepare(sym: str) -> Prepared:
    bars5 = D.load(sym, "5min")
    daily = D.daily_from_intraday_or_cache(sym)
    sessions = D.rth_sessions_5min(bars5)
    # only sessions with a computable pre-session level set
    sessions = {
        d: b for d, b in sessions.items() if len(session_levels(daily, d)) > 0
    }
    touches_by_k = {}
    for k in K_GRID:
        touches_by_k[k] = {
            d: classify_session(b, session_levels(daily, d), k)
            for d, b in sessions.items()
        }
    return Prepared(sym, sessions, daily, touches_by_k)


def variant_trades(p: Prepared, mode: str, K: int) -> list[Trade]:
    out = []
    for d, b in p.sessions.items():
        out.extend(simulate_trades(b, p.touches_by_k[K][d], mode, d))
    return out


def daily_returns(trades: list[Trade], sessions: list, cost_bp: float) -> pd.Series:
    """Sum of per-trade net returns per session (flat overnight)."""
    r = pd.Series(0.0, index=pd.DatetimeIndex(sessions))
    for t in trades:
        r[t.session] += t.ret - cost_bp * 1e-4
    return r


def matched_null_p(
    p: Prepared, trades: list[Trade], cost_bp: float, n: int = N_NULL
) -> float:
    """Random entries matched on trade count, per-trade holding time (bars)
    AND direction mix - not exposure-only. One-sided: P(null >= observed)."""
    if not trades:
        return np.nan
    obs = sum(t.ret - cost_bp * 1e-4 for t in trades)
    holds = np.array([t.hold_bars for t in trades])
    dirs = np.array([t.direction for t in trades])
    dates = list(p.sessions)
    closes = {d: p.sessions[d]["close"].values for d in dates}
    hits = 0
    for _ in range(n):
        tot = 0.0
        perm = RNG.permutation(dirs)
        for h, direction in zip(holds, perm):
            d = dates[RNG.integers(len(dates))]
            c = closes[d]
            if len(c) <= h + 1:
                continue
            i = RNG.integers(0, len(c) - h - 1)
            tot += direction * (c[i + h] - c[i]) / c[i] - cost_bp * 1e-4
        if tot >= obs:
            hits += 1
    return (1 + hits) / (1 + n)


def buy_hold_maxdd(p: Prepared) -> float:
    closes = pd.concat([b["close"] for b in p.sessions.values()])
    eq = closes / closes.iloc[0]
    return float((eq / eq.cummax() - 1).min())


def anchored_walk_forward(p: Prepared, mode: str, cost_bp: float) -> dict:
    """Pick K in-sample by total net return, lock, test next block.

    Returns fold table + pooled OOS returns. Marked infeasible when the
    pre-registered depth floor (MIN_FOLDS folds x MIN_TEST_SESS sessions)
    cannot be met - the caller must then treat everything as diagnostic.
    """
    dates = sorted(p.sessions)
    n = len(dates)
    feasible = n >= MIN_TEST_SESS * (MIN_FOLDS + 1)
    n_folds = MIN_FOLDS if feasible else max(2, min(3, n // 4))
    block = n // (n_folds + 1)
    folds, oos = [], []
    if block < 2:
        return {"feasible": False, "folds": [], "oos": pd.Series(dtype=float)}
    for f in range(n_folds):
        train = dates[: block * (f + 1)]
        test = dates[block * (f + 1): block * (f + 2)] if f < n_folds - 1 else dates[block * (f + 1):]
        if not test:
            continue
        best_k, best_tot = None, -np.inf
        for k in K_GRID:
            tr = [t for t in variant_trades(p, mode, k) if t.session in train]
            tot = sum(t.ret - cost_bp * 1e-4 for t in tr)
            if tot > best_tot:
                best_k, best_tot = k, tot
        te = [t for t in variant_trades(p, mode, best_k) if t.session in test]
        r = daily_returns(te, test, cost_bp)
        oos.append(r)
        folds.append({"fold": f + 1, "K": best_k, "train_n": len(train),
                      "test_n": len(test), "oos_tot": float((1 + r).prod() - 1)})
    return {
        "feasible": feasible,
        "folds": folds,
        "oos": pd.concat(oos) if oos else pd.Series(dtype=float),
    }


def main() -> None:
    lines = ["# Sweep/run intraday test - machine-generated results",
             "", f"Generated by scripts/sweep_run_intraday_test.py; "
             f"null resamples per test: {N_NULL}.", ""]
    n_tests_per_sym = len(MODES) * len(K_GRID)
    verdict_rows = []
    for sym in SYMS:
        p = prepare(sym)
        dates = sorted(p.sessions)
        bh_dd = buy_hold_maxdd(p)
        lines += [f"## {sym}", "",
                  f"- sessions tested: **{len(dates)}** "
                  f"({dates[0].date()} -> {dates[-1].date()})",
                  f"- buy & hold MaxDD over span: {bh_dd:.2%}",
                  f"- cost base (round trip): {COST_RT_BP[sym]} bp; "
                  f"multiplicity: Bonferroni x{n_tests_per_sym}", ""]
        print(f"=== {sym}: {len(dates)} sessions ===")

        # fixed-parameter diagnostic grid (all variants, all cost multiples)
        lines += ["| mode | K | trades | win% | avg bp/trade | Tot% (0.5x/1x/2x cost) "
                  "| Sharpe(1x) | MaxDD(1x) | CVaR(1x) | null p raw | p corr |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for mode in MODES:
            for k in K_GRID:
                tr = variant_trades(p, mode, k)
                if not tr:
                    lines.append(f"| {mode} | {k} | 0 | - | - | - | - | - | - | - | - |")
                    continue
                base = COST_RT_BP[sym]
                tots = []
                for m in COST_MULTS:
                    r = daily_returns(tr, dates, base * m)
                    tots.append(f"{(1 + r).prod() - 1:+.2%}")
                r1 = daily_returns(tr, dates, base)
                s = stats(r1)
                wins = sum(1 for t in tr if t.ret - base * 1e-4 > 0)
                avg_bp = np.mean([t.ret for t in tr]) * 1e4 - base
                praw = matched_null_p(p, tr, base)
                pcorr = min(1.0, praw * n_tests_per_sym) if np.isfinite(praw) else np.nan
                lines.append(
                    f"| {mode} | {k} | {len(tr)} | {wins / len(tr):.0%} "
                    f"| {avg_bp:+.1f} | {' / '.join(tots)} | {s['sharpe']:.2f} "
                    f"| {s['maxdd']:.2%} | {s['cvar']:.3%} | {praw:.3f} | {pcorr:.3f} |")
                print(f"  {mode} K={k}: n={len(tr)} avg={avg_bp:+.1f}bp p={praw:.3f}")
        lines.append("")

        # anchored walk-forward per mode
        for mode in MODES:
            wf = anchored_walk_forward(p, mode, COST_RT_BP[sym])
            tag = "" if wf["feasible"] else "  **[INFEASIBLE DEPTH - diagnostic only]**"
            lines.append(f"### {sym} walk-forward, {mode}{tag}")
            lines.append("")
            if not wf["folds"]:
                lines += ["Not enough sessions to form even diagnostic folds.", ""]
                verdict_rows.append((sym, mode, np.nan, False))
                continue
            lines += ["| fold | K chosen IS | train sess | test sess | OOS tot |",
                      "|---|---|---|---|---|"]
            for f in wf["folds"]:
                lines.append(f"| {f['fold']} | {f['K']} | {f['train_n']} "
                             f"| {f['test_n']} | {f['oos_tot']:+.2%} |")
            s = stats(wf["oos"])
            lines += ["", f"pooled OOS: Tot {s['tot']:+.2%}, Sharpe {s['sharpe']:.2f}, "
                      f"MaxDD {s['maxdd']:.2%}, CVaR {s['cvar']:.3%}", ""]
            verdict_rows.append((sym, mode, s["sharpe"], wf["feasible"]))

    # kill-criteria checklist
    lines += ["## Kill-criteria checklist (pre-registered)", ""]
    any_feasible = any(v[3] for v in verdict_rows)
    lines += [
        f"1. OOS Sharpe >= 0.8: {'assessable' if any_feasible else '**NOT ASSESSABLE** - walk-forward depth floor (>= ~60 sessions) not met'}",
        "2. Corrected null p <= 0.05: see per-variant table (diagnostic sample only)",
        "3. MaxDD <= buy-and-hold MaxDD: see per-instrument tables",
        "4. Consistent on >= 3 of 4 instruments: requires criterion 1 first",
        "5. Net CAGR > 0 at 1x cost: see tables",
        "",
        "Prior being updated: daily-resolution version, matched-null p = 0.179 "
        "(not significant).",
        "",
    ]
    verdict = "NOT VALIDATED" if not any_feasible else "see criteria"
    lines += [f"## VERDICT: **{verdict}**", ""]
    if not any_feasible:
        lines += [
            "Reason: the walk-forward depth floor pre-registered above cannot be "
            "met with the data obtainable in this environment (IBKR MCP caps "
            "every request at 1000 bars; no local TWS for the ib_async deep "
            "fetch). All numbers above are DIAGNOSTIC ONLY - they exercise the "
            "pipeline end-to-end and must not be read as evidence for or "
            "against the strategy. Run scripts/fetch_intraday.py on a machine "
            "with TWS/Gateway, rebuild, and rerun this script unchanged.", ""]
    REPORT.write_text("\n".join(lines))
    print(f"\nwrote {REPORT}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
