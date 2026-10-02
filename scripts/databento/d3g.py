#!/usr/bin/env python3
"""Tests 1-2 of reports/d3g_preregistration.md (committed with it, before any run).

NQ family : D3-G/A (18:00 reopen -> next RTH close), D3-G/B (-> next RTH open)
ES family : ES-D3 (RTH close -> next RTH close, as registered for NQ), ES-G/A
Exposure-matched random-entry null, 5,000 lists, Holm within each family.
Seen data 2010-06-07 -> 2026-09-24.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step4_common as C                                            # noqa: E402

ROOT = C.ROOT
S4, B1, ROLLS = ROOT / "data/clean/step4", ROOT / "data/clean/bars_1m", ROOT / "data/clean/rolls"
OUT = ROOT / "reports"
FROZEN = C.OUT / "frozen"
A0, A1 = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-09-24")
HALF = pd.Timestamp("2018-07-01")
SEED, N_SIM = 20260929, 5000
SPEC = {"NQ": dict(mult=20.0, rt=14.50, mmult=2.0, mrt=2.24, micro="MNQ"),
        "ES": dict(mult=50.0, rt=29.50, mmult=5.0, mrt=3.74, micro="MES")}


# ------------------------------------------------------------------ data ----
def load_rth(sym):
    """RTH daily series exactly as daily3.load builds it (>= 300 bars, 15:58 close, factor)."""
    d = pd.read_parquet(S4 / f"{sym}_1m.parquet")
    d["day"] = d.timestamp.dt.normalize()
    d["mm"] = (d.timestamp.dt.hour * 60 + d.timestamp.dt.minute - 570).astype(int)
    cnt = d.groupby("day").size()
    d = d[d.day.isin(cnt[cnt >= 300].index)]
    g = d.groupby("day")
    D = pd.DataFrame({"o": g.open.first(), "c": g.close.last()})
    D["c58"] = d[d.mm == 388].set_index("day").close.reindex(D.index)
    f = pd.read_parquet(S4 / f"{sym}_factor.parquet")
    D["fac"] = pd.Series(f.factor.to_numpy(), index=pd.to_datetime(f.day)).reindex(D.index).to_numpy()
    return D


def signals(D):
    c, c58 = D.c.to_numpy(), D.c58.to_numpy()
    return [i for i in range(3, len(D)) if c58[i] < c[i - 1] and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3]]


def globex(sym):
    """One row per Globex session with RTH bars: first bar (entry), first RTH bar, last RTH bar."""
    fs = sorted(B1.glob(f"{sym}_*.parquet"))
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "session", "instrument_id", "open", "close", "rth"])
                   for f in fs], ignore_index=True).sort_values("ts_et")
    g = b.groupby("session")
    G = pd.DataFrame({"t_in": g.ts_et.first(), "px_in": g.open.first(), "id_in": g.instrument_id.first()})
    r = b[b.rth].groupby("session")
    G = G.join(pd.DataFrame({"t_rth0": r.ts_et.first(), "px_rth0": r.open.first(), "id_rth0": r.instrument_id.first(),
                             "t_rth1": r.ts_et.last(), "px_rth1": r.close.last(), "id_rth1": r.instrument_id.last()}),
               how="inner")
    G.index = pd.DatetimeIndex(G.index)
    return G[G.t_in < G.t_rth0]


def leg(G, R, sym, which):
    """Net $ (1 contract) of a long from each session's first bar to its RTH open ('B') or
    RTH close ('A'); rolled at the roll prices with one extra round trip; NaN across a
    stale roll."""
    k = "rth1" if which == "A" else "rth0"
    t_out, px_out, id_out = G[f"t_{k}"], G[f"px_{k}"], G[f"id_{k}"]
    gross = (px_out - G.px_in).to_numpy().astype(float)
    rolls = np.zeros(len(G), int)
    info = {}
    rr = {(int(x.old_id), int(x.new_id)): x for x in R.itertuples()}
    for j in np.flatnonzero((G.id_in != id_out).to_numpy()):
        x = rr.get((int(G.id_in.iloc[j]), int(id_out.iloc[j])))
        ok = x is not None and x.ratio_valid and G.t_in.iloc[j] < x.t_new <= t_out.iloc[j]
        if not ok:
            gross[j] = np.nan
            continue
        gross[j] = (x.old_close - G.px_in.iloc[j]) + (px_out.iloc[j] - x.new_open)
        rolls[j] = 1
        info[G.index[j]] = (x.old_close, x.new_open, x.t_new)
    s = SPEC[sym]
    V = pd.DataFrame({"gross_pts": gross, "rolls": rolls}, index=G.index)
    V["net_usd"] = V.gross_pts * s["mult"] - s["rt"] * (1 + V.rolls)
    V["net_micro"] = V.gross_pts * s["mmult"] - s["mrt"] * (1 + V.rolls)
    V["t_in"], V["t_out"], V["px_in"], V["px_out"] = G.t_in, t_out, G.px_in, px_out
    V["id_in"], V["id_out"] = G.id_in, id_out
    V["exit_at"] = "close" if which == "A" else "open"
    V["roll_old_close"] = [info.get(d, (np.nan,) * 3)[0] for d in G.index]
    V["roll_new_open"] = [info.get(d, (np.nan,) * 3)[1] for d in G.index]
    V["roll_t"] = [info.get(d, (np.nan,) * 3)[2] for d in G.index]
    return V


def load_rolls(sym):
    R = pd.read_csv(ROLLS / f"{sym}_rolls.csv", parse_dates=["ts_new_first"])
    R["t_new"] = R.ts_new_first.dt.tz_convert("America/New_York").dt.tz_localize(None)
    return R


# ---------------------------------------------------------------- trades ----
def g_trades(D, G, V, sig, lo=A0, hi=A1):
    days = D.index
    rows = []
    for i in sig:
        j = G.index.searchsorted(days[i], side="right")
        if j >= len(G):
            continue
        s = G.index[j]
        if days[i] < lo or s > hi:
            continue
        rows.append(dict(signal_day=days[i], session=s))
    T = pd.DataFrame(rows, columns=["signal_day", "session"])         # columns kept when empty
    T = T.join(V, on="session")
    dropped = int(T.gross_pts.isna().sum())
    return T[T.gross_pts.notna()].reset_index(drop=True), dropped


def d3_trades(D, sym, sig, lo=A0, hi=A1):
    """D3 as registered (daily3.trades_oversold + pnl_frame), on `sym`."""
    s = SPEC[sym]
    c, fac, days = D.c.to_numpy(), D.fac.to_numpy(), D.index
    rows = [i for i in sig if i + 1 < len(D) and lo <= days[i] and days[i + 1] <= hi]
    T = pd.DataFrame({"i": np.asarray(rows, dtype=int)})                # int even when empty
    T["signal_day"] = days[T.i]
    T["session"] = days[T.i + 1]
    T["gross_pts"] = (c[T.i + 1] - c[T.i]) / fac[T.i]
    T["rolls"] = (fac[T.i] != fac[T.i + 1]).astype(int)
    rt_pts = s["rt"] / s["mult"]
    T["net_usd"] = (T.gross_pts - rt_pts * (1 + T.rolls)) * s["mult"]
    T["net_micro"] = T.gross_pts * s["mmult"] - s["mrt"] * (1 + T.rolls)
    return T


# ----------------------------------------------------------------- nulls ----
def null_g(T, V, rng):
    pool = V[(V.index >= A0) & (V.index <= A1) & V.net_usd.notna()].net_usd.to_numpy()
    tot = np.array([pool[rng.integers(0, len(pool), len(T))].sum() for _ in range(N_SIM)])
    return tot, float(pool.mean())


def null_d3(T, D, sym, rng):
    """P7 null: random start day, hold one RTH day, close -> close, each random trade
    keeping one actual trade's cost (rolls included), as in daily3.null_p."""
    s = SPEC[sym]
    c, fac, days = D.c.to_numpy(), D.fac.to_numpy(), D.index
    first = int(np.searchsorted(days, A0))
    last = int(np.searchsorted(days, A1, side="right")) - 1
    span = last - 1 - first + 1
    rt_pts = s["rt"] / s["mult"]
    cost = rt_pts * (1 + T.rolls.to_numpy())
    tot = np.empty(N_SIM)
    for k in range(N_SIM):
        st = first + (rng.random(len(T)) * span).astype(int)
        tot[k] = (((c[st + 1] - c[st]) / fac[st] - cost) * s["mult"]).sum()
    return tot


