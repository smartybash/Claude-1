# FOMC straddle — Amendment 2, declared before the run

Amends `a971882` (pre-registration) and `b7becac` (amendment 1). No event P&L has
been computed beyond the single disclosed plumbing probe.

---

## A. `fomc.csv` provenance — settled, and the 45/45 validation stands

Amendment 1 rested the credibility of the recalled 2016–2020 dates on an exact
match against `data/events/fomc.csv`. That is only a valid test if the file was
externally sourced rather than recall-derived by the same process.

**It was externally sourced.** The file has exactly one commit, `a306378`
(2026-09-18), and the accompanying `reports/fomc_family_preregistration.md` is
explicit:

> line 9: **48 dates supplied**, 2021-01 to 2026-12
>
> line 31: paste the CPI and NFP release dates as text, **exactly as the FOMC
> dates were pasted**

The dates were pasted into the environment by the principal from an outside
source. Independently recalling that block and reproducing it 45/45 is therefore
a genuine validation, and the recalled 2016–2020 dates inherit its credibility.

The limitation recorded in amendment 1 §B still stands and is unchanged: the
2016–2020 dates are **recall-sourced with structural verification, not
source-verified**. The 2021–2026 block is source-verified. Validation against
realised volatility remains ruled out as contaminating.

---

## B. Correction to record: the repo already knew

The commit that added `fomc.csv` states:

> the single non Wednesday is the November 2024 meeting that shifted for the
> election, **which is correct rather than an error**

**That fact was in the repository on 2026-09-18. The pre-registration at
`a971882` hardcoded Wednesday entry, Wednesday exit and a Wednesday-only
verification gate anyway.** Amendment 1 caught it, but it should not have needed
catching — the evidence was already on disk.

This is the **second** instance in this project of contradicting evidence already
committed to the repository; the ATAS `Step` / `TickSize` incident at `5509fcc`
was the first. Both are specification errors, and both would have produced
plausible-looking numbers. To be added to `reports/correction_ledger.md`.

---

## C. Quarterly expiry: promoted from diagnostic to promotion gate

Amendment 1 reported the quarterly split as a diagnostic excluded from promotion.
That leaves a gap: promotion could still fire on the pooled estimate while the
split showed the effect living entirely in one contract class. The ±1-week
placebo **cannot** detect this, because the placebo is a different instrument.

### Measured, not assumed

| | events | standard 3rd-Friday expiry | of which quarterly |
|---|---|---|---|
| discovery 2021–2026 | 45 | **15 (33%)** | **15** |
| OOS 2016–2020 | 39 | **12 (31%)** | **12** |
| **pooled** | **84** | **27 (32%)** | **27** |

**Every standard-expiry FOMC week is a quarterly week — 27 of 27.** The
mechanically correct contract-class boundary (third Friday) and the declared
boundary (quarterly) coincide exactly in this sample, so a single rule suffices.
Verified rather than assumed; a second rule would be redundant.

### The placebo cannot control for it

| | standard-expiry share |
|---|---|
| FOMC events | **32%** (27 of 84) |
| ±1-week placebos | **12%** (20 of 168) |

For **all 27 quarterly events, both placebos are necessarily weeklies** — ±1 week
from a third Friday is the second or fourth Friday. The contract class is
confounded with the event by construction.

### The rule, declared

> **If the quarterly and non-quarterly sub-estimates differ by more than the
> pooled MDE, promotion is void and the family closes.**

Split sizes: pooled 27 vs 57; discovery 15 vs 30.

### Operating characteristic, stated before the run

With σ ≈ 0.45 of premium, the SE of the quarterly minus non-quarterly difference
is `0.45 × sqrt(1/27 + 1/57)` = **10.5%**, against a pooled MDE of **9.8%**.

**Under a true null of no heterogeneity the rule voids about 35% of the time**
(`P(|z| > 0.93)`). That is a high unconditional false-void rate and it is
accepted deliberately:

- The gate only binds **conditional on the pooled estimate already clearing
  MDE**, and conditional on that, real heterogeneity is likelier.
