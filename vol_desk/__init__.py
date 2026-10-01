"""Vol Desk — mechanical GEX swing system for single-stock options.

Core thesis: when dealer delta positioning flips bullish on a name with
strong options structure, price tends to accelerate toward the next major
gamma level. Enter just above the positive transition level (pTrans),
ride to +GEX as the primary target.

Spec: reports/vol_desk_system.md. The only discretion the system allows
is at T1 (take it or lock-and-ride). Everything else is rules.
"""

from .models import Position, ScreenRow
from .entry import (
    BLOCKED,
    CONFIRMED,
    PENDING,
    WAIT,
    ScreenResult,
    continuation_eligible,
    evaluate_filters,
    open_trigger,
    screen,
)
from .exits import (
    EXIT_NEXT_OPEN,
    EXIT_NOW,
    EXIT_STALL,
    EXIT_TIME,
    HOLD,
    T1_DECISION,
    T2_HIT,
    WATCH,
    ExitAction,
    hard_cap_hit,
    lock_and_ride,
    mark_session,
    take_t1,
)
from .regime import (
    B_CONTINUATION,
    P2P,
    GateReading,
    approve,
    read_gates,
    size_factor,
)

__all__ = [
    "ScreenRow", "Position",
    "screen", "evaluate_filters", "open_trigger", "continuation_eligible",
    "ScreenResult", "CONFIRMED", "PENDING", "BLOCKED", "WAIT",
    "mark_session", "hard_cap_hit", "take_t1", "lock_and_ride", "ExitAction",
    "HOLD", "WATCH", "EXIT_NOW", "EXIT_NEXT_OPEN", "EXIT_TIME", "EXIT_STALL",
    "T1_DECISION", "T2_HIT",
    "read_gates", "approve", "size_factor", "GateReading",
    "P2P", "B_CONTINUATION",
]
