"""Loaders for IBKR columnar price-history JSON and session bucketing.

All timestamps in the raw files are UTC. Everything here converts to
America/New_York so sessions line up across EST/EDT boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")

RTH_START = "09:30"
RTH_END = "16:00"


def load_ibkr_json(path: str | Path) -> pd.DataFrame:
    """Load an IBKR get_price_history columnar JSON file.

    Returns a DataFrame indexed by ET timestamp with columns
    open/high/low/close/volume, sorted ascending, duplicates dropped.
    """
    raw = json.loads(Path(path).read_text())
    df = pd.DataFrame(
        {
            "open": raw["open"],
            "high": raw["high"],
            "low": raw["low"],
            "close": raw["close"],
            "volume": raw["volume"],
        },
        index=pd.to_datetime(raw["time"], utc=True),
    )
    df.index = df.index.tz_convert(ET)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index.name = "ts"
    return df


def add_session_date(df: pd.DataFrame) -> pd.DataFrame:
    """Tag each bar with its trading session date.

    For futures trading nearly 23h, bars from 18:00 ET onward belong to the
    NEXT day's session (CME convention). For RTH-only equity data this is a
    no-op relabel.
    """
    out = df.copy()
    ts = out.index
    session = pd.Series(ts.date, index=ts)
    after_1800 = ts.hour >= 18
    session[after_1800] = (ts[after_1800] + pd.Timedelta(days=1)).date
    out["session"] = pd.to_datetime(session.values)
    return out


def rth_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep bars whose start time falls inside 09:30-16:00 ET."""
    t = df.index.time
    lo = pd.Timestamp(RTH_START).time()
    hi = pd.Timestamp(RTH_END).time()
    return df[(t >= lo) & (t < hi)]


def rth_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate intraday bars into one row per RTH session.

    Returns per-session open/high/low/close/volume plus:
      - path: sum of |close-to-close| moves within the session (for the
        session efficiency ratio)
      - n_bars: bar count (used to drop half days / partial sessions)
    """
    bars = rth_only(df).copy()
    bars["date"] = pd.to_datetime(pd.Series(bars.index.date, index=bars.index))
    g = bars.groupby("date")
    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
            "path": g["close"].apply(lambda s: s.diff().abs().sum()),
            "n_bars": g["close"].size(),
        }
    )
    out.index.name = "date"
    return out


def overnight_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per-session overnight (18:00 prior ET -> 09:30 ET) high/low/range.

    Only meaningful for futures data that includes the Globex session.
    """
    tagged = add_session_date(df)
    t = tagged.index.time
    on = tagged[(t < pd.Timestamp(RTH_START).time()) | (t >= pd.Timestamp("18:00").time())]
    g = on.groupby("session")
    out = pd.DataFrame(
        {
            "on_high": g["high"].max(),
            "on_low": g["low"].min(),
            "on_open": g["open"].first(),
            "on_close": g["close"].last(),
            "on_n_bars": g["close"].size(),
        }
    )
    out["on_range"] = out["on_high"] - out["on_low"]
    out.index.name = "date"
    return out
