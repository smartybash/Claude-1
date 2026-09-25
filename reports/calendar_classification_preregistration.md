# Calendar session classification — Stage 1, declared before running

Descriptive only. **No expectancy, no win rate, no verdict, no performance test.**
Sealed NQ days are not read. **The 1,259 sessions of 2016–2020 stay sealed** and
are reserved as the holdout for anything that survives; this screen reads only
`QQQ_1m.parquet`, which begins 2021-01-04 and cannot reach them.

The rationale is the one that distinguishes this from everything before it: a
calendar label identifies participants with an **obligation** to trade rather than
a choice, and the label is **known years in advance**, so unlike the regime work
nothing has to be forecast.

---

## 1. One third of the requested design cannot be built, and I will not fake it

**The scheduled-events family — FOMC day, day after FOMC, CPI day, NFP day, and
the no-release control — requires real release dates, and I cannot obtain them.**

| source | result |
|---|---|
| this repository | no FOMC / CPI / NFP dates anywhere |
| FMP `economics-calendar` (has true release dates) | **denied — requires Starter tier or above** |
| Alpha Vantage `CPI`, `NONFARM_PAYROLL` | keyed by **reference month** (`2026-08-01`), not release date — verified, not assumed |

I am not deriving these from memory. FOMC dates are a published schedule, CPI has
no derivable rule, and NFP's "first Friday" heuristic is wrong often enough that a
10–15% mislabel rate would contaminate both the category *and* its control.
Fabricated dates would produce a plausible-looking result, which is worse than no
result. My training cutoff also sits inside the sample window, so part of 2026
could not be checked even in principle.

**To unblock it:** either an FMP Starter subscription, or a CSV of release dates
dropped into `data/` (the Fed publishes its meeting calendar years ahead; the BLS
publishes CPI and Employment Situation release schedules annually). Either would
make the scheduled-events family a straightforward addition.

**What runs instead:** the two families that are pure calendar arithmetic and
carry no inference at all — forced flow and expiry.

---

## 2. The 13 categories, defined exactly

**Forced flow** — control is every other session unless stated:

| # | category | definition |
|---|---|---|
| 1 | last 3 of month | the final 3 trading sessions of the calendar month |
| 2 | last 3 of quarter | the final 3 trading sessions of the calendar quarter |
| 3 | first of month | the first trading session of the calendar month |
| 4–8 | Monday … Friday | day of week, each against all other days |
| 9 | futures roll week | **the 5 sessions ending on the Thursday immediately before quarterly expiry** — stated exactly so it cannot drift |

**Expiry:**

| # | category | control |
|---|---|---|
| 10 | monthly expiry (third Friday) | ordinary Fridays |
| 11 | quarterly expiry (third Friday of Mar/Jun/Sep/Dec) | ordinary Fridays |
| 12 | session before monthly expiry | **ordinary Thursdays** |
| 13 | session before quarterly expiry | **ordinary Thursdays** |

### One declared deviation from the brief

The brief specified *ordinary Fridays* as the control for the whole expiry family.
For categories 12 and 13 that would compare a **Thursday** against **Fridays**,
confounding day-of-week with expiry — and categories 4–8 exist precisely because
day-of-week might matter. Those two use **day-matched controls (ordinary
Thursdays)** instead. Declared here rather than done silently.

---

## 3. Multiple testing burden, stated before any result

| | |
|---|---|
| categories | **13** |
| statistics per category | **4** — realised vol, session range, efficiency ratio, OR height ÷ trailing 20-session mean |
| **total tests** | **52** |
| **Bonferroni threshold** | **α = 0.05 / 52 = 0.000962** |
| two-sided critical z | **3.302** |

Volume distribution across intraday windows is **reported but not tested** — it is
descriptive context, and counting it would inflate the burden without adding a
hypothesis.

---

## 4. Minimum detectable difference — what each group can and cannot show

At α = 0.000962 with 80% power, using the pooled marginal SDs (rv 50.33 bps,
range 94.42 bps, efficiency 0.0437, OR ratio 0.4269 — these are properties of the
sample, not of any comparison):

