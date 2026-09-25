"""Shared machinery for step 4 (reports/step4_preregistration.md).

Costs (section 5): per side NQ $2.25 + 1 tick = $7.25, MNQ $0.62 + 1 tick = $1.12.
Round trip in points: NQ 0.725, MNQ 1.12. If a frozen spec's own round-trip cost
in points is larger, it applies instead (per instrument).

Sharpe, CAGR and drawdown follow study_cd.evaluate: daily $ P&L over every session
in the sample (zeros on days without a trade), Sharpe x sqrt(252), CAGR compounded
on one contract's notional at the prior close.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/step4"
RESULTS = OUT / "results.csv"
sys.path.insert(0, str(ROOT / "scripts/orderflow"))
sys.path.insert(0, str(ROOT / "scripts/databento"))

MULT = {"NQ": 20.0, "MNQ": 2.0}
RT_STD_PTS = {"NQ": 2 * (2.25 + 5.00) / 20.0, "MNQ": 2 * (0.62 + 0.50) / 2.0}


def rt_pts(inst, frozen_rt_pts=0.0):
    return max(RT_STD_PTS[inst], float(frozen_rt_pts or 0.0))


def clustered(session, x):
    """Session-clustered t: mean of per-session means over its standard error."""
    s = pd.Series(np.asarray(x, float), index=pd.Index(session)).dropna()
    m = s.groupby(level=0).mean()
    if len(m) < 3 or m.std(ddof=1) == 0:
        return dict(n_sessions=len(m), t=np.nan, p=np.nan, mean_session=float(m.mean()))
    t = m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))
    return dict(n_sessions=len(m), t=float(t), p=float(2 * stats.t.sf(abs(t), len(m) - 1)),
                mean_session=float(m.mean()), pos_sessions=int((m > 0).sum()))


def evaluate(session, gross_pts, all_sessions, close_by_session=None, frozen_rt_pts=0.0):
    """session: per-trade session labels; gross_pts: per-trade points, unadjusted."""
    session = pd.Index(pd.to_datetime(pd.Index(session)))
    gp = np.asarray(gross_pts, float)
    idx = pd.Index(sorted(pd.to_datetime(pd.Index(all_sessions)).unique()))
    out = dict(n=len(gp))
    for inst in ("NQ", "MNQ"):
        net = gp - rt_pts(inst, frozen_rt_pts)
        usd = net * MULT[inst]
        daily = pd.Series(usd, index=session).groupby(level=0).sum().reindex(idx, fill_value=0.0)
        cum = daily.cumsum()
        out[f"dd_{inst}"] = float((cum.cummax() - cum).max()) if len(cum) else np.nan
        if inst == "NQ":
            out["net_pts_mean"] = float(net.mean()) if len(net) else np.nan
            out["usd_per_trade"] = float(usd.mean()) if len(usd) else np.nan
            out["win"] = float((net > 0).mean()) if len(net) else np.nan
            pos, neg = usd[usd > 0].sum(), -usd[usd < 0].sum()
            out["pf"] = float(pos / neg) if neg > 0 else np.nan
            sd = daily.std(ddof=1)
            out["sharpe"] = float(daily.mean() / sd * np.sqrt(252)) if sd > 0 else np.nan
            if close_by_session is not None:
                c = pd.Series(close_by_session).reindex(idx).shift(1) * MULT["NQ"]
                r = (daily / c).fillna(0.0)
                out["cagr"] = float(np.prod(1 + r) ** (252 / len(r)) - 1) if len(r) else np.nan
            else:
                out["cagr"] = np.nan
            out["total_usd"] = float(daily.sum())
            out.update(clustered(session, net))
    return out


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, min(1.0, (len(p) - k) * p[i]))
        adj[i] = run
    return adj


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    adj = np.empty(n)
    run = 1.0
    for k in range(n - 1, -1, -1):
        i = o[k]
        run = min(run, p[i] * n / (k + 1))
        adj[i] = run
    return adj


def run_frozen(module_name, patches, out_name, argv=None):
    """Import a frozen study module, apply attribute patches, run main() and
    save everything it prints. Returns (module, text)."""
    mod = importlib.import_module(module_name)
    for target, attr, value in patches:
        setattr(importlib.import_module(target) if isinstance(target, str) else target, attr, value)
        if isinstance(target, str) and target != module_name and hasattr(mod, attr):
            setattr(mod, attr, value)
    buf = io.StringIO()
    old = sys.argv
    sys.argv = [module_name] + list(argv or [])
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    finally:
        sys.argv = old
    txt = buf.getvalue()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / out_name).write_text(txt)
    return mod, txt


def record(row: dict):
    """Append or replace one study's primary result in reports/step4/results.csv."""
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS) if RESULTS.exists() else pd.DataFrame()
    if len(df) and "id" in df:
        df = df[df.id != row["id"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.sort_values("id").to_csv(RESULTS, index=False)


def fmt(r):
    return (f"n {r['n']} | net {r.get('net_pts_mean', np.nan):+.2f} pt/trade "
            f"(${r.get('usd_per_trade', np.nan):+.1f}) | win {100*r.get('win', np.nan):.1f}% | "
            f"PF {r.get('pf', np.nan):.2f} | Sharpe {r.get('sharpe', np.nan):+.2f} | "
            f"CAGR {100*r.get('cagr', np.nan):.2f}% | maxDD ${r.get('dd_NQ', np.nan):,.0f}/NQ "
            f"${r.get('dd_MNQ', np.nan):,.0f}/MNQ | sessions {r.get('n_sessions')} "
            f"t {r.get('t', np.nan):+.2f} p {r.get('p', np.nan):.4f}")
