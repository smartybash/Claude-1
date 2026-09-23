#!/usr/bin/env python3
"""Order-flow primitives. Tested against synthetic fixtures before use.

The RP-010 gate: aggression, price progress and impact must return the KNOWN
answer on `fixtures.py` cases before any discovery outcome is read. Nothing
here reads a chart level, a strategy, or an outcome.

Conventions, declared once here rather than per study:
  * `aggressor` is 'B' when the trade lifted the offer and 'S' when it hit the
    bid. It is taken from the recorder, never inferred from the tick rule.
  * volume is contracts; a zero-volume row is a price print with no size and
    contributes to price progress but not to volume.
  * delta = buy volume - sell volume, signed the same way everywhere.
  * ZERO CASES are explicit: zero total volume gives imbalance 0.0, and zero
    progress gives impact 0.0 -- never NaN, never a division by zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def aggression(trades: pd.DataFrame, side_col="aggressor",
               vol_col="volume", px_col="price") -> dict:
    """Aggressive volume, delta and terminal-price concentration."""
    if not len(trades):
        return dict(buy_vol=0, sell_vol=0, delta=0, total=0, imbalance=0.0,
                    n_trades=0, n_prices=0, terminal_price=np.nan,
                    vol_at_terminal=0, buy_at_terminal=0, sell_at_terminal=0,
                    trades_at_terminal=0)
    s = trades[side_col].astype(str).str.upper().str[0]
    v = trades[vol_col].to_numpy(float)
    p = trades[px_col].to_numpy(float)
    buy = float(v[s.to_numpy() == "B"].sum())
    sell = float(v[s.to_numpy() == "S"].sum())
    total = buy + sell
    term = float(p[-1])
    at = p == term
    return dict(
        buy_vol=buy, sell_vol=sell, delta=buy - sell, total=total,
        imbalance=(abs(buy - sell) / total) if total > 0 else 0.0,
        n_trades=int(len(trades)), n_prices=int(len(np.unique(p))),
        terminal_price=term,
        vol_at_terminal=float(v[at].sum()),
        buy_at_terminal=float(v[at & (s.to_numpy() == "B")].sum()),
        sell_at_terminal=float(v[at & (s.to_numpy() == "S")].sum()),
        trades_at_terminal=int(at.sum()))


def progress(trades: pd.DataFrame, tick: float, px_col="price") -> dict:
    """Signed price progress and excursions WITHIN the window."""
    if not len(trades):
        return dict(signed=0.0, ticks=0, first=np.nan, last=np.nan,
                    max_up=0.0, max_dn=0.0)
    p = trades[px_col].to_numpy(float)
    first, last = float(p[0]), float(p[-1])
    signed = last - first
    return dict(signed=signed,
                ticks=int(round(abs(signed) / tick)) * (1 if signed >= 0 else -1)
                if signed != 0 else 0,
                first=first, last=last,
                max_up=float(p.max() - first), max_dn=float(first - p.min()))


def impact(agg: dict, prog: dict, atr=None) -> dict:
    """Price progress per unit of aggressive volume. The primary RP-010 object.

    `ticks_per_1k` is |ticks| per 1,000 aggressive contracts, with the sign of
    progress carried separately so buying and selling stay symmetric.
    """
    total = agg["total"]
    ticks = abs(prog["ticks"])
    per_1k = (1000.0 * ticks / total) if total > 0 else 0.0
    per_delta = (ticks / abs(agg["delta"])) if agg["delta"] != 0 else 0.0
    aligned = (np.sign(prog["signed"]) == np.sign(agg["delta"])
               and agg["delta"] != 0)
    return dict(ticks_per_1k=float(per_1k),
                ticks_per_delta=float(per_delta),
                signed_ticks=int(prog["ticks"]),
                aligned=bool(aligned),
                per_atr=(abs(prog["signed"]) / atr) if atr else np.nan)


def windows(trades: pd.DataFrame, seconds: int, overlap=False,
            time_col="time"):
    """Split a tape into fixed-length windows. Declared construction only.

    `overlap=False` gives non-overlapping windows anchored to the session
    start; `overlap=True` is NOT implemented here on purpose -- RP-010 must
    declare one construction before outcomes, and a rolling variant would make
    it trivially easy to try both.
    """
    if overlap:
        raise NotImplementedError(
            "rolling windows are deliberately unavailable: declare one "
            "construction before outcomes")
    t = pd.DatetimeIndex(trades[time_col])
    t0 = t[0].floor("s")
    idx = ((t - t0).total_seconds() // seconds).astype(int)
    for k, g in trades.groupby(idx):
        yield int(k), g
