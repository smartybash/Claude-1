# RP-006B — corrected cross-sectional intraday momentum: re-registration

Supersedes the defective specification halted at `963cafd`
(`reports/rp006_stage1_halt.md`). **This document is written before the corrected
harness is executed.** One discovery run, on 2023 only, one verdict.

---

## 1. Contamination declared before anything else

The halt report §4 records that I have **seen a negative 2021–2022 output**:
long-strongest / short-weakest spread negative at every horizon, −8.57 bps at the
cash close, HIGH dispersion worse than ORDINARY. That output came from a
defective run (211 usable sessions, effectively 2022 only, two broken controls)
and is **not a result**. But it was seen.

Therefore, per the ruling:

| block | status |
|---|---|
| 2021-01-04 → 2022-12-31 | **CONTAMINATED. Not used in any performance calculation.** May appear only as a labelled invalid diagnostic. |
| 2023-01-01 → 2023-12-31 | **Discovery. Untouched. Opened by this run.** |
| 2024 | Internal validation. **Not read unless discovery passes.** |
| 2025 | Secondary validation. **Not read.** |
| 2026 / forward | Final out-of-sample. Newly acquired or forward only. |

### Warm-up declaration — the one place 2022 dates are touched

The design needs 20 prior completed sessions for the causal beta and 60 prior
sessions for the dispersion tercile reference. Those windows are drawn from
**2022-08-01 → 2022-12-30**.

They are **causal estimation inputs**, not observations:

* no 2022 session produces an observation row;
* no forward return is computed for any 2022 date;
* no 2022 session enters any mean, t-statistic, control or cost figure.

Without this the first ~80 sessions of 2023 would be consumed by warm-up and a
third of the discovery block would be lost. The alternative — warming up inside
2023 — would spend discovery data on estimation, which is worse. **This is
declared before the run, not after.**

Prior directional knowledge of the 2022 block does not transmit to 2023 through
a beta estimate or a dispersion percentile; it would transmit through a
specification choice, and no specification choice below has been changed except
the four corrections named in §3, all of which were written down in the halt
report **before** 2023 was opened.

---

## 2. What is unchanged from RP-006

Frozen, and **not** re-opened: factor (SPY, excluded from the ranked universe),
ranked universe (QQQ, IWM, IJH), EFA excluded completely, XLK excluded, causal
no-intercept rolling beta on 20 prior completed sessions, formation window
09:30 → 10:00, beta-neutral residual as the ranking variable, dispersion terciles
on a 60-session trailing reference, horizons 30 / 60 / 120 minutes and the cash
close, cost model 1 tick + $0.0035/share each way.

No alternative formation window, beta lookback, factor, dispersion boundary or
instrument universe is tested in this run.

---

## 3. The four corrections, restated

| # | defective | corrected |
|---|---|---|
| 1 | ≥380 aligned bars across all four instruments | **Six measurement timestamps present for all four** (09:30, 10:00, 10:30, 11:00, 12:00, last bar) **+ ≥300 bars pairwise against SPY + a fresh 10:00 print.** No four-way 380-bar intersection. |
| 2 | rank domination flagged at >60% | **Deviation from the 66.7% structural baseline; flag at >80% or <53%.** A diagnostic, not an automatic kill. |
| 3 | shuffled control permuted outcome columns | **Permutes the complete (strongest, weakest) identity across dates**, applied to each date's own forward returns. |
| 4 | random pair counted only on coincidence | **Computed for the drawn pair on every date.** |

Both randomised controls run **200 repetitions** and are reported as
distributions (mean, sd, p5, p95), not as a single draw.

A note on correction 1: the 10:00 freshness test is `close(10:00) ≠ close(09:59)`.
**09:30 is presence-only** — it is the session's first bar, so staleness is
undefined there and a freshness test would be meaningless rather than lenient.

### IJH split — verified before the run

The five-for-one split is confirmed in the stored series at **2024-02-22**
(280.84 → 56.99). **The whole of 2023 sits on the pre-split basis with no
discontinuity**, so no adjustment applies to this run, and the ~$260 price level
used in the cost calculation is the price IJH actually traded at in 2023. The
adjustment is required **before 2024 is opened** and must be verified then.

---

## 4. Cost hurdle, stated before results

Round trip per share = 1 tick ($0.01) + $0.0035 each way = **$0.017**. In basis
points this is `1e4 × 0.017 / P`, computed **per realised pair on the day**, both
legs:

| pair | approximate 2023 prices | two-leg round trip | 3× hurdle |
|---|---|---|---|
| IWM / IJH | ~$185 / ~$260 | ~1.57 bps | **~4.7 bps** |
| QQQ / IWM | ~$350 / ~$185 | ~1.41 bps | **~4.2 bps** |
| QQQ / IJH | ~$350 / ~$260 | ~1.14 bps | **~3.4 bps** |

The declared bar is **gross spread > 3 × the pair's own round-trip cost**, using
each date's realised prices rather than these approximations.

---

## 5. Discovery pass requirements — all nine must hold

1. Mean future spread is **positive** at one or more horizons.
2. That spread **exceeds 3× the realised pair-specific round-trip cost**.
3. Both legs contribute — the result is not one leg carrying the spread.
4. HIGH dispersion is **not worse** than ORDINARY.
5. True ranking beats the **random-pair** distribution (above its p95).
6. True ranking beats the **shuffled-identity** distribution (above its p95).
7. The reversed spread is materially weaker than the true spread.
8. **No single pair carries more than 60%** of total spread continuation.
9. **Realised frequency is at least four sessions per month.**

## 6. Kill conditions — any one closes the family

1. Mean future spread is **negative** at the majority of horizons (reversal).
2. Spread positive but **below** the 3× cost hurdle at every horizon.
3. One leg carries essentially all of it.
4. HIGH dispersion is **worse** than ORDINARY.
5. Random-pair or shuffled-identity distributions **contain** the true value.
6. Reversed spread is as strong as, or stronger than, the true spread.
7. A single pair carries **>60%** of continuation.
8. Realised frequency **below four per month**.
9. Discovery fails before validation is opened.

Rank domination is reported as a diagnostic. If QQQ exceeds 80% at either
extreme, the ex-QQQ-pair figure is reported **for information only** — the
universe is not redefined and that diagnostic is not promoted into another
strategy.

## 7. Reporting order

Eligibility funnel → rank balance → pair counts → realised frequency → future
spread by horizon → pair-specific cost and headroom → leg contributions → HIGH
versus ORDINARY → corrected controls → pair concentration → statistics appendix.

Counts before performance. Statistics confined to the appendix. **No P&L,
expectancy, profit factor, drawdown or pass probability.** The controls cannot be
promoted into strategies.

## 8. Verdict form

Exactly one of:

* Cross-sectional momentum **supported** — open 2024 validation;
* Cross-sectional momentum **unclear** — stop;
* Cross-sectional momentum **rejected** — close RP-006.

2024 and 2025 are not opened unless the preceding stage passes. **2021–2022 is
not re-run.**

---

## 9. Prior, stated before the run

Against. Three instruments give only three unordered pairs, which is a very thin
cross-section — the "cross-sectional momentum" literature rests on breadth that
this universe does not have. QQQ is the high-beta-residual name and the ranking
will frequently reduce to "QQQ versus one other", which is closer to a single
pair trade than to a cross-section. The halt report's §2 arithmetic already
predicts QQQ will sit at an extreme well above 66.7%.

**I expect this to fail, most likely on requirement 2 or requirement 8.** Stating
it here so that a marginal positive is not read as confirmation.
