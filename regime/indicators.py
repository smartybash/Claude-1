"""Daily indicators and the ex-post day-type label.

Everything operates on a daily OHLC DataFrame (columns open/high/low/close)
and returns Series aligned to it. All are standard textbook definitions —
the point of the study is which of them predict day type, not novelty.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(d: pd.DataFrame) -> pd.Series:
    pc = d["close"].shift(1)
    return pd.concat(
        [d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1
    ).max(axis=1)


def atr(d: pd.DataFrame, n: int = 20) -> pd.Series:
    return true_range(d).rolling(n).mean()


def adx(d: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ADX."""
    up = d["high"].diff()
    dn = -d["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(d)
    alpha = 1.0 / n
    atr_w = tr.ewm(alpha=alpha, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=d.index).ewm(alpha=alpha, adjust=False).mean() / atr_w
    minus_di = 100 * pd.Series(minus_dm, index=d.index).ewm(alpha=alpha, adjust=False).mean() / atr_w
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=alpha, adjust=False).mean()


def efficiency_ratio(close: pd.Series, n: int = 10) -> pd.Series:
    """Kaufman efficiency ratio: |net change| / sum of |daily changes|."""
    change = close.diff(n).abs()
    volatility = close.diff().abs().rolling(n).sum()
    return change / volatility


def nr_flag(d: pd.DataFrame, n: int = 7) -> pd.Series:
    """True when today's range is the narrowest of the last n days (NR7)."""
    rng = d["high"] - d["low"]
    return rng == rng.rolling(n).min()


def inside_day(d: pd.DataFrame) -> pd.Series:
    return (d["high"] < d["high"].shift(1)) & (d["low"] > d["low"].shift(1))


def directional_range_capture(d: pd.DataFrame) -> pd.Series:
    """|close - open| / (high - low). 1.0 = pure trend day, ~0 = round trip."""
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    return (d["close"] - d["open"]).abs() / rng


def label_day_type(
    d: pd.DataFrame,
    atr_n: int = 20,
    trend_drc: float = 0.60,
    trend_range: float = 0.80,
    chop_drc: float = 0.35,
    chop_range: float = 0.70,
) -> pd.Series:
    """Ex-post day-type label from daily OHLC.

    TREND: open-to-close move captures most of the range AND the range is
    at least `trend_range` of ATR (a big directional day worth pressing).
    CHOP: the day round-trips (low DRC) OR the range is compressed.
    Everything else is NEUTRAL.
    """
    drc = directional_range_capture(d)
    rng_atr = (d["high"] - d["low"]) / atr(d, atr_n).shift(1)
    out = pd.Series("NEUTRAL", index=d.index)
    out[(drc >= trend_drc) & (rng_atr >= trend_range)] = "TREND"
    out[(drc <= chop_drc) | (rng_atr <= chop_range)] = "CHOP"
    # A day that is both low-DRC and huge-range is violent chop, keep CHOP.
    return out
