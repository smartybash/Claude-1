# Three mechanism-first proposals that do not depend on the NQ tape

Prepared while RP-011 waits for forward data. **None has been run.** No
performance, expectancy, profit factor or drawdown appears here. Each is a
proposal only and requires separate approval before Stage 1.

## Data actually on disk, measured

| set | coverage | sessions |
|---|---|---|
| QQQ 1-minute RTH | 2021-01-04 → 2026-08-31 | 1,421 |
| SPY / IWM / IJH / EFA 1-minute RTH | 2021-01-04 → 2025-12-31 | 1,255 each |
| **five-way aligned intersection** | **2021-01-04 → 2025-12-31** | **1,255** (252/251/250/252/250 by year) |
| QQQ 1-minute including ETH | 2021 → 2026-08-31 | 1,399 |
| QQQ 1-minute 2016–2020 | **spent as OOS** — standing rule, not reusable | 1,259 |
| QQQ / SPY daily | 1999-11-01 → 2026-09-11 | 6,756 |
| **QQQ / SPY daily before 2016** | **never read by any family in this project** | **4,068** |
| sector basket daily (SPY + 9 XL*) | 2021-08-13 → 2026-08-11 | 1,253 |
| FOMC calendar | 2021-01-27 → 2026-12-09 | **48 events**, 45 with QQQ 1-minute |
| NQ / ES bar history | `NQ_5min.parquet` is 2,174 rows with unparsed 1970 timestamps; `intraday_nq/` holds one recent CSV | **effectively none** |

### One constraint that applies to all three

**None of these can validate an MNQ deployment.** Your own standing rule from
RP-007 — *"QQQ may screen the architecture but cannot validate an MNQ
deployment"* — binds here, and the NQ bar archive is empty, so there is no
instrument-native confirmation path for any ETF-screened family today.

**This is a much smaller acquisition than RP-011's.** RP-011 needs true-tick
tape with aggressor labels, recorded live, at ~2.4 months minimum. A confirmation
path for these three needs only **NQ 1-minute bars, 2021–2026**, which is a
historical download rather than a live recording. I recommend acquiring it
regardless of which proposal is approved.

### Data-role conflicts, declared up front

- **2016–2020 is spent as OOS** and is not proposed as OOS anywhere below.
- **2023 was opened by RP-006B** (cross-sectional ranking) and is treated as
  examined, not clean.
- **2021–2022 is examined** by several closed families.
- **2024–2025 (502 sessions) is unread** and is the only genuinely untouched
  intraday block. It is proposed as final OOS in exactly one place, because it
  can only be spent once.
- **Pre-2016 daily (4,068 sessions) is unread** by any family here.

---

# Proposal A — Intraday relative volume and price-impact persistence

## Mechanism

RP-010's one positive finding: **scale variables carried forward information and
the ratio built from them did not.** Top-decile delta (+16.024), price progress
(+14.679) and total volume (+16.030) each returned ≈ +15 NQ points at 900 s,
while impact alone returned +3.112.

The economic claim is not about footprints. It is that **an unusual quantity of
trading is itself informative**, because a participant who must transact size
cannot finish in one window, and the remainder of that requirement is
mechanically still to come. The testable consequence: **relative volume should
persist, and its persistence should be measurable in price continuation.**

This is a *liquidity-demand* mechanism, not an order-flow-reading one. It is
testable on 1-minute bars without aggressor labels, which is why it does not need
the tape.

## Construction (to be frozen if approved)

- **Relative volume** at minute *m*: that minute's volume divided by the median
  volume at the same clock minute over the trailing 20 sessions — causal,
  block-free, and immune to the pooled-threshold defect that broke RP-010's
  opening block because it compares each minute against **itself**.
- **Event**: relative volume ≥ trailing p95, with a 15-minute cooldown, capped at
  two per time block per session with the ⅓-block separation rule from RP-011.
- **Persistence**: does relative volume at *m* predict relative volume at
  *m+5 … m+30*?
- **Impact persistence**: does the signed price move per unit of relative volume
  persist, or mean-revert?
- **Cross-sectional arm**: does an unusual-volume event in SPY predict
  continuation in QQQ, IWM, IJH — the only part that needs five instruments.

## Data roles

| role | block | sessions |
|---|---|---|
| discovery | 2021–2022 (examined; declared) | 503 |
| internal validation | 2023 (opened by RP-006B; semi-spent, declared) | 250 |
| **final out-of-sample** | **2024–2025, unread** | **502** |
| forward | 2026 QQQ only until the others are extended | 165 |

## Expected frequency

At p95 relative volume with a 15-minute cooldown and two per block, roughly
**6–8 events/session** before any confirmation filter, on 1,255 aligned
sessions — of the order of **7,500–10,000 discovery events** and **3,000–4,000**
in the untouched OOS block. Frequency is not a constraint. *(Order-of-magnitude
from the construction, not a measurement; the exact count is a Stage 0 output.)*

