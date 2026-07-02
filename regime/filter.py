"""Mechanical trend-vs-chop regime filter for NQ/ES day trading.

Validated on QQQ/SPY (near-perfect NQ/ES RTH proxies: 30-min return
correlation 0.999 / 0.997) over Nov 2025 - Jul 2026 hourly sessions, with
spot confirmation on front-month NQ/ES. See reports/trend_regime_study.md.

Two checkpoints, all inputs computable on any platform:

  10:30 ET  chop veto      opening-range compression -> stand down
  11:00 ET  full read      TREND_UP / TREND_DOWN / CHOP / NEUTRAL

Inputs per session:
  atr20        prior day's 20-day daily ATR (points)
  session_open 09:30 ET print
  fh_high/fh_low/fh_close  first-90-min high, low, last price (09:30-11:00)
  fh_path      optional: sum of |bar close-to-close| over the first 90 min
               (improves the read; omit if unavailable)
Optional pre-open prior:
  gap_atr      |open - prior RTH close| / atr20
  atr_ratio    ATR(5) / ATR(20) on daily bars
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time as dtime

# Calibrated thresholds (see scripts/study_filter.py). Deliberately round
# numbers: the effect is a plateau, not a knife edge, and round values
# resist overfit.
RANGE_CHOP = 0.35   # first-hour range/ATR below this -> chop veto
RANGE_TREND = 0.55  # minimum expansion for a trend call
POS_EXTREME = 0.80  # close pinned to top/bottom 20% of the opening range
ER_ROTATION = 0.40  # first-hour efficiency ratio below this = rotation


@dataclass
class RegimeReading:
    state: str            # TREND_UP | TREND_DOWN | CHOP | NEUTRAL
    score: float          # 0-100 continuous trendiness (for sizing/ranking)
    range_atr: float      # first-hour range / daily ATR20
    pos: float            # close position within first-hour range, 0..1
    er: float | None      # first-hour efficiency ratio (None if no path given)
    notes: list[str] = field(default_factory=list)


def chop_veto_1030(or_high: float, or_low: float, atr20: float) -> bool:
    """10:30 ET early exit: compressed 60-min opening range -> chop day.

    In sample, OR60/ATR < 0.35 gave P(CHOP) 0.71-0.93 and P(TREND) 0-6%
    across QQQ/SPY/NQ/ES. When True, stand down from continuation plays.
    """
    return (or_high - or_low) / atr20 < RANGE_CHOP


def read_1100(
    atr20: float,
    session_open: float,
    fh_high: float,
    fh_low: float,
    fh_close: float,
    fh_path: float | None = None,
    gap_atr: float | None = None,
    atr_ratio: float | None = None,
) -> RegimeReading:
    """Full 11:00 ET regime read from the first 90 minutes."""
    rng = fh_high - fh_low
    r = rng / atr20
    pos = (fh_close - fh_low) / rng if rng > 0 else 0.5
    er = None
    if fh_path is not None and fh_path > 0:
        er = abs(fh_close - session_open) / fh_path

    notes = []
    # --- state (hard rules, exactly as validated) ---
    state = "NEUTRAL"
    if r >= RANGE_TREND and (pos >= POS_EXTREME or pos <= 1 - POS_EXTREME):
        state = "TREND_UP" if pos >= POS_EXTREME else "TREND_DOWN"
    if r < RANGE_CHOP:
        state = "CHOP"
        notes.append(f"range veto: first-hour range {r:.2f} ATR < {RANGE_CHOP}")
    elif er is not None and er < ER_ROTATION and (1 - POS_EXTREME) < pos < POS_EXTREME:
        state = "CHOP"
        notes.append(f"rotation veto: ER {er:.2f} with mid-range close")

    # --- continuous score for sizing (0-100) ---
    s_r = _clip01((r - RANGE_CHOP) / (0.75 - RANGE_CHOP))
    s_p = _clip01((abs(pos - 0.5) * 2 - 0.3) / 0.7)
    s_e = _clip01((er - 0.3) / 0.5) if er is not None else 0.5
    score = 100 * (0.5 * s_r + 0.3 * s_p + 0.2 * s_e)

    # --- pre-open prior: nudge only, never flips a hard rule ---
    if gap_atr is not None and atr_ratio is not None:
        if gap_atr >= 0.5 and atr_ratio >= 1.05:
            score = min(100, score + 8)
            notes.append("expansion prior (large gap + rising vol)")
        elif gap_atr < 0.10 and atr_ratio < 0.90:
            score = max(0, score - 8)
            notes.append("compression prior (no gap + falling vol)")

    return RegimeReading(state, round(score, 1), round(r, 3), round(pos, 3), er if er is None else round(er, 3), notes)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


class TrendChopFilter:
    """Convenience wrapper: feed intraday bars, get session regime reads.

    Works on a DataFrame of RTH bars (ET tz-aware index, columns
    open/high/low/close) for a single session, plus the daily ATR context.
    """

    def __init__(self, atr20: float, prior_close: float | None = None,
                 atr_ratio: float | None = None):
        self.atr20 = atr20
        self.prior_close = prior_close
        self.atr_ratio = atr_ratio

    def read(self, session_bars) -> RegimeReading:
        """Regime read using bars up to (and including) the 10:30-11:00 bar."""
        fh = session_bars[session_bars.index.time < dtime(11, 0)]
        if fh.empty or fh.index[0].time() != dtime(9, 30):
            raise ValueError("session_bars must start at the 09:30 ET bar")
        o = float(fh["open"].iloc[0])
        gap = None
        if self.prior_close:
            gap = abs(o - self.prior_close) / self.atr20
        closes = fh["close"]
        path = float(closes.diff().abs().sum() + abs(closes.iloc[0] - o))
        return read_1100(
            atr20=self.atr20,
            session_open=o,
            fh_high=float(fh["high"].max()),
            fh_low=float(fh["low"].min()),
            fh_close=float(closes.iloc[-1]),
            fh_path=path,
            gap_atr=gap,
            atr_ratio=self.atr_ratio,
        )
