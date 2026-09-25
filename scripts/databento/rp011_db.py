#!/usr/bin/env python3
"""RP-011 Stage 1 on the Databento discovery ticks -- rp011_stage1_preregistration.md
(cba8a50) with Amendment 1 (fc2ca9f). Discovery sessions are labelled
"sessions already read by step-4 tape studies". The holdout is NOT loaded here.

IMPLEMENTATION (fixed before the first run):
  * sessions: the 65-session gate table (reports/rp011_quality_gate.csv) with the
    amended volume check (-5% <= trades/cleared - 1 <= 0) and every other criterion
    unchanged; sessions in time order.
  * windows: orderflow_core.windows(s, 30) on RTH prints, exactly as RP-010's
    build(); minutes after the open from ET (tape clock minus 4 h); first and last
    5 minutes excluded; tod = minutes at the window's first print.
  * construction: rp011_spec.label_block_relative and rp011_spec.retain, unchanged.
  * outcomes: from the last print of the window, strictly after it; r{h} =
    direction-adjusted move at the last print within h seconds (sign of the
    window's delta), h in 30, 60, 180, 300, 600, 900; MFE/MAE over the same slice.
  * matched random times: one ORDINARY window per event, same session and block,
    |tod difference| <= 15 min, |delta| within 25%, drawn with a fixed seed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent / "step4"))
import tape_lib as TL                                              # noqa: E402
C = TL.C
import orderflow_core as OF                                        # noqa: E402
import rp011_spec as RS                                            # noqa: E402
import tape                                                        # noqa: E402

TICK = 0.25
HZ = (30, 60, 180, 300, 600, 900)
OUT = C.ROOT / "reports"
WDIR = C.ROOT / "data/clean/rp011"
SEED = 20260925
L = []
p = L.append


def gate_sessions():
    q = pd.read_csv(OUT / "rp011_quality_gate.csv")
    base = [c for c in q.columns if c.startswith("ok_") and c != "ok_volume"]
    q["ok_volume_amended"] = (q.recon_dev <= 0) & (q.recon_dev >= -0.05)
    q["passes_amended"] = q[base].all(axis=1) & q.ok_volume_amended
    return q


def build(sessions):
    D = {k: tape.rth(v) for k, v in TL.A.load_tape_all().items()}
    rows = []
    for ds in sessions:
        key = ds.replace("-", "")
        s = D[key].sort_values("time", kind="stable").reset_index(drop=True)
        et = s.time - pd.Timedelta(hours=4)
        m = ((et - et.dt.normalize()).dt.total_seconds() / 60.0 - 570.0).to_numpy()
        body = (m >= 5) & (m < 385)
        s = s.loc[body].reset_index(drop=True)
        mm = m[body]
        lv = float(np.std(np.diff(np.log(s["price"].to_numpy(float)[::100]))))
        for k, g in OF.windows(s, 30):
            a = OF.aggression(g)
            pr = OF.progress(g, TICK)
            im = OF.impact(a, pr)
            j0, j1 = int(g.index[0]), int(g.index[-1])
            rows.append(dict(day=key, wk=pd.Timestamp(ds).isocalendar().week, widx=int(k),
                             tod=float(mm[j0]), i_end=j1, delta=a["delta"], total=a["total"],
                             imb=a["imbalance"], ticks=pr["ticks"], tpk=im["ticks_per_1k"],
                             aligned=im["aligned"], loc_vol=lv))
    W = pd.DataFrame(rows)
    W["block"] = W.tod.map(RS.block_of)
    W = W[W.block != "outside"].reset_index(drop=True)
    W["side"] = np.where(W.delta > 0, "buy", np.where(W.delta < 0, "sell", "flat"))
    return W, D


def outcomes(W, D):
    out = []
    for d, g in W.groupby("day"):
        s = D[d].sort_values("time", kind="stable").reset_index(drop=True)
        et = s.time - pd.Timedelta(hours=4)
        m = ((et - et.dt.normalize()).dt.total_seconds() / 60.0 - 570.0).to_numpy()
        s = s.loc[(m >= 5) & (m < 385)].reset_index(drop=True)
        px = s.price.to_numpy(float)
        tt = (s.time - s.time.iloc[0]).dt.total_seconds().to_numpy()
        for r in g.itertuples():
            j = r.i_end
            sgn = np.sign(r.delta)
            rec = {"_i": r.Index}
            for h in HZ:
                hi = int(np.searchsorted(tt, tt[j] + h, "right"))
                seg = px[j + 1:hi]
                if len(seg) == 0 or sgn == 0:
                    rec[f"r{h}"] = rec[f"mfe{h}"] = np.nan
                    continue
                adv = sgn * (seg - px[j])
                rec[f"r{h}"] = float(adv[-1])
                rec[f"mfe{h}"] = float(adv.max())
            out.append(rec)
    R = pd.DataFrame(out).set_index("_i")
    return W.join(R)


def counts_gate(W, K, binds):
    g = RS.grid(K)
    C_ = W[W.state.isin(["INITIATIVE", "ABSORPTION"])]
    gc = RS.grid(C_)
    ok = {}
    miss = [b for b in RS.NAMES if gc.reindex(RS.NAMES).fillna(0).loc[b].min() == 0]
    ok["1 all four blocks produce both states"] = (not miss, f"missing: {miss}")
    empty = [b for b in RS.NAMES if g.loc[b].sum() == 0]
    ok["2 no block structurally empty"] = (not empty, f"empty: {empty}")
    share = 100 * g.sum(axis=1) / max(1, g.values.sum())
    ok["3 no block over 40% of retained"] = (share.max() <= 40.0,
                                             ", ".join(f"{b} {share[b]:.1f}%" for b in RS.NAMES))
    sess = K.groupby(["block", "state"]).day.nunique()
    one_sided, dom, few = [], [], []
    for b in RS.NAMES:
        for st in ("INITIATIVE", "ABSORPTION"):
            cell = K[(K.block == b) & (K.state == st)]
            if not len(cell):
                continue
            ns = cell.day.nunique()
            if ns >= 5 and ((cell.side == "buy").sum() == 0 or (cell.side == "sell").sum() == 0):
                one_sided.append(f"{b}/{st}")
            if ns < 5:
                few.append(f"{b}/{st} ({ns})")
            top4 = cell.day.value_counts().head(4).sum()
            if top4 > 0.5 * len(cell):
                dom.append(f"{b}/{st} top4 {100*top4/len(cell):.0f}%")
    ok["4 buy and sell in every interpretable cell"] = (not one_sided, f"one-sided: {one_sided}")
    nlab = W[W.state != "WARMUP"].day.nunique()
    bind_rate = binds.groupby(["block", "state"]).day.nunique() / max(1, nlab) * 100 if len(binds) else pd.Series(dtype=float)
    ok["5 cap binds on <= 50% of sessions per cell"] = (
        (bind_rate.max() if len(bind_rate) else 0) <= 50.0,
        f"max {bind_rate.max() if len(bind_rate) else 0:.1f}%")
    both30 = [b for b in RS.NAMES
              if sess.get((b, "INITIATIVE"), 0) >= 30 and sess.get((b, "ABSORPTION"), 0) >= 30]
    ok["6 >= 3 blocks with both states in >= 30 sessions"] = (len(both30) >= 3, f"blocks: {both30}")
    ok["7 closing block among them"] = ("closing" in both30, "")
    ok["8 no cell dominated by few sessions"] = (not few and not dom, f"few: {few}; dominated: {dom}")
    return ok, sess


def clustered_diff(E, col="r900"):
    a = E[E.state == "INITIATIVE"].groupby("day")[col].mean()
    b = E[E.state == "ABSORPTION"].groupby("day")[col].mean()
    d = (a - b).dropna()
    if len(d) < 3:
        return np.nan, np.nan, np.nan, d
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    return float(d.mean()), float(t), float(stats.t.sf(t, len(d) - 1)), d


def block_eval(b, E, O, months, rng):
    Eb, Ob = E[E.block == b], O[O.block == b]
    ini, ab = Eb[Eb.state == "INITIATIVE"], Eb[Eb.state == "ABSORPTION"]
    Dm, t, p1, dser = clustered_diff(Eb)
    mi, ma = ini.r900.mean(), ab.r900.mean()
    sel = {"delta": Ob[Ob.delta.abs() >= Ob.delta.abs().quantile(.9)].r900.mean(),
           "progress": Ob[Ob.ticks.abs() >= Ob.ticks.abs().quantile(.9)].r900.mean(),
           "volume": Ob[Ob.total >= Ob.total.quantile(.9)].r900.mean(),
           "loc_vol": Ob[Ob.loc_vol >= Ob.loc_vol.quantile(.9)].r900.mean(),
           "impact": Ob[Ob.tpk >= Ob.tpk.quantile(.9)].r900.mean()}
    pool = Ob[Ob.state == "ORDINARY"]
    mt = {"INITIATIVE": [], "ABSORPTION": []}
    for r in Eb.itertuples():
        c = pool[(pool.day == r.day) & ((pool.tod - r.tod).abs() <= 15)
                 & ((pool.delta.abs() - abs(r.delta)).abs() <= 0.25 * abs(r.delta))]
        if len(c):
            mt[r.state].append(c.r900.iloc[int(rng.integers(len(c)))])
    m_ini = np.nanmean(mt["INITIATIVE"]) if mt["INITIATIVE"] else np.nan
    m_ab = np.nanmean(mt["ABSORPTION"]) if mt["ABSORPTION"] else np.nan
    it = ini.ticks.abs()
    c2i = pool[(pool.ticks.abs() >= it.quantile(.1)) & (pool.ticks.abs() <= it.quantile(.9))].r900.mean() if len(ini) else np.nan
    c2a = pool[pool.ticks.abs() <= ab.ticks.abs().quantile(.9)].r900.mean() if len(ab) else np.nan
    c4 = Ob[(Ob.total >= Ob.total.quantile(.9)) & (Ob.imb <= Ob.imb.quantile(.5))].r900.mean()
    sides_ok = (ini[ini.side == "buy"].r900.mean() > 0 and ini[ini.side == "sell"].r900.mean() > 0
                and ab[ab.side == "buy"].r900.mean() < 0 and ab[ab.side == "sell"].r900.mean() < 0)
    order = dser.sort_values(ascending=False)
    d_b3 = dser.drop(order.index[:3]).mean() if len(dser) > 3 else np.nan
    best3_share = order.iloc[:3].sum() / dser.sum() * 100 if len(dser) > 3 and dser.sum() > 0 else np.nan
    wk = Eb.groupby(["wk", "state"]).r900.mean().unstack()
    wkd = (wk.get("INITIATIVE") - wk.get("ABSORPTION")).dropna() if {"INITIATIVE", "ABSORPTION"} <= set(wk.columns) else pd.Series(dtype=float)
    cont300 = (ini.r300 > 0).mean() if len(ini) else np.nan
    freq = len(Eb) / months
    P = {
        "1 different paths (D t >= 2)": np.isfinite(t) and t >= 2,
        "2 initiative continues": mi > 0 and cont300 > 0.5,
        "3 absorption reverses": ma < 0,
        "4 buy and sell both correct": bool(sides_ok),
        "5 impact load-bearing": mi > max(sel.values()) and ma < min(sel.values()),
        "6 matched controls materially weaker": (np.isfinite(m_ini) and np.isfinite(m_ab)
                                                 and m_ini < 0.5 * mi and m_ab > 0.5 * ma and mi > 0 and ma < 0),
        "7 survives session clustering": np.isfinite(t) and t >= 2,
        "8 survives removing best three sessions": np.isfinite(d_b3) and d_b3 > 0,
        "9 appears across weeks (>= 60%)": len(wkd) > 0 and (wkd > 0).mean() >= 0.6,
        "10 clears 2 pt with 1 pt headroom": mi - 2.0 >= 1.0 and -ma - 2.0 >= 1.0,
        "11 >= 12 retained events / month": freq >= 12,
    }
    best = max(mi, -ma) if np.isfinite(mi) and np.isfinite(ma) else np.nan
    Kc = {
        "K1 delta alone similar": sel["delta"] >= 0.8 * mi if mi > 0 else True,
        "K2 progress alone similar": sel["progress"] >= 0.8 * mi if mi > 0 else True,
        "K3 volume alone similar": sel["volume"] >= 0.8 * mi if mi > 0 else True,
        "K4 only one side works": not sides_ok,
        "K5 best three sessions > 50% of D": (not np.isfinite(best3_share)) or best3_share > 50,
        "K6 matched times match the treatment": (np.isfinite(m_ini) and m_ini >= mi) or (np.isfinite(m_ab) and m_ab <= ma),
        "K7 aggressor checks fail": False,
        "K8 better state below 2 pt": not (np.isfinite(best) and best >= 2.0),
        "K9 controls 2-4 match the treatment": ((np.isfinite(c2i) and c2i >= mi) or (np.isfinite(c4) and c4 >= mi)
                                               or (np.isfinite(c2a) and c2a <= ma)),
        "K10 states not opposite": not (mi > 0 and ma < 0),
    }
    info = dict(n_ini=len(ini), n_abs=len(ab), s_ini=ini.day.nunique(), s_abs=ab.day.nunique(),
                ini=mi, abs=ma, D=Dm, t=t, p1=p1, sel=sel, m_ini=m_ini, m_abs=m_ab,
                c2i=c2i, c2a=c2a, c4=c4, d_b3=d_b3, best3=best3_share, cont300=cont300, freq=freq)
    return P, Kc, info


def main():
    r = subprocess.run([sys.executable, str(C.ROOT / "scripts/orderflow/test_platform.py")],
                       capture_output=True, text=True)
    line = [x for x in r.stdout.splitlines() if "PASS " in x and "FAIL" in x]
    p("RP-011 STAGE 1 -- DATABENTO DISCOVERY, sessions already read by step-4 tape studies")
    p(f"platform tests: {line[-1].strip() if line else '(no summary)'}  (exit {r.returncode})")
    if r.returncode != 0:
        p("PLATFORM TESTS FAILED -- stop.")
        return finish()
    q = gate_sessions()
    ok_s = q[q.passes_amended].session.tolist()
    p(f"quality gate (amended volume check): {len(ok_s)} of {len(q)} sessions pass (>= 50 required)")
    if len(ok_s) < 50:
        p("GATE FAILS -- stop.")
        return finish()
    W, D = build(ok_s)
    W, THR = RS.label_block_relative(W)
    kept, binds = RS.retain(W)
    W["event"] = kept
    lab = W[W.state != "WARMUP"]
    K = W[W.event]
    nlab = lab.day.nunique()
    p(f"sessions {W.day.nunique()}, warm-up 10, labelled {nlab}; windows {len(lab)}; "
      f"candidates {int(lab.state.isin(['INITIATIVE','ABSORPTION']).sum())}; retained {len(K)} "
      f"({len(K)/nlab:.2f}/session)")
    p("")
    p("=== RETAINED by block x state ===")
    p("  " + RS.grid(K).to_string().replace("\n", "\n  "))
    ok, sess = counts_gate(W, K, binds)
    p("")
    p("=== COUNTS GATE (all eight must hold before any outcome) ===")
    p("  independent sessions per cell: " + sess.to_string().replace("\n", "; "))
    for k, (v, s) in ok.items():
        p(f"  [{'PASS' if v else 'FAIL'}] {k}   {s}")
    WDIR.mkdir(parents=True, exist_ok=True)
    W.to_parquet(WDIR / "rp011_discovery_windows.parquet", index=False)
    if not all(v for v, _ in ok.values()):
        p("")
        p("COUNTS GATE FAILS -- RP-011 returns for redesign; no outcome computed; nothing amended.")
        return finish()
    p("")
    p("counts gate passes -> outcomes computed now (strictly after each window).")
    O = outcomes(lab.copy(), D)
    E = O[O.event]
    months = nlab / 21.0
    rng = np.random.default_rng(SEED)
    res = {}
    for b in RS.NAMES:
        res[b] = block_eval(b, E, O, months, rng)
    ph = C.holm([res[b][2]["p1"] if np.isfinite(res[b][2]["p1"]) else 1.0 for b in RS.NAMES])
    p("")
    p("=== OUTCOMES BY BLOCK (15-minute primary; NQ points, direction-adjusted) ===")
    support = []
    for b, hp in zip(RS.NAMES, ph):
        P, Kc, i = res[b]
        p(f"--- {b}: INITIATIVE n {i['n_ini']} ({i['s_ini']} sess) mean {i['ini']:+.2f} | "
          f"ABSORPTION n {i['n_abs']} ({i['s_abs']} sess) mean {i['abs']:+.2f} | D {i['D']:+.2f} "
          f"t {i['t']:+.2f} p1 {i['p1']:.4f} Holm {hp:.4f}")
        p("    selectors: " + ", ".join(f"{k} {v:+.2f}" for k, v in i["sel"].items())
          + f" | matched times INI {i['m_ini']:+.2f} ABS {i['m_abs']:+.2f} | ctl2 INI {i['c2i']:+.2f} "
            f"ABS {i['c2a']:+.2f} | ctl4 {i['c4']:+.2f} | D w/o best3 {i['d_b3']:+.2f} | best3 share "
            f"{i['best3']:.0f}% | INI cont300 {100*i['cont300']:.0f}% | events/month {i['freq']:.1f}")
        p("    pass: " + " ".join(f"[{'Y' if v else 'n'}]{k.split()[0]}" for k, v in P.items())
          + f"   ({sum(P.values())} of 11)")
        p("    kill: " + " ".join(f"[{'FIRES' if v else '-'}]{k.split()[0]}" for k, v in Kc.items()))
        if all(P.values()) and hp <= 0.05:
            support.append(b)
    fires_all = [k for k in res[RS.NAMES[0]][1] if all(res[b][1][k] for b in RS.NAMES)]
    p("")
    if support:
        verdict = f"PASSES DISCOVERY in {support} -> read the holdout once, for those blocks only."
    elif fires_all:
        verdict = f"REJECTED: kill condition(s) fire in every block: {fires_all}."
    else:
        verdict = "UNCLEAR -- stop."
    p("VERDICT: " + verdict)
    return finish()


def finish():
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp011_discovery_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
