# ORB + Fibonacci: the reversal cannot be resolved, and the continuation is not demonstrated

Pre-registered at `5612140`, amended at `c9196d1`
(`reports/orb_fibonacci_preregistration.md`) before the amended run.

**Continuation and reversal are reported separately and were never pooled at
any point.** They are corrected separately at α = 0.05/4 = 0.0125 each.

**Sealed NQ days were not read. 2016–2020 remains sealed** — this screen reads
only `QQQ_1m.parquet`, which begins 2021-01-04 and cannot reach it.

---

## 1. The answer you asked for first: the reversal family cannot be resolved

> *"State up front how many sessions produce a reversal setup. If it fires on
> fewer than 150 sessions the family cannot be resolved and I want to know that
> before results."*

| variant | reversal sessions | vs floor of 150 |
|---|---|---|
| ORB 09:30–09:45, band A | **39** | below |
| ORB 09:30–09:45, band B | **34** | below |
| ORB 09:30–10:00, band A | **17** | below |
| ORB 09:30–10:00, band B | **13** | below |

**Best variant: 39 sessions against a floor of 150.** The reversal family is
**unresolvable at this sample size.** Its expectancy is reported below as
descriptive only and is **not evidence in either direction**. This is an
absence of resolution, not a negative result.

The reason is structural: the reversal is a **seven-link chain inside a single
session** — break, outburst, Fib failure, structure shift, opposite outburst,
new Fib, retracement entry. The funnel shows where it goes:

| ORB 09:30–09:45, band A | sessions |
|---|---|
| ORB formed | 1,396 |
| broke a boundary | 1,395 |
| **outburst confirmed** | **126** |
| Fib failure | 81 |
| structure shift (close, not wick) | 52 |
| opposite outburst | 49 |
| **reversal entry taken** | **39** |

To reach 150 reversal sessions this rule would need roughly **5,400 sessions**,
or about 21 years of one instrument. It cannot be resolved on any sample this
project holds.

---

## 2. Counts before any performance number

1,396 sessions after sealing, 2021-01-04 .. 2026-08-31. **Entry lookahead: 0 on
every variant.** One trade per session per variant by construction, so trades =
sessions and there is no within-variant date clustering to correct.

| variant | outburst | CONT setup | CONT trades | REV trades |
|---|---|---|---|---|
| ORB15 band A | 126 | 112 | **112** | 39 |
| ORB15 band B | 126 | 101 | **101** | 34 |
| ORB30 band A | 82 | 76 | **76** | 17 |
| ORB30 band B | 82 | 65 | **65** | 13 |

### Minimum detectable effect, stated before expectancy

| variant | family | n | sd | **MDE** |
|---|---|---|---|---|
| ORB15 A | continuation | 112 | 1.230 | **+0.388** |
| ORB15 B | continuation | 101 | 1.877 | **+0.624** |
| ORB30 A | continuation | 76 | 1.135 | **+0.435** |
| ORB30 B | continuation | 65 | 1.121 | **+0.464** |
| ORB15 A | reversal | 39 | 0.997 | +0.533 (below floor) |
| ORB30 B | reversal | 13 | 1.000 | +0.926 (below floor) |

**Hold on to these.** The largest continuation effect observed below is
**+0.207 R**, against an MDE of **+0.435**. The study is underpowered by a
factor of two to four against its own results.

---

## 3. Amendment 1 — the literal 50% rule was degenerate, and I fixed it on counts

Implemented exactly as written — *retracement ≥ 50% of the run from origin to
the running extreme* — the rule killed **99% of outburst attempts within 3 bars
of the break, median 1 bar**. At the break bar the leg is a few cents wide, so
the next bar's ordinary range retraces more than half of it mechanically. The
rule was measuring a percentage of noise.

| variant | outbursts, literal | outbursts, amended | CONT trades lit → amd | REV trades lit → amd |
|---|---|---|---|---|
| ORB15 A | 6 | 126 | 6 → 112 | 2 → 39 |
| ORB15 B | 6 | 126 | 6 → 101 | 1 → 34 |
| ORB30 A | 11 | 82 | 11 → 76 | 2 → 17 |
| ORB30 B | 11 | 82 | 10 → 65 | 1 → 13 |

**The amendment measures the 50% retracement against the required leg length,
`X × ORB height`, instead of the run-so-far.** It is parameter-free — X and the
ORB height were both already declared — and it preserves the source's intent:
the impulse must not give back half the move it is making.

**It was made on counts alone. No expectancy number had been displayed when the
amendment was written and committed.** That is what the counts-first rule is
for. Had I not looked, the family would have "failed" on 6 trades for reasons
that belonged entirely to my implementation.

---

## 4. Continuation — 2 of 4 pass the screen, and that is not the same as a result

