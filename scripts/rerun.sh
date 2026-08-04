#!/usr/bin/env bash
# Standard daily "rerun" — regime-first, confluence-based, candle-triggered.
#   1. REGIME    - trend vs balance (intraday_engine): decides the playbook
#   2. CONFLUENCE- HTF-anchored scored support/resistance zones (confluence):
#                  the ONLY levels we trade; standalone 5-min levels ignored
#   3. CANDLE    - 5/10/15/30-min triggers at the zones (candle_read)
# Fetch fresh NQ 5m+30m+1h AND QQQ 5m+1h into data/ before running.
# confluence.py auto-cross-references QQQ (scaled) -> A++ = QQQ-confirmed zone.
set -euo pipefail
cd "$(dirname "$0")/.."
SYM="${1:-NQ}"

echo "########## 1. REGIME (decides trend-follow vs fade) ##########"
python3 scripts/intraday_engine.py | sed -n '1,4p'
echo
echo "########## 2. CONFLUENCE ZONES (the levels that matter) ##########"
python3 scripts/confluence.py
echo
echo "########## 3. CANDLE TRIGGERS (5/10/15/30m) ##########"
python3 scripts/candle_read.py | sed -n '/--- 5m/,/=== ACTIONABLE/p'
