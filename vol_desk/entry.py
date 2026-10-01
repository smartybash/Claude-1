"""Vol Desk entry engine: the five filters, statuses, and the open trigger.

Every name must clear five filters before it touches the portfolio:

  1. grade >= 9/11          structural quality bar; grade <= 8 is a hard
                            block, no exceptions
  2. db_change >= 0.50      dealer positioning actively recovering toward
                            bullish; grade-11 DEEP names need only 0.30;
                            SUSTAINED names (delta pegged at 1.00 two
                            consecutive sessions) are exempt
  3. COTMP cushion >= 2.0%  spot far enough above the put-mass floor;
                            grade-11 DEEP and high-db_change names get a
                            1.0% exception
  4. no spike-crash         if the +GEX target is a prior spike high where
                            institutional selling already occurred, the
                            setup is blocked regardless of every other
                            filter (0/3 on the validated data)
  5. R/R >= 2.0             upside to +GEX vs downside to pTrans

Statuses off the evening scan:

  CONFIRMED  all filters pass, spot above pTrans, greenlit at the open
  PENDING    filters pass, spot within 0.5% below pTrans — watch the
             first candle
  BLOCKED    any filter failed, no entry
  WAIT       nothing failed but spot is too far below pTrans to be a
             candidate yet (not surfaced by the P2P scan)

The actual entry trigger is never the pre-market snapshot: it is the first
5-minute candle CLOSE above pTrans at the open. That confirmed close is
the signal — not the level, not the pre-market price. This eliminates
fakeouts and gap fills.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ScreenRow

GRADE_MIN = 9                 # 11-rule structural grade; <= 8 hard block
DB_CHANGE_MIN = 0.50          # delta balance change vs prior session
DB_CHANGE_MIN_DEEP = 0.30     # grade-11 DEEP exception
COTMP_CUSHION_MIN = 0.02      # spot >= 2.0% above center of put mass
COTMP_CUSHION_EXCEPTION = 0.01  # grade-11 DEEP / high-db_change exception
HIGH_DB_CHANGE = 1.00         # "high db_change" = a full-point swing: delta
                              # balance runs -1..+1 and pegs at 1.00, so a
                              # change >= 1.00 means positioning crossed the
                              # whole neutral zone in one session — a flip,
                              # not drift (2x the entry bar, the standard
                              # aggressive-repositioning read)
RR_MIN = 2.0                  # minimum upside:downside to qualify
PENDING_BAND = 0.005          # within 0.5% below pTrans -> PENDING

CONFIRMED = "CONFIRMED"
PENDING = "PENDING"
BLOCKED = "BLOCKED"
WAIT = "WAIT"


@dataclass
class FilterCheck:
    name: str
    passed: bool
    note: str = ""


@dataclass
class ScreenResult:
    symbol: str
    status: str                       # CONFIRMED | PENDING | BLOCKED | WAIT
    checks: list[FilterCheck] = field(default_factory=list)
    rr: float | None = None
    cushion: float | None = None

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def failed_filters(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]


def _deep11(row: ScreenRow) -> bool:
    return row.grade >= 11 and row.deep


def evaluate_filters(row: ScreenRow, price: float | None = None) -> list[FilterCheck]:
    """Run the five entry filters at ``price`` (defaults to spot).

    The R/R check is only decidable above pTrans; at or below the level it
    passes provisionally and is re-checked at the confirming 5-min close.
    """
    p = row.spot if price is None else price
    checks = []

    checks.append(FilterCheck(
        "grade", row.grade >= GRADE_MIN,
        f"grade {row.grade}/11 vs min {GRADE_MIN} (<= 8 is a hard block)"))

    if row.sustained:
        checks.append(FilterCheck(
            "db_change", True,
            "sustained: delta pegged at 1.00 two consecutive sessions, exempt"))
    else:
        db_min = DB_CHANGE_MIN_DEEP if _deep11(row) else DB_CHANGE_MIN
        checks.append(FilterCheck(
            "db_change", row.db_change >= db_min,
            f"db_change {row.db_change:+.2f} vs min {db_min:.2f}"))

    cushion = (p - row.cotmp) / row.cotmp
    c_min = COTMP_CUSHION_MIN
    if _deep11(row) or row.db_change >= HIGH_DB_CHANGE:
        c_min = COTMP_CUSHION_EXCEPTION
    checks.append(FilterCheck(
        "cotmp_cushion", cushion >= c_min,
        f"cushion {cushion:.1%} vs min {c_min:.1%}"))

    checks.append(FilterCheck(
        "spike_crash", not row.spike_crash,
        "+GEX target is a prior spike high — hard no" if row.spike_crash
        else "no spike-crash pattern"))

    rr = row.rr(p)
    if rr is None:
        checks.append(FilterCheck(
            "rr", True,
            "at/below pTrans — provisional, re-checked on the confirming close"))
    else:
        checks.append(FilterCheck(
            "rr", rr >= RR_MIN, f"R/R {rr:.2f} vs min {RR_MIN:.1f}"))

    return checks


def screen(row: ScreenRow) -> ScreenResult:
    """Evening scan classification: CONFIRMED / PENDING / BLOCKED / WAIT."""
    checks = evaluate_filters(row)
    cushion = row.cotmp_cushion
    rr = row.rr()

    if not all(c.passed for c in checks):
        status = BLOCKED
    elif row.spot > row.p_trans:
        status = CONFIRMED
    elif row.spot >= row.p_trans * (1 - PENDING_BAND):
        status = PENDING
    else:
        status = WAIT
    return ScreenResult(row.symbol, status, checks, rr, cushion)


def open_trigger(row: ScreenRow, first_5min_close: float) -> bool:
    """The entry signal: first 5-minute candle close above pTrans.

    Re-validates the filters at the confirming close (this is where a
    PENDING name's R/R becomes decidable). Not the level, not the
    pre-market price — the 5-min close.
    """
    if first_5min_close <= row.p_trans:
        return False
    return all(c.passed for c in evaluate_filters(row, price=first_5min_close))


def continuation_eligible(row: ScreenRow) -> bool:
    """B Continuation bucket structural bar (regime gate checked separately).

    Names already in confirmed uptrends pulling back into / breaking above
    a GEX level: Minervini score >= 100 plus the same five filters. The
    caller confirms clean staircase structure and that dealer positioning
    supports continuation; the full 3/3 regime gate is enforced in
    ``vol_desk.regime.approve``.
    """
    if row.minervini is None or row.minervini < 100:
        return False
    return all(c.passed for c in evaluate_filters(row))
