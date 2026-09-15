#!/usr/bin/env python3
"""Convert Alpha Vantage TIME_SERIES_INTRADAY payloads into the monthly 5-min
CSVs the intraday backtests read (data/intraday/qqq_5m_YYYY-MM.csv).

Each AV monthly pull (interval=5min, month=YYYY-MM, extended_hours=false,
return_full_data=true) offloads to a tool-result file shaped {"result": "<csv>"}
with header timestamp,open,high,low,close,volume in ET. Point this at the folder
of those files; it writes one CSV per month (month derived from the data), which
backtest_tos_fvg.load_sessions globs.

Usage:
  python3 scripts/ingest_av_intraday.py <folder> [--sym qqq] [--glob '*TIME_SERIES_INTRADAY*']
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sym", default="qqq")
    ap.add_argument("--interval", default="5m")
    ap.add_argument("--glob", default="*TIME_SERIES_INTRADAY*")
    a = ap.parse_args()
    outdir = ROOT / "data" / "intraday"
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for f in sorted(glob.glob(str(Path(a.folder) / a.glob))):
        try:
            obj = json.loads(Path(f).read_text())
        except Exception:
            continue
        csv = obj.get("result") if isinstance(obj, dict) else None
        if not csv or not csv.strip():
            continue
        csv = csv.replace("\r", "")
        lines = csv.splitlines()
        if len(lines) < 2:
            continue
        month = lines[1].split(",")[0][:7]          # YYYY-MM from first data row
        out = outdir / f"{a.sym}_{a.interval}_{month}.csv"
        out.write_text(csv if csv.endswith("\n") else csv + "\n")
        written.append((month, len(lines) - 1))
    for m, n in sorted(written):
        print(f"  {m}: {n} bars")
    print(f"wrote {len(written)} monthly files to {outdir}")


if __name__ == "__main__":
    main()
