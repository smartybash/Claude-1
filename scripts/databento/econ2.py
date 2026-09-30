#!/usr/bin/env python3
"""reports/econ2_preregistration.md (committed with it, before any run).

H1 late-day momentum: sign(15:29 close / prior RTH close - 1) -> trade 15:30 open -> 15:59 close.
H2 turn-of-month: long 18:00 reopen -> RTH close in the last Globex session of each month and
   the first three of the next (the D3-G/A leg).
Discovery 2010-06-07 -> 2020-12-31 (Holm x2); the holdout 2021-01-01 -> 2026-09-24 is read
once, automatically, only for a discovery pass. Final pass -> paper-tracking + prop simulator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3g                                                          # noqa: E402
import prop_sim as PS                                               # noqa: E402
import step4_common as C                                            # noqa: E402

DISC = (pd.Timestamp("2010-06-07"), pd.Timestamp("2020-12-31"))
HOLD = (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-24"))
SEED, N_SIM = 20260930, 5000
SPEC = d3g.SPEC
OUT = d3g.OUT


# ------------------------------------------------------------------ data ----
def minute_table(sym):
    d = pd.read_parquet(d3g.S4 / f"{sym}_1m.parquet")
    d["day"] = d.timestamp.dt.normalize()
    d["mm"] = (d.timestamp.dt.hour * 60 + d.timestamp.dt.minute - 570).astype(int)
    cnt = d.groupby("day").size()
    d = d[d.day.isin(cnt[cnt >= 300].index)]
    D = pd.DataFrame({"c": d.groupby("day").close.last()})
    at = lambda m, col: d[d.mm == m].set_index("day")[col].reindex(D.index)     # noqa: E731
    D["c0959"], D["c1529"], D["o1530"], D["c1559"] = at(29, "close"), at(359, "close"), at(360, "open"), at(389, "close")
    f = pd.read_parquet(d3g.S4 / f"{sym}_factor.parquet")
    fi = pd.to_datetime(f.day)
    D["fac"] = pd.Series(f.factor.to_numpy(), index=fi).reindex(D.index).to_numpy()
    D["iid"] = pd.Series(f.instrument_id.to_numpy(), index=fi).reindex(D.index).to_numpy()
    D["c_prev"] = D.c.shift(1)
    D["r"] = D.c1529 / D.c_prev - 1
    D["r_gao"] = D.c0959 / D.c_prev - 1
    D["move"] = (D.c1559 - D.o1530) / D.fac                       # real points, 15:30 open -> 15:59 close
    return D


def h1_trades(D, sym, lo, hi, sig="r"):
    s = SPEC[sym]
    E = D[(D.index >= lo) & (D.index <= hi) & D.move.notna() & D[sig].notna() & (D[sig] != 0)]
    T = pd.DataFrame({"session": E.index, "side": np.sign(E[sig]).astype(int).to_numpy(),
                      "absr": E[sig].abs().to_numpy(), "move": E.move.to_numpy()})
    T["gross_pts"] = T.side * T.move
    T["rolls"] = 0
    T["net_usd"] = T.gross_pts * s["mult"] - s["rt"]
    T["net_micro"] = T.gross_pts * s["mmult"] - s["mrt"]
    T["t_in"] = T.session + pd.Timedelta(hours=15, minutes=30)
    T["t_out"] = T.session + pd.Timedelta(hours=15, minutes=59)
    T["px_in"] = (E.o1530 / E.fac).to_numpy()
    T["px_out"] = (E.c1559 / E.fac).to_numpy()
    T["id_in"] = E.iid.to_numpy()
    T["exit_at"] = "close"
    for c in ("roll_old_close", "roll_new_open"):
        T[c] = np.nan
    return T


def h1_null(D, T, sym, lo, hi, rng):
    s = SPEC[sym]
    pool = D[(D.index >= lo) & (D.index <= hi) & D.move.notna() & D.r.notna()].move.to_numpy()
    side = T.side.to_numpy()
    return np.array([(side * pool[rng.integers(0, len(pool), len(T))]).sum() * s["mult"] - s["rt"] * len(T)
                     for _ in range(N_SIM)])


def tom_sessions(G):
    idx = G.index
    ym = idx.to_period("M")
    out = set()
    for per in np.unique(ym):
        m = idx[ym == per]
        out.add(m[-1])
        out.update(m[:3])
    return pd.DatetimeIndex(sorted(out))


def h2_trades(V, tom, lo, hi):
    T = V.loc[V.index.isin(tom) & (V.index >= lo) & (V.index <= hi) & V.net_usd.notna()].copy()
    T["session"] = T.index
    T["side"] = 1
    return T.reset_index(drop=True)


def h2_null(V, T, lo, hi, rng):
    pool = V[(V.index >= lo) & (V.index <= hi) & V.net_usd.notna()].net_usd.to_numpy()
    return np.array([pool[rng.integers(0, len(pool), len(T))].sum() for _ in range(N_SIM)])


def pval(tot, act):
    return float((1 + (tot >= act).sum()) / (N_SIM + 1))


# ---------------------------------------------------------------- report ----
def descr(L, name, T, sym, lo, hi, D=None):
    mid = lo + (hi - lo) / 2
    for a, b, lab in ((lo, mid, f"{lo.date()}..{mid.date()}"), (mid + pd.Timedelta(days=1), hi,
                                                             f"{(mid + pd.Timedelta(days=1)).date()}..{hi.date()}")):
        L.append(d3g.line(f"{name} {lab}", T[(T.session >= a) & (T.session <= b)], sym, a, b))
    yr = T.groupby(T.session.dt.year).net_usd.agg(["size", "sum"])
    L.append(f"  {name} by year (n, net $): " + ", ".join(f"{y} {int(r['size'])} {r['sum']:+,.0f}"
                                                      for y, r in yr.iterrows()))
    if "absr" in T:
        q = pd.qcut(T.absr, 5, labels=False)
        g = T.groupby(q).agg(n=("net_usd", "size"), usd=("net_usd", "mean"), absr=("absr", "median"))
        L.append(f"  {name} by |r| quintile ($/trade, median |r|): " + ", ".join(
            f"Q{k + 1} {r.usd:+,.0f} ({100 * r.absr:.2f}%)" for k, r in g.iterrows()))
        Tg = h1_trades(D, sym, lo, hi, sig="r_gao")
        L.append(f"  {name} alternative signal (Gao et al., prior close -> 09:59): n {len(Tg)}, "
                 f"${Tg.net_usd.mean():+,.1f}/trade, total ${Tg.net_usd.sum():,.0f}")


def run_window(which, lo, hi, names, data, rng):
    """Returns {name: (T, tot, p)} for the requested hypotheses on NQ in [lo, hi]."""
    out = {}
    D, G, V, tom = data["NQ"]
    for n in names:
        if n == "H1":
            T = h1_trades(D, "NQ", lo, hi)
            tot = h1_null(D, T, "NQ", lo, hi, rng)
        else:
            T = h2_trades(V, tom, lo, hi)
            tot = h2_null(V, T, lo, hi, rng)
        out[n] = (T, tot, pval(tot, T.net_usd.sum()))
    return out


def main():
    rng = np.random.default_rng(SEED)
    data = {}
    for sym in ("NQ", "ES"):
        D = minute_table(sym)
        G, R = d3g.globex(sym), d3g.load_rolls(sym)
        V = d3g.leg(G, R, sym, "A")
        data[sym] = (D, G, V, tom_sessions(G))
    labels = {"H1": "H1 late-day momentum", "H2": "H2 turn-of-month"}
    L = ["TWO ECONOMIC SLEEVES -- NQ; discovery 2010-06-07 -> 2020-12-31, holdout 2021-01-01 -> 2026-09-24",
         "Registered reports/econ2_preregistration.md. Null: 5,000 exposure-matched lists. Costs NQ $14.50 RT.", "",
         "== DISCOVERY (Holm across H1, H2) =="]
    disc = run_window("disc", *DISC, ["H1", "H2"], data, rng)
    adj = dict(zip(disc, C.holm([disc[n][2] for n in disc])))
    dpass = {}
    for n, (T, tot, p) in disc.items():
        ok = T.net_usd.sum() > 0 and adj[n] <= 0.05
        dpass[n] = ok
        L.append(d3g.line(labels[n], T, "NQ", *DISC))
        L.append(f"    null median ${np.median(tot):,.0f}, 95th ${np.percentile(tot, 95):,.0f}; p {p:.4f}, "
                 f"Holm {adj[n]:.4f} -> {'DISCOVERY PASS' if ok else 'FAIL (closed; holdout not read)'}")
    L.append("")
    to_hold = [n for n in disc if dpass[n]]
    final = {n: False for n in disc}
    hold = {}
    if to_hold:
        L.append(f"== HOLDOUT (read once for {', '.join(to_hold)}"
                 + (", Holm across both)" if len(to_hold) == 2 else ")") + " ==")
        hold = run_window("hold", *HOLD, to_hold, data, rng)
        hadj = dict(zip(hold, C.holm([hold[n][2] for n in hold]))) if len(hold) == 2 else \
            {n: hold[n][2] for n in hold}
        for n, (T, tot, p) in hold.items():
            ok = T.net_usd.sum() > 0 and hadj[n] <= 0.05
            final[n] = ok
            L.append(d3g.line(labels[n], T, "NQ", *HOLD))
            L.append(f"    null median ${np.median(tot):,.0f}, 95th ${np.percentile(tot, 95):,.0f}; p {p:.4f}"
                     + (f", Holm {hadj[n]:.4f}" if len(hold) == 2 else "")
                     + f" -> {'HOLDOUT PASS: FINAL PASS' if ok else 'FAIL (closed)'}")
        L.append("")
    else:
        L += ["== HOLDOUT: not read (nothing passed discovery) ==", ""]
    L.append("VERDICTS: " + "; ".join(f"{labels[n]}: {'PASS -> paper-tracking' if final[n] else 'CLOSED'}"
                                      for n in disc))
    L += ["", "DESCRIPTIVE (cannot change a verdict)"]
    D, G, V, tom = data["NQ"]
    for n in disc:
        descr(L, f"{n} disc", disc[n][0], "NQ", *DISC, D=D)
        if n in hold:
            descr(L, f"{n} hold", hold[n][0], "NQ", *HOLD, D=D)
    for n in disc:                                                  # ES replication, same windows read
        De, Ge, Ve, tome = data["ES"]
        for lo, hi, lab in ((*DISC, "disc"),) + (((*HOLD, "hold"),) if n in hold else ()):
            Te = h1_trades(De, "ES", lo, hi) if n == "H1" else h2_trades(Ve, tome, lo, hi)
            L.append(d3g.line(f"ES {n} {lab}", Te, "ES", lo, hi))
    txt = "\n".join(L)
    print(txt)
    (OUT / "econ2_output.txt").write_text(txt + "\n")

    passed = [n for n in final if final[n]]
    if passed:
        S = ["PROP-EVALUATION SIMULATOR, econ2 final passes -- full window, seen data (descriptive)",
             "Accounts and mechanics as reports/d3g_preregistration.md section 4.", ""]
        sess = G.index[(G.index >= DISC[0]) & (G.index <= HOLD[1])]
        for n in passed:
            T = h1_trades(D, "NQ", DISC[0], HOLD[1]) if n == "H1" else h2_trades(V, tom, DISC[0], HOLD[1])
            T.to_csv(d3g.FROZEN / f"econ2_{n}_trades.csv", index=False)
            R = PS.simulate(PS.build_trades(T, "NQ"), sess, SPEC["NQ"]["mmult"])
            for c in ("pass_30d", "pass_90d", "pass_365d", "fail_365d"):
                R[c] = (100 * R[c]).map("{:.1f}%".format)
            S += [f"== {labels[n]}: {len(T)} trades, MNQ sizes 1-10 ==", R.to_string(index=False), ""]
        st = "\n".join(S)
        print(st)
        (OUT / "econ2_prop_sim_output.txt").write_text(st + "\n")
    return final


if __name__ == "__main__":
    main()
