#!/usr/bin/env python3
"""Risk-managed rerun, Phase 2 (reports/risk_rerun_p2_preregistration.md).

Rebuilds the trades of the seven fixed-exit tape studies (T01 T02 T03 T10 T13 T14 T15)
exactly as the step-4 ports select them, checks the rebuild against the ports (count and
gross points per cell), then applies the Phase 1 risk block tick by tick: stop 0.5 x ADR20
x sqrt(hold/390), $250 risk (<= 10 MNQ), one position at a time per cell, $500 daily cap,
$4.00 per micro round trip.

    python3 scripts/databento/risk_rerun_p2.py --selftest
    python3 scripts/databento/risk_rerun_p2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "step4"))

STOP_K, RISK, CAP_MICROS, DAY_CAP, COST_MICRO, MMULT = 0.5, 250.0, 10, 500.0, 4.00, 2.0


# --------------------------------------------------------------- engine ----
def stop_distance(adrp, px, hold_min):
    return STOP_K * adrp * px * np.sqrt(max(min(hold_min, 1440.0), 1.0) / 390.0)


def size(sd):
    return min(int(np.floor(RISK / (sd * MMULT))), CAP_MICROS) if sd > 0 else 0


def tick_exit(P, side, px_in, i0, i1, sd):
    """Prints after the entry (i0 + 1 .. i1). First print at or through the stop fills there;
    otherwise the planned exit P[i1]. Returns (pnl points, exit index, stopped)."""
    seg = P[i0 + 1:i1 + 1]
    hit = np.flatnonzero(side * (seg - px_in) <= -sd)
    if len(hit):
        j = i0 + 1 + int(hit[0])
        return side * (P[j] - px_in), j, True
    return side * (P[i1] - px_in), i1, False


def run_cell(trades, prints, adr):
    """trades: DataFrame(k, side, px_in, i0, i1). Applies the whole risk block."""
    out, skipped = [], dict(open=0, cap=0, wide=0)
    for k, g in trades.sort_values(["k", "i0"]).groupby("k", sort=True):
        P, Tm = prints[k]
        busy, day_pnl = -1, 0.0
        a = adr.get(k, np.nan)
        for r in g.itertuples():
            if r.i0 <= busy:
                skipped["open"] += 1
                continue
            if day_pnl <= -DAY_CAP:
                skipped["cap"] += 1
                continue
            hold = (Tm[r.i1] - Tm[r.i0]) / np.timedelta64(1, "m")
            sd = stop_distance(a, r.px_in, hold)
            q = size(sd) if np.isfinite(sd) else 0
            if q < 1:
                skipped["wide"] += 1
                continue
            pnl, j, st = tick_exit(P, r.side, r.px_in, r.i0, r.i1, sd)
            net = q * (pnl * MMULT - COST_MICRO)
            day_pnl += net
            busy = j
            out.append(dict(k=k, side=r.side, qty=q, pnl=pnl, net=net, stopped=st, sd=sd))
    return pd.DataFrame(out), skipped


def daily_t(T, all_keys):
    daily = T.groupby("k").net.sum().reindex(all_keys, fill_value=0.0) if len(T) else \
        pd.Series(0.0, index=all_keys)
    sd = daily.std(ddof=1)
    t = daily.mean() / (sd / np.sqrt(len(daily))) if sd > 0 else np.nan
    return t, (float(stats.t.sf(t, len(daily) - 1)) if np.isfinite(t) else 1.0)


# ---------------------------------------------------------- rebuilders ----
def win_idx(Tm, ends):
    """Index of the last print strictly before each window end."""
    return np.searchsorted(Tm, np.asarray(ends, dtype="datetime64[ns]"), "left") - 1


def window_trades(k, w, secs, sel, side, kk, Tm, P):
    """Entry = close of window i (sel true), exit = close of window i + kk (row based)."""
    ends = (w.index + pd.Timedelta(seconds=secs)).to_numpy()
    pos = np.flatnonzero(np.asarray(sel, bool))
    pos = pos[pos + kk < len(w)]
    side = np.broadcast_to(np.asarray(side), (len(w),))[pos] if np.ndim(side) else np.full(len(pos), side)
    i0, i1 = win_idx(Tm, ends[pos]), win_idx(Tm, ends[pos + kk])
    return pd.DataFrame({"k": k, "side": side.astype(int), "px_in": P[i0], "i0": i0, "i1": i1})


def rebuild(D):
    import tape
    import step4_adapters as A
    import g1_tape_e as E
    cells = {}
    prints = {k: (s.price.to_numpy(np.float64), s.time.to_numpy()) for k, s in D.items()}

    def add(study, cell, df):
        cells.setdefault(study, {}).setdefault(cell, []).append(df)

    # T01
    import absorption as M1
    for k, s in D.items():
        P, Tm = prints[k]
        w = M1.windows(s, 30)
        hi, lo = w.delta.quantile(0.80), w.delta.quantile(0.20)
        flat = w["move"].abs() <= 5.0
        add("T01", "buy_absorbed_short", window_trades(k, w, 30, (w.delta >= hi) & flat, -1, 4, Tm, P))
        add("T01", "sell_absorbed_long", window_trades(k, w, 30, (w.delta <= lo) & flat, 1, 4, Tm, P))
    # T02
    import sweep_tape as M2
    W = {(k, secs): M2.windows(s, secs) for k, s in D.items() for secs in (30, 60)}
    for secs in (30, 60):
        for hold_s in (120, 300, 600, 1800):
            kk = max(1, hold_s // secs)
            for k in D:
                P, Tm = prints[k]
                w = W[(k, secs)]
                sel = (w.delta >= w.delta.quantile(0.80)) & (w["move"].abs() <= 5)
                add("T02", f"H1 {secs}s hold {hold_s // 60}m", window_trades(k, w, secs, sel, -1, kk, Tm, P))
    for q in (0.99, 0.999):
        for hold_s in (120, 600):
            kk = hold_s // 30
            for k, s in D.items():
                P, Tm = prints[k]
                w = W[(k, 30)]
                bw, _ = M2.block_windows(s, 30, q)
                w = w.join(bw).fillna({"bdelta": 0.0, "bvol": 0.0})
                hot = w.bdelta.abs() >= w.bdelta.abs().quantile(0.90)
                sgn = np.sign(w.bdelta).to_numpy()
                sel = (hot & (sgn != 0)).to_numpy()
                add("T02", f"H2 q{q} go hold {hold_s // 60}m", window_trades(k, w, 30, sel, sgn, kk, Tm, P))
                add("T02", f"H2 q{q} fade hold {hold_s // 60}m", window_trades(k, w, 30, sel, -sgn, kk, Tm, P))
    for look_m in (15, 30, 60):
        for hold_s in (300, 900):
            kk, L = hold_s // 30, look_m * 2
            for k in D:
                P, Tm = prints[k]
                w = W[(k, 30)].copy()
                w["cvd"] = w.delta.cumsum()
                short = (w["last"] >= w["last"].rolling(L).max()) & (w["cvd"] < w["cvd"].rolling(L).max())
                long_ = (w["last"] <= w["last"].rolling(L).min()) & (w["cvd"] > w["cvd"].rolling(L).min())
                lab = f"H3 look {look_m}m hold {hold_s // 60}m"
                add("T02", lab, window_trades(k, w, 30, short, -1, kk, Tm, P))
                add("T02", lab, window_trades(k, w, 30, long_, 1, kk, Tm, P))
    # T03
    import divergence_audit as M3
    for use_cvd, lab in ((True, "divergence_dedup"), (False, "control_no_cvd")):
        for k, s in D.items():
            P, Tm = prints[k]
            w = M3.windows(s)
            tr, kk = M3.trades(w, use_cvd, True)
            if not tr:
                continue
            pos = np.array([i for i, _ in tr])
            sd_ = np.array([d for _, d in tr])
            ends = (w.index + pd.Timedelta(seconds=30)).to_numpy()
            i0, i1 = win_idx(Tm, ends[pos]), win_idx(Tm, ends[pos + kk])
            add("T03", lab, pd.DataFrame({"k": k, "side": sd_, "px_in": P[i0], "i0": i0, "i1": i1}))
    # T10
    import forecast as FC
    F = FC.build()
    Z = FC.zscore_within(F, ["vwap_disp"])
    Z = Z.assign(q=pd.qcut(Z.vwap_disp.rank(method="first"), 5, labels=False).to_numpy())
    for lab, (hh, mm) in {"exit 17:00 (13:00 ET)": (17, 0), "exit 19:00 (15:00 ET)": (19, 0),
                          "exit close 20:00 (16:00 ET)": (20, 0)}.items():
        for d, g in Z.groupby("day"):
            sig = g[(g.q == 4) | (g.q == 0)]
            if sig.empty or d not in prints:
                continue
            t0 = sig.index[0]
            ex = t0.normalize() + pd.Timedelta(hours=hh, minutes=mm)
            entry_t = t0 + pd.Timedelta(minutes=1)
            if entry_t >= ex:
                continue
            P, Tm = prints[d]
            i_in = int(np.searchsorted(Tm, np.datetime64(entry_t), "left")) - 1
            i_out = int(np.searchsorted(Tm, np.datetime64(ex), "left")) - 1
            if i_in < 0 or i_out <= i_in:
                continue
            side = -1 if sig.q.iloc[0] == 4 else 1
            add("T10", lab, pd.DataFrame({"k": [d], "side": [side], "px_in": [P[i_in]], "i0": [i_in], "i1": [i_out]}))
    # T13 (full sessions, as the port)
    import footprint as FP
    FP.split = E.split_all
    disc, _, _ = E.split_all(A.load_tape_all())
    per, rth13 = {}, {}
    for d, x in disc.items():
        s = tape.rth(x)
        f = FP.session_features(s)
        if f is not None:
            per[d], rth13[d] = f, s
    for d, s in rth13.items():
        prints.setdefault(d, (s.price.to_numpy(np.float64), s.time.to_numpy()))
    Fall = pd.concat([f.assign(day=d, _pos=np.arange(len(f))) for d, f in per.items()])
    for h in FP.HORIZONS:
        kk = max(1, h // 5)
        G = Fall.dropna(subset=[f"fwd{h}", "absorb_lo"]).copy()
        q = pd.qcut(G["absorb_lo"].rank(method="first"), 5, labels=False)
        top = G[q == 4]
        for d, g in top.groupby("day"):
            f = per[d]
            P, Tm = prints[d]
            t0 = rth13[d].time.iloc[0].normalize() + pd.Timedelta(hours=13, minutes=30)
            pos = g._pos.to_numpy()
            b0, b1 = f.index.to_numpy()[pos], f.index.to_numpy()[pos + kk]
            i0 = win_idx(Tm, (t0 + pd.to_timedelta((b0 + 1) * 5, unit="min")).to_numpy())
            i1 = win_idx(Tm, (t0 + pd.to_timedelta((b1 + 1) * 5, unit="min")).to_numpy())
            add("T13", f"short top absorb_lo, hold {h}m", pd.DataFrame({"k": d, "side": -1, "px_in": P[i0], "i0": i0, "i1": i1}))
    # T14 (heavy levels, full sessions)
    import levels_footprint as LF
    for d, x in disc.items():
        s = tape.rth(x)
        prints.setdefault(d, (s.price.to_numpy(np.float64), s.time.to_numpy()))
        R = LF.rungs_of(s)
        if R.empty:
            continue
        heavy = R[R.heavy >= LF.HEAVY]
        P, Tm = prints[d]
        px, tm = s.price.to_numpy(np.float64), s.time.to_numpy()
        for _, L in heavy.iterrows():
            j, side = LF.first_return(px, tm, L.born, L.price)
            if j is None or side == 0:
                continue
            for h in LF.HORIZONS:
                kx = min(int(np.searchsorted(tm, tm[j] + np.timedelta64(h, "m"), "left")), len(px) - 1)
                add("T14", f"heavy levels, +{h}m", pd.DataFrame({"k": [d], "side": [int(side)], "px_in": [L.price],
                                                                 "i0": [j], "i1": [kx]}))
    # T15
    import batch_ladder as BL
    import batch_sweep as BS
    BL.split = E.split_all
    per15 = BL.per_session()
    for d in list(per15):
        cf = E.c_features(d, D)
        per15[d] = per15[d].join(cf[["C1", "C2"]], how="left")
    kk = max(1, BL.HORIZON // BL.BAR_MIN)
    Aall = pd.concat([F_.assign(day=d, _pos=np.arange(len(F_))) for d, F_ in per15.items()])
    for c in ["A1", "A2", "B1", "B2", "C1", "C2", "E1", "E2"]:
        G = Aall.dropna(subset=[c, "fwd_pts"])
        if G[c].nunique() < 5:
            continue
        q = pd.qcut(G[c].rank(method="first"), 5, labels=False)
        for grp, side in ((G[q == 4], 1), (G[q == 0], -1)):
            for d, g in grp.groupby("day"):
                F_ = per15[d]
                P, Tm = prints[d]
                t0 = tape.session_day(D[d]) + pd.Timedelta(hours=13, minutes=30)
                pos = g._pos.to_numpy()
                ok = pos + kk < len(F_)
                pos = pos[ok]
                b0, b1 = F_.index.to_numpy()[pos], F_.index.to_numpy()[pos + kk]
                i0 = win_idx(Tm, (t0 + pd.to_timedelta((b0 + 1) * BL.BAR_MIN, unit="min")).to_numpy())
                i1 = win_idx(Tm, (t0 + pd.to_timedelta((b1 + 1) * BL.BAR_MIN, unit="min")).to_numpy())
                add("T15", c, pd.DataFrame({"k": d, "side": side, "px_in": P[i0], "i0": i0, "i1": i1}))
    out = {st: {c: pd.concat(v, ignore_index=True) for c, v in cs.items()} for st, cs in cells.items()}
    _ = BS
    return out, prints


def port_reference(D):
    """Run the step-4 port functions with cell_eval replaced by a recorder: count and
    gross-point sum of every cell (the reproduction target)."""
    import step4_common as C
    import tape_lib as TL
    import g1_tape_a as GA
    import g1_tape_d as GD
    import g1_tape_e as GE
    C.run_frozen = lambda *a, **k: (None, "")

    def rec(rows, frozen_rt, all_sessions):
        v = np.concatenate([np.asarray(x, float) for _, x in rows]) if rows else np.array([])
        v = v[np.isfinite(v)]
        return dict(n=len(v), gross=float(v.sum()))
    GA.cell_eval = rec
    TL.cell_eval = rec
    ref = {"T01": GA.t01(D), "T02": GA.t02(D), "T03": GA.t03(D), "T10": GD.t10(D), "T13": GE.t13(D)}
    ref["T14"] = GE.t14(D)[0]
    ref["T15"] = GE.t15(D)[0]
    return ref


PRIMARY = {"T01": ["buy_absorbed_short", "sell_absorbed_long"], "T03": ["divergence_dedup"]}
CARRIED = {"T14": "paired vs ordinary rungs and +/-25 placebos (step 4: failed)",
           "T15": "IC |t| >= 3 and beats circular-shift null (step 4: failed)"}


def main():
    import tape_lib as TL
    import ldm
    import step4_common as C4
    D = TL.days()
    A = ldm.load("NQ", pd.Timestamp("2026-09-24"))
    adr_by_day = pd.Series(A["adrp"], index=A["days"])
    cells, prints = rebuild(D)
    ref = port_reference(D)
    adr = {k: float(adr_by_day.get(TL.sess(k), np.nan)) for k in prints}
    keys = sorted(D)
    L = ["RISK-MANAGED RERUN, PHASE 2 -- seven fixed-exit tape studies, Databento discovery sessions (seen)",
         "Registered reports/risk_rerun_p2_preregistration.md. Stop 0.5 x ADR20 x sqrt(hold/390) on every tick; "
         "$250 risk (<= 10 MNQ); one position per cell; $500 daily cap; $4.00 per micro RT.", "",
         "REPRODUCTION GATE (unstopped rebuild vs step-4 port: trades, gross points)"]
    good = {}
    for st in ("T01", "T02", "T03", "T10", "T13", "T14", "T15"):
        for c, T in cells.get(st, {}).items():
            g = (T.side * (np.array([prints[k][0][i] for k, i in zip(T.k, T.i1)]) - T.px_in)).to_numpy()
            n, s = int(np.isfinite(g).sum()), float(np.nansum(g))
            r = ref.get(st, {}).get(c)
            ok = r is not None and r["n"] == n and abs(r["gross"] - s) <= 0.01 * max(n, 1)
            good.setdefault(st, {})[c] = ok
            L.append(f"  {st} {c:<34} rebuild n {n:>6} gross {s:>+10.2f} | port n {r['n'] if r else '-':>6} "
                     f"gross {r['gross'] if r else float('nan'):>+10.2f} -> {'OK' if ok else 'NOT REPRODUCED'}")
    if REPRO_ONLY:
        txt = "\n".join(L)
        print(txt)
        return
    L += ["", "RESULTS WITH THE RISK BLOCK"]
    study_p = {}
    for st in ("T01", "T02", "T03", "T10", "T13", "T14", "T15"):
        res = {}
        for c, T in cells.get(st, {}).items():
            if not good[st][c]:
                continue
            R, skipped = run_cell(T, prints, adr)
            t, p = daily_t(R, keys)
            g = (T.side * (np.array([prints[k][0][i] for k, i in zip(T.k, T.i1)]) - T.px_in)).mean()
            res[c] = dict(R=R, t=t, p=p, skipped=skipped, gross_unstopped=g)
        prim = [c for c in PRIMARY.get(st, list(res)) if c in res]
        if not prim:
            L.append(f"  {st}: no reproduced primary cell -> not evaluated")
            continue
        ph = dict(zip(prim, C4.holm([res[c]["p"] for c in prim])))
        best = min(prim, key=lambda c: (ph[c], res[c]["p"]))
        R = res[best]["R"]
        extra, why = True, ""
        if st == "T03" and "control_no_cvd" in res:
            ctl = res["control_no_cvd"]["R"]
            extra = (R.net.mean() if len(R) else -np.inf) > (ctl.net.mean() if len(ctl) else -np.inf)
            why = f"beats risk-managed control: {extra}"
        if st == "T10":
            extra = all(np.isfinite(res[c]["t"]) and res[c]["t"] >= 2.4 for c in prim)
            why = f"t >= 2.4 at every exit: {extra}"
        if st in CARRIED:
            extra, why = False, f"carried-over gate: {CARRIED[st]}"
        net_ok = len(R) > 0 and R.net.sum() > 0
        study_p[st] = (ph[best], net_ok and extra)
        for c in res:
            Rc, sk = res[c]["R"], res[c]["skipped"]
            L.append(f"  {st} {c:<34} trades {len(Rc):>5} | skipped open {sk['open']:>5} cap {sk['cap']:>3} wide "
                     f"{sk['wide']:>3} | ${Rc.net.mean() if len(Rc) else 0:+7.1f}/trade, total ${Rc.net.sum() if len(Rc) else 0:+9,.0f} "
                     f"| stops {100 * Rc.stopped.mean() if len(Rc) else 0:3.0f}% | micros {Rc.qty.mean() if len(Rc) else 0:4.1f} | "
                     f"t {res[c]['t']:+.2f} p {res[c]['p']:.4f}" + (f" Holm {ph[c]:.4f}" if c in ph else ""))
        L.append(f"    {st} best {best}: Holm p {ph[best]:.4f}; net > 0: {net_ok}; {why or 'no extra gate'}")
    # BH across studies
    sts = list(study_p)
    ps = np.array([study_p[s][0] for s in sts])
    o = np.argsort(ps)
    m = len(ps)
    bh = np.empty(m)
    run = 1.0
    for rank in range(m - 1, -1, -1):
        i = o[rank]
        run = min(run, ps[i] * m / (rank + 1))
        bh[i] = run
    L += ["", "VERDICTS (BH across studies, q = 0.05; pass = net > 0, extra gates, BH-adjusted p <= 0.05)"]
    for s, b in zip(sts, bh):
        ok = study_p[s][1] and b <= 0.05
        L.append(f"  {s}: study p {study_p[s][0]:.4f}, BH {b:.4f} -> {'PASS (candidate; needs tick data forward)' if ok else 'stays closed'}")
    txt = "\n".join(L)
    print(txt)
    (HERE.parents[1] / "reports/risk_rerun_p2_output.txt").write_text(txt + "\n")


def selftest():
    def chk(name, got, want):
        print(f"[{'ok' if got == want else 'FAIL'}] {name}: {got}")
        if got != want:
            raise SystemExit(1)
    P = np.array([100, 100.5, 99.0, 98.0, 101.0])
    chk("long stopped at first print through (gap fill at print)", tick_exit(P, 1, 100.0, 0, 4, 1.5)[:3],
        (-2.0, 3, True))
    chk("long, touch exactly at stop", tick_exit(np.array([100, 98.5, 102.0]), 1, 100.0, 0, 2, 1.5)[:3], (-1.5, 1, True))
    chk("long not stopped -> planned exit", tick_exit(np.array([100, 99.0, 101.0]), 1, 100.0, 0, 2, 1.5)[:3],
        (1.0, 2, False))
    r = tick_exit(np.array([100, 101.6, 99.0]), -1, 100.0, 0, 2, 1.5)
    chk("short stopped", (round(float(r[0]), 6), r[1], r[2]), (-1.6, 1, True))
    chk("size", (size(10.0), size(50.0), size(200.0)), (10, 2, 0))
    Tm = (np.datetime64("2026-03-02T13:30") + np.arange(10) * np.timedelta64(1, "m")).astype("datetime64[ns]")
    prints = {"k": (np.array([100, 100, 100, 97, 100, 100, 100, 100, 104, 100.0]), Tm)}
    T = pd.DataFrame({"k": "k", "side": [1, 1, 1], "px_in": [100.0, 100.0, 100.0], "i0": [0, 2, 6], "i1": [5, 7, 9]})
    R, sk = run_cell(T, prints, {"k": 0.02})
    chk("one position at a time: second trade skipped while the first is open",
        (len(R), sk["open"]), (2, 1))
    print("selftest passed")


REPRO_ONLY = "--repro" in sys.argv

if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
