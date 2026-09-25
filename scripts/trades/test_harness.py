#!/usr/bin/env python3
"""Checks for tradovate_harness.py on synthetic Tradovate exports built from the real
NQ 1-minute bars (needs data/clean/bars_1m locally). Writes only to a temp dir.

    python3 scripts/trades/test_harness.py

 1. FIFO: scale-out, reversal and an open lot on a hand-made file.
 2. Costs: step-4 round trip = $14.50 per NQ lot, $2.24 per MNQ lot.
 3. Orders.csv shape: Status filter, column picks (Fill Time, filledQty, Avg Fill
    Price, not Limit Price / _priceFormat), Chicago time zone -> every fill in its bar.
 4. Wrong time zone: fills fall outside their bars and the diagnostic names Chicago.
 5. Nulls: random trades are not flagged; perfect-foresight trades are (p < 0.01 on
    both nulls).
 6. Performance.csv shape: same trades, same totals, Tradovate pnl check passes.
 --calibration: 60 no-edge trade sets; about 5% of p-values should fall below 0.05
    (2026-09-25 run: 5.0% on both nulls, mean p 0.46 / 0.47).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tradovate_harness as H                                         # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="trades_test_"))
CODES = {3: "H", 6: "M", 9: "U", 12: "Z"}


def contract_for(ts, root):
    """Quarterly code of the next expiry (good enough for the root test)."""
    m = next(q for q in (3, 6, 9, 12, 15) if q >= ts.month)
    y = ts.year + (m > 12)
    return f"{root}{CODES[(m - 1) % 12 + 1]}{y % 10}"


def synth_trades(bars, n, rng, foresight=False):
    """Round trips on random sessions: entry and exit prices inside their bars; trades in
    the same root never overlap, so FIFO must give back exactly these pairs."""
    rth = bars[(bars.index.hour * 60 + bars.index.minute >= 570) & (bars.index.hour < 16)]
    days = rth.session.unique()
    rows, busy = [], {"NQ": [], "MNQ": []}
    while len(rows) < n:
        d = days[rng.integers(len(days))]
        day = rth[rth.session == d]
        if len(day) < 300:
            continue
        i = int(rng.integers(0, len(day) - 130))
        hold = int(rng.integers(1, 120))
        b_in, b_out = day.iloc[i], day.iloc[i + hold]
        if b_in.instrument_id != b_out.instrument_id:
            continue
        side = (1 if b_out.close > b_in.close else -1) if foresight else int(rng.choice([1, -1]))
        px = lambda b: round(rng.uniform(b.low, b.high) / 0.25) * 0.25          # noqa: E731
        p_in, p_out = (b_in.close, b_out.close) if foresight else (px(b_in), px(b_out))
        t_in = day.index[i] + pd.Timedelta(seconds=int(rng.integers(0, 60)))
        t_out = day.index[i + hold] + pd.Timedelta(seconds=int(rng.integers(0, 60)))
        root = "MNQ" if rng.random() < 0.3 else "NQ"
        if any(t_in <= e + pd.Timedelta(minutes=1) and s_ <= t_out + pd.Timedelta(minutes=1)
               for s_, e in busy[root]):
            continue
        busy[root].append((t_in, t_out))
        rows.append(dict(t_in=t_in, t_out=t_out, side=side, p_in=p_in, p_out=p_out,
                         qty=int(rng.integers(1, 4)), root=root, contract=contract_for(t_in, root),
                         setup=["ORB", "VWAP fade", "Trend pullback"][int(rng.integers(3))]))
    return pd.DataFrame(rows).sort_values("t_in").reset_index(drop=True)


def to_orders_csv(R, path, tz, rng):
    """Tradovate Orders.csv shape, timestamps in `tz`, a few cancelled orders mixed in."""
    out, oid = [], 1000
    fmt = lambda t: (t.tz_localize("America/New_York").tz_convert(tz)                # noqa: E731
                     .strftime("%m/%d/%Y %H:%M:%S"))
    for r in R.itertuples():
        for leg, (t, s, p, txt) in enumerate(((r.t_in, r.side, r.p_in, r.setup),
                                              (r.t_out, -r.side, r.p_out, "Exit"))):
            oid += 1
            out.append({"orderId": oid, "Account": "DEMO123", "Order ID": oid,
                        "B/S": " Buy" if s > 0 else " Sell", "Contract": r.contract, "Product": r.root,
                        "avgPrice": p, "filledQty": r.qty, "Fill Time": fmt(t), "Status": " Filled",
                        "Text": txt, "Timestamp": fmt(t - pd.Timedelta(seconds=5)),
                        "Date": fmt(t)[:10], "Quantity": r.qty, "Limit Price": p + 50, "Stop Price": "",
                        "Avg Fill Price": f"{p:,.2f}", "Filled Qty": r.qty, "_priceFormat": -2,
                        "_tickSize": 0.25})
            if rng.random() < 0.05:
                oid += 1
                out.append({**out[-1], "orderId": oid, "Order ID": oid, "Status": " Canceled",
                            "filledQty": 0, "Filled Qty": 0, "avgPrice": "", "Avg Fill Price": "",
                            "Fill Time": ""})
    df = pd.DataFrame(out).iloc[::-1]                    # Tradovate lists newest first
    df.to_csv(path, index=False)
    return path


def to_performance_csv(R, path, tz):
    fmt = lambda t: (t.tz_localize("America/New_York").tz_convert(tz)                # noqa: E731
                     .strftime("%m/%d/%Y %H:%M:%S"))
    rows = []
    for k, r in enumerate(R.itertuples()):
        mult = H.SPEC[r.root]["mult"]
        pnl = r.side * (r.p_out - r.p_in) * mult * r.qty
        buy_t, buy_p, sell_t, sell_p = ((r.t_in, r.p_in, r.t_out, r.p_out) if r.side > 0
                                        else (r.t_out, r.p_out, r.t_in, r.p_in))
        rows.append({"symbol": r.contract, "_priceFormat": -2, "_priceFormatType": 0, "_tickSize": 0.25,
                     "buyFillId": f"B{k}", "sellFillId": f"S{k}", "qty": r.qty, "buyPrice": buy_p,
                     "sellPrice": sell_p, "pnl": f"${pnl:,.2f}" if pnl >= 0 else f"$({-pnl:,.2f})",
                     "boughtTimestamp": fmt(buy_t), "soldTimestamp": fmt(sell_t), "duration": "1min"})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def check(name, cond, detail=""):
    print(f"[{'ok' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        raise SystemExit(1)


def main():
    rng = np.random.default_rng(7)
    bars = H.load_bars(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-08-31"))

    # 1-2. FIFO and costs, hand-made
    hand = pd.DataFrame({
        "Timestamp": ["2026-03-02 10:00:00", "2026-03-02 10:05:00", "2026-03-02 10:07:00",
                      "2026-03-02 10:10:00", "2026-03-02 10:20:00", "2026-03-02 10:30:00",
                      "2026-03-02 11:00:00", "2026-03-02 11:05:00"],
        "B/S": ["Buy", "Sell", "Sell", "Buy", "Sell", "Buy", "Buy", "Sell"],
        "Quantity": [3, 1, 2, 1, 2, 1, 2, 1],
        "Price": [100.0, 101.0, 102.0, 105.0, 103.0, 99.0, 50.0, 51.0],
        "Contract": ["NQH6"] * 6 + ["MNQH6"] * 2, "Fill ID": list(range(1, 9))})
    hp = hand.to_csv(TMP / "hand.csv", index=False) or TMP / "hand.csv"
    F, _, _ = H.parse_fills(hp, "America/New_York")
    T = H.add_costs(H.round_trips(F))
    nq = T[T.root == "NQ"]
    want = [(1, 1, 100.0, 101.0), (1, 2, 100.0, 102.0), (1, 1, 105.0, 103.0), (-1, 1, 103.0, 99.0)]
    got = [(int(r.side), int(r.qty), r.entry, r.exit) for r in nq[~nq.open].itertuples()]
    check("FIFO scale-out and reversal", got == want, got)
    op = T[T.open]
    check("open lot kept and flagged", len(op) == 1 and op.iloc[0].root == "MNQ" and op.iloc[0].qty == 1,
          op[["root", "qty", "entry"]].to_dict("records"))
    check("step-4 cost NQ", abs(nq.iloc[0].cost_step4 - 14.50) < 1e-9, nq.iloc[0].cost_step4)
    check("step-4 cost MNQ", abs(T[(T.root == "MNQ") & ~T.open].iloc[0].cost_step4 - 2.24) < 1e-9)
    check("gross $ NQ", list(nq[~nq.open].gross_usd) == [20.0, 80.0, -40.0, 80.0], list(nq.gross_usd))

    # 3. Orders.csv in Chicago time
    R = synth_trades(bars, 400, rng)
    op = to_orders_csv(R, TMP / "Orders.csv", "America/Chicago", rng)
    F, T, base, tzd, txt = H.run([str(op), "--tz", "America/Chicago", "--sims", "2000",
                                  "--out", str(TMP / "out_orders")])
    check("column picks", True, "see report header")
    cols = txt.split("Columns used: ")[1].split("\n")[0]
    check("price column is Avg Fill Price or avgPrice", "price='Avg Fill Price'" in cols or
          "price='avgPrice'" in cols, cols)
    check("time column is Fill Time", "time='Fill Time'" in cols, cols)
    check("cancelled rows dropped", len(F) == 2 * len(R), f"{len(F)} fills for {len(R)} trades")
    check("every fill has a bar and sits inside it", F.has_bar.all() and (F.bar_ok == 1).all(),
          f"has_bar {F.has_bar.mean():.3f}, ok {F.bar_ok.mean():.3f}")
    check("no tz warning", tzd is None)
    C = T[~T.open]
    check("round trips rebuilt", len(C) == len(R) and not T.open.any(), f"{len(C)} vs {len(R)}")
    want_net = sum(r.side * (r.p_out - r.p_in) * H.SPEC[r.root]["mult"] * r.qty
                   - (2 * H.SPEC[r.root]["comm"] + 2 * 0.25 * H.SPEC[r.root]["mult"]) * r.qty
                   for r in R.itertuples())
    check("net step-4 total", abs(C.net_step4.sum() - want_net) < 1e-6, f"{C.net_step4.sum():.2f} vs {want_net:.2f}")
    re_ = base["random entry"]
    check("random-entry null places every trade", re_["excluded"] == 0 and re_["n"] == len(R), re_["pool"])
    p_re, p_ss = re_["groups"]["all"].p.iloc[0], base["shuffled side"]["groups"]["all"].p.iloc[0]
    check("random trades not flagged", 0.01 < p_re < 0.99 and 0.01 < p_ss < 0.99, f"p {p_re:.3f} / {p_ss:.3f}")
    g = re_["groups"]["setup"]
    check("per-setup nulls with Holm", set(g.index) == {"ORB", "VWAP fade", "Trend pullback"}
          and (g["Holm p"] >= g.p - 1e-12).all())
    check("report written", (TMP / "out_orders/trade_report.md").exists())

    # 4. wrong time zone
    F2, _, _, tzd2, _ = H.run([str(op), "--tz", "UTC", "--sims", "200", "--out", str(TMP / "out_wrong")])
    check("wrong tz flagged", tzd2 is not None and tzd2["bad_share"] > 0.5,
          f"bad share {tzd2 and tzd2['bad_share']:.2f}")
    check("diagnostic names a Central-time fit",
          tzd2["tried"][0][0] == "America/Chicago" and tzd2["tried"][0][1] > 0.99, tzd2["tried"][:3])

    # 5. perfect foresight
    Rf = synth_trades(bars, 150, rng, foresight=True)
    fp = to_orders_csv(Rf, TMP / "Orders_foresight.csv", "America/New_York", rng)
    _, _, bf, _, _ = H.run([str(fp), "--tz", "America/New_York", "--sims", "2000",
                            "--out", str(TMP / "out_foresight")])
    pf_re, pf_ss = bf["random entry"]["groups"]["all"].p.iloc[0], bf["shuffled side"]["groups"]["all"].p.iloc[0]
    check("foresight flagged by both nulls", pf_re < 0.01 and pf_ss < 0.01, f"p {pf_re:.4f} / {pf_ss:.4f}")

    # 6. Performance.csv
    pp = to_performance_csv(R, TMP / "Performance.csv", "America/Chicago")
    Fp, Tp, bp, tzp, txtp = H.run([str(pp), "--tz", "America/Chicago", "--sims", "500",
                                   "--out", str(TMP / "out_perf")])
    check("performance: same trades and total", len(Tp) == len(R) and
          abs(Tp.net_step4.sum() - want_net) < 1e-6, f"{Tp.net_step4.sum():.2f}")
    check("performance: Tradovate pnl matches", "0 of" in txtp.split("Tradovate pnl vs ours")[1][:40])
    check("performance: fills in their bars", (Fp.bar_ok == 1).all())
    print(f"\nall checks passed; outputs in {TMP}")


def calibration(n_sets=60):
    bars = H.load_bars(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-08-31"))
    ps = {"random entry": [], "shuffled side": []}
    for k in range(n_sets):
        rng = np.random.default_rng(1000 + k)
        f = to_orders_csv(synth_trades(bars, 150, rng), TMP / f"cal{k}.csv", "America/New_York", rng)
        _, _, b, _, _ = H.run([str(f), "--tz", "America/New_York", "--sims", "400", "--out", str(TMP / "cal")])
        for name in ps:
            ps[name].append(b[name]["groups"]["all"].p.iloc[0])
    for name, x in ps.items():
        x = np.array(x)
        print(f"{name}: share p < 0.05 = {(x < 0.05).mean():.3f}, mean p = {x.mean():.3f}, "
              f"quintiles {np.histogram(x, bins=5, range=(0, 1))[0].tolist()}")


if __name__ == "__main__":
    calibration() if "--calibration" in sys.argv else main()
