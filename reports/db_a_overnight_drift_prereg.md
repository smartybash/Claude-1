# Study (a) — overnight drift overlay: pre-registration

Registered **before any Databento data is requested or read**. Data roles per
`reports/databento_register.md` §5.

## Hypothesis

Holding NQ (and, separately, ES) from the RTH close to the next RTH open earns a
return that is better, per unit of risk, **when the close is above its 200-day
SMA** than always holding overnight or buying and holding. Mechanism: the overnight
risk premium is compensation for bearing gap risk while the cash market is shut;
above a long trend filter that risk has been cheaper to bear than below it.

## Data

- Databento `GLBX.MDP3`, `ohlcv-1m`, `NQ.v.0` and `ES.v.0`, `stype_in=continuous`,
  2010-06-06 → latest. UTC → America/New_York with DST.
- **Unadjusted prices kept**, with `instrument_id`. Minutes with no trades have no
  bar; nothing is invented or forward-filled.
- **Ratio back-adjusted daily closes** are used **only** for the 200-day SMA. At each
  change of `instrument_id` the ratio is new-contract first-bar open ÷ old-contract
  last-bar close, and is valid only if those two bars are **≤ 5 minutes apart**
  (flagged otherwise). Every traded return is computed **within one contract**.

## Sessions and prices

- **RTH close** = close of the last bar before 16:00 ET. **RTH open** = open of the
  09:30 bar, or the first bar 09:30–09:34 if it is missing; otherwise that day is
  skipped in every arm.
- **Half days** (identified by `sessioncal.early_closes` on RTH bars): a night whose
  entry or exit session is a half day is skipped **in every arm**.
- **Roll nights:** a night is held only if `instrument_id` is the same at the entry
  close and at the exit open; otherwise it is skipped **in every arm**. No return is
  ever computed across a roll.

## Rule — one specification, no variants

- **Signal**, known before the fill: close of the **15:58 bar** above the 200-day SMA
  of the prior 200 back-adjusted RTH closes.
- **Entry:** long 1 contract at the 15:59 bar's close. **Exit:** the next RTH open.
- First signal after 200 sessions of warm-up (≈ March 2011).

## Comparison arms

1. **Always overnight:** every eligible night, same entry and exit.
2. **Buy and hold:** long throughout, P&L summed within contract as the overnight
   returns of non-roll nights plus every day's open→close return. One round trip is
   charged at each roll.

## Costs, applied to every side of every trade

| | commission / side | slippage / side |
|---|---|---|
| NQ | $2.25 | 1 tick = $5.00 |
| ES | $2.25 | 1 tick = $12.50 |
| MNQ | $0.62 | 1 tick = $0.50 |
| MES | $0.62 | 1 tick = $1.25 |

## Metrics

- Sharpe of daily $ P&L per contract (flat days = 0) × √252.
- CAGR on unlevered notional (contract notional at the start of each period).
- Max drawdown in $ per NQ **and** per MNQ contract (ES and MES likewise).
- Trade count and profit factor (gross winning nights ÷ gross losing nights).
- Adjusted p-values: **Holm** across the two primary tests (NQ overlay vs null,
  ES overlay vs null).

## Null — 5,000 simulations

Draw at random, from the same period's eligible nights, **the same number of nights
the overlay held**; apply identical costs; compute Sharpe. p = (1 + #null Sharpe ≥
observed) ÷ 5,001.

## Walk-forward

The rule has **no fitted parameter** (200 is fixed). An anchored walk-forward would
refit nothing, so it is replaced by a **per-year table**. Nothing is tuned.

## Periods

| block | label |
|---|---|
| first signal → 2020-12-31 | **never used for this hypothesis; read by other daily studies, incl. overnight gap base rates** |
| 2021-01-01 → registration date | seen (explored informally on QQQ); reported, not decisive |
| after the registration date | **the only true out-of-sample**, evaluated later |

## Kill criteria — on the 2010–2020 block, per instrument

The overlay is killed if **any** fails: Sharpe ≥ 0.8; profit factor ≥ 1.3; beats the
null at Holm-adjusted p ≤ 0.05; Sharpe ≥ buy-and-hold.

**Nothing is promoted on backtest alone.** Surviving means only that forward data is
worth collecting.
