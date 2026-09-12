"""The causal touch -> confirmation-window -> sweep/run classifier.

This is the fix for the daily-resolution bug: the event is defined by the
touch bar, the classification is decided by closes strictly at-or-after the
touch bar within a K-bar window, and anything tradeable happens at the CLOSE
of the bar that confirms the classification - never at the touch itself, and
never using the session's own later data.

The same state machine runs bar-by-bar in the backtest (Part B) and in the
live screener (Part C).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .levels import Level


@dataclass
class Touch:
    level: Level
    touch_idx: int
    touch_time: pd.Timestamp
    touch_extreme: float      # touch bar's high (high-side) / low (low-side)
    status: str = "pending"   # pending -> "sweep" | "run"
    confirm_idx: int | None = None
    confirm_time: pd.Timestamp | None = None
    confirm_price: float | None = None  # close of the confirming bar


@dataclass
class SweepRunTracker:
    """One session, one level set, one K.

    Feed bars in order via on_bar(); it returns newly confirmed Touch events.
    Each level can be touched (and classified) at most once per session -
    re-entry is deliberately NOT tested (kept out of the walk-forward grid).
    """

    levels: list[Level]
    K: int
    touches: dict[str, Touch] = field(default_factory=dict)

    def on_bar(self, i: int, ts: pd.Timestamp, o: float, h: float, lo: float, c: float) -> list[Touch]:
        confirmed: list[Touch] = []
        # 1. register first touches
        for lv in self.levels:
            if lv.name in self.touches:
                continue
            if lv.side == "high" and h > lv.price:
                self.touches[lv.name] = Touch(lv, i, ts, h)
            elif lv.side == "low" and lo < lv.price:
                self.touches[lv.name] = Touch(lv, i, ts, lo)
        # 2. classify pending touches (touch bar itself participates: j=0)
        for t in self.touches.values():
            if t.status != "pending":
                continue
            j = i - t.touch_idx
            closed_inside = (
                c < t.level.price if t.level.side == "high" else c > t.level.price
            )
            if closed_inside:
                t.status = "sweep"
            elif j >= self.K:
                t.status = "run"
            else:
                continue
            t.confirm_idx, t.confirm_time, t.confirm_price = i, ts, c
            confirmed.append(t)
        return confirmed


def classify_session(bars: pd.DataFrame, levels: list[Level], K: int) -> list[Touch]:
    """Run the tracker over a full session of bars. Returns confirmed touches."""
    tr = SweepRunTracker(levels, K)
    out: list[Touch] = []
    for i, (ts, row) in enumerate(bars.iterrows()):
        out.extend(tr.on_bar(i, ts, row["open"], row["high"], row["low"], row["close"]))
    return out


@dataclass
class Trade:
    session: pd.Timestamp
    level: str
    kind: str        # "sweep" | "run"
    direction: int   # +1 long, -1 short
    entry_idx: int
    entry_time: pd.Timestamp
    entry: float
    stop: float
    exit_idx: int
    exit_time: pd.Timestamp
    exit: float
    exit_reason: str  # "stop" | "eod"
    ret: float        # signed fractional return before costs

    @property
    def hold_bars(self) -> int:
        return self.exit_idx - self.entry_idx


def simulate_trades(
    bars: pd.DataFrame,
    touches: list[Touch],
    mode: str,                # "sweep" (fade) or "run" (follow)
    session: pd.Timestamp,
) -> list[Trade]:
    """Turn confirmed touches of one kind into flat-at-EOD trades.

    Entry: close of the confirming bar (never the touch bar unless the touch
    bar itself confirms - which is still information available at that close).
    Stop: sweep -> beyond the touch bar's extreme; run -> back at the level.
    Exit: stop hit intra-bar (filled AT the stop, conservative), else the
    session's last bar close. Entries on the final bar are skipped.
    """
    n = len(bars)
    trades: list[Trade] = []
    for t in touches:
        if t.status != mode or t.confirm_idx is None or t.confirm_idx >= n - 1:
            continue
        if mode == "sweep":
            direction = -1 if t.level.side == "high" else +1
            stop = t.touch_extreme
        else:
            direction = +1 if t.level.side == "high" else -1
            stop = t.level.price
        entry = float(t.confirm_price)
        # a confirmed-sweep entry already inside the level can sit on the
        # wrong side of a run stop; sanity: skip degenerate zero-risk setups
        if (direction > 0 and stop >= entry) or (direction < 0 and stop <= entry):
            continue
        exit_idx, exit_price, reason = n - 1, float(bars["close"].iloc[-1]), "eod"
        for j in range(t.confirm_idx + 1, n):
            row = bars.iloc[j]
            if direction > 0 and row["low"] <= stop:
                exit_idx, exit_price, reason = j, stop, "stop"
                break
            if direction < 0 and row["high"] >= stop:
                exit_idx, exit_price, reason = j, stop, "stop"
                break
        trades.append(
            Trade(
                session=session,
                level=t.level.name,
                kind=mode,
                direction=direction,
                entry_idx=t.confirm_idx,
                entry_time=t.confirm_time,
                entry=entry,
                stop=stop,
                exit_idx=exit_idx,
                exit_time=bars.index[exit_idx],
                exit=exit_price,
                exit_reason=reason,
                ret=direction * (exit_price - entry) / entry,
            )
        )
    return trades
