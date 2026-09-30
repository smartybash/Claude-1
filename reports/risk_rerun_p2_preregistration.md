# Risk-managed rerun, Phase 2: the earlier fixed-exit tape studies — pre-registration

**Registered 2026-09-30, before any of these studies has been run with a stop.**
The user instructed "Run p2" (Phase 2 of `reports/risk_rerun_preregistration.md`).

## 0. Scope correction (found while reading the code)

Phase 1 said 13 earlier trading tests had no stop. **That count was wrong.** It
scanned the script paths listed in the inventory. Four of those entries name two
scripts ("levels.py + levels_audit.py"), and the scan scored those as having no
stop because the combined path doesn't exist as one file.

Reading the code that actually runs (the step-4 ports):
- **Stops are already in:** T04 (a stop/target grid), T05 and T06 (30-point
  stop and target), and B15, B17 and B19 (all in R units, from a stop).
- **Fixed exit time, no stop: T01, T02, T03, T10, T13, T14, T15.**

Corrected: **24 of the 31 earlier trading tests had stops; 7 did not.** Phase 2
covers those 7.

## 1. The seven studies (entries exactly as in the step-4 ports)

| study | entry | direction | planned exit |
|---|---|---|---|
| T01 absorption | close of a 30 s window with delta in the top/bottom 20% and ≤ 5 pt move | fade the delta | 4 windows later |
| T02 sweep (all registered cells) | H1: delta top 20%, flat; H2: block-print delta top 10% (go and fade); H3: new 15/30/60-minute extreme unconfirmed by CVD | per cell | 2–30 minutes, per cell |
| T03 CVD divergence (dedup) and its no-CVD control | as `divergence_audit.trades` | fade the extreme | 5 minutes |
| T10 VWAP displacement | first top/bottom-quintile minute of the day, +1 minute | fade | 13:00, 15:00 or 16:00 ET |
| T13 footprint absorb_lo | close of a 5-minute bar in the top quintile | short | 5, 15 or 30 minutes |
| T14 heavy footprint levels | first return to a heavy level, filled at the level | as price arrived | 15, 30 or 60 minutes |
| T15 batch features A1–E2 | close of a 5-minute bar in the top/bottom quintile of each feature | long top, short bottom | 15 minutes |

**Data:** the Databento tick prints of the discovery sessions (2026-03 → 05),
exactly as the step-4 ports used them. **Everything here is seen data.**

## 2. The risk block (Phase 1's, plus the rules that multi-trade days need)

1. **Stop:** 0.5 × ADR20 × √(planned hold ÷ 390), in points at the entry price.
   ADR20 comes from the prior 20 RTH days. The stop is checked on **every tick**
   after entry, and fills at the first print at or through it (a gap fills at
   that print).
2. **Size:** $250 risk per trade; MNQ = floor($250 ÷ (stop × $2)), capped at 10
   micros; skipped if under 1.
3. **One position at a time per rule (cell):** a signal while a position is
   open is skipped.
4. **Daily loss cap $500:** after the day's realised loss reaches $500, no more
   trades that day.
5. **Costs:** the stricter of the step-4 micro cost ($2.24) and the study's own
   frozen cost (2.0 points = $4.00 per micro). That gives **$4.00 per micro per
   round trip.**

## 3. Reproduction gate (before any risk result is read)

Without the risk block, the rebuilt trades must reproduce the step-4 port's
trades for every cell: the same number of trades and the same total gross
points (to 0.01 point per trade).

The gate runs **on its own first** (`--repro`), and prints no risk-managed
number. Bugs in the rebuild may be fixed until it matches the port. Matching is
an objective target that uses no result. Cells that still do not match are
reported as "not reproduced" and left out; they are never re-tuned.

## 4. Test

- **Statistic:** a one-sided t-test on daily net $ (zero days included), the
  step-4 rule (Clarification 3).
- **Holm within each study** across its registered cells, as in step 4.
- **Study pass:** best cell net > 0, Holm p ≤ 0.05, and the study's extra gates:
  - T03: the divergence cell must beat its no-CVD control, which is also run
    with the risk block;
  - T10: t ≥ 2.4 at each exit, recomputed;
  - T14: the paired and placebo gates, and T15: the IC gates. These do not use
    the exit and are carried over from step 4 unchanged.
- **Benjamini–Hochberg across the 7 studies** (q = 0.05), as step 4 did across
  trading claims.
- **Pass →** logged as a candidate. These rules need tick data, which the
  forward pulls do not buy, so a forward test would be a cost decision for the
  user. **Fail →** stays closed.
- **Descriptive:** trades taken and skipped (open position, daily cap, stop too
  wide), stop-out share, average micros, the largest loss, and the per-cell
  result without the risk block (the reproduction) next to the result with it.

Script: `scripts/databento/risk_rerun_p2.py`, committed with this file before any run.
