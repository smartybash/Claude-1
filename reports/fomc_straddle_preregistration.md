# FOMC event-vol straddle — pre-registered

**A new instrument class.** Every prior family in this ledger is a directional
barrier trade on a normalised R scale. This is not one. It is the first test in
the project that does not divide session magnitude out.

**Nothing from any closed family is reused.** No shared parameter, no shared
signal, no shared mechanism. The FOMC volatility result (post/pre realised-vol
ratio 3.14×, 6 of 6 years) is the *motivation* for looking here. It is **not**
evidence for this hypothesis — see §3.

---

## 1. Standing constraints, recorded so they cannot be quietly revisited

The 2016–2020 block is granted for this test. The §0 clause that governs it:

> re-using it for anything else costs us the last clean out-of-sample block

Granting it spends that block. The binding ruling, verbatim:

> **After this test, no future family uses 2016–2020 as OOS.**

The grant is narrow and its reasoning is on record: the FOMC straddle shares no
parameter, no signal and no mechanism with the IB midpoint pullback family. It
shares only the calendar window, **and the window is not the asset.** The
standing prohibition on that family is untouched: no rescaling, refitting,
filtering, reversing or reinterpreting it, and 2016–2020 is not reused as a
holdout for any derivative of it.

### Scope of the NQ tape seal

The sealed prefixes `202606*` and `20260723` are **instrument-specific: they
seal the NQ tick tape.** They do not seal QQQ bars or QQQ options. QQQ June 2026
bars are already part of the discovery set and have been used throughout.
Reading 2026-06-17 option chains touches no sealed NQ data. **2026-06-17 is
included**, by ruling, and this note fixes the seal's boundary on the record.

---

## 2. Why this family exists

§3.5 of the project ledger, stated as a prescription rather than a diagnosis:

> The predictable component of a session is its size — and size is exactly what
> R-normalisation divides out.

Across 300+ pre-registered tests, the ratio of net displacement to path length
has not conditioned on anything observable in advance. That is the structural
reason the programme has returned nulls. Magnitude without direction is a
long-volatility position. Futures cannot express one. A straddle can.

---

## 3. The prior is against this trade, and that is stated before running

The 3.14× FOMC figure is **realised-to-realised**. It says volatility *arrives*.
It says nothing about whether volatility is *priced*. FOMC is the most
calendared event in the market.

Apply the §0 test — who is on the other side, and why do they keep losing?
**For a long scheduled-event straddle there is no answer.** The a priori losing
side is the buyer; the seller harvests the event premium. Converting "vol
arrives" into "buy vol" does not survive our own methodology.

Consequence, fixed now:

- **Measurement is two-sided.** We estimate the sign of the mispricing.
- **Promotion is one-sided.** Only a positive result can become a candidate.
- A significantly *negative* result is recorded as "event premium is rich, the
  seller's side" and is **a finding, not a strategy.** It is not acted on and
  not promoted in this test. Short 0DTE-adjacent straddle risk is unbounded and
  has an entirely different capacity and risk profile; it would require its own
  pre-registration. **Controls and inverted results are never promoted.**

---

## 4. Instrument specification — one grid point

| | |
|---|---|
| Underlying | QQQ |
| Contract | ATM **straddle**, expiry = **Friday of the FOMC week** |
| Strike | Single strike nearest the Tuesday close (ties → higher strike) |
| Entry | **Tuesday close (T−1)**, EOD chain. DTE = 3. |
| Exit | **Wednesday close (T)**, EOD chain, same two contracts. DTE = 2. |
| Holding | One day, spanning the 14:00 ET announcement and the post-announcement IV crush |
| Grid | **One point.** No strike grid, no DTE grid, no entry-time grid, no moneyness tilt. |

### Why this construction and not the one originally proposed

The original proposal — 0DTE straddle marked at 13:55 ET — is **unimplementable
and would have been inverted**:

1. `HISTORICAL_OPTIONS` returns **one end-of-day snapshot per date**. No 13:55
   mark exists or is obtainable. The 2024-09-18 chain is the *expiry* snapshot:
   every put below 472 is bid 0.00 / ask 0.01. Using it as a "pre-announcement"
   IV would read the mark after the vol had realised and crushed.
2. **QQQ had no Wednesday expiry before ~Sept 2022** (`date=2021-03-16,
   expiration=2021-03-17` returns empty). 0DTE-on-FOMC-day does not exist for
   the first 14 events. Real n on that spec is ~32, not 48.

Tuesday-close entry reads the T−1 chain, so the crushed expiry-day quotes are
never the mark. Verified on a live event in §10.

---

## 5. Estimand — the tradeable quantity, not the variance

