#!/usr/bin/env bash
# Standard daily "rerun" — regime-first, confluence-based, candle-triggered.
#   1. REGIME    - trend vs balance (intraday_engine): decides the playbook.
#                  Read on TWO clocks - whole session AND the last hour - and
#                  flags a REGIME SHIFT when the last hour breaks from the morning.
#   2. LEVELS    - DEALER-GAMMA walls + flip = the tradeable map (validated),
#                  plus GAMMA/EM context (VIX expected-move band + vol regime).
#                  The "A+" confluence scoring was RETIRED: on ~2y it held no
#                  better than random levels (reports/gamma_backtest_findings.md).
#                  Confluence zones still print but as UNVALIDATED context only.
#   3. CANDLE    - 5/10/15/30-min triggers at the levels (candle_read)
#   4. TOS       - copy-paste ThinkOrSwim studies (FVG + breakout + gamma walls)
#   5. ROTATION  - MAGS/SMH/IGV vs QQQ: since-open AND last-hour %chg + RS vs QQQ,
#                  live breadth, and a ROTATION SHIFT flag (sector leadership/breadth)
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
#   GAMMA (once, pre-open): fetch the prior-session option chain and recompute
#     dealer GEX / flip / walls -> data/gamma_levels.json (+ log to
#     gex_history.jsonl, which feeds the EM tercile scaling):
#       HISTORICAL_OPTIONS(symbol=QQQ, date=<prior session>, datatype=csv,
#         return_full_data=true)  # saves <file>.txt
#       python3 scripts/av_gex.py <file> --sym QQQ --mult 100 --write --log \
#         --also-nq <NQ/QQQ ratio>
#       # SAME saved chain also feeds the 25d IV-skew log (zero extra fetch):
#       python3 scripts/av_skew.py <file> --sym QQQ --log   # -> skew_history.jsonl
#       # (skew is research-only: backtest_skew.py found no tradeable directional
#       #  edge at n=56; keep logging to re-test as the sample grows.)
#   EARNINGS CAL (weekly-ish): refresh the forward mega-cap widener dates:
#       EARNINGS_CALENDAR(symbol=<MAG7>, horizon=6month)  # save each output
#       python3 scripts/earnings_cal.py <saved files...>  # -> earnings_calendar.json
#     The EM band auto-widens x1.20 on a reaction day (stacks with the gamma mult).
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
python3 scripts/intraday_engine.py | sed -n '1,5p'
echo
echo "########## 2. DEALER-GAMMA LEVELS (the tradeable map; A+ confluence retired) ##########"
python3 scripts/confluence.py
echo
echo "########## 3. CANDLE TRIGGERS (5/10/15/30m) ##########"
python3 scripts/candle_read.py | sed -n '/--- 5m/,/=== ACTIONABLE/p'
echo
echo "########## 4. ThinkOrSwim STUDY — VALUE-AREA FADE (the only chart study) ##########"
#   Sole ToS study: short the 2nd VAH/call-wall rejection -> POC/VAL. The FVG,
#   breakout, daily-context and 4-box studies were retired from the rerun at the
#   user's request; their generators remain in scripts/ if ever needed.
python3 scripts/generate_tos_va.py --sym MNQ
echo
echo "########## 5. SECTOR ROTATION (MAGS/SMH/IGV vs QQQ — leadership/breadth) ##########"
python3 scripts/rotation.py
echo
echo "########## 6. ATAS LEVELS SHEET (VAH/POC/VAL + walls + flip for the footprint) ##########"
#   Morning levels to draw in ATAS; order-flow imbalance only counts AT a level.
#   Playbook: reports/atas_imbalance_playbook.md
python3 scripts/export_levels_atas.py
