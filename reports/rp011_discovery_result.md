# RP-011 Stage 1 — Databento discovery: REJECTED

Protocol: `reports/rp011_stage1_preregistration.md` (`cba8a50`) with Amendment 1
(`fc2ca9f`, decision P6). Harness `scripts/databento/rp011_db.py`; raw output
`reports/rp011_discovery_output.txt`. **Sessions already read by step-4 tape
studies.** The holdout was not loaded.

## Gate and counts

- Platform tests pass. Quality gate with the amended volume check: **56 of 65**
  sessions pass (50 required). 10 warm-up, **46 labelled**.
- Retained events: 499 (10.8 per session). **Counts gate: all eight conditions
  pass** — every block has both states; max block share 31.3% (midday); cap binds
  on at most 30.4% of sessions in a cell; morning, midday and closing each have both
  states in ≥ 39 sessions; no cell dominated by fewer than five sessions.

## Outcomes, 15 minutes, NQ points (direction-adjusted)

| block | INITIATIVE | ABSORPTION | D (paired by session) | t | Holm p | pass conditions |
|---|---|---|---|---|---|---|
| opening | −9.59 (n 31) | +11.67 (n 35) | +5.19 | +0.21 | 1.00 | 1 of 11 |
| morning | −2.50 (n 61) | −5.50 (n 70) | +7.89 | +0.89 | 0.77 | 2 of 11 |
| midday | +3.12 (n 76) | +5.17 (n 80) | −5.51 | −0.89 | 1.00 | 1 of 11 |
| closing | +5.07 (n 72) | +3.98 (n 74) | −1.55 | −0.38 | 1.00 | 2 of 11 |

**Kill conditions firing in every block:** K4 (only one side works), K5 (the best
three sessions carry the result), K6 (matched random times match the treatment),
K9 (controls reproduce the treatment), K10 (the two states are not opposite in
the mechanism's direction).

> **Verdict: RP-011 is rejected** (the pre-registered rule: any kill condition
> firing in every block). No block passes discovery, so **the holdout is not
> read** for RP-011. The block-relative construction fixed RP-010's sampling
> defect — every block and state is populated — and the mechanism still does not
> appear: absorption does not reverse, initiative does not continue, and matched
> random times do as well.