| category | n | ctrl | MDE rv | MDE range | MDE eff | MDE OR | rv as % of mean |
|---|---|---|---|---|---|---|---|
| last 3 of month | 204 | 1,214 | 15.8 | 29.6 | 0.0137 | 0.134 | **16%** |
| last 3 of quarter | 69 | 1,349 | 25.7 | 48.3 | 0.0223 | 0.218 | 26% |
| first of month | 68 | 1,350 | 25.9 | 48.6 | 0.0225 | 0.220 | 27% |
| Monday | 264 | 1,154 | 14.2 | 26.7 | 0.0124 | 0.121 | 15% |
| Tuesday | 294 | 1,124 | 13.7 | 25.6 | 0.0119 | 0.116 | **14%** |
| Wednesday | 292 | 1,126 | 13.7 | 25.7 | 0.0119 | 0.116 | 14% |
| Thursday | 285 | 1,133 | 13.8 | 25.9 | 0.0120 | 0.117 | 14% |
| Friday | 283 | 1,135 | 13.9 | 26.0 | 0.0120 | 0.118 | 14% |
| futures roll week | 110 | 1,308 | 20.7 | 38.8 | 0.0180 | 0.176 | 21% |
| monthly expiry | 68 | 215 | 29.0 | 54.4 | 0.0252 | 0.246 | 30% |
| **quarterly expiry** | **22** | **215** | **46.7** | **87.6** | **0.0405** | **0.396** | **48%** |
| pre-monthly expiry | 68 | 218 | 29.0 | 54.3 | 0.0251 | 0.246 | 30% |
| pre-quarterly expiry | 22 | 218 | 46.6 | 87.5 | 0.0405 | 0.396 | 48% |

### Answering the question directly

**Quarterly expiry has 22 sessions, not 23.** What that can show:

- It can detect an effect that changes realised volatility by **≥ 46.7 bps —
  roughly half the sample mean of 97.6**. A quarterly expiry that is half again
  as volatile as an ordinary Friday would show up clearly.
- It **cannot** show anything subtler. A genuine 20% volatility effect — large by
  any practical standard — would be **missed**, and a null on this category means
  "not enormous", not "not there".
- On the efficiency ratio it needs a difference of **0.0405** against a sample
  mean of **0.0600**. It can effectively only detect an effect that changes
  session character by two thirds or more.

**So quarterly expiry is structurally near-useless at this sample size, and that
is known before the run rather than discovered after.** It is reported for
completeness and any null on it will be labelled underpowered, not negative. The
day-of-week categories, at 264–294 sessions and a 14% MDE, are the only ones with
real resolving power.

---

## 5. The control that decides it

**1,000 random label assignments per category, with group sizes matched exactly.**
For each of the 52 statistic-category pairs, the real difference is placed in the
distribution of 1,000 random differences and its percentile is reported.

**If real calendar categories do not separate session character beyond what random
labels of the same size produce, that will be said plainly and Stage 1 ends there.**

---

## 6. The intraday split, honouring the mechanism

The brief asks for pre/post release windows because compression before a known
time and release after it would be averaged away by a whole-session statistic.
That reasoning survives the loss of the scheduled-events family, because **the
constructible categories also have known times**:

- **Month-end and quarter-end flow is struck at the close** — benchmark
  rebalancing prints in the closing auction.
- **Expiry settles at the open** for AM-settled index products.

So every category is measured in three windows, not one:

| window | minutes from the open |
|---|---|
| `open30` | 0–30 |
| `mid` | 30–360 |
| `close30` | 360–390 |

Realised volatility **and** share of session volume are reported per window, so a
concentration at one end is visible rather than averaged into the middle.

---

## 7. What this run will not do

- **No performance test of any kind.** No rule is run, no trade is generated, no
  expectancy is computed.
- **If something separates, I will propose a Stage 2 pre-registration for
  approval** — grid declared, sample size stated — and not run it.
- **2016–2020 remains sealed.** It is the only clean sample left and it is
  reserved for whatever survives discovery.

---

Committed before `scripts/orderflow/calendar_session_study.py` was run.
