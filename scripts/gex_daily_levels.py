#!/usr/bin/env python3
"""Per-day dealer-gamma levels for the ThinkOrSwim study.

The chart used to bake ONE set of walls and draw them flat across all history,
so reviewing a trade from three weeks ago showed today's walls against that
day's price action. This emits the levels DAY BY DAY, each taken from the
option chain of the PRIOR session — i.e. exactly what was on the screen
pre-market that morning, no lookahead. That makes historical review honest and
matches what the backtests already do (backtest_style_by_regime.lookup_prior).

Two emission modes:
  absolute  (QQQ)  — the wall price itself, straight from the QQQ chain
  ratio     (MNQ/MES) — wall / spot, a dimensionless number that thinkScript
                        multiplies by the instrument's own prior daily close.
                        Futures have no per-day option history here, so this
                        is the QQQ read transposed onto the future; it inherits
                        QQQ's skew (see ib_nq_gex.py for the native NQ read,
                        which is more accurate but only available for today).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = (("gamma_flip", "GF"), ("call_wall", "CW"), ("put_wall", "PW"))


def load_reads(src_sym: str | None = None):
    """Chronological option reads: date -> levels (+ spot for ratios).

    src_sym filters to one logged symbol (e.g. 'QQQ' for the Nasdaq family,
    'SPY' for the S&P family) so a chart doesn't mix QQQ and SPY reads on the
    same date. Falls back to all-with-spot when src_sym isn't in the log."""
    out = []
    f = ROOT / "data" / "gex_history.jsonl"
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("spot"):
            out.append(r)
    if src_sym and any(r.get("sym") == src_sym for r in out):
        out = [r for r in out if r.get("sym") == src_sym]
    out.sort(key=lambda r: r["date"])
    return out


def _vals(read, mode):
    vals = {}
    for key, tag in KEYS:
        v = read.get(key)
        if v is not None:
            vals[tag] = (v / read["spot"]) if mode == "ratio" else v
    return vals


def pairs(n_days: int, mode: str, today: str | None = None, src_sym: str | None = None):
    """[(YYYYMMDD of the SESSION, {GF/CW/PW: value}), ...] using the PRIOR read."""
    reads = load_reads(src_sym)
    rows = []
    for prev, cur in zip(reads, reads[1:]):
        # `cur` is the next session we have a record for; the read available
        # pre-market that day is `prev`.
        v = _vals(prev, mode)
        if v:
            rows.append((cur["date"].replace("-", ""), v))
    # the newest read has no following record yet — it is TODAY's pre-market data
    if today:
        last = reads[-1]
        if today.replace("-", "") > last["date"].replace("-", ""):
            v = _vals(last, mode)
            if v:
                rows.append((today.replace("-", ""), v))
    return rows[-n_days:]


def block(sym: str, mode: str, n_days: int = 120, today: str | None = None,
          today_native: dict | None = None) -> str:
    """thinkScript: per-day levels selected by GetYYYYMMDD().

    today_native: absolute levels for the CURRENT session that beat the scaled
    read (e.g. the NQ-native FOP computation). Applied only to today's date."""
    src = {"MNQ": "QQQ", "QQQ": "QQQ", "NQ": "QQQ",
           "MES": "SPY", "SPY": "SPY", "ES": "SPY"}.get(sym.upper())
    rows = pairs(n_days, mode, today, src)
    if not rows:
        return "# ---- per-day gamma levels: no history available ----"
    # NOTE: showGL is declared once in the study's own input block — do NOT
    # declare it here or thinkScript errors with "Identifier Already Used".
    L = [f"# ---- PER-DAY DEALER GAMMA ({len(rows)} sessions) ----",
         "#   Each day shows the walls from the PRIOR session's option chain —",
         "#   what you actually had pre-market that morning. Scroll back and the",
         "#   levels change with the date instead of showing today's everywhere.",
         "def dt = GetYYYYMMDD();"]
    if mode == "ratio":
        L += ["#   futures: levels are stored as a fraction of the underlying's spot",
              "#   and rescaled by this instrument's prior daily close.",
              "def anchor = close(period = AggregationPeriod.DAY)[1];"]
    for tag, plotn, col, style, lw in (("GF", "GFlip", "Color.WHITE", "Curve.FIRM", 2),
                                       ("CW", "CWall", "Color.RED", "Curve.LONG_DASH", 3),
                                       ("PW", "PWall", "Color.GREEN", "Curve.LONG_DASH", 3)):
        terms = []
        for d, vals in rows:
            if tag in vals:
                v = f"{vals[tag]:.6f}" if mode == "ratio" else f"{vals[tag]:.2f}"
                terms.append(f"if dt == {d} then {v}")
        if not terms:
            continue
        expr = " else ".join(terms) + " else Double.NaN"
        scale = " * anchor" if mode == "ratio" else ""
        L.append(f"def {plotn}v = {expr};")
        nat = (today_native or {}).get(tag)
        if nat is not None and today:
            L.append(f"def {plotn}nat = if dt == {today.replace('-','')} then {nat:.2f} "
                     f"else Double.NaN;   # native read, beats the scaled one")
            L.append(f"plot {plotn} = if !showGL then Double.NaN "
                     f"else if !IsNaN({plotn}nat) then {plotn}nat "
                     f"else if !IsNaN({plotn}v) then {plotn}v{scale} else Double.NaN;")
        else:
            L.append(f"plot {plotn} = if showGL and !IsNaN({plotn}v) then {plotn}v{scale} else Double.NaN;")
        L.append(f"{plotn}.SetDefaultColor({col});  {plotn}.SetStyle({style});  "
                 f"{plotn}.SetLineWeight({lw});")
    return "\n".join(L)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="MNQ")
    ap.add_argument("--mode", choices=("absolute", "ratio"), default="ratio")
    ap.add_argument("--days", type=int, default=120)
    a = ap.parse_args()
    print(block(a.sym, a.mode, a.days))
