#!/usr/bin/env python3
"""Risk-managed rerun of the stop-less rules (reports/risk_rerun_preregistration.md).

    python3 scripts/databento/risk_rerun.py --selftest   # stop engine + sizing on synthetic bars
    python3 scripts/databento/risk_rerun.py              # the registered run (once)

Risk block: stop = 0.5 x ADR20 x sqrt(H/390) (H = planned hold, minutes, cap 1440); size =
floor($250 / (stop x $/pt/micro)), cap 10 micros, skip if < 1; daily cap $500; micro costs.
The same block is applied to every random trade of the exposure-matched null.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3g                                                          # noqa: E402
import econ2                                                        # noqa: E402
import h1b_explore as HX                                            # noqa: E402
import ldm                                                          # noqa: E402
import prop_sim as PS                                               # noqa: E402
import step4_common as C                                            # noqa: E402

A0, A1 = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-09-24")
SPLIT = pd.Timestamp("2018-07-01")
STOP_K, RISK, CAP_MICROS, DAY_CAP = 0.5, 250.0, 10, 500.0
SEED, N_SIM = 20260930, 5000
SPEC = d3g.SPEC
OUT = d3g.OUT


# --------------------------------------------------------------- engine ----
def stop_distance(adrp, px, hold_min):
    return STOP_K * adrp * px * np.sqrt(min(hold_min, 1440) / 390.0)


def size(stop_pts, sym):
    q = int(np.floor(RISK / (stop_pts * SPEC[sym]["mmult"]))) if stop_pts > 0 else 0
    return min(q, CAP_MICROS)


def stop_scan(ro, rh, rl, rc, side, sd, exit_at):
    """Bars from the entry bar (entry at its open, ro[0] == 0) to the planned exit bar, as
    price minus entry-base (long view). exit_at 'close' = close of the last bar; 'open' = open
    of the last bar. Returns pnl points (position view), exit index, reason, best[], worst[]."""
    n = len(ro)
    full = n if exit_at == "close" else n - 1
    op = side * ro[:full]
    worst = (rl if side > 0 else -rh)[:full]
    best = (rh if side > 0 else -rl)[:full]
    gap = op <= -sd
    gap[:1] = False
    hit = gap | (worst <= -sd)
    if hit.any():
        k = int(hit.argmax())
        pnl = float(op[k]) if gap[k] else -sd
        w = worst[:k + 1].copy()
        w[k] = max(w[k], pnl)
        return pnl, k, "stop", best[:k + 1], w
    pnl = float(side * (rc[n - 1] if exit_at == "close" else ro[n - 1]))
    if exit_at == "open":
        return pnl, n - 1, "planned", np.append(best, pnl), np.append(worst, pnl)
    return pnl, n - 1, "planned", best, worst


def settle(pnl, stop_pts, rolls, sym):
    q = size(stop_pts, sym)
    if q < 1:
        return 0, np.nan
    s = SPEC[sym]
    return q, q * (pnl * s["mmult"] - s["mrt"] * (1 + rolls))


# ---------------------------------------------------------- RTH templates ----
def rth_values(A, entry_bar, side_of_day=None):
    """For every loaded RTH day: stopped, sized net $ of a trade entering at the open of
    `entry_bar` and exiting at the 15:59 close, for side +1 and -1. Real points = adjusted / fac."""
    sym = A["sym"]
    rows = {}
    for d in range(len(A["days"])):
        o, h, l, c = A["O"][d], A["H"][d], A["L"][d], A["C"][d]
        valid = np.flatnonzero(~np.isnan(c))
        if not len(valid) or valid[-1] <= entry_bar or np.isnan(o[entry_bar]) or not np.isfinite(A["adrp"][d]):
            continue
        x = valid[-1]
        fac, px = A["fac"][d], o[entry_bar]
        seg = slice(entry_bar, x + 1)
        ro, rh, rl, rc = [(v[seg] - px) / fac for v in (o, h, l, c)]
        ro = np.nan_to_num(ro, nan=0.0)
        rh, rl = np.nan_to_num(rh, nan=0.0), np.nan_to_num(rl, nan=0.0)
        sd = stop_distance(A["adrp"][d], px / fac, 390 - entry_bar)
        out = {}
        for side in (1, -1):
            pnl, k, why, best, worst = stop_scan(ro, rh, rl, rc, side, sd, "close")
            q, net = settle(pnl, sd, 0, sym)
            out[side] = dict(net=net, qty=q, pnl=pnl, why=why, sd=sd, best=best, worst=worst)
        rows[A["days"][d]] = out
    return rows


# ------------------------------------------------------- Globex templates ----
def globex_values(sym, which):
    """Every Globex session: 18:00 reopen -> RTH close ('A') or RTH open ('B'), stopped and
    sized, long only (the G rules and H2 are long)."""
    G, R = d3g.globex(sym), d3g.load_rolls(sym)
    V = d3g.leg(G, R, sym, which)
    fs = sorted(d3g.B1.glob(f"{sym}_*.parquet"))
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "instrument_id", "open", "high", "low", "close"])
                   for f in fs], ignore_index=True).sort_values("ts_et").reset_index(drop=True)
    ts = b.ts_et.to_numpy()
    O, H, L, Cc, I = (b[c].to_numpy() for c in ("open", "high", "low", "close", "instrument_id"))
    Ar = ldm.load(sym, A1)
    adr = pd.Series(Ar["adrp"], index=Ar["days"])
    rows = {}
    for s, v in V.iterrows():
        if not np.isfinite(v.gross_pts) or s < A0 or s > A1:
            continue
        i0 = int(np.searchsorted(ts, np.datetime64(v.t_in)))
        i1 = int(np.searchsorted(ts, np.datetime64(v.t_out)))
        if i1 <= i0 or i1 >= len(ts):
            continue
        a = adr.reindex([s], method="bfill").iloc[0]
        if not np.isfinite(a):
            continue
        base = np.where(I[i0:i1 + 1] == v.id_in, v.px_in,
                        (v.roll_new_open - v.roll_old_close + v.px_in) if v.rolls else np.nan)
        if np.isnan(base).any():
            continue
        ro, rh, rl, rc = (X[i0:i1 + 1] - base for X in (O, H, L, Cc))
        hold = (v.t_out - v.t_in) / pd.Timedelta(minutes=1) + (1 if which == "A" else 0)
        sd = stop_distance(a, v.px_in, hold)
        pnl, k, why, best, worst = stop_scan(ro, rh, rl, rc, 1, sd, "close" if which == "A" else "open")
        q, net = settle(pnl, sd, int(v.rolls), sym)
        rows[s] = {1: dict(net=net, qty=q, pnl=pnl, why=why, sd=sd, best=best, worst=worst, rolls=int(v.rolls))}
    return rows


# ------------------------------------------------------------ evaluate ----
def evaluate(name, sym, vals, trades, pool, rng):
    """trades: list of (session, side). pool: sessions eligible for the null."""
    act = [(s, sd_) for s, sd_ in trades if s in vals and vals[s][sd_]["qty"] >= 1]
    skipped = sum(1 for s, sd_ in trades if s in vals and vals[s][sd_]["qty"] < 1)
    T = pd.DataFrame([dict(session=s, side=sd_, **{k: vals[s][sd_][k] for k in ("net", "qty", "pnl", "why", "sd")})
                      for s, sd_ in act])
    sides = T.side.to_numpy()
    tot = np.empty(N_SIM)
    pool_net = {sd_: np.array([vals[s][sd_]["net"] for s in pool if sd_ in vals[s] and vals[s][sd_]["qty"] >= 1])
                for sd_ in (1, -1)}
    for k in range(N_SIM):
        t = 0.0
        for sd_ in (1, -1):
            m = int((sides == sd_).sum())
            if m:
                arr = pool_net[sd_]
                t += arr[rng.integers(0, len(arr), m)].sum()
        tot[k] = t
    p = float((1 + (tot >= T.net.sum()).sum()) / (N_SIM + 1))
    return dict(name=name, sym=sym, T=T, tot=tot, p=p, skipped=skipped)


def describe(T):
    yrs = (A1 - A0).days / 365.25
    x = T.net
    lo, hi = T[T.session < SPLIT].net, T[T.session >= SPLIT].net
    return (f"n {len(T)} ({len(T) / yrs:.0f}/yr) | ${x.mean():+,.1f}/trade | win {100 * (x > 0).mean():.1f}% | "
            f"total ${x.sum():+,.0f} | stops {100 * (T.why == 'stop').mean():.0f}% | avg micros {T.qty.mean():.1f} | "
            f"worst ${x.min():,.0f} | losses > ${DAY_CAP:.0f}: {int((x < -DAY_CAP).sum())} | "
            f"pre-2018 ${lo.sum():+,.0f}, 2018+ ${hi.sum():+,.0f}")


def main():
    rng = np.random.default_rng(SEED)
    An = ldm.load("NQ", A1)
    days = An["days"]
    win = lambda idx: [s for s in idx if A0 <= s <= A1]                         # noqa: E731
    # --- trade lists (timing and direction exactly as the original rules) ---
    g = pd.read_csv(d3g.FROZEN / "d3g_trades.csv", parse_dates=["session"])
    sess = {r: list(g[g.rule == r].session) for r in ("NQ-G/A", "NQ-G/B", "ES-G/A")}
    Dr = d3g.load_rth("NQ")
    sig_days = Dr.index[d3g.signals(Dr)]
    d3p = [days[days.searchsorted(sd, side="right")] for sd in sig_days if days.searchsorted(sd, side="right") < len(days)]
    Dm = econ2.minute_table("NQ")
    h1 = econ2.h1_trades(Dm, "NQ", A0, A1)
    Dx = HX.day_table("NQ", A1)
    h1b, _ = HX.config_trades(Dx, "NQ", "15:45", "abs_r", 90, A0, A1)
    Gn = d3g.globex("NQ")
    tom = econ2.tom_sessions(Gn)
    # --- stopped, sized values for every eligible session ---
    vA, vB, vES = globex_values("NQ", "A"), globex_values("NQ", "B"), globex_values("ES", "A")
    v0930, v1530, v1545 = rth_values(An, 0), rth_values(An, 360), rth_values(An, 375)
    rth_pool = win(v0930.keys())
    specs = [("D3-G/A", "NQ", vA, [(s, 1) for s in sess["NQ-G/A"]], win(vA.keys())),
             ("D3-G/B", "NQ", vB, [(s, 1) for s in sess["NQ-G/B"]], win(vB.keys())),
             ("ES-G/A", "ES", vES, [(s, 1) for s in sess["ES-G/A"]], win(vES.keys())),
             ("D3P", "NQ", v0930, [(s, 1) for s in win(d3p)], rth_pool),
             ("H1", "NQ", v1530, list(zip(h1.session, h1.side)), win(v1530.keys())),
             ("H1-B", "NQ", v1545, list(zip(h1b.session, h1b.side)), win(v1545.keys())),
             ("H2", "NQ", vA, [(s, 1) for s in win(tom)], win(vA.keys()))]
    res = [evaluate(n, sym, v, tr, pool, rng) for n, sym, v, tr, pool in specs]
    adj = C.holm([r["p"] for r in res])
    L = ["RISK-MANAGED RERUN -- stop 0.5 x ADR20 x sqrt(hold/390), $250 risk per trade (<= 10 micros), "
         "daily cap $500, micro costs; 2010-06-07 -> 2026-09-24 (all seen)",
         "Registered reports/risk_rerun_preregistration.md. Null: 5,000 exposure-matched lists under the same "
         "risk block. Holm across 7.", ""]
    for r, a in zip(res, adj):
        ok = r["T"].net.sum() > 0 and a <= 0.05
        r["pass"], r["holm"] = ok, a
        L.append(f"  {r['name']:<7} {describe(r['T'])}")
        L.append(f"          skipped (stop too wide for $250 at 1 micro): {r['skipped']}; null median "
                 f"${np.median(r['tot']):+,.0f}, 95th ${np.percentile(r['tot'], 95):+,.0f}; p {r['p']:.4f}, Holm {a:.4f} "
                 f"-> {'RISK-MANAGED PASS' if ok else 'FAIL'}")
    L += ["", "PROP SIMULATOR, risk-sized (descriptive)"]
    for r in res:
        vals = dict(specs[[s[0] for s in specs].index(r["name"])][2])
        T = r["T"].sort_values("session")
        trades = []
        for t in T.itertuples():
            v = vals[t.session][t.side]
            trades.append(PS.Trade(day=pd.Timestamp(t.session), hi=np.asarray(v["best"], float),
                                   lo=np.asarray(v["worst"], float), gross=float(v["pnl"]),
                                   cost=SPEC[r["sym"]]["mrt"] * (1 + v.get("rolls", 0)), qty=int(v["qty"])))
        G = d3g.globex(r["sym"])
        S = PS.simulate(trades, G.index[(G.index >= A0) & (G.index <= A1)], SPEC[r["sym"]]["mmult"], sizes=(None,))
        for _, x in S.iterrows():
            L.append(f"  {r['name']:<7} {x.account:<14} pass 30d {100 * x.pass_30d:5.1f}%  90d {100 * x.pass_90d:5.1f}%  "
                     f"365d {100 * x.pass_365d:5.1f}%  fail 365d {100 * x.fail_365d:5.1f}%  median days "
                     f"{x.median_days_to_pass:.0f}")
    txt = "\n".join(L)
    print(txt)
    (OUT / "risk_rerun_output.txt").write_text(txt + "\n")
    return res


# ------------------------------------------------------------- selftest ----
def selftest():
    def chk(name, got, want):
        print(f"[{'ok' if got == want else 'FAIL'}] {name}: {got}")
        if got != want:
            raise SystemExit(1)
    z = lambda *a: np.array(a, float)                                           # noqa: E731
    # long, stop 5: path never below -5 -> planned close exit at +3
    r = stop_scan(z(0, 1, 2), z(1, 2, 4), z(-2, 0, 1), z(1, 2, 3), 1, 5.0, "close")
    chk("no stop -> planned close", (r[0], r[2]), (3.0, "planned"))
    # low touches -6 on bar 1 -> exit at -5
    r = stop_scan(z(0, 1, 2), z(1, 2, 4), z(-2, -6, 1), z(1, 2, 3), 1, 5.0, "close")
    chk("touch -> stop at level", (r[0], r[1], r[2]), (-5.0, 1, "stop"))
    # bar 2 opens at -8 (gap through) -> exit at the open
    r = stop_scan(z(0, 1, -8), z(1, 2, -7), z(-2, 0, -9), z(1, -1, -8), 1, 5.0, "close")
    chk("gap -> exit at open", (r[0], r[1]), (-8.0, 2))
    # entry bar low below the stop counts (entry at the open; the bar follows the fill)
    r = stop_scan(z(0, 1), z(1, 2), z(-6, 0), z(1, 2), 1, 5.0, "close")
    chk("entry-bar stop", (r[0], r[1]), (-5.0, 0))
    # short: price rises 6 (rh = +6) -> stopped at -5
    r = stop_scan(z(0, 1, 2), z(1, 6, 3), z(-1, 0, 1), z(1, 2, 2), -1, 5.0, "close")
    chk("short stop", (r[0], r[1]), (-5.0, 1))
    # short, price falls to -4 at close -> +4
    r = stop_scan(z(0, -1, -3), z(1, 0, -2), z(-1, -2, -4), z(-1, -3, -4), -1, 5.0, "close")
    chk("short planned", r[0], 4.0)
    # exit at the open of the last bar
    r = stop_scan(z(0, 1, 2.5), z(1, 2, 9), z(-1, 0, -9), z(1, 2, 3), 1, 5.0, "open")
    chk("exit at last bar open (its range ignored)", (r[0], r[2]), (2.5, "planned"))
    # sizing: stop 10 pts MNQ ($20/micro) -> 12 -> cap 10; stop 50 -> 2; stop 200 -> 0 (skip)
    chk("size cap", size(10.0, "NQ"), 10)
    chk("size 50 pts", size(50.0, "NQ"), 2)
    chk("size skip", size(200.0, "NQ"), 0)
    chk("stop distance 0.5 x ADR x sqrt(H/390)", round(stop_distance(0.02, 20000, 390), 6), 200.0)
    chk("stop distance, 29-minute hold", round(stop_distance(0.02, 20000, 29), 2), round(200 * np.sqrt(29 / 390), 2))
    print("selftest passed")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
