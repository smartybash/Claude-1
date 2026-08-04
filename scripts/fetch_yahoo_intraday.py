"""Deep intraday fetch via the Yahoo v8 chart API — the depth fix for Part B.

Why this exists: the sweep/run walk-forward needs ~60 RTH sessions, but every
IBKR MCP get_price_history call is capped at ~1000 bars (~13 sessions of 5-min),
so the pre-registered depth floor never cleared and the verdict stayed
DIAGNOSTIC / NOT VALIDATED.

The session egress policy allows query1/query2.finance.yahoo.com (they answer
200) but denies fc.yahoo.com, the cookie/crumb host yfinance hits first — so
yfinance itself fails at the crumb step. The v8 /chart endpoint needs no crumb,
so we call it directly through the agent proxy (requests honours HTTPS_PROXY and
the CA bundle) with backoff on Yahoo's own 429 rate limit.

Yahoo interval history caps: 5m -> 60d, 15m/30m -> 60d, 1h -> 730d, 1d -> years.
5m at 60d is what finally meets the session floor.

Writes data/{name}.json in our IBKR columnar schema
    {"time":[iso...], "open":[...], "high":[...], "low":[...], "close":[...], "volume":[...]}
timestamps as UTC ISO, exactly what sweeplib.data.load_ibkr_json expects.

Usage:
    python3 scripts/fetch_yahoo_intraday.py           # fetch the default deep set
    python3 scripts/fetch_yahoo_intraday.py --dry-run  # probe reachability only
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
# query2 is the reachable/200 host in this environment; query1 is the fallback
# (it answers but rate-limits anonymous requests harder). fc/finance.yahoo.com
# stay proxy-blocked, so we never fetch a cookie/crumb — the v8 chart endpoint
# does not require one.
HOSTS = ["query2.finance.yahoo.com", "query1.finance.yahoo.com"]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# (yahoo_symbol, range, interval, out_json)  — futures use =F continuous fronts.
# 5m/60d (~60 RTH sessions) is the depth-critical pull that finally clears the
# Part B walk-forward floor; 1h/730d (~500 sessions) gives the large N for the
# confluence-filter validation. Yahoo caps intraday lookback (5m/15m/30m -> 60d,
# 1h -> 730d); requesting more returns 422, so these ranges are the deepest each
# interval allows. We keep the request count small (8) because Yahoo throttles
# the shared egress IP hard when there is no cookie/crumb (those hosts are
# proxy-blocked here). 30m is resampled from 5m downstream; daily already ships
# in the repo, so neither is fetched.
JOBS = [
    ("SPY",  "60d", "5m", "spy_5min_yf.json"),
    ("QQQ",  "60d", "5m", "qqq_5min_yf.json"),
    ("ES=F", "60d", "5m", "es_5min_yf.json"),
    ("NQ=F", "60d", "5m", "nq_5min_yf.json"),
    ("SPY",  "730d", "1h", "spy_1h_yf.json"),
    ("QQQ",  "730d", "1h", "qqq_1h_yf.json"),
    ("ES=F", "730d", "1h", "es_1h_yf.json"),
    ("NQ=F", "730d", "1h", "nq_1h_yf.json"),
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    # requests honours HTTPS_PROXY from env; make sure it verifies the proxy CA
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
    if Path(ca).exists():
        s.verify = ca
    return s


# patient backoff schedule (seconds) for Yahoo's anonymous 429 wall — the shared
# egress IP is throttled hard and there is no crumb to lift it, so we wait it out
BACKOFF = [15, 30, 45, 60, 90, 120, 120, 120]


def fetch_chart(s: requests.Session, symbol: str, rng: str, interval: str) -> dict:
    """Return the parsed chart 'result[0]', alternating hosts and waiting out
    429s on the patient BACKOFF schedule."""
    params = {"range": rng, "interval": interval, "includePrePost": "false",
              "events": "div,splits"}
    last = None
    for attempt, wait in enumerate(BACKOFF):
        host = HOSTS[attempt % len(HOSTS)]
        url = f"https://{host}/v8/finance/chart/{symbol}"
        try:
            r = s.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {str(e)[:60]}"
            print(f"    {symbol} {interval} {host[:6]}: {last}; waiting {wait}s",
                  flush=True)
            time.sleep(wait)
            continue
        if r.status_code == 200:
            j = r.json()
            res = (j.get("chart") or {}).get("result")
            if not res:
                err = (j.get("chart") or {}).get("error")
                raise RuntimeError(f"{symbol}: empty chart result ({err})")
            return res[0]
        last = f"HTTP {r.status_code}"
        if r.status_code in (429, 503, 502):     # transient — wait it out
            print(f"    {symbol} {interval} {host[:6]}: {last}; waiting {wait}s",
                  flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"{symbol} {interval}: {last} {r.text[:160]}")
    raise RuntimeError(f"{symbol} {interval}: exhausted retries ({last})")


def to_columnar(res: dict) -> dict:
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    o, h, l, c, v = q["open"], q["high"], q["low"], q["close"], q["volume"]
    out = {"time": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    for i, t in enumerate(ts):
        # Yahoo leaves gaps as null; drop any bar missing OHLC
        if None in (o[i], h[i], l[i], c[i]):
            continue
        out["time"].append(
            __import__("datetime").datetime.utcfromtimestamp(t)
            .replace(tzinfo=__import__("datetime").timezone.utc).isoformat())
        out["open"].append(float(o[i])); out["high"].append(float(h[i]))
        out["low"].append(float(l[i])); out["close"].append(float(c[i]))
        out["volume"].append(float(v[i]) if v[i] is not None else 0.0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="probe one symbol for reachability, write nothing")
    a = ap.parse_args()
    s = _session()

    if a.dry_run:
        res = fetch_chart(s, "SPY", "5d", "1h")
        print(f"reachable: SPY 1h -> {len(res['timestamp'])} bars, "
              f"tz={res['meta'].get('exchangeTimezoneName')}")
        return

    ok = 0
    for symbol, rng, interval, name in JOBS:
        try:
            res = fetch_chart(s, symbol, rng, interval)
            col = to_columnar(res)
            (DATA / name).write_text(json.dumps(col))
            t0 = col["time"][0][:10] if col["time"] else "?"
            t1 = col["time"][-1][:10] if col["time"] else "?"
            print(f"{name:20s} {symbol:5s} {interval:>3s} "
                  f"bars={len(col['time']):5d}  {t0} -> {t1}")
            ok += 1
        except Exception as e:
            print(f"{name:20s} FAILED: {e}")
        time.sleep(20.0)    # gentle spacing between jobs to avoid the 429 wall
    print(f"\n{ok}/{len(JOBS)} files written to {DATA}")


if __name__ == "__main__":
    main()