# -------------------------------------------------------------- describe ----
def stats(T, lo=A0, hi=A1, col="net_usd"):
    sess = pd.bdate_range(lo, hi)
    daily = T.groupby("session")[col].sum().reindex(sess, fill_value=0.0)
    cum = daily.cumsum()
    x = T[col]
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return dict(n=len(T), per_trade=x.mean(), win=100 * (x > 0).mean(), pf=pos / neg if neg > 0 else np.nan,
                sharpe=daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else np.nan,
                dd=float((cum.cummax() - cum).max()), worst=x.min(), total=x.sum())


def line(label, T, sym, lo=A0, hi=A1):
    a, m = stats(T, lo, hi), stats(T, lo, hi, "net_micro")
    yrs = (hi - lo).days / 365.25
    return (f"  {label:<30} n {a['n']:>4} ({a['n'] / yrs:.0f}/yr) | ${a['per_trade']:+,.0f}/trade "
            f"(${m['per_trade']:+,.2f} {SPEC[sym]['micro']}) | win {a['win']:.1f}% | PF {a['pf']:.2f} | "
            f"Sharpe {a['sharpe']:+.2f} | maxDD ${a['dd']:,.0f} (${m['dd']:,.0f} {SPEC[sym]['micro']}) | "
            f"worst ${a['worst']:,.0f} (${m['worst']:,.0f}) | total ${a['total']:,.0f}")


