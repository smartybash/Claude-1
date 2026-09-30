#!/usr/bin/env python3
"""LDM: price-triggered late-day momentum (reports/ldm_preregistration.md).

    python3 scripts/databento/ldm.py --selftest   # engine checks on synthetic bars only
    python3 scripts/databento/ldm.py              # fit grid on 2010-06-07 -> 2020-12-31 (refuses later data)
    python3 scripts/databento/ldm.py --forward    # paper-track the frozen rule from 2026-10-01

Entry: fresh cross of prior close x (1 +/- X) inside [W, 15:50], stop order fill (level or gap
open). Stop k x ADR20 (points at the day's price). Target 1R / 2R / none -> 15:59 close.
Stop before target within a bar; entry bar checks the stop only. NQ $14.50, ES $29.50 per RT.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3g                                                          # noqa: E402

DISC0, DISC1 = pd.Timestamp("2010-06-07"), pd.Timestamp("2020-12-31")
MID = pd.Timestamp("2015-09-19")
FWD0 = pd.Timestamp("2026-10-01")
XS = (0.005, 0.0075, 0.01, 0.015)
WS = {"13:00": 210, "14:30": 300}
KS = (0.15, 0.25, 0.40)
TGS = ("1R", "2R", "close")
LAST_ENTRY, NBAR = 380, 390
SPEC = d3g.SPEC
OUT = d3g.OUT
FROZEN = None            # set from reports/ldm_frozen.md after the fit: dict(X=, W=, k=, tgt=)


# --------------------------------------------------------------- engine ----
def triggers(O, H, L, C, pc, X, w):
    """First fresh cross per day in bars [w, LAST_ENTRY]. Returns side (0 = none), bar, fill."""
    n = O.shape[0]
    Cf = pd.DataFrame(C).ffill(axis=1).to_numpy()
    prev = np.full_like(Cf, np.nan)
    prev[:, 1:] = Cf[:, :-1]
    up, dn = (pc * (1 + X))[:, None], (pc * (1 - X))[:, None]
    cols = np.arange(NBAR)
    win = (cols >= w) & (cols <= LAST_ENTRY)
    lh = win & (prev < up) & (H >= up)
    sh = win & (prev > dn) & (L <= dn)
    jl = np.where(lh.any(1), lh.argmax(1), NBAR)
    js = np.where(sh.any(1), sh.argmax(1), NBAR)
    side = np.where(jl < js, 1, np.where(js < jl, -1, 0))
    j = np.minimum(jl, js)
    fill = np.full(n, np.nan)
    r = np.arange(n)
    ok = side != 0
    jj = np.where(ok, j, 0)
    fill = np.where(side > 0, np.maximum(up[:, 0], O[r, jj]), np.where(side < 0, np.minimum(dn[:, 0], O[r, jj]), np.nan))
    return side, np.where(ok, j, -1), fill


def exit_scan(o, h, l, c, j, side, px, stop, tgt):
    """o/h/l/c: one day's bars. Returns (price, bar, reason)."""
    if (side > 0 and l[j] <= stop) or (side < 0 and h[j] >= stop):
        return stop, j, "stop"
    oo, hh, ll = o[j + 1:], h[j + 1:], l[j + 1:]
    s_hit = (ll <= stop) if side > 0 else (hh >= stop)
    t_hit = np.zeros(len(oo), bool) if tgt is None else ((hh >= tgt) if side > 0 else (ll <= tgt))
    s = int(s_hit.argmax()) if s_hit.any() else None
    t = int(t_hit.argmax()) if t_hit.any() else None
    if s is not None and (t is None or s <= t):
        g = oo[s]
        return (g if (side > 0 and g <= stop) or (side < 0 and g >= stop) else stop), j + 1 + s, "stop"
    if t is not None:
        g = oo[t]
        return (g if (side > 0 and g >= tgt) or (side < 0 and g <= tgt) else tgt), j + 1 + t, "target"
    last = int(np.flatnonzero(~np.isnan(c))[-1])
    return c[last], last, "close"


