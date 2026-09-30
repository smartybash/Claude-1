# Risk-managed rerun, Phase 2 — result

Registered `reports/risk_rerun_p2_preregistration.md` (b9c17bb). Reproduction gate
run first; then the risk block, once. Output: `reports/risk_rerun_p2_output.txt`.
Data: Databento tick prints, discovery sessions 2026-03 → 05 (seen).

## Correction to the Phase 1 count

**24 of the 31 earlier trading tests had stops; 7 did not**, not 13. Phase 1's
count came from a scan of inventory script paths. Four entries list two scripts
each, and those scored as "no stop" because the combined path does not exist as
one file. T04–T06 (stop/target) and B15, B17 and B19 (in R) always had stops.

## Reproduction gate: 41 of 41 cells reproduced exactly

Without the risk block, the rebuilt trades match the step-4 ports in every
cell: the same number of trades and the same gross points. T15 B1 and E2 are
absent in both, for the same reason (too few distinct values).

## Verdict: all seven studies stay closed

With a stop on every tick, $250 risk (at most 10 MNQ), one position at a time
and a $500 daily cap, **every one of the 41 cells loses money.**

| study | best cell with the risk block | $/trade | total | study Holm p |
|---|---|---|---|---|
| T01 absorption | sell_absorbed_long | −$32.1 | −$25,394 | 1.00 |
| T02 tape sweep (22 cells) | H3 look 15m hold 15m | −$2.0 | −$1,460 | 1.00 |
| T03 CVD divergence | divergence_dedup | −$28.6 | −$14,829 | 0.999 |
| T10 VWAP displacement | exit 13:00 (the other two exits: every trade too big for $250) | −$18.4 | −$1,122 | 1.00 |
| T13 footprint absorb_lo | hold 30m | −$34.0 | −$10,759 | 1.00 |
| T14 heavy levels | +30m | −$34.6 | −$7,229 | 1.00 |
| T15 batch features | E1 | −$5.3 | −$3,181 | 1.00 |

## Why a stop made them worse

- These entries had **about zero gross edge** without a stop: T01 −240 and
  +310 points over some 3,200 trades each, and T02's H1 cells negative.
- A stop can cut the size of losses, but it cannot create an edge that the
  entries don't have.
- Short holds (2–15 minutes) get small stops (about 10–20 NQ points). The $250
  risk rule then sizes up to about 9 micros, and at $4.00 per micro that is
  about **$35 of costs a trade**. Net ≈ −costs: T01 loses $35.2 a trade on 8.8
  micros.
- T10's 15:00 and 16:00 exits hold for 5–7 hours. A proper stop needs more than
  $250 per micro at 2026 prices, so every trade was skipped. That is the same
  finding as D3-G in Phase 1.

## Where the whole rerun leaves the programme

With proper risk management, every earlier study and every rule designed in
this programme is closed except two:
- **H1-B risk-managed**, forward-tracked, with a probable fit to 2020 flagged;
- **D3-G**, tracked only as a record, because it is not tradable at 50K prop
  size.

Nothing currently tested is a prop-ready edge.
