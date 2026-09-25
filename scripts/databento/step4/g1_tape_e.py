#!/usr/bin/env python3
"""Step 4, G1 -- T13 footprint shapes (footprint.py), T14 footprint levels and
placebo (levels_footprint.py), T15 order-flow batch families A, B, E
(batch_ladder.py) and C (batch_sweep.py).

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions (tape adapter). roster.split is patched so
every full session (tape.is_full_session, unchanged) is "discovery": the ATAS
date windows mean nothing for Databento dates, and the D2 tick holdout is not
loaded at all. Frozen constants unchanged; cost 2.0 pt (stricter, applies).
INVENTORY CORRECTION: batch_ladder.py is families A, B and E on the tape (not a
depth script, as the inventory's X03 row said); only batch_book.py (D, F) needs
depth.

T13 primary: footprint.tradeable -- short the top quintile of absorb_lo, holds 5,
    15, 30 min, 2 pt cost. Three cells, Holm on one-sided session-clustered p.
    The IC table and its null count are reported. Pass: net > 0, p <= 0.05.
T14 primary: heavy footprint levels, revisit trade at 15, 30, 60 min, net of 2
    pt. Three cells, Holm. Pass also requires, at the best horizon, the frozen
    paired comparison against ordinary rungs (session bootstrap, 4,000, seed 0)
    with a 95% interval above 0, and the real level beating both +/-25-point
    placebos at 15 min (the frozen placebo test).
T15 primary: the registered batch bar (d85b15c, Part 4) for the eight tape
    features A1 A2 B1 B2 C1 C2 E1 E2 -- (1) IC |t| >= 3.0 across sessions, (2)
    beats its own circular-shift null, (3) top/bottom quintile at 15 min pays
    after 2 pt with a positive per-session mean. The p entering BH is the
    one-sided session-clustered p of (3), Holm across the eight; pass needs all
    three gates. C1/C2 use recombined Databento orders: sweep depth = |last -
    first print price| / 0.25 (prints are per price level, so this is the span
    the fills covered).
Old verdicts: T13 dead; T14 dead (placebo pays the same); T15 0 of 12 (A B C E:
0 of 8).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C, A = TL.C, TL.A
import tape                                                        # noqa: E402
import roster                                                      # noqa: E402


def split_all(days):
    disc, bad = {}, {}
    for d, x in sorted(days.items()):
        (disc if tape.is_full_session(x) else bad)[d] = x
    return disc, {}, bad


roster.split = split_all


def quintile_short_top(F, col, h, cost):
    G = F.dropna(subset=[f"fwd{h}", col]).copy()
    G["pts"] = G[f"fwd{h}"] * G.c
    q = pd.qcut(G[col].rank(method="first"), 5, labels=False)
    top = G[q == 4]
    return [(d, -g.pts.to_numpy()) for d, g in top.groupby("day")]


def t13(D):
    import footprint as FP
    FP.split = split_all
    C.run_frozen("footprint", [], "T13_frozen_output.txt")
    disc, _, _ = split_all(A.load_tape_all())
    per = {}
    for d, x in disc.items():
        f = FP.session_features(tape.rth(x))
        if f is not None:
            per[d] = f
    F = pd.concat([f.assign(day=d) for d, f in per.items()])
    return {f"short top absorb_lo, hold {h}m": TL.cell_eval(quintile_short_top(F, "absorb_lo", h, 2.0), 2.0, D)
            for h in FP.HORIZONS}


def t14(D):
    import levels_footprint as LF
    LF.split = split_all
    C.run_frozen("levels_footprint", [], "T14_frozen_output.txt")
    disc, _, _ = split_all(A.load_tape_all())
    allr = []
    for d, x in disc.items():
        s = tape.rth(x)
        R = LF.rungs_of(s)
        if R.empty:
            continue
        heavy = R[R.heavy >= LF.HEAVY]
        ordin = R[(R.heavy >= LF.ORDINARY[0]) & (R.heavy <= LF.ORDINARY[1])]
        if len(ordin) > len(heavy) and len(heavy) > 0:
            ordin = ordin.sample(len(heavy), random_state=0)
        for lv, tag in ((heavy, "heavy"), (ordin, "ordinary")):
            r = LF.revisits(s, lv, tag)
            if not r.empty:
                allr.append(r.assign(day=d))
    R = pd.concat(allr)
    res, paired = {}, {}
    rng = np.random.default_rng(0)
    for h in LF.HORIZONS:
        g = R[R.kind == "heavy"]
        res[f"heavy levels, +{h}m"] = TL.cell_eval(
            [(d, x[f"pts{h}"].to_numpy()) for d, x in g.groupby("day")], LF.COST_PTS, D)
        a = R[R.kind == "heavy"].groupby("day")[f"pts{h}"].mean()
        b = R[R.kind == "ordinary"].groupby("day")[f"pts{h}"].mean()
        dd = (a - b).dropna()
        bs = np.array([rng.choice(dd.to_numpy(), len(dd), replace=True).mean() for _ in range(4000)])
        paired[f"heavy levels, +{h}m"] = (dd.mean(), *np.percentile(bs, [2.5, 97.5]))
    plac = {}
    for off in (0.0, 25.0, -25.0):
        rows = []
        for d, x in disc.items():
            s = tape.rth(x)
            Rg = LF.rungs_of(s)
            if Rg.empty:
                continue
            lv = Rg[Rg.heavy >= LF.HEAVY].copy()
            lv["price"] = lv.price + off
            px, tm = s.price.to_numpy(np.float64), s.time.to_numpy()
            for _, L in lv.iterrows():
                j, side = LF.first_return(px, tm, L.born, L.price)
                if j is None or side == 0:
                    continue
                k = min(int(np.searchsorted(tm, tm[j] + np.timedelta64(15, "m"), "left")), len(px) - 1)
                rows.append(dict(day=d, pts15=int(side) * (px[k] - L.price)))
        plac[off] = pd.DataFrame(rows).pts15.mean() - LF.COST_PTS
    return res, paired, plac


def c_features(day, D):
    import batch_sweep as BS
    s = D[day]
    t0 = tape.session_day(s) + pd.Timedelta(hours=13, minutes=30)
    s = s.assign(bar=((s.time - t0) // pd.Timedelta(minutes=BS.BAR_MIN)))
    px, vol = s.groupby("bar").price.last(), s.groupby("bar").volume.sum()
    o = A.load_cum_all()[day]
    o = o[(o.time >= t0) & (o.time < t0 + pd.Timedelta(hours=6, minutes=30))].copy()
    o["span"] = (o.last_price - o.first_price).abs() / BS.TICK
    o["sign"] = np.where(o.aggressor == "B", 1.0, np.where(o.aggressor == "S", -1.0, 0.0))
    o["signed"] = o["sign"] * o.volume
    o["bar"] = (o.time - t0) // pd.Timedelta(minutes=BS.BAR_MIN)
    out = pd.DataFrame(index=px.index)
    out["px"], out["vol"] = px, vol
    for name, lim in (("C1", BS.SHALLOW), ("C2", BS.DEEP)):
        out[name] = o[o.span >= lim].groupby("bar").signed.sum()
    out = out.fillna({"C1": 0.0, "C2": 0.0})
    for name in ("C1", "C2"):
        out[name] = out[name] / out.vol.replace(0, np.nan)
    k = max(1, BS.HORIZON // BS.BAR_MIN)
    out["fwd_pts"] = (out.px.shift(-k) / out.px - 1.0) * out.px
    return out.replace([np.inf, -np.inf], np.nan)


def t15(D):
    import batch_ladder as BL
    import batch_sweep as BS
    from ic_harness import spearman
    BL.split = split_all
    C.run_frozen("batch_ladder", [], "T15_frozen_ladder_output.txt")
    per = BL.per_session()
    for d in list(per):
        cf = c_features(d, D)
        per[d] = per[d].join(cf[["C1", "C2"]], how="left")
    feats = ["A1", "A2", "B1", "B2", "C1", "C2", "E1", "E2"]
    rng = np.random.default_rng(0)
    ic, res = {}, {}
    Aall = pd.concat([F.assign(day=d) for d, F in per.items()])
    for c in feats:
        ics, nulls = [], []
        for d, F in per.items():
            x, y = F[c].to_numpy(float), F.fwd_pts.to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 30 or np.nanstd(x[m]) == 0:
                continue
            ics.append(spearman(x[m], y[m]))
            k = int(rng.integers(5, max(6, m.sum() - 5)))
            nulls.append(spearman(x[m], np.roll(y[m], k)))
        ics = np.array([v for v in ics if np.isfinite(v)])
        nulls = np.array([v for v in nulls if np.isfinite(v)])
        t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))) if len(ics) > 4 else np.nan
        nt = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls))) if len(nulls) > 4 else np.nan
        ic[c] = (ics.mean() if len(ics) else np.nan, t, nt, len(ics))
        G = Aall.dropna(subset=[c, "fwd_pts"])
        if G[c].nunique() < 5:
            continue
        q = pd.qcut(G[c].rank(method="first"), 5, labels=False)
        lo, hi = G[q == 0], G[q == 4]
        rows = [(d, g.fwd_pts.to_numpy()) for d, g in hi.groupby("day")] + \
               [(d, -g.fwd_pts.to_numpy()) for d, g in lo.groupby("day")]
        res[c] = TL.cell_eval(rows, BS.COST, D)
    return res, ic


def main():
    D = TL.days()
    print(f"sessions: {len(D)}")
    r13 = t13(D)
    TL.report("T13", "footprint shapes (absorb_lo priced)", r13, list(r13), old="dead")
    r14, pr, plac = t14(D)
    keys = list(r14)
    raw = [r14[k]["p_one"] if np.isfinite(r14[k]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    beats_placebo = plac[0.0] > max(plac[25.0], plac[-25.0])
    note = ("; ".join(f"{k}: vs ordinary {d:+.2f} [{lo:+.2f}, {hi:+.2f}]" for k, (d, lo, hi) in pr.items())
            + f"; placebo @15m net: real {plac[0.0]:+.2f}, +25 {plac[25.0]:+.2f}, -25 {plac[-25.0]:+.2f}")
    TL.report("T14", "footprint levels (revisit) + placebo", r14, keys,
              extra_ok=bool(pr[best][1] > 0 and beats_placebo),
              extra_lab=", beats ordinary rungs and both placebos", old="dead: placebo pays the same", note=note)
    r15, ic = t15(D)
    keys = [k for k in r15]
    gates = {k: (abs(ic[k][1]) >= 3.0, abs(ic[k][2]) < abs(ic[k][1]), r15[k]["mean_session"] > 0) for k in keys}
    note = "; ".join(f"{k}: IC {ic[k][0]:+.4f} t {ic[k][1]:+.2f} null t {ic[k][2]:+.2f} gates {''.join('Y' if g else 'n' for g in gates[k])}"
                     for k in keys)
    raw = [r15[k]["p_one"] if np.isfinite(r15[k]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    TL.report("T15", "order-flow batch A B C E (registered bar)", r15, keys,
              extra_ok=all(gates[best]), extra_lab=", all three registered gates",
              old="0 of 12 (A B C E: 0 of 8)", note=note)


if __name__ == "__main__":
    main()
