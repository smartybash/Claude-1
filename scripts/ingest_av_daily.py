#!/usr/bin/env python3
"""Turn an Alpha Vantage TIME_SERIES_DAILY payload into a clean data/*.json.

AV daily (full) covers 20+ years — far longer than IBKR's 5y cap — so this is
the source for the deep backtest history. The MCP result is large and offloads
to a file; this reads that file (or a raw CSV/JSON paste) and writes the
canonical columnar shape {time,open,high,low,close,volume}, ascending, which
backtest_range_breakout.load_daily() prefers as <sym>_daily_full.json.

USAGE:
  python3 scripts/ingest_av_daily.py <raw_payload_path> <sym>_daily_full.json

Accepts any of:
  * {"result": "<csv>"}                (return_full_data=true offload)
  * {"sample_data": "<csv>", ...}      (preview wrapper — PARTIAL, warns)
  * raw CSV: timestamp,open,high,low,close,volume
  * AV JSON: {"Time Series (Daily)": {"YYYY-MM-DD": {"1. open":..}, ...}}
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
KEYS = ("time", "open", "high", "low", "close", "volume")


def _csv_to_rows(text):
    rows = list(csv.DictReader(io.StringIO(text.replace("\r", ""))))
    out = []
    for r in rows:
        out.append({
            "time": r["timestamp"], "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "volume": float(r["volume"]),
        })
    return out


def load_rows(path: Path):
    raw = path.read_text()
    partial = False
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return _csv_to_rows(raw), partial          # raw CSV file
    if isinstance(obj, dict) and "result" in obj:
        return _csv_to_rows(obj["result"]), partial
    if isinstance(obj, dict) and "sample_data" in obj:
        print("!! WARNING: this is a PREVIEW payload (partial). Re-pull with "
              "return_full_data=true for the complete history.", file=sys.stderr)
        return _csv_to_rows(obj["sample_data"]), True
    # AV native JSON
    ts = next((v for k, v in obj.items() if "Time Series" in k), None)
    if ts:
        out = []
        for d, bar in ts.items():
            out.append({"time": d,
                        "open": float(bar["1. open"]), "high": float(bar["2. high"]),
                        "low": float(bar["3. low"]),
                        "close": float(bar.get("4. close", bar.get("5. adjusted close"))),
                        "volume": float(bar.get("6. volume", bar.get("5. volume", 0)))})
        return out, partial
    raise ValueError("unrecognised payload shape")


def main():
    if len(sys.argv) != 3:
        print(__doc__); raise SystemExit(1)
    src = Path(sys.argv[1]); out = sys.argv[2]
    rows, partial = load_rows(src)
    df = pd.DataFrame(rows).drop_duplicates("time").sort_values("time")
    obj = {k: (df[k].tolist() if k != "time" else df["time"].tolist()) for k in KEYS}
    dest = ROOT / "data" / out
    dest.write_text(json.dumps(obj))
    tag = "  [PARTIAL PREVIEW]" if partial else ""
    print(f"wrote {dest}  ({len(df)} bars, {df['time'].iloc[0]} -> "
          f"{df['time'].iloc[-1]}){tag}")


if __name__ == "__main__":
    main()