def run_config(A, X, w, k, tg, trig=None):
    """Trades for one configuration over the loaded days A."""
    side, j, fill = trig if trig is not None else triggers(A["O"], A["H"], A["L"], A["C"], A["pc"], X, w)
    rows = []
    m = {"1R": 1.0, "2R": 2.0, "close": None}[tg]
    for d in np.flatnonzero((side != 0) & np.isfinite(A["adrp"])):
        sd = k * A["adrp"][d] * fill[d]
        s = side[d]
        stop = fill[d] - s * sd
        tgt = None if m is None else fill[d] + s * m * sd
        px, xb, why = exit_scan(A["O"][d], A["H"][d], A["L"][d], A["C"][d], j[d], s, fill[d], stop, tgt)
        rows.append((d, s, j[d], fill[d], xb, px, why, sd / fill[d]))
    T = pd.DataFrame(rows, columns=["d", "side", "j", "px", "xb", "exit", "why", "sd_pct"])
    T["session"] = A["days"][T.d.to_numpy()] if len(T) else pd.Series(dtype="datetime64[ns]")
    fac = A["fac"][T.d.to_numpy()] if len(T) else np.array([])
    s = SPEC[A["sym"]]
    T["gross_pts"] = T.side * (T.exit - T.px) / fac
    T["stop_pts"] = T.sd_pct * T.px / fac
    T["net_usd"] = T.gross_pts * s["mult"] - s["rt"]
    T["net_micro"] = T.gross_pts * s["mmult"] - s["mrt"]
    return T


# ----------------------------------------------------------------- data ----
def load(sym, until):
    d = pd.read_parquet(d3g.S4 / f"{sym}_1m.parquet")
    d = d[d.timestamp < until + pd.Timedelta(days=1)]
    d["day"] = d.timestamp.dt.normalize()
    d["mm"] = (d.timestamp.dt.hour * 60 + d.timestamp.dt.minute - 570).astype(int)
    cnt = d.groupby("day").size()
    d = d[d.day.isin(cnt[cnt >= 300].index) & d.mm.between(0, NBAR - 1)]
    days = pd.DatetimeIndex(sorted(d.day.unique()))
    di = days.get_indexer(d.day)
    M = {}
    for col, key in (("open", "O"), ("high", "H"), ("low", "L"), ("close", "C")):
        a = np.full((len(days), NBAR), np.nan)
        a[di, d.mm.to_numpy()] = d[col].to_numpy()
        M[key] = a
    g = d.groupby("day")
    dc, dh, dl = g.close.last().to_numpy(), g.high.max().to_numpy(), g.low.min().to_numpy()
    f = pd.read_parquet(d3g.S4 / f"{sym}_factor.parquet")
    fi = pd.to_datetime(f.day)
    A = dict(M, sym=sym, days=days,
             pc=np.concatenate([[np.nan], dc[:-1]]),
             adrp=pd.Series((dh - dl) / dc).rolling(20).mean().shift(1).to_numpy(),
             fac=pd.Series(f.factor.to_numpy(), index=fi).reindex(days).to_numpy(),
             iid=pd.Series(f.instrument_id.to_numpy(), index=fi).reindex(days).to_numpy())
    assert days.max() <= until
    return A


# ------------------------------------------------------------------ fit ----
def metrics(T, lo, hi):
    yrs = (hi - lo).days / 365.25
    h1, h2 = T[T.session <= MID].net_usd.sum(), T[T.session > MID].net_usd.sum()
    yr = T.groupby(T.session.dt.year).net_usd.sum()
    return dict(n=len(T), per_yr=len(T) / yrs, usd_trade=T.net_usd.mean() if len(T) else np.nan,
                total=T.net_usd.sum(), half1_yr=h1 / ((MID - lo).days / 365.25),
                half2_yr=h2 / ((hi - MID).days / 365.25),
                ex_best=T.net_usd.sum() - (yr.max() if len(yr) else 0.0))


