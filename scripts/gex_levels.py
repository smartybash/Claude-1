"""Approximate Vol Desk GEX levels from an IBKR option-chain OI snapshot.

    python scripts/gex_levels.py data/ibkr_oi_20260702.json [-o report.md]

The vendor gamma screen isn't reachable from IBKR, so this rebuilds the
level set from first principles on the front-monthly chain:

  net GEX(S)   sum over strikes of [callOI - putOI] x BS-gamma(K, S)
               x 100 x S^2 x 1%  (dollar gamma per 1% move; dealers long
               calls / short puts convention)
  zeroGEX      the flip: where net GEX(S) crosses zero
  nTrans/pTrans  edges of the neutral band around the flip — the largest S
               below (smallest S above) the flip where |GEX| reaches 5% of
               the curve's max. Multiple crossings widen the band to the
               outermost ones.
  +GEX (T1)    strike with the largest positive per-strike net GEX at spot
               (the call wall / magnet)
  COTMP/COTMC  OI-weighted center of put / call mass
  T2           next major positive-GEX strike above +GEX (else COTMC)

Flat-vol BS gamma from the underlying's annual IV — good enough for level
location, which is OI-driven; the vendor's exact transition math will
differ in detail. Grade, delta balance, and db_change are NOT derivable
from IBKR: the entry filters that need them stay UNKNOWN in the output.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

RISK_FREE = 0.04
BAND = 0.05          # neutral-band edge: 5% of max |GEX| on the grid
GRID_PCT = 0.15      # scan spot +/- 15%
GRID_N = 601


def bs_gamma(spot: float, strike: float, iv: float, t_years: float) -> float:
    if t_years <= 0 or iv <= 0 or spot <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (RISK_FREE + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    phi = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    return phi / (spot * iv * math.sqrt(t_years))


def net_gex_at(s: float, strikes: dict[float, tuple[int, int]], iv: float, t: float) -> float:
    """Dealer dollar gamma per 1% move if spot were at s ($M)."""
    tot = 0.0
    for k, (c_oi, p_oi) in strikes.items():
        tot += (c_oi - p_oi) * bs_gamma(s, k, iv, t) * 100 * s * s * 0.01
    return tot / 1e6


def levels(name: str, spot: float, iv: float, dte: int,
           call_oi: dict[str, int], put_oi: dict[str, int]) -> dict:
    t = dte / 365
    ks = sorted(set(call_oi) | set(put_oi), key=float)
    strikes = {float(k): (call_oi.get(k, 0), put_oi.get(k, 0)) for k in ks}

    grid = [spot * (1 - GRID_PCT) + i * (2 * GRID_PCT * spot / (GRID_N - 1)) for i in range(GRID_N)]
    curve = [net_gex_at(s, strikes, iv, t) for s in grid]
    peak = max(abs(v) for v in curve)

    crossings = [grid[i] for i in range(1, GRID_N) if curve[i - 1] * curve[i] < 0]
    if crossings:
        zero_gex = crossings[len(crossings) // 2]
        n_trans = max((grid[i] for i in range(GRID_N)
                       if grid[i] < crossings[0] and curve[i] <= -BAND * peak), default=None)
        p_trans = min((grid[i] for i in range(GRID_N)
                       if grid[i] > crossings[-1] and curve[i] >= BAND * peak), default=None)
    else:
        zero_gex = n_trans = p_trans = None  # one-signed gamma across the whole grid

    # per-strike net GEX at current spot -> walls and targets
    per_strike = {k: (c - p) * bs_gamma(spot, k, iv, t) * 100 * spot * spot * 0.01 / 1e6
                  for k, (c, p) in strikes.items()}
    pos = {k: v for k, v in per_strike.items() if v > 0}
    plus_gex = max(pos, key=pos.get) if pos else None
    t2 = None
    if plus_gex is not None:
        above = {k: v for k, v in pos.items() if k > plus_gex}
        t2 = max(above, key=above.get) if above else None

    put_tot = sum(p for _, p in strikes.values())
    call_tot = sum(c for c, _ in strikes.values())
    cotmp = sum(k * p for k, (_, p) in strikes.items()) / put_tot if put_tot else None
    cotmc = sum(k * c for k, (c, _) in strikes.items()) / call_tot if call_tot else None

    out = {"symbol": name, "spot": spot, "gex_at_spot": net_gex_at(spot, strikes, iv, t),
           "zero_gex": zero_gex, "n_trans": n_trans, "p_trans": p_trans,
           "plus_gex": plus_gex, "t2": t2, "cotmp": cotmp, "cotmc": cotmc,
           "sign": "positive" if curve[GRID_N // 2] > 0 and not crossings else
                   ("negative" if not crossings else "mixed")}
    if cotmp:
        out["cushion"] = (spot - cotmp) / cotmp
    if p_trans and plus_gex and spot > p_trans and plus_gex > spot:
        out["rr"] = (plus_gex - spot) / (spot - p_trans)
    return out


def fmt(v, nd=2):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot_json")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    data = json.loads(Path(args.snapshot_json).read_text())
    dte = data["dte"]
    rows = [levels(sym, d["spot"], d["annual_iv"], dte, d["call_oi"], d["put_oi"])
            for sym, d in data["names"].items()]

    lines = [f"# GEX levels from IBKR chain OI — as of {data['as_of']}", "",
             f"Front monthly {data['expiry']} ({dte} DTE), flat-vol BS gamma. "
             "Computed levels, not the vendor screen — see scripts/gex_levels.py.", "",
             "| Name | Spot | nTrans | zeroGEX | pTrans | +GEX (T1) | T2 | COTMP | COTMC | Cushion | R/R | GEX@spot ($M/1%) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['symbol']} | {fmt(r['spot'])} | {fmt(r['n_trans'])} | {fmt(r['zero_gex'])} "
            f"| {fmt(r['p_trans'])} | {fmt(r['plus_gex'], 0)} | {fmt(r['t2'], 0)} "
            f"| {fmt(r['cotmp'], 1)} | {fmt(r['cotmc'], 1)} "
            f"| {r.get('cushion', 0):+.1%} | {fmt(r.get('rr'))} | {r['gex_at_spot']:+.1f} |")
    report = "\n".join(lines)
    print(report)
    if args.out:
        Path(args.out).write_text(report + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
