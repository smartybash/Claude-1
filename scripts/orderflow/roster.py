#!/usr/bin/env python3
"""WHICH SESSIONS ARE DISCOVERY AND WHICH ARE HOLDOUT.

The split was written down as a count -- "46 sessions" -- and a count is not a
roster. Sessions kept arriving, the count kept being restated, and nothing in
the code could say whether a given date was on one side of the line or the
other. That is the exact mechanism by which a holdout quietly stops being one,
so the split is pinned here, by date, once.

    DISCOVERY   2026-07-01 .. 2026-09-08
    HOLDOUT     everything else, plus 2026-07-23

The window is the set of dates that were on disk when the three exit variants
were measured and pre-registered. 23 July sits inside it but was never
recorded, so no fit has ever seen it; it is holdout on the rule that matters --
whether the discovery analysis could have looked at it -- and saying so here,
before any holdout number exists, is what keeps that from being a convenient
decision later.

Two corrections are baked in, and both cost sessions rather than adding them:

  * The pre-registration said 46 discovery sessions. Counting the window gives
    47 usable. The earlier figure was a tally kept by hand across batches and
    it drifted; the window is checkable and is what governs from here.

  * September 2, 3, 4 and 8 were previously called holdout. They were on disk
    when the discovery table was last restated, so they cannot be trusted as
    unseen. They move to discovery. That shrinks the holdout from 7 to 3 before
    the June backfill puts it back to 7, and shrinking is the only direction a
    reclassification is allowed to go once it is ambiguous.

Usage: python3 scripts/orderflow/roster.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import is_full_session, load_all                                 # noqa

DISCOVERY_FROM = "20260701"
DISCOVERY_TO = "20260908"

# In the window by date, but never recorded, so never fitted.
HOLDOUT_INSIDE_WINDOW = {"20260723"}


def is_discovery(day: str) -> bool:
    if day in HOLDOUT_INSIDE_WINDOW:
        return False
    return DISCOVERY_FROM <= day <= DISCOVERY_TO


def split(days: dict) -> tuple[dict, dict, dict]:
    """(discovery, holdout, rejected) -- rejected is not a third sample.

    A session that is not a full cash day is dropped from both sides. It is not
    evidence for or against anything; the tested rule is simply not defined on
    it.
    """
    disc, hold, bad = {}, {}, {}
    for d, x in sorted(days.items()):
        if not is_full_session(x):
            bad[d] = x
        elif is_discovery(d):
            disc[d] = x
        else:
            hold[d] = x
    return disc, hold, bad


def main():
    days = load_all()
    disc, hold, bad = split(days)
    print("=" * 78)
    print("SESSION ROSTER")
    print("=" * 78)
    print(f"  discovery window {DISCOVERY_FROM} .. {DISCOVERY_TO}\n")
    for name, g in (("DISCOVERY", disc), ("HOLDOUT", hold),
                    ("NOT A FULL SESSION", bad)):
        print(f"  {name:<20}{len(g):>3}  " +
              " ".join(d[4:] for d in sorted(g)))
    print()
    print(f"  The holdout is evaluated ONCE, when it is complete. Nothing in")
    print(f"  this file reads a price.")


if __name__ == "__main__":
    main()
