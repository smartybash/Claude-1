#!/usr/bin/env python3
"""Step 4, G1 -- T09 IC harness, T10 VWAP-displacement three exits, T11 order-size
gate, T12 magnitude / range filter.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Data: 61 Databento discovery sessions (tape adapter); cost 2.0 pt round trip
(stricter than the NQ/MNQ standard, applies).

T09 (ic_harness.py): frozen features and horizons (1, 5, 15 min), IC per session,
    t across sessions, circular-shift null. NO trading claim and no registered
    test, so it is DESCRIPTIVE: reported, excluded from BH. Old verdict "IC is
    not edge".
T10 (registered three-exit test, findings_summary a72200b). No script for it was
    ever committed; the rule is reconstructed from the registered text with the
    frozen code it names: vwap_disp from ic_harness.features, standardised with
    forecast.zscore_within (expanding, min_periods 30); pooled quintiles as in
    forecast.report; top quintile -> short, bottom -> long; one position at a
    time, read as the session's FIRST signal held to the exit clock; entry at the
    signal minute's last price. Exits 17:00 / 19:00 / 20:00 on the adapter clock
    (13:00 / 15:00 / 16:00 ET, the same wall-clock times the ATAS UTC stamps
    meant in summer); exit price = last trade before the exit time. A session
    whose first signal comes after an exit time has no trade for that exit.
    Registered bar, per exit: per-session mean > 0 after 2 pt, t >= 2.4, sign as
    in discovery (positive). Primary: three exits, Holm on one-sided p.
T11 (bigorder.py): recombined Databento orders replace the CUM stream
    (bigorder.cum_ok patched; sweep = |last - first| / tick, fills = prints).
    bigorder.collect is copied with one added field (gross points) so points
    can be session-clustered; logic unchanged. Gates: 25+ and 50+ lot net delta
    (>= 1) and net share (>= 2%), sweep delta (>= 1) and share (>= 2%), 3- and
    5-minute bars = 12 cells. Pass: gated trades net > 0 at one-sided p <= 0.05
    (Holm across 12) AND the frozen paired comparison's 95% interval above 0.
T12 (magnitude.py): IC signed vs absolute reported (descriptive). Primary: the
    range filter -- structure breaks (3-min) in the top quartile of the frozen
    range forecast; pass: net > 0, one-sided p <= 0.05, and top quartile beats
    the bottom quartile.
Old verdicts: T10 "cannot be won at 30 sessions; holdout sealed" (the holdout
here is not used); T11 dead; T12 rejected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tape_lib as TL                                              # noqa: E402
C, A = TL.C, TL.A


def pairs_of(D):
    k = sorted(D)
    return [(a, b) for a, b in zip(k, k[1:]) if len(pd.bdate_range(a, b)) == 2]


def t09():
    C.run_frozen("ic_harness", [], "T09_frozen_output.txt")


def t10(D):
    import forecast as FC
    F = FC.build()
    Z = FC.zscore_within(F, ["vwap_disp"])
    q = pd.qcut(Z.vwap_disp.rank(method="first"), 5, labels=False)
    Z = Z.assign(q=q.to_numpy())
    exits = {"exit 17:00 (13:00 ET)": (17, 0), "exit 19:00 (15:00 ET)": (19, 0),
             "exit close 20:00 (16:00 ET)": (20, 0)}
    res = {}
    for lab, (hh, mm) in exits.items():
        rows = []
        for d, g in Z.groupby("day"):
            sig = g[(g.q == 4) | (g.q == 0)]
            if sig.empty:
                continue
            t0 = sig.index[0]
            ex = t0.normalize() + pd.Timedelta(hours=hh, minutes=mm)
            entry_t = t0 + pd.Timedelta(minutes=1)          # end of the signal minute
            if entry_t >= ex:
                continue
            s = D[d]
            px = s.price.to_numpy()
            tm = s.time.to_numpy()
            i_in = int(np.searchsorted(tm, np.datetime64(entry_t), "left")) - 1
            i_out = int(np.searchsorted(tm, np.datetime64(ex), "left")) - 1
            if i_in < 0 or i_out <= i_in:
                continue
            direction = -1.0 if sig.q.iloc[0] == 4 else 1.0
            rows.append((d, [direction * (px[i_out] - px[i_in])]))
        res[lab] = TL.cell_eval(rows, FC.COST_PTS, D)
    return res


def cum_ok_db(day):
    c = A.load_cum_all().get(day)
    if c is None:
        return None
    c = c.copy()
    c["sign"] = np.where(c.aggressor == "B", 1, np.where(c.aggressor == "S", -1, 0))
    c["signed"] = c["sign"] * c.volume
    c["sweep"] = (c.last_price - c.first_price).abs() / 0.25
    return c


def collect_pts(days, pairs, minutes):
    """bigorder.collect, unchanged except for the added `gross` field."""
    import bigorder as BO
    rows = []
    for d0, d1 in pairs:
        prev, s = days[d0], days[d1]
        c = BO.cum_ok(d1)
        if c is None:
            continue
        b = BO.bars(s, minutes)
        if len(b) < 10:
            continue
        lv = BO.levels_of(BO.bars(prev, minutes), BO.BUCKET_PTS)
        cf = BO.per_bar(c, b.timestamp, minutes)
        px_all, tm_all = s.price.to_numpy(), s.time.to_numpy()
        for sig in BO.signals(b):
            i = sig["i"]
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            tgt = BO.next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            sign = 1.0 if up else -1.0
            start = int(np.searchsorted(tm_all, np.datetime64(b.timestamp.iloc[i]), side="right"))
            pnl = None
            for j in range(start, len(px_all)):
                if up:
                    if px_all[j] <= stop:
                        pnl = -risk; break
                    if px_all[j] >= tgt:
                        pnl = abs(tgt - entry); break
                else:
                    if px_all[j] >= stop:
                        pnl = -risk; break
                    if px_all[j] <= tgt:
                        pnl = abs(tgt - entry); break
            if pnl is None:
                pnl = (px_all[-1] - entry) if up else (entry - px_all[-1])
            w = cf.iloc[max(0, i - 1):i + 1]
            tot = float(w["vol"].sum())
            r = dict(day=d1, R=pnl / risk - BO.COST_PTS / risk, gross=pnl)
            for lim in BO.SIZES:
                net = float(w[f"big{lim}"].sum()) * sign
                r[f"big{lim}"] = net
                r[f"big{lim}_sh"] = net / tot if tot > 0 else np.nan
            net = float(w["swp"].sum()) * sign
            r["swp"], r["swp_sh"] = net, (net / tot if tot > 0 else np.nan)
            rows.append(r)
    return pd.DataFrame(rows)


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


def t11(D):
    import bigorder as BO
    BO.cum_ok = cum_ok_db
    C.run_frozen("bigorder", [("bigorder", "cum_ok", cum_ok_db)], "T11_frozen_output.txt")
    P = pairs_of(D)
    res, pr = {}, {}
    for m in (3, 5):
        df = collect_pts(D, P, m)
        for key, cut, lab in (("big25", 1, "25+ lot net delta"), ("big25_sh", 0.02, "25+ lot net >= 2%"),
                              ("big50", 1, "50+ lot net delta"), ("big50_sh", 0.02, "50+ lot net >= 2%"),
                              ("swp", 1, "sweep delta"), ("swp_sh", 0.02, "sweep net >= 2%")):
            on = df.dropna(subset=[key])
            on = on[on[key] >= cut]
            name = f"{m}-min {lab}"
            res[name] = TL.cell_eval([(d, g.gross.to_numpy()) for d, g in on.groupby("day")],
                                     BO.COST_PTS, D)
            pr[name] = paired_ci(df, key, cut)
    return res, pr


def t12(D):
    import magnitude as MG
    from structure_cvd import bars
    from structure_trade import levels_of, next_level, signals
    C.run_frozen("magnitude", [], "T12_frozen_output.txt")
    rows = []
    for d0, d1 in pairs_of(D):
        s = D[d1]
        b = bars(s, 3)
        if len(b) < 25:
            continue
        lv = levels_of(bars(D[d0], 3), 2.0)
        rng = (b.h - b.l).rolling(20, min_periods=8).mean().shift(1).to_numpy()
        px_all, tm_all = s.price.to_numpy(), s.time.to_numpy()
        for sig in signals(b):
            i = sig["i"]
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0 or not np.isfinite(rng[i]) or rng[i] <= 0:
                continue
            tgt = next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            start = int(np.searchsorted(tm_all, np.datetime64(b.timestamp.iloc[i]), "right"))
            pnl = None
            for j in range(start, len(px_all)):
                if up:
                    if px_all[j] <= stop:
                        pnl = -risk; break
                    if px_all[j] >= tgt:
                        pnl = abs(tgt - entry); break
                else:
                    if px_all[j] >= stop:
                        pnl = -risk; break
                    if px_all[j] <= tgt:
                        pnl = abs(tgt - entry); break
            if pnl is None:
                pnl = (px_all[-1] - entry) if up else (entry - px_all[-1])
            rows.append(dict(day=d1, gross=pnl, rng=rng[i]))
    T = pd.DataFrame(rows)
    q = pd.qcut(T.rng, 4, labels=False, duplicates="drop")
    res = {}
    for i, lab in ((3, "top range quartile"), (0, "bottom range quartile")):
        g = T[q == i]
        res[lab] = TL.cell_eval([(d, x.gross.to_numpy()) for d, x in g.groupby("day")], MG.COST_PTS, D)
    res["all breaks"] = TL.cell_eval([(d, x.gross.to_numpy()) for d, x in T.groupby("day")], MG.COST_PTS, D)
    return res


def main():
    D = TL.days()
    print(f"sessions: {len(D)}")
    t09()
    r10 = t10(D)
    keys = list(r10)
    ok_sign = all(r10[k]["mean_session"] > 0 for k in keys)
    TL.report("T10", "VWAP displacement, three registered exits", r10, keys,
              extra_ok=True, extra_lab="; registered bar t >= 2.4 per exit",
              old="cannot be won at 30 sessions; holdout sealed",
              note="reconstructed from the registered text (no committed script)")
    r11, pr = t11(D)
    keys = list(r11)
    raw = [r11[k]["p_one"] if np.isfinite(r11[k]["p_one"]) else 1.0 for k in keys]
    ph = C.holm(raw)
    best = keys[min(range(len(keys)), key=lambda i: (ph[i], raw[i]))]
    note = "; ".join(f"{k}: {d:+.3f}R [{lo:+.3f}, {hi:+.3f}]" for k, (d, lo, hi) in pr.items())
    TL.report("T11", "order-size / sweep gates on structure break", r11, keys,
              extra_ok=bool(pr[best][1] > 0), extra_lab=", paired interval above 0",
              old="dead: month D -0.434R", note=note)
    r12 = t12(D)
    TL.report("T12", "range filter on structure break (magnitude)", r12, ["top range quartile"],
              extra_ok=r12["top range quartile"]["net_pts_mean"] > r12["bottom range quartile"]["net_pts_mean"],
              extra_lab=", top beats bottom quartile", old="rejected")


if __name__ == "__main__":
    main()
