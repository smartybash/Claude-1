#!/usr/bin/env python3
"""Step 4, G1 -- T16 filter survey, tape families (filter_survey.py).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions (tape adapter). No depth files exist for
these dates, so book_series returns nothing and the BOOK family drops out (it is
X, depth). Frozen constants unchanged; cost 2.0 pt (stricter, applies).
filter_survey.build keeps only R, so its source is loaded and ONE field is
inserted into the per-trade dict (gross points, `gross=pnl`); nothing else in
the function changes. SPEED counts prints: Databento prints are per price level
within a match, ATAS prints were per fill, so the ratio of prints to the last 20
bars is comparable within the data but not in level with the ATAS run.
Primary: every tape gate x {3, 5} min = 22 cells -- SURGE >= 1.0/1.3/1.7, SPEED
>= 1.0/1.3/1.7, RUN >= 1/2/3, BIGPRINT net >= 1, BIGPRINT share >= 1%. Holm on
the one-sided session-clustered p of the gated trades' net points. Pass: net > 0,
p <= 0.05, and the frozen paired comparison (session bootstrap 8,000, seed 0)
with a 95% interval above 0 for the best cell. Old verdict: no filter.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C = TL.C


def patched_module():
    src_path = C.ROOT / "scripts/orderflow/filter_survey.py"
    src = src_path.read_text()
    old = "r = dict(day=d1, R=pnl / risk - COST_PTS / risk)"
    assert src.count(old) == 1
    src = src.replace(old, "r = dict(day=d1, R=pnl / risk - COST_PTS / risk, gross=pnl)")
    m = types.ModuleType("filter_survey_pts")
    m.__file__ = str(src_path)
    exec(compile(src, str(src_path), "exec"), m.__dict__)
    return m


def paired_ci(df, key, cut, draws=8000):
    d = df.dropna(subset=[key])
    hit = (d[key] >= cut).to_numpy()
    R = d.R.to_numpy()
    if hit.sum() < 8 or (~hit).sum() < 8:
        return np.nan, np.nan, np.nan
    obs = R[hit].mean() - R[~hit].mean()
    codes, _ = pd.factorize(d.day)
    k = codes.max() + 1
    on_s, on_n = np.bincount(codes[hit], R[hit], minlength=k), np.bincount(codes[hit], minlength=k).astype(float)
    off_s, off_n = np.bincount(codes[~hit], R[~hit], minlength=k), np.bincount(codes[~hit], minlength=k).astype(float)
    pick = np.random.default_rng(0).integers(0, k, size=(draws, k))
    a_s, a_n, b_s, b_n = on_s[pick].sum(1), on_n[pick].sum(1), off_s[pick].sum(1), off_n[pick].sum(1)
    ok = (a_n > 0) & (b_n > 0)
    lo, hi = np.percentile(a_s[ok] / a_n[ok] - b_s[ok] / b_n[ok], [2.5, 97.5])
    return obs, lo, hi


def main():
    D = TL.days()
    print(f"sessions: {len(D)}")
    C.run_frozen("filter_survey", [], "T16_frozen_output.txt")
    FS = patched_module()
    k = sorted(D)
    P = [(a, b) for a, b in zip(k, k[1:]) if len(pd.bdate_range(a, b)) == 2]
    gates = ([("surge", x, f"volume >= {x:.1f}x") for x in (1.0, 1.3, 1.7)]
             + [("speed", x, f"prints >= {x:.1f}x") for x in (1.0, 1.3, 1.7)]
             + [("run", x, f"{x}+ agreeing bars") for x in (1, 2, 3)]
             + [("bigprint", 1, "big-print net >= 1"), ("bigprint_sh", 0.01, "big-print net >= 1%")])
    res, pr = {}, {}
    for m in (3, 5):
        df = FS.build(D, P, m)
        for key, cut, lab in gates:
            if key not in df:
                continue
            on = df.dropna(subset=[key])
            on = on[on[key] >= cut]
            name = f"{m}-min {lab}"
            res[name] = TL.cell_eval([(d, g.gross.to_numpy()) for d, g in on.groupby("day")], FS.COST_PTS, D)
            pr[name] = paired_ci(df, key, cut)
    keys = list(res)
    raw = [res[x]["p_one"] if np.isfinite(res[x]["p_one"]) else 1.0 for x in keys]
    ph = C.holm(raw)
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    note = "; ".join(f"{x}: {d:+.3f}R [{lo:+.3f}, {hi:+.3f}]" for x, (d, lo, hi) in pr.items())
    TL.report("T16", "filter survey, tape families", res, keys,
              extra_ok=bool(pr[best][1] > 0), extra_lab=", paired interval above 0",
              old="no filter", note=note)


if __name__ == "__main__":
    main()
