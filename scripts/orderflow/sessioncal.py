#!/usr/bin/env python3
"""THE session calendar. One implementation, tested, used by every study.

Written for the RP-010 integrity audit. Before this module each study did its
own clock arithmetic, and two of them got it wrong in ways that reached a
report: the FOMC weekday was hardcoded to Wednesday, and RP-009's NQ arm used
the QQQ minute offset on a UTC tape and mislabelled every timestamp by four
hours.

RULES
  * Every time window in a study comes from here. No study computes its own
    offset, and no study hardcodes 570 or 810.
  * ET <-> UTC goes through zoneinfo, so DST is real rather than assumed.
  * Early closes are MEASURED from the data, not remembered. `early_closes()`
    derives them; a study passes the measured set in rather than trusting a
    literal list.

Usage: python3 scripts/orderflow/sessioncal.py     (self-check)
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Cash session, in EXCHANGE LOCAL TIME. These are the only literals here.
CASH_OPEN_ET = dt.time(9, 30)
CASH_CLOSE_ET = dt.time(16, 0)
EARLY_CLOSE_ET = dt.time(13, 0)
IB_END_ET = dt.time(10, 30)
# CME equity-index maintenance halt, local time
HALT_START_ET = dt.time(17, 0)
HALT_END_ET = dt.time(18, 0)
# FOMC statement release
FOMC_RELEASE_ET = dt.time(14, 0)


def _et(day, t: dt.time) -> dt.datetime:
    """Tz-aware ET datetime for a date and a local time."""
    d = pd.Timestamp(day).date() if not isinstance(day, dt.date) else day
    if isinstance(d, dt.datetime):
        d = d.date()
    return dt.datetime.combine(d, t, tzinfo=ET)


def et_to_utc(day, t: dt.time) -> dt.datetime:
    """Exchange local time -> UTC, with real DST."""
    return _et(day, t).astimezone(UTC)


def utc_offset_minutes(day) -> int:
    """Minutes UTC is ahead of ET on this date. 240 in EDT, 300 in EST."""
    return int(-_et(day, dt.time(12, 0)).utcoffset().total_seconds() // 60)


def open_minute_utc(day) -> int:
    """Minute-of-day, in UTC, of the cash open. 810 in EDT, 870 in EST."""
    u = et_to_utc(day, CASH_OPEN_ET)
    return u.hour * 60 + u.minute


def minutes_after_open(ts, day=None, clock="ET") -> np.ndarray:
    """Minutes after the cash open for a timestamp or array of timestamps.

    `clock` says what the NAIVE timestamps are expressed in. Passing "UTC" for
    a UTC tape and "ET" for an ET bar file is the whole point of this function:
    RP-009's four-hour error was calling the UTC branch with the ET constant.
    """
    idx = pd.DatetimeIndex(pd.Series(ts).astype("datetime64[ns]"))
    if day is None:
        day = idx[0].date()
    mins = idx.hour * 60 + idx.minute
    if clock.upper() == "ET":
        base = CASH_OPEN_ET.hour * 60 + CASH_OPEN_ET.minute
    elif clock.upper() == "UTC":
        base = open_minute_utc(day)
    else:
        raise ValueError(f"clock must be ET or UTC, got {clock!r}")
    return (mins - base).to_numpy()


def session_window(day, early=False, clock="ET"):
    """(open, close) minute-of-day in the requested clock."""
    close_t = EARLY_CLOSE_ET if early else CASH_CLOSE_ET
    if clock.upper() == "ET":
        o = CASH_OPEN_ET.hour * 60 + CASH_OPEN_ET.minute
        c = close_t.hour * 60 + close_t.minute
    else:
        a, b = et_to_utc(day, CASH_OPEN_ET), et_to_utc(day, close_t)
        o, c = a.hour * 60 + a.minute, b.hour * 60 + b.minute
    return o, c


def session_minutes(day, early=False) -> int:
    """Length of the cash session in minutes. 390 normally, 210 on an early."""
    o, c = session_window(day, early=early, clock="ET")
    return c - o


def ib_end_minute() -> int:
    """Minutes after the open at which the Initial Balance is COMPLETE.

    A level defined by the IB is not knowable before this bar, which is the
    look-ahead RP-007 shipped and this constant exists to prevent.
    """
    return (IB_END_ET.hour * 60 + IB_END_ET.minute) - \
           (CASH_OPEN_ET.hour * 60 + CASH_OPEN_ET.minute)


def fomc_release_minute() -> int:
    """Minutes after the open of the FOMC statement. 270."""
    return (FOMC_RELEASE_ET.hour * 60 + FOMC_RELEASE_ET.minute) - \
           (CASH_OPEN_ET.hour * 60 + CASH_OPEN_ET.minute)


def halt_window_utc(day):
    """CME maintenance halt in UTC minute-of-day, for the given date."""
    a = et_to_utc(day, HALT_START_ET)
    b = et_to_utc(day, HALT_END_ET)
    return a.hour * 60 + a.minute, b.hour * 60 + b.minute


def early_closes(bars: pd.DataFrame, ts_col="timestamp", clock="ET",
                 tol_min=30) -> set:
    """MEASURE which sessions closed early. Never remembered, always derived.

    A session is an early close when its last bar is more than `tol_min`
    before the regular close. Returns a set of dates.
    """
    d = bars[[ts_col]].copy()
    d["ts"] = pd.to_datetime(d[ts_col])
    d["day"] = d["ts"].dt.normalize()
    out = set()
    for day, g in d.groupby("day"):
        last = g["ts"].max()
        m = last.hour * 60 + last.minute
        _o, c = session_window(day.date(), early=False, clock=clock)
        if c - m > tol_min:
            out.add(day.date())
    return out


def dst_transitions(year: int):
    """(spring forward, fall back) US dates for a year, derived not recalled."""
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    offs = [utc_offset_minutes(d.date()) for d in days]
    spring = fall = None
    for i in range(1, len(offs)):
        if offs[i - 1] == 300 and offs[i] == 240:
            spring = days[i].date()
        if offs[i - 1] == 240 and offs[i] == 300:
            fall = days[i].date()
    return spring, fall


if __name__ == "__main__":
    print("session calendar self-check")
    for d in ("2026-01-15", "2026-06-18", "2026-11-05"):
        day = pd.Timestamp(d).date()
        print(f"  {d}  UTC offset {utc_offset_minutes(day)} min  "
              f"open minute UTC {open_minute_utc(day)}  "
              f"session {session_minutes(day)} min")
    for y in (2025, 2026):
        print(f"  {y} DST transitions: {dst_transitions(y)}")
    print(f"  IB completes {ib_end_minute()} min after the open")
    print(f"  FOMC release {fomc_release_minute()} min after the open")