def main():
    rng = np.random.default_rng(SEED)
    L = ["D3-G / ES REPLICATION -- SEEN DATA, 2010-06-07 -> 2026-09-24",
         "Registered reports/d3g_preregistration.md. Null: 5,000 exposure-matched random lists; Holm within family.",
         ""]
    res, trades, keep = {}, {}, {}
    for sym in ("NQ", "ES"):
        D = load_rth(sym)
        sig = signals(D)
        G, R = globex(sym), load_rolls(sym)
        keep[sym] = (D, G, sig)
        VA, VB = leg(G, R, sym, "A"), leg(G, R, sym, "B")
        for name, V in ((f"{sym}-G/A", VA), (f"{sym}-G/B", VB)):
            if name == "ES-G/B":
                continue                                   # not registered
            T, drop = g_trades(D, G, V, sig)
            tot, pool_mean = null_g(T, V, rng)
            res[name] = dict(T=T, tot=tot, dropped=drop, pool_mean=pool_mean, sym=sym)
        if sym == "ES":
            T = d3_trades(D, sym, sig)
            res["ES-D3"] = dict(T=T, tot=null_d3(T, D, sym, rng), dropped=0, pool_mean=np.nan, sym=sym)
    fams = {"NQ family": ["NQ-G/A", "NQ-G/B"], "ES family": ["ES-D3", "ES-G/A"]}
    labels = {"NQ-G/A": "D3-G/A (NQ, primary)", "NQ-G/B": "D3-G/B (NQ, secondary)",
              "ES-D3": "ES-D3", "ES-G/A": "ES-G/A"}
    verdicts = {}
    for fam, names in fams.items():
        L.append(f"== {fam} ==")
        ps = []
        for n in names:
            r = res[n]
            act = r["T"].net_usd.sum()
            r["p"] = float((1 + (r["tot"] >= act).sum()) / (N_SIM + 1))
            ps.append(r["p"])
        adj = C.holm(ps)
        for n, a in zip(names, adj):
            r = res[n]
            act = r["T"].net_usd.sum()
            ok = act > 0 and a <= 0.05
            verdicts[n] = ok
            L.append(line(labels[n], r["T"], r["sym"]))
            extra = f"; random session ${r['pool_mean']:+,.2f}/trade" if np.isfinite(r["pool_mean"]) else ""
            L.append(f"    null median ${np.median(r['tot']):,.0f}, 95th ${np.percentile(r['tot'], 95):,.0f}{extra}; "
                     f"p {r['p']:.4f}, Holm {a:.4f}; dropped (stale roll) {r['dropped']} -> "
                     f"{'PASS' if ok else 'FAIL'}")
        L.append("")
    L.append("DESCRIPTIVE (cannot change a verdict)")
    for n in ("NQ-G/A", "NQ-G/B", "ES-D3", "ES-G/A"):
        T, sym = res[n]["T"], res[n]["sym"]
        for lo, hi, lab in ((A0, HALF - pd.Timedelta(days=1), "2010-06..2018-06"), (HALF, A1, "2018-07..2026-09")):
            L.append(line(f"{labels[n].split(' (')[0]} {lab}", T[(T.session >= lo) & (T.session <= hi)], sym, lo, hi))
    for n in ("NQ-G/A", "ES-G/A", "ES-D3"):
        T = res[n]["T"]
        yr = T.groupby(T.session.dt.year).net_usd.agg(["size", "sum"])
        L.append(f"  {n} by year (n, net $): " + ", ".join(f"{y} {int(r['size'])} {r['sum']:+,.0f}"
                                                        for y, r in yr.iterrows()))
    # the slice the G rules give up: signal day's RTH close -> next session's first bar
    for sym in ("NQ", "ES"):
        D, G, sig = keep[sym]
        T = res[f"{sym}-G/A"]["T"]
        prev = G.reindex(pd.DatetimeIndex(T.signal_day))
        same = prev.id_rth1.to_numpy() == T.id_in.to_numpy()
        gap = np.where(same, T.px_in.to_numpy() - prev.px_rth1.to_numpy(), np.nan)
        L.append(f"  {sym} 15:59 -> 18:00 slice given up, same signals: {np.nanmean(gap):+.2f} pts/trade "
                 f"(n {int(np.isfinite(gap).sum())}); G/A leg {T.gross_pts.mean():+.2f} pts/trade")
    D = keep["NQ"][0]
    T3 = d3_trades(D, "NQ", keep["NQ"][2])
    L.append(f"  reproduction check, NQ D3 as registered: n {len(T3)}, total ${T3.net_usd.sum():,.0f} "
             f"(daily3 context: n 339, total $210,852)")
    a = res["NQ-G/A"]["T"].set_index("session").net_usd
    b = res["ES-G/A"]["T"].set_index("session").net_usd
    common = a.index.intersection(b.index)
    L.append(f"  NQ-G/A vs ES-G/A per-trade correlation on {len(common)} shared sessions: "
             f"{np.corrcoef(a[common], b[common])[0, 1]:+.2f}; NQ-only {len(a.index.difference(b.index))}, "
             f"ES-only {len(b.index.difference(a.index))}")
    txt = "\n".join(L)
    print(txt)
    (OUT / "d3g_output.txt").write_text(txt + "\n")
    FROZEN.mkdir(parents=True, exist_ok=True)
    allT = pd.concat([r["T"].assign(rule=n, sym=r["sym"], passed=verdicts[n]) for n, r in res.items()],
                     ignore_index=True)
    allT.to_csv(FROZEN / "d3g_trades.csv", index=False)
    return verdicts


