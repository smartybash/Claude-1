#!/usr/bin/env python3
"""Test 3 of reports/d3g_preregistration.md: prop-evaluation simulator (descriptive).

    python3 scripts/databento/prop_sim.py            # rules from reports/step4/frozen/d3g_trades.csv
    python3 scripts/databento/prop_sim.py --selftest # engine checks on synthetic trades only

Accounts (50K; third-party summaries of the rules, 2026-09-29 -- confirm in the dashboards):
  apex_intraday  target +3,000; threshold = peak equity incl. open profit - 2,500, stops at
                 50,100; breached intraday; no daily loss limit
  apex_eod       target +3,000; threshold = peak end-of-day balance - 2,500, stops at 50,100;
                 breached intraday; daily loss limit 1,000 closes the position for the day
  lucid_flex     target +3,000; threshold = peak end-of-day balance - 2,000, stops at 50,100
                 (assumed); checked at the close only; 50% consistency to pass
Conservative mechanics: full round-trip cost charged at entry; within a 1-minute bar the
favourable extreme comes first (the trailing threshold rises, then the low is tested).
Starts: every session of the window with >= 365 days of data after it; each evaluation runs
on the actual history until it passes or fails.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
START = 50_000.0
LOCK = START + 100.0
TARGET = START + 3_000.0
ACCOUNTS = ("apex_intraday", "apex_eod", "lucid_flex")
SIZES = range(1, 11)


@dataclass
class Trade:
    day: pd.Timestamp        # Globex session (one trading day)
    hi: np.ndarray           # per bar, best open P&L in points per contract (after the roll offset)
    lo: np.ndarray           # per bar, worst open P&L in points
    gross: float             # final P&L in points per contract
    cost: float              # round-trip cost per micro, $ (rolls included)


def run(trades, account, q, mult):
    """Evaluate one account at q micros from trades[0]. Returns (event, day) with event
    'pass' / 'fail' / None (data ended first)."""
    B = START
    thr = START - (2_000.0 if account == "lucid_flex" else 2_500.0)
    dd = START - thr
    peak = START
    best_day = 0.0
    for t in trades:
        day_start = B
        B -= t.cost * q
        hi, lo = B + t.hi * mult * q, B + t.lo * mult * q
        final = B + t.gross * mult * q
        if account == "apex_intraday":
            pk = np.maximum(peak, np.maximum.accumulate(hi))
            th = np.maximum(thr, np.minimum(pk - dd, LOCK))
            if (lo <= th).any():
                return "fail", t.day
            B, peak, thr = final, max(pk[-1], final), max(th[-1], min(max(pk[-1], final) - dd, LOCK))
        elif account == "apex_eod":
            dll = day_start - 1_000.0
            mn = lo.min() if len(lo) else final
            if dll > thr:
                B = dll if mn <= dll else final
            else:
                if mn <= thr:
                    return "fail", t.day
                B = final
            peak = max(peak, B)
            thr = max(thr, min(peak - dd, LOCK))
        else:                                                   # lucid_flex: close-only checks
            B = final
            if B <= thr:
                return "fail", t.day
            peak = max(peak, B)
            thr = max(thr, min(peak - dd, LOCK))
            best_day = max(best_day, B - day_start)
        if B >= TARGET:
            if account != "lucid_flex" or best_day <= 0.5 * (B - START):
                return "pass", t.day
    return None, None


def simulate(trades, sessions, mult, horizon_days=365):
    """For every account and size: outcome by start session. Runs from each first trade k
    are shared by all starts that map to k."""
    days = pd.DatetimeIndex([t.day for t in trades])
    last = sessions.max()
    starts = sessions[sessions <= last - pd.Timedelta(days=horizon_days)]
    kmap = days.searchsorted(starts)
    rows = []
    for acc in ACCOUNTS:
        for q in SIZES:
            ev = [run(trades[k:], acc, q, mult) for k in range(len(trades))]
            res = []
            for s, k in zip(starts, kmap):
                e, d = ev[k] if k < len(trades) else (None, None)
                res.append((e, (d - s).days if d is not None else np.inf))
            e = np.array([r[0] for r in res], dtype=object)
            dd = np.array([r[1] for r in res], float)
            row = dict(account=acc, micros=q, starts=len(starts))
            for h in (30, 90, 365):
                row[f"pass_{h}d"] = float(((e == "pass") & (dd <= h)).mean())
            row["fail_365d"] = float(((e == "fail") & (dd <= 365)).mean())
            pd_ = dd[(e == "pass") & (dd <= 365)]
            row["median_days_to_pass"] = float(np.median(pd_)) if len(pd_) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------- real trades ----
def build_trades(T, sym):
    """Trade paths from the unadjusted 1-minute bars, per contract, in points."""
    import d3g
    mrt = d3g.SPEC[sym]["mrt"]
    months = pd.period_range(T.t_in.min().to_period("M"), T.t_out.max().to_period("M"), freq="M")
    fs = [d3g.B1 / f"{sym}_{m.strftime('%Y-%m')}.parquet" for m in months]
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "instrument_id", "high", "low"]) for f in fs if f.exists()],
                  ignore_index=True).sort_values("ts_et").set_index("ts_et")
    out = []
    for r in T.itertuples():
        seg = b.loc[r.t_in:r.t_out]
        if r.exit_at == "open":                     # exit at the open of the last bar
            seg = seg[seg.index < r.t_out]
        # open P&L: before the roll price - entry; after it (old_close - entry) + (price - new_open)
        after = seg.instrument_id.to_numpy() != r.id_in
        base = np.where(after, (r.roll_new_open - r.roll_old_close + r.px_in) if r.rolls else np.nan, r.px_in)
        out.append(Trade(day=pd.Timestamp(r.session), hi=seg.high.to_numpy() - base, lo=seg.low.to_numpy() - base,
                         gross=float(r.gross_pts), cost=mrt * (1 + int(r.rolls))))
    return out


def main():
    import d3g
    T = pd.read_csv(d3g.FROZEN / "d3g_trades.csv",
                    parse_dates=["signal_day", "session", "t_in", "t_out", "roll_t"])
    passed = sorted(T[T.passed & T.rule.str.contains("-G/")].rule.unique())
    note = ""
    if not passed:
        passed = ["NQ-G/A"]
        note = "  (no G rule passed Tests 1-2: D3-G/A shown as a FAILED RULE, ILLUSTRATION ONLY)"
    if (T.passed & (T.rule == "ES-D3")).any():
        note += "\n  ES-D3 passed but holds through the close: not tradable at Apex / Lucid, not simulated."
    L = ["PROP-EVALUATION SIMULATOR -- SEEN DATA (descriptive; cannot pass or fail a rule)",
         "Accounts: Apex 50K intraday trailing, Apex 50K EOD (+$1,000 DLL), Lucid Flex 50K (EOD, 50% consistency).",
         "Conservative: cost at entry, favourable extreme first within a bar." + note, ""]
    for rule in passed:
        sub = T[T.rule == rule].sort_values("session")
        sym = sub.sym.iloc[0]
        trades = build_trades(sub, sym)
        G = d3g.globex(sym)
        sess = G.index[(G.index >= d3g.A0) & (G.index <= d3g.A1)]
        R = simulate(trades, sess, d3g.SPEC[sym]["mmult"])
        L.append(f"== {rule}: {len(trades)} trades, {d3g.SPEC[sym]['micro']} sizes 1-10 ==")
        R2 = R.copy()
        for c in ("pass_30d", "pass_90d", "pass_365d", "fail_365d"):
            R2[c] = (100 * R2[c]).map("{:.1f}%".format)
        L.append(R2.to_string(index=False))
        L.append("")
    txt = "\n".join(L)
    print(txt)
    (d3g.OUT / "prop_sim_output.txt").write_text(txt + "\n")


# --------------------------------------------------------------- selftest ----
def selftest():
    d = pd.Timestamp("2020-01-02")
    day = lambda k: d + pd.Timedelta(days=k)                                    # noqa: E731
    mk = lambda k, path, g, cost=0.0: Trade(day(k), np.array([p[0] for p in path], float),   # noqa: E731
                                            np.array([p[1] for p in path], float), g, cost)
    mult = 2.0                                                                 # MNQ $/pt

    def chk(name, got, want):
        print(f"[{'ok' if got == want else 'FAIL'}] {name}: {got}")
        if got != want:
            raise SystemExit(1)

    # 1. steady winners: +$500/day at 10 MNQ (25 pts) -> pass on the 6th trade everywhere except
    #    Lucid, where the 50% consistency needs no single day > half: 6 x 500 fine
    W = [mk(k, [(25, -1)], 25) for k in range(10)]
    for acc in ACCOUNTS:
        chk(f"steady winners, {acc}", run(W, acc, 10, mult), ("pass", day(5)))
    # 2. give-back: open profit +$2,000 (100 pts at 10 MNQ), closes at -$600: only the
    #    intraday-trailing account fails (threshold 49,500)
    X = [mk(0, [(100, 0), (100, -30)], -30)]
    chk("give-back, apex_intraday", run(X, "apex_intraday", 10, mult), ("fail", day(0)))
    chk("give-back, apex_eod", run(X, "apex_eod", 10, mult), (None, None))
    chk("give-back, lucid_flex", run(X, "lucid_flex", 10, mult), (None, None))
    # 3. daily loss limit: dips -$1,500 then closes +$100 -> apex_eod closed at -$1,000 (49,000),
    #    then +$700 a day: apex_eod passes after 6 winners, apex_intraday (50,100) after 5
    Y = [mk(0, [(0, -75), (5, -75)], 5)] + [mk(k, [(35, 0)], 35) for k in range(1, 12)]
    chk("DLL then winners, apex_eod", run(Y, "apex_eod", 10, mult), ("pass", day(6)))
    chk("DLL then winners, apex_intraday", run(Y, "apex_intraday", 10, mult), ("pass", day(5)))
    # 4. Lucid consistency: +$3,000 on day 0 cannot pass until total >= $6,000
    Z = [mk(0, [(150, 0)], 150)] + [mk(k, [(25, 0)], 25) for k in range(1, 20)]
    chk("consistency, lucid_flex", run(Z, "lucid_flex", 10, mult), ("pass", day(6)))
    chk("no consistency, apex_eod", run(Z, "apex_eod", 10, mult), ("pass", day(0)))
    # 5. Lucid checks the close only: an intraday dip below the threshold that recovers survives
    V = [mk(0, [(0, -130), (0, 0)], 0)]
    chk("intraday dip, lucid_flex", run(V, "lucid_flex", 10, mult), (None, None))
    chk("intraday dip, apex_eod (DLL closes it at -1,000)", run(V, "apex_eod", 10, mult), (None, None))
    chk("intraday dip, apex_intraday", run(V, "apex_intraday", 10, mult), ("fail", day(0)))
    # 6. the threshold stops rising at 50,100: open profit +$2,900, close +$2,600 (52,600), then a
    #    close at 50,150 survives (unlocked levels 50,400 Apex / 50,600 Lucid would fail it);
    #    a close at 50,050 fails
    U = [mk(0, [(145, 130)], 130), mk(1, [(0, -122.5)], -122.5)]
    U2 = [mk(0, [(145, 130)], 130), mk(1, [(0, -127.5)], -127.5)]
    for acc in ("apex_intraday", "lucid_flex"):
        chk(f"lock holds, {acc}", run(U, acc, 10, mult), (None, None))
        chk(f"below lock fails, {acc}", run(U2, acc, 10, mult), ("fail", day(1)))
    # 7. costs are charged: +2 pt ($4) at 1 MNQ passes after 750 trades without costs, never with $2.24
    K = [mk(k, [(2, 0)], 2, 2.24) for k in range(1000)]
    K0 = [mk(k, [(2, 0)], 2, 0.0) for k in range(1000)]
    chk("costs charged, apex_eod", run(K, "apex_eod", 1, mult), (None, None))
    chk("no costs, apex_eod", run(K0, "apex_eod", 1, mult), ("pass", day(749)))
    # 8. simulate(): outcome shared by starts that map to the same first trade; days counted from start
    S = pd.DatetimeIndex([day(k) for k in range(0, 800)])
    R = simulate(W, S, mult, horizon_days=365)
    r = R[(R.account == "apex_eod") & (R.micros == 10)].iloc[0]
    chk("simulate: starts after the last trade never pass", r.pass_365d < 1.0 and r.pass_30d > 0, True)
    print("selftest passed")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