- The costs are asymmetric. A false void loses a candidate. A false promotion
  sends capital at a **contract-class artefact dressed as an FOMC effect**, in a
  programme whose §5 default action is closure. The conservative error is the
  cheap one.

---

## D. Single-event influence — reported, not promotion-relevant

The disclosed plumbing probe, 2024-09-18, returned `r_exec` = **−23.9%**, more
than 2× the pooled MDE. At n = 45 one observation of that size moves the mean
materially.

**It is not excluded** — excluding a looked-at event is worse than disclosing it,
and this desk does not filter. Reported beside the headline:

1. Mean **with and without 2024-09-18**, both blocks and pooled.
2. The standing concentration rule `max(10, ⌈0.10n⌉)` — **10 trades at n = 45**,
   and **10 at n = 84** (⌈8.4⌉ = 9, floor binds) — run on both tails, same as
   every other family in the ledger.
3. Top-5 concentration, event set and placebo set.

**All three are informational. None is a promotion gate**, consistent with the
concentration rule's standing demotion to a reported diagnostic.

---

## E. Unchanged

Everything else in `a971882` and `b7becac` stands: one grid point ·
announcement-relative entry and exit · placebos preserve weekday · `r_exec`
headline with `r_mid` beside · RV/IV diagnostic only · placebo-estimated σ ·
the ρ > 0.25 paired/unpaired switch · ±1 week primary, ±2 week robustness ·
two-stage discovery-then-OOS with pooled promotion and OOS sign agreement · the
one-sided promotion rule · Thursday/DTE split diagnostic · no strangle, delta
overlay, VIX filter, skew tilt or moneyness search · **after this test, no future
family uses 2016–2020 as OOS.**

---

Committed before `scripts/orderflow/fomc_straddle.py` was written or run.

---

## F. Correction to §C and to amendment 1 §A, before the run

Building the script surfaced two errors in the counts declared above. Nothing
had been run; no P&L informed either correction.

### 1. The quarterly count was computed with a naive Friday

§C classified contract class using the same-week Friday without applying the
holiday fallback that the pre-registration §9 declares. **2026-06-19 is
Juneteenth, a Friday market holiday**, so the June 2026 FOMC week has no Friday
expiry and the fallback moves it to Thursday 2026-06-18.

Calling that Thursday a weekly is wrong. **When the third Friday is an exchange
holiday, the monthly and quarterly contracts expire on the preceding Thursday** —
2026-06-18 *is* the June 2026 quarterly. The classifier is now holiday-aware
(`standard_expiry`).

**The declared counts in §C are unchanged and correct: 27 of 84 quarterly, 15
discovery and 12 OOS, 57 non-quarterly.** The intermediate figure of 26 produced
by the naive classifier was the error, and it is recorded here rather than
quietly fixed. The promotion gate and its stated operating characteristic
(split SE 10.5% against pooled MDE 9.8%, ~35% false-void under a true null)
stand as declared.

### 2. The DTE-1 set is four events, not three

Amendment 1 §A listed three events exiting at DTE 1, all election-week
Thursdays. **There is a fourth:** 2026-06-17, where the Juneteenth holiday moves
the expiry to Thursday 2026-06-18 and leaves the announcement-day exit one day
from expiry.

| event | weekday | expiry | cause | quarterly |
|---|---|---|---|---|
| 2018-11-08 | Thursday | 2018-11-09 | midterm shift | no |
| 2020-11-05 | Thursday | 2020-11-05+1 | election shift | no |
| 2024-11-07 | Thursday | 2024-11-08 | election shift | no |
| **2026-06-17** | **Wednesday** | **2026-06-18** | **Juneteenth holiday** | **yes** |

80 events exit at DTE 2, four at DTE 1. The DTE split remains **a reported
diagnostic excluded from promotion**, on the same footing as before; only its
membership changes.

### Placebo exclusions

Two placebos fall on market holidays and are excluded, recorded not silent:
**2024-06-19** (Juneteenth) and **2024-12-25** (Christmas). Placebo count is
**166**, not 168. Placebo standard-expiry share is **19 of 166 (11%)** against
the events' 27 of 84 (32%); the confound in §C is unchanged.
