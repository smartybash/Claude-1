"""Pre-announcement driver framework for earnings trades.

A directional earnings position is only worth recommending when several
independent drivers agree BEFORE the report and that agreement has been
shown to predict the reaction on data the method never saw. This module
supplies the pieces:

  load_series       split-adjusted daily OHLCV from an Alpha Vantage CSV
  detect_reactions  earnings reaction sessions found from price/volume
                    (validated against confirmed report dates; see
                    scripts/earnings_backtest.py)
  drivers           eight pre-event drivers, each in {-1, 0, +1}, computed
                    strictly from data up to the decision close
  build_events      every historical event with its drivers and outcome

Timing convention: the REACTION session is the first session that trades
on the news (the day after a post-market report, the same day for a
pre-market one). The DECISION close is the session before it — the last
close at which a position can be opened ahead of the announcement.
"""

from __future__ import annotations

import csv
import io
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

# Known share splits since 1999 for the research universe. Each is
# confirmed against the price series (within +/-3 sessions) before it is
# applied; unconfirmed entries are reported, never silently used.
KNOWN_SPLITS: dict[str, list[tuple[str, float]]] = {
    "AAPL": [("2000-06-21", 2), ("2005-02-28", 2), ("2014-06-09", 7), ("2020-08-31", 4)],
    "MSFT": [("2003-02-18", 2)],
    "NVDA": [("2000-06-27", 2), ("2001-09-17", 2), ("2006-04-07", 2), ("2007-09-11", 1.5),
             ("2021-07-20", 4), ("2024-06-10", 10)],
    "AMD": [("2000-08-22", 2)],
    "INTC": [("2000-07-31", 2)],
    "QCOM": [("1999-12-31", 4)],
    "AVGO": [("2024-07-15", 10)],
    "ORCL": [("2000-01-19", 2), ("2000-10-13", 2)],
    "ADBE": [("2000-10-25", 2), ("2005-05-24", 2)],
    "CRM": [("2013-04-18", 4)],
    "NFLX": [("2004-02-12", 2), ("2015-07-15", 7), ("2025-11-17", 10)],
    "GOOGL": [("2014-04-03", 2), ("2022-07-18", 20)],
    "TSLA": [("2020-08-31", 5), ("2022-08-25", 3)],
    "COST": [("2000-01-14", 2)],
    "JPM": [("2000-06-12", 1.5)],
    "MU": [("2000-05-02", 2)],
    "NKE": [("2007-04-03", 2), ("2012-12-26", 2), ("2015-12-24", 2)],
}

DRIVERS = ("trend", "rel_strength", "runup", "prior_reaction", "post_drift",
           "near_high", "regime", "accumulation", "prior_surprise", "beat_streak")


@dataclass
class Series:
    sym: str
    dates: list[str]
    open: list[float]
    close: list[float]
    volume: list[float]
    splits: list[str] = field(default_factory=list)
    idx: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.idx = {d: i for i, d in enumerate(self.dates)}


def load_series(path: str | Path, sym: str | None = None) -> Series:
    """Daily OHLCV, back-adjusted for confirmed splits (prices and volume)."""
    raw = Path(path).read_text()
    if raw.lstrip().startswith("{"):
        raw = json.loads(raw)["result"]
    rows = sorted(csv.DictReader(io.StringIO(raw)), key=lambda r: r["timestamp"])
    sym = sym or Path(path).stem.upper()
    s = Series(sym, [r["timestamp"] for r in rows], [float(r["open"]) for r in rows],
               [float(r["close"]) for r in rows], [float(r["volume"]) for r in rows])
    for day, ratio in KNOWN_SPLITS.get(sym, []):
        i = _confirm_split(s, day, ratio)
        if i is None:
            s.splits.append(f"UNCONFIRMED {day} {ratio:g}:1 (not applied)")
            continue
        for j in range(i):
            s.open[j] /= ratio
            s.close[j] /= ratio
            s.volume[j] *= ratio
        s.splits.append(f"{s.dates[i]} {ratio:g}:1")
    return s


def _confirm_split(s: Series, day: str, ratio: float) -> int | None:
    """Session within +/-3 of `day` whose close-to-close ratio matches."""
    lo = next((i for i, d in enumerate(s.dates) if d >= day), None)
    if lo is None:
        return None
    # generous tolerance: the split is known to have happened, we only need
    # the session — and volatile names move a lot on split day (TSLA rose
    # 12.6% on its 2020 5:1, so the close ratio was 4.4)
    best, err = None, 0.25
    for i in range(max(1, lo - 3), min(len(s.dates), lo + 4)):
        e = abs((s.close[i - 1] / s.close[i]) / ratio - 1)
        if e < err:
            best, err = i, e
    return best


# ------------------------------------------------------- earnings dates

def load_earnings(path: str | Path) -> list[tuple[str, str, float | None]]:
    """(report date, 'pre'|'post', EPS surprise %) oldest first."""
    d = json.loads(Path(path).read_text())
    return sorted((tuple(e) for e in d["events"]), key=lambda e: e[0])


