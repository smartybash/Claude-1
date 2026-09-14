"""Inventory Retracement Bar (IRB, Rob Hoffman) backtest — honest, null-baselined.

QUESTION: does the IRB continuation setup have an edge, and at what timeframe?

PRE-REGISTERED DEFINITION (Hoffman), tested as-is — no shape tuning:
  range r = high - low (skip r==0).
  * LONG IRB  (uptrend):  body has retraced >=45% below the high, i.e. the whole
      real body sits in the lower part with a big trend-side (upper) wick:
          (high - max(open,close)) >= 0.45 * r
      trade = BUY-stop 1 tick above the bar HIGH; hard stop = bar LOW.
  * SHORT IRB (downtrend): mirror —
          (min(open,close) - low) >= 0.45 * r
      trade = SELL-stop below bar LOW; hard stop = bar HIGH.
  TREND FILTER (Hoffman uses an EMA): EMA20 on the series' own bars —
      up   = close > ema20 and ema20 rising over the last 3 bars
      down = close < ema20 and ema20 falling
  Only long IRBs in an uptrend, short IRBs in a downtrend.

MECHANICS (matches the repo's other backtests: intrabar H/L, stop-first tie):
  * fill: the entry stop must be breached within the next FILL_BARS bars (else
    no trade). Fill assumed AT the level (no slippage/costs modelled — caveat).
  * outcome: risk R = |entry - stop|. Symmetric test — reach +1R before -1R
    within HOLD bars = WIN, -1R first = LOSS, neither = flat/undecided (dropped
    from the win-rate, reported separately). Expectancy also reported at
    target = 1R / 1.5R / 2R with the same 1R stop.
  * intraday: detection, fill and resolution all stay inside one RTH session
    (09:30-16:00 ET). Daily series run continuously.

NULL (the honest control): same trade mechanics (break of a bar's trend-side
extreme, opposite-side stop, same targets) on RANDOM bars that pass ONLY the
trend filter — NOT the IRB shape. Same count and same long/short split per
series. If IRB ~= null, the candle shape adds nothing beyond "trend + break".

Scope caveat: correlated equity-index instruments; intraday windows ~1-2
months, daily ~5y (QQQ/SPY). A real sample, not multi-year-independent per TF.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ET = "America/New_York"
X = 0.45           # IRB body-retracement threshold
EMA_LEN = 20
FILL_BARS = 3      # entry stop must trigger within this many bars
HOLD = 20          # bars allowed to reach +1R / -1R after fill
RNG = np.random.default_rng(20260805)

# (file, instrument, timeframe-bucket, is_intraday)
SERIES = [
    ("qqq_daily_5y.json", "QQQ", "1D", False),
    ("spy_daily_5y.json", "SPY", "1D", False),
    ("nq_daily_3m.json",  "NQ",  "1D", False),
    ("es_daily_3m.json",  "ES",  "1D", False),
    ("nq_1h.json",  "NQ", "1h", True), ("es_1h.json", "ES", "1h", True),
    ("qqq_1h.json", "QQQ", "1h", True), ("spy_1h.json", "SPY", "1h", True),
    ("nq_30min.json", "NQ", "30m", True), ("es_30min.json", "ES", "30m", True),
    ("qqq_30min.json", "QQQ", "30m", True), ("spy_30min.json", "SPY", "30m", True),
    ("qqq_15min.json", "QQQ", "15m", True), ("spy_15min.json", "SPY", "15m", True),
    ("nq_5min_rth.json", "NQ", "5m", True), ("es_5min_rth.json", "ES", "5m", True),
    ("qqq_5min_rth.json", "QQQ", "5m", True), ("spy_5min_rth.json", "SPY", "5m", True),
]
TF_ORDER = ["5m", "15m", "30m", "1h", "1D"]


def load(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def prep(df, intraday):
    """RTH-filter (intraday), add EMA20 + trend state + session id."""
    if intraday:
        t = df.index.time
        df = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
        sess = pd.Series(df.index.date, index=df.index)
    else:
        df = df.copy()
        sess = pd.Series(df.index.date, index=df.index)
    df["ema"] = df["close"].ewm(span=EMA_LEN, adjust=False).mean()
    rising = df["ema"] > df["ema"].shift(3)
    df["trend"] = np.where((df["close"] > df["ema"]) & rising, 1,
                    np.where((df["close"] < df["ema"]) & (~rising) & (df["ema"] < df["ema"].shift(3)), -1, 0))
    df["sess"] = pd.to_datetime(sess.values)
    return df.reset_index(drop=True)


INV = False   # False = canonical Hoffman (body retraced vs trend); True = inverse-wick variant


def is_irb(o, h, l, c, direction):
    r = h - l
    if r <= 0:
        return False
    if not INV:
        if direction == 1:                   # long: body in lower 55%, big upper wick
            return (h - max(o, c)) >= X * r
        return (min(o, c) - l) >= X * r      # short: body in upper 55%, big lower wick
    # inverse variant: long = big LOWER wick (rejection of lows), short = big upper wick
    if direction == 1:
        return (min(o, c) - l) >= X * r
    return (h - max(o, c)) >= X * r


def simulate(g, i, direction):
    """Given entry-signal bar index i (within session frame g), return
    ('R at 1R target', reached_r dict) or None if never filled.
    Returns dict(filled, win1, r15_win, r20_win) or None."""
    hi, lo = g["high"].values, g["low"].values
    n = len(g)
    if direction == 1:
        entry = hi[i]; stop = lo[i]
    else:
        entry = lo[i]; stop = hi[i]
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    # fill: breach of entry within FILL_BARS
    fill_j = None
    for j in range(i + 1, min(i + 1 + FILL_BARS, n)):
        if (direction == 1 and hi[j] >= entry) or (direction == -1 and lo[j] <= entry):
            fill_j = j
            break
    if fill_j is None:
        return None
    # resolve outcomes for target multiples with a 1R stop; stop-first on ties
    targets = {"1R": 1.0, "1.5R": 1.5, "2R": 2.0}
    res = {"filled": True}
    for name, k in targets.items():
        if direction == 1:
            tgt = entry + k * risk; stp = entry - risk
        else:
            tgt = entry - k * risk; stp = entry + risk
        outcome = None
        for j in range(fill_j, min(fill_j + HOLD, n)):
            hit_stop = (lo[j] <= stp) if direction == 1 else (hi[j] >= stp)
            hit_tgt = (hi[j] >= tgt) if direction == 1 else (lo[j] <= tgt)
            if hit_stop:                     # conservative: stop resolves first
                outcome = False; break
            if hit_tgt:
                outcome = True; break
        res[name] = outcome                  # True win / False loss / None undecided
    return res


def process_frame(g, lo_i, hi_i, collect_null):
    """Detect IRBs + build the trend-matched null on one bar frame g, scanning
    entry-signal indices in [lo_i, hi_i). Resolution stays inside g."""
    o, h, l, c = g["open"].values, g["high"].values, g["low"].values, g["close"].values
    tr = g["trend"].values
    ev, idxs = [], []
    for i in range(lo_i, hi_i):
        d = tr[i]
        if d == 0:
            continue
        if is_irb(o[i], h[i], l[i], c[i], d):
            r = simulate(g, i, d)
            if r:
                ev.append({"dir": d, **{k: r[k] for k in ("1R", "1.5R", "2R")}})
                idxs.append((i, d))
    nullev = []
    if collect_null and idxs:
        longs = sum(1 for _, d in idxs if d == 1)
        for d, cnt in ((1, longs), (-1, len(idxs) - longs)):
            if cnt <= 0:
                continue
            pool = [i for i in range(lo_i, hi_i)
                    if tr[i] == d and not is_irb(o[i], h[i], l[i], c[i], d)]
            if not pool:
                continue
            for i in np.atleast_1d(RNG.choice(pool, size=min(cnt, len(pool)), replace=False)):
                r = simulate(g, int(i), d)
                if r:
                    nullev.append({"dir": d, **{k: r[k] for k in ("1R", "1.5R", "2R")}})
    return ev, nullev


def run_series(fname, intraday, collect_null=True):
    df = prep(load(fname), intraday)
    df.iloc[:EMA_LEN, df.columns.get_loc("trend")] = 0   # EMA warmup: unreliable
    ev, nullev = [], []
    if intraday:
        # keep entries + resolution inside one RTH session (no overnight holding)
        for _, g in df.groupby("sess", sort=True):
            g = g.reset_index(drop=True)
            n = len(g)
            if n < FILL_BARS + 3:
                continue
            e, x = process_frame(g, 0, n - FILL_BARS - 1, collect_null)
            ev += e; nullev += x
    else:
        g = df.reset_index(drop=True)
        n = len(g)
        e, x = process_frame(g, EMA_LEN, n - FILL_BARS - 1, collect_null)
        ev += e; nullev += x
    return ev, nullev


def wr(events, key):
    v = [e[key] for e in events if e[key] is not None]
    n = len(v); w = sum(v)
    return (w / n if n else float("nan")), n


def expectancy(events, key, k):
    """E[R] treating win=+k, loss=-1, undecided=0 (flat exit)."""
    n = len(events)
    if not n:
        return float("nan")
    tot = 0.0
    for e in events:
        if e[key] is True: tot += k
        elif e[key] is False: tot += -1.0
    return tot / n


def main():
    by_tf = {}
    for fname, inst, tf, intraday in SERIES:
        try:
            ev, nl = run_series(fname, intraday)
        except FileNotFoundError:
            continue
        by_tf.setdefault(tf, {"ev": [], "nl": []})
        by_tf[tf]["ev"] += ev
        by_tf[tf]["nl"] += nl

    print("INVENTORY RETRACEMENT BAR (IRB) BACKTEST — pooled equity-index instruments")
    print(f"def: body retraced >={X:.0%} vs trend (EMA{EMA_LEN}); enter break of trend-side extreme,")
    print("stop = opposite extreme; symmetric +1R-before--1R = win; stop-first on ties.\n")
    hdr = f"{'TF':>4} | {'signals':>7} {'fill%':>6} | {'IRB win@1R':>16} | {'NULL win@1R':>14} | {'edge':>6} | {'E[R]@1R/1.5R/2R (IRB)':>22}"
    print(hdr); print("-" * len(hdr))
    rows = []
    for tf in TF_ORDER:
        if tf not in by_tf:
            continue
        ev, nl = by_tf[tf]["ev"], by_tf[tf]["nl"]
        # fill% = filled events / (attempted signals). Every ev is a filled trade;
        # attempted = filled + unfilled — we only kept filled, so approximate fill%
        # via ratio of resolved. Report n filled trades instead (cleaner).
        p, n = wr(ev, "1R")
        pn, nn = wr(nl, "1R")
        se = (p * (1 - p) / n) ** 0.5 if n else 0
        e1 = expectancy(ev, "1R", 1.0); e15 = expectancy(ev, "1.5R", 1.5); e2 = expectancy(ev, "2R", 2.0)
        edge = (p - pn) if (n and nn) else float("nan")
        print(f"{tf:>4} | {n:>7} {'—':>6} | {p:>6.0%} +/-{1.96*se:>4.0%} (n={n:>4}) | "
              f"{pn:>5.0%} (n={nn:>4}) | {edge:>+5.0%} | {e1:>+6.2f} / {e15:>+6.2f} / {e2:>+6.2f}")
        rows.append((tf, p, pn, n, e1, e15, e2))

    # pooled all-TF
    allev = [e for tf in by_tf for e in by_tf[tf]["ev"]]
    allnl = [e for tf in by_tf for e in by_tf[tf]["nl"]]
    p, n = wr(allev, "1R"); pn, nn = wr(allnl, "1R")
    print("-" * len(hdr))
    print(f"{'ALL':>4} | {n:>7} {'—':>6} | {p:>6.0%}         (n={n:>4}) | {pn:>5.0%} (n={nn:>4}) | "
          f"{p-pn:>+5.0%} | {expectancy(allev,'1R',1.0):>+6.2f} / {expectancy(allev,'1.5R',1.5):>+6.2f} / {expectancy(allev,'2R',2.0):>+6.2f}")

    print("\nread: 'win@1R' = P(reach +1R before -1R). null = same break-of-bar trade on random")
    print("trend-aligned bars (no IRB shape). edge = IRB - null. E[R] = expectancy per trade in R.")
    _verdict(rows, p, pn)
    _chart(rows)

    # ROBUSTNESS: inverse-wick variant (rules out a merely mis-signed pattern)
    global INV
    INV = True
    inv_tf = {}
    for fname, inst, tf, intraday in SERIES:
        try:
            ev, nl = run_series(fname, intraday)
        except FileNotFoundError:
            continue
        inv_tf.setdefault(tf, {"ev": [], "nl": []})
        inv_tf[tf]["ev"] += ev; inv_tf[tf]["nl"] += nl
    INV = False
    print("\nROBUSTNESS — INVERSE-wick variant (long=big lower wick / short=big upper wick):")
    for tf in TF_ORDER:
        if tf not in inv_tf:
            continue
        p2, n2 = wr(inv_tf[tf]["ev"], "1R"); pn2, _ = wr(inv_tf[tf]["nl"], "1R")
        e = expectancy(inv_tf[tf]["ev"], "1.5R", 1.5)
        print(f"  {tf:>3}: win@1R {p2:.0%} vs null {pn2:.0%} (edge {p2-pn2:+.0%}, E[R]@1.5R {e:+.2f}, n={n2})")


def _verdict(rows, p_all, pn_all):
    print("\nVERDICT:")
    best = None
    for tf, p, pn, n, e1, e15, e2 in rows:
        edge = p - pn
        best_e = max(e1, e15, e2)
        tag = "EDGE" if (edge >= 0.05 and n >= 40 and best_e > 0.05) else \
              ("weak" if edge >= 0.03 and best_e > 0 else "no edge")
        print(f"  {tf:>3}: {tag:8s} (IRB {p:.0%} vs null {pn:.0%}, best E[R] {best_e:+.2f} over n={n})")
        if tag == "EDGE" and (best is None or (p - pn) > best[1]):
            best = (tf, p - pn)
    if best:
        print(f"  -> Best-supported timeframe: {best[0]}.")
    else:
        print("  -> No timeframe clears the bar (edge>=+5pts vs null, n>=40, E[R]>+0.05). "
              "IRB adds little beyond trend + break-of-bar on this sample.")


def _chart(rows):
    if not rows:
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tfs = [r[0] for r in rows]
    irb = [r[1] * 100 for r in rows]
    null = [r[2] * 100 for r in rows]
    ns = [r[3] for r in rows]
    x = np.arange(len(tfs)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 6))
    b1 = ax.bar(x - w / 2, irb, w, label="IRB win@1R", color="#26a69a")
    b2 = ax.bar(x + w / 2, null, w, label="null (trend+break)", color="#b0bec5")
    ax.axhline(50, color="#455a64", lw=1, ls="--", label="coin flip 50%")
    for xi, (v, n) in enumerate(zip(irb, ns)):
        ax.text(xi - w / 2, v + 0.6, f"{v:.0f}%\nn={n}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(tfs)
    ax.set_ylabel("win rate: reach +1R before -1R (%)")
    ax.set_title("Inventory Retracement Bar — win@1R vs trend-matched null, by timeframe\n"
                 "(pooled NQ/ES/QQQ/SPY; stop=bar extreme, symmetric 1R)", fontsize=11)
    ax.legend(); ax.grid(axis="y", alpha=0.2)
    ax.set_ylim(0, max(max(irb), max(null), 55) + 8)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "irb_backtest.png"
    plt.savefig(out, dpi=110, bbox_inches="tight")
    print(f"\nchart -> {out}")


if __name__ == "__main__":
    main()
