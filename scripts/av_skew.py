"""Compute 25-delta IV skew / risk-reversal from an Alpha Vantage HISTORICAL_OPTIONS
chain and append it to data/skew_history.jsonl (one row per session).

Risk reversal RR25 = IV(25-delta PUT) - IV(25-delta CALL).
  RR25 > 0  -> OTM puts richer than OTM calls = downside skew (hedging/fear).
  RR25 < 0  -> calls richer = upside skew (call chasing / melt-up).
Also stored normalized by ATM IV (rr25_norm) so it's comparable across vol levels.

We take the expiry whose DTE is closest to 30 (standard 1-month skew; 0DTE skew
is noise), interpolate IV at |delta|=0.25 on each wing, and ATM IV at delta~0.50.

Usage (cloud): fetch the chain (auto-saves to a tool-results .txt), then:
  python3 scripts/av_skew.py <saved_file> --sym QQQ --log
Reads {"result":"<csv>"} or raw CSV. Columns: expiration, strike, type,
implied_volatility, delta, date.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load_av(path) -> pd.DataFrame:
    raw = Path(path).read_text()
    try:
        blob = json.loads(raw)
        csv = blob["result"] if isinstance(blob, dict) and "result" in blob else raw
    except json.JSONDecodeError:
        csv = raw
    df = pd.read_csv(io.StringIO(csv))
    for c in ("strike", "implied_volatility", "delta"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["type"] = df["type"].str.lower()
    return df


def iv_at_delta(sub: pd.DataFrame, target: float) -> float:
    """Interpolate IV at a given signed delta on one option wing."""
    s = sub.dropna(subset=["delta", "implied_volatility"])
    s = s[(s["implied_volatility"] > 0.01) & (s["implied_volatility"] < 2.0)]
    if len(s) < 2:
        return float("nan")
    s = s.sort_values("delta")
    x, y = s["delta"].values, s["implied_volatility"].values
    if target < x.min() or target > x.max():
        return float("nan")               # don't extrapolate past the wing
    return float(np.interp(target, x, y))


def skew_for_expiry(g: pd.DataFrame) -> dict | None:
    calls = g[g["type"] == "call"]
    puts = g[g["type"] == "put"]
    iv25c = iv_at_delta(calls, 0.25)      # OTM call wing
    iv25p = iv_at_delta(puts, -0.25)      # OTM put wing
    atm_c = iv_at_delta(calls, 0.50)
    atm_p = iv_at_delta(puts, -0.50)
    atm = np.nanmean([atm_c, atm_p])
    if not np.isfinite(iv25c) or not np.isfinite(iv25p) or not np.isfinite(atm):
        return None
    rr25 = iv25p - iv25c
    return {"atm_iv": round(atm, 5), "iv25p": round(iv25p, 5), "iv25c": round(iv25c, 5),
            "rr25": round(rr25, 5), "rr25_norm": round(rr25 / atm, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--sym", required=True)
    ap.add_argument("--dte-target", type=int, default=30)
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()

    df = load_av(a.file)
    asof = str(df["date"].max())[:10]
    asof_d = dt.datetime.strptime(asof, "%Y-%m-%d").date()
    df["exp_d"] = pd.to_datetime(df["expiration"]).dt.date
    df["dte"] = df["exp_d"].apply(lambda e: (e - asof_d).days)
    fut = df[df["dte"] >= 1]
    if fut.empty:
        raise SystemExit("no future expiries")
    # expiry whose DTE is closest to the target
    exps = fut.groupby("exp_d")["dte"].first()
    pick = (exps - a.dte_target).abs().idxmin()
    g = fut[fut["exp_d"] == pick]
    dte = int(exps[pick])
    res = skew_for_expiry(g)
    if res is None:
        raise SystemExit(f"could not interpolate 25d wings for {asof} exp {pick} (dte {dte})")

    print(f"{a.sym} {asof}  exp {pick} (dte {dte})")
    print(f"  ATM IV {res['atm_iv']*100:.1f}%  |  25d put {res['iv25p']*100:.1f}%  "
          f"25d call {res['iv25c']*100:.1f}%")
    print(f"  RR25 = {res['rr25']*100:+.2f} vol pts   (norm {res['rr25_norm']:+.3f})  "
          f"{'downside skew (fear)' if res['rr25']>0 else 'upside skew (greed)'}")

    if a.log:
        row = {"date": asof, "sym": a.sym, "dte": dte, **res}
        logf = ROOT / "data" / "skew_history.jsonl"
        existing = [json.loads(l) for l in logf.read_text().splitlines()] if logf.exists() else []
        existing = [r for r in existing if not (r["date"] == asof and r["sym"] == a.sym)]
        with logf.open("w") as fh:
            for r in sorted(existing + [row], key=lambda r: r["date"]):
                fh.write(json.dumps(r) + "\n")
        print(f"  -> logged to skew_history.jsonl ({len(existing)+1} rows)")


if __name__ == "__main__":
    main()
