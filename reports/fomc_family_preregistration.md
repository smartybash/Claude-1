# FOMC family — Stage 1, declared before running

Descriptive only. **No expectancy, no win rate, no verdict, no rule run.**
Sealed NQ days are not read. **2016–2020 stays sealed** — this screen reads only
`QQQ_1m.parquet`, which begins 2021-01-04.

## 1. What could be built and what could not

**FOMC: complete and validated.** 48 dates supplied, 2021-01 to 2026-12, checked
before use — 48 rows, **8 per year**, **4 SEP per year**, unique, sorted, all
Wednesdays except **2024-11-07**, which is a Thursday because that meeting shifted
for the US election. That irregularity is correct, not an error. **45 of 48 fall
inside the price sample** (2026-09-16, 10-28 and 12-09 are past 2026-08-31).

**CPI, NFP and PPI: cannot be built in this environment.**

| path | result |
|---|---|
| `curl` → alfred.stlouisfed.org | **403 CONNECT — policy denial** |
| `WebFetch` → alfred.stlouisfed.org | **EGRESS_BLOCKED** |
| `curl` / `WebFetch` → www.bls.gov | **EGRESS_BLOCKED** |
| fred.stlouisfed.org, api.stlouisfed.org | unreachable |

Both the primary source and its declared fallback are blocked by the network
egress policy. The proxy README states policy denials are to be reported, not
retried. **The 08:30 family is therefore not run, and is not reconstructed from
heuristics** — the first-Friday rule is known to mislabel January 2026 (moved to
11 February) and April 2026 (second Friday), and October 2025 CPI never published.

**To unblock:** paste the CPI and NFP release dates as text, exactly as the FOMC
dates were pasted. That is the only channel into this environment that works.

## 2. Why FOMC is kept as its own family

A 14:00 decision and an 08:30 print are **different experiments**. The 08:30 group
tests whether the *open* behaves differently after a release already absorbed
overnight. FOMC tests whether a **mid-session event splits one session into two
regimes**. Pooling them would make "pre" and "post" mean different things in each,
so they are never pooled.

## 3. Windows

| window | minutes from 09:30 | clock |
|---|---|---|
| **pre** | 0–270 | 09:30–14:00, ending exactly at the statement |
| **post** | 270–390 | 14:00–16:00 |

## 4. Categories and statistics

| # | category | n |
|---|---|---|
| 1 | FOMC decision day | 45 |
| 2 | day after FOMC | 45 |
| 3 | FOMC with SEP | 22 |
| 4 | FOMC without SEP | 23 |

Control for all four: **non-FOMC, non-day-after sessions, n = 1,328.**

**Statistics (5):** `rv_pre`, `rv_post`, `rv_ratio` (= post ÷ pre, the direct test
of the mechanism), `eff_post`, `or_ratio`.

### The control is contaminated, and the direction is stated now

Without CPI/NFP dates the control cannot be a *no-release* control. It is a
**non-FOMC** control, and roughly 24 of every 250 sessions in it (~10%) are CPI or
NFP days. That makes the control noisier and more event-like than intended, which
biases **towards finding no difference**. A null here is therefore weaker evidence
than a clean control would give; a positive is not weakened.

## 5. Multiple-testing burden and power, before any result

| | |
|---|---|
| categories | **4** |
| statistics | **5** |
| **total tests** | **20** |
| **Bonferroni α** | **0.05 / 20 = 0.00250** |
| two-sided critical z | 3.023 |

Minimum detectable difference, 80% power, as a percentage of each statistic's
sample mean:

| category | n | rv_pre | rv_post | rv_ratio | eff_post | or_ratio |
|---|---|---|---|---|---|---|
| FOMC decision day | 45 | **29%** | 43% | 56% | 45% | **25%** |
| day after FOMC | 45 | **29%** | 43% | 56% | 45% | **25%** |
| FOMC with SEP | 22 | 41% | 60% | **79%** | 63% | 35% |
| FOMC without SEP | 23 | 40% | 59% | **78%** | 62% | 34% |

**What this can and cannot show.** At n = 45 the decision-day category can detect a
29% change in morning volatility and a 43% change in afternoon volatility. If the
Fed effect is what folklore claims — afternoon volatility multiples of normal — it
will be unmissable. **What it cannot do is resolve anything subtle**: a genuine 20%
afternoon effect would be missed. **The two SEP categories (n = 22, 23) are
underpowered on every statistic except `or_ratio`** and any null on them will be
labelled underpowered, not negative.

## 6. Control that decides it

**1,000 random label assignments per category, group sizes matched exactly**, over
the same pooled sessions. Each real difference is placed in the distribution of
1,000 random differences and its percentile reported.

## 7. What will not happen

No performance test. No rule is run or imported. If something separates, a Stage 2
pre-registration is proposed for approval with grid and sample size declared, and
not run. 2016–2020 stays sealed.

Committed before `scripts/orderflow/fomc_study.py` was run.