**RV/IV and straddle P&L are different trades.** RV/IV compares realised
*variance* (path length) to implied. An unhedged straddle pays **|S_T − K|**
(net displacement). The wedge between them **is the efficiency ratio** — the
quantity §3.5 identifies as the unforecastable part.

A retail desk cannot close that wedge: delta-hedging a 1-day QQQ straddle needs
several share round-trips, each a full round trip in cost, breaching the
10%-of-premium gate before the second rebalance. Testing RV/IV would answer a
question about a position we cannot hold.

**Primary estimand, per event, as a fraction of entry premium:**

```
P_entry_mid = mark_call(T-1) + mark_put(T-1)
P_exit_mid  = mark_call(T)   + mark_put(T)

r_mid  = (P_exit_mid - P_entry_mid - commission) / P_entry_mid
r_exec = ([bid_call(T)+bid_put(T)] - [ask_call(T-1)+ask_put(T-1)] - commission)
         / P_entry_mid
```

**`r_exec` is the headline.** `r_mid` is reported alongside, mirroring the
honest-fill / naive-fill discipline used throughout the bar work, so it is
visible whether the spread assumption is doing the work.

**RV/IV is computed and reported per event as a diagnostic and is excluded from
every decision rule.** If RV/IV > 1 while `r_exec` < 0, that is §3.5 confirmed
in a new instrument class — a publishable null, not a wasted run.

---

## 6. Controls — matched placebo Wednesdays

"Any non-FOMC Wednesday" controls for generic 1-day straddle P&L but not for
week-of-month, month-of-quarter, or FOMC-adjacent term-structure effects.

**Primary control: the Wednesday exactly one week before and one week after each
FOMC date** — same week-of-month, approximately the same IV regime. Two placebos
per event, identical construction throughout.

**Secondary (robustness, pre-declared, excluded from promotion): ±2 weeks**,
which brings the control set to ~4 per event. It is listed separately because
±2 weeks breaks the week-of-month match that motivates the primary control.
Reporting both resolves the stated rule and the stated count without creating a
search.

**Placebo exclusions:** any placebo Wednesday that is a market holiday, is
itself an FOMC date, or lacks a valid same-week Friday expiry. Adjacent FOMC
meetings are ≥5 weeks apart, so ±1 week never collides.

### Which estimate is primary — declared before results

Pairing helps only if event and placebo P&L are positively correlated. With
`Var(X − Ȳ) = σ²(1.5 − 2ρ)` for two placebos, pairing beats the unpaired mean
only for **ρ > 0.25**.

> **If the realised ρ between each FOMC event and its placebo mean exceeds 0.25,
> the paired difference is primary. Otherwise the unpaired FOMC mean is
> primary.** Both are reported either way.

ρ is a nuisance parameter independent of the mean effect, so fixing this
threshold in advance is not adaptive selection on the result.

---

## 7. Cost model — measured, not assumed

| | |
|---|---|
| Spread | Taken from the actual bid/ask on each leg on each date |
| Commission | **$0.65 per contract per leg**, 4 legs = $2.60 per straddle = $0.026/share |
| Gate | **Round-trip cost > 10% of entry premium → event rejected before its P&L is computed.** Rejected count reported. |

Measured on the §10 probe: 4 half-spreads = $0.08/share + $0.026 commission on a
$9.51 premium = **1.11% of premium**. The earlier 2016 probe implies ~4% in the
thinner era. The gate is applied **per event**, not on an average.

---

## 8. Power and the promotion rule — stated before results

Per-event P&L standard deviation for a one-day hold is assumed **σ ≈ 0.45** of
premium. **σ is estimated from the placebo sample only**, never from the FOMC
sample, so the threshold cannot move with the result.

| block | FOMC n | estimator | SE | **MDE (2 SE)** |
|---|---|---|---|---|
| discovery 2021–2026 | 45 | unpaired | 6.7% | **±13.4%** |
| discovery 2021–2026 | 45 | paired, ρ=0 | 8.2% | ±16.4% |
| discovery 2021–2026 | 45 | paired, ρ=0.3 | 6.4% | ±12.7% |
| pooled with 2016–2020 | 84 | unpaired | 4.9% | **±9.8%** |
| pooled with 2016–2020 | 84 | paired, ρ=0.3 | 4.6% | ±9.3% |

Add the ~1–4% cost hurdle. **At n=45 an edge is only claimable at roughly ≥16%
of premium. Measured event-vol premia sit at 5–15%.** The discovery block alone
cannot resolve a normal-sized mispricing. That is stated now, not discovered
later, and it is why the OOS block was granted.

### Two-stage structure

