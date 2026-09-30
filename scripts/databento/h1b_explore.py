#!/usr/bin/env python3
"""H1-B exploration on DISCOVERY ONLY (reports/h1b_exploration_plan.md).

45 configurations = entry {15:30, 15:45, 15:50} x size measure {|r|, |r|/sigma20, |r_open|}
x trailing-percentile threshold {50..90}. Selection rule fixed in the plan. Data after
2020-12-31 is cut on load and asserted absent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3g                                                          # noqa: E402

DISC0, DISC1 = pd.Timestamp("2010-06-07"), pd.Timestamp("2020-12-31")
MID = DISC0 + (DISC1 - DISC0) / 2
ENTRIES = {"15:30": 360, "15:45": 375, "15:50": 380}
MEASURES = ("abs_r", "abs_r_over_sigma20", "abs_r_open")
QS = (50, 60, 70, 80, 90)
SEED, N_SIM = 20260930, 5000
SPEC = d3g.SPEC
OUT = d3g.OUT


def day_table(sym, end):
    """Per RTH day (>= 300 bars): prior close, today's open, closes/opens around each entry,
    15:59 close, sigma20 of prior daily returns, factor. Nothing after `end` is loaded."""
    d = pd.read_parquet(d3g.S4 / f"{sym}_1m.parquet")
    d = d[d.timestamp < end + pd.Timedelta(days=1)]
    d["day"] = d.timestamp.dt.normalize()
    d["mm"] = (d.timestamp.dt.hour * 60 + d.timestamp.dt.minute - 570).astype(int)
    cnt = d.groupby("day").size()
    d = d[d.day.isin(cnt[cnt >= 300].index)]
    D = pd.DataFrame({"c": d.groupby("day").close.last()})
    at = lambda m, col: d[d.mm == m].set_index("day")[col].reindex(D.index)     # noqa: E731
    D["o0930"], D["c1559"] = at(0, "open"), at(389, "close")
    for k, m in ENTRIES.items():
        D[f"cs_{k}"], D[f"o_{k}"] = at(m - 1, "close"), at(m, "open")
    f = pd.read_parquet(d3g.S4 / f"{sym}_factor.parquet")
    fi = pd.to_datetime(f.day)
    D["fac"] = pd.Series(f.factor.to_numpy(), index=fi).reindex(D.index).to_numpy()
    D["iid"] = pd.Series(f.instrument_id.to_numpy(), index=fi).reindex(D.index).to_numpy()
    D["c_prev"] = D.c.shift(1)
    D["sig20"] = np.log(D.c / D.c_prev).rolling(20).std().shift(1)
    assert D.index.max() <= end
    return D


def trailing_pct(S, n=250, min_n=120):
    """pct[t] = share of the prior n valid values below S[t] (causal); NaN until min_n exist."""
    v = S.to_numpy(float)
    out = np.full(len(v), np.nan)
    hist = []
    for i, x in enumerate(v):
        if np.isnan(x):
            continue
        if len(hist) >= min_n:
            w = np.asarray(hist[-n:])
            out[i] = (w < x).mean()
        hist.append(x)
    return pd.Series(out, index=S.index)


def config_trades(D, sym, entry, measure, q, lo, hi):
    base = D.c_prev if measure != "abs_r_open" else D.o0930
    r = D[f"cs_{entry}"] / base - 1
    S = r.abs() / D.sig20 if measure == "abs_r_over_sigma20" else r.abs()
    pct = trailing_pct(S)
    move = (D.c1559 - D[f"o_{entry}"]) / D.fac
    ok = (pct >= q / 100) & (r != 0) & move.notna() & (D.index >= lo) & (D.index <= hi)
    s = SPEC[sym]
    T = pd.DataFrame({"session": D.index[ok], "side": np.sign(r[ok]).astype(int).to_numpy(),
                      "move": move[ok].to_numpy(), "S": S[ok].to_numpy()})
    T["gross_pts"] = T.side * T.move
    T["net_usd"] = T.gross_pts * s["mult"] - s["rt"]
    T["net_micro"] = T.gross_pts * s["mmult"] - s["mrt"]
    pool = move[move.notna() & (D.index >= lo) & (D.index <= hi)].to_numpy()
    return T, pool


def null_p(T, pool, sym, rng):
    s = SPEC[sym]
    side = T.side.to_numpy()
    tot = np.array([(side * pool[rng.integers(0, len(pool), len(T))]).sum() * s["mult"] - s["rt"] * len(T)
                    for _ in range(N_SIM)])
    return float((1 + (tot >= T.net_usd.sum()).sum()) / (N_SIM + 1)), tot


def main():
    rng = np.random.default_rng(SEED)
    Dn, De = day_table("NQ", DISC1), day_table("ES", DISC1)
    yrs = (DISC1 - DISC0).days / 365.25
    hy1, hy2 = (MID - DISC0).days / 365.25, (DISC1 - MID).days / 365.25
    rows = []
    for entry in ENTRIES:
        for meas in MEASURES:
            for q in QS:
                T, pool = config_trades(Dn, "NQ", entry, meas, q, DISC0, DISC1)
                Te, _ = config_trades(De, "ES", entry, meas, q, DISC0, DISC1)
                assert T.session.max() <= DISC1 and Te.session.max() <= DISC1
                h1 = T[T.session <= MID].net_usd.sum()
                h2 = T[T.session > MID].net_usd.sum()
                p, _ = null_p(T, pool, "NQ", rng)
                rows.append(dict(entry=entry, measure=meas, q=q, n=len(T), per_yr=len(T) / yrs,
                                 usd_trade=T.net_usd.mean(), total=T.net_usd.sum(), half1_yr=h1 / hy1,
                                 half2_yr=h2 / hy2, es_total=Te.net_usd.sum(), p_disc=p))
    R = pd.DataFrame(rows)
    R["eligible"] = (R.per_yr >= 25) & (R.half1_yr > 0) & (R.half2_yr > 0) & (R.es_total > 0)
    R["min_half_yr"] = R[["half1_yr", "half2_yr"]].min(axis=1)
    R["entry_min"] = R.entry.map(ENTRIES)
    E = R[R.eligible].sort_values(["min_half_yr", "q", "entry_min"], ascending=False)
    R.drop(columns="entry_min").to_csv(OUT / "h1b_exploration_grid.csv", index=False, float_format="%.4f")

    L = ["H1-B EXPLORATION -- DISCOVERY ONLY (NQ, ES 2010-06-07 -> 2020-12-31); holdout sealed",
         "Plan: reports/h1b_exploration_plan.md. Costs NQ $14.50 / ES $29.50 per round trip.", "",
         "HONESTY CHECKS"]
    # original H1 top quintile (quintiles on the whole discovery sample: look-ahead)
    T0, pool0 = config_trades(Dn, "NQ", "15:30", "abs_r", 0, DISC0, DISC1)
    top = T0[T0.S >= T0.S.quantile(0.8)].net_usd
    boot = np.array([rng.choice(top.to_numpy(), len(top)).mean() for _ in range(5000)])
    L.append(f"  original H1 top |r| quintile (full-sample cut, after the 120-day warm-up): n {len(top)}, ${top.mean():+.1f}/trade, "
             f"t {top.mean() / top.std() * np.sqrt(len(top)):+.2f}, bootstrap 95% CI "
             f"[{np.percentile(boot, 2.5):+.1f}, {np.percentile(boot, 97.5):+.1f}]")
    L.append(f"  grid: {len(R)} configurations; net positive {int((R.total > 0).sum())}; "
             f"p_disc <= 0.05 {int((R.p_disc <= 0.05).sum())} (about {0.05 * len(R):.0f} expected by chance if "
             f"independent; they are highly correlated); eligible {int(R.eligible.sum())}")
    L += ["", "FULL GRID (NQ discovery; $/yr per half; ES total same configuration)",
          f"  {'entry':<6}{'measure':<20}{'q':>3}{'n':>6}{'/yr':>6}{'$/trade':>9}{'total':>10}{'half1/yr':>10}"
          f"{'half2/yr':>10}{'ES total':>10}{'p':>8}  elig"]
    for r in R.itertuples():
        L.append(f"  {r.entry:<6}{r.measure:<20}{r.q:>3}{r.n:>6}{r.per_yr:>6.0f}{r.usd_trade:>+9.1f}{r.total:>+10,.0f}"
                 f"{r.half1_yr:>+10,.0f}{r.half2_yr:>+10,.0f}{r.es_total:>+10,.0f}{r.p_disc:>8.4f}  "
                 f"{'yes' if r.eligible else ''}")
    L.append("")
    if E.empty:
        L.append("SELECTION: no configuration is eligible -> nothing frozen; H1-B CLOSED; holdout stays sealed.")
    else:
        b = E.iloc[0]
        L.append(f"SELECTION: entry {b.entry}, measure {b.measure}, q {b.q} -- n {b.n} ({b.per_yr:.0f}/yr), "
                 f"${b.usd_trade:+.1f}/trade, halves ${b.half1_yr:+,.0f}/yr and ${b.half2_yr:+,.0f}/yr, "
                 f"ES ${b.es_total:+,.0f}; discovery p {b.p_disc:.4f} (INFLATED by selection over {len(R)})")
        L.append("  runner-up configurations (eligible, by the same rule):")
        for r in E.iloc[1:6].itertuples():
            L.append(f"    {r.entry} {r.measure} q{r.q}: min half ${r.min_half_yr:+,.0f}/yr, ${r.usd_trade:+.1f}/trade, "
                     f"n {r.n}")
    txt = "\n".join(L)
    print(txt)
    (OUT / "h1b_exploration_output.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