FWD_G = pd.Timestamp("2026-09-29")        # registration date: signals from this RTH day on


def forward(since=FWD_G, out=OUT):
    """Paper-track the four rules that passed (d3g_result.md): every signal on or after
    `since`. Writes out/d3g_paper_ledger.csv (no price levels; committed),
    out/d3g_paper_ledger_full.csv (prices; Databento-derived, gitignored) and
    out/d3g_paper_status.md. Signals whose trade has not happened yet are PENDING."""
    rows, ends = [], {}
    for sym in ("NQ", "ES"):
        D = load_rth(sym)
        ends[sym] = D.index[-1]
        if D.index[-1] < since:
            continue
        sig = [i for i in signals(D) if D.index[i] >= since]
        G, R = globex(sym), load_rolls(sym)
        rules = [(f"{sym}-G/A", leg(G, R, sym, "A"))] + ([("NQ-G/B", leg(G, R, sym, "B"))] if sym == "NQ" else [])
        for name, V in rules:
            T, _ = g_trades(D, G, V, sig, since, pd.Timestamp.max)
            rows += [dict(rule=name, signal_day=r.signal_day.date(), session=r.session.date(), status="closed",
                          rolls=int(r.rolls), gross_pts=round(r.gross_pts, 2), net_usd=round(r.net_usd, 2),
                          net_micro=round(r.net_micro, 2), px_in=r.px_in, px_out=r.px_out) for r in T.itertuples()]
            done = set(T.signal_day)
            rows += [dict(rule=name, signal_day=D.index[i].date(), session=None,
                          status="PENDING (enters at the next 18:00 reopen)")
                     for i in sig if D.index[i] not in done and G.index.searchsorted(D.index[i], side="right") >= len(G)]
        if sym == "ES":
            T = d3_trades(D, sym, sig, since, pd.Timestamp.max)
            rows += [dict(rule="ES-D3", signal_day=r.signal_day.date(), session=r.session.date(), status="closed",
                          rolls=int(r.rolls), gross_pts=round(r.gross_pts, 2), net_usd=round(r.net_usd, 2),
                          net_micro=round(r.net_micro, 2)) for r in T.itertuples()]
            if sig and sig[-1] == len(D) - 1:
                rows.append(dict(rule="ES-D3", signal_day=D.index[-1].date(), session=None,
                                 status="OPEN (bought the close; exits next RTH close)"))
    if not rows and min(ends.values()) < since:
        print(f"No forward sessions yet: bars end {min(ends.values()).date()}; D3-G paper-tracking counts signals "
              f"from {since.date()}. Forward bars come from forward_pull.py (P8, monthly).")
        return None
    cols = ["rule", "signal_day", "session", "status", "rolls", "gross_pts", "net_usd", "net_micro", "px_in", "px_out"]
    L = pd.DataFrame(rows, columns=cols).sort_values(["signal_day", "rule"], kind="stable")
    L.to_csv(out / "d3g_paper_ledger_full.csv", index=False)
    L.drop(columns=["px_in", "px_out"]).to_csv(out / "d3g_paper_ledger.csv", index=False)
    M = ["# D3-G rules: paper-tracking status", "",
         f"Registered 0146a06, passed 050dc8c. Signals from {since.date()}; bars to "
         f"{max(ends.values()).date()}. Per 1 contract after step-4 costs. First review 2027-09-25.", "",
         "| rule | closed | pending/open | net $ (1 contract) | net $ (1 micro) |", "|---|---|---|---|---|"]
    for k in ("NQ-G/A", "NQ-G/B", "ES-G/A", "ES-D3"):
        x = L[L.rule == k]
        c = x[x.status == "closed"]
        M.append(f"| {k} | {len(c)} | {len(x) - len(c)} | {c.net_usd.sum():+,.0f} | {c.net_micro.sum():+,.2f} |")
    txt = "\n".join(M)
    (out / "d3g_paper_status.md").write_text(txt + "\n")
    print(txt)
    return L


if __name__ == "__main__":
    forward() if "--forward" in sys.argv else main()
