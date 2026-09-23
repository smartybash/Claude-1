# RP-005 Stage 1 — close auction and time-constrained flow

Descriptive only. **No P&L, no expectancy, no profit factor, no evaluation
simulation.** Data roles frozen before running.

| | |
|---|---|
| Discovery | QQQ 2021-01-04 → 2023-12-31, **688 sessions** |
| Internal validation | QQQ 2024-01-01 → 2025-12-31, **502 sessions** |
| Jan–Aug 2026 | **EXCLUDED — contaminated.** Inside the QQQ discovery set already used by the IB midpoint pullback (1,396 sessions), pre-open conditioning (1,395), trade conditioning and compression families. Not a clean diagnostic period. |
| 2016–2020 | not touched (spent) |
| Sessions dropped | 4, short or incomplete |

**Two specification notes recorded before results.** The state window ends at the
**15:00 bar open** and every reported outcome starts at that same price, so no
part of the classifying return sits inside any headline outcome. And **§8
condition 6 asks for "three of the four discovery years" while §2 sets discovery
at three years** — I did not invent a threshold; every year is reported and kill
condition 6 (concentration in one year) is the operative test.

**The dataset ends at 15:59 and does not contain the 16:00 auction print.** This
tests movement *into* the close, not the auction.

---

## 1. State counts and frequency

| block | state | n | /month | up | dn |
|---|---|---|---|---|---|
| Discovery | LARGE | 228 | **6.71** | 125 | 103 |
| | MEDIUM | 229 | 6.94 | 124 | 105 |
| | SMALL | 231 | 7.00 | 127 | 104 |
| Validation | LARGE | 168 | **7.00** | 82 | 86 |
| | MEDIUM | 164 | 6.83 | 99 | 65 |
| | SMALL | 170 | 7.08 | 90 | 80 |

**Frequency passes comfortably** — 6.7–7.0/month against the 4/month floor. This
is the only pass condition RP-005 meets.

---

## 2. Large versus medium and small

Direction-adjusted, basis points, all measured strictly after 15:00.

| block | state | 15:00→15:30 | **15:00→15:59** | MFE | MAE | RV | close with | new extreme |
|---|---|---|---|---|---|---|---|---|
| **Discovery** | **LARGE** | +7.1 | **+8.4** | 37.8 | 28.2 | 40.5 | 57.0% | 66.2% |
| | MEDIUM | +6.1 | **+7.8** | 34.2 | 25.6 | 35.9 | 61.1% | 48.5% |
| | SMALL | −1.8 | −1.4 | 26.2 | 30.1 | 34.3 | 50.6% | 24.7% |
| **Validation** | **LARGE** | +2.0 | **−0.9** | 30.1 | 34.9 | 35.4 | **49.4%** | 45.2% |
| | MEDIUM | +1.6 | +1.5 | 21.0 | 18.2 | 24.9 | 53.0% | 39.6% |
| | SMALL | +0.3 | −0.9 | 18.8 | 20.2 | 24.8 | 50.0% | 23.5% |

**The magnitude scaling the mechanism requires is absent even in discovery.**
§1 point 1 demands that closing movement *strengthens* with the move already
established by 15:00. LARGE gives **+8.4** against MEDIUM's **+7.8** — a
difference of **+0.56 bps, t = +0.13.** The separation is entirely
LARGE-and-MEDIUM against SMALL, which is a threshold effect, not the monotonic
scaling a size-proportional rebalance predicts.

**Kill condition: the discovery LARGE mean of +8.4 (t = +2.59) is the only
number in this report that would look promotable in isolation.**

---

## 3. Matched-volatility control

| block | | n | 15:00→15:59 | pre-15:00 RV |
|---|---|---|---|---|
| Discovery | LARGE | 228 | **+8.4** | 105.4 bps |
| | MATCHED-RV | 228 | **+4.9** | 104.1 bps |
| Validation | LARGE | 168 | **−0.9** | 98.4 bps |
| | MATCHED-RV | 156 | **+2.9** | 84.0 bps |

Discovery matching is tight (105.4 vs 104.1) and leaves a residual of **+3.5
bps** — about 40% of the raw effect survives, so most of the discovery number
was high-volatility days continuing to move.

**In validation the control beats the state**: −0.9 against +2.9. **Kill
condition 1 is met.** (The validation match is looser, 98.4 vs 84.0 — that
mismatch favours LARGE, and LARGE still loses.)

**Control 2, randomised direction, discovery:** +8.4 as traded against **−8.0**
when the same magnitudes are re-signed at random. A single random re-signing
produces a mean of comparable size to the observed effect. That is the honest
scale of the discovery result.

---

## 4. The 15:00 window versus the 14:00 control

| block | LARGE by 14:00 → 14:00–14:59 | LARGE by 15:00 → 15:00–15:59 |
|---|---|---|
| Discovery | **+4.3** (n=218) | **+8.4** (n=228) |
| Validation | **+0.4** (n=168) | **−0.9** (n=168) |

Discovery satisfies pass condition 4 — the close window is roughly twice the
ordinary earlier hour. But **both windows are positive**, which points at general
intraday continuation on large-move days rather than anything close-specific.

**In validation the ordinary 14:00 hour is stronger than the close hour.**
**Kill condition 3 is met.**

---

## 5. Up versus down sessions

| block | | n | 15:00→15:59 | t |
|---|---|---|---|---|
| Discovery | LARGE-UP | 125 | +6.3 | +1.64 |
| | LARGE-DOWN | 103 | +10.9 | +2.01 |
| Validation | LARGE-UP | 82 | **−5.3** | −0.99 |
| | LARGE-DOWN | 86 | **+3.3** | +0.63 |

