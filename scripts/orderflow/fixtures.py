#!/usr/bin/env python3
"""Synthetic fixtures where the correct answer is known by construction.

Every fixture here exists because a defect of the same shape reached a run or a
report. The test suite asserts the harness returns the KNOWN answer, so the
answer cannot be inferred from the fact that a script completed.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd


def bars(minutes, highs, lows, closes, day="2026-06-18", clock="ET"):
    """Minute bars at declared minutes-after-open, in the declared clock."""
    d = pd.Timestamp(day)
    base = 9 * 60 + 30 if clock == "ET" else 13 * 60 + 30
    ts = [d + pd.Timedelta(minutes=int(base + m)) for m in minutes]
    return pd.DataFrame(dict(timestamp=ts, high=highs, low=lows, close=closes))


# ---------------------------------------------------------------- timezone --
TZ_CASES = [
    # (date, expected UTC offset minutes, expected open minute in UTC)
    ("2026-01-15", 300, 870),      # EST
    ("2026-06-18", 240, 810),      # EDT -- the RP-009 case
    ("2026-03-07", 300, 870),      # day before spring forward
    ("2026-03-09", 240, 810),      # day after spring forward
    ("2026-10-31", 240, 810),      # before fall back
    ("2026-11-02", 300, 870),      # after fall back
]
DST_2026 = (dt.date(2026, 3, 8), dt.date(2026, 11, 1))


# ------------------------------------------------------------ IB lookahead --
def ib_fixture():
    """IB high is set at minute 20 and is BEATEN at minute 75.

    A correct harness reports IB high = 105 and records NO interaction with it
    before minute 60. The RP-007 defect entered on the bar that SET the high.
    """
    m = list(range(0, 130))
    hi, lo, cl = [], [], []
    for i in m:
        if i == 20:
            hi.append(105.0); lo.append(100.0); cl.append(101.0)
        elif i == 75:
            hi.append(107.0); lo.append(104.0); cl.append(106.0)
        else:
            hi.append(102.0); lo.append(100.0); cl.append(101.0)
    return bars(m, hi, lo, cl), dict(ib_high=105.0, ib_low=100.0,
                                     first_legal_touch_minute=75)


# ------------------------------------------------- approach side / crossing --
def approach_fixture():
    """Price sits ABOVE 100 then comes down to it, then goes BELOW and back up.

    Bar 2 approaches 100 from above  -> SUPPORT test.
    Bar 6 approaches 100 from below  -> RESISTANCE test.
    A touch-only implementation sees bar 4 (range spans 100) as an event; a
    crossing implementation does not, because it never left the zone.
    """
    #      0      1      2*     3      4      5      6*     7
    # zone is [99.5, 100.5]; * marks the two intended entries
    m = [0, 1, 2, 3, 4, 5, 6, 7]
    hi = [110, 108, 101, 98, 97, 96, 100, 104]
    lo = [106, 104, 99, 96, 95, 94, 98, 102]
    cl = [107, 105, 100, 97, 96, 95, 99, 103]
    # bar 2: previous bar sits entirely ABOVE the zone -> SUPPORT test
    # bar 6: previous bar sits entirely BELOW the zone -> RESISTANCE test
    # bars 3-5 are below the zone and never re-enter it, so a CROSSING
    # implementation records nothing there; a touch implementation would.
    return bars(m, hi, lo, cl), dict(level=100.0, half=0.5,
                                     support_bars=[2], resistance_bars=[6])


# ------------------------------------------------- stop / target sequencing --
def barrier_fixture():
    """Three paths with a KNOWN first barrier.

    entry 100, stop 99, target 102 (long)
      path A: target only            -> +1
      path B: stop only              -> -1
      path C: one bar spans both     -> ambiguous; adverse-first says -1
    """
    A = bars([0, 1, 2], [100.5, 102.5, 103], [99.5, 101, 102], [100, 102, 102.5])
    B = bars([0, 1, 2], [100.5, 100.2, 100], [99.5, 98.5, 98], [100, 99, 98.5])
    C = bars([0, 1, 2], [100.5, 102.5, 101], [99.5, 98.5, 100], [100, 101, 100.5])
    return dict(A=(A, 1, False), B=(B, -1, False), C=(C, -1, True)), \
        dict(entry=100.0, stop=99.0, target=102.0)


# ------------------------------------------------------------- split adjust --
def split_fixture():
    """Five-for-one on day 3. A split scan must flag day 3 and only day 3."""
    c = [260.0, 262.0, 261.0, 52.4, 52.8, 53.1]
    return c, dict(split_index=3, ratio=5.0)


# --------------------------------------------------- aggressor / delta / OF --
def tape_fixture():
    """A tape with KNOWN aggressor labels and a KNOWN delta.

    12 trades. Buys (B) 7 contracts, sells (S) 5 -> delta +2, total 12.
    Terminal price 100.75, with 3 contracts traded there, 2 of them buys.
    Price progress open->close = +0.75 over 3 ticks.
    """
    t0 = pd.Timestamp("2026-06-18 13:30:00")
    #  price   vol side      running buy / sell
    rows = [
        (0.0, 100.00, 1, "B"),   # B 1   S 0
        (0.1, 100.00, 1, "S"),   # B 1   S 1
        (0.2, 100.25, 2, "B"),   # B 3   S 1
        (0.3, 100.25, 1, "S"),   # B 3   S 2
        (0.4, 100.50, 2, "B"),   # B 5   S 2
        (0.5, 100.50, 1, "S"),   # B 5   S 3
        (0.6, 100.75, 2, "B"),   # B 7   S 3
        (0.7, 100.75, 1, "S"),   # B 7   S 4
        (0.8, 100.75, 1, "B"),   # B 8   S 4
        (0.9, 100.75, 1, "S"),   # B 8   S 5
    ]
    df = pd.DataFrame(
        [(t0 + pd.Timedelta(seconds=s), p, v, a) for s, p, v, a in rows],
        columns=["time", "price", "volume", "aggressor"])
    # buys 1+2+2+2+1 = 8 ; sells 1+1+1+1+1 = 5 ; total 13 ; delta +3
    # terminal price is the LAST print, 100.75; 5 contracts traded there,
    # 3 of them buys. First 100.00 -> last 100.75 is +0.75 = 3 ticks.
    return df, dict(buy_vol=8, sell_vol=5, delta=3, total=13,
                    n_trades=10, n_prices=4,
                    first_price=100.00, last_price=100.75,
                    terminal_price=100.75, vol_at_terminal=5,
                    buy_at_terminal=3, ticks_progressed=3)


def absorption_fixture():
    """Heavy one-sided aggression, almost no progress -- State B by design.

    200 buy contracts, 10 sell, price moves one tick. Impact per 1,000
    aggressive contracts is 1 tick / 210 contracts.
    """
    t0 = pd.Timestamp("2026-06-18 14:00:00")
    rows = []
    for i in range(40):
        rows.append((t0 + pd.Timedelta(seconds=i * 0.5), 100.00, 5, "B"))
    for i in range(2):
        rows.append((t0 + pd.Timedelta(seconds=20 + i), 100.00, 5, "S"))
    rows.append((t0 + pd.Timedelta(seconds=25), 100.25, 0, "B"))
    df = pd.DataFrame(rows, columns=["time", "price", "volume", "aggressor"])
    return df, dict(buy_vol=200, sell_vol=10, delta=190, total=210,
                    ticks_progressed=1, one_sided=True, low_impact=True)


def initiative_fixture():
    """One-sided aggression with large progress -- State A by design.

    60 buy contracts, 5 sell, price moves 12 ticks.
    """
    t0 = pd.Timestamp("2026-06-18 14:10:00")
    rows = []
    px = 100.00
    for i in range(12):
        rows.append((t0 + pd.Timedelta(seconds=i * 0.5), px, 5, "B"))
        px += 0.25
    rows.append((t0 + pd.Timedelta(seconds=10), px, 5, "S"))
    df = pd.DataFrame(rows, columns=["time", "price", "volume", "aggressor"])
    return df, dict(buy_vol=60, sell_vol=5, delta=55, total=65,
                    ticks_progressed=12, one_sided=True, low_impact=False)


# ------------------------------------------------------------- control ------
def ranking_fixture():
    """Three instruments, five dates, with a KNOWN (strong, weak) assignment
    and outcomes that differ by identity.

    A correct shuffled control permutes the IDENTITY across dates; the RP-006
    defect permuted the outcome COLUMN, which leaves every mean unchanged.
    """
    rng = np.random.default_rng(7)
    n = 200
    strong = rng.choice(["X", "Y", "Z"], n)
    weak = np.array([rng.choice([c for c in "XYZ" if c != s]) for s in strong])
    out = {c: rng.normal(0, 1, n) for c in "XYZ"}
    # inject a real identity effect: X outperforms when it is the strong name
    out["X"] = out["X"] + 2.0 * (strong == "X")
    return pd.DataFrame(dict(strong=strong, weak=weak, **out))
