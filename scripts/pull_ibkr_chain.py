"""Pull a live option chain from YOUR IBKR (TWS / IB Gateway) and compute the
dealer-gamma read — net GEX, gamma flip, call/put walls, dealer delta — then
write them into data/gamma_levels.json for the rerun. No manual export.

RUNS ON YOUR MACHINE (not the cloud sandbox): needs TWS or IB Gateway running
with the API enabled (Global Config > API > Enable ActiveX and Socket Clients),
and `pip install ib_insync pandas`. Live greeks/OI need a market-data
subscription; without one, pass --delayed (delayed greeks still give a usable
read pre-open).

WHAT IT PULLS (per --sym, override with --underlying/--sectype/--exchange):
  NQ  -> NDX index options (mult 100)     ES  -> SPX index options (mult 100)
  QQQ -> QQQ ETF options  (mult 100)      SPY -> SPY ETF options  (mult 100)
NDX/SPX are ~ the NQ/ES scale (small basis) — the flip in index points maps
directly onto the futures for the regime call. It writes under the --sym key.

USAGE (pre-open, at your machine):
  python3 scripts/pull_ibkr_chain.py --sym NQ --write
  python3 scripts/pull_ibkr_chain.py --sym QQQ --port 7496 --max-strikes 50 --write
  # then run the normal rerun — confluence prints NEGATIVE/POSITIVE gamma at open.

Ports: TWS live 7496 / paper 7497; Gateway live 4001 / paper 4002 (default 7497).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gex_calc  # reuse the exact GEX math + writer

# --sym -> (symbol, secType, exchange, currency, out multiplier)
UNDERLYING = {
    "NQ":  ("NDX", "IND", "NASDAQ", "USD", 100),
    "ES":  ("SPX", "IND", "CBOE",   "USD", 100),
    "QQQ": ("QQQ", "STK", "SMART",  "USD", 100),
    "SPY": ("SPY", "STK", "SMART",  "USD", 100),
}


def pick_expiry(expirations, dte_max):
    today = dt.date.today()
    fut = []
    for e in sorted(set(expirations)):
        d = dt.datetime.strptime(e, "%Y%m%d").date()
        if d >= today:
            fut.append((e, max((d - today).days, 0)))
    if not fut:
        raise SystemExit("no future expirations returned")
    within = [x for x in fut if x[1] <= dte_max]
    return (within or fut)[0]          # nearest expiry (0DTE if listed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", required=True, choices=list(UNDERLYING))
    ap.add_argument("--underlying"); ap.add_argument("--sectype"); ap.add_argument("--exchange")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7497)
    ap.add_argument("--clientid", type=int, default=17)
    ap.add_argument("--dte-max", type=int, default=7, help="only consider expiries within N days")
    ap.add_argument("--max-strikes", type=int, default=40, help="strikes each side of spot")
    ap.add_argument("--wait", type=float, default=6.0, help="seconds to let greeks/OI populate")
    ap.add_argument("--delayed", action="store_true", help="use delayed data (no live sub)")
    ap.add_argument("--rate", type=float, default=0.0)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    try:
        from ib_insync import IB, Index, Stock, Option, util  # noqa
    except ImportError:
        raise SystemExit("pip install ib_insync  (run this on your machine with TWS/Gateway up)")

    sym0, sec0, exch0, cur0, mult = UNDERLYING[a.sym]
    sym0 = a.underlying or sym0; sec0 = a.sectype or sec0; exch0 = a.exchange or exch0

    ib = IB()
    ib.connect(a.host, a.port, clientId=a.clientid, timeout=15)
    ib.reqMarketDataType(3 if a.delayed else 1)
    try:
        und = Index(sym0, exch0, cur0) if sec0 == "IND" else Stock(sym0, exch0, cur0)
        ib.qualifyContracts(und)
        [ut] = ib.reqTickers(und)
        spot = ut.marketPrice()
        if not spot or spot != spot:  # NaN
            spot = ut.close or ut.last
        if not spot:
            raise SystemExit("could not get underlying spot; is data connected?")
        print(f"{a.sym}: {sym0} spot {spot:.2f}")

        params = ib.reqSecDefOptParams(und.symbol, "", und.secType, und.conId)
        params = [p for p in params if p.strikes and p.expirations] or params
        chain = sorted(params, key=lambda p: (p.exchange != "SMART", len(p.strikes)))[0]
        exp, dte = pick_expiry(chain.expirations, a.dte_max)
        strikes = sorted(chain.strikes)
        near = min(strikes, key=lambda s: abs(s - spot))
        i = strikes.index(near)
        strikes = strikes[max(0, i - a.max_strikes): i + a.max_strikes + 1]
        print(f"  expiry {exp} (DTE {dte})  tradingClass {chain.tradingClass}  "
              f"{len(strikes)} strikes {strikes[0]:g}-{strikes[-1]:g}")

        # build + qualify call/put contracts
        opts = []
        for K in strikes:
            for right in ("C", "P"):
                opts.append(Option(und.symbol, exp, K, right, "SMART",
                                   tradingClass=chain.tradingClass,
                                   multiplier=chain.multiplier or "100", currency=cur0))
        opts = [o for o in ib.qualifyContracts(*opts) if o.conId]

        # subscribe: 101 = option OI (call/put), 106 = implied vol; modelGreeks arrive on tick 13
        tickers = {}
        for o in opts:
            tickers[(o.strike, o.right)] = ib.reqMktData(o, "100,101,104,106", False, False)
        ib.sleep(a.wait)

        rows = {}
        for (K, right), t in tickers.items():
            row = rows.setdefault(K, {"strike": K})
            g = t.modelGreeks
            if right == "C":
                row["call_oi"] = t.callOpenInterest
                if g:
                    row["call_gamma"], row["call_delta"], row["call_iv"] = g.gamma, g.delta, g.impliedVol
            else:
                row["put_oi"] = t.putOpenInterest
                if g:
                    row["put_gamma"], row["put_delta"], row["put_iv"] = g.gamma, g.delta, g.impliedVol
        for o in opts:
            ib.cancelMktData(o)
    finally:
        ib.disconnect()

    df = pd.DataFrame(list(rows.values()))
    for c in ("call_oi", "put_oi", "call_gamma", "put_gamma", "call_delta", "put_delta", "call_iv", "put_iv"):
        if c not in df.columns:
            df[c] = float("nan")
    df = df.dropna(subset=["call_oi", "put_oi"], how="all")
    have_g = df[["call_gamma", "put_gamma"]].notna().any().all()
    have_iv = df[["call_iv", "put_iv"]].notna().any().all()
    iv_mode = not have_g and have_iv     # prefer live gamma; use IV->BS only if greeks missing
    if not have_g and not have_iv:
        raise SystemExit("no greeks or IV came back — check market-data subscription (try --delayed)")
    # for a real FLIP we need to reprice across spot -> IV mode; if we only have
    # static gamma the sign of net GEX is still valid, flip will be None.
    T = max(dte, 1) / 365.0
    res = gex_calc.compute_gex(df.fillna(0.0), spot, mult, iv_mode, T, a.rate)
    gex_calc.print_read(a.sym, spot, mult, iv_mode, res)
    if res["gamma_flip"] is None and have_iv:
        # recompute flip in IV mode even if we used live gamma for net GEX
        res["gamma_flip"] = gex_calc.find_flip(df.fillna(0.0), spot, mult, True, T, a.rate)
        if res["gamma_flip"]:
            print(f"  (flip via IV reprice = {res['gamma_flip']:.2f})")

    if a.write:
        gex_calc.write_levels(a.sym, res, source=f"IBKR {exp}")
        print(f"  -> wrote data/gamma_levels.json[{a.sym}]  (run the rerun to see it)")


if __name__ == "__main__":
    main()
