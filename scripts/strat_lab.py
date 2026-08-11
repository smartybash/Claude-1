#!/usr/bin/env python3
"""strat_lab — one consistent engine to sweep simple daily strategies.

Execution model (no lookahead):
  * a strategy emits a target position for each bar using data through that
    bar's CLOSE (long-only: 0/1, long-short: -1/0/+1);
  * the position is shifted one bar, so it earns the NEXT day's close-to-close
    return — you cannot trade on a bar you haven't seen yet;
  * turnover (|Δposition|) is charged cost_bps per unit per side.

Same engine, same costs for every strategy so the numbers are comparable.
Usage:  python3 scripts/strat_lab.py [path_to_daily_json] [--cost 1.0]
"""
import sys, json, math
import numpy as np, pandas as pd

COST_BPS = 1.0  # one-way cost in basis points applied to turnover


# ----------------------------- data -----------------------------------------
def load_daily(path):
    """Load the repo's daily chart JSON (arrays) OR a generic OHLC CSV."""
    if path.endswith(".json"):
        d = json.load(open(path))
        df = pd.DataFrame({
            "t": pd.to_datetime(d["time"]),
            "open": d["open"], "high": d["high"],
            "low": d["low"], "close": d["close"], "volume": d["volume"],
        }).dropna().reset_index(drop=True)
    else:
        df = pd.read_csv(path)
        df.columns = [c.lower() for c in df.columns]
        tcol = "date" if "date" in df.columns else ("t" if "t" in df.columns else df.columns[0])
        df["t"] = pd.to_datetime(df[tcol])
        df = df[["t", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
    return df


# ----------------------------- indicators -----------------------------------
def ema(s, n):  return s.ewm(span=n, adjust=False).mean()
def sma(s, n):  return s.rolling(n).mean()

def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def laguerre_rsi(s, gamma=0.5):
    p = s.values; n = len(p)
    L0 = L1 = L2 = L3 = 0.0
    out = np.full(n, np.nan)
    for i in range(n):
        pr = p[i]
        L0p, L1p, L2p, L3p = L0, L1, L2, L3
        L0 = (1 - gamma) * pr + gamma * L0p
        L1 = -gamma * L0 + L0p + gamma * L1p
        L2 = -gamma * L1 + L1p + gamma * L2p
        L3 = -gamma * L2 + L2p + gamma * L3p
        cu = (max(L0 - L1, 0) + max(L1 - L2, 0) + max(L2 - L3, 0))
        cd = (max(L1 - L0, 0) + max(L2 - L1, 0) + max(L3 - L2, 0))
        tot = cu + cd
        out[i] = cu / tot if tot != 0 else 0.5
    return pd.Series(out, index=s.index)

def atr(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()


# ----------------------------- strategies -----------------------------------
# each returns a target-position Series (index aligned to df); NaN -> flat.
def strat_buyhold(df):
    return pd.Series(1.0, index=df.index)

def strat_sma_cross(df, fast=50, slow=200, short=False):
    f, s = sma(df.close, fast), sma(df.close, slow)
    pos = np.where(f > s, 1.0, (-1.0 if short else 0.0))
    return pd.Series(pos, index=df.index).where(s.notna())

def strat_ema_cross(df, fast=12, slow=26, short=False):
    f, s = ema(df.close, fast), ema(df.close, slow)
    pos = np.where(f > s, 1.0, (-1.0 if short else 0.0))
    return pd.Series(pos, index=df.index)

def strat_macd(df, short=False):
    macd = ema(df.close, 12) - ema(df.close, 26)
    sig = ema(macd, 9)
    pos = np.where(macd > sig, 1.0, (-1.0 if short else 0.0))
    return pd.Series(pos, index=df.index)

def strat_rsi_meanrev(df, n=14, lo=30, exit=50):
    r = rsi(df.close, n); pos = np.zeros(len(df)); held = 0.0
    rv = r.values
    for i in range(len(df)):
        if np.isnan(rv[i]): pos[i] = 0; continue
        if held == 0 and rv[i] < lo: held = 1.0
        elif held == 1 and rv[i] > exit: held = 0.0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_rsi_trend(df, n=14, short=False):
    r = rsi(df.close, n)
    pos = np.where(r > 50, 1.0, (-1.0 if short else 0.0))
    return pd.Series(pos, index=df.index).where(r.notna())

def strat_lrsi(df, gamma=0.5):
    lr = laguerre_rsi(df.close, gamma)
    pos = np.where(lr > 0.5, 1.0, 0.0)
    return pd.Series(pos, index=df.index)

def strat_donchian(df, entry=20, exit=10, short=False):
    hh = df.high.rolling(entry).max().shift(1)
    ll = df.low.rolling(exit).min().shift(1)
    pos = np.zeros(len(df)); held = 0.0
    c, h_, l_ = df.close.values, hh.values, ll.values
    for i in range(len(df)):
        if np.isnan(h_[i]): pos[i] = 0; continue
        if held == 0 and c[i] > h_[i]: held = 1.0
        elif held == 1 and c[i] < l_[i]: held = 0.0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_keltner(df, n=20, mult=1.5):
    mid = ema(df.close, n); band = mult * atr(df, n)
    up, dn = mid + band, mid - band
    pos = np.zeros(len(df)); held = 0.0
    c, u, d = df.close.values, up.values, dn.values
    for i in range(len(df)):
        if np.isnan(u[i]): pos[i] = 0; continue
        if held == 0 and c[i] > u[i]: held = 1.0
        elif held == 1 and c[i] < mid.values[i]: held = 0.0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_sma_regime(df, n=200):
    s = sma(df.close, n)
    return pd.Series(np.where(df.close > s, 1.0, 0.0), index=df.index).where(s.notna())

def strat_boll_meanrev(df, n=20, k=2.0, short=False):
    mid = sma(df.close, n); sd = df.close.rolling(n).std()
    z = (df.close - mid) / sd
    pos = np.zeros(len(df)); held = 0.0
    zv = z.values
    for i in range(len(df)):
        if np.isnan(zv[i]): pos[i] = 0; continue
        if held == 0 and zv[i] < -k: held = 1.0
        elif held == 0 and short and zv[i] > k: held = -1.0
        elif held == 1 and zv[i] >= 0: held = 0.0
        elif held == -1 and zv[i] <= 0: held = 0.0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_nr7(df):
    rng = df.high - df.low
    nr7 = rng == rng.rolling(7).min()
    trig = df.high.where(nr7).shift(1)  # break of the NR7 bar's high next day
    pos = np.zeros(len(df)); held = 0.0; days = 0
    c = df.close.values; tv = trig.values
    for i in range(len(df)):
        if held == 1:
            days += 1
            if days >= 5: held = 0.0; days = 0
        if held == 0 and not np.isnan(tv[i]) and c[i] > tv[i]:
            held = 1.0; days = 0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_engulfing(df, hold=5):
    o, c = df.open.values, df.close.values
    bull = np.zeros(len(df), bool)
    for i in range(1, len(df)):
        bull[i] = (c[i-1] < o[i-1]) and (c[i] > o[i]) and (c[i] >= o[i-1]) and (o[i] <= c[i-1])
    pos = np.zeros(len(df)); held = 0.0; days = 0
    for i in range(len(df)):
        if held == 1:
            days += 1
            if days >= hold: held = 0.0; days = 0
        if held == 0 and bull[i]: held = 1.0; days = 0
        pos[i] = held
    return pd.Series(pos, index=df.index)

def strat_grid(df, step=0.03, maxunits=4):
    """Buy-dips grid: add a unit each `step` below the running 20d high,
    scale out as price recovers. Net exposure in [0, maxunits]/maxunits."""
    ref = df.high.rolling(20).max()
    units = 0.0; pos = np.zeros(len(df))
    c, r = df.close.values, ref.values
    for i in range(len(df)):
        if np.isnan(r[i]): pos[i] = 0; continue
        drop = (r[i] - c[i]) / r[i]
        target = min(maxunits, max(0, math.floor(drop / step)))
        units = target
        pos[i] = units / maxunits
    return pd.Series(pos, index=df.index)


# ----------------------------- engine ---------------------------------------
def run(df, pos, cost_bps=COST_BPS):
    ret = df.close.pct_change().fillna(0).values
    p = pos.reindex(df.index).fillna(0).clip(-1, 1).values
    p_eff = np.concatenate([[0], p[:-1]])            # shift: act next bar
    turn = np.abs(np.diff(np.concatenate([[0], p])))
    cost = turn * cost_bps / 1e4
    r = p_eff * ret - cost
    eq = np.cumprod(1 + r)
    n = len(r)
    yrs = n / 252
    cagr = eq[-1] ** (1 / yrs) - 1 if eq[-1] > 0 else -1
    vol = r.std() * math.sqrt(252)
    sharpe = (r.mean() * 252) / vol if vol > 0 else 0
    dn = r[r < 0].std() * math.sqrt(252)
    sortino = (r.mean() * 252) / dn if dn > 0 else 0
    peak = np.maximum.accumulate(eq); dd = (eq / peak - 1).min()
    expo = np.abs(p_eff).mean()
    # trade extraction (contiguous constant-nonzero sign runs)
    trades = []; i = 0
    while i < n:
        if p_eff[i] == 0: i += 1; continue
        j = i
        while j < n and p_eff[j] == p_eff[i]: j += 1
        seg = r[i:j]
        trades.append(np.prod(1 + seg) - 1)
        i = j
    trades = np.array(trades)
    nt = len(trades)
    win = (trades > 0).mean() * 100 if nt else 0
    return dict(cagr=cagr*100, sharpe=sharpe, sortino=sortino, maxdd=dd*100,
                expo=expo*100, ntr=nt, win=win, fin=eq[-1])


STRATS = [
    ("BuyHold",              strat_buyhold),
    ("SMA 50/200 LO",        lambda d: strat_sma_cross(d, 50, 200)),
    ("SMA 50/200 L/S",       lambda d: strat_sma_cross(d, 50, 200, short=True)),
    ("EMA 12/26 LO",         lambda d: strat_ema_cross(d, 12, 26)),
    ("EMA 12/26 L/S",        lambda d: strat_ema_cross(d, 12, 26, short=True)),
    ("MACD LO",              lambda d: strat_macd(d)),
    ("MACD L/S",             lambda d: strat_macd(d, short=True)),
    ("RSI14 mean-rev LO",    lambda d: strat_rsi_meanrev(d)),
    ("RSI14 trend LO",       lambda d: strat_rsi_trend(d)),
    ("RSI14 trend L/S",      lambda d: strat_rsi_trend(d, short=True)),
    ("Laguerre RSI LO",      lambda d: strat_lrsi(d)),
    ("Donchian 20/10 LO",    lambda d: strat_donchian(d)),
    ("Keltner ATR brk LO",   lambda d: strat_keltner(d)),
    ("SMA50 regime LO",      lambda d: strat_sma_regime(d, 50)),
    ("SMA100 regime LO",     lambda d: strat_sma_regime(d, 100)),
    ("SMA200 regime LO",     lambda d: strat_sma_regime(d, 200)),
    ("Bollinger z mean-rev", lambda d: strat_boll_meanrev(d)),
    ("Bollinger z L/S",      lambda d: strat_boll_meanrev(d, short=True)),
    ("NR7 compress brk LO",  strat_nr7),
    ("Bull engulf LO",       strat_engulfing),
    ("Grid buy-dips LO",     strat_grid),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "data/qqq_daily_5y.json"
    cost = COST_BPS
    if "--cost" in sys.argv: cost = float(sys.argv[sys.argv.index("--cost")+1])
    df = load_daily(path)
    label = path.split("/")[-1]
    print(f"\n=== strat_lab: {label}  |  {len(df)} bars  {df.t.iloc[0].date()} -> {df.t.iloc[-1].date()}  |  cost {cost}bp/side ===\n")
    hdr = f"{'strategy':22} {'CAGR%':>7} {'Sharpe':>7} {'Sortino':>8} {'MaxDD%':>8} {'Expo%':>6} {'#tr':>5} {'win%':>6}"
    print(hdr); print("-"*len(hdr))
    rows = []
    for name, fn in STRATS:
        try:
            m = run(df, fn(df), cost)
            rows.append((name, m))
        except Exception as e:
            print(f"{name:22}  ERROR {e}")
    bh = dict(rows)["BuyHold"]["sharpe"]
    for name, m in sorted(rows, key=lambda x: -x[1]["sharpe"]):
        flag = " *" if m["sharpe"] > bh and name != "BuyHold" else ""
        print(f"{name:22} {m['cagr']:7.1f} {m['sharpe']:7.2f} {m['sortino']:8.2f} "
              f"{m['maxdd']:8.1f} {m['expo']:6.0f} {m['ntr']:5d} {m['win']:6.0f}{flag}")
    print(f"\n  (* = higher Sharpe than Buy&Hold={bh:.2f}.  LO=long-only, L/S=long-short.)")


if __name__ == "__main__":
    main()
