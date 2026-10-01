"""GEX level engine — shared by the equity, QQQ and NQ daily runs.

Takes an option chain (strike, side, open interest, implied vol) and
produces the Vol Desk level set:

  zeroGEX        where dealer net gamma flips sign
  nTrans/pTrans  edges of the neutral band around the flip (|GEX| back to
                 BAND x the curve's peak)
  +GEX (T1)      strike carrying the most positive net gamma at spot
  T2             next positive-gamma strike above +GEX
  COTMP/COTMC    open-interest-weighted center of put / call mass

Convention: dealers are long calls and short puts, so per-strike net
gamma is (callOI - putOI) x gamma. Dollar gamma per 1% move is
  OI x gamma x multiplier x S^2 x 0.01
with multiplier 100 for equity/ETF options and 20 for NQ futures options.

Gamma as a function of *hypothetical* spot is required to trace the curve
(a vendor's per-contract gamma is only valid at the current spot), so the
curve is rebuilt with Black-Scholes using each contract's own implied
vol — keeping the vendor's volatility smile, which is the part that
actually matters for level placement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

RISK_FREE = 0.04
BAND = 0.05        # neutral-band edge as a fraction of peak |GEX|
GRID_PCT = 0.15    # scan spot +/- 15%
GRID_N = 601


@dataclass
class Leg:
    strike: float
    is_call: bool
    oi: int
    iv: float


def bs_gamma(spot: float, strike: float, iv: float, t: float) -> float:
    if t <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (RISK_FREE + 0.5 * iv * iv) * t) / (iv * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (spot * iv * math.sqrt(t))


def net_gex(spot: float, legs: list[Leg], t: float, mult: float) -> float:
    """Dealer dollar gamma per 1% move, in $M, if spot were at ``spot``."""
    total = 0.0
    for leg in legs:
        signed = leg.oi if leg.is_call else -leg.oi
        total += signed * bs_gamma(spot, leg.strike, leg.iv, t) * mult * spot * spot * 0.01
    return total / 1e6


def per_strike_gex(spot: float, legs: list[Leg], t: float, mult: float) -> dict[float, float]:
    out: dict[float, float] = {}
    for leg in legs:
        signed = leg.oi if leg.is_call else -leg.oi
        v = signed * bs_gamma(spot, leg.strike, leg.iv, t) * mult * spot * spot * 0.01 / 1e6
        out[leg.strike] = out.get(leg.strike, 0.0) + v
    return out


def levels(spot: float, legs: list[Leg], dte: float, mult: float = 100.0) -> dict:
    """Full Vol Desk level set for one underlying."""
    t = max(dte, 0.5) / 365
    lo, hi = spot * (1 - GRID_PCT), spot * (1 + GRID_PCT)
    grid = [lo + i * (hi - lo) / (GRID_N - 1) for i in range(GRID_N)]
    curve = [net_gex(s, legs, t, mult) for s in grid]
    peak = max((abs(v) for v in curve), default=0.0)

    crossings = [grid[i] for i in range(1, GRID_N) if curve[i - 1] * curve[i] < 0]
    zero_gex = n_trans = p_trans = None
    if crossings and peak > 0:
        zero_gex = crossings[len(crossings) // 2]
        n_trans = max((grid[i] for i in range(GRID_N)
                       if grid[i] < crossings[0] and curve[i] <= -BAND * peak), default=None)
        p_trans = min((grid[i] for i in range(GRID_N)
                       if grid[i] > crossings[-1] and curve[i] >= BAND * peak), default=None)

    ps = per_strike_gex(spot, legs, t, mult)
    pos = {k: v for k, v in ps.items() if v > 0}
    plus_gex = max(pos, key=pos.get) if pos else None
    t2 = None
    if plus_gex is not None:
        above = {k: v for k, v in pos.items() if k > plus_gex}
        t2 = max(above, key=above.get) if above else None

    call_oi = sum(l.oi for l in legs if l.is_call)
    put_oi = sum(l.oi for l in legs if not l.is_call)
    cotmc = (sum(l.strike * l.oi for l in legs if l.is_call) / call_oi) if call_oi else None
    cotmp = (sum(l.strike * l.oi for l in legs if not l.is_call) / put_oi) if put_oi else None

    out = {
        "spot": spot, "gex_at_spot": net_gex(spot, legs, t, mult),
        "zero_gex": zero_gex, "n_trans": n_trans, "p_trans": p_trans,
        "plus_gex": plus_gex, "t2": t2, "cotmp": cotmp, "cotmc": cotmc,
        "call_oi": call_oi, "put_oi": put_oi,
    }
    if cotmp:
        out["cushion"] = (spot - cotmp) / cotmp
    if p_trans and plus_gex and spot > p_trans and plus_gex > spot:
        out["rr"] = (plus_gex - spot) / (spot - p_trans)
    return out


def rescale(lv: dict, factor: float) -> dict:
    """Translate a level set into another instrument's units (QQQ -> NQ).

    Prices scale; ratios (cushion, R/R) are scale-invariant and carry over.
    """
    price_keys = ("spot", "zero_gex", "n_trans", "p_trans", "plus_gex", "t2", "cotmp", "cotmc")
    out = dict(lv)
    for k in price_keys:
        if lv.get(k) is not None:
            out[k] = lv[k] * factor
    return out
