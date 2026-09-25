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

---

## Amendment 1 — accepted by the user (decision P6), declared before any RP-011 window is built

**Data label.** The discovery sessions are **"sessions already read by step-4 tape
studies"** (T01–T17 read forward returns on them; see P6 addendum). Discovery is
therefore weaker evidence than registered; the D2 holdout is read **once**, and
only for a block that passes discovery.

**Volume check (gate criterion 9), amended.** One-sided: the tick feed's session
volume must not exceed CME cleared volume (no invented prints) and may fall short
of it by **at most 5%**. Every other gate criterion is unchanged.

**Counts gate, operationalised (the eight pre-outcome conditions in
`rp011_spec.py` — the five base conditions plus the three fresh-data additions —
all must hold):**
1. all four blocks produce both INITIATIVE and ABSORPTION candidates;
2. no block is structurally empty of retained events;
3. no block contributes more than 40% of retained events;
4. buy and sell events both exist in every cell with ≥ 5 sessions;
5. the cap binds on ≤ 50% of sessions within every cell;
6. at least three blocks have both states retained in ≥ 30 independent sessions;
7. genuine closing representation: the closing block is one of those blocks;
8. no cell is dominated by few sessions: every non-empty cell has ≥ 5 sessions,
   and its top four sessions supply ≤ 50% of its events.

**Outcome decision, operationalised (primary horizon 15 minutes, `r900`, NQ points,
direction-adjusted by the event window's delta sign; per block):**

- **Primary statistic D** = session-clustered mean of (INITIATIVE `r900`) minus
  (ABSORPTION `r900`), using per-session state means over sessions with both
  states; one-sided p that D > 0 (the mechanism: initiative continues, absorption
  reverses); **Holm across the four blocks**.
- **Pass conditions (all eleven):** (1) D's clustered t ≥ 2; (2) INITIATIVE mean
  `r900` > 0 and its 300 s continuation rate > 50%; (3) ABSORPTION mean `r900` < 0;
  (4) buy and sell both have the right sign in both states; (5) impact is
  load-bearing: INITIATIVE mean above, and ABSORPTION mean below, the top-decile
  selectors of |delta|, |progress|, volume, local volatility and impact alone (same
  block); (6) matched random times (same session and block, ±15 min, |delta| within
  25%) are materially weaker: their mean is less than half the treatment's in the
  mechanism's direction, for both states; (7) = (1), clustered t ≥ 2; (8) D > 0
  after removing the three sessions with the largest contribution; (9) D > 0 in at
  least 60% of the ISO weeks with both states; (10) both states clear 2.0 points
  with ≥ 1.0 point to spare (continuation `r900` for INITIATIVE, fade `−r900` for
  ABSORPTION); (11) retained events ≥ 12 per month in the block (4 per month after
  one-third retention).
- **Kill conditions (RP-010's ten), each evaluated per block:** K1–K3 |delta|,
  |progress| or volume alone reaches ≥ 80% of the INITIATIVE mean (or of |D|);
  K4 only one side works (buy and sell opposite in sign in either state); K5 the
  best three sessions supply > 50% of D; K6 matched random times match or exceed
  the treatment; K7 aggressor checks fail; K8 the better state does not clear 2.0
  points; K9 controls 2, 3 or 4 match or exceed the treatment; K10 INITIATIVE and
  ABSORPTION are not opposite (INITIATIVE > 0 and ABSORPTION < 0 required).
- **Decision:** a block supports the mechanism if all eleven pass conditions hold
  **and** its Holm p ≤ 0.05; RP-011 passes discovery if at least one block does
  (then that block, and only it, is read once on the holdout). RP-011 is
  **rejected** if any single kill condition fires in every block. Otherwise
  **unclear — stop**.

**T18 (RP-010, frozen)** runs after RP-011 on the same sessions, as a step-4
verdict-agreement rerun (outside BH).
