#!/usr/bin/env bash
# Standard daily "rerun": one command, fixed order, every time.
#   Stream 1 - overnight failed-auction levels + R:R (overnight_setup)
#   Stream 2 - multi-day composite / trend gate (multiday_levels)
#   Candle   - multi-timeframe candlestick signals with entry/stop/target
# Fetch fresh data into data/nq_5min_eth_live.json + data/nq_30min_eth.json
# BEFORE running this. Symbol defaults to NQ; pass an arg to override.
set -euo pipefail
cd "$(dirname "$0")/.."
SYM="${1:-NQ}"

echo "########## REGIME + INTRADAY ENGINE (VWAP/OR/PD) - READ THIS FIRST ##########"
python3 scripts/intraday_engine.py
echo
echo "########## STREAM 1: overnight levels (only trade these on BALANCE regime) ##########"
python3 scripts/overnight_setup.py --symbol "$SYM"
echo
echo "########## STREAM 2: multi-day composite / trend gate ##########"
python3 scripts/multiday_levels.py | sed -n '1,12p'
echo
echo "########## CANDLE READ: 5/10/15/30-min signals ##########"
python3 scripts/candle_read.py
