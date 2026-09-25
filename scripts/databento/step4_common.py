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
    """Round trip in points: the larger of the NQ/MNQ standard and the frozen
    cost. `frozen_rt_pts` may be a scalar or a per-trade array."""
    f = np.nan_to_num(np.asarray(frozen_rt_pts, float), nan=0.0)
    return np.maximum(RT_STD_PTS[inst], f)


def clustered(session, x):
    """Session-clustered t: mean of per-session means over its standard error."""
    s = pd.Series(np.asarray(x, float), index=pd.Index(session)).dropna()
    m = s.groupby(level=0).mean()
    if len(m) < 3 or m.std(ddof=1) == 0:
        return dict(n_sessions=len(m), t=np.nan, p=np.nan, p_one=np.nan,
                    mean_session=float(m.mean()))
    t = m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))
    return dict(n_sessions=len(m), t=float(t), p=float(2 * stats.t.sf(abs(t), len(m) - 1)),
                p_one=float(stats.t.sf(t, len(m) - 1)),
                mean_session=float(m.mean()), pos_sessions=int((m > 0).sum()))


def evaluate(session, gross_pts, all_sessions, close_by_session=None, frozen_rt_pts=0.0):
    """session: per-trade session labels; gross_pts: per-trade points, unadjusted."""
    session = pd.Index(pd.to_datetime(pd.Index(session)))
    gp = np.asarray(gross_pts, float)
    if np.ndim(frozen_rt_pts) and len(np.atleast_1d(frozen_rt_pts)) != len(gp):
        raise ValueError("per-trade frozen cost must match the trades")
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
            cl = clustered(session, net)            # diagnostic only (Clarification 3)
            out["n_sessions"] = cl["n_sessions"]
            out["t_sessmean"] = cl.get("t", np.nan)
            out["mean_session"] = cl.get("mean_session", np.nan)
            out["pos_sessions"] = cl.get("pos_sessions", np.nan)
            nd = len(daily)
            if nd > 2 and sd > 0:
                td = float(daily.mean() / (sd / np.sqrt(nd)))
                out.update(t=td, p=float(2 * stats.t.sf(abs(td), nd - 1)),
                           p_one=float(stats.t.sf(td, nd - 1)), n_days=nd)
            else:
                out.update(t=np.nan, p=np.nan, p_one=np.nan, n_days=nd)
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
    safe = OUT / "frozen"
    safe.mkdir(parents=True, exist_ok=True)
    if getattr(mod, "ROOT", None) == ROOT:
        mod.ROOT = sandbox_root()             # writes to ROOT/reports land in the sandbox
    for attr in ("OUT", "REPORTS", "OUTDIR", "OUT_DIR"):
        v = getattr(mod, attr, None)
        if isinstance(v, Path) and str(v.resolve()).startswith(str((ROOT / "reports").resolve())):
            setattr(mod, attr, safe)          # never overwrite an earlier result
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
    assert_reports_untouched()
    return mod, txt


def sandbox_root():
    """A stand-in repository root: data/ links to the real data, reports/ is a
    scratch directory under reports/step4/frozen/root, so a frozen script that
    writes ROOT/'reports/...' cannot overwrite an earlier result."""
    sb = OUT / "frozen" / "root"
    (sb / "reports").mkdir(parents=True, exist_ok=True)
    if not (sb / "data").exists():
        (sb / "data").symlink_to(ROOT / "data")
    return sb


def assert_reports_untouched():
    """Restore any tracked file under reports/ (outside reports/step4) that a
    frozen run modified, remove new untracked files there, and fail loudly."""
    import subprocess
    st = subprocess.run(["git", "status", "--porcelain", "--", "reports", "results"],
                        cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    bad = [l for l in st if not l[3:].startswith(("reports/step4", "results/", "reports/of_h_"))
           and not l[3:].startswith("reports/decisions_pending.md")]
    if bad:
        for l in bad:
            p = l[3:]
            if l.startswith("??"):
                (ROOT / p).unlink(missing_ok=True) if (ROOT / p).is_file() else None
            else:
                subprocess.run(["git", "checkout", "--", p], cwd=ROOT)
        raise RuntimeError(f"frozen run touched earlier results (restored): {bad}")


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
            f"${r.get('dd_MNQ', np.nan):,.0f}/MNQ | trade-sessions {r.get('n_sessions')}/{r.get('n_days')} "
            f"daily-P&L t {r.get('t', np.nan):+.2f} p1 {r.get('p_one', np.nan):.4f} (sess-mean t {r.get('t_sessmean', np.nan):+.2f})")


def nq_close():
    d = pd.read_parquet(ROOT / "data/clean/daily/NQ_daily.parquet")
    return pd.Series(d.close.to_numpy(), index=pd.to_datetime(d.session))
