# RP-14 — regime-conditional intraday pre-registration: HALTED at section 1

The brief required each section to be complete before the next, and a stop —
not a placeholder — where a section cannot be completed from the information
available. **Section 1 (regime taxonomy) cannot be completed.** Sections 2–8
were not drafted.

## Why "learn the rules from history" is not a test

A test requires a hypothesis fixed before the data can influence it and an
outcome that could have gone against it. Searching history for the rule–regime
pairing that performed best has no fixed hypothesis: the same history both
chooses the rules and scores them, so a strong in-sample result is guaranteed by
construction — the search converts noise into fit. Its only honest reading is on
data it never saw, and none exists here. The 152-subset conditioning run is this
desk's own demonstration: the best real subset sat below the median of a random
search.

## Why section 1 cannot be completed

Every observable regime dimension available has already been tested for
direction or directness and closed:

| dimension | closed by | result |
|---|---|---|
| volatility (RV₆₀, VIX) | RP-008; pre-open conditioning | tercile adds +0.0014 R²; null |
| 14 price-derived session states | regime forecastability | 0 of 14 |
| trend vs chop (daily ADX and similar) | trend-regime study | unknowable the night before |
| dealer gamma | gamma study | 0 of 4 on regime |
| overnight state | RP-002 | separation circular |
| time of day | RP-009 | scale only |
| forced flow and expiry (month/quarter end, roll week, expiries) | calendar classification | flat on every statistic |
| conditioning existing trade sets | trade conditioning | best real subset at the null's 1st percentile |

Re-using any of them violates the brief's ban on re-entering closed families;
the volatility dimensions also fail "not a volatility proxy".

The one untested dimension with a distinct mechanism — **scheduled macro-release
days** — cannot be built: 48 FOMC dates are on disk (and the FOMC straddle
family has run), and CPI/NFP *release* dates have never been obtained. The
calendar study verified that the available APIs give reference months only and
declined to reconstruct dates from memory. Proposal B is blocked on the same
input.

## Decisions not specified by the brief

1. "Closed family" = a recorded null or rejection verdict — mechanism-driven.
2. Calendar classification closed for forced-flow/expiry but not for scheduled
   releases (never run) — mechanism-driven.
3. Release-day regime excluded for missing data, not for failure — required by
   the stop rule.
4. "Observable at the decision point" read strictly: a dated, verifiable label
   before the decision — mechanism-driven (anything weaker admits lookahead).

No convenience choices were made.

**Unblocked by:** a verified CSV of Fed/BLS release dates and times in `data/`.
