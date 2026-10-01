"""Vol Desk exit framework — the only thing that governs an open position.

Once in, entry filter logic no longer applies. Four stops, in order:

  Stop 1  close below nTrans          -> exit at the next open, no discretion
  Stop 2  -10% from entry, below      -> out immediately (intraday),
          pTrans                         non-negotiable
  Stop 3  time stop: by day 7 the     -> exit and revisit; a position
          position needs >= 50%          sitting still for a week is not
          progress toward T1             going to the target
  Stop 4  stalling: < 10%/day          -> exit regardless of day count
          progress three consecutive
          sessions

States while open:

  CONFIRMED  above pTrans, not yet at target — hold
  WATCH      below pTrans but above nTrans — hold existing, add nothing

Taking profit: T1 is the +GEX level. When it hits, two choices — exit and
bank, or lock the stop to entry and ride toward T2 (usually +GEX next or
COTMC). You cannot hold for T2 without first locking T1; that rule exists
to prevent giving back a winner chasing an extension.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Position

HARD_CAP = -0.10            # stop 2: max drawdown from entry while below pTrans
TIME_STOP_DAY = 7           # stop 3: session count checkpoint
TIME_STOP_MIN_PROGRESS = 0.50  # stop 3: minimum progress toward T1 by day 7
STALL_RATE = 0.10           # stop 4: minimum per-session progress rate
STALL_SESSIONS = 3          # stop 4: consecutive sessions below the rate

# actions
HOLD = "HOLD"                       # CONFIRMED: above pTrans, ride it
WATCH = "WATCH"                     # below pTrans, above nTrans: add nothing
EXIT_NOW = "EXIT_NOW"               # stop 2 / locked stop: out immediately
EXIT_NEXT_OPEN = "EXIT_NEXT_OPEN"   # stop 1: structural stop, exit the open
EXIT_TIME = "EXIT_TIME"             # stop 3: day-7 progress test failed
EXIT_STALL = "EXIT_STALL"           # stop 4: three stalled sessions
T1_DECISION = "T1_DECISION"         # target hit: bank it or lock-and-ride
T2_HIT = "T2_HIT"                   # extension target reached: bank it


@dataclass
class ExitAction:
    action: str
    reason: str


def hard_cap_hit(pos: Position, price: float) -> bool:
    """Stop 2, checked intraday: -10% from entry while below pTrans."""
    return price <= pos.entry * (1 + HARD_CAP) and price < pos.p_trans


def take_t1(pos: Position) -> ExitAction:
    """T1 choice A: exit and bank the gain."""
    pos.t1_hit = True
    return ExitAction(EXIT_NOW, "T1 (+GEX) hit — banking the gain")


def lock_and_ride(pos: Position) -> None:
    """T1 choice B: lock the stop to entry and ride toward T2.

    The only discretion the system allows. Requires a T2 level — you are
    riding toward a structural level, not an open-ended hope.
    """
    if not pos.t1_hit:
        raise ValueError("cannot ride for T2 without T1 hitting first")
    if pos.t2 is None:
        raise ValueError("no T2 level defined — take T1 instead")
    pos.t1_locked = True
    pos.stop = pos.entry


def mark_session(pos: Position, close: float) -> ExitAction:
    """End-of-session mark: apply the stop framework, in order.

    Call once per completed session with the session close. Updates the
    position's day count and progress history, and returns the action.
    """
    pos.day += 1
    prog = pos.progress(close)
    pos.progress_history.append(prog)

    # stop 1 — structural stop: close below nTrans, exit next open
    if close < pos.n_trans:
        return ExitAction(EXIT_NEXT_OPEN, f"stop 1: close {close} below nTrans {pos.n_trans}")

    # stop 2 — hard cap: -10% from entry while below pTrans
    if hard_cap_hit(pos, close):
        return ExitAction(EXIT_NOW, f"stop 2: {prog:+.0%} of T1 leg, "
                                    f"{close / pos.entry - 1:+.1%} from entry below pTrans")

    # locked stop once riding for T2
    if pos.t1_locked and close <= pos.stop:
        return ExitAction(EXIT_NOW, "locked stop: back at entry after T1")

    # targets
    if pos.t1_locked:
        if pos.t2 is not None and close >= pos.t2:
            return ExitAction(T2_HIT, "T2 reached — bank it")
    elif close >= pos.t1:
        pos.t1_hit = True
        return ExitAction(T1_DECISION, "T1 (+GEX) hit: take it, or lock stop "
                                       "to entry and ride for T2")

    # stop 3 — time stop: >= 50% progress toward T1 by day 7
    if pos.day >= TIME_STOP_DAY and prog < TIME_STOP_MIN_PROGRESS:
        return ExitAction(EXIT_TIME, f"stop 3: day {pos.day}, only {prog:.0%} "
                                     f"toward T1 (need {TIME_STOP_MIN_PROGRESS:.0%})")

    # stop 4 — stalling: < 10%/day progress, three consecutive sessions
    h = pos.progress_history
    gains = [b - a for a, b in zip([0.0] + h[:-1], h)]  # per-session progress
    if len(gains) >= STALL_SESSIONS and all(g < STALL_RATE for g in gains[-STALL_SESSIONS:]):
        return ExitAction(EXIT_STALL, f"stop 4: three consecutive sessions "
                                      f"below {STALL_RATE:.0%}/day progress")

    # no stop fired: state depends on where we sit vs pTrans
    if close >= pos.p_trans:
        return ExitAction(HOLD, "CONFIRMED: above pTrans, holding to target")
    return ExitAction(WATCH, "below pTrans, above nTrans: hold existing, add nothing")