Discovery is directionally present both ways (pass condition 5 met). **Validation
splits into opposite signs. Kill condition 2 is met.**

---

## 6. Next-morning behaviour

| block | state | close move | next 09:30–10:00 | retrace ≥50% |
|---|---|---|---|---|
| Discovery | LARGE | +8.4 | **−0.1** | 64.5% |
| | MEDIUM | +7.8 | −6.0 | 62.7% |
| | SMALL | −1.4 | −3.0 | 65.8% |
| Validation | LARGE | −0.9 | −2.6 | 57.7% |

LARGE shows no next-morning continuation, which is *consistent* with mechanical
rather than informational flow — kill condition 7 is **not** met. But the reading
is weak: **MEDIUM reverses more than LARGE (−6.0 vs −0.1)**, which is backwards
for a size-proportional rebalance, and the ≥50% retrace rate is
indistinguishable across all three states (62–66%), i.e. it is what any session
does, not what these sessions do.

---

## 7. Discovery versus validation — the decisive comparison

| | discovery 2021–23 | validation 2024–25 |
|---|---|---|
| LARGE 15:00→15:59 | **+8.38 bps, t = +2.59** | **−0.91 bps, t = −0.24** |
| close in direction | 57.0% | **49.4%** |
| new session extreme after 15:00 | 66.2% | 45.2% |
| LARGE − MEDIUM | +0.56, t = +0.13 | −2.44, t = −0.56 |
| beats matched-RV control | +3.5 | **−3.8** |
| stronger than 14:00 control | yes | **no** |
| up and down same sign | yes | **no** |

By discovery year: **2021 −2.5** (close-with 43.9%), 2022 +15.8 (61.6%),
2023 +9.4 (63.2%). Two of three years, with the first negative.
Validation years: 2024 −2.6, 2025 +0.8 — both flat.

**Kill condition 5 — the discovery effect disappears in validation — is met
unambiguously.**

---

## 8. Calendar diagnostics (never pooled)

| category | discovery n | 15:00→15:59 | next-am | validation n | 15:00→15:59 | next-am |
|---|---|---|---|---|---|---|
| ordinary | 181 | +7.4 | −0.2 | 140 | −0.3 | −4.9 |
| month-end (last 3) | 33 | **+16.1** | −8.1 | 18 | **+0.6** | +1.7 |
| quarter-end (last 3) | 7 | +6.3 | −18.5 | 3 | −4.9 | −3.2 |
| monthly opex | 14 | +2.8 | +19.4 | 10 | −12.1 | +22.6 |
| quarterly opex | 5 | +1.4 | −13.3 | 3 | −22.7 | −17.0 |

Month-end looked like the strongest sub-category in discovery at +16.1 on 33
sessions — **and it collapses to +0.6 in validation.** Quarter-end and expiry
cells hold 3–14 sessions and carry no information. Diagnostics only, as declared.

---

## 9. Commercial interpretation

The forced flow is real. Leveraged and inverse ETF sponsors must rebalance daily,
in the direction of the day's move, near the close, in size proportional to that
move. Nothing in this test disputes that.

**What the test shows is that the flow has no detectable price consequence in
QQQ after 15:00 at one-minute resolution.** The most likely reading is that it is
entirely anticipated: the rebalance is publicly computable from the day's return,
so other participants position ahead of it and absorb it. A forced order that
everyone can calculate in advance is not an edge — it is a schedule.

Three specific failures:

1. **No size scaling.** LARGE minus MEDIUM is +0.56 bps, t = +0.13. A flow whose
   size is proportional to the day's move must produce an effect that grows with
   the day's move. It does not.
2. **Most of the discovery effect is volatility.** Tight RV matching removes 60%
   of it, and the randomised-direction control produces a number of the same
   magnitude.
3. **It does not survive the frozen validation block.** +8.4 → −0.9,
   close-with 57.0% → 49.4%, and up/down sessions split into opposite signs.

**Kill conditions met: 1, 2, 3 and 5.** Pass conditions met: **9 only**
(frequency).

This is the two-stage design doing its job. A discovery-only read — +8.4 bps at
t = +2.59, 57% closing with the move, 66% making a new session extreme, stronger
at the close than at 14:00 — would have looked like a candidate to anyone who
stopped there.

---

## Appendix — formal detail

| block | group | n | mean (bps) | sd | SE | t |
|---|---|---|---|---|---|---|
| Discovery | LARGE | 228 | +8.38 | 48.8 | 3.23 | **+2.59** |
| | LARGE-UP | 125 | +6.28 | — | 3.84 | +1.64 |
| | LARGE-DOWN | 103 | +10.93 | — | 5.44 | +2.01 |
| | LARGE − MEDIUM | — | +0.56 | — | 4.46 | **+0.13** |
| Validation | LARGE | 168 | −0.91 | 49.1 | 3.79 | **−0.24** |
| | LARGE-UP | 82 | −5.35 | — | 5.42 | −0.99 |
| | LARGE-DOWN | 86 | +3.32 | — | 5.29 | +0.63 |
| | LARGE − MEDIUM | — | −2.44 | — | 4.33 | −0.56 |

Matched-RV control: each LARGE session paired without replacement to a non-LARGE
session whose 09:30–15:00 realised volatility lies within ±10%; 228 of 228
matched in discovery, 156 of 168 in validation; seed 20260923.

No multiplicity correction is applied because none is needed to reach the
verdict: the single pre-registered validation test returns t = −0.24.

---

# VERDICT: MECHANISM REJECTED — CLOSE RP-005

No Stage 2 proposal. No data acquisition. No NQ or MNQ history.

RP-003 (cross-sectional relative strength) and RP-004 (intraday lead-lag) remain
unrun and await separate authorisation.