def abnormal_volume(s: Series, spy: Series, i: int) -> float:
    """Session volume over its trailing median, net of SPY's own spike."""
    if i < 65:
        return 0.0
    base = statistics.median(s.volume[i - 60:i - 5])
    if base <= 0:
        return 0.0
    j = spy.idx.get(s.dates[i])
    spy_vr = 1.0
    if j is not None and j >= 65:
        sb = statistics.median(spy.volume[j - 60:j - 5])
        spy_vr = max(1.0, spy.volume[j] / sb) if sb > 0 else 1.0
    return s.volume[i] / base / spy_vr


@dataclass
class Resolved:
    date: str            # report date as given
    label: str           # 'pre' / 'post' as given
    surprise: float | None
    r: int | None        # resolved reaction index (None if unusable)
    abn: float           # abnormal volume on the reaction session
    relabelled: bool     # volume contradicted the given timing


def resolve_reactions(s: Series, spy: Series, earnings) -> list[Resolved]:
    """Pin each report to its reaction session using volume.

    The reaction is the report day itself (pre-market) or the next session
    (post-market). The vendor's label stands unless the other session's
    abnormal volume clearly beats it (>= 1.5x and >= 2.0 absolute) — older
    labels are often wrong, but quiet quarters shouldn't be relabelled on
    noise. A report with no volume spike on either session is kept but
    flagged (abn < 1.5) for audit.
    """
    out = []
    for date, label, surprise in earnings:
        i = s.idx.get(date)
        if i is None:
            # report on a non-trading day: reaction is the next session
            nxt = next((k for k, d in enumerate(s.dates) if d > date), None)
            if nxt is None:
                continue
            out.append(Resolved(date, label, surprise, nxt, abnormal_volume(s, spy, nxt), False))
            continue
        if i + 1 >= len(s.dates):
            out.append(Resolved(date, label, surprise, None, 0.0, False))
            continue
        a0, a1 = abnormal_volume(s, spy, i), abnormal_volume(s, spy, i + 1)
        expected = i if label.startswith("pre") else i + 1
        a_exp, a_alt = (a0, a1) if expected == i else (a1, a0)
        alt = i + 1 if expected == i else i
        r = alt if a_alt >= max(2.0, 1.5 * a_exp) else expected
        out.append(Resolved(date, label, surprise, r, a0 if r == i else a1, r != expected))
    return out


# ------------------------------------------------------------ detection

def detect_reactions(s: Series, spy: Series, min_abn: float = 2.5, min_gap_z: float = 1.5,
                     spacing: int = 40) -> list[int]:
    """Earnings reaction sessions from abnormal volume plus an overnight gap.

    Abnormal volume is the session's volume over its trailing median,
    divided by the same ratio for SPY so market-wide spikes (crashes,
    index rebalances) don't qualify. The gap is measured in units of the
    stock's own recent daily volatility. Candidates are taken greedily by
    strength, at most one per `spacing` sessions (earnings are ~63 apart).
    """
    cands = []
    for i in range(65, len(s.dates)):
        base = statistics.median(s.volume[i - 60:i - 5])
        if base <= 0:
            continue
        vr = s.volume[i] / base
        j = spy.idx.get(s.dates[i])
        spy_vr = 1.0
        if j is not None and j >= 65:
            sb = statistics.median(spy.volume[j - 60:j - 5])
            spy_vr = max(1.0, spy.volume[j] / sb) if sb > 0 else 1.0
        abn = vr / spy_vr
        rets = [s.close[k] / s.close[k - 1] - 1 for k in range(i - 60, i)]
        sd = statistics.pstdev(rets) or 1e-9
        gap_z = abs(s.open[i] / s.close[i - 1] - 1) / sd
        if abn >= min_abn and gap_z >= min_gap_z:
            cands.append((abn * (1 + gap_z / 2), i))
    taken: list[int] = []
    for _, i in sorted(cands, reverse=True):
        if all(abs(i - t) >= spacing for t in taken):
            taken.append(i)
    return sorted(taken)


def reaction_index(s: Series, report: str, when: str) -> int | None:
    i = s.idx.get(report)
    if i is None:
        return None
    return i + 1 if when.startswith("post") else i


# -------------------------------------------------------------- drivers

def _sma(x: list[float], i: int, n: int) -> float | None:
    return sum(x[i - n + 1:i + 1]) / n if i >= n - 1 else None


def _ret(x: list[float], i: int, n: int) -> float | None:
    return x[i] / x[i - n] - 1 if i >= n else None