## Cost and risk feasibility

QQQ round turn at `COST_F = 2.00/30000` = **0.667 bps**; measured ATR₁ₘ on QQQ
is **6.19 bps** (RP-009), so one ATR₁ₘ of movement carries a **10.8%** cost
burden — at the edge of the 10% gate and **failing it**, exactly as RP-009 found.
The family therefore must demonstrate movement of **at least 1.5 × ATR₁ₘ** to be
commercially interesting, and that threshold is declared now.

## Falsification control

The control that killed RP-010 is the primary control here: **matched random
times inside the same session**, matched on time of day and on realised
volatility. Plus: shuffled relative-volume labels; same absolute volume without
the *relative* elevation (which separates "busy stock" from "busy moment"); and
the opposite-direction arm.

## Prop-evaluation compatibility

Deployable instrument is MNQ/MES, not the ETFs. **Screen only** until NQ bars
exist. The 40%-consistency rule maps directly onto the best-three-sessions test
already in the platform.

## What would kill it

Relative volume persists but carries no price information; the cross-sectional
arm is explained by index membership; matched random times reproduce it;
continuation is below 1.5 × ATR₁ₘ.

---

# Proposal B — Opening-gap behaviour conditioned on confirmed public information

## Mechanism

A scheduled macro release is **genuinely exogenous**: it arrives at a known
instant, it is not selected by the market, and its existence is verifiable from a
public calendar. That makes it the cleanest identification available to this
project — every family closed so far has failed because its condition was
endogenous to price. If the overnight gap that follows a confirmed release
behaves differently from an unconditional gap, the difference is attributable to
information rather than to selection.

## The frequency problem, stated before anything else

**The only verifiable calendar on disk is `data/events/fomc.csv`: 48 events,
45 with QQQ 1-minute data.** Forty-five independent days cannot support 150
untouched frozen-rule trades. Multiplying across five ETFs does not help: the
same 48 days, and the session is the independence unit.

**This proposal is blocked until a macro-release calendar is acquired and
provenance-verified.** FOMC + CPI + NFP is roughly 36 releases/year; 2021–2025
would give ~180 events, which reaches the 150-trade floor with nothing spare. The
acquisition is small — a few hundred dated rows — but it must carry verifiable
provenance, and the FOMC weekday defect already in the ledger (three of 84 events
are Thursdays, not Wednesdays) is the reason every date must be checked rather
than generated from a rule.

## Construction (if the calendar is acquired)

Gap = open/prior close − 1, direction-adjusted by the sign of the release
surprise where a surprise is available and unsigned where it is not. Outcomes:
gap fill within 5/15/30/60 minutes; continuation at the same horizons; range
expansion against the trailing 20-session norm. Controls: matched non-event days
by weekday, month and trailing volatility; the day *before* each release, which
shares the calendar position but not the information.

## Data roles

Discovery 2021–2023; internal validation 2024; **final OOS 2025 plus forward**.
Deliberately does not touch 2024–2025 as a pair, so Proposal A can keep it.

## Cost and risk feasibility

A gap trade is a single entry at or after the open; cost is one round turn
against a move that is typically several ATR₁ₘ on a release day, so the cost
burden is structurally the most favourable of the three. That is the main
attraction.

## Falsification control

The day-before control is the strong one: same calendar slot, no information. If
it reproduces the effect, the effect is calendar seasonality, not news.

## What would kill it

The day-before control reproduces it; the effect exists only for FOMC and not for
CPI/NFP; gaps fill at the unconditional rate; fewer than 150 events after quality
filtering.

---

# Proposal C — Multi-day swing and overnight-hold outside the closed intraday families

## Mechanism

Every family closed in this project is intraday and directional, and the
recurring reason for failure has been that **costs are large relative to the move
available inside a session**. A multi-day hold inverts that ratio: the same 2-point
round turn is amortised over a move measured in ATRs rather than in fractions of
one. The mechanism to test is not a new signal but a **horizon**: whether
displacement that is not forecastable at one hour becomes forecastable at three
to ten days.

This is also the one proposal with genuinely deep untouched data: **4,068 QQQ/SPY
daily sessions before 2016 have never been read by any family here.**

## A standing instruction that needs your ruling

You have instructed repeatedly: **"Do not use overnight variables."** That
instruction was issued as a condition of the *intraday NQ* families (RP-008,
RP-009, RP-010), where an overnight variable would have been a look-ahead-prone
predictor of an intraday outcome.

In a multi-day family the overnight move is **the outcome**, not a predictor.
I am proposing it under that reading and flagging it rather than assuming: if
the instruction is meant to be absolute, Proposal C reduces to a close-to-close
family and the overnight decomposition is dropped. **That choice does not block
the rest of the proposal.**

