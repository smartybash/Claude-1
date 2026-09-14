#!/usr/bin/env python3
"""strat_lab2 — Tier-2 multi-asset strategies on the sector basket.

Universe: 9 SPDR sectors (XLK/XLF/XLE/XLV/XLY/XLP/XLI/XLU/XLB), SPY, QQQ.
Same discipline as strat_lab: signals use data through close[t], weights are
shifted one day (act next bar), turnover charged cost_bps/side. All metrics
are return-based so IBKR's constant dividend back-adjustment is irrelevant.

Strategies:
  * Sector momentum rotation (top-K, monthly), lookbacks 63/126d
  * Dual momentum (rotation + absolute-momentum cash filter = 'market timing')
  * Equal-weight-9 and SPY buy&hold benchmarks
  * Pairs (market-neutral z-score): SPY/QQQ and XLK/XLF
"""
import glob, math
import numpy as np, pandas as pd

COST_BPS = 1.0
SECTORS = ["XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLU","XLB"]


def load_close():
    px = {}
    for f in glob.glob("data/basket/*.csv"):
        sym = f.split("/")[-1][:-4]
        d = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        px[sym] = d.close
    # QQQ from the repo JSON
    import json
    q = json.load(open("data/qqq_daily_5y.json"))
    qidx = pd.to_datetime(q["time"]).tz_localize(None).normalize()
    px["QQQ"] = pd.Series(q["close"], index=qidx)
    df = pd.DataFrame(px).sort_index()
    df.index = df.index.normalize()
    return df.dropna(how="all")


def metrics(r):
    r = np.asarray(r); r = r[~np.isnan(r)]
    eq = np.cumprod(1 + r); n = len(r); yrs = n / 252
    cagr = eq[-1] ** (1/yrs) - 1 if eq[-1] > 0 else -1
    vol = r.std() * math.sqrt(252); shp = (r.mean()*252)/vol if vol > 0 else 0
    dn = r[r < 0].std() * math.sqrt(252); srt = (r.mean()*252)/dn if dn > 0 else 0
    peak = np.maximum.accumulate(eq); dd = (eq/peak - 1).min()
    return dict(cagr=cagr*100, sharpe=shp, sortino=srt, maxdd=dd*100, fin=eq[-1])


def sim_weights(px, W, cost_bps=COST_BPS):
    """W: daily target-weight frame (cols subset of px). Returns daily pnl."""
    cols = list(W.columns)
    rets = px[cols].pct_change().fillna(0.0)
    Weff = W.shift(1).fillna(0.0)                      # act next bar
    turn = (W.fillna(0.0) - W.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost = turn * cost_bps / 1e4
    pnl = (Weff * rets).sum(axis=1) - cost
    return pnl


def rotation(px, lookback=126, k=3, dual=False):
    close = px[SECTORS]
    mom = close / close.shift(lookback) - 1
    me = close.resample("ME").last().index               # month-end rebalance
    W = pd.DataFrame(0.0, index=close.index, columns=SECTORS)
    for dt in me:
        sub = close.index[close.index <= dt]
        if len(sub) == 0: continue
        d = sub[-1]
        m = mom.loc[d].dropna()
        if m.empty: continue
        top = m.sort_values(ascending=False).head(k).index
        w = {}
        for s in top:
            if dual and m[s] <= 0:      # absolute-momentum filter -> cash
                continue
            w[s] = 1.0 / k
        W.loc[d:, :] = 0.0
        for s, wt in w.items(): W.loc[d:, s] = wt
    return sim_weights(px, W)


def equal_weight(px):
    W = pd.DataFrame(1.0/len(SECTORS), index=px.index, columns=SECTORS)
    return sim_weights(px, W)


def buyhold(px, sym):
    W = pd.DataFrame({sym: 1.0}, index=px.index)
    return sim_weights(px, W)


def pairs(px, a, b, win=60, entry=2.0, exit=0.5, cost_bps=COST_BPS):
    A, B = np.log(px[a]), np.log(px[b])
    spread = A - B
    z = (spread - spread.rolling(win).mean()) / spread.rolling(win).std()
    pos = np.zeros(len(z)); held = 0.0; zv = z.values
    for i in range(len(z)):
        if np.isnan(zv[i]): pos[i] = 0; continue
        if held == 0:
            if zv[i] > entry: held = -1.0      # short A / long B
            elif zv[i] < -entry: held = 1.0    # long A / short B
        elif held == 1 and zv[i] >= -exit: held = 0.0
        elif held == -1 and zv[i] <= exit: held = 0.0
        pos[i] = held
    pos = pd.Series(pos, index=z.index)
    ra, rb = px[a].pct_change().fillna(0), px[b].pct_change().fillna(0)
    peff = pos.shift(1).fillna(0)
    gross = 0.5
    turn = (pos - pos.shift(1)).abs().fillna(0) * 2 * gross
    pnl = peff * gross * ra - peff * gross * rb - turn * cost_bps/1e4
    nt = int(((pos != 0) & (pos.shift(1) == 0)).sum())
    return pnl, nt


def main():
    px = load_close()
    print(f"\n=== strat_lab2 (Tier-2)  |  {px.index[0].date()} -> {px.index[-1].date()}  "
          f"|  {len(px)} bars  |  cost {COST_BPS}bp/side ===\n")
    runs = []
    runs.append(("SPY buy&hold",            buyhold(px, "SPY")))
    runs.append(("QQQ buy&hold",            buyhold(px, "QQQ")))
    runs.append(("Equal-weight 9 sectors",  equal_weight(px)))
    for lb in (63, 126):
        for k in (1, 2, 3):
            runs.append((f"Rotation top{k} L{lb}",      rotation(px, lb, k)))
        runs.append((f"Dual-mom top3 L{lb}",            rotation(px, lb, 3, dual=True)))
    hdr = f"{'strategy':26} {'CAGR%':>7} {'Sharpe':>7} {'Sortino':>8} {'MaxDD%':>8}"
    print(hdr); print("-"*len(hdr))
    spy_shp = metrics(runs[0][1])["sharpe"]
    rows = [(n, metrics(p)) for n, p in runs]
    for n, m in sorted(rows, key=lambda x: -x[1]["sharpe"]):
        flag = " *" if m["sharpe"] > spy_shp and "buy&hold" not in n else ""
        print(f"{n:26} {m['cagr']:7.1f} {m['sharpe']:7.2f} {m['sortino']:8.2f} {m['maxdd']:8.1f}{flag}")

    print(f"\n  Pairs (market-neutral, long/short, gross~1.0):")
    print(f"  {'pair':16} {'CAGR%':>7} {'Sharpe':>7} {'MaxDD%':>8} {'#tr':>5}")
    for a, b in [("SPY","QQQ"), ("XLK","XLF"), ("XLE","XLB")]:
        pnl, nt = pairs(px, a, b)
        m = metrics(pnl.values)
        print(f"  {a+'/'+b:16} {m['cagr']:7.1f} {m['sharpe']:7.2f} {m['maxdd']:8.1f} {nt:5d}")
    print(f"\n  (* = beats SPY buy&hold Sharpe={spy_shp:.2f}. Rotation = monthly, equal-weight top-K by trailing return.)")


if __name__ == "__main__":
    main()
