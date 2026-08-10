"""Compute REAL dealer GEX / gamma-flip / call+put walls / dealer delta from an
Alpha Vantage HISTORICAL_OPTIONS chain and write them into data/gamma_levels.json.

This replaces manual FlashAlpha reading: AV premium gives the full per-strike
chain (open interest + greeks) for the prior session — exactly what sets the
open. In the cloud sandbox, fetch it with the MCP tool (it auto-saves the big
CSV to disk), then run this on the saved file:

  mcp__Alpha_Vantage_MCP_Server__HISTORICAL_OPTIONS(symbol=QQQ, date=YYYY-MM-DD,
      datatype=csv, return_full_data=true)          # -> saves <file>.txt
  python3 scripts/av_gex.py <file> --sym QQQ --mult 100 --dte-max 35 --write --log
  # add --also-nq <ratio> to also write the NQ slot scaled to NQ points.

Saved file is JSON {"result":"<csv>"} (or a raw CSV). Columns include
strike, type, open_interest, implied_volatility, delta, gamma.

Math is delegated to gex_calc.compute_gex/find_flip so the CSV, IBKR, and AV
paths all agree. Net GEX uses real chain gamma; the flip is IV-repriced.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gex_calc


def load_av(path) -> pd.DataFrame:
    raw = Path(path).read_text()
    try:
        blob = json.loads(raw)
        csv = blob["result"] if isinstance(blob, dict) and "result" in blob else raw
    except json.JSONDecodeError:
        csv = raw
    df = pd.read_csv(io.StringIO(csv))
    for c in ("strike", "open_interest", "implied_volatility", "delta", "gamma"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["type"] = df["type"].str.lower()
    return df


def estimate_spot(df: pd.DataFrame) -> float:
    """Put-call parity at the ATM strike of the nearest expiration: S ~= K + C - P."""
    exp = sorted(df["expiration"].unique())[0]
    g = df[df["expiration"] == exp]
    piv = g.pivot_table(index="strike", columns="type", values="mark", aggfunc="first")
    piv = piv.dropna()
    if piv.empty:
        return float(g["strike"].median())
    k = (piv["call"] - piv["put"]).abs().idxmin()
    return float(k + piv.loc[k, "call"] - piv.loc[k, "put"])


def to_per_strike(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate call/put rows into one row per strike, OI-weighting the greeks."""
    out = {}
    for side, tag in (("call", "call"), ("put", "put")):
        s = df[df["type"] == side].copy()
        s["oi"] = s["open_interest"].fillna(0)
        grp = s.groupby("strike")
        oi = grp["oi"].sum()

        def wavg(col):
            def f(idx):
                w = s.loc[idx.index, "oi"]
                v = s.loc[idx.index, col]
                return np.average(v, weights=w) if w.sum() > 0 else v.mean()
            return grp[col].apply(f)
        out[f"{tag}_oi"] = oi
        out[f"{tag}_gamma"] = wavg("gamma")
        out[f"{tag}_iv"] = wavg("implied_volatility")
        out[f"{tag}_delta"] = wavg("delta")
    per = pd.DataFrame(out).fillna(0.0).reset_index()
    return per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--sym", required=True)
    ap.add_argument("--mult", type=float, default=100)
    ap.add_argument("--dte-max", type=int, default=35, help="aggregate expiries within N days")
    ap.add_argument("--spot", type=float)
    ap.add_argument("--rate", type=float, default=0.0)
    ap.add_argument("--also-nq", type=float, help="also write NQ slot, levels scaled by this ratio")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--log", action="store_true", help="append to data/gex_history.jsonl")
    a = ap.parse_args()

    df = load_av(a.file)
    asof = str(df["date"].max())
    asof_d = dt.datetime.strptime(asof[:10], "%Y-%m-%d").date()
    df["exp_d"] = pd.to_datetime(df["expiration"]).dt.date
    win = df[(df["exp_d"] >= asof_d) & (df["exp_d"] <= asof_d + dt.timedelta(days=a.dte_max))]
    if win.empty:
        raise SystemExit("no expirations within window")
    spot = a.spot or estimate_spot(win)
    dte = max((sorted(win["exp_d"].unique())[0] - asof_d).days, 1)
    per = to_per_strike(win)

    res = gex_calc.compute_gex(per, spot, a.mult, iv_mode=False, T=dte / 365.0, r=a.rate)
    res["gamma_flip"] = gex_calc.find_flip(per, spot, a.mult, True, dte / 365.0, a.rate)
    # walls: conventional = largest RAW open interest strike (calls above / puts below spot)
    ca = per[per["strike"] >= spot]
    pu = per[per["strike"] <= spot]
    if not ca.empty and ca["call_oi"].max() > 0:
        res["call_wall"] = float(ca.loc[ca["call_oi"].idxmax(), "strike"])
    if not pu.empty and pu["put_oi"].max() > 0:
        res["put_wall"] = float(pu.loc[pu["put_oi"].idxmax(), "strike"])
    gex_calc.print_read(a.sym, spot, a.mult, False, res)
    print(f"  as-of {asof}  expiries<= +{a.dte_max}d  strikes {len(per)}  (Alpha Vantage)")

    if a.write:
        gex_calc.write_levels(a.sym, res, source=f"AlphaVantage {asof}")
        print(f"  -> wrote data/gamma_levels.json[{a.sym}]")
    if a.also_nq:
        r = a.also_nq
        nq = {"net_gex": round(res["net_gex"], 0),
              "gamma_flip": round(res["gamma_flip"] * r) if res["gamma_flip"] else None,
              "zero_gamma": round(res["gamma_flip"] * r) if res["gamma_flip"] else None,
              "call_wall": round(res["call_wall"] * r), "put_wall": round(res["put_wall"] * r)}
        if res.get("dealer_delta") is not None:
            nq["dealer_delta"] = round(res["dealer_delta"], 0)
        if a.write:
            f = ROOT / "data" / "gamma_levels.json"
            blob = json.loads(f.read_text())
            blob.setdefault("levels", {})["NQ"] = nq
            f.write_text(json.dumps(blob, indent=2))
            print(f"  -> wrote NQ slot scaled x{r:.3f}: flip {nq['gamma_flip']} call {nq['call_wall']} put {nq['put_wall']}")
    if a.log:
        row = {"date": asof, "sym": a.sym, "spot": round(spot, 2),
               "net_gex": round(res["net_gex"], 0),
               "gamma_flip": round(res["gamma_flip"], 2) if res["gamma_flip"] else None,
               "call_wall": round(res["call_wall"], 2), "put_wall": round(res["put_wall"], 2),
               "dealer_delta": round(res["dealer_delta"], 0) if res.get("dealer_delta") is not None else None}
        logf = ROOT / "data" / "gex_history.jsonl"
        existing = [json.loads(l) for l in logf.read_text().splitlines()] if logf.exists() else []
        existing = [r for r in existing if not (r["date"] == asof and r["sym"] == a.sym)]
        with logf.open("w") as fh:
            for r in existing + [row]:
                fh.write(json.dumps(r) + "\n")
        print(f"  -> logged to gex_history.jsonl ({len(existing)+1} rows)")


if __name__ == "__main__":
    main()
