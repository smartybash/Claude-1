"""Ingest an external intraday CSV (yfinance or Stooq) into our data/ JSON schema.

The session's egress policy blocks Yahoo/Stooq/Kaggle, so fetch locally and drop
the CSV in — this converts it to {time, open, high, low, close, volume} exactly
like the IBKR-sourced files, so every backtest picks it up unchanged.

Usage:
    python3 scripts/ingest_csv.py SPY_1h.csv spy_1h_deep.json --tz America/New_York
    python3 scripts/ingest_csv.py QQQ_1h.csv qqq_1h_deep.json --resample 30min

Handles:
  * yfinance CSV  (Datetime index + Open/High/Low/Close/Adj Close/Volume;
                   tolerates the 2-3 row multiindex header yfinance writes)
  * Stooq CSV     (Date[,Time],Open,High,Low,Close,Volume)
Timestamps are localized/converted to UTC on write. Optional --resample
downsamples (e.g. 1h -> 30min is NOT valid; only coarser, e.g. 5min -> 30min).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def _find(cols, *names):
    low = {str(c).strip().lower(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    return None


def read_any(path: Path, tz: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    # yfinance multiindex header leaves junk rows like "Ticker"/"Date" — drop them
    dt_col = _find(raw.columns, "datetime", "date", "timestamp", "time")
    if dt_col is None:
        # header rows shifted; retry treating first col as datetime
        raw = pd.read_csv(path, skiprows=[1, 2])
        dt_col = raw.columns[0]
    o = _find(raw.columns, "open"); h = _find(raw.columns, "high")
    l = _find(raw.columns, "low");  c = _find(raw.columns, "close")
    v = _find(raw.columns, "volume", "vol")
    if None in (o, h, l, c):
        raise SystemExit(f"could not find OHLC columns in {list(raw.columns)}")
    tcol = raw[dt_col].astype(str)
    time_col = _find(raw.columns, "time")
    if time_col and time_col != dt_col and raw[time_col].notna().any():
        tcol = tcol + " " + raw[time_col].astype(str)
    ts = pd.to_datetime(tcol, errors="coerce", utc=False)
    df = pd.DataFrame({
        "open": pd.to_numeric(raw[o], errors="coerce").values,
        "high": pd.to_numeric(raw[h], errors="coerce").values,
        "low": pd.to_numeric(raw[l], errors="coerce").values,
        "close": pd.to_numeric(raw[c], errors="coerce").values,
        "volume": pd.to_numeric(raw[v], errors="coerce").values if v else 0.0,
    }, index=pd.DatetimeIndex(ts)).dropna(subset=["open", "high", "low", "close"])
    df = df[~df.index.isna()]
    if df.index.tz is None:
        df.index = df.index.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
    df.index = df.index.tz_convert("UTC")
    return df[~df.index.duplicated(keep="last")].sort_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("out_json")
    ap.add_argument("--tz", default="America/New_York",
                    help="timezone of naive timestamps (yfinance intraday is US/Eastern)")
    ap.add_argument("--resample", default=None, help="coarser bar, e.g. 30min")
    a = ap.parse_args()
    df = read_any(Path(a.csv), a.tz)
    if a.resample:
        df = (df.resample(a.resample, label="left", closed="left")
                .agg({"open": "first", "high": "max", "low": "min",
                      "close": "last", "volume": "sum"}).dropna(subset=["open"]))
    out = {"time": [t.isoformat() for t in df.index],
           "open": df["open"].tolist(), "high": df["high"].tolist(),
           "low": df["low"].tolist(), "close": df["close"].tolist(),
           "volume": df["volume"].fillna(0).tolist()}
    p = ROOT / "data" / a.out_json
    p.write_text(json.dumps(out))
    sess = pd.Series(df.index.tz_convert(a.tz).date).nunique()
    print(f"wrote {p}  bars={len(df)}  sessions={sess}  "
          f"{df.index.min().date()} -> {df.index.max().date()}")


if __name__ == "__main__":
    main()
