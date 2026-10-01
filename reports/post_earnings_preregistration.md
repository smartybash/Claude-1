# Pre-registration: trading AFTER the earnings reaction

Written and committed before any post-announcement statistic was computed
(2026-10-01). No parameter below may change after results are seen.

Universe: the 14 stocks in data/earnings/ and data/earnings_holdout/.
Reaction session = first session trading on the news (resolved by volume,
vol_desk/earnings_method.resolve_reactions). "Typical move" = mean
|reaction-session return| of the stock's previous 8 reports. All tests are
one-sided exact binomial tests against the sample's own base rate of the
predicted direction.

## A. Daily entries (all usable reports, 2000–2026)

Directions are fixed in advance (continuation, the documented
post-earnings-drift hypothesis), not learned from the data.

- **D2 (primary daily): drift after the first session.** Enter at the
  reaction-session close in the direction of the reaction-session return
  (gap plus day). Win if the next 5 sessions move the same way.
- **D1 (secondary): gap-and-go.** Enter at the reaction-session open in
  the direction of the overnight gap. Win if open → close moves the same way.
- **D3 (secondary): 20-session drift.** As D2, held 20 sessions.
- Each is also reported for the pre-specified subset of large reactions:
  |reaction| ≥ the stock's typical move.

## B. Intraday entry at 10:30 ET (first full RTH hour complete)

Sample: every report whose reaction session falls between 2024-01-01 and
2026-09-30, using Alpha Vantage 5-minute RTH bars. The 10:30 price is the
close of the 10:25 bar.

Fixed rule, no fitting:
- Gap G = reaction open / previous close − 1. Only events with
  |G| ≥ 0.5 × typical move qualify (a real reaction).
- First-hour return F = 10:30 price / open − 1. Position P = (10:30 price −
  first-hour low) / (first-hour high − first-hour low).
- **CONFIRM:** sign(F) = sign(G) and the price is in the gap-side 30% of the
  first-hour range (P ≥ 0.70 if G > 0, P ≤ 0.30 if G < 0). Predict
  continuation in G's direction.
- **REJECT:** sign(F) ≠ sign(G) and the price is in the opposite 30% of the
  range. Predict continuation against G (the fade).

- **I1 (primary intraday):** CONFIRM events move in G's direction from 10:30
  to the close more often than the base rate.
- **I2 (secondary):** REJECT events move against G from 10:30 to the close.
- For information only: 10:30 → close of the next session and of session
  +5, and move sizes in units of the typical move.

## Decision rule
A primary hypothesis (D2, I1) that is confirmed at one-sided α = 0.05 becomes
a validated post-announcement entry, eligible for the gate method in
reports/earnings_method.md. Unconfirmed hypotheses are reported, not used.