| variant | n | expR | t | PF | win% | RR | **RW%** | **GAP** | yrs+ | ex-top1% | +50% cost | naive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ORB15 A** | 112 | **+0.1154** | +0.99 | 1.23 | 44.6 | 1.52 | 39.6 | **+5.0** | 5/6 | +9.0 | +0.1044 | +0.0903 |
| ORB15 B | 101 | −0.1335 | −0.71 | 0.81 | 37.6 | 1.35 | 42.6 | −5.0 | 2/6 | −17.5 | −0.1465 | −0.0096 |
| **ORB30 A** | 76 | **+0.2071** | +1.59 | 1.53 | 50.0 | 1.53 | 39.6 | **+10.4** | 5/6 | +13.8 | +0.1948 | +0.1220 |
| ORB30 B | 65 | +0.0982 | +0.71 | 1.22 | 46.2 | 1.42 | 41.2 | +4.9 | 3/6 | +4.4 | +0.0838 | +0.0137 |

| variant | expR>0 | PF>1.15 | 4/6 yrs | ex-top1% | +50% cost | beats RW | |
|---|---|---|---|---|---|---|---|
| ORB15 A | PASS | PASS | PASS | PASS | PASS | PASS | **5/5 + RW** |
| ORB15 B | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | rejected |
| ORB30 A | PASS | PASS | PASS | PASS | PASS | PASS | **5/5 + RW** |
| ORB30 B | PASS | PASS | FAIL | PASS | PASS | PASS | rejected |

**Honest fills cost real money here** — the naive figure is +0.0903 vs +0.1154
honest on ORB15 A, and +0.1220 vs +0.2071 on ORB30 A. Ambiguous bars 0.0–3.1%.
Lookahead zero.

### Why "passes the screen" is not "demonstrated"

**The rejection rules are a filter, not a significance test, and they were never
claimed to be one.** Against the statistics:

- **t = +0.99 and +1.59.** Neither clears an *uncorrected* two-sided 5%
  threshold of 1.96, let alone the pre-registered Bonferroni z of **2.498**.
- **Both effects sit well below their own pre-declared MDE** (+0.115 vs +0.388;
  +0.207 vs +0.435). The screen cannot see an effect this size, so passing it
  carries little information.
- **The median trade is negative on three of four variants**, including ORB15 A
  at −0.351. The mean is positive because of the right tail, not the centre.

### Diagnostic 1 — how much of this rests on a handful of trades

| variant | n | mean | median | top 3 as % of total | drop best 5 | **drop best 10** |
|---|---|---|---|---|---|---|
| ORB15 A | 112 | +0.1154 | −0.3513 | **46%** | +0.0281 | **−0.0675** |
| ORB15 B | 101 | −0.1335 | −1.0111 | — | −0.2438 | −0.3657 |
| ORB30 A | 76 | +0.2071 | +0.0412 | **38%** | +0.0819 | **−0.0616** |
| ORB30 B | 65 | +0.0982 | −0.3224 | **93%** | −0.0582 | −0.2348 |

**Three trades carry 38–46% of the total. Remove the best ten and all four
variants are negative.** The pre-registered "remove the best 1%" test removes
one or two trades at n ≈ 100 and is simply too weak a test at this sample size
— it passed, and it should not be read as having shown much. The deeper
removals are diagnostics, not rejection rules, and reject nothing; they show
where the result lives.

### Diagnostic 2 — there are not four independent tests here

Session overlap between continuation variants:

| | ORB15/A | ORB15/B | ORB30/A | ORB30/B |
|---|---|---|---|---|
| **ORB15/A** | 1.00 | **0.90** | 0.13 | 0.13 |
| **ORB15/B** | 0.90 | 1.00 | 0.12 | 0.13 |
| **ORB30/A** | 0.13 | 0.12 | 1.00 | **0.86** |
| **ORB30/B** | 0.13 | 0.13 | 0.86 | 1.00 |

**Bands A and B are the same trades with different entry and stop geometry** —
they share 86–90% of sessions. The four variants are really **two samples
(one per ORB window) seen through two geometries**, and the two ORB windows are
close to independent of each other at 13% overlap.

That cuts both ways, and both should be said:

- **Against:** band A "beating" band B is not two setups competing. It is one
  set of sessions priced two ways, and A wins because its shallower 0.382 entry
  buys a larger risk denominator — geometry, exactly as flagged in §2 of the
  pre-registration.
- **For:** ORB15/A and ORB30/A share only 13% of sessions and are both
  positive (+0.115, +0.207). Two near-independent samples pointing the same way
  is the one genuinely encouraging thing in this run. It is also entirely
  consistent with noise at these sample sizes, which is the point of the MDE.

---

## 5. Reversal — descriptive only, below the floor, reported for completeness

| variant | n | expR | t | PF | win% | RR | RW% | GAP | |
|---|---|---|---|---|---|---|---|---|---|
| ORB15 A | 39 | −0.0584 | −0.37 | 0.87 | 38.5 | 1.40 | 41.7 | −3.3 | below floor |
| ORB15 B | 34 | +0.0382 | +0.20 | 1.08 | 41.2 | 1.55 | 39.2 | +2.0 | below floor |
| ORB30 A | 17 | −0.1274 | −0.59 | 0.71 | 41.2 | 1.02 | 49.6 | −8.4 | below floor |
| ORB30 B | 13 | −0.0571 | −0.21 | 0.87 | 30.8 | 1.96 | 33.8 | −3.0 | below floor |

