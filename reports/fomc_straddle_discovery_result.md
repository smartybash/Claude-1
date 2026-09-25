# FOMC event-vol straddle — discovery result

Pre-registered `a971882`, amended `b7becac` and `648b45d`, harness `0114543`.
**2021-01-27 → 2026-07-29. The 2016–2020 block has NOT been opened.**

---

## 1. Counts before performance

| | events | placebos |
|---|---|---|
| in manifest | 45 | 88 |
| priced | **45 of 45** | 88 of 88 |
| **rejected by the 10% cost gate** | **6** | 9 |
| **used** | **39** | **79** |

Two placebos were excluded earlier as market holidays — 2024-06-19 (Juneteenth)
and 2024-12-25 — recorded, not silent.

**The six cost-gate rejections, listed rather than summarised:** 2021-01-27
(12.1%), 2021-04-28 (11.0%), 2024-07-31 (11.1%), 2024-12-18 (19.6%),
2025-05-07 (22.7%), 2026-07-29 (13.4%). All are cheap-premium events where four
half-spreads plus commission breach the declared ceiling. The gate bound exactly
as pre-registered, before any P&L was read.

| | events | placebos |
|---|---|---|
| premium | **2.11% of spot** | 1.82% of spot |
| round-trip cost | 2.57% of premium | 2.69% of premium |
| \|net delta\| at entry | **0.024** | 0.027 |

**The market already charges for the event before any P&L is computed** — FOMC
straddles cost 2.11% of spot against 1.82% on matched placebo Wednesdays, a 16%
premium uplift. Strike selection is genuinely delta-neutral.

---

## 2. The result

σ is estimated **from the placebo sample only**, so the threshold cannot move
with the FOMC mean (declared `648b45d` §D). Realised σ = **0.2817**, well below
the 0.45 assumed in the power table, so the test is *better* powered than
declared: **MDE ±9.02%**, not ±13.4%.

| | value |
|---|---|
| **FOMC mean `r_exec`** (headline) | **−6.89%** of premium |
| FOMC mean `r_mid` (beside) | −4.65% |
| placebo mean | −2.30% (n=79) |
| n | 39 |
| SE | 4.51% |
| **MDE (2 SE)** | **±9.02%** |
| t (unpaired) | **−1.527** |

### Primary estimand, resolved by the pre-declared rule

`ρ(event, its placebo mean)` = **+0.288**, above the 0.25 threshold fixed in
advance, so **the paired difference is primary**:

| | value |
|---|---|
| **paired difference** | **−3.54%** of premium |
| SE | 4.08% |
| **t** | **−0.868** |
| n | 37 |

`r_mid` at −4.65% against `r_exec` at −6.89% says the spread assumption
contributes about 2.2 points — real, but not the result.

---

## 3. Verdict, by the rule fixed before the run

The declared decision table:

| result | verdict |
|---|---|
| mean ≥ +MDE, OOS sign agrees | Candidate — forward collection only |
| 0 < mean < MDE | Unresolvable. Close. |
| **mean ≤ 0** | **Null. Close the family, and with it the programme per §5.** |
| mean ≤ −MDE | "Event premium is rich" — a finding, not acted on |

Primary (paired) **−3.54%**; headline (unpaired) **−6.89%**. Both negative;
neither reaches −MDE.

# NULL

**The long FOMC straddle does not pay.** The sign is exactly what §3 of the
pre-registration predicted from the desk's own §0 test: for a scheduled-event
straddle there is no answer to *who is on the other side and why do they keep
losing*, because the buyer is the one who loses. The 3.14× realised-vol
expansion is real and it is already in the price.

The result is not negative *enough* to claim the seller's side decisively
(−3.54% and −6.89% are both inside −MDE = −9.02%), and per §3 that finding would
not be acted on here in any case.

---

## 4. Diagnostics — declared, none promotion-relevant

| diagnostic | value |
|---|---|
| **quarterly (promotion gate)** | −11.64% (n=14) vs non-quarterly −4.23% (n=25); difference **−7.41% vs MDE 9.02% → gate not triggered** |
| DTE 2 / DTE 1 | −7.71% (n=37) / +8.38% (n=2) — n=2 carries nothing |
| **excluding the disclosed 2024-09-18 probe** | **−6.44% (n=38)** — the probe is not driving the result |
| concentration `max(10,⌈0.10n⌉)` = 10 each tail | **−10.34%** — trimming makes it *more* negative |
| top-5 removed / bottom-5 removed | −12.67% / −2.81% |
| win rate | **35.9%** |
| best / worst event | +45.8% / −37.1% |
| by year | 2021 −8.8% · 2022 +1.2% · 2023 −4.0% · **2024 +0.6%** · 2025 −18.4% · 2026 −17.1% |
| IV, entry → exit (diagnostic only) | 0.2944 → 0.2757 |

Two observations worth recording:

1. **The negative is not a tail artefact.** Removing ten trades from each tail
   moves the mean from −6.89% to −10.34%. The losses are broad, not concentrated.
2. **The IV crush is small** — 29.44% to 27.57%, under two vol points on
   average. The loss is not mainly vol collapse; it is theta plus spread against
   a move that is usually too small. That is the efficiency wedge of §5 showing
   up in options: the session's *size* expands as promised, and the straddle is
   paid on *net displacement*, which does not.

---

## 5. The out-of-sample block must NOT be opened, and the reason is arithmetic

The two-stage rule declared in `a971882`:

> Promotion requires the pooled n≈84 estimate to clear MDE **and** the OOS block
> to share the sign of discovery.

Discovery is negative. Therefore:

- If OOS is **negative**, it shares the sign — but the pooled estimate is then
  negative too and cannot clear +MDE.
- If OOS is **positive**, the pooled estimate might rise — but it no longer
  shares discovery's sign.

**Promotion is impossible for every possible OOS outcome.** Reading 2016–2020
cannot change the verdict; it can only sharpen the size of a negative we have
already agreed not to act on.

The grant was made to resolve the question. **The question is resolved.**
Spending the last clean out-of-sample block to add precision to a decision that
is already fixed is the exact waste the desk's discipline exists to prevent.

**Recommendation: close the family on discovery and leave 2016–2020 unread.**

---

## 6. What this costs in economic terms

At −6.89% of a premium worth 2.11% of spot, the unpaired estimate is **−0.145%
of spot per event**, or about **−1.16% of spot per year** at 8 events. On the
paired estimate, −0.075% per event and **−0.60% per year**. Both are losses a
retail desk would actually incur, not rounding.

---

Reproduce: `python3 scripts/orderflow/fomc_straddle.py run --block discovery`.
Per-event rows `data/events/fomc_straddle_events.parquet`.
