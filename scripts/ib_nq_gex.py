#!/usr/bin/env python3
"""NQ-NATIVE dealer gamma from IBKR NQ futures options (FOP) — flip / walls
computed from /NQ's OWN option chain and skew, not scaled off QQQ.

WHY: QQQ->NQ scaling inherits QQQ's vol skew and dealer positioning. NQ futures
options are skewed differently, so the native flip/walls can sit hundreds of
points away from the scaled ones (observed 2026-08-12: native flip 29275 vs
scaled 29774). For NQ trading, this is the accurate read.

COMPUTE (this script): reads a per-strike CSV and runs the shared GEX math
(gex_calc) with the futures multiplier (NQ = 20), then writes gamma_levels.json[NQ].
CSV columns: strike,call_oi,put_oi,call_iv,put_iv   (IV annualized, e.g. 0.21)

FETCH (agent/MCP step, run pre-open once per day — OI only updates at settlement):
  1. search_contracts("NQ")            -> underlying_contract_id (row w/ FOP), = 11004958
  2. get_option_parameters(uid, FOP)   -> pick nearest expiry id (0-2 DTE weekly)
  3. get_option_data(expiration_id, min_strike, max_strike)
        -> call/put contract_id per strike. NQ strikes are 10-pt; SAMPLE the
           round-50 grid (that's where OI concentrates — round strikes hold
           100s of OI, 10-pt strikes ~5).
  4. get_price_snapshot(contract_id, exchange="CME",
        market_data_names=["option_open_interest","option_midpoint_iv"])
        -> callInterest/putInterest + annualIv, per contract.
  Assemble those into the CSV, then run this script.

Usage:
  python3 scripts/ib_nq_gex.py chain.csv --spot 29773 --dte 2 --expiry 20260814 --write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gex_calc  # reuse the exact GEX math + writer

NQ_MULT = 20  # /NQ index multiplier ($ per point)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chain", help="per-strike CSV: strike,call_oi,put_oi,call_iv,put_iv")
    ap.add_argument("--spot", type=float, required=True, help="NQ front-future price")
    ap.add_argument("--dte", type=float, default=2.0, help="calendar days to the sampled expiry")
    ap.add_argument("--expiry", default="", help="expiry label for the source tag (YYYYMMDD)")
    ap.add_argument("--rate", type=float, default=0.0)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    df = gex_calc.load_chain(a.chain)
    if "call_iv" not in df.columns or "put_iv" not in df.columns:
        raise SystemExit("chain needs call_iv/put_iv (annualized) for the native BS-gamma read")
    res = gex_calc.compute_gex(df.fillna(0.0), a.spot, NQ_MULT, True, a.dte / 365.0, a.rate)
    gex_calc.print_read("NQ", a.spot, NQ_MULT, True, res)
    if a.write:
        gex_calc.write_levels("NQ", res, source=f"IBKR-FOP {a.expiry}".strip())
        print(f"  -> wrote data/gamma_levels.json[NQ]  (native, from /NQ options)")


if __name__ == "__main__":
    main()
