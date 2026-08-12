"""Data model for the Vol Desk GEX swing system.

Two inputs feed the system every evening:

  gamma screen  master file, 700+ names: dealer delta balance (today and
                prior session), 11-rule structural grade, OI depth,
                Minervini momentum score, and the key GEX levels
                (pTrans, nTrans, zeroGEX, +GEX, COTMP, COTMC).
  P2P scan      filtered view of the screen where spot has already crossed
                above pTrans, with R/R and cushion to the +GEX target.

A ``ScreenRow`` is one name from the gamma screen; everything the entry
filters need lives on it. A ``Position`` is an open trade governed solely
by the exit framework in ``vol_desk.exits`` — entry filter logic never
applies to an open position.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Delta balance is "pegged" at this value; two consecutive pegged sessions
# make a name SUSTAINED (exempt from the db_change filter — it is not
# recovering, it is already fully positioned).
DB_PEGGED = 1.00
_EPS = 1e-9


@dataclass
class ScreenRow:
    """One name from the evening gamma screen."""

    symbol: str
    spot: float
    # --- GEX levels ---
    p_trans: float            # positive transition: the entry level
    n_trans: float            # negative transition: the structural stop
    plus_gex: float           # +GEX: the T1 target
    cotmp: float              # center of put mass: the structural floor
    zero_gex: float | None = None
    cotmc: float | None = None   # center of call mass: usual T2 candidate
    t2: float | None = None      # next structural level beyond +GEX
    # --- structure / positioning ---
    grade: int = 0               # 0-11 boolean structural rules passed
    deep: bool = False           # grade-11 DEEP designation
    delta_balance: float = 0.0   # dealer delta balance, this session
    delta_balance_prior: float | None = None
    db_change: float = 0.0       # delta balance change vs prior session
    spike_crash: bool = False    # +GEX target is a prior spike high
    minervini: float | None = None
    oi_depth: float | None = None

    @property
    def sustained(self) -> bool:
        """Delta balance pegged at 1.00 for two consecutive sessions."""
        return (
            self.delta_balance >= DB_PEGGED - _EPS
            and self.delta_balance_prior is not None
            and self.delta_balance_prior >= DB_PEGGED - _EPS
        )

    @property
    def cotmp_cushion(self) -> float:
        """How far spot sits above the center of put mass, as a fraction."""
        return (self.spot - self.cotmp) / self.cotmp

    def rr(self, price: float | None = None) -> float | None:
        """Upside to +GEX relative to downside to pTrans, at ``price``.

        Undefined (None) at or below pTrans — there is no downside leg to
        measure until spot is above the level.
        """
        p = self.spot if price is None else price
        if p <= self.p_trans:
            return None
        return (self.plus_gex - p) / (p - self.p_trans)


@dataclass
class Position:
    """An open trade. Only the exit framework governs it from here."""

    symbol: str
    entry: float
    p_trans: float
    n_trans: float
    t1: float                    # +GEX at entry
    t2: float | None = None      # next structural level (usually +GEX next or COTMC)
    day: int = 0                 # completed sessions held
    t1_hit: bool = False
    t1_locked: bool = False      # stop moved to entry, riding for T2
    stop: float | None = None    # active hard stop once T1 is locked
    progress_history: list[float] = field(default_factory=list)

    def progress(self, price: float) -> float:
        """Fraction of the entry -> T1 distance covered at ``price``."""
        return (price - self.entry) / (self.t1 - self.entry)
