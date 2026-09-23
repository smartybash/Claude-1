#!/usr/bin/env python3
"""Shared data-quality checks. Every study report prints the relevant ones.

Written for the RP-010 integrity audit. Each check here corresponds to a defect
that actually reached a report or a run: resolution inferred from file format,
duplicate files chosen by name, a completeness filter imported from the wrong
family, a split read as a market move, stale prints taken as trades.

Nothing here is remembered. Everything is measured from the prices.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def min_increment(prices) -> float:
    """Smallest non-zero gap between DISTINCT prices. The only resolution test.

    Never infer resolution from a filename or a header: the ledger records a
    plain .gz file at true 0.25 and its _run2 twin at 5.00, and a compact
    header declaring tick=0.25 for a file whose offsets are all multiples of 20.
    """
    u = np.unique(np.asarray(prices, float))
    if len(u) < 2:
        return float("nan")
    g = np.diff(u)
    g = g[g > 1e-9]
    return float(g.min()) if len(g) else float("nan")


def off_tick(prices, tick: float) -> float:
    """Fraction of prices that are not a whole multiple of the tick."""
    p = np.asarray(prices, float)
    r = np.abs(p / tick - np.round(p / tick))
    return float((r > 1e-6).mean())


def monotonic(ts) -> dict:
    t = pd.DatetimeIndex(pd.Series(ts).astype("datetime64[ns]"))
    d = t.to_series().diff().dropna()
    return dict(monotonic=bool((d >= pd.Timedelta(0)).all()),
                backsteps=int((d < pd.Timedelta(0)).sum()),
                max_gap_s=float(d.max().total_seconds()) if len(d) else np.nan)


def duplicate_dates(names, date_re=r"(\d{8})") -> dict:
    """Which dates appear in more than one file. Selection must then be by
    MEASURED quality, never by filename or extension."""
    import re
    out = {}
    for n in names:
        m = re.search(date_re, str(n))
        if m:
            out.setdefault(m.group(1), []).append(str(n))
    return {k: v for k, v in out.items() if len(v) > 1}


def bar_completeness(minutes, expected: int) -> dict:
    """Missing-bar report. Reported, NEVER silently used as a session filter --
    RP-006 lost 58% of its sessions to a filter imported from a family whose
    design actually read every bar."""
    m = np.asarray(minutes)
    return dict(bars=int(len(m)), expected=int(expected),
                missing=int(expected - len(m)),
                coverage=float(len(m) / expected) if expected else np.nan)


def staleness(close) -> dict:
    """Repeated-close diagnostics. EFA's 13.4% zero-return rate was the whole
    of RP-004's apparent lead-lag."""
    c = np.asarray(close, float)
    if len(c) < 2:
        return dict(zero_rate=np.nan, max_run=0)
    z = np.diff(c) == 0
    run = best = 0
    for v in z:
        run = run + 1 if v else 0
        best = max(best, run)
    return dict(zero_rate=float(z.mean()), max_run=int(best))


def split_scan(daily_close, thresh=0.5) -> list:
    """Session-close jumps large enough to be a corporate action, not a move.

    IJH's five-for-one at 2026-02-22 is the reference case: 280.84 -> 56.99.
    """
    c = pd.Series(np.asarray(daily_close, float))
    r = np.log(c).diff()
    idx = np.flatnonzero(np.abs(r.to_numpy()) > thresh)
    return [(int(i), float(c.iloc[i - 1]), float(c.iloc[i]),
             float(c.iloc[i - 1] / c.iloc[i])) for i in idx]


def roll_scan(prices, thresh_pts: float) -> dict:
    """Largest consecutive-print jump. A contract roll shows as a jump far
    larger than any single-print market move; RP-007 cleared its NQ block this
    way (max 65 points against a ~900-point roll basis)."""
    p = np.asarray(prices, float)
    if len(p) < 2:
        return dict(max_jump=np.nan, suspect=False)
    j = np.abs(np.diff(p))
    return dict(max_jump=float(j.max()), suspect=bool(j.max() > thresh_pts))


def report(name, **checks) -> str:
    """One-line-per-check block for a study report."""
    out = [f"  DATA QUALITY -- {name}"]
    for k, v in checks.items():
        out.append(f"    {k:<28}{v}")
    return "\n".join(out)


# ---------------------------------------------------------------- lint ------
# Three recurrences of the same defect -- DataFrame.pivot, .mod and .agg -- are
# three too many. Naming discipline is not allowed to depend on memory, so it
# lives here and in test_platform.py instead.

RESERVED = frozenset(a for a in dir(pd.DataFrame) if not a.startswith("_"))


def offending_columns(cols) -> list:
    """Column names that collide with a public pandas DataFrame attribute."""
    return sorted(str(c) for c in cols if str(c) in RESERVED)


def assert_safe_columns(df, ctx="") -> None:
    """RAISE on any column that shadows a pandas DataFrame method.

    Every frame a study builds passes through here. `df.agg` resolving to the
    method rather than the column is then impossible to ship.
    """
    bad = offending_columns(df.columns)
    if bad:
        raise ValueError(
            f"reserved pandas column name(s) {bad}"
            + (f" in {ctx}" if ctx else "")
            + " -- rename; bracket indexing is not an acceptable fix because "
              "it relies on remembering to use it every time")


def lint_reserved_columns(paths) -> list:
    """Static scan: reserved names used as DataFrame column keys.

    Flags `dict(agg=...)`, `{"pivot": ...}` and `df["mod"] = ...` patterns in
    source files. Heuristic by nature -- a false positive is cheap, a missed
    collision has cost this project three times.
    """
    import ast
    hits = []
    for p in paths:
        try:
            tree = ast.parse(Path(p).read_text())
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "dict":
                for kw in node.keywords:
                    if kw.arg in RESERVED:
                        hits.append((str(p), node.lineno, kw.arg, "dict() key"))
            elif isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                            and k.value in RESERVED:
                        hits.append((str(p), node.lineno, k.value, "dict literal"))
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Subscript) and \
                            isinstance(t.slice, ast.Constant) and \
                            isinstance(t.slice.value, str) and \
                            t.slice.value in RESERVED:
                        hits.append((str(p), node.lineno, t.slice.value,
                                     "column assignment"))
    return hits
