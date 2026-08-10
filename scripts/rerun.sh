#!/usr/bin/env bash
# Standard daily "rerun" — regime-first, confluence-based, candle-triggered.
#   1. REGIME    - trend vs balance (intraday_engine): decides the playbook
#   2. CONFLUENCE- HTF-anchored scored support/resistance zones (confluence)
#                  + GAMMA/EM context (VIX expected-move band + vol regime);
#                  the ONLY levels we trade; standalone 5-min levels ignored
#   3. CANDLE    - 5/10/15/30-min triggers at the zones (candle_read)
#   4. TOS       - copy-paste ThinkOrSwim studies (with EM band + gamma pin)
#   5. ROTATION  - MAGS/SMH/IGV vs QQQ normalized %chg (sector leadership/breadth)
# confluence.py auto-cross-references QQQ (scaled) -> A++ = QQQ-confirmed zone.
#
# DELIVERY REQUIREMENT (every rerun / every gamma or data update, non-negotiable):
#   share in chat BOTH the charts AND the FULL code for ALL FOUR ToS studies
#   (MNQ, QQQ, MES, SPY) pasted IN THEIR ENTIRETY — every single time, even if
#   only one number changed. NEVER post deltas, "unchanged from last time", or
#   find-and-replace/edit instructions. Always the complete, ready-to-paste box
#   for each of the four. Also include the confluence + rotation charts.
#   (Standing instruction from the user.)
#
# DATA REFRESH — to keep reruns fast, split the fetch by how fast it moves:
#   FAST (every intraday rerun): only the live intraday bars that actually move
#     the read — NQ 5m (nq_5min_eth_live.json) + QQQ 5m (qqq_5min.json), and the
#     30m closes used as ToS price anchors (nq/es/qqq/spy _30m_live.json).
#   SLOW (once, pre-open): the HTF confluence anchors that barely change
#     intraday — 30m/1h swings, daily (5y) for VIX/EM + macro SMA, VP inputs.
#     Skip refetching these on every intraday rerun.
#   ROTATION basket (5m): MAGS 624756922, SMH 229725622, IGV 12658199 (all STK) ->
#     mags_5m.json / smh_5m.json / igv_5m.json (QQQ reused from qqq_5min.json).
#   INGEST: never hand-transcribe bars. Save the raw get_price_history payload
#     to a scratch file and run:  python3 scripts/ingest_ibkr.py <raw> <out.json>
#     It normalises + length-validates + writes data/<out.json>. Tip: pass a big
#     step_count (e.g. 1200) to FORCE the result to disk instead of coming inline.
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
echo
echo "########## 4. ThinkOrSwim STUDIES (share FULL code for ALL 4 boxes in chat) ##########"
python3 scripts/generate_tos.py
echo
echo "########## 5. SECTOR ROTATION (MAGS/SMH/IGV vs QQQ — leadership/breadth) ##########"
python3 scripts/rotation.py
