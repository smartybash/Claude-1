"""Shared helpers for step-4 tape ports (G1). Same logic as g1_tape_a.py."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402
import step4_adapters as A                                         # noqa: E402
import tape                                                        # noqa: E402

tape.load_all = A.load_tape_all


def days(min_prints=5000):
    d = {k: tape.rth(v) for k, v in sorted(A.load_tape_all().items())}
    return {k: s for k, s in d.items() if len(s) > min_prints}


def sess(k):
    return pd.Timestamp(f"{k[:4]}-{k[4:6]}-{k[6:]}")


def cell_eval(rows, frozen_rt, all_sessions):
    """rows: list of (session_key, gross_pts array)."""
    rows = [(k, np.asarray(v, float)) for k, v in rows]
    s = np.concatenate([[sess(k)] * len(v) for k, v in rows]) if rows else np.array([])
    g = np.concatenate([v for _, v in rows]) if rows else np.array([])
    ok = np.isfinite(g)
    return C.evaluate(pd.Index(s)[ok], g[ok], [sess(k) for k in all_sessions],
                      close_by_session=C.nq_close(), frozen_rt_pts=frozen_rt)


def report(tid, name, res, primary, extra_ok=True, extra_lab="", old="dead",
           note=""):
    L = [f"=== {tid} {name} (Databento discovery sessions) ==="]
    if note:
        L.append(f"  note: {note}")
    keys = list(primary)
    raw = [res[k]["p_one"] if np.isfinite(res[k]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    for k in res:
        L.append(f"  {k:<30} {C.fmt(res[k])}")
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    pstudy = float(ph.min())
    r = res[best]
    ok = bool(np.isfinite(r["net_pts_mean"]) and r["net_pts_mean"] > 0
              and pstudy <= 0.05 and extra_ok)
    L.append(f"  PRIMARY: {len(keys)} cell(s), Holm on one-sided p; best = {best}, "
             f"study p = {pstudy:.4f}")
    L.append(f"  pass bar (net > 0, p <= 0.05{extra_lab}): {'MET' if ok else 'NOT MET'}"
             f"  -> {'candidate for BH' if ok else 'stays closed'}")
    txt = "\n".join(L)
    (C.OUT / f"{tid}_output.txt").write_text(txt)
    print(txt, "\n")
    C.record(dict(id=tid, study=name, primary=best, n=r["n"], sessions=r.get("n_sessions"),
                  net_pts=r["net_pts_mean"], usd_trade=r["usd_per_trade"], sharpe=r["sharpe"],
                  cagr=r["cagr"], dd_nq=r["dd_NQ"], dd_mnq=r["dd_MNQ"], pf=r["pf"],
                  t=r["t"], p_raw=r["p"], p_one=r["p_one"], p_study=pstudy, pass_bar=ok,
                  old_verdict=old, new_verdict_pre_bh="pass bar met" if ok else "stays closed"))
    return ok
