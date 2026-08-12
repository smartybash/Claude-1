"""Daily NQ gamma read — the Vol Desk level map for Nasdaq futures.

Two data paths, because no single provider does the whole job:

  --av-chain FILE     Alpha Vantage QQQ chain (HISTORICAL_OPTIONS, csv).
                      Free tier, prior session's close, vendor IV + OI.
                      QQQ is the validated NQ proxy (30-min return
                      correlation 0.999, see reports/trend_regime_study.md).
                      Levels are computed in QQQ space and multiplied by
                      --ratio to land in NQ points.
  --nq-chain FILE     IBKR NQ futures-options snapshot (JSON, same shape
                      as data/ibkr_oi_*.json). True NQ gamma, multiplier
                      20, no proxy step.

The AV file may be either raw CSV or the JSON envelope the MCP writes
when a response is offloaded ({"result": "<csv>"}).

    python scripts/nq_daily.py --av-chain chain.csv --nq-close 29835.5 \
        --qqq-close 718.45 --dte 9

--ratio is derived from the two closes when both are given, else pass it
directly. Print the report and optionally write it with -o.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk.gex import Leg, levels, rescale  # noqa: E402

NQ_MULT = 20.0      # NQ futures-option contract multiplier
EQ_MULT = 100.0


def load_av_chain(path: str | Path, expiration: str | None = None) -> tuple[list[Leg], str]:
    """Parse an Alpha Vantage options chain into legs.

    Accepts the raw CSV or the {"result": "<csv>"} envelope. Returns the
    legs plus the expiration actually used (the nearest one present when
    not specified).
    """
    raw = Path(path).read_text()
    if raw.lstrip().startswith("{"):
        raw = json.loads(raw)["result"]
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows:
        raise ValueError(f"{path}: no rows")

    exps = sorted({r["expiration"] for r in rows})
    exp = expiration or exps[0]
    legs = []
    for r in rows:
        if r["expiration"] != exp:
            continue
        try:
            oi = int(float(r["open_interest"]))
            iv = float(r["implied_volatility"])
        except (ValueError, KeyError):
            continue
        if oi <= 0 or iv <= 0:
            continue
        legs.append(Leg(float(r["strike"]), r["type"].lower() == "call", oi, iv))
    if not legs:
        raise ValueError(f"{path}: no usable contracts for expiration {exp}")
    return legs, exp


def load_nq_chain(path: str | Path) -> tuple[list[Leg], float, float]:
    """Parse an IBKR NQ FOP snapshot: {spot, annual_iv, call_oi{}, put_oi{}}."""
    d = json.loads(Path(path).read_text())
    nq = d["names"]["NQ"] if "names" in d else d
    default_iv = nq["annual_iv"]
    ivs = nq.get("iv", {})
    legs = []
    for k, oi in nq["call_oi"].items():
        if oi > 0:
            legs.append(Leg(float(k), True, int(oi), float(ivs.get(k, default_iv))))
    for k, oi in nq["put_oi"].items():
        if oi > 0:
            legs.append(Leg(float(k), False, int(oi), float(ivs.get(k, default_iv))))
    return legs, float(nq["spot"]), float(d.get("dte", nq.get("dte", 15)))


def fmt(v, nd=0):
    return f"{v:,.{nd}f}" if isinstance(v, (int, float)) else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily NQ gamma level read")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--av-chain", help="Alpha Vantage QQQ chain (csv or MCP json envelope)")
    src.add_argument("--nq-chain", help="IBKR NQ futures-option snapshot (json)")
    ap.add_argument("--expiration", help="expiration to use (default: nearest in file)")
    ap.add_argument("--dte", type=float, help="days to expiry (required for --av-chain)")
    ap.add_argument("--nq-close", type=float, help="NQ front-month close")
    ap.add_argument("--qqq-close", type=float, help="QQQ close (with --nq-close gives the ratio)")
    ap.add_argument("--ratio", type=float, help="NQ points per QQQ dollar (overrides the closes)")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    if args.nq_chain:
        legs, spot, dte = load_nq_chain(args.nq_chain)
        if args.dte:
            dte = args.dte
        lv = levels(spot, legs, dte, mult=NQ_MULT)
        basis = "IBKR NQ futures options (true NQ gamma, multiplier 20)"
        ratio = None
        exp = "—"
    else:
        if args.dte is None:
            ap.error("--dte is required with --av-chain")
        ratio = args.ratio
        if ratio is None:
            if not (args.nq_close and args.qqq_close):
                ap.error("need --ratio, or both --nq-close and --qqq-close")
            ratio = args.nq_close / args.qqq_close
        legs, exp = load_av_chain(args.av_chain, args.expiration)
        spot = args.qqq_close or max(l.strike for l in legs) * 0  # spot required below
        if not spot:
            ap.error("--qqq-close is required with --av-chain (it is the spot)")
        qqq_lv = levels(spot, legs, args.dte, mult=EQ_MULT)
        lv = rescale(qqq_lv, ratio)
        basis = (f"Alpha Vantage QQQ chain x {ratio:.3f} NQ pts/$ "
                 f"(QQQ is the validated NQ proxy)")

    lines = [f"# NQ gamma read — {date.today().isoformat()}", "",
             f"Source: {basis}",
             f"Expiration: {exp} · {args.dte if args.dte else dte:.0f} DTE · "
             f"{len(legs)} contracts · call OI {lv['call_oi']:,} / put OI {lv['put_oi']:,}", "",
             "| Level | NQ points |", "|---|---|",
             f"| Spot | {fmt(lv['spot'], 1)} |",
             f"| nTrans (stop) | {fmt(lv['n_trans'])} |",
             f"| zeroGEX (flip) | {fmt(lv['zero_gex'])} |",
             f"| pTrans (entry) | {fmt(lv['p_trans'])} |",
             f"| +GEX / T1 | {fmt(lv['plus_gex'])} |",
             f"| T2 | {fmt(lv['t2'])} |",
             f"| COTMP (put mass) | {fmt(lv['cotmp'])} |",
             f"| COTMC (call mass) | {fmt(lv['cotmc'])} |", ""]

    gex = lv["gex_at_spot"]
    lines.append(f"Dealer gamma at spot: **{gex:+,.1f} $M per 1%** — "
                 f"{'positive: moves get dampened, mean-reversion regime' if gex > 0 else 'negative: hedging amplifies moves, trend/acceleration regime'}.")
    if lv.get("cushion") is not None:
        lines.append(f"COTMP cushion: {lv['cushion']:+.1%} "
                     f"({'passes' if lv['cushion'] >= 0.02 else 'FAILS'} the 2.0% floor).")
    if lv.get("rr") is not None:
        lines.append(f"R/R to +GEX from pTrans: {lv['rr']:.2f} "
                     f"({'passes' if lv['rr'] >= 2.0 else 'FAILS'} the 2.0 bar).")
    else:
        lines.append("R/R: undefined — spot is not above pTrans, so there is no entry leg.")
    lines += ["",
              "Position vs the band: " + (
                  "**above pTrans** — the P2P long structure is live."
                  if lv["p_trans"] and lv["spot"] > lv["p_trans"] else
                  "**below pTrans** — no long trigger; watch for a 5-min close above it."),
              "",
              "Grade, delta balance and db_change are not derivable from either "
              "feed, so entry filters 1-2 remain UNKNOWN and nothing here is CONFIRMED."]

    report = "\n".join(lines)
    print(report)
    if args.out:
        Path(args.out).write_text(report + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
