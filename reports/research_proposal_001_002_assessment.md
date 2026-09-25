# Research proposals 001 and 002 — §4 assessment before discovery

Required by `84704f8` §4: no performance is run until a research proposal proves
a valid deployment and validation path exists. Required by `84704f8` §3: an
untouched sample capable of ≥150 trades over ≥12 months must be **confirmed to
exist before discovery**, and the proposal rejected if no credible validation
path does.

**No performance has been run. No rule has been frozen. This document is the
gate, not the study.**

---

## Summary

| | Proposal 001 · Event Vol Expansion | Proposal 002 · Opening Auction Inventory |
|---|---|---|
| Named discovery data | NQ 2021–2025 | NQ 2021–2025 |
| **Held** | **15 sessions** | **15 sessions** |
| Named validation data | ES + RTY | ES |
| **Held** | ES 15 sessions · **RTY none** | ES 15 sessions |
| Event universe as specified | 32/yr | n/a |
| **Event universe obtainable** | **8/yr (FOMC only)** | n/a |
| Frequency vs 4/mo portfolio floor | **0.67/mo — 6× short** | plausibly clears 12/mo |
| 150 OOS trades would take | **18.75 years** | ~12 months |
| **§3 gate** | **FAIL** | **PASS, conditional** |

**Recommendation: invert the stated priority.** 002 is executable now on QQQ;
001 is not executable at all as written.

---

## 1. The data named in both proposals does not exist here

Both proposals specify NQ 2021–2025 for discovery. Measured holdings:

| file | rows | sessions | span |
|---|---|---|---|
| `NQ_5min.parquet` | 2,174 | **15** | 2026-06-17 → 2026-07-06 |
| `ES_5min.parquet` | 2,174 | **15** | 2026-06-17 → 2026-07-06 |
| `NQ_daily.parquet` | 61 | 61 | 2026-04-07 → 2026-07-02 |
| RTY — any resolution | — | **0** | **absent entirely** |

The loose `nq_*.json` / `es_*.json` files are recent 1,000-bar API windows, all
inside 2026. The NQ **tick tape** is 36 true-0.25 sessions (2026-07-01 →
08-20) plus 17 quantised to 5.00 — also 2026 only.

**There is no NQ, ES or RTY history for 2021–2025 in this environment.**

Acquisition has not been attempted and is **not established as feasible**: Alpha
Vantage carries no futures; FMP's economics endpoint is plan-gated and siblings
likely sit on the same tier; IBKR does hold futures history but continuous
series require a declared roll rule and back-adjustment convention, which is
exactly the class of specification choice that silently redefines a rule. Any
NQ-based proposal must first pass a data-acquisition step with the roll
convention frozen in writing.

---

## 2. Proposal 001 — the event universe collapses, and the §3 gate fails

### 2.1 CPI and NFP release dates are unobtainable — re-confirmed

This was already recorded at `a306378` when the FOMC family was pre-registered.
Re-checked rather than assumed:

- `federalreserve.gov` — **egress-blocked** (curl and WebFetch, this session)
- `cdn.alphavantage.co` — **egress-blocked**
- FMP `economics-calendar` — **plan-gated, access denied**
- Alpha Vantage `CPI` — returns **reference month, not release date**. The
  August 2026 figure is stamped `2026-08-01`; it was published in mid-September.
  `NONFARM_PAYROLL` has the same shape.

The first-Friday heuristic was already rejected at `a306378` because it
mislabels two sessions in this very window and one inflation print was never
published at all.

**Event universe: 32/year as proposed → 8/year obtainable.** FOMC only.

### 2.2 The §3 gate fails on arithmetic

| | FOMC only | full proposed universe |
|---|---|---|
| events/year | 8 | 32 |
| trades/year (1 bracket per event) | 8 | 32 |
| **years to reach 150 OOS trades** | **18.75** | **4.7** |
| trades/month | **0.67** | 2.7 |
| vs 4/month three-strategy floor | **6× short** | 1.5× short |

§4.1 requires 150 OOS trades over ≥12 months. **No untouched sample capable of
that exists or can be constructed for this event set**, at either universe size.
Per §3 this is a rejection before discovery, not a finding after it.

The <150 exception in §4.1 does not rescue it: the exception permits a smaller
sample when a power analysis shows the sample can resolve the required edge. At
8 events/year the constraint is not statistical power, it is **calendar time** —
no analysis makes 18.75 years available.

### 2.3 A mechanism objection that matters more than the logistics

The proposal states the mechanism "does not require directional forecasting."
**Half true, and the other half is the problem.**

V1–V3 are breakout brackets: buy stop above the pre-event range, sell stop
below, time exit. That is **a barrier trade, not a volatility harvest.** It pays
|displacement from the trigger| in the direction triggered. It does not require
*forecasting* direction — but it does require the move to **persist after the
trigger**. If price expands and reverses, the bracket triggers, loses, and may
trigger the opposite side and lose again.

That persistence is the efficiency ratio — net displacement over path length —
which §3.5 of the ledger identifies as the one quantity that has not conditioned
on anything observable across 300+ tests. **The breakout bracket re-imports the
exact problem the proposal is trying to escape.**

If this family is ever run, the **double-trigger rate must be a declared kill
condition**, measured before expectancy.

### 2.4 We already have direct evidence on the premise

