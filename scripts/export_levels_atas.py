#!/usr/bin/env python3
"""Export today's tradeable levels (VAH / POC / VAL + dealer-gamma flip / call
wall / put wall) as a morning "levels sheet" for ATAS — one row per level, with
the price, a label, a colour and which side it is (resistance/support/pivot).

ATAS has no one-click CSV import for horizontal lines in the standard build, so
this is a sheet you draw from each morning (or feed to a custom indicator via the
ATAS API later). It writes both a CSV (reports/atas/levels_YYYYMMDD.csv) and a
plain readable table to stdout.

Levels come from the SAME source as the ToS studies: prior-session value area
(70% volume profile) + data/gamma_levels.json (native / scaled per instrument).

Usage: python3 scripts/export_levels_atas.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import scripts.generate_tos_va as V           # per_day_va(), INTRADAY map
import scripts.gamma_context as gc

# instrument -> (gamma slot, multiplier applied to that slot's levels)
GAMMA_SRC = {"MNQ": ("NQ", 1.0), "QQQ": ("QQQ", 1.0),
             "MES": ("SPY", 10.0531), "SPY": ("SPY", 1.0)}


def levels_for(sym, date):
    rows = V.per_day_va(sym, 1, date)          # [(YYYYMMDD, (poc,vah,val))]
    if not rows:
        return None
    _tag, (poc, vah, val) = rows[-1]
    slot, mult = GAMMA_SRC[sym]
    g = gc.load_gamma_levels(slot) or {}
    flip = g.get("gamma_flip"); cw = g.get("call_wall"); pw = g.get("put_wall")
    out = [
        ("VAH", vah, "resistance", "red",    "prior VAH — fade-short zone (2nd tag)"),
        ("POC", poc, "pivot",      "yellow", "prior POC — T1 for fades / magnet"),
        ("VAL", val, "support",    "green",  "prior VAL — fade-long zone / T2"),
    ]
    if cw is not None:
        out.append(("CALL_WALL", cw * mult, "resistance", "red",   "dealer call wall — upper magnet / breakout trigger"))
    if flip is not None:
        out.append(("GAMMA_FLIP", flip * mult, "pivot",   "white", "regime pivot — above=range/fade, below=trend/go-with"))
    if pw is not None:
        out.append(("PUT_WALL", pw * mult, "support",     "green", "dealer put wall — lower magnet / breakdown trigger"))
    return sorted(out, key=lambda r: -r[1])     # high -> low


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=V.DATE)
    a = ap.parse_args()
    outdir = ROOT / "reports" / "atas"
    outdir.mkdir(parents=True, exist_ok=True)
    tag = a.date.replace("-", "")
    csv_path = outdir / f"levels_{tag}.csv"

    all_rows = []
    print(f"\n===== ATAS LEVELS SHEET — {a.date} =====")
    print("(draw these as horizontal lines; footprint/imbalance signals only count AT a level)\n")
    for sym in ("MNQ", "QQQ", "MES", "SPY"):
        L = levels_for(sym, a.date)
        if not L:
            print(f"{sym}: no value-area history"); continue
        print(f"--- {sym} ---")
        print(f"  {'level':<11}{'price':>11}  {'side':<11}note")
        for name, price, side, color, note in L:
            dp = 2
            print(f"  {name:<11}{price:>11.{dp}f}  {side:<11}{note}")
            all_rows.append([sym, name, f"{price:.2f}", side, color, note])
        print()

    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "level", "price", "side", "color", "note"])
        w.writerows(all_rows)
    print(f"wrote {csv_path}  ({len(all_rows)} levels)")


if __name__ == "__main__":
    main()