**0 of 4 pass the rejection rules.** No weight should be placed on that. At
n = 13–39 with MDE +0.53 to +0.93, these numbers would look like this whether
the reversal works or not.

---

## 6. The claim, against the right benchmark

**Claimed: 59.13% at 1.43 RR.** A driftless walk at 1.43 RR gives
`1/2.43 = 41.15%`. **The claimed gap is +17.98 points.**

| family | variant | win% | realised RR | RW% | **gap** |
|---|---|---|---|---|---|
| continuation | ORB15 A | 44.6 | 1.52 | 39.6 | **+5.0** |
| continuation | ORB15 B | 37.6 | 1.35 | 42.6 | −5.0 |
| continuation | **ORB30 A** | 50.0 | 1.53 | 39.6 | **+10.4** |
| continuation | ORB30 B | 46.2 | 1.42 | 41.2 | +4.9 |
| reversal | ORB15 A | 38.5 | 1.40 | 41.7 | −3.3 |
| reversal | ORB15 B | 41.2 | 1.55 | 39.2 | +2.0 |
| reversal | ORB30 A | 41.2 | 1.02 | 49.6 | −8.4 |
| reversal | ORB30 B | 30.8 | 1.96 | 33.8 | −3.0 |

**The claimed +17.98-point gap is not reproduced anywhere.** The best variant
in the whole grid reaches **+10.4**, on 76 trades, at t = +1.59. Realised
reward-to-risk came in at 1.02–1.96 against the claimed 1.43, so the benchmark
comparison is on fair ground.

Note what the right benchmark does to the headline: **a 50.0% win rate sounds
like a coin flip and is not.** At 1.53 realised RR a coin gives 39.6%, so 50.0%
is +10.4 points of genuine edge *if it is real*. Measured against 50% — the
wrong benchmark — this variant would have looked like nothing. That is the
whole reason for the rule, and it works in the strategy's favour here.

---

## 7. What this family is and is not

**It is not demonstrated.** Nothing clears the pre-registered significance bar,
the two passing variants sit below their own MDE, the medians are negative, and
removing ten trades turns every variant negative.

**It is not refuted either.** Two near-independent ORB windows both point
positive with band A, the gaps against the random-walk rate are positive on
three of four continuation variants, and the sample is far too small to
distinguish +0.12 R from zero. Calling this a null would overstate what 112
trades can say.

**The reversal half is simply unresolvable** and will stay that way on any data
this project can reach.

### Recommendation

**Do not promote this to the holdout, and do not spend 2016–2020 on it.**

The arithmetic is the same as the last family and is if anything more decisive.
At the observed effect of +0.207 R with sd 1.135, and a continuation trade rate
of 76/1,396 ≈ 5.4%, the 1,259 sealed sessions would yield roughly **68 trades**
— *fewer than the discovery sample*. One-sided at α = 0.05 that gives an MDE of
about **+0.34 R**, against an observed effect of +0.207. The holdout would be
**underpowered against this candidate's own point estimate**, and would return
an uninformative null while consuming the only clean sample left.

**The honest next step, if this family is worth pursuing, is more instruments
rather than the holdout** — the same move that resolved the IB family, and one
that costs nothing sealed. SPY, IWM, IJH and EFA are already on disk at
5-minute resolution from the previous family; 1-minute would need fetching.
Four instruments at ~76 trades each would roughly triple the sample and bring
the MDE under the observed effect for the first time. That is a proposal, not
something I have run.

---

## 8. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| regime forecastability, gamma | 336 sessions, 4 combinations | closed, 0 of 4 |
| levels, predictive | 1,414 + 336 sessions, 13 tests | closed, 0 of 13 |
| setup grading | 13,840 trades, 6 sets | closed, worse than random |
| calendar classification | 1,418 sessions, 52 tests | closed, 1 of 52 |
| FOMC family | 48 dates, 20 tests | decisive pass, post/pre rv 3.14× |
| IB by rejection | 1,418 sessions | 86% is the geometric identity |
| related-instrument check | 5 instruments, 2,983 trades | closed, pooled +0.0269, CI spans zero |
| **ORB + Fib, continuation** | **1,396 sessions, 4 variants** | **not resolved — 2 of 4 pass the screen at t ≤ 1.59, below MDE** |
| **ORB + Fib, reversal** | **1,396 sessions, 13–39 setups** | **UNRESOLVABLE — below the 150-session floor** |

**2016–2020 remains unread and unspent.**

Reproduce: `python3 scripts/orderflow/orb_fib_study.py`.
Full output in `reports/orb_fib_output.txt`; per-trade detail in
`reports/orb_fib_continuation_trades.csv` and `reports/orb_fib_reversal_trades.csv`.
