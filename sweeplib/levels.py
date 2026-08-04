"""Pre-session liquidity level sets.

Everything here is computable strictly before the session opens: prior-day
H/L, prior-week H/L, equal-highs/equal-lows pools built from CONFIRMED swing
pivots (a pivot at bar i needs k bars after it, so it only exists k bars
later - that lag is deliberate), and round numbers near the prior close.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Level:
    name: str
    price: float
    side: str  # "high": liquidity above (level from highs); "low": below


def swing_pivots(daily: pd.DataFrame, k: int = 2) -> tuple[pd.Series, pd.Series]:
    """Confirmed swing highs/lows on daily bars.

    H[i] must strictly exceed the highs of the k bars before AND after i
    (mirror for lows). Returned series are indexed by the pivot bar's date but
    a pivot is only *usable* k bars later; callers enforce that via as_of.
    """
    h, lo = daily["high"].values, daily["low"].values
    n = len(daily)
    ph, pl = [], []
    for i in range(k, n - k):
        if h[i] > h[i - k:i].max() and h[i] > h[i + 1:i + 1 + k].max():
            ph.append(i)
        if lo[i] < lo[i - k:i].min() and lo[i] < lo[i + 1:i + 1 + k].min():
            pl.append(i)
    return (
        pd.Series(h[ph], index=daily.index[ph]),
        pd.Series(lo[pl], index=daily.index[pl]),
    )


def equal_pools(
    pivots: pd.Series, tol_frac: float = 0.0012, min_touches: int = 2
) -> list[float]:
    """Cluster pivot prices within tol_frac; >=min_touches pivots = a pool.

    Returns the mean price of each qualifying cluster.
    """
    if len(pivots) < min_touches:
        return []
    prices = np.sort(pivots.values.astype(float))
    pools, cluster = [], [prices[0]]
    for p in prices[1:]:
        if abs(p - cluster[-1]) <= tol_frac * p:
            cluster.append(p)
        else:
            if len(cluster) >= min_touches:
                pools.append(float(np.mean(cluster)))
            cluster = [p]
    if len(cluster) >= min_touches:
        pools.append(float(np.mean(cluster)))
    return pools


def round_numbers(ref_price: float, step: float, n_each: int = 2) -> list[float]:
    """Nearest n_each multiples of `step` on each side of ref_price."""
    base = np.floor(ref_price / step) * step
    return [float(base + i * step) for i in range(-n_each + 1, n_each + 1)]


def volume_profile(bars: pd.DataFrame, n_bins: int = 50):
    """Volume-at-price for one session -> (POC, VAH, VAL).

    Each bar's volume is spread uniformly across the price bins its [low, high]
    range spans (a standard 5-min approximation - true tick profile needs tick
    data). POC = highest-volume bin center. Value area = the 70%-of-volume band
    grown outward from the POC by repeatedly annexing the richer adjacent bin
    (the Market Profile value-area rule). Returns None if the session is flat.
    """
    lo, hi = float(bars["low"].min()), float(bars["high"].max())
    if hi <= lo:
        return None
    edges = np.linspace(lo, hi, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vol = np.zeros(n_bins)
    for low, high, v in zip(bars["low"].values, bars["high"].values, bars["volume"].values):
        # skip malformed bars (NaN, or low>high from a bad feed) so the uniform
        # spread below never divides by a zero/negative bin span
        if not (np.isfinite(low) and np.isfinite(high) and np.isfinite(v)) or high < low:
            continue
        b_lo = max(0, int(np.searchsorted(edges, low, "right")) - 1)
        b_hi = min(n_bins - 1, int(np.searchsorted(edges, high, "right")) - 1)
        span = max(1, b_hi - b_lo + 1)
        vol[b_lo:b_hi + 1] += v / span
    if vol.sum() <= 0:
        return None
    poc_i = int(vol.argmax())
    target = 0.70 * vol.sum()
    lo_i = hi_i = poc_i
    acc = vol[poc_i]
    while acc < target and (lo_i > 0 or hi_i < n_bins - 1):
        up = vol[hi_i + 1] if hi_i < n_bins - 1 else -1.0
        dn = vol[lo_i - 1] if lo_i > 0 else -1.0
        if up >= dn:
            hi_i += 1
            acc += vol[hi_i]
        else:
            lo_i -= 1
            acc += vol[lo_i]
    return float(centers[poc_i]), float(centers[hi_i]), float(centers[lo_i])


def poc_session_levels(prior_bars: pd.DataFrame, ref_close: float, n_bins: int = 50) -> list[Level]:
    """Prior-session POC / VAH / VAL as pre-session levels for today.

    This is the "naked POC" family: yesterday's high-volume node and value-area
    edges, known before today's open. Side is assigned by position vs the prior
    close, the same convention used for round numbers and prior-week levels
    (these are in-range magnets with no fixed approach direction).
    """
    vp = volume_profile(prior_bars, n_bins)
    if vp is None:
        return []
    poc, vah, val = vp
    out = []
    for name, price in (("POC", poc), ("VAH", vah), ("VAL", val)):
        out.append(Level(name, price, "high" if price >= ref_close else "low"))
    return out


CATEGORIES = {
    "POC": "POC-family", "VAH": "POC-family", "VAL": "POC-family",
    "PDH": "prior-day", "PDL": "prior-day",
    "PWH": "prior-week", "PWL": "prior-week",
    "eqH": "equal-pool", "eqL": "equal-pool",
    "RN": "round-number",
}


def level_category(name: str) -> str:
    for prefix, cat in CATEGORIES.items():
        if name.startswith(prefix):
            return cat
    return "other"


def round_step(ref_price: float) -> float:
    """Round-number grid scaled to the live price (not hardcoded to a symbol):
    250 for NQ-scale prices, 50 for ES-scale, 10 for ETF-scale."""
    if ref_price >= 15000:
        return 250.0
    if ref_price >= 2000:
        return 50.0
    return 10.0


def session_levels(
    daily: pd.DataFrame,
    as_of: pd.Timestamp,
    pivot_k: int = 2,
    pool_tol: float = 0.0012,
    pool_lookback: int = 20,
    include_round: bool = True,
    merge_tol: float = 0.0005,
) -> list[Level]:
    """The full pre-session level set for the session dated `as_of`.

    Uses only daily bars strictly before as_of; pivots additionally need
    pivot_k bars of confirmation before as_of.
    """
    hist = daily[daily.index < as_of]
    if len(hist) < pivot_k * 2 + 2:
        return []
    prior = hist.iloc[-1]
    levels = [
        Level("PDH", float(prior["high"]), "high"),
        Level("PDL", float(prior["low"]), "low"),
    ]

    iso = hist.index.isocalendar()
    cur_week = pd.Timestamp(as_of).isocalendar()
    prior_weeks = hist[
        ~((iso["year"] == cur_week.year) & (iso["week"] == cur_week.week))
    ]
    if len(prior_weeks):
        wk = prior_weeks.index.isocalendar()
        last_wk = prior_weeks[
            (wk["year"] == wk["year"].iloc[-1]) & (wk["week"] == wk["week"].iloc[-1])
        ]
        levels.append(Level("PWH", float(last_wk["high"].max()), "high"))
        levels.append(Level("PWL", float(last_wk["low"].min()), "low"))

    # equal-H/L pools from confirmed pivots in the last pool_lookback sessions
    win = hist.iloc[-(pool_lookback + pivot_k):]
    ph, pl = swing_pivots(win, k=pivot_k)
    # confirmation: pivot at bar i needs k later bars, all inside `hist`, so
    # every pivot returned on `hist` is already confirmed as of `as_of`.
    for p in equal_pools(ph, pool_tol):
        levels.append(Level(f"eqH_{p:.0f}", p, "high"))
    for p in equal_pools(pl, pool_tol):
        levels.append(Level(f"eqL_{p:.0f}", p, "low"))

    if include_round:
        ref = float(prior["close"])
        for p in round_numbers(ref, round_step(ref)):
            side = "high" if p >= ref else "low"
            levels.append(Level(f"RN_{p:.0f}", p, side))

    # merge near-duplicates (same side, within merge_tol) so one physical
    # level can't produce two trades
    merged: list[Level] = []
    for lv in sorted(levels, key=lambda x: x.price):
        dup = next(
            (m for m in merged
             if m.side == lv.side and abs(m.price - lv.price) <= merge_tol * lv.price),
            None,
        )
        if dup is None:
            merged.append(lv)
        elif not dup.name.startswith(("PDH", "PDL", "PWH", "PWL")):
            # keep the structurally-named level over pools/round numbers
            if lv.name.startswith(("PDH", "PDL", "PWH", "PWL")):
                merged[merged.index(dup)] = lv
    return merged
