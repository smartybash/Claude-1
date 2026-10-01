"""Vol Desk regime overlay: three daily gates before approving new entries.

  basket gate     SPY or QQQ up more than 0.5% on the session — the market
                  needs to be showing follow-through
  bull:bear gate  more than 3.0:1 bull names to bear names across the full
                  700-name universe — below 3.0 the broader tape is not
                  confirming
  VIX delta gate  dealer positioning on VIX must be negative (bearish on
                  vol = bullish for equities)

Track requirements:

  P2P Track 1 (mechanical)   can run at 2/3 gates on strong individual
                             setups; 3/3 approves normally
  B Continuation bucket      requires all 3/3 before any entries

Credit / rotation overlay: HYG and sector ETF positioning are checked
daily. HYG going bear while equities stay bullish is a known divergence —
new entries get smaller sizing, not a shutdown.
"""

from __future__ import annotations

from dataclasses import dataclass

BASKET_MIN = 0.005          # SPY or QQQ session change must exceed +0.5%
BULL_BEAR_MIN = 3.0         # bull:bear ratio across the universe
TRACK1_MIN_GATES = 2        # P2P mechanical, strong setups only at 2/3
CONTINUATION_MIN_GATES = 3  # B Continuation: full gate, no exceptions
HYG_DIVERGENCE_SIZE = 0.5   # sizing factor on new entries during divergence

P2P = "P2P"
B_CONTINUATION = "B_CONTINUATION"


@dataclass
class GateReading:
    basket: bool
    bull_bear: bool
    vix: bool

    @property
    def count(self) -> int:
        return int(self.basket) + int(self.bull_bear) + int(self.vix)


def read_gates(
    spy_pct: float,
    qqq_pct: float,
    bull_names: int,
    bear_names: int,
    vix_dealer_delta: float,
) -> GateReading:
    """The daily 3-gate read. Session % changes as fractions (0.006 = +0.6%)."""
    basket = spy_pct > BASKET_MIN or qqq_pct > BASKET_MIN
    ratio = bull_names / bear_names if bear_names else float("inf")
    return GateReading(
        basket=basket,
        bull_bear=ratio > BULL_BEAR_MIN,
        vix=vix_dealer_delta < 0,
    )


def approve(track: str, gates: GateReading, strong_setup: bool = False) -> bool:
    """May this track take new entries today?

    B Continuation needs all three gates. P2P Track 1 needs all three too,
    unless the individual setup is strong — then 2/3 is enough.
    """
    if track == B_CONTINUATION:
        return gates.count >= CONTINUATION_MIN_GATES
    if track == P2P:
        if gates.count >= 3:
            return True
        return gates.count >= TRACK1_MIN_GATES and strong_setup
    raise ValueError(f"unknown track: {track}")


def size_factor(hyg_bear: bool, equities_bullish: bool) -> float:
    """Credit-divergence sizing overlay for new entries.

    HYG bear while equities stay bullish warrants smaller size — the trade
    still happens, but at HYG_DIVERGENCE_SIZE of normal.
    """
    return HYG_DIVERGENCE_SIZE if hyg_bear and equities_bullish else 1.0
