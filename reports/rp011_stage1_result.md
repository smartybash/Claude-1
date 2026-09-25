# RP-011 Stage 1 — stopped at the quality gate

Protocol: `reports/rp011_stage1_preregistration.md` (`cba8a50`). Gate script:
`scripts/databento/rp011_integrity.py`, committed before its first run (`2611516`;
the only later edit is a one-line timestamp-type fix, with no criterion changed).
Per-session table: `reports/rp011_quality_gate.csv`; raw output
`reports/rp011_quality_gate_output.txt`.

**No RP-011 window, state, count or forward return was built or read.**

## Result

| | sessions |
|---|---|
| discovery window 2026-03-02 → 05-29 | 65 |
| pass every criterion except volume | 60 |
| **pass every criterion** | **27** |
| required | 50 |

> **Gate FAILED: 27 < 50. RP-011 Stage 1 stops, as registered.** Nothing is amended.

| criterion | fails | sessions |
|---|---|---|
| grid, monotonic timestamps, duplicate dates, prior use | 0 | — |
| full cash session / coverage | 2 | 04-03 (Good Friday), 05-25 (holiday, 12:59 close) |
| roll lag (registered exclusion) | 2 | 03-16, 03-17 |
| RTH side-N print | 1 | 04-21 (one print) |
| RTH gap > 60 s | 1 | 04-03 |
| **volume within ±2% of CME cleared volume** | **36** | |

## Why the volume check fails

Tick-feed session volume divided by CME `CLEARED_VOLUME` (statistics, pull C), minus 1,
over the 60 sessions that pass every other criterion:

| min | p10 | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|
| −12.7% | −3.4% | −2.7% | −2.1% | −1.7% | −1.4% | −1.0% |

- **The shortfall is one-sided.** In no session does the trade feed exceed cleared
  volume, so there are no duplicated or invented prints.
- It is **steady at 1–3.5% in ordinary weeks and widens in roll weeks**, down to
  −11% to −13% on 03-13 and 03-18. That is where calendar-spread volume peaks.
- **Good Friday (04-03), a session with no spread or block activity, reconciles
  to −0.01%.**
- **The ATAS recordings match Databento to within 0.01%** on all five cross-check
  sessions (`databento_data_quality.md`). The ±2% test against cleared volume would
  therefore have failed RP-011's original ATAS data in the same way.

Reading: CME cleared volume includes block trades, spread-leg and other off-book
volume that is not in the outright trades feed. Pull B did not buy the spread
instruments, so that volume cannot be subtracted. The ±2% two-sided tolerance was
set before pull C landed, without knowing this. The tick data looks sound on
every other test, but under the check as registered, RP-011 stops.

**Disclosure.** Before the gate script was written, an exploratory join of
committed session volumes to cleared volume was run, and a tolerance-sensitivity
count was run after the gate (±3% → 49 sessions, ±4% → 56, ±5% → 56). Both are
quality statistics, not RP-011 quantities, and are shown here so that any
amendment is judged knowing they were seen.

The decision on what happens next is yours: `decisions_pending.md` P6.
