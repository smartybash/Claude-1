"""Forward-log dealer-gamma levels so a real backtest becomes possible.

WealthCharts built-in data is LIVE, not historical — so the only way to backtest
a gamma filter is to snapshot the levels each day and accumulate our own history.
Run this once per day AFTER filling data/gamma_levels.json from WealthCharts; it
appends a dated row per symbol to data/gamma_log.jsonl. After a few weeks that
log is enough to test the gamma-location filter honestly.

USAGE:  python3 scripts/log_gamma.py            # uses today's gamma_levels.json
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "gamma_log.jsonl"


def main():
    blob = json.loads((ROOT / "data" / "gamma_levels.json").read_text())
    date = blob.get("date") or dt.date.today().isoformat()
    levels = blob.get("levels") or {}
    rows, skipped = [], []
    for sym, lv in levels.items():
        vals = {k: v for k, v in (lv or {}).items() if v is not None}
        if not vals:
            skipped.append(sym); continue
        rows.append({"date": date, "sym": sym, "source": blob.get("source", ""), **vals})
    if not rows:
        print("nothing to log — gamma_levels.json has no filled values "
              f"(all null for {', '.join(skipped)}). Fill it from WealthCharts first.")
        return
    # de-dup same (date,sym): keep the latest write
    existing = []
    if LOG.exists():
        existing = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    keep = [r for r in existing if not any(r["date"] == n["date"] and r["sym"] == n["sym"] for n in rows)]
    with LOG.open("w") as f:
        for r in keep + rows:
            f.write(json.dumps(r) + "\n")
    print(f"logged {len(rows)} row(s) for {date}: {', '.join(r['sym'] for r in rows)}"
          + (f"  (skipped empty: {', '.join(skipped)})" if skipped else ""))
    print(f"gamma history now {len(keep)+len(rows)} rows -> {LOG}")


if __name__ == "__main__":
    main()
