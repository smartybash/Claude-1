"""Deep 5-minute history fetch via ib_async against a local TWS / IB Gateway.

THIS SCRIPT CANNOT RUN IN THE REMOTE RESEARCH CONTAINER - there is no TWS
there (verified: ports 7496/7497/4001/4002 all closed) and the IBKR MCP
connector caps every historical request at 1000 bars with no backward paging.
Run it on the machine where TWS/Gateway is running, then commit the parquet
files it writes; scripts/sweep_run_intraday_test.py picks them up directly.

Usage:
    pip install ib_async pandas pyarrow
    python scripts/fetch_intraday.py --port 7497 --years 3

Design (per spec):
  - chunked reqHistoricalData walking endDateTime backward (IBKR pacing:
    sleep PACING_S between calls, retry once on pacing violations)
  - every chunk appended to the parquet cache immediately, so a crash or
    rate-limit loses nothing and reruns resume from the oldest cached bar
  - futures use IBKR's continuous contract (ContFuture, CONTFUT data) so
    there are no self-stitched roll jumps; roll dates are still flagged in
    data/parquet/{SYM}_roll_dates.json (from the quarterly contract calendar)
    so the backtest can exclude sessions spanning a roll. Method used must be
    stated in the final report: CONTINUOUS CONTRACT (not manual stitching).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PARQUET = ROOT / "data" / "parquet"

CHUNK = "5 D"          # duration per reqHistoricalData call
PACING_S = 3.0         # sleep between calls (spec: 2-5s)
BAR = "5 mins"


def fetch_symbol(ib, contract, sym: str, years: int, use_rth: bool) -> None:
    from ib_async import util

    PARQUET.mkdir(parents=True, exist_ok=True)
    out = PARQUET / f"{sym}_5min.parquet"
    existing = pd.read_parquet(out) if out.exists() else None
    # resume: walk backward from the oldest bar we already have
    end = (
        existing.index.min().tz_convert("UTC").to_pydatetime()
        if existing is not None and len(existing)
        else datetime.utcnow()
    )
    floor = datetime.utcnow() - timedelta(days=365 * years)
    n_calls = 0
    while end > floor:
        for attempt in (1, 2):
            try:
                bars = ib.reqHistoricalData(
                    contract,
                    endDateTime=end,
                    durationStr=CHUNK,
                    barSizeSetting=BAR,
                    whatToShow="TRADES",
                    useRTH=use_rth,
                    formatDate=2,
                )
                break
            except Exception as e:  # pacing violation etc.
                print(f"  retry after error: {e}")
                time.sleep(30 * attempt)
        else:
            raise RuntimeError(f"{sym}: two consecutive failures at {end}")
        n_calls += 1
        if not bars:
            print(f"{sym}: no more data before {end}, stopping")
            break
        df = util.df(bars).set_index("date")[["open", "high", "low", "close", "volume"]]
        df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
        df.index.name = "ts"
        merged = df if existing is None else pd.concat([existing, df])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        merged.to_parquet(out)  # cache EVERY chunk as it arrives
        existing = merged
        new_end = df.index.min().tz_convert("UTC").to_pydatetime()
        if new_end >= end:
            break
        end = new_end
        print(f"{sym}: {len(merged)} bars cached, back to {merged.index.min()} "
              f"({n_calls} calls)")
        time.sleep(PACING_S)


def flag_roll_dates(ib, root: str, exchange: str, sym: str) -> None:
    """Store quarterly last-trading-dates so sessions near rolls can be
    excluded from gap/level statistics."""
    from ib_async import Future

    details = ib.reqContractDetails(Future(root, exchange=exchange, includeExpired=True))
    dates = sorted({d.contract.lastTradeDateOrContractMonth for d in details})
    (PARQUET / f"{sym}_roll_dates.json").write_text(json.dumps(dates, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7497)
    ap.add_argument("--client-id", type=int, default=11)
    ap.add_argument("--years", type=int, default=3)
    args = ap.parse_args()

    from ib_async import IB, ContFuture, Stock

    ib = IB()
    ib.connect(args.host, args.port, clientId=args.client_id)

    jobs = [
        (ContFuture("NQ", exchange="CME"), "NQ", False),  # ETH included
        (ContFuture("ES", exchange="CME"), "ES", False),
        (Stock("QQQ", "SMART", "USD"), "QQQ", True),
        (Stock("SPY", "SMART", "USD"), "SPY", True),
    ]
    for contract, sym, use_rth in jobs:
        ib.qualifyContracts(contract)
        print(f"=== {sym} ({contract.localSymbol or contract.symbol}) ===")
        fetch_symbol(ib, contract, sym, args.years, use_rth)
    for root, sym in (("NQ", "NQ"), ("ES", "ES")):
        flag_roll_dates(ib, root, "CME", sym)
    ib.disconnect()
    print("done - now run scripts/build_parquet_cache.py is NOT needed; "
          "parquet was written directly. Re-run the backtest.")


if __name__ == "__main__":
    main()
