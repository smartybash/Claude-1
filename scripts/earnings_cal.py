"""Refresh data/earnings_calendar.json from saved Alpha Vantage EARNINGS_CALENDAR
outputs (the forward mega-cap report dates that widen the next QQQ session).

In the cloud sandbox, fetch each name with the MCP tool and save its output to a
file, then run this over the files:

  mcp__Alpha_Vantage_MCP_Server__EARNINGS_CALENDAR(symbol=NVDA, horizon=6month)
      # -> save the {"result": "<csv>"} to e.g. /tmp/nvda_cal.txt
  python3 scripts/earnings_cal.py /tmp/*_cal.txt

Each file is {"result": "<csv>"} or raw CSV with columns
symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay.

reaction_day (the session that trades the news) = next business day for a
post-market or blank timeOfTheDay, the reportDate itself for pre-market. AV's
forward coverage is partial; names it hasn't populated are simply omitted.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAG7 = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA"}
WIDEN_MULT = 1.20


def load_csv(path) -> pd.DataFrame:
    raw = Path(path).read_text()
    try:
        blob = json.loads(raw)
        csv = blob["result"] if isinstance(blob, dict) and "result" in blob else raw
    except json.JSONDecodeError:
        csv = raw
    if not csv.strip() or "reportDate" not in csv:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(csv))


def reaction_day(report_date: str, tod: str) -> str:
    d = pd.Timestamp(report_date)
    pre = isinstance(tod, str) and tod.strip().lower().startswith("pre")
    if pre:
        return d.strftime("%Y-%m-%d")
    return (d + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")


def main():
    files = sys.argv[1:]
    if not files:
        raise SystemExit("usage: earnings_cal.py <saved EARNINGS_CALENDAR file>...")
    today = dt.date.today()
    events = {}
    for f in files:
        df = load_csv(f)
        for _, r in df.iterrows():
            sym = str(r.get("symbol", "")).upper()
            rd = str(r.get("reportDate", ""))[:10]
            if sym not in MAG7 or not rd or rd == "nan":
                continue
            if pd.Timestamp(rd).date() < today:
                continue
            tod = r.get("timeOfTheDay", "")
            tod = "" if (tod is None or str(tod) == "nan") else str(tod)
            events[(sym, rd)] = {"sym": sym, "report_date": rd,
                                 "time": tod.strip().lower() or "unknown",
                                 "reaction_day": reaction_day(rd, tod)}
    evs = sorted(events.values(), key=lambda e: e["report_date"])
    out = {"generated": today.strftime("%Y-%m-%d"),
           "source": "AlphaVantage EARNINGS_CALENDAR (MAG7)",
           "note": ("Forward mega-cap report dates. reaction_day = next trading day "
                    "for post-market/unknown, same day for pre-market. AV forward "
                    "coverage is partial; unpopulated names are absent (no widener)."),
           "widen_mult": WIDEN_MULT, "events": evs}
    (ROOT / "data" / "earnings_calendar.json").write_text(json.dumps(out, indent=2))
    print(f"wrote data/earnings_calendar.json  ({len(evs)} upcoming MAG7 events)")
    for e in evs:
        print(f"  {e['sym']:5s} reports {e['report_date']} ({e['time']}) -> QQQ reacts {e['reaction_day']}")


if __name__ == "__main__":
    main()
