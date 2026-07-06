"""Parquet cache for intraday/daily IBKR data.

Raw fetches (whatever the source: the ib_async deep fetch in
scripts/fetch_intraday.py, or the capped MCP get_price_history pulls) land as
IBKR columnar JSON in data/.  build_cache() merges everything per symbol and
timeframe into data/parquet/{SYM}_{TF}.parquet, deduplicated on timestamp, so
the backtest and screener never re-hit IBKR.
"""

from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PARQUET = DATA / "parquet"

# raw JSON files feeding each parquet cache, per (symbol, timeframe)
SOURCES: dict[tuple[str, str], list[str]] = {
    ("NQ", "5min"): ["nq_5min.json", "nq_5min_live.json", "nq_5min_rth.json"],
    ("ES", "5min"): ["es_5min.json", "es_5min_live.json", "es_5min_rth.json"],
    ("QQQ", "5min"): ["qqq_5min_rth.json"],
    ("SPY", "5min"): ["spy_5min_rth.json"],
    ("NQ", "daily"): ["nq_daily_3m.json"],
    ("ES", "daily"): ["es_daily_3m.json"],
    ("QQQ", "daily"): ["qqq_daily_5y.json", "qqq_daily_1m.json"],
    ("SPY", "daily"): ["spy_daily_5y.json", "spy_daily_1m.json"],
}

FUTURES = {"NQ", "ES"}


def load_ibkr_json(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text())
    df = pd.DataFrame(
        {k: raw[k] for k in ("open", "high", "low", "close", "volume")},
        index=pd.to_datetime(raw["time"], utc=True),
    )
    df.index = df.index.tz_convert(ET)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "ts"
    return df


def build_cache(verbose: bool = True) -> dict:
    """Merge all raw JSON into per-symbol parquet files. Returns manifest."""
    PARQUET.mkdir(exist_ok=True)
    manifest = {}
    for (sym, tf), files in SOURCES.items():
        frames, used = [], []
        for f in files:
            p = DATA / f
            if p.exists():
                frames.append(load_ibkr_json(p))
                used.append(f)
        if not frames:
            continue
        df = pd.concat(frames)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        out = PARQUET / f"{sym}_{tf}.parquet"
        df.to_parquet(out)
        manifest[f"{sym}_{tf}"] = {
            "sources": used,
            "bars": len(df),
            "start": str(df.index.min()),
            "end": str(df.index.max()),
        }
        if verbose:
            print(f"{sym}_{tf}: {len(df)} bars  {df.index.min()} -> {df.index.max()}")
    (PARQUET / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load(sym: str, tf: str) -> pd.DataFrame:
    """Load a cached series; raises if the cache hasn't been built."""
    p = PARQUET / f"{sym}_{tf}.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run scripts/build_parquet_cache.py")
    return pd.read_parquet(p)


def rth_sessions_5min(df: pd.DataFrame) -> dict[pd.Timestamp, pd.DataFrame]:
    """Split a 5-min series into RTH sessions (09:30-16:00 ET), keyed by date.

    Sessions with fewer than 60 bars (half days, partial fetches, today's
    still-open session) are dropped for backtesting purposes.
    """
    t = df.index.time
    lo, hi = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()
    rth = df[(t >= lo) & (t < hi)]
    out = {}
    for date, g in rth.groupby(rth.index.date):
        if len(g) >= 60:
            out[pd.Timestamp(date)] = g
    return out


def daily_from_intraday_or_cache(sym: str) -> pd.DataFrame:
    """Daily OHLC for level computation, indexed by SESSION date.

    CME futures daily bars are stamped at the 18:00 ET Globex open of the
    prior calendar day (the bar stamped Tue 18:00 is Wednesday's session);
    equity daily bars are stamped at the 09:30 ET session open. Shift the
    futures dates forward one calendar day so both align on session date.
    """
    d = load(sym, "daily").copy()
    ts = d.index
    dates = pd.Series(ts.date, index=ts)
    if sym in FUTURES:
        evening = ts.hour >= 17
        dates[evening] = (ts[evening] + pd.Timedelta(days=1)).date
    d["date"] = pd.to_datetime(dates.values)
    d = d.set_index("date")[["open", "high", "low", "close", "volume"]]
    return d[~d.index.duplicated(keep="last")].sort_index()
