# Studies (c) and (d) — pre-registration

Registered **before either rule is run on any data**. Data roles:
`reports/databento_register.md` §7. The block 2010-06 → 2020-12 is **decisive**,
labelled *"never used for this hypothesis; read by other studies, incl. study
(b)"*. 2021 → registration is reported as seen and is not decisive. Forward data
after registration is the only true out-of-sample. **Nothing is promoted on
backtest alone.**

**Common to both:** Databento NQ (and for (c) ES) `ohlcv-1m`, UTC → ET. Returns
within one contract; half days and sessions with an RTH roll excluded. Entry at
the next bar's open; stops at the stop or the bar's open if it gaps through;
targets at the target; stop first within a bar; the entry bar is searched for
exits. Costs per side: NQ/ES $2.25 + 1 tick, MNQ/MES $0.62 + 1 tick.
**Harness:** no fitted parameter (all fixed below), so an anchored walk-forward
refits nothing and is replaced by a per-year table. **Null:** random-direction
entries at the same times with the same stop/target geometry, 5,000 simulations.
**Kill criteria**, decisive block: Sharpe ≥ 0.8, profit factor ≥ 1.3, beats the
null at Holm-adjusted p ≤ 0.05. Metrics: Sharpe, CAGR, max drawdown $ per NQ and
per MNQ (ES/MES), trade count, profit factor.

---

## (c) Intraday momentum — noise boundaries (Zarattini, Aziz & Barbon 2024)

Source rule: *"Beat the Market: An Effective Intraday Momentum Strategy for
S&P500 ETF (SPY)"*. Parameters as published; not fitted.

- **σ(t):** for each minute t after the RTH open, the mean over the **prior 14
  sessions** of |close(t) ÷ RTH open − 1|.
- **Bands with the paper's gap adjustment:** UB(t) = max(Open_d, Close_{d−1}) ×
  (1 + σ(t)); LB(t) = min(Open_d, Close_{d−1}) × (1 − σ(t)). Close_{d−1} is the prior
  RTH close; if the contract changed overnight, Open_d is used for both.
- **Decision marks:** every half hour, 10:00 → 15:30 ET, on the close of the bar
  ending at the mark; execution at the next bar's open.
- **Logic at each mark:** flat → long if close > UB, short if close < LB. Long →
  exit if close < max(UB, VWAP), then short if close < LB. Short → exit if close >
  min(LB, VWAP), then long if close > UB.
- **VWAP:** RTH session VWAP from 1-minute bars (typical price × volume).
- **Flat at the close** (15:59 bar close). **Sizing:** one contract (the paper's
  volatility targeting is not used, so per-contract metrics are comparable).
- **Instruments:** **ES** (the faithful replication; the paper trades SPY) and
  **NQ**. Holm across the two.

## (d) Liquidity sweep — fade back into the range

- **Levels:** PDH and PDL (the prior RTH session's high and low, same contract);
  ONH and ONL (the Globex overnight high and low, 18:00 prior day → 09:29 ET,
  same contract).
- **Sweep (high level):** the first 1-minute bar starting 09:30–14:59 whose high
  is ≥ level + 1 tick while the previous bar's close was below the level. Lows
  mirrored.
- **Reclaim:** a 1-minute close back below the level (above, for lows) **within 5
  bars** of the sweep bar, counting the sweep bar.
- **Entry:** next bar's open, **fading** the sweep (short after a high sweep).
  **Stop:** the sweep extreme (highest high from the sweep bar to the reclaim bar)
  + 1 tick. **Target:** 2R. Otherwise flat at 15:59.
- Skipped if the entry open is at or beyond the stop. **One trade per level per
  day**, one position at a time. **NQ only.**
- **Prior, declared:** this repository closed a close cousin (`9fb43f9`, prior-day
  high/low sweep-and-reclaim on QQQ 5-minute bars, −0.19R, 523 sessions).
