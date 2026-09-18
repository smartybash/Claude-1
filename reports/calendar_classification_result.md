# Calendar classification, Stage 1: the mechanism families show nothing

Pre-registered at `c147285`
(`reports/calendar_classification_preregistration.md`) before this ran.
**Descriptive only — no expectancy, no win rate, no verdict, no rule run.**

**2016–2020 remains sealed.** This script reads only `QQQ_1m.parquet`, which
begins 2021-01-04 and cannot reach it. Sealed NQ days were not read.

---

## 1. What could not be built

**The scheduled-events family (FOMC, day-after, CPI, NFP, no-release control) was
not run, because real release dates could not be obtained.** The repo has none;
FMP's `economics-calendar`, which carries true release dates, is **denied on this
plan tier**; Alpha Vantage's `CPI` and `NONFARM_PAYROLL` are keyed by **reference
month** (`2026-08-01`), not release date — verified, not assumed.

I did not derive them from memory. The NFP "first Friday" heuristic is wrong often
enough that a 10–15% mislabel rate would contaminate both the category and its
control, and fabricated dates would have produced a plausible-looking result,
which is worse than none.

**To unblock:** an FMP Starter subscription, or a CSV of Fed/BLS release dates
dropped into `data/`. Both publish their schedules a year ahead.

---

## 2. Counts and power, as declared

1,418 sessions, 2021-01-04 to 2026-08-31. 13 categories × 4 statistics = **52
tests**, Bonferroni **α = 0.000962**.

| category | n | ctrl | MDE rv | as % of mean | |
|---|---|---|---|---|---|
| last 3 of month | 204 | 1,214 | 15.8 | 16% | |
| last 3 of quarter | 69 | 1,349 | 25.7 | 26% | |
| first of month | 68 | 1,350 | 25.9 | 27% | |
| Monday–Friday | 264–294 | ~1,130 | 13.7–14.2 | **14–15%** | best resolution |
| futures roll week | 110 | 1,308 | 20.7 | 21% | |
| monthly expiry | 68 | 215 | 29.0 | 30% | |
| **quarterly expiry** | **22** | 215 | **46.7** | **48%** | **UNDERPOWERED** |
| pre-monthly expiry | 68 | 218 | 29.0 | 30% | |
| **pre-quarterly expiry** | **22** | 218 | **46.6** | **48%** | **UNDERPOWERED** |

---

## 3. Result

| | |
|---|---|
| tests clearing Bonferroni | **1 of 52** |
| tests beating the 95th pct of random labels | **6 of 52** |
| expected by chance at the 95th pct alone | **2.6 of 52** |

**Clearing both: one.** Wednesday, OR ratio, −0.0860, p = 8.22e-04, 99.8th
percentile of random, n = 292.

### The families carrying the mechanism showed nothing

The rationale for this whole direction was **obligation** — participants who must
trade. Those are the forced-flow and expiry families, and they are empty:

| category | best result | |
|---|---|---|
| last 3 of month | rv −2.9 bps, 55th pct of random | nothing |
| last 3 of quarter | rv −9.5 bps, 87th pct | doesn't clear |
| first of month | OR ratio +0.137, 99.1st pct | beats random, fails Bonferroni |
| futures roll week | rv +5.7 bps, 75th pct | nothing |
| monthly expiry | all four ≤ 55th pct | nothing |
| quarterly expiry | all four ≤ 53rd pct | nothing, and underpowered |
| pre-monthly expiry | all four ≤ 71st pct | nothing |
| pre-quarterly expiry | all four ≤ 53rd pct | nothing, and underpowered |

**Month-end, quarter-end, roll week and every expiry category are flat.** The
intraday split was built specifically so closing-auction rebalancing could not be
averaged away, and it was not: last-3-of-quarter puts 16.6% of volume in the final
30 minutes against 14.1% for all sessions — visible, but small and not significant.

### The only structure is day of week, which is the weakest mechanism in the set

