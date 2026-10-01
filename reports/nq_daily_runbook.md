# Running the Vol Desk gamma read on NQ, daily

Answer to "can this be rerun on NQ daily using the AV MCP": **yes daily, but
Alpha Vantage cannot do NQ directly.** AV has no futures at all, so the AV
path runs on QQQ as a proxy. IBKR *can* do NQ natively. Both paths are
implemented; the verification behind that claim is below.

## What each provider actually offers (verified 2026-08-12)

| Capability | Alpha Vantage | IBKR |
|---|---|---|
| NQ futures symbol | **No** — `SYMBOL_SEARCH("NQ nasdaq 100 futures")` returns zero matches | Yes (conid 11004958, CME) |
| NQ futures options (FOP) | **No** — options endpoints are US equity/ETF only | **Yes** — full expiry ladder, dailies through quarterlies |
| NQ open interest | No | Yes, per contract |
| NQ live price | n/a | **No** — snapshot returns `{}` (no CME market-data entitlement); historical bars *do* work |
| QQQ options + OI + Greeks | **Yes, free tier** via `HISTORICAL_OPTIONS` (prior session) | Yes, but one call per contract per side |
| QQQ realtime options | Premium-gated on this key | Yes |
| NDX index | Premium-gated on this key | — |

Two consequences worth knowing:

1. **AV's free options endpoint is T+1**, not intraday. `REALTIME_OPTIONS`
   returns a premium notice with artificial sample data. So the AV path
   gives you a *prior-session close* level map — which is exactly what an
   evening scan wants, and useless for an intraday re-read.
2. **IBKR has NQ options but not NQ prices** on this account. Chain, OI and
   per-contract IV all come through; `get_price_snapshot` on the future
   returns empty. Spot has to come from `get_price_history` (daily bars
   work) until CME data is added to the subscription.

## The two paths

Both land in `scripts/nq_daily.py`, sharing the level engine in
`vol_desk/gex.py`.

**Path A — AV QQQ proxy (free, T+1, no entitlements needed)**

QQQ is the validated NQ proxy: 30-minute return correlation 0.999
(`reports/trend_regime_study.md`). Levels are computed in QQQ space and
multiplied into NQ points.

```
python scripts/nq_daily.py --av-chain chain.csv \
    --qqq-close 718.45 --nq-close 29835.5 --dte 10
```

**Path B — IBKR NQ futures options (true NQ gamma, multiplier 20)**

No proxy step, real CME positioning, but it costs one MCP call per contract
per side to collect open interest, so a 25-strike window is ~50 calls.

```
python scripts/nq_daily.py --nq-chain data/ibkr_nq_oi_YYYYMMDD.json
```

## The scale factor

NQ points per QQQ dollar. Measured 41.528 on Aug 11 (29,835.5 / 718.45),
against a 41.57 mean over 252 overlapping hourly bars in the repo's own
data (range 41.47–41.69). **It drifts** — roughly −0.1/month over the
May–July sample, from ETF expense drag and futures roll — about 0.5% over
two months, which is ~150 NQ points. Recompute it each run from the two
closes rather than pinning it; that is why `--nq-close`/`--qqq-close` are
preferred over `--ratio`.

## Daily procedure

1. `MARKET_STATUS` (AV) to confirm the session closed.
2. `HISTORICAL_OPTIONS` (AV) — `symbol=QQQ`, `date=<prior session>`,
   `expiration=<front monthly>`, `datatype=csv`, `return_full_data=true`.
   The full chain across all expiries is 12.5k contracts / 2.1M tokens, so
   **always pass `expiration`**; one expiry is ~460 rows. Large responses
   are offloaded to a file — pass that file straight to `--av-chain`, the
   parser reads both the raw CSV and the `{"result": "<csv>"}` envelope.
3. `GLOBAL_QUOTE` (AV) for the QQQ close; `get_price_history` (IBKR, NQ
   front month, `outside_rth=true`) for the NQ close.
4. Run `scripts/nq_daily.py`, commit the report.

Front month rolls: NQ front is currently NQU6 (Sep 18). Re-run
`search_futures` after each roll — the ladder is not returned in expiry
order, so sort by `contract_month` and take the earliest non-expired.

## Engine validation

The level curve needs gamma at *hypothetical* spots, so it is rebuilt with
Black-Scholes from each contract's own implied vol rather than using the
vendor's per-contract gamma (which is only valid at the current spot).
Checked against AV's own gamma across 289 near-money QQQ contracts:
**median relative error 0.31%, mean 0.37%, p90 0.66%**. The vendor smile is
preserved; the reconstruction is not a material source of error.

## Two calibration caveats for index gamma

These are real analytical limits, not implementation gaps:

- **The COTMP cushion filter loses its teeth on an index.** Index put open
  interest sits far out of the money (crash hedging), so the center of put
  mass lands ~11% below spot on QQQ versus ~1–5% on the single stocks run
  in July. The 2.0% floor is therefore passed almost automatically and
  stops discriminating. Don't read a passing cushion on NQ as the same
  quality signal it carries on a single name.
- **NQ open interest is fragmented across expiries.** NQ lists dailies,
  weeklies, monthlies and quarterlies; the Aug 31 monthly carried only
  86/28 contracts at strikes where the quarterly holds the real
  positioning. A single-expiry read can badly understate the true gamma
  profile — for NQ specifically, prefer the quarterly (trading class `NQ`)
  or aggregate several expiries. The QQQ proxy path does not have this
  problem, since QQQ monthly OI is deep (633k calls / 752k puts on Aug 21).

## Scheduling

Not yet scheduled. A Routine can fire this on a weekday evening cadence,
but the MCP calls in steps 1–3 are agent-side, so the scheduled unit has to
be a session that makes the calls and then runs the script — not a bare
cron'd Python process. Say the word and I'll set it up.
