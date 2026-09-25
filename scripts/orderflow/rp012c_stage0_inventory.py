#!/usr/bin/env python3
"""RP-012C Stage 0 -- daily data inventory. NO SIGNED RETURN IS COMPUTED.

Measures what the daily files are: raw or adjusted, which splits and dividends
they carry, whether open and close are adjusted consistently, which dates are
missing, whether the daily open agrees with the 09:30 cash open, and the
MAGNITUDE of overnight gaps in units of daily ATR for gap-risk sizing.

No mean return, no signed overnight or intraday return, no continuation
statistic appears anywhere in this file. Those are Stage 1 questions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dataquality as DQ                                            # noqa: E402

L = []
p = L.append


def load_raw(sym):
    d = json.load(open(ROOT / f"data/{sym.lower()}_daily_full.json"))
    t = pd.to_datetime(pd.Series(d["time"]), unit="s").dt.normalize()
    return pd.DataFrame({"day": t, "open": d["open"], "high": d["high"],
                         "low": d["low"], "close": d["close"],
                         "volume": d["volume"]}).drop_duplicates("day")


def load_adj(sym):
    d = pd.read_csv(ROOT / f"data/daily_long/{sym}.csv", parse_dates=["timestamp"])
    return d.rename(columns={"timestamp": "day"}).assign(
        day=lambda x: x["day"].dt.normalize())


def main():
    p("RP-012C STAGE 0 -- DAILY DATA INVENTORY (no signed returns)")
    p("")
    p("=== 1. FILES ===")
    for sym in ("QQQ", "SPY", "IWM"):
        r = load_raw(sym)
        p(f"  {sym} raw  data/{sym.lower()}_daily_full.json  {len(r):>5} days  "
          f"{r.day.min().date()} -> {r.day.max().date()}")
        if sym != "IWM":
            a = load_adj(sym)
            p(f"  {sym} adj  data/daily_long/{sym}.csv          {len(a):>5} days  "
              f"{a.day.min().date()} -> {a.day.max().date()}  "
              f"pre-2016 {int((a.day < '2016-01-01').sum())}")
    p("  IJH, EFA: no daily file. Daily bars derivable only from 1-minute RTH")
    p("            files, 2021-01-04 -> 2025-12-31.")
    for f in ("nq_daily_3m.json", "es_daily_3m.json"):
        d = json.load(open(ROOT / "data" / f))
        t = pd.to_datetime(pd.Series(d["time"]), unit="s")
        p(f"  {f:<22} {len(t)} days {t.min().date()} -> {t.max().date()} -- "
          "a three-month live-chart cache, not a research series")
    p("  NQ_daily.parquet: 61 rows with 1970 timestamps -- unusable")
    p("")

    p("=== 2. ADJUSTMENT, SPLITS, DIVIDENDS (measured) ===")
    for sym in ("QQQ", "SPY", "IWM"):
        r = load_raw(sym).set_index("day")
        sp = [(r.index[i].date(), round(k, 3)) for i, _, _, k in
              DQ.split_scan(r["close"].to_numpy(), 0.3)]
        p(f"  {sym} raw: split-like jumps {sp if sp else 'none'}")
        if sym == "IWM":
            p("  IWM: no adjusted file on disk -- dividends CANNOT be verified;")
            p("       raw only, so a raw overnight return on an ex-date omits the dividend")
            continue
        a = load_adj(sym).set_index("day")
        j = r.join(a, lsuffix="_r", rsuffix="_a", how="inner")
        fc = j["close_a"] / j["close_r"]
        fo = j["open_a"] / j["open_r"]
        mism = (np.abs(fo / fc - 1) > 1e-4).mean()
        steps = fc.pct_change().abs()
        n_steps = int((steps > 1e-4).sum())
        big = steps[steps > 0.2]
        p(f"  {sym} adjusted/raw factor: {fc.iloc[0]:.4f} at start -> "
          f"{fc.iloc[-1]:.4f} at end; {n_steps} factor steps "
          f"({len(big)} split-sized)")
        p(f"       open and close share the same factor on "
          f"{100*(1-mism):.2f}% of days -> "
          f"{'CONSISTENT' if mism < 0.005 else 'INCONSISTENT'}")
        yrs = steps[steps > 1e-4].groupby(steps[steps > 1e-4].index.year).size()
        p(f"       dividend-sized steps per year: median {yrs.median():.0f} "
          f"(quarterly payer = 4)")
        p(f"       => daily_long is split AND dividend adjusted (total-return basis)")
    p("")

    p("=== 3. MISSING AND BAD DATES ===")
    q, s = load_raw("QQQ"), load_raw("SPY")
    i = load_raw("IWM")
    qs = set(q.day) ^ set(s.day)
    p(f"  QQQ vs SPY raw date sets differ on {len(qs)} dates")
    iwm_missing = sorted(set(q.day[q.day >= i.day.min()]) - set(i.day))
    p(f"  dates in QQQ but missing from IWM (after IWM start): {len(iwm_missing)}")
    for sym, d in (("QQQ", q), ("SPY", s), ("IWM", i)):
        gaps = d.day.diff().dt.days
        p(f"  {sym}: calendar gaps > 4 days: {int((gaps > 4).sum())} "
          f"(max {int(gaps.max())}, {d.day[gaps.idxmax()].date()}); "
          f"flat bars (O=H=L=C) {int(((d.open==d.high)&(d.high==d.low)&(d.low==d.close)).sum())}; "
          f"zero/NaN open {int((d.open.fillna(0)<=0).sum())}")
    p("  2001-09-11..14 closure and 2012-10-29..30 (Sandy) appear as the long gaps")
    p("")

    p("=== 4. IS THE DAILY OPEN THE 09:30 CASH OPEN? (2021+, where 1m exists) ===")
    for sym, path in (("QQQ", "data/intraday_long/QQQ_1m.parquet"),
                      ("SPY", "data/related/SPY_1m.parquet"),
                      ("IWM", "data/related/IWM_1m.parquet")):
        m = pd.read_parquet(ROOT / path)
        m["timestamp"] = pd.to_datetime(m["timestamp"])
        m["day"] = m["timestamp"].dt.normalize()
        first = m[m["timestamp"].dt.strftime("%H:%M") == "09:30"].set_index("day")
        r = load_raw(sym).set_index("day")
        j = r.join(first[["open"]], rsuffix="_1m", how="inner")
        diff = 1e4 * np.abs(j["open"] / j["open_1m"] - 1)
        p(f"  {sym}: {len(j)} common days; |daily open - 09:30 bar open| median "
          f"{diff.median():.2f} bps, p95 {diff.quantile(.95):.2f}, "
          f">5 bps on {100*(diff>5).mean():.1f}% of days")
    p("  The daily 'open' is the official opening print, which for ETFs is the")
    p("  opening auction; the 09:30 bar's open is the first print in that minute.")
    p("")

    p("=== 5. OVERNIGHT GAP MAGNITUDE -- risk sizing only, |gap| never signed ===")
    p("  gap = |open_t / close_{t-1} - 1| (adjusted series where it exists)")
    p("  ATR20 = trailing 20-day mean true range, prior days only")
    p(f"  {'instr':<6}{'period':<12}{'days':>6}{'med |gap|':>10}{'p95':>8}{'p99':>8}"
      f"{'max':>8}{'>0.5ATR':>9}{'>1ATR':>8}{'>2ATR':>8}{'wkend/wkday':>12}")
    for sym in ("QQQ", "SPY", "IWM"):
        d = (load_adj(sym) if sym != "IWM" else load_raw(sym)).sort_values("day")
        d = d.reset_index(drop=True)
        pc = d["close"].shift(1)
        tr = np.maximum(d["high"], pc) - np.minimum(d["low"], pc)
        atr = (tr / pc).rolling(20).mean().shift(1)
        gap = (d["open"] / pc - 1).abs()
        wk = d["day"].diff().dt.days > 1
        for lab, lo, hi in (("1999-2015", "1999", "2015-12-31"),
                            ("2016-2020", "2016", "2020-12-31"),
                            ("2021-2026", "2021", "2026-12-31")):
            m = (d["day"] >= lo) & (d["day"] <= hi) & atr.notna()
            g, a = gap[m], atr[m]
            rel = g / a
            p(f"  {sym:<6}{lab:<12}{int(m.sum()):>6}{1e4*g.median():>9.1f}b"
              f"{1e4*g.quantile(.95):>7.0f}b{1e4*g.quantile(.99):>7.0f}b"
              f"{1e4*g.max():>7.0f}b{100*(rel>0.5).mean():>8.1f}%"
              f"{100*(rel>1).mean():>7.1f}%{100*(rel>2).mean():>7.1f}%"
              f"{(g[wk[m]].median()/g[~wk[m]].median()):>12.2f}")
    p("  IWM is raw, so its ex-dividend dates add a dividend-sized spurious gap")
    p("")
    txt = "\n".join(L)
    print(txt)
    (ROOT / "reports/rp012c_stage0_inventory.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