def fit():
    An, Ae = load("NQ", DISC1), load("ES", DISC1)
    rows, keep = [], {}
    for X in XS:
        for wn, w in WS.items():
            tn = triggers(An["O"], An["H"], An["L"], An["C"], An["pc"], X, w)
            te = triggers(Ae["O"], Ae["H"], Ae["L"], Ae["C"], Ae["pc"], X, w)
            for k in KS:
                for tg in TGS:
                    T = run_config(An, X, w, k, tg, tn)
                    T = T[(T.session >= DISC0) & (T.session <= DISC1)]
                    Te = run_config(Ae, X, w, k, tg, te)
                    Te = Te[(Te.session >= DISC0) & (Te.session <= DISC1)]
                    assert T.session.max() <= DISC1 and Te.session.max() <= DISC1
                    r = dict(X=X, W=wn, k=k, tgt=tg, **metrics(T, DISC0, DISC1), es_total=Te.net_usd.sum())
                    rows.append(r)
                    keep[(X, wn, k, tg)] = T
    R = pd.DataFrame(rows)
    R["min_half_yr"] = R[["half1_yr", "half2_yr"]].min(axis=1)
    R["eligible"] = (R.per_yr >= 25) & (R.half1_yr > 0) & (R.half2_yr > 0) & (R.ex_best > 0) & (R.es_total > 0)
    idx = {"X": list(XS), "W": list(WS), "k": list(KS), "tgt": list(TGS)}
    pos = {c: R[c].map({v: i for i, v in enumerate(idx[c])}) for c in idx}
    score = []
    for i in range(len(R)):
        nb = np.zeros(len(R), bool)
        for c in idx:
            others = [o for o in idx if o != c]
            same = np.all([pos[o] == pos[o][i] for o in others], axis=0)
            nb |= same & ((pos[c] - pos[c][i]).abs() == 1)
        nb[i] = True
        score.append(float(np.median(R.min_half_yr[nb])))
    R["plateau"] = score
    return R, keep, An


def null_disc(T, A, rng, n_sim=2000):
    """Exposure-matched random entries (descriptive on discovery): same side, entry bar,
    stop/target distances (% of price) and cost, on a uniformly random discovery day."""
    s = SPEC[A["sym"]]
    pool = np.flatnonzero((A["days"] >= DISC0) & (A["days"] <= DISC1) & np.isfinite(A["adrp"]))
    tgm = T.attrs["tgt_mult"]
    tot = np.empty(n_sim)
    for k in range(n_sim):
        dd = pool[rng.integers(0, len(pool), len(T))]
        acc = 0.0
        for d, r in zip(dd, T.itertuples()):
            o, h, l, c = A["O"][d], A["H"][d], A["L"][d], A["C"][d]
            px = o[r.j]
            if not np.isfinite(px):
                px = c[r.j - 1] if r.j > 0 and np.isfinite(c[r.j - 1]) else np.nanmean(c)
            sd = r.sd_pct * px
            stop = px - r.side * sd
            tgt = None if tgm is None else px + r.side * tgm * sd
            ex, _, _ = exit_scan(o, h, l, c, r.j, r.side, px, stop, tgt)
            acc += (r.side * (ex - px) / A["fac"][d]) * s["mult"] - s["rt"]
        tot[k] = acc
    return float((1 + (tot >= T.net_usd.sum()).sum()) / (n_sim + 1))