The proposal's stated edge is "realized movement exceeding what is priced into
the immediate post-event period." **That hypothesis was tested and closed six
commits ago** (`c7aad00`):

| | |
|---|---|
| FOMC straddle, paired | **−3.54%** of premium |
| unpaired | **−6.89%**, n=39 |
| FOMC premium vs matched placebo | 2.11% vs 1.82% of spot |

Realised movement did **not** exceed the priced amount; the market charges a 16%
premium uplift for the event and collects it. A futures bracket is a genuinely
different trade — it pays no option premium, so it is not buying vol at the
market's price — but the evidence that the underlying premise is false now
exists and is specific to this instrument and these dates.

### 2.5 Verdict on 001

**Reject before discovery**, per §3. Not on the mechanism's merit — on the
absence of any validation path, at a frequency 6× below the portfolio floor,
against a premise with direct contrary evidence.

**A cheaper version is available if the mechanism question is worth settling:**
run it on **QQQ 1-minute 2021–2026 around the 45 held FOMC dates**, data already
in hand, zero acquisition cost. That can **never** be a deployable candidate at
8 events/year — it would be a mechanism study, explicitly labelled as such — but
it would resolve whether post-event continuation exists before any money is
spent on futures history.

---

## 3. Proposal 002 — executable now, but not on the named instrument

### 3.1 What exists

NQ 2021–2025 does not. **QQQ 1-minute does**: 1,421 sessions, 2021-01-04 →
2026-08-31, the established discovery set. SPY/IWM/IJH/EFA 1-minute 2021–2025
exist at 1,255 sessions each.

Every state variable the proposal names is computable on it: gap size (prior
close → open), overnight return, distance of open relative to overnight range,
and the 15-minute opening extension. **The QQQ extended-hours file is required
for the overnight range**, and it carries the documented bad-print defect —
33.2% of sessions had a raw overnight range set by a single print — so a robust
range estimator must be declared before discovery, not chosen after.

### 3.2 Frequency — the first proposal in this project that plausibly clears

~21 sessions/month. If the setup fires on ≥57% of sessions it reaches 12/month
as a standalone. At ≥19% it clears the 4/month three-strategy floor. **This is
the first construction in the ledger whose frequency is plausible by
construction rather than by relaxation** — every prior family ran at 2.6–5.7
trades/month.

The expected firing rate must be **stated before discovery**, per §4 of the
clarifications, and then checked against the realised rate.

### 3.3 Out-of-sample designation — the open question

2016–2020 is spent. The candidates, and what each would actually be:

| sample | role it could serve |
|---|---|
| SPY / IWM / IJH / EFA 1-min 2021–2025 | **validation**, but only under the §2 conditions — rule frozen first, no prior study influencing a parameter, mechanism expected to transfer, definitions instrument-native |
| forward collection on QQQ | genuine out-of-time; at 12/month, 150 trades = **12.5 months** |
| NQ, once acquired | out-of-time on the intended deployment instrument — needs the roll convention frozen |

The §2 clarification turns on whether the hypothesis is Nasdaq-specific.
**It is not.** Overnight inventory accumulation, transfer through the opening
auction, and dealer rebalancing is a general market-structure claim, not a
Nasdaq microstructure claim. On that reading the related instruments are
legitimate **validation** rather than mere portability — but that reading must
be **declared explicitly in the pre-registration and defended before discovery**,
because if it is wrong the whole validation path is wrong.

### 3.4 What is still missing before this can proceed

- The rule is **not frozen**. The proposal says so itself ("Example only. Not
  yet frozen").
- Deployment instrument vs discovery instrument mismatch: discovery on QQQ,
  intended deployment NQ. Prop evaluations trade futures. A QQQ-discovered rule
  must transfer to NQ, and that transfer is **portability, not validation** —
  the IB midpoint pullback family already demonstrated how expensive it is to
  discover that late.
- Execution model, prop compatibility and kill control are unspecified.

### 3.5 Verdict on 002

**Proceed to a full pre-registration — do not run performance yet.** The §3 gate
passes conditionally: a sample capable of ≥150 trades over ≥12 months plausibly
exists, provided the firing rate clears ~19–57% of sessions and the OOS
designation is defended in advance.

---

## 4. Recommendation

**Invert the stated priority.**

1. **Proposal 002 first**, discovery on QQQ 1-minute 2021–2026, with the rule,
   the firing-rate estimate, the OOS designation and the QQQ→NQ transfer
   question all frozen in a pre-registration before any performance is computed.
2. **Proposal 001 rejected before discovery** as a deployable candidate. If the
   mechanism is worth settling, run the zero-cost QQQ+FOMC mechanism study and
   label it as such.
3. **Neither proposal proceeds on NQ** until futures history is acquired and the
   roll convention is frozen in writing.

I am not starting either. The next artefact is a pre-registration for 002, on
request.

---

## Note on the priority I was given

Proposal 001 was ranked first for good reasons — strongest surviving mechanism,
not another directional prediction, tied to identifiable participants. The
ranking is sound on the merits. It fails on availability: the data named does
not exist, the event dates cannot be obtained, and the frequency cannot reach
the standard committed at `a94e717`. That is a logistics verdict, not a verdict
on the idea.

The proposal's closing instruction — *start with "who must trade and why?", not
"what pattern appears on the chart?"* — is the correct lesson and both proposals
honour it. 002 honours it **and** is executable.
