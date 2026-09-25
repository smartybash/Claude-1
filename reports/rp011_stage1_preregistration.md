# RP-011 Stage 1 — pre-registration on Databento ticks

Registered **before any RP-011 window is built from Databento data**. The frozen
construction is unchanged (`reports/rp011_frozen_spec.md`, `scripts/orderflow/rp011_spec.py`),
and so is the counts gate. The D3 waiver and the session exclusions follow
`reports/databento_register.md` §§3 and 8. **The Stage 1 outcome protocol below is
RP-010's approved Stage 1 structure, applied per time block.** Adopting it is
logged in `decisions_pending.md` (P5) for your review.

## Data

- Databento NQ `trades`, **discovery only**: 2026-03-02 → 05-29, **61 sessions**
  after the registered exclusions. RTH only.
- Side B → buy aggressor, A → sell aggressor (confirmed against ATAS, 99.99%
  footprint agreement).
- The 30-second windows use Databento's price-level prints. Every RP-011 state is
  **volume-based** (imbalance; ticks per 1,000 contracts), so print granularity —
  ATAS fills versus Databento level aggregates — does not change any state.
- **The holdout (23 sessions) is read once, at the very end**, together with every
  other tick hypothesis.

## Order of work

1. `test_platform.py`: every test must pass; the count is reported.
2. **Quality gate per session**, with the D3 integrity check replacing the ATAS
   status file:
   - measured 0.25 grid
   - full cash session
   - zero RTH side-N prints
   - monotonic timestamps
   - no duplicate dates
   - no prior research use
   - RTH coverage 09:30–15:59
   - no RTH gap between trades longer than 60 s
   - session volume reconciled to the statistics schema, **tolerance ±2%**
3. **≥ 50 sessions must pass.** Otherwise stop.
4. **Construction and counts gate** (all seven conditions) before any forward
   return. If the gate fails, stop and return RP-011 for redesign; nothing is amended.
5. Stage 1 outcomes, controls and decision below.

## Outcomes (strictly after the event window), per block × state

Horizons 30 s, 1, 3, 5, 10 and 15 minutes. For each: direction-adjusted return in
NQ points and ticks, median, MFE, MAE, continuation and reversal frequency, time to
± one typical 30-second move, return to origin, break of the event extreme. Buy and
sell events are reported separately, and results are shown by week and by session.

## Controls (RP-010's, per block)

Impact labels shuffled within the aggression set; same price progress without
unusual aggression; matched random times (same session, same block, ±15 minutes,
|delta| within 25%); high volume with balanced delta; opposite direction.
**Load-bearing test:** top decile of delta alone, progress alone, volume alone,
local volatility alone and impact alone, against both states.

## Decision (fixed now)

- **A block supports the mechanism** only if all eleven RP-010 pass conditions hold
  in that block:
  1. initiative and absorption produce different paths
  2. initiative continues
  3. absorption fails or reverses
  4. buy and sell both point correctly
  5. impact is load-bearing
  6. matched controls are materially weaker
  7. the result survives session clustering
  8. it survives removing the best three sessions
  9. it appears across multiple weeks
  10. it clears 2-point costs with headroom
  11. frequency is at least 4 per month
- **Primary horizon: 15 minutes.** Session-clustered t, **Holm across the four
  blocks**.
- **RP-011 passes discovery** if at least one block supports the mechanism at Holm
  p ≤ 0.05. A pass is then **confirmed or refuted on the holdout, read once**, for
  the same block only.
- **RP-011 is rejected** if any RP-010 kill condition fires in every block.
- Otherwise: **unclear, stop.**
- No entry, stop, target or strategy is defined in Stage 1.