def main_fit():
    R, keep, An = fit()
    R.to_csv(OUT / "ldm_grid.csv", index=False, float_format="%.4f")
    E = R[R.eligible].sort_values(["plateau", "per_yr"], ascending=False)
    L = ["LDM FIT -- NQ/ES 2010-06-07 -> 2020-12-31 ONLY (2021-2026 unused); price-triggered entry",
         "Registered reports/ldm_preregistration.md. Costs NQ $14.50 / ES $29.50 per round trip.", "",
         f"grid {len(R)}: net positive {int((R.total > 0).sum())}; eligible {int(R.eligible.sum())}", "",
         f"  {'X':>6} {'W':>6} {'k':>5} {'tgt':>5} {'n':>5} {'/yr':>5} {'$/tr':>7} {'total':>9} {'h1/yr':>8} "
         f"{'h2/yr':>8} {'exbest':>8} {'ES':>8} {'plat':>7} elig"]
    for r in R.itertuples():
        L.append(f"  {100 * r.X:>5.2f}% {r.W:>6} {r.k:>5.2f} {r.tgt:>5} {r.n:>5} {r.per_yr:>5.0f} {r.usd_trade:>+7.1f} "
                 f"{r.total:>+9,.0f} {r.half1_yr:>+8,.0f} {r.half2_yr:>+8,.0f} {r.ex_best:>+8,.0f} {r.es_total:>+8,.0f} "
                 f"{r.plateau:>+7,.0f} {'yes' if r.eligible else ''}")
    L.append("")
    frozen = None
    if E.empty:
        L.append("SELECTION: no eligible configuration -> nothing frozen; LDM CLOSED; nothing tracked.")
    else:
        b = E.iloc[0]
        frozen = dict(X=float(b.X), W=b.W, k=float(b.k), tgt=b.tgt)
        T = keep[(b.X, b.W, b.k, b.tgt)].copy()
        T.attrs["tgt_mult"] = {"1R": 1.0, "2R": 2.0, "close": None}[b.tgt]
        p = null_disc(T, An, np.random.default_rng(20260930))
        L += [f"SELECTION (frozen): X {100 * b.X:.2f}%, window from {b.W}, stop {b.k:.2f} x ADR20, target {b.tgt}",
              f"  n {b.n} ({b.per_yr:.0f}/yr), ${b.usd_trade:+.1f}/trade, total ${b.total:+,.0f}; halves "
              f"${b.half1_yr:+,.0f}/yr, ${b.half2_yr:+,.0f}/yr; without best year ${b.ex_best:+,.0f}; ES ${b.es_total:+,.0f}; "
              f"plateau ${b.plateau:+,.0f}/yr",
              f"  discovery p vs exposure-matched random entries (2,000 lists): {p:.4f} -- INFLATED by selection over "
              f"{len(R)}; not evidence", "", "DESCRIPTIVE (chosen configuration, discovery)"]
        y = T.groupby(T.session.dt.year).net_usd.agg(["size", "sum"])
        L.append("  by year (n, net $): " + ", ".join(f"{k} {int(r['size'])} {r['sum']:+,.0f}" for k, r in y.iterrows()))
        L.append(f"  longs {int((T.side > 0).sum())} ${T[T.side > 0].net_usd.mean():+.1f}/trade; shorts "
                 f"{int((T.side < 0).sum())} ${T[T.side < 0].net_usd.mean():+.1f}/trade")
        L.append("  exits: " + ", ".join(f"{k} {v}" for k, v in T.why.value_counts().items()))
        s20 = T[T.session.dt.year == 2020]
        L.append(f"  stop in NQ points: median {T.stop_pts.median():.1f} over 2010-2020, {s20.stop_pts.median():.1f} in 2020")
        L.append(d3g.line("LDM discovery", T, "NQ", DISC0, DISC1))
        T.to_csv(d3g.FROZEN / "ldm_disc_trades.csv", index=False)
    txt = "\n".join(L)
    print(txt)
    (OUT / "ldm_fit_output.txt").write_text(txt + "\n")
    return frozen


def prop_disc():
    """Prop simulator on the frozen rule's discovery trades (descriptive, seen)."""
    import prop_sim as PS
    A = load("NQ", DISC1)
    T = pd.read_csv(d3g.FROZEN / "ldm_disc_trades.csv", parse_dates=["session"])
    F = T.copy()
    F["t_in"] = F.session + pd.to_timedelta(570 + F.j, unit="min")
    F["t_out"] = F.session + pd.to_timedelta(570 + F.xb, unit="min")
    fac = A["fac"][F.d.to_numpy()]
    F["px_in"], F["px_out"] = F.px / fac, F.exit / fac
    F["id_in"] = A["iid"][F.d.to_numpy()]
    F["rolls"], F["exit_at"] = 0, "close"
    F["roll_old_close"] = F["roll_new_open"] = np.nan
    G = d3g.globex("NQ")
    sess = G.index[(G.index >= DISC0) & (G.index <= DISC1)]
    R = PS.simulate(PS.build_trades(F, "NQ"), sess, SPEC["NQ"]["mmult"])
    for c in ("pass_30d", "pass_90d", "pass_365d", "fail_365d"):
        R[c] = (100 * R[c]).map("{:.1f}%".format)
    txt = "\n".join(["PROP SIMULATOR, LDM frozen rule on DISCOVERY trades 2010-06 -> 2020-12 (seen; descriptive)",
                     f"== LDM: {len(F)} trades, MNQ sizes 1-10 ==", R.to_string(index=False)])
    print(txt)
    (OUT / "ldm_prop_sim_output.txt").write_text(txt + "\n")


