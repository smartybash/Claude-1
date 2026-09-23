# RP-008 Stage 1 — regime validity. Pre-registration.

**Written and committed before any forward-environment result was computed.**

This stage is about the market, not about strategies. **No strategy P&L, no
strategy trade, no conditional performance, no allocator, no pairing, no Monte
Carlo.** Nothing in the frozen strategy library is loaded by the Stage 1 code.

The question, restated in the form that decides it:

> **If I know the state at time T, do I face a materially different forward
> trading environment than I would in another state?**

Direction prediction is not required and is not tested.

---

## 1. The pivot, and why the burden is now on the regimes

RP-002 through RP-007 all asked "is there another setup?" and all closed. Stage 0
found that the frozen library has no time-of-day diversity — 95% of 13,890
trades enter before 11:30 — so "which strategy in which regime" cannot be asked
honestly of this library.

The prior question is whether the states are economically distinct **at all**. If
they are not, then a large class of future work — every "trade only when X" rule
this desk might write — loses its premise in one measurement. That is worth more
than another setup.

**My prior: against, narrowly.** The regime-forecastability study already found
that price-derived information at a decision timestamp does not predict later
session character (14 combinations, largest |ρ| 0.042, 91% of the cross-session
spread in efficiency reproduced by random walks). Stage 1 asks a *weaker* and
different question — not "does the state predict direction or efficiency" but
"does the state change the size of what happens next" — and volatility is the
one quantity in this project that has repeatedly clustered. **I expect
volatility and excursion scale to separate, and I expect path efficiency and
transition structure not to.** Stated now so a partial pass is not read as a
full one.

---

## 2. Inputs — approved causal variables only

Used: prior-session realised volatility; realised volatility through the
classification instant; realised-volatility percentile against prior completed
sessions; net displacement ÷ path length to the classification instant;
opening-range size vs trailing distribution; distance from session VWAP in ATR
units; verified FOMC flag; frozen time-of-day block.

**Not used, and not loaded by the code:** overnight return, overnight range, any
future session information, any strategy P&L, any strategy trade, any strategy
outcome.

Sample: **QQQ one-minute, 2021-01-04 → 2026-08-31, 1,421 sessions.** QQQ is the
only instrument with enough history for this question; the finding is about
market structure and the Stage 2 decision it feeds is not an MNQ deployment
decision.

---

## 3. Frozen state definitions

### 3.1 Classification instants

Two, per session, chosen **before** any forward outcome was viewed:

| instant | block it opens | time remaining to the cash close |
|---|---|---|
| **09:30** | opening auction 09:30–10:00 | 390 min |
| **11:30** | midday 11:30–14:00 | 270 min |

**Why these two and not all four.** The cap is six states. Two blocks × three
volatility terciles = six exactly. The open and the midday are the two blocks
most different in the folk account — the high-activity auction against the
lunchtime lull — so this pair gives the **time-of-day-only** kill condition its
best chance of firing. Choosing the two most contrasting blocks is the
conservative choice, not the flattering one.

Morning and closing blocks are reported in a **secondary descriptive panel**
only. They carry no pass/fail weight. Declared here so the panel cannot later be
promoted.

### 3.2 Volatility axis — one definition, both instants

**RV₆₀ = realised volatility of the most recent 60 minutes of regular-hours
trading strictly before the classification instant**, as the standard deviation
of one-minute log returns.

* at **11:30** that is 10:30–11:30 of the same session;
* at **09:30** there is no prior cash data in the session, so it is **15:00–16:00
  of the previous regular session** — a prior-session variable, which is on the
  approved list.

One definition, uniform in form at both instants: *the last hour of trading
before the decision.*

**Terciles are pooled across both instants**, from a rolling causal history of
the **prior 250 classification observations** (both instants, chronological, the
current observation excluded). Boundaries at the 33.3rd and 66.7th percentiles.

Pooling is deliberate. Block-relative terciles would force one third of each
block into each state and would **erase by construction** any volatility
difference between the open and the midday — which is part of what Stage 1 must
measure. Pooled boundaries let the cells come out unbalanced, and the imbalance
is itself a reportable finding about whether volatility and time of day are the
same variable wearing two hats.

### 3.3 The six frozen states

| state | classification instant | RV₆₀ tercile |
|---|---|---|
| **S1** | 09:30 | LO |
| **S2** | 09:30 | NORMAL |
| **S3** | 09:30 | HI |
| **S4** | 11:30 | LO |
| **S5** | 11:30 | NORMAL |
| **S6** | 11:30 | HI |

**Axis 3 (directional efficiency) is NOT used to form states.** Splitting six
states into twelve would halve every cell for no gain — Stage 1 has ample sample
per state (roughly 470 observations before the warm-up) and the cap is a
discipline on multiplicity, not on sample. Causal path efficiency to the
classification instant is instead **reported as a within-state covariate and as
a forward outcome**, which is where it answers a question rather than creating
cells.

### 3.4 Volatility unit

**ATR₁ₘ = mean one-minute true range of the previous regular session.** Causal,
one number per session, the same unit RP-007 used. Every scaled outcome below is
in ATR₁ₘ so that nothing depends on QQQ's price level, which roughly doubles
across the sample.

---

## 4. Forward outcomes — measured forward only

**Horizon: 60 minutes from the classification instant, exclusive of the
classification bar.** The classification window is never inside the forward
window: RV₆₀ looks back, the outcomes look forward, and the two do not share a
bar.

Sixty minutes is used at both instants so the two are directly comparable, even
though it extends past the end of the 30-minute opening block. The block labels
name the decision time, not the measurement window.

For each observation:

