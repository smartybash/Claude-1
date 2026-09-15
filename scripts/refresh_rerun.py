#!/usr/bin/env python3
"""Morning refresh + rerun, in one deterministic step.

Bundles the two things that must be current for the A+ read to be trustworthy:
  1. NQ price feed  (data/nq_5min_eth_live.json)  <- fresh IBKR NQ 5-min raw
  2. AV gamma levels (data/gamma_levels.json)      <- av_gex --write from a
     fresh Alpha Vantage QQQ option chain, NQ scaled by the live NQ/QQQ ratio
...then runs scripts.confluence so the A+ SETUP note reflects both.

The two raw inputs come from MCP fetches (Alpha Vantage HISTORICAL_OPTIONS and
IBKR get_price_history) which live outside this sandbox's Python — pass their
saved file paths in. Everything after that is scripted here.

Usage:
  python3 scripts/refresh_rerun.py --nq-raw <ibkr_nq.json> --av-chain <av_qqq.txt> \
      [--ratio auto] [--no-run]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
FEED = ROOT / "data" / "nq_5min_eth_live.json"


def load_raw(path):
    """IBKR get_price_history JSON (or {'result': json})."""
    raw = Path(path).read_text()
    d = json.loads(raw)
    if isinstance(d, dict) and "result" in d and "time" not in d:
        d = json.loads(d["result"])
    return d


def write_price_feed(nq_raw):
    d = load_raw(nq_raw)
    keys = ("time", "open", "high", "low", "close", "volume")
    feed = {k: d[k] for k in keys}
    FEED.write_text(json.dumps(feed))
    return feed["time"][-1], feed["close"][-1], len(feed["time"])


def qqq_spot(av_chain):
    out = subprocess.run([PY, str(ROOT / "scripts/av_gex.py"), av_chain,
                          "--sym", "QQQ", "--mult", "100"],
                         capture_output=True, text=True)
    m = re.search(r"spot ([\d.]+)", out.stdout)
    if not m:
        raise SystemExit(f"could not read QQQ spot from av_gex:\n{out.stdout}\n{out.stderr}")
    return float(m.group(1))


def write_levels(av_chain, ratio):
    subprocess.run([PY, str(ROOT / "scripts/av_gex.py"), av_chain,
                    "--sym", "QQQ", "--mult", "100",
                    "--also-nq", str(ratio), "--write"], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nq-raw", required=True, help="IBKR NQ 5-min price-history JSON file")
    ap.add_argument("--av-chain", required=True, help="Alpha Vantage QQQ HISTORICAL_OPTIONS file")
    ap.add_argument("--ratio", default="auto", help="NQ/QQQ scale ratio, or 'auto' (default)")
    ap.add_argument("--nq-native", help="NQ FOP chain CSV (strike,call_oi,put_oi,call_iv,put_iv); "
                    "if given, NQ levels come from /NQ's own options via ib_nq_gex, overwriting the scaled read")
    ap.add_argument("--nq-dte", type=float, default=2.0, help="DTE of the sampled NQ FOP expiry")
    ap.add_argument("--nq-expiry", default="", help="NQ FOP expiry label (YYYYMMDD) for the source tag")
    ap.add_argument("--no-run", action="store_true", help="refresh files but skip the confluence rerun")
    a = ap.parse_args()

    last_t, nq_last, n = write_price_feed(a.nq_raw)
    print(f"[price] nq_5min_eth_live.json <- {n} bars, latest {last_t} close {nq_last}")

    spot = qqq_spot(a.av_chain)
    ratio = round(nq_last / spot, 3) if a.ratio == "auto" else float(a.ratio)
    print(f"[ratio] QQQ spot {spot} | NQ {nq_last} -> ratio {ratio}"
          + ("  (auto)" if a.ratio == "auto" else ""))

    write_levels(a.av_chain, ratio)
    print("[levels] gamma_levels.json <- Alpha Vantage (QQQ + NQ scaled)")

    # NQ-native override: replace the scaled NQ slot with /NQ's own dealer gamma
    if a.nq_native:
        subprocess.run([PY, str(ROOT / "scripts/ib_nq_gex.py"), a.nq_native,
                        "--spot", str(nq_last), "--dte", str(a.nq_dte),
                        "--expiry", a.nq_expiry, "--write"], check=True)
        print("[levels] gamma_levels.json[NQ] <- IBKR NQ FOP (native, overrides scaled)")

    if not a.no_run:
        print("[rerun] scripts.confluence\n" + "-" * 60)
        subprocess.run([PY, "-m", "scripts.confluence"], cwd=str(ROOT))


if __name__ == "__main__":
    main()
