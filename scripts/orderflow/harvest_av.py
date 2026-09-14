#!/usr/bin/env python3
"""Collect Alpha Vantage intraday pulls out of the MCP tool-results directory.

The connector refuses to return a month of 5-minute bars inline -- roughly
100 KB per month -- and writes the payload to a file instead. That is not an
obstacle, it is the mechanism: it means years of intraday history can be
pulled without any of it passing through the conversation. Each call costs a
few hundred tokens of "saved to <path>" and leaves a megabyte of bars on disk.

This script sweeps that directory, parses every payload it finds, and folds
them into one parquet file per symbol. It is idempotent: rows are de-duplicated
on timestamp, so re-running after more pulls only adds what is new, and a month
pulled twice costs nothing.

Bars are RTH only (extended_hours=false) and unadjusted (adjusted=false) --
unadjusted because the gap a trader saw at the open is the one that matters,
and back-adjusting prices would erase it.

Usage: python3 scripts/orderflow/harvest_av.py [--out data/intraday_long]
"""
from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path

import pandas as pd

RESULTS = Path("/root/.claude/projects/-home-user-Claude-1/"
               "53a4adb9-543d-5460-95dd-0cda0b53172f/tool-results")
PREFIX = "mcp-Alpha_Vantage_MCP_Server-TIME_SERIES_INTRADAY-"
HEAD = "timestamp,open,high,low,close,volume"


def payloads(results: Path):
    """Every intraday CSV payload sitting in the tool-results directory."""
    for f in sorted(results.glob(PREFIX + "*.txt")):
        try:
            raw = json.loads(f.read_text())["result"]
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            continue
        if not isinstance(raw, str) or not raw.lstrip().startswith(HEAD):
            continue
        yield f.name, raw


def spacing_minutes(d: pd.DataFrame) -> int:
    """Bar interval, read off the data rather than trusted from the filename.

    The payloads carry no symbol and no interval, and the directory mixes
    every pull made in the session. The timestamps settle it: the modal gap
    between consecutive bars within a day IS the interval, so a 1-minute pull
    can never be folded into a 5-minute file by accident.
    """
    t = d.timestamp.sort_values()
    gaps = t.diff().dt.total_seconds().div(60).dropna()
    gaps = gaps[(gaps > 0) & (gaps <= 60)]
    return int(gaps.mode().iloc[0]) if len(gaps) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/intraday_long")
    ap.add_argument("--interval", type=int, default=5,
                    help="bar size in minutes; payloads at any other spacing "
                         "are left alone, so 1min and 5min pulls can share "
                         "the tool-results directory")
    ap.add_argument("--symbol", default="QQQ",
                    help="label for the output file; the payloads carry no "
                         "symbol of their own, so pulls for different symbols "
                         "must be harvested before the next symbol is pulled")
    a = ap.parse_args()

    frames, seen, skipped = [], 0, 0
    for name, raw in payloads(RESULTS):
        d = pd.read_csv(io.StringIO(raw))
        if d.empty:
            continue
        d["timestamp"] = pd.to_datetime(d.timestamp)
        if spacing_minutes(d) != a.interval:
            skipped += 1
            continue
        frames.append(d)
        seen += 1
    if not frames:
        print(f"nothing at {a.interval}min to harvest ({skipped} other pulls)")
        return

    d = pd.concat(frames, ignore_index=True)
    d = (d.drop_duplicates(subset="timestamp")
           .sort_values("timestamp")
           .reset_index(drop=True))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{a.symbol}_{a.interval}m.parquet"
    if f.exists():
        old = pd.read_parquet(f)
        d = (pd.concat([old, d], ignore_index=True)
               .drop_duplicates(subset="timestamp")
               .sort_values("timestamp")
               .reset_index(drop=True))
    d.to_parquet(f, index=False)

    days = d.timestamp.dt.date.nunique()
    print(f"{seen} payloads at {a.interval}min ({skipped} skipped) -> {len(d):,} bars, {days:,} sessions, "
          f"{d.timestamp.min():%Y-%m-%d} to {d.timestamp.max():%Y-%m-%d}")
    print(f"written to {f}")


if __name__ == "__main__":
    main()