# -------------------------------------------------------------- forward ----
def forward(since=FWD0, until=None, out=OUT):
    if FROZEN is None:
        raise SystemExit("no frozen LDM rule")
    A = load("NQ", until or pd.Timestamp.max.normalize())
    if A["days"].max() < since:
        print(f"No forward sessions yet: bars end {A['days'].max().date()}; LDM paper-tracking starts {since.date()}.")
        return None
    T = run_config(A, FROZEN["X"], WS[FROZEN["W"]], FROZEN["k"], FROZEN["tgt"])
    T = T[T.session >= since]
    hm = lambda b: (pd.Timestamp("2000-01-01 09:30") + pd.Timedelta(minutes=int(b))).strftime("%H:%M")   # noqa: E731
    Lg = pd.DataFrame({"session": T.session.dt.date, "side": T.side, "entry_time": T.j.map(hm),
                       "exit_time": T.xb.map(hm), "exit": T.why, "stop_pts": T.stop_pts.round(2),
                       "gross_pts": T.gross_pts.round(2), "net_usd": T.net_usd.round(2),
                       "net_micro": T.net_micro.round(2)})
    Lg.to_csv(out / "ldm_paper_ledger.csv", index=False)
    M = ["# LDM paper-tracking status", "",
         f"Frozen rule: {FROZEN}. Signals from {since.date()}; bars to {A['days'].max().date()}. "
         "First review on or after 2027-10-01.", "",
         f"- trades {len(T)} (long {int((T.side > 0).sum())}, short {int((T.side < 0).sum())}); "
         f"net ${T.net_usd.sum():+,.0f} per NQ, ${T.net_micro.sum():+,.2f} per MNQ"]
    txt = "\n".join(M)
    (out / "ldm_paper_status.md").write_text(txt + "\n")
    print(txt)
    return T