def drivers(s: Series, spy: Series, d: int, prior: list[int],
            prior_surprises: list[float | None] | None = None) -> dict[str, int] | None:
    """The ten pre-event drivers at decision index `d`.

    Uses only data at or before `d`. `prior` holds the reaction indices of
    earlier events for this stock (all < d), oldest first, and
    `prior_surprises` their EPS surprise % (already public at `d`).
    Returns None when there isn't enough history to compute them.
    """
    j = spy.idx.get(s.dates[d])
    if d < 260 or j is None or j < 60 or not prior:
        return None
    c, sc = s.close, spy.close
    sma50, sma200 = _sma(c, d, 50), _sma(c, d, 200)
    out: dict[str, int] = {}

    # 1. trend: price and moving averages stacked
    out["trend"] = 1 if c[d] > sma50 > sma200 else -1 if c[d] < sma50 < sma200 else 0

    # 2. relative strength vs SPY, 60 sessions
    rs = _ret(c, d, 60) - _ret(sc, j, 60)
    out["rel_strength"] = 1 if rs > 0.02 else -1 if rs < -0.02 else 0

    # 3. run-up into the print, 10 sessions, vs SPY
    ru = _ret(c, d, 10) - _ret(sc, j, 10)
    out["runup"] = 1 if ru > 0.02 else -1 if ru < -0.02 else 0

    # 4. previous earnings reaction (announcement-return drift)
    p = prior[-1]
    pr = c[p] / c[p - 1] - 1
    out["prior_reaction"] = 1 if pr > 0.01 else -1 if pr < -0.01 else 0

    # 5. drift since the previous reaction, vs SPY
    jp = spy.idx.get(s.dates[p])
    if jp is None:
        return None
    dr = (c[d] / c[p] - 1) - (sc[j] / sc[jp] - 1)
    out["post_drift"] = 1 if dr > 0.03 else -1 if dr < -0.03 else 0

    # 6. distance from the 52-week high
    hi = max(c[d - 251:d + 1])
    gap = c[d] / hi - 1
    out["near_high"] = 1 if gap > -0.05 else -1 if gap < -0.30 else 0

    # 7. market regime
    spy50 = _sma(sc, j, 50)
    r20 = _ret(sc, j, 20)
    out["regime"] = 1 if sc[j] > spy50 and r20 > 0 else -1 if sc[j] < spy50 and r20 < 0 else 0

    # 8. accumulation: up-volume minus down-volume, 20 sessions
    flow = sum(math.copysign(s.volume[k], c[k] - c[k - 1]) for k in range(d - 19, d + 1)
               if c[k] != c[k - 1])
    tot = sum(s.volume[d - 19:d + 1]) or 1
    out["accumulation"] = 1 if flow / tot > 0.15 else -1 if flow / tot < -0.15 else 0

    # 9. last quarter's EPS surprise (earnings-surprise drift)
    sp = [x for x in (prior_surprises or []) if x is not None]
    last = (prior_surprises or [None])[-1]
    out["prior_surprise"] = 0 if last is None else 1 if last > 2 else -1 if last < -2 else 0

    # 10. beat streak over the last four reports
    last4 = sp[-4:]
    if len(last4) < 4:
        out["beat_streak"] = 0
    else:
        beats = sum(1 for x in last4 if x > 0)
        out["beat_streak"] = 1 if beats == 4 else -1 if beats <= 2 else 0
    return out


@dataclass
class Event:
    sym: str
    date: str          # reaction session
    d: int             # decision index
    r: int             # reaction index
    ret: float         # decision close -> reaction close
    typical: float     # mean |reaction| of the previous 8 events
    rv_ratio: float    # 20-session / 120-session realised vol at decision
    drv: dict[str, int]


def build_events(s: Series, spy: Series, reactions: list[int],
                 surprises: list[float | None] | None = None) -> list[Event]:
    """Every event with >= 4 prior reports, its drivers and its outcome.

    `reactions` are reaction indices oldest first; `surprises` (same order)
    the EPS surprise of each report. A report's own surprise is never used
    for its own drivers — only earlier ones.
    """
    surprises = surprises or [None] * len(reactions)
    out = []
    for k, r in enumerate(reactions):
        if k < 4:
            continue
        d = r - 1
        prior = reactions[max(0, k - 8):k]
        drv = drivers(s, spy, d, prior, surprises[max(0, k - 8):k])
        if drv is None:
            continue
        typical = statistics.mean(abs(s.close[p] / s.close[p - 1] - 1) for p in prior)
        rets = [s.close[i] / s.close[i - 1] - 1 for i in range(d - 119, d + 1)]
        rv20, rv120 = statistics.pstdev(rets[-20:]), statistics.pstdev(rets)
        out.append(Event(s.sym, s.dates[r], d, r, s.close[r] / s.close[d] - 1,
                         typical, rv20 / rv120 if rv120 else 1.0, drv))
    return out


# ------------------------------------------------------------ statistics

def binom_p(k: int, n: int, p: float = 0.5) -> float:
    """Two-sided exact binomial p-value."""
    if n == 0:
        return 1.0
    def pmf(i):
        return math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                        + i * math.log(p) + (n - i) * math.log(1 - p))
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs * (1 + 1e-9)))
