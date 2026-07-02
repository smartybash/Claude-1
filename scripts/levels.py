"""Morning level sheet for NQ/ES: every price the regime filter keys off.

Usage: python3 scripts/levels.py [YYYY-MM-DD]   (default: today's session)

Prints a compact sheet to enter into TWS as horizontal lines / price alerts:
  - prior-day RTH high / low / close
  - overnight (Globex 18:00 -> 09:30) high / low
  - ATR-derived decision levels for the session:
      veto line   : opening range must exceed 0.35 x ATR by 10:30
      entry band  : 0.35 - 0.55 x ATR at 11:00 (mechanical entry zone)
      stop width  : 0.30 x ATR
  - once the first 90 min exist in the data: OR high/low, the top/bottom-25%
    trigger prices, and the band-ceiling price in each direction.

Needs data/{nq,es}_5min_live.json refreshed (ask the assistant to re-pull)
and the ETF daily files for the ATR reference.
"""

import sys
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from regime.indicators import atr

DATA = Path(__file__).resolve().parents[1] / "data"


def sheet(name: str, fut_file: str, etf_file: str, date: pd.Timestamp):
    fut = load_ibkr_json(DATA / fut_file)
    etf = load_ibkr_json(DATA / etf_file)

    # ATR20 through the prior session, scaled ETF -> futures by prior close ratio
    prior = date - pd.offsets.BDay(1)
    etf_idx = pd.to_datetime(etf.index.date)
    mask = etf_idx <= pd.Timestamp(prior.date())
    a_etf = float(atr(etf, 20)[mask].iloc[-1])
    etf_close = float(etf["close"][mask].iloc[-1])

    dts = pd.Series(fut.index.date, index=fut.index)
    prior_rth = fut[(dts == prior.date())
                    & (fut.index.time >= dtime(9, 30)) & (fut.index.time < dtime(16, 0))]
    pc = float(prior_rth["close"].iloc[-1])
    a = a_etf * pc / etf_close

    on = fut[(fut.index >= pd.Timestamp(f"{prior.date()} 18:00", tz="America/New_York"))
             & (fut.index < pd.Timestamp(f"{date.date()} 09:30", tz="America/New_York"))]

    d = 2 if a < 500 else 1  # print precision
    print(f"\n=== {name} — session {date.date()}   ATR20 ref {a:,.0f} pts")
    print(f"  prior day high   {prior_rth['high'].max():,.{d}f}")
    print(f"  prior day low    {prior_rth['low'].min():,.{d}f}")
    print(f"  prior close      {pc:,.{d}f}")
    if len(on):
        print(f"  overnight high   {on['high'].max():,.{d}f}")
        print(f"  overnight low    {on['low'].min():,.{d}f}")
    print(f"  -- decision arithmetic --")
    print(f"  veto if OR < {0.35 * a:,.0f} pts | entry band {0.35 * a:,.0f}-{0.55 * a:,.0f} pts | stop {0.30 * a:,.0f} pts")

    rth = fut[(dts == date.date())
              & (fut.index.time >= dtime(9, 30)) & (fut.index.time < dtime(11, 0))]
    if len(rth):
        hi, lo = float(rth["high"].max()), float(rth["low"].min())
        rng = hi - lo
        print(f"  -- opening range so far (through {rth.index[-1].strftime('%H:%M')} ET bar) --")
        print(f"  OR high          {hi:,.{d}f}")
        print(f"  OR low           {lo:,.{d}f}     (range {rng:,.0f} pts = {rng / a:.2f} ATR)")
        print(f"  long trigger     {lo + 0.75 * rng:,.{d}f}   (top-25% line)")
        print(f"  short trigger    {lo + 0.25 * rng:,.{d}f}   (bottom-25% line)")
        print(f"  band ceiling up  {lo + 0.55 * a:,.{d}f}   (high above this = too late long)")
        print(f"  band floor down  {hi - 0.55 * a:,.{d}f}   (low below this = too late short)")


def main():
    date = pd.Timestamp(sys.argv[1]) if len(sys.argv) > 1 else pd.Timestamp("2026-07-02")
    sheet("NQ Sep26", "nq_5min_live.json", "qqq_daily_5y.json", date)
    sheet("ES Sep26", "es_5min_live.json", "spy_daily_5y.json", date)


if __name__ == "__main__":
    main()