| day | n | raw OR15 | OR ratio | rv | rv mid | vol% open30 |
|---|---|---|---|---|---|---|
| **Mon** | 264 | **55.9** | **1.075** | **91.3** | **76.7** | **16.0** |
| Tue | 294 | 50.9 | 0.975 | 92.5 | 78.6 | 15.0 |
| **Wed** | 292 | **49.8** | **0.946** | **102.0** | **88.1** | 14.4 |
| Thu | 285 | 54.6 | 1.046 | 100.5 | 86.0 | 15.1 |
| Fri | 283 | 54.6 | 1.036 | 101.1 | 86.5 | 14.7 |
| all | 1,418 | 53.1 | 1.014 | 97.6 | 83.3 | 15.0 |

**Monday front-loads and then goes quiet** — the widest opening range relative to
its own trailing norm, the largest share of volume in the first 30 minutes, and
the lowest mid-session volatility. Four of Monday's measures point the same way,
and three of them beat random. That is coherent in a way noise usually is not, and
it has an obvious mechanism: the weekend's accumulated news is priced at the open.

**Diagnostic — is the OR ratio finding an artifact of its own normalisation?**
The ratio divides by a trailing 20-session mean that mixes weekdays, so a raw
weekday pattern would appear in it mechanically. Checked:

| | one-way F across weekdays | approx p |
|---|---|---|
| raw OR height | 2.77 (4, 1413) | ≈ 0.026 |
| OR ratio | 4.38 (4, 1393) | ≈ 0.0016 |

The normalisation does not *create* the effect — the raw pattern is there — it
sharpens it by removing slow drift in the volatility level. Legitimate, but the
underlying statement is the modest one: **raw opening range runs ~12% wider on
Mondays than Wednesdays.**

---

## 4. The plain answer

**The calendar categories that carried the mechanism — forced flow and expiry —
do not separate session character beyond what random labels produce.** Month-end,
quarter-end, roll week and all four expiry categories are flat, on every statistic
and in every intraday window.

**One real pattern survives, and it is day of week**, which is the category with
the least "obligation" content in the set — nobody is *forced* to trade on a
Wednesday. Six of 52 beating the 95th percentile against 2.6 expected is about
2.3× chance, on 52 correlated tests. That is weak evidence, and only one test
clears the corrected threshold.

### And the surviving axis has already been measured, pointing the wrong way

The setup-grading run measured the OR-ratio axis directly on 13,840 trades:
**OR ratio ≥ 1.00 returned −0.021 R net, −0.038 gross.** Monday's distinguishing
feature is a *high* OR ratio. So the one calendar effect that survived Stage 1
operates through a variable already shown to be mildly *unfavourable*.

---

## 5. Stage 2, proposed as requested — with a recommendation against it

You asked for a proposal if something separated. Something marginally did, so here
it is, along with the reason I would not run it.

**Hypothesis:** day-of-week separates the outcome of the existing ORB and pullback
rules.

**Grid — 4 variants:** {Monday, Wednesday} × {ORB OR15 3R, pullback OR15 3R},
both machines unchanged, stop 1.0 ATR.

**Sample:** the sealed 2016–2020 set, 1,259 sessions, ≈250 per weekday.

**And here is why I recommend against spending it.** Per-session R has a standard
deviation near 2.54. At α = 0.05/4 and 80% power, with ~250 Monday sessions
against ~1,009 others:

> **MDE ≈ 0.60 R per session.**

The effects this project has measured are **0.04–0.08 R per session**. A Stage 2
on the holdout would be roughly **eight times underpowered** against any realistic
effect size. It would almost certainly return a null that means nothing, and it
would spend the only clean sample left to do it.

**My recommendation: do not approve Stage 2.** The holdout's value is that it is
unused. Spending it on a weak effect, in the wrong family, operating through a
variable already measured as unfavourable, at one-eighth the required power, is
the worst available use of it.

**If the calendar direction is worth continuing**, the honest next step is to
unblock the scheduled-events family — FOMC, CPI and NFP are where the obligation
mechanism is strongest and where an intraday pre/post split has real content. That
needs release dates, not more analysis of what is already on disk.

---

## 6. Where the ledger stands

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
| **calendar classification** | **1,418 sessions, 52 tests** | **1 of 52; mechanism families flat** |

Reproduce: `python3 scripts/orderflow/calendar_session_study.py`.
Detail in `reports/calendar_study_tests.csv` and `_control.csv`.