| outcome | definition |
|---|---|
| forward realised volatility | sd of 1-min log returns over the forward 60 bars, in bps |
| forward range | (high − low) over the forward window, in ATR₁ₘ |
| forward MFE | max(high) − price at classification, in ATR₁ₘ |
| forward MAE | price at classification − min(low), in ATR₁ₘ |
| forward path efficiency | \|net displacement\| ÷ sum of \|1-min changes\| over the forward window |
| **stop-out probability** | P(adverse excursion ≥ d) for d ∈ {0.5, 1.0, 1.5, 2.0} × ATR₁ₘ, reported **separately for the down side and the up side**, and for either |
| time remaining to the cash close | deterministic per instant — reported because it is a pure time-of-day property and must not be mistaken for a volatility effect |
| transition | the state at the **next** classification instant (same-day 11:30 after 09:30; next-session 09:30 after 11:30) |

Also reported per state: counts, sessions, days per month, minutes, share of
sample, mean duration, by-year frequency, by-year outcome, and the by-year
transition matrix.

---

## 5. What "materially different" means — economic bars, frozen now

Statistical detectability is not the test. With ~470 observations per state,
differences far too small to matter will be significant. **Every bar below is a
size, not a p-value.**

| # | condition | bar |
|---|---|---|
| 1 | **volatility differs** | forward RV of the HI state ≥ **1.50×** the LO state, at the same instant |
| 2 | **excursion distributions differ** | median forward MAE (and MFE) of HI ≥ **1.30×** LO, **and** the overlap coefficient of the two distributions ≤ **0.85** |
| 3 | **stop-out risk differs** | at ≥1 representative stop distance, P(adverse excursion ≥ d) differs by ≥ **10 percentage points** between two states |
| 4 | **holding opportunity differs** | mean forward path efficiency differs by ≥ **0.05**, or time-to-close differs by ≥ 60 minutes with a corresponding excursion difference |
| 5 | **stable across years** | the ordering of states on conditions 1–3 holds in **≥ 5 of 6** calendar years |
| 6 | **survives neighbouring thresholds** | repeating with 30/70 and 40/60 splits instead of 33/67 terciles preserves the ordering and keeps conditions 1–3 clear |
| 7 | **economically meaningful** | condition 3's difference is ≥ 10 points at a stop distance a real trade would use (0.5–2.0 ATR₁ₘ), not only at an extreme |

**At least two states must have clearly different forward environments.**

### The separation test that decides between the two verdicts

Conditions 1–7 can all be satisfied by time of day alone. So one further test,
declared now, is decisive:

> **At matched volatility tercile, do the 09:30 and 11:30 states differ? And at
> matched instant, do the LO and HI terciles differ?**

* If **only the instant matters** (S1≈S2≈S3, S4≈S5≈S6, but 09:30 ≠ 11:30), the
  finding is "time of day is the only regime", which **fires kill condition 7**.
* If **only volatility matters** (LO ≈ LO and HI ≈ HI across instants, but
  LO ≠ HI), volatility is a genuine regime axis and time of day is decoration.
* If **both matter and interact**, regimes are meaningful in the full sense.

---

## 6. Kill conditions

Close RP-008 immediately if any holds:

1. states differ only by construction — the forward difference is a restatement
   of RV₆₀ itself with no independent forward content;
2. forward environments are materially similar (conditions 1–4 fail their bars);
3. excursion distributions overlap heavily (overlap coefficient > 0.85);
4. stop-out probabilities are similar (< 10 points everywhere);
5. transition behaviour is unstable across years;
6. neighbouring thresholds produce the same results, i.e. the tercile boundaries
   are doing no work;
7. **the only meaningful distinction is time of day itself.**

## 7. Condition 1, made testable rather than rhetorical

"States differ only by construction" is the hardest kill to adjudicate, because
a volatility state *should* be followed by volatility — that is what clustering
means, and it is not a defect. The version that would be circular is if the
forward measurement shared bars with the classification window. It does not:
RV₆₀ ends at the classification bar and the forward window begins after it.

The test applied is a **persistence control**: compare the state's forward RV
against the forward RV predicted by a simple AR(1) on RV₆₀ alone. If the state
labels add nothing beyond the trivial persistence of volatility, the tercile
structure is a lookup table for RV₆₀ and not a regime. Reported as the ratio of
between-state variance explained to AR(1)-explained variance.

## 8. Multiplicity

6 states × 7 primary outcome families = **42 primary comparisons**, plus 2
neighbouring-threshold repetitions and 1 persistence control. Where a p-value is
quoted at all it is against **α = 0.05/42 = 0.00119** — but no pass condition
depends on a p-value. The bars in §5 are sizes.

## 9. Verdict form

Exactly one:

* **Verdict A — regimes not meaningful, close RP-008;**
* **Verdict B — regimes meaningful, proceed to a redesigned Stage 2.**

**Stage 2 is not authorised by a Verdict B.** It only opens the discussion.

---

## 10. Declared

No strategy P&L is read. No strategy module is imported by the Stage 1 code. No
allocator is built, no pairing evaluated, no Monte Carlo run. Sealed NQ dates
are not read; the NQ tape is not opened at all. 2016–2020 is not opened.

Every constant above is frozen: two classification instants (09:30, 11:30),
RV₆₀ as the last 60 minutes of regular trading before the instant, pooled
rolling 250-observation causal terciles at 33.3/66.7, ATR₁ₘ as the prior
session's mean one-minute true range, a 60-minute forward horizon, stop
distances {0.5, 1.0, 1.5, 2.0} × ATR₁ₘ, and the seven economic bars in §5.

None will be varied during or after the run.
