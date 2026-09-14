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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/intraday_long")
    ap.add_argument("--symbol", default="QQQ",
                    help="label for the output file; the payloads carry no "
                         "symbol of their own, so pulls for different symbols "
                         "must be harvested before the next symbol is pulled")
    a = ap.parse_args()

    frames, seen = [], 0
    for name, raw in payloads(RESULTS):
        d = pd.read_csv(io.StringIO(raw))
        if d.empty:
            continue
        frames.append(d)
        seen += 1
    if not frames:
        print("nothing to harvest")
        return

    d = pd.concat(frames, ignore_index=True)
    d["timestamp"] = pd.to_datetime(d.timestamp)
    d = (d.drop_duplicates(subset="timestamp")
           .sort_values("timestamp")
           .reset_index(drop=True))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{a.symbol}_5m.parquet"
    if f.exists():
        old = pd.read_parquet(f)
        d = (pd.concat([old, d], ignore_index=True)
               .drop_duplicates(subset="timestamp")
               .sort_values("timestamp")
               .reset_index(drop=True))
    d.to_parquet(f, index=False)

    days = d.timestamp.dt.date.nunique()
    print(f"{seen} payloads -> {len(d):,} bars, {days:,} sessions, "
          f"{d.timestamp.min():%Y-%m-%d} to {d.timestamp.max():%Y-%m-%d}")
    print(f"written to {f}")


if __name__ == "__main__":
    main()
