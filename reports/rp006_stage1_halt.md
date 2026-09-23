# RP-006 Stage 1 — HALTED: the specification is defective, the run is invalid

Discovery 2021-2022 was executed and **its output must not be read as a discovery
result.** Three defects, two of them mine. 2023 and 2024–2025 were **not read**.

---

## 1. The frozen 380-bar filter is an IJH liquidity filter, and it destroys the block

| instrument | bars in 2021–22 | median bars/session | sessions below 380 |
|---|---|---|---|
| QQQ | 195,972 | **390** | **3** |
| SPY | 196,046 | **390** | **2** |
| IWM | 195,937 | **390** | **3** |
| **IJH** | **188,197** | **374** | **292 of 503** |

**IJH does not print in roughly 16 minutes of a typical session.** It is the
thinnest of the four. Applied to the 4-way intersection, the ≥380-aligned-bar
rule therefore drops **292 of 503 sessions (58%)** — and it is dropping them for
IJH's trade frequency, not for any data defect.

| | 2021 | 2022 |
|---|---|---|
| sessions in block | 252 | 251 |
| **passing the 380-bar filter** | **79** | **132** |
| surviving the 20+60 session warm-up | **0** | **129** |

**The 79 surviving 2021 sessions were consumed entirely by the beta and
dispersion warm-up. Every usable session in the run is in 2022.**

Pass condition 5 — *the result appears in both 2021 and 2022* — is therefore
**unachievable by construction**. The specification cannot pass its own gate.

### Why the filter is the wrong instrument here

I imported the ≥380-bar rule from RP-003 and RP-004, where the **entire
one-minute return series** was the object of study and completeness genuinely
mattered. RP-006 needs **six timestamps**: 09:30, 10:00, 10:30, 11:00, 12:00 and
the close.

Those timestamps are fine. From the approved inventory, **IJH's 10:00 print
equals its 09:59 print on only 1.22% of sessions** — comparable to QQQ (1.00%),
SPY (1.39%) and IWM (1.59%), and nothing like EFA's 9.16%. IJH's missing bars are
scattered minutes that the design never reads.

**The filter rejects 58% of sessions for a reason with no bearing on the
measurement.** That is my specification error, carried in from two families where
it was correct.

---

## 2. The >60% rank-domination threshold cannot be satisfied by a 3-instrument ranking

The run flagged QQQ at **86.8% "either extreme"** and printed the mechanical-
domination warning.

But with three instruments, **every session places one instrument strongest and
one weakest — two of three are at an extreme.** By symmetry the expected "either
extreme" rate is **66.7% for every instrument**. The 60% threshold sits *below*
the structural floor, so **the flag fires unconditionally regardless of the
data.**

Observed against that 66.7% baseline:

| instrument | strongest | weakest | either extreme | vs 66.7% baseline |
|---|---|---|---|---|
| **QQQ** | 41.1% | 45.7% | **86.8%** | **+20.1 pts — genuine over-representation** |
| IWM | 29.5% | 30.2% | 59.7% | −7.0 pts |
| IJH | 29.5% | 24.0% | 53.5% | −13.2 pts |

So there **is** a real finding buried here — QQQ sits at an extreme far more than
chance, i.e. it is the high-beta-residual name and the cross-section is largely
"QQQ versus one of the others". But the *test as written* could not have told us
that. The threshold needs restating as a deviation from the structural baseline,
not an absolute percentage.

---

## 3. Two controls were implemented incorrectly — their output is void

**Shuffled-rankings control.** I permuted the *outcome* columns across rows while
keeping the same row set. Permuting a column and then taking its mean returns the
identical mean, which is why the control printed values **identical to the true
ranking to two decimals** at every horizon. It tested nothing. The correct
construction takes the (strongest, weakest) *identity* from a randomly chosen
other date and applies it to this date's forward returns.

**Random-pair control.** I recorded a value only when the randomly drawn pair
happened to coincide with the realised pair, collapsing n from 129 to 34–45. The
correct construction computes the spread for the random pair on every date,
using that date's forward returns for those two instruments.

Both require storing forward returns for **all three** instruments per session,
which the current harness does not do.

---

## 4. Disclosure — what I saw before halting

I have seen the invalid run's output and must record it, because it bears on any
corrected re-run.

On the 129 surviving 2022-only sessions, the long-strongest / short-weakest
spread was **negative at every horizon**: −3.94 bps at 30 minutes, −2.92 at 60,
−3.79 at 120, **−8.57 at the cash close** (t = −1.53, −0.89, −0.90, −1.77).
Positive-continuation rate 47–52%. HIGH dispersion was **worse** than ORDINARY
(−20.29 vs −2.91 at the close).

**That is reversal, not persistence — the direction of kill condition 1.** It is
on a 2022-only subsample with two broken controls and cannot stand as a result,
but I now hold prior directional knowledge about this block and a corrected
re-run is no longer blind to it.

---

## 5. What I am not doing

I am **not** re-running with a relaxed filter. Changing a frozen specification
after seeing its output is the single failure this desk's process exists to
prevent, and the fact that the change would be *justified on its merits* is
exactly what makes it dangerous.

I am **not** reporting the 2022-only numbers as a discovery result.

I am **not** opening 2023 or 2024–2025.

---

## 6. Recommended correction, for approval before any re-run

| item | current (defective) | proposed |
|---|---|---|
| Session filter | ≥380 aligned bars across all 4 instruments | **All six required timestamps present for all four instruments** (09:30, 10:00, 10:30, 11:00, 12:00, last bar), plus ≥300 bars for the beta estimation series **per instrument pairwise against SPY**, not on the 4-way join |
| Rank-domination test | ">60% at either extreme" | **Deviation from the 66.7% structural baseline**; flag at >80% or <53% |
| Shuffled control | permuted outcome columns | **permute the (strong, weak) identity across dates**, apply to each date's own forward returns |
| Random-pair control | counted only on coincidence | **compute for the drawn pair on every date** |
| Everything else | — | **unchanged**: factor, universe, beta method, formation window, dispersion terciles, horizons, cost hurdles |

Expected effect: ~500 usable sessions instead of 211, both discovery years
populated, and the warm-up no longer consuming the whole of 2021.

**Any re-run must be recorded as contaminated by §4** — I have seen a negative
2022 result and cannot un-see it. If you prefer a clean test, the alternative is
to close RP-006 here and rebuild the hypothesis on an untouched block.

---

# VERDICT: CROSS-SECTIONAL MOMENTUM UNCLEAR — STOP

Stopped on a defective specification, not on evidence. The hypothesis has not
been tested. 2023 and 2024–2025 remain unread.
