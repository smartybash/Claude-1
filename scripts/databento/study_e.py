#!/usr/bin/env python3
"""Study (e) -- four simple intraday rules, pre-registered at
reports/db_e_preregistration.md (commit 3b5f631) before any was run.

Reuses the exit simulation, evaluation and Holm code of study_cd.py unchanged.
IMPLEMENTATION (fixed before this script first ran): ATR14 is computed on the
daily RTH bars of full sessions; the RTH open is the first bar at or before 09:34;
"first 5-minute bar" = the bars with minute offset 0-4; the 5-minute Donchian
bars are built from 1-minute bars in 5-minute buckets from 09:30, and exits are
simulated on the 1-minute bars.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import study_cd as S                                                # noqa: E402

L = []
p = L.append


def atr14(D):
    F = D[~D.half_day & D.n_rth_bars.notna()].copy()
    pc = F.close.shift(1)
    tr = pd.concat([F.high - F.low, (F.high - pc).abs(), (F.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().shift(1)


def trade(o, h, l, c, k_in, side, stop, tgt):
    e = o[k_in]
    risk = (e - stop) if side > 0 else (stop - e)
    if risk <= 0:
        return None
    if tgt is None:
        tgt = e + side * 2 * risk
    px, _ = S.exit_path(o, h, l, c, k_in, side, stop, tgt)
    mpx, _ = S.exit_path(o, h, l, c, k_in, -side, e + (e - stop), e + (e - tgt))
    return side * (px - e), -side * (mpx - e)


def run():
    b, D = S.sessions("NQ")
    A = atr14(D)
    rows = {k: [] for k in ("gap_go", "gap_fade", "pdhl_brk", "donchian")}
    days = []
    prev = None
    for s, g in b[b.rth].groupby("session"):
        if s not in D.index or D.at[s, "half_day"] or g.instrument_id.nunique() != 1:
            prev = None
            continue
        m = g.m.to_numpy()
        o, h, l, c = (g[x].to_numpy() for x in ("open", "high", "low", "close"))
        iid = g.instrument_id.iloc[0]
        atr = A.get(s, np.nan)
        days.append(s)
        same = prev is not None and prev[0] == iid
        if m.min() <= 4 and np.isfinite(atr):
            f5 = m <= 4
            k5 = np.flatnonzero(m >= 5)
            if same and len(k5):
                op, pcl = o[0], prev[1]
                gap = op - pcl
                c5, h5, l5 = c[f5][-1], h[f5].max(), l[f5].min()
                if abs(gap) >= 0.5 * atr:
                    gs = 1 if gap > 0 else -1
                    if np.sign(c5 - op) == gs:                      # gap-and-go
                        r = trade(o, h, l, c, k5[0], gs, l5 if gs > 0 else h5, None)
                        if r: rows["gap_go"].append((s, *r))
                    elif np.sign(c5 - op) == -gs:                   # gap-fade
                        side = -gs
                        stop = h5 if gs > 0 else l5
                        e = o[k5[0]]
                        risk = (e - stop) if side > 0 else (stop - e)
                        if risk > 0 and side * (pcl - e) >= risk:
                            r = trade(o, h, l, c, k5[0], side, stop, pcl)
                            if r: rows["gap_fade"].append((s, *r))
            if same and np.isfinite(atr):                           # PDH/PDL breakout
                pdh, pdl = prev[2], prev[3]
                cand = np.flatnonzero((m >= 15) & (m < 330) & ((c > pdh) | (c < pdl)))
                if len(cand) and cand[0] + 1 < len(o):
                    j = cand[0]
                    up = c[j] > pdh
                    side = 1 if up else -1
                    stop = pdh - 0.25 * atr if up else pdl + 0.25 * atr
                    r = trade(o, h, l, c, j + 1, side, stop, None)
                    if r: rows["pdhl_brk"].append((s, *r))
        # intraday Donchian on 5-minute buckets
        bk = m // 5
        ub = np.unique(bk)
        H5 = np.array([h[bk == u].max() for u in ub])
        L5 = np.array([l[bk == u].min() for u in ub])
        C5 = np.array([c[bk == u][-1] for u in ub])
        for i in range(20, len(ub) - 1):
            hi, lo = H5[i - 20:i].max(), L5[i - 20:i].min()
            if C5[i] > hi or C5[i] < lo:
                side = 1 if C5[i] > hi else -1
                k_in = int(np.flatnonzero(bk == ub[i + 1])[0])
                if m[k_in] >= 330 + 60:
                    break
                r = trade(o, h, l, c, k_in, side, (hi + lo) / 2, None)
                if r: rows["donchian"].append((s, *r))
                break
        prev = (iid, c[-1], h.max(), l.min())
    out = {}
    for k, v in rows.items():
        out[k] = pd.DataFrame(v, columns=["session", "pts", "mir_pts"])
    return out, D, days


def main():
    rng = np.random.default_rng(S.SEED)
    T, D, days = run()
    S.L.clear()
    p("STUDY (e) -- four simple intraday rules, NQ, pre-registered 3b5f631")
    p("Costs per side NQ $2.25 + 1 tick, MNQ $0.62 + 1 tick. Random-direction null, mirrored geometry.")
    p("")
    res = S.report("(e) SIMPLE INTRADAY RULES", {k: (v, D, days, "NQ", "mir_pts") for k, v in T.items()}, rng)
    L.extend(S.L)
    hp = S.holm({k: res[(k, "2010")]["p"] for k in T})
    p("")
    p("=== KILL CRITERIA, 2010-2020 block (Sharpe >= 0.8, PF >= 1.3, null Holm p <= 0.05) ===")
    for k in T:
        r = res[(k, "2010")]
        ok = [r["sharpe"] >= 0.8, r["pf"] >= 1.3, hp[k] <= 0.05]
        p(f"  {k:<9} Sharpe {r['sharpe']:+.2f} {'PASS' if ok[0] else 'FAIL'} | PF {r['pf']:.2f} "
          f"{'PASS' if ok[1] else 'FAIL'} | Holm p {hp[k]:.4f} {'PASS' if ok[2] else 'FAIL'}"
          f"  => {'SURVIVES (forward data required)' if all(ok) else 'KILLED'}")
    txt = "\n".join(L)
    print(txt)
    (S.OUT / "db_e_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
