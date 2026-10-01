# Pre-registration: earnings direction drivers — holdout test

Written and committed **before** any holdout data was collected
(2026-10-01, after the training/test run on 8 stocks).

## Frozen model
`reports/earnings_model_v1_frozen.json` — trained on AAPL, JPM, META, MSFT,
MU, NKE, NVDA, TSLA reports before 2017-01-01. Drivers selected on training
(p < 0.10), both **contrarian**:

- `runup`: 10-session return into the report minus SPY's; > +2% → expect
  DOWN, < −2% → expect UP.
- `prior_reaction`: previous report's reaction-session return; > +1% →
  expect DOWN, < −1% → expect UP.

No parameter, sign, threshold or driver set may change before the holdout
evaluation.

## Hypotheses
- **H1 (primary):** when both drivers fire in the same direction
  (|score| = 2), the reaction goes the predicted way more often than the
  holdout's own base rate implies. One-sided α = 0.05.
- **H2 (secondary):** the same with at least one driver firing (|score| ≥ 1).

## Holdout
Stocks never used in training or model selection: AMD, INTC, NFLX, GOOGL,
QCOM, ORCL. All of their usable reports, every year. Dates come from Alpha
Vantage EARNINGS, transcribed exactly as for the training set.

## What counts as success
H1 confirmed → the alignment gate is used as a direction filter in live
cards. H1 not confirmed → the method reports **no validated directional
driver** and recommends no directional earnings position on direction
grounds.