# ------------------------------------------------------------- selftest ----
def selftest():
    def day(path_c, lo_off=None, hi_off=None, opens=None):
        """One day of 390 bars from a close path (flat after it ends)."""
        c = np.full(NBAR, np.nan)
        c[:len(path_c)] = path_c
        c = pd.Series(c).ffill().to_numpy()
        o = np.concatenate([[c[0]], c[:-1]]) if opens is None else opens
        h = np.maximum(o, c) + (0 if hi_off is None else hi_off)
        l = np.minimum(o, c) - (0 if lo_off is None else lo_off)
        return o, h, l, c

    def run(o, h, l, c, pc, X=0.01, w=210, k=0.25, tg="close", adrp=0.02):
        A = dict(O=o[None], H=h[None], L=l[None], C=c[None], pc=np.array([pc]), adrp=np.array([adrp]),
                 days=pd.DatetimeIndex(["2020-01-02"]), fac=np.array([1.0]), sym="NQ")
        T = run_config(A, X, w, k, tg)
        return None if T.empty else T.iloc[0]

    def chk(name, got, want):
        print(f"[{'ok' if got == want else 'FAIL'}] {name}: {got}")
        if not got == want:
            raise SystemExit(1)

    base = np.full(NBAR, 100.0)
    # 1. fresh cross at bar 250 from 100.5 to 101.2 (level 101) -> long at 101, hold to close 101.5
    p = base.copy(); p[:250] = 100.5; p[250:] = 101.2; p[300:] = 101.5
    o = np.concatenate([[p[0]], p[:-1]]); h, l = np.maximum(o, p), np.minimum(o, p)
    t = run(o, h, l, p, 100.0)
    chk("fresh cross long: side, bar, fill, exit", (t.side, int(t.j), round(t.px, 4), t.why, round(t.exit, 4)),
        (1, 250, 101.0, "close", 101.5))
    # 2. gap through: bar 250 opens at 101.4 -> fill at the open
    o2 = o.copy(); o2[250] = 101.4; h2 = np.maximum(o2, p); l2 = np.minimum(o2, p)
    t = run(o2, h2, l2, p, 100.0)
    chk("gap-through fill at open", round(t.px, 4), 101.4)
    # 3. already above the level when the window opens (bar 210): no trade without a re-cross
    p3 = base.copy(); p3[:] = 101.5
    o3 = p3.copy(); h3, l3 = p3 + 0.05, p3 - 0.05
    chk("already beyond at window open -> no trade", run(o3, h3, l3, p3, 100.0), None)
    # 3b. ... then dips inside at bar 260 and re-crosses at bar 261 -> long at 101
    p3b = p3.copy(); p3b[260] = 100.8
    o3b = np.concatenate([[p3b[0]], p3b[:-1]]); h3b, l3b = np.maximum(o3b, p3b), np.minimum(o3b, p3b)
    t = run(o3b, h3b, l3b, p3b, 100.0)
    chk("re-cross after dipping inside", (t.side, int(t.j)), (1, 261))
    # 4. stop before target in the same bar: long 101, stop 101 - 0.25*0.02*101 = 100.495; bar 270 spans both
    p4 = p.copy(); p4[250:] = 101.1
    o4 = np.concatenate([[p4[0]], p4[:-1]]); h4, l4 = np.maximum(o4, p4), np.minimum(o4, p4)
    h4[270], l4[270] = 102.5, 100.3
    t = run(o4, h4, l4, p4, 100.0, tg="1R")
    chk("stop checked before target", (t.why, round(t.exit, 3)), ("stop", 100.495))
    # 5. stop touched on the entry bar
    l5 = l.copy(); l5[250] = 100.4
    t = run(o, h, l5, p, 100.0)
    chk("stop on the entry bar", (t.why, int(t.xb)), ("stop", 250))
    # 6. 2R target: long 101, R 0.505 -> target 102.01, reached at bar 320
    p6 = p.copy(); p6[250:320] = 101.2; p6[320:] = 102.3
    o6 = np.concatenate([[p6[0]], p6[:-1]]); h6, l6 = np.maximum(o6, p6), np.minimum(o6, p6)
    o6[320] = 101.9; h6[320] = 102.3
    t = run(o6, h6, l6, p6, 100.0, tg="2R")
    chk("2R target", (t.why, round(t.exit, 3), int(t.xb)), ("target", 102.01, 320))
    # 7. short mirror: crosses 99 at bar 250, closes 98.5
    q = base.copy(); q[:250] = 99.5; q[250:] = 98.8; q[300:] = 98.5
    oq = np.concatenate([[q[0]], q[:-1]]); oq[250] = 99.2          # cross bar opens inside the stop
    hq, lq = np.maximum(oq, q), np.minimum(oq, q)
    t = run(oq, hq, lq, q, 100.0)
    chk("short mirror", (t.side, round(t.px, 4), round(t.exit, 4)), (-1, 99.0, 98.5))
    # 8. cross after 15:50 (bar 385) -> no trade
    p8 = base.copy(); p8[:385] = 100.5; p8[385:] = 101.3
    o8 = np.concatenate([[p8[0]], p8[:-1]]); h8, l8 = np.maximum(o8, p8), np.minimum(o8, p8)
    chk("no trigger after 15:50", run(o8, h8, l8, p8, 100.0), None)
    # 9. cross before the window (bar 100) and stays above -> no trade
    p9 = base.copy(); p9[:100] = 100.5; p9[100:] = 101.3
    o9 = np.concatenate([[p9[0]], p9[:-1]]); h9, l9 = np.maximum(o9, p9), np.minimum(o9, p9)
    chk("cross before the window, stays beyond -> no trade", run(o9, h9, l9, p9, 100.0), None)
    print("selftest passed")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--forward" in sys.argv:
        forward()
    elif "--prop" in sys.argv:
        prop_disc()
    else:
        main_fit()
