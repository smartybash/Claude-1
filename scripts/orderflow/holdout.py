#!/usr/bin/env python3
"""THE sealed-date register, and a guard that raises.

Written after RP-010 Stage 1 read all nine sealed NQ sessions. The seal had
been stated in prose in every proposal and enforced by code in exactly one
script (`session_profile.py`, which kept its own private copy of the list).
RP-010's loader filtered on measured resolution and session completeness and
never asked whether a date was sealed, so eight June sessions entered the
threshold warm-up and 23 July entered the discovery block.

A rule that lives in prose is not a rule. This module is the single register,
and `assert_unsealed` is the only acceptable way to satisfy it.

The same reasoning as the reserved-column lint: the fix is not to remember.
"""
from __future__ import annotations

# Eight June 2026 sessions plus 23 July 2026, sealed since the tape archive was
# first inventoried. Recorded here as a prefix and an explicit set because that
# is how they were declared.
SEALED_PREFIXES = ("202606",)
SEALED_DATES = frozenset({"20260723"})

# Spent by RP-010 Stage 1 (commit 3c5bcff) before the guard existed. Listed so
# that "sealed" and "still unread" are never again treated as the same claim.
SPENT_BY_RP010 = frozenset({
    "20260618", "20260622", "20260623", "20260624", "20260625",
    "20260626", "20260629", "20260630",          # threshold warm-up only
    "20260723",                                   # full discovery session
})


def is_sealed(day) -> bool:
    d = str(day)
    return d in SEALED_DATES or d.startswith(SEALED_PREFIXES)


def sealed_in(days) -> list:
    return sorted({str(d) for d in days if is_sealed(d)})


def assert_unsealed(days, ctx="") -> None:
    """RAISE if any sealed date is about to be read."""
    bad = sealed_in(days)
    if bad:
        raise ValueError(
            f"sealed date(s) {bad}" + (f" in {ctx}" if ctx else "")
            + " -- a sealed date may not be loaded, labelled, used for a"
              " trailing threshold, or counted. Filter with holdout.drop_sealed"
              " at the loader, not in a comment")


def drop_sealed(days) -> list:
    return [d for d in days if not is_sealed(d)]


def still_unread() -> frozenset:
    """Sealed dates that have never been read. Currently EMPTY."""
    return frozenset(SEALED_DATES | {  # the June eight, spelled out
        "20260618", "20260622", "20260623", "20260624",
        "20260625", "20260626", "20260629", "20260630"}) - SPENT_BY_RP010
