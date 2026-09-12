#!/usr/bin/env python3
"""Batch-compute dealer gamma from a folder of saved Alpha Vantage option-chain
payloads and append to data/gex_history.jsonl (deduped, sorted).

This extends the gamma history backward so the regime split (negative vs
positive gamma) has real statistical power instead of ~1 year. Each AV
HISTORICAL_OPTIONS pull offloads to a tool-result file; point this at that
folder and it computes {net_gex, gamma_flip, call_wall, put_wall} per date using
the same near-dated, near-money rule as av_gex, then merges into the history.

Only rows whose chain symbol matches --sym are used (so a SPY chain in the same
folder is skipped). Existing (date,sym) rows are replaced, not duplicated.

Usage:
  python3 scripts/backfill_gamma_history.py <dir-with-chain-files> \
      [--sym QQQ] [--dte-max 9] [--wall-band 0.15] [--glob '*HISTORICAL_OPTIONS*']
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import av_gex          # load_av, estimate_spot, to_per_strike
import gex_calc


def compute(path, sym, mult, dte_max, wall_band, rate=0.0):
    df = av_gex.load_av(path)
    if "symbol" in df.columns:
        syms = set(str(s).upper() for s in df["symbol"].dropna().unique())
        if sym.upper() not in syms:
            return None                       # not this instrument's chain
    asof = str(df["date"].max())
    asof_d = dt.datetime.strptime(asof[:10], "%Y-%m-%d").date()
    df["exp_d"] = pd.to_datetime(df["expiration"]).dt.date
    win = df[(df["exp_d"] >= asof_d) & (df["exp_d"] <= asof_d + dt.timedelta(days=dte_max))]
    if win.empty:
        return None
    spot = av_gex.estimate_spot(win)
    dte = max((sorted(win["exp_d"].unique())[0] - asof_d).days, 1)
    per = av_gex.to_per_strike(win)
    res = gex_calc.compute_gex(per, spot, mult, iv_mode=False, T=dte / 365.0, r=rate)
    res["gamma_flip"] = gex_calc.find_flip(per, spot, mult, True, dte / 365.0, rate)
    ca = per[per["strike"] >= spot]; pu = per[per["strike"] <= spot]
    if wall_band:
        lo, hi = spot * (1 - wall_band), spot * (1 + wall_band)
        ca = ca[ca["strike"] <= hi]; pu = pu[pu["strike"] >= lo]
    if ca.empty or pu.empty or ca["call_oi"].max() <= 0 or pu["put_oi"].max() <= 0:
        return None
    cw = float(ca.loc[ca["call_oi"].idxmax(), "strike"])
    pw = float(pu.loc[pu["put_oi"].idxmax(), "strike"])
    return {"date": asof, "sym": sym, "spot": round(spot, 2),
            "net_gex": round(res["net_gex"], 0),
            "gamma_flip": round(res["gamma_flip"], 2) if res["gamma_flip"] else None,
            "call_wall": round(cw, 2), "put_wall": round(pw, 2),
            "dealer_delta": round(res["dealer_delta"], 0) if res.get("dealer_delta") is not None else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sym", default="QQQ")
    ap.add_argument("--mult", type=float, default=100)
    ap.add_argument("--dte-max", type=int, default=9)
    ap.add_argument("--wall-band", type=float, default=0.15)
    ap.add_argument("--glob", default="*HISTORICAL_OPTIONS*")
    a = ap.parse_args()

    files = sorted(glob.glob(str(Path(a.folder) / a.glob)))
    rows, skipped = [], 0
    for f in files:
        try:
            r = compute(f, a.sym, a.mult, a.dte_max, a.wall_band)
        except Exception as e:
            r = None; print(f"  skip {Path(f).name}: {e}", file=sys.stderr)
        if r:
            rows.append(r)
        else:
            skipped += 1
    logf = ROOT / "data" / "gex_history.jsonl"
    existing = [json.loads(l) for l in logf.read_text().splitlines() if l.strip()] \
        if logf.exists() else []
    by_key = {(r["date"], r["sym"]): r for r in existing}
    added = 0
    for r in rows:
        k = (r["date"], r["sym"])
        if k not in by_key:
            added += 1
        by_key[k] = r
    merged = sorted(by_key.values(), key=lambda r: (r["date"], r["sym"]))
    with logf.open("w") as fh:
        for r in merged:
            fh.write(json.dumps(r) + "\n")
    qqq = [r for r in merged if r["sym"] == a.sym]
    print(f"processed {len(files)} files, computed {len(rows)}, skipped {skipped}")
    print(f"added {added} new rows; gex_history.jsonl now {len(merged)} rows "
          f"({a.sym}: {len(qqq)}, {qqq[0]['date']} -> {qqq[-1]['date']})")


if __name__ == "__main__":
    main()
