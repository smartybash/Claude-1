"""Compute dealer GEX / gamma-flip / walls from an options-chain export and write
them into data/gamma_levels.json — so a rerun reads NEGATIVE vs POSITIVE gamma
"at the open" automatically instead of you eyeballing it.

WHERE THE INPUT COMES FROM: export the option chain (with greeks) for the index
you trade — SPX/NDX (or SPY/QQQ) — from WealthCharts, or pull it from the IBKR
API. Save it as CSV or JSON with a row per strike.

REQUIRED columns (names are flexible — common aliases accepted):
  strike, call_oi, put_oi,  AND EITHER
    call_gamma, put_gamma                 (greeks straight from the platform), OR
    call_iv, put_iv   plus  --dte --rate  (we compute Black-Scholes gamma)
OPTIONAL: call_delta, put_delta           (adds the dealer-delta directional lean)

USAGE:
  python3 scripts/gex_calc.py chain.csv --sym NQ --spot 29500 --mult 20 --dte 1
  # mult: SPX/NDX index=100, ES=50, NQ=20, SPY/QQQ=100. --dte only needed for IV.

CONVENTION (standard/SqueezeMetrics): per-strike GEX = gamma*OI*mult*spot^2*0.01,
calls +, puts -.  Net > 0 = POSITIVE gamma (dealers dampen -> range/chop).
Net < 0 = NEGATIVE gamma (dealers amplify -> trend / 'long day').  Flip = the
spot price where net GEX crosses zero (below it = negative gamma).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ALIASES = {
    "k": "strike", "strikes": "strike",
    "coi": "call_oi", "c_oi": "call_oi", "calloi": "call_oi", "call_open_interest": "call_oi",
    "poi": "put_oi", "p_oi": "put_oi", "putoi": "put_oi", "put_open_interest": "put_oi",
    "cgamma": "call_gamma", "c_gamma": "call_gamma", "gamma_call": "call_gamma",
    "pgamma": "put_gamma", "p_gamma": "put_gamma", "gamma_put": "put_gamma",
    "civ": "call_iv", "piv": "put_iv", "cdelta": "call_delta", "pdelta": "put_delta",
}


def _norm(x):
    return math.erf(x / math.sqrt(2)) / 2 + 0.5


def _pdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def bs_gamma(S, K, sigma, T, r=0.0):
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * math.sqrt(T))
    return _pdf(d1) / (S * sigma * math.sqrt(T))


def bs_delta(S, K, sigma, T, call=True, r=0.0):
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * math.sqrt(T))
    return _norm(d1) if call else _norm(d1) - 1


def load_chain(path):
    p = Path(path)
    if p.suffix.lower() == ".json":
        raw = json.loads(p.read_text())
        df = pd.DataFrame(raw["data"] if isinstance(raw, dict) and "data" in raw else raw)
    else:
        df = pd.read_csv(p)
    df.columns = [ALIASES.get(c.strip().lower(), c.strip().lower()) for c in df.columns]
    for c in ("strike", "call_oi", "put_oi"):
        if c not in df.columns:
            raise SystemExit(f"chain missing required column: {c} (have {list(df.columns)})")
    return df


def net_gex_at(df, S, mult, iv_mode, T, r):
    """Net GEX ($ per 1% move) at hypothetical spot S. calls +, puts -."""
    tot = 0.0
    for _, row in df.iterrows():
        K = float(row["strike"])
        if iv_mode:
            cg = bs_gamma(S, K, float(row.get("call_iv", 0) or 0), T, r)
            pg = bs_gamma(S, K, float(row.get("put_iv", 0) or 0), T, r)
        else:
            cg = float(row.get("call_gamma", 0) or 0)
            pg = float(row.get("put_gamma", 0) or 0)
        tot += (cg * float(row["call_oi"] or 0) - pg * float(row["put_oi"] or 0)) * mult * S * S * 0.01
    return tot


def find_flip(df, spot, mult, iv_mode, T, r):
    """Scan spot +/-12% for the zero-gamma crossing nearest current spot."""
    lo, hi = spot * 0.88, spot * 1.12
    xs = [lo + (hi - lo) * i / 60 for i in range(61)]
    vals = [(S, net_gex_at(df, S, mult, iv_mode, T, r)) for S in xs]
    best = None
    for (s0, v0), (s1, v1) in zip(vals, vals[1:]):
        if v0 == 0 or (v0 < 0) != (v1 < 0):        # sign change
            cross = s0 if v1 == v0 else s0 + (s1 - s0) * (-v0) / (v1 - v0)
            if best is None or abs(cross - spot) < abs(best - spot):
                best = cross
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chain")
    ap.add_argument("--sym", required=True)
    ap.add_argument("--spot", type=float, required=True)
    ap.add_argument("--mult", type=float, required=True)
    ap.add_argument("--dte", type=float, default=1.0, help="calendar days to expiry (IV mode)")
    ap.add_argument("--rate", type=float, default=0.0)
    ap.add_argument("--write", action="store_true", help="write into data/gamma_levels.json")
    a = ap.parse_args()

    df = load_chain(a.chain)
    iv_mode = "call_gamma" not in df.columns or "put_gamma" not in df.columns
    if iv_mode and ("call_iv" not in df.columns or "put_iv" not in df.columns):
        raise SystemExit("need call_gamma/put_gamma OR call_iv/put_iv (+ --dte) in the chain")
    res = compute_gex(df, a.spot, a.mult, iv_mode, a.dte / 365.0, a.rate)
    print_read(a.sym, a.spot, a.mult, iv_mode, res)
    if a.write:
        write_levels(a.sym, res)
        print(f"  -> wrote data/gamma_levels.json[{a.sym}]")


def compute_gex(df, spot, mult, iv_mode, T, r=0.0) -> dict:
    """Net GEX, gamma flip, call/put walls, dealer delta from a per-strike chain.
    Reused by gex_calc (CSV) and pull_ibkr_chain (live IBKR). Columns: strike,
    call_oi, put_oi, and either call_gamma/put_gamma or (iv_mode) call_iv/put_iv;
    optional call_delta/put_delta."""
    net = net_gex_at(df, spot, mult, iv_mode, T, r)
    flip = find_flip(df, spot, mult, iv_mode, T, r)
    # WALLS = gamma-weighted (Tanuki/SpotGamma style), NOT raw open interest.
    # The wall is the strike carrying the most dealer GAMMA on its side
    # (gamma * OI ~ gamma$), which peaks near-the-money — so walls sit around
    # price, not on a deep round-number/LEAP strike where OI piles up but gamma
    # is ~0. (Raw-OI walls were why the NQ put wall printed 900pts away.)
    strike = df["strike"].astype(float)
    if not iv_mode:
        cg = df["call_gamma"].fillna(0)
        pg = df["put_gamma"].fillna(0)
    else:                                            # BS gamma at spot per strike
        cg = pd.Series([bs_gamma(spot, float(k), float(iv or 0), T, r)
                        for k, iv in zip(strike, df.get("call_iv", 0).fillna(0)
                                         if "call_iv" in df else [0] * len(df))],
                       index=df.index)
        pg = pd.Series([bs_gamma(spot, float(k), float(iv or 0), T, r)
                        for k, iv in zip(strike, df.get("put_iv", 0).fillna(0)
                                         if "put_iv" in df else [0] * len(df))],
                       index=df.index)
    cw = cg * df["call_oi"].fillna(0)
    pw = pg * df["put_oi"].fillna(0)
    # call wall on/above spot, put wall on/below spot (the support/resistance sides)
    cw_side = cw.where(strike >= spot, 0.0)
    pw_side = pw.where(strike <= spot, 0.0)
    call_wall = float(strike[cw_side.idxmax()]) if cw_side.max() > 0 else float(strike[cw.idxmax()])
    put_wall = float(strike[pw_side.idxmax()]) if pw_side.max() > 0 else float(strike[pw.idxmax()])
    dealer_delta = None
    if {"call_delta", "put_delta"}.issubset(df.columns):
        # dealers are short customer calls / long puts -> dealer delta ~ -(cd*coi)+(pd*poi)
        dealer_delta = float((-(df["call_delta"].fillna(0) * df["call_oi"].fillna(0))
                              + (df["put_delta"].fillna(0) * df["put_oi"].fillna(0))).sum() * mult)
    return {"net_gex": net, "gamma_flip": flip,
            "call_wall": call_wall, "put_wall": put_wall,
            "dealer_delta": dealer_delta}


def print_read(sym, spot, mult, iv_mode, res):
    net, flip = res["net_gex"], res["gamma_flip"]
    state = "NEGATIVE" if net < 0 else "POSITIVE"
    print(f"{sym}  spot {spot:.2f}  mult {mult:g}  ({'IV->BS gamma' if iv_mode else 'chain gamma'})")
    print(f"  NET GEX = {net/1e9:+.2f}B  -> {state} GAMMA "
          f"({'trend/expansion, long-day if it turns up' if net < 0 else 'range/mean-revert, breakouts stall'})")
    print(f"  gamma flip (zero-gamma) = {flip:.2f}" if flip else "  gamma flip = (no crossing in +/-12%)")
    if flip:
        print(f"    spot is {'BELOW' if spot < flip else 'above'} the flip -> "
              f"{'NEGATIVE' if spot < flip else 'positive'} gamma at open")
    print(f"  call wall {res['call_wall']:.2f} (resistance/magnet) | put wall {res['put_wall']:.2f} (support/magnet)")
    if res.get("dealer_delta") is not None:
        dd = res["dealer_delta"]
        print(f"  dealer delta = {dd/1e6:+.1f}M -> lean {'UP (buy dips)' if dd > 0 else 'DOWN (sell rallies)'}")


def write_levels(sym, res, source="gex_calc"):
    """Merge computed levels into data/gamma_levels.json[sym]."""
    f = ROOT / "data" / "gamma_levels.json"
    blob = json.loads(f.read_text()) if f.exists() else {"levels": {}}
    blob.setdefault("levels", {})
    flip = res["gamma_flip"]
    entry = {"net_gex": round(res["net_gex"], 0),
             "gamma_flip": round(flip, 2) if flip else None,
             "zero_gamma": round(flip, 2) if flip else None,
             "call_wall": round(res["call_wall"], 2),
             "put_wall": round(res["put_wall"], 2)}
    if res.get("dealer_delta") is not None:
        entry["dealer_delta"] = round(res["dealer_delta"], 0)
    if res.get("spot") is not None:
        entry["spot"] = round(res["spot"], 2)
    # source is stored PER ENTRY (not just globally) so writing one symbol's
    # levels can't strip another's provenance (e.g. SPY overwriting NQ's FOP tag).
    entry["source"] = source
    blob["levels"][sym] = entry
    blob["source"] = source
    f.write_text(json.dumps(blob, indent=2))


if __name__ == "__main__":
    main()