1. **Discovery** — 2021–2026, n = 45. Reported and committed first.
2. **Out-of-sample** — 2016–2020, n ≈ 39. **Read once**, after the discovery
   result is committed. No interim yearly reporting.

**Promotion requires the pooled n≈84 estimate to clear MDE *and* the OOS block
to share the sign of discovery.** This uses the granted power while preserving a
genuine out-of-sample check. §5 of the ledger is explicit that in-sample control
behaviour did not predict out-of-sample survival for the IB midpoint pullback
family; a single pooled run would have no out-of-sample component at all.

### Decision rule, one-sided

| result | verdict |
|---|---|
| mean **≥ +MDE**, OOS sign agrees | **Candidate — forward collection only.** Needs an options fill model, an IV feed, and an execution study before any capital. |
| **0 < mean < MDE** | **Unresolvable. Close.** No rescue. |
| mean **≤ 0** | **Null. Close the family, and with it the programme** per §5. |
| mean **≤ −MDE** | Recorded as "event premium is rich." A finding for a possible future pre-registration. **Not acted on here.** |

**No third arm. No strangle rescue, no delta overlay, no VIX filter, no skew
tilt, no moneyness search, no "if VIX is high also…".** If this is null it is
null.

---

## 9. Event set, sourcing and declared exclusions

`data/events/fomc.csv` contains **45 events in 2021-01-27 → 2026-07-29 and no
pre-2021 dates.** The 2016–2020 dates must be sourced and are **not** hard-coded
from recall.

**Verification gate, before any P&L is computed:** every date must be a
Wednesday, must be a valid QQQ session, and the count must be 8 per year.
Deviations are enumerated in the report, not silently dropped.

### Declared in advance

- **The March 2020 scheduled meeting is excluded.** The Mar 17–18 meeting was
  cancelled; the action was the emergency cut announced Sunday 2020-03-15,
  outside market hours. There is no Tuesday-close → Wednesday-close straddle for
  it. **2020 therefore has 7 events, and OOS n ≈ 39.**
- **Unscheduled/inter-meeting actions are out of scope** (including 2020-03-03
  and 2020-03-15). This pre-registration covers scheduled meetings only.
- **If the same-week Friday is a market holiday**, use the Thursday expiry if
  one exists, else exclude the event and record it.
- **March/June/September/December FOMC meetings fall systematically in quarterly
  expiry week** (e.g. 2024-09-18 → 2024-09-20 is the September quarterly).
  Those straddles are quarterly contracts and the ±1-week placebos are not.
  **The quarterly / non-quarterly split is reported as a diagnostic and is
  excluded from promotion**, on the same footing as the concentration
  diagnostic. It is not a decision arm and must not become a subset search.
- **No winsorising.** COVID-era 2020 events are extreme in both the event and
  placebo sets. Top-5 and `max(10, ⌈0.10n⌉)` concentration are **reported as
  diagnostics** for both sets, consistent with the standing rule's demotion to a
  reported diagnostic. Concentration is not a promotion gate here.

---

## 10. Plumbing probe — disclosed, not hidden

The T−1 construction was verified on one live event **before this document was
frozen**, and its value is disclosed rather than concealed. It is n = 1 of ~84,
it is **not evidence**, and **2024-09-18 remains in the sample** — excluding a
looked-at event would be worse than disclosing it.

QQQ Tuesday 2024-09-17 close **473.51** → strike **474**, expiry 2024-09-20.

| | call 474 | put 474 | straddle |
|---|---|---|---|
| entry Tue 09-17 | 4.72 / 4.75, IV 28.80%, Δ +0.4955 | 4.76 / 4.79, IV 26.85%, Δ −0.5056 | mid **9.51** = 2.008% of spot, net Δ **−0.011** |
| exit Wed 09-18 | 3.07 / 3.09, IV 29.78% | 4.22 / 4.30, IV 21.00% | mid **7.34** |

`r_mid` = (7.34 − 9.51 − 0.026) / 9.51 = **−23.1%**.
`r_exec` = (7.29 − 9.54 − 0.026) / 9.51 = **−23.9%**.

Confirms: live two-sided quotes on the T−1 chain, a genuinely delta-neutral
strike selection (net Δ −0.011), no crushed 0.00/0.01 marks, and a measured cost
of 1.11% of premium against the 10% gate.

---

## 11. Fill and causality integrity

Entry uses only the T−1 chain · exit uses only the T chain · the same two
contract IDs at entry and exit, asserted · executable prices cross the spread in
the adverse direction on both sides · mid-quote performance reported beside ·
commission applied to all four legs · **zero lookahead**, asserted.

---

Committed before `scripts/orderflow/fomc_straddle.py` was written or run.