Separately, and regardless: **RP-002's two-bar overnight cleaning estimator must
not be reused** (ledger entry 3 — it altered 98.1% of sessions and cut the mean
overnight range 22%). A magnitude-based bad-print test replaces it.

## Construction

Signals restricted to ones unavailable to the closed intraday families:
multi-day displacement relative to trailing realised volatility; the sector
dispersion of the ten-name basket; and the daily efficiency ratio, which this
project has already established as its central finding at session scale
(*magnitude is forecastable, directness is not*) and which has never been tested
at multi-day scale. Horizons 3, 5 and 10 sessions. Barrier geometry reused from
RP-009 so the driftless identity `P(+MR before −1R) = 1/(1+M)` remains the
benchmark.

## Data roles

| role | block | sessions |
|---|---|---|
| discovery | **1999–2015 daily, unread** | 4,068 |
| internal validation | 2016–2020 daily | 1,259 |
| final out-of-sample | 2021–2026 daily | 1,429 |

Note 2016–2020 is spent as *intraday* OOS; using it as daily **internal
validation** is a different resolution and a different family, and it is proposed
as validation rather than as final OOS for exactly that reason. If you read the
standing rule as covering all resolutions, discovery becomes 1999–2012 and
validation 2013–2015.

## Cost and risk feasibility

**The strongest of the three.** At a 5-day horizon QQQ moves several percent
against a 0.667 bps round turn — a cost burden under 1%, against 10.8% for
Proposal A. Overnight gap risk replaces intraday cost as the binding constraint,
which is a different and more tractable problem.

## Prop-evaluation compatibility

**This is the proposal's weakness.** A $50,000 evaluation with a $2,000 trailing
drawdown and a $1,000 daily loss limit is hostile to multi-day holds: an
overnight gap can breach the daily limit with no opportunity to act, and a 10-day
hold consumes the 10-day minimum-trading-day requirement with a single position.
Any Stage 2 would need position sizing derived from the gap distribution, not
from intraday ATR.

## What would kill it

Multi-day continuation is present pre-2016 and absent after; the effect is a
proxy for the index's secular drift and disappears against a
buy-and-hold benchmark; gap risk makes the drawdown shape incompatible with the
evaluation at any size that clears costs.

---

# Comparative ranking

| | **A — relative volume** | **B — event gaps** | **C — multi-day swing** |
|---|---|---|---|
| mechanism strength | strong — the one thing RP-010 established | **strongest** — exogenous information | weak — a horizon, not a signal |
| data available **today** | **yes**, 1,255 aligned sessions | **no** — 45 usable events | **yes**, 4,068 unread sessions |
| untouched OOS path | yes — 502 sessions | yes, after acquisition | yes — 1,429 sessions |
| cost burden | **10.8% — fails the 10% gate at 1 ATR₁ₘ** | low | **lowest, under 1%** |
| frequency | very high | **marginal — ~180 events total** | moderate |
| prop-evaluation fit | screen only, needs NQ bars | screen only, needs NQ bars | **poor — gap risk vs a $1,000 daily limit** |
| falsification control | matched random times (the control that killed RP-010) | day-before-release — the cleanest available | barrier identity benchmark |
| blocking dependency | none | **a verified macro calendar** | your ruling on overnight variables |

## Recommended priority: **Proposal A**

Three reasons, in the order a desk would weigh them.

**Economics first.** A is the only proposal whose mechanism this project has
already observed rather than assumed. RP-010's load-bearing table is a positive
result pointing at scale variables, on 1,900 windows, and it has never been
tested as a hypothesis in its own right. B's mechanism is better identified but
entirely untested here; C's is a horizon argument, not a mechanism.

**Cost and capacity second.** A's 10.8% cost burden at one ATR₁ₘ is a real
problem and I am not hiding it — it is the same arithmetic that failed RP-009's
gate. But it is a *threshold* problem with a stated remedy (require 1.5 × ATR₁ₘ),
whereas B's frequency ceiling of ~180 lifetime events is a *structural* one, and
C's incompatibility with a $2,000 trailing drawdown is structural too.

**Statistics last, as it should be.** A can run today on 1,255 aligned sessions
with 502 genuinely unread sessions held back. B cannot run at all until a
calendar is acquired. C can run, but on daily data whose OOS block overlaps a
resolution question you would need to rule on first.

**Suggested sequence:** approve **A** now; commission the macro calendar for **B**
in parallel, since it is a small, verifiable acquisition that unblocks the
best-identified mechanism in the set; hold **C** pending your ruling on the
overnight instruction. And acquire **NQ 1-minute bars 2021–2026** regardless —
it is the cheapest single purchase that converts any of these from an
architecture screen into a deployment candidate.
