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
