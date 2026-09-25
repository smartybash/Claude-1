#!/usr/bin/env python3
"""Power of 3, pre-registered at reports/po3_preregistration.md. Seen data,
2010-06-07 -> 2026-09-24, run once. Reuses study_cd's exit_path and evaluate
(random-direction null with mirrored geometry) and study_e's atr14 unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import study_cd as S                                                # noqa: E402
import study_e as E                                                 # noqa: E402

A, B = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-09-24")
K = 0.10
TICK = 0.25
L = []
p = L.append


def tod(ts):
    return ts.dt.hour * 60 + ts.dt.minute


def find_setup(tm, o, h, l, c, ref_hi, ref_lo, w0, w1, thr, range_mode):
    """Scan bars with w0 <= tm < w1. Returns (side, reclaim_index, extreme) or None.
    side = +1 long (manipulation was DOWN), -1 short (manipulation was UP)."""
    man, ext = 0, None
    for i in range(len(tm)):
        if tm[i] < w0:
            continue
        if tm[i] >= w1:
            return None
        if man == 0:
            up = h[i] - ref_hi >= thr
            dn = ref_lo - l[i] >= thr
            if up and dn:                       # both on one bar: order unknown, skip day
                return None
            if up:
                man, ext = 1, h[i]
            elif dn:
                man, ext = -1, l[i]
            else:
                continue
        else:
            ext = max(ext, h[i]) if man == 1 else min(ext, l[i])
        if man == 1 and c[i] < ref_hi:
            return -1, i, ext
        if man == -1 and c[i] > ref_lo:
            return 1, i, ext
    return None


def run(variant):
    b, D = S.sessions("NQ")
    atr = E.atr14(D)
    rows, days = [], []
    ids = D.id_close
    sess_list = list(D.index)
    prev_of = {s: sess_list[i - 1] for i, s in enumerate(sess_list) if i > 0}
    for s, g in b.groupby("session"):
        if s < A or s > B or s not in D.index or D.at[s, "half_day"] or not np.isfinite(atr.get(s, np.nan)):
            continue
        g = g.sort_values("ts_et")
        t = g.ts_et
        mins = tod(t).to_numpy()
        evening = (t.dt.normalize() < s).to_numpy()
        day = ~evening
        rth = g.rth.to_numpy()
        thr = K * atr[s]
        if variant == "V2":
            ref_bar = np.flatnonzero(day & (mins >= 0) & (mins < 5))
            if not len(ref_bar):
                continue
            k0 = ref_bar[0]
            ref = g.open.to_numpy()[k0]
            ref_hi = ref_lo = ref
            w0, w1 = 570, 660
        elif variant == "V1":
            r = np.flatnonzero(rth)
            if not len(r):
                continue
            k0 = r[0]
            ref = g.open.to_numpy()[k0]
            ref_hi = ref_lo = ref
            w0, w1 = 570, 630
        else:
            asian = np.flatnonzero(evening & (mins >= 18 * 60))
            if len(asian) < 30:
                continue
            k0 = asian[0]
            ref_hi = g.high.to_numpy()[asian].max()
            ref_lo = g.low.to_numpy()[asian].min()
            w0, w1 = 120, 300
        last = np.flatnonzero(day & rth)
        if not len(last):
            continue
        kz = last[-1]
        seg = g.iloc[k0:kz + 1]
        if seg.instrument_id.nunique() != 1:
            continue
        iid = seg.instrument_id.iloc[0]
        days.append(s)
        sm = mins[k0:kz + 1]
        sday = day[k0:kz + 1]
        o, h, l, c = (seg[x].to_numpy() for x in ("open", "high", "low", "close"))
        # window minutes on the session DAY only (evening bars have large tod but are prior day)
        tm = np.where(sday, sm, -1)
        st = find_setup(tm, o, h, l, c, ref_hi, ref_lo, w0, w1, thr, variant == "V3")
        if st is None:
            continue
        side, i, ext = st
        ie = i + 1
        if ie > len(o) - 1:
            continue
        e = o[ie]
        stop = ext + TICK if side < 0 else ext - TICK
        risk = (stop - e) if side < 0 else (e - stop)
        if risk <= 0:
            continue
        if variant == "V1":
            tgt = e + side * 2 * risk
        elif variant == "V2":
            ps = prev_of.get(s)
            if ps is None or ids.get(ps) != iid:
                continue
            tgt = D.at[ps, "high"] if side > 0 else D.at[ps, "low"]
            if side * (tgt - e) < risk:
                continue
        else:
            tgt = e + side * 1e9                 # no target: flat 15:59
        px, _ = S.exit_path(o, h, l, c, ie, side, stop, tgt)
        mstop = e + (e - stop)
        mtgt = e - (tgt - e) if variant != "V3" else e - side * 1e9
        mpx, _ = S.exit_path(o, h, l, c, ie, -side, mstop, mtgt)
        rows.append((s, side, side * (px - e), -side * (mpx - e), risk))
    T = pd.DataFrame(rows, columns=["session", "side", "pts", "mir_pts", "risk"])
    return T, D, sorted(set(days))


def main():
    rng = np.random.default_rng(S.SEED)
    S.L.clear()
    p("POWER OF 3 -- NQ 1-minute, 2010-06-07 -> 2026-09-24, SEEN DATA (run once). Pre-registered.")
    p("Costs per side NQ $2.25 + 1 tick, MNQ $0.62 + 1 tick. Random-direction null, mirrored geometry, 5,000 sims.")
    p("")
    res = {}
    for v in ("V2", "V1", "V3"):
        T, D, days = run(v)
        r = S.evaluate(T, D, days, "NQ", A, B, mirror="mir_pts", rng=rng)
        res[v] = r
        p(f"=== {v}{' (PRIMARY)' if v == 'V2' else ' (secondary)'}: eligible sessions {len(days)}, trades {r['n']} "
          f"(long {int((T.side > 0).sum())}, short {int((T.side < 0).sum())})")
        p(f"    Sharpe {r['sharpe']:+.2f}  CAGR {100*r['cagr']:.2f}%  PF {r['pf']:.2f}  win {100*r['win']:.1f}%  "
          f"maxDD ${r['dd']:,.0f}/NQ ${r['dd_m']:,.0f}/MNQ  total ${r['total']:,.0f}")
        p(f"    random-direction null: 95th pct {r['p95']:+.2f}, p = {r['p']:.4f}")
        p("    per year $: " + "  ".join(f"{y}:{x:+,.0f}" for y, x in r["yr"].items()))
    hp = S.holm({v: res[v]["p"] for v in res})
    p("")
    p("=== KILL CRITERIA (Sharpe >= 0.8, PF >= 1.3, null Holm p <= 0.05, Sharpe > ORB baseline -0.37) ===")
    for v in res:
        r = res[v]
        ok = [r["sharpe"] >= 0.8, r["pf"] >= 1.3, hp[v] <= 0.05, r["sharpe"] > -0.37]
        tag = "PRIMARY" if v == "V2" else "secondary"
        p(f"  {v} ({tag}): Sharpe {r['sharpe']:+.2f} {'PASS' if ok[0] else 'FAIL'} | PF {r['pf']:.2f} "
          f"{'PASS' if ok[1] else 'FAIL'} | Holm p {hp[v]:.4f} {'PASS' if ok[2] else 'FAIL'} | vs ORB "
          f"{'PASS' if ok[3] else 'FAIL'}  => {'PASSES' if all(ok) else 'FAILS'}")
    prim = res["V2"]
    okp = prim["sharpe"] >= 0.8 and prim["pf"] >= 1.3 and hp["V2"] <= 0.05 and prim["sharpe"] > -0.37
    p("")
    p("VERDICT: " + ("PRIMARY PASSES -> forward paper-tracking only, from the registration date."
                     if okp else "PRIMARY FAILS -> Power of 3 is CLOSED."))
    txt = "\n".join(L)
    print(txt)
    (S.OUT / "po3_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
