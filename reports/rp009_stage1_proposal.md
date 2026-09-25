# RP-009 — Time-of-Day Opportunity and Risk Design
## Stage 1 specification and data inventory. **Nothing was run.**

**No strategy P&L will be read at any point in Stage 1.** No expectancy, no
profit factor, no win rate, no drawdown, no trade. No strategy module is
imported by the Stage 1 code. This is a barrier-geometry map of the market, and
barrier geometry is not evidence of edge.

Not an allocator. Not a directional test. Long and short paths are measured
symmetrically and no result may be read as a claim about direction.

---

## 1. The question, and what carries into it from RP-008

RP-008 established that the session becomes **quieter without becoming more or
less directionally efficient**: forward volatility falls ~44% and excursions
~55% from the open to 14:00, while path efficiency stays flat at 0.127–0.140.

RP-009 asks the design consequence:

> Given a falling excursion budget and a shrinking holding window, does the
> **architecture** of a trade — its risk container, its target distance, its
> viability against cost — have to change mechanically with the clock, before
> any question of predictive edge arises?

---

## 2. Two results available before Stage 1 runs

Both are arithmetic on committed data, and both narrow the grid the user
proposed. Stating them now rather than presenting them later as findings.

### 2.1 The NQ volatility unit, measured

44 full NQ sessions at true 0.25 resolution, 2026-06-18 → 2026-08-20:

| | |
|---|---|
| mean 1-minute ATR | **21.55 points** |
| median 1-minute true range | 18.00 points |
| mean price | 29,460 |
| mean RTH range | 464 points |

### 2.2 Three of the six risk containers are dead on cost alone

NQ round turn is **2.0 points** (one tick crossed each way plus commission), the
figure this project's frozen runners already use. The deployment standard caps
round-trip cost at **10% of initial risk**.

| risk container | NQ points | cost / risk | vs the 10% bar |
|---|---|---|---|
| **10 NQ points** | 10.0 | **20.0%** | **FAIL** |
| 20 NQ points | 20.0 | **10.0%** | exactly at the limit |
| 30 NQ points | 30.0 | 6.7% | pass |
| **0.5 × ATR₁ₘ** | 10.8 | **18.6%** | **FAIL** |
| 1.0 × ATR₁ₘ | 21.6 | 9.3% | pass, narrowly |
| 1.5 × ATR₁ₘ | 32.3 | 6.2% | pass |

**The 10-point and 0.5-ATR containers are eliminated before a single path is
measured**, and the 20-point container sits exactly on the limit with no
headroom for slippage. They are still measured and reported — the map is more
useful complete, and §4's question "at what times do fixed point stops become
economically unsuitable?" is partly answered by this table — but they cannot be
carried into any later design.

A consequence worth naming now: **on NQ the smallest viable stop is about one
1-minute ATR**, ≈21.6 points ≈ 7.3 bps. Any architecture needing a tighter stop
is not an NQ architecture.

---

## 3. Data inventory

| instrument | dates | sessions | resolution | coverage | role in RP-009 | previous use |
|---|---|---|---|---|---|---|
| **QQQ 1-minute** | 2021-01-04 → 2026-08-31 | **1,421** (1,418 usable) | $0.01 | RTH 09:30–15:59 | **primary map**, ATR-normalised containers | spent — every strategy and RP-007/008 screened here |
| **NQ 1-minute from tape** | 2026-06-18 → 2026-08-20 | **46** (44 full) | true 0.25, verified per date | 24-hour; RTH extracted | **native map**, fixed-point containers | 36 examined, 10 sealed |
| NQ 5.00 recordings | 18 dates | — | 5.00 | — | **excluded** | — |
| QQQ 2016–2020 | — | 1,259 | $0.01 | RTH | **not opened** — spent | one authorised holdout |
| NQ 2026-08-21 → 09-11 | 16 dates | — | **still 5.00** | — | **not available** | see §3.1 |

### 3.1 Preservation status — checked, not assumed

`data/tape/` holds **104 files**, `data/bbo/` **46**, `data/status/` **41** —
**unchanged since the RP-007 baseline**. The sixteen re-recordings have **not
been delivered** and nothing is claimed for them. If they land and pass
`verify_preservation.py`, the NQ map grows from 44 to ~59 full sessions.

### 3.2 The instrument split, and why it is not a compromise

| container type | instrument | reason |
|---|---|---|
| **ATR-normalised** (0.5 / 1.0 / 1.5 × ATR₁ₘ) | **QQQ, 1,418 sessions** | dimensionless; the question is about barrier geometry relative to the sizing unit, and QQQ gives 32× the sample |
| **Fixed NQ points** (10 / 20 / 30) | **NQ, 44 sessions** | absolute points are instrument-specific. RP-007 established that transferring absolute NQ quantities into QQQ is not permitted |

There is no long NQ price history on disk to convert with: `NQ_daily.parquet`
holds **61 days** (2026-04-07 → 2026-07-02). A per-session conversion of "10 NQ
points" into QQQ bps across 2021–2026 is therefore impossible, and inventing a
fixed ratio would repeat the error RP-007 closed.

**Consequence, declared:** the fixed-point questions are answerable only on 44
NQ sessions, giving a standard error of about ±7.5 points on a probability. They
are reported as **exploratory**; the ATR-normalised questions are reported as
**primary**.

### 3.3 Cost assumptions

| instrument | round turn | as bps | source |
|---|---|---|---|
| **NQ** | **2.0 points** (1 tick each way + commission) | **0.68 bps** at 29,460 | the constant every frozen NQ runner uses |
| **MNQ** | same in points | same in bps | micro contract, same tick |
| QQQ | $0.017 ($0.01 spread + $0.0035 each way) | **0.422 bps** mean | `$0.017/share`, this project's ETF model |

**The headline cost is NQ's, because deployment is MNQ/NQ.** QQQ's own cost is
reported alongside and must not be substituted: QQQ is **1.6× cheaper in bps**
and getting cheaper as its price rises —

| year | QQQ price | QQQ cost (bps) | NQ cost (bps) |
|---|---|---|---|
| 2021 | 353 | 0.482 | 0.68 |
| 2023 | 346 | 0.492 | 0.68 |
| 2026 | 664 | **0.256** | 0.68 |

A QQQ-cost map would flatter NQ viability, increasingly so in recent years. Every
cost-as-a-share-of-excursion figure in Stage 1 is computed at **0.68 bps**.

### 3.4 Volatility units

| | QQQ | NQ |
|---|---|---|
| mean 1-minute ATR | $0.2945 | 21.55 pts |
| as bps of price | **7.04** | **7.32** |

The two agree to within 0.3 bps, which is what licenses the ATR-normalised map
on QQQ.

---

## 4. Fixed timestamps

**Fourteen, frozen, on a 30-minute grid with one extra anchor in the opening
block** (which is only 30 minutes long and would otherwise have a single point):

| block | timestamps |
|---|---|
| **opening auction** 09:30–10:00 | 09:30, 09:45 |
| **morning** 10:00–11:30 | 10:00, 10:30, 11:00 |
| **midday** 11:30–14:00 | 11:30, 12:00, 12:30, 13:00, 13:30 |
| **closing period** 14:00–16:00 | 14:00, 14:30, 15:00, 15:30 |

Block boundaries are RP-008's and are **not altered after viewing results**.
Every timestamp is a clock time known in advance; nothing is conditioned on.

The entry price is the **close of the timestamp bar**, and the forward window
begins at the **next** bar — the timestamp bar is excluded from the path, the
same convention RP-007 and every frozen runner use.

## 5. Holding horizons

**15, 30, 60 and 120 minutes, plus hold-to-the-cash-close.** Five per timestamp.

Truncation is a measurement, not a defect: a 120-minute horizon from 15:30 has
only 30 minutes available, and **the frequency of truncated paths is one of the
outputs** (§3 of the brief: "frequency of unresolved paths at the close"). Every
table reports available minutes alongside the horizon so a truncated cell is
never mistaken for a resolved one.

## 6. Risk containers

The six from the brief, unchanged: **10, 20, 30 NQ points** and **0.5, 1.0,
1.5 × ATR₁ₘ**, with §2.2's cost verdict attached to each wherever it appears.

ATR₁ₘ is the **prior session's mean 1-minute true range** — causal, one number
per session, the unit RP-007 and RP-008 both used.

## 7. Barrier convention, declared before measurement

One-minute OHLC cannot resolve intra-bar order. When a single bar's range spans
both the favourable and the adverse barrier:

* **the adverse barrier is deemed hit first** — the conservative convention this
  desk already applies in `bar_resolution_gate`, `orb_fib` and every frozen
  runner;
* **the ambiguity rate is reported per cell**, so the reader can see how much of
  each figure rests on the convention rather than on the data.

The bar-resolution gate measured 23.5% of tick-level trades opening and closing
inside one minute, so this is a real limit and not a formality. Where the NQ
tape is used the true tick order is available and the same cells are reported
**both ways** — ambiguity-free from tape and under the 1-minute convention —
which calibrates how much the convention costs.

---

## 8. Expected sample sizes

| | per timestamp | opening | morning | midday | closing | total |
|---|---|---|---|---|---|---|
| **QQQ** (1,418 sessions) | 1,418 | 2,836 | 4,254 | 7,090 | 5,672 | **19,852** |
| **NQ** (44 full sessions) | 44 | 88 | 132 | 220 | 176 | **616** |

Standard error on a barrier probability near 0.5: **±1.3 points** on QQQ per
timestamp, **±7.5 points** on NQ. Every NQ cell is labelled exploratory.

Sessions lost: 1 with fewer than 300 bars, 1 with no usable prior session (no
ATR₁ₘ). Late timestamps lose no sessions — 15:30 exists on every full session.

---

## 9. Proposed opportunity-map tables

**Table A — excursion budget by timestamp.** One row per timestamp × horizon.

`timestamp · block · horizon · available minutes · MFE points (median, p75) ·
MAE points · MFE in ATR₁ₘ · MAE in ATR₁ₘ · range in ATR₁ₘ · % of paths
truncated by the close`

**Table B — time to excursion.** One row per timestamp × excursion level
{0.5, 1.0, 1.5, 2.0 × ATR₁ₘ}.

`timestamp · level · P(reached before the opposite level) · P(reached before the
close) · median minutes to reach · p75 minutes · % never reached`

**Table C — barrier geometry by risk container.** The brief's §5 table, one row
per block × container.

`block · container · cost as % of risk · P(+1R before −1R) · P(+1.5R before −1R)
· P(+2R before −1R) · median minutes to resolution · % unresolved at the close ·
ambiguous-bar rate`

**Table D — cost as a share of attainable movement.** One row per block ×
horizon.

`block · horizon · median MFE in bps · NQ cost 0.68 bps as % of median MFE · as
% of p25 MFE · % of paths whose MFE never covers 3× cost`

**Table E — controls.** The brief's §7, four arms:

| arm | what it isolates |
|---|---|
| same fixed container across all blocks | raw opportunity difference |
| ATR-normalised container across all blocks | what survives normalisation |
| equal holding horizon across all blocks | differences caused only by the horizon |
| hold to the cash close | differences caused only by shorter remaining time |

**Table F — existing strategy compatibility.** The brief's §6. Entry window,
median risk, median holding time, target architecture, whether the block
supplies enough attainable movement, whether the target is frequently truncated
by the close, and whether cost-and-excursion economics make the design viable
**before predictive edge is considered**.

**No strategy expectancy appears in Table F or anywhere else.** The inputs are
each strategy's frozen entry window, median risk and median holding time — all
already measured in the RP-008 Stage 0 audit — placed against the opportunity
map. The purpose is to identify structurally incompatible designs, not to
rescue any backtest.

**Table G — by year**, for the primary excursion and barrier figures, 2021–2026.

---

## 10. Verdict form

Exactly one of the brief's four:

* **Time-of-day architecture supported** — blocks support materially different
  risk, target or holding structures after the §7 controls;
* **Time affects only scale** — ATR normalisation removes the differences, so
  architecture stays fixed and only sizing adapts;
* **Late-session opportunity insufficient** — midday or closing cannot support
  the required excursion after costs and time;
* **No additional information** — the map adds nothing beyond RP-008.

**My prior: "time affects only scale", with a real possibility of "late-session
opportunity insufficient" for the closing block.** RP-008 already showed
excursions falling 55% while efficiency stays flat, which is the signature of a
pure scale effect; and the closing block starts with 120 minutes of runway
against a median 1-ATR resolution time that Stage 1 will measure. Stated now so
a scale result is not later dressed up as an architecture result.

---

## 11. What will not be claimed

Per the brief, and restated so it binds the report: **no claim that a time block
predicts direction; that an opening breakout has edge; that midday mean
reversion has edge; that any strategy should be deployed; or that changing stop
or target sizes creates expectancy.** Stage 1 determines economic opportunity
only, and any later strategy test must still supply a mechanism for directional
or relative-value edge.

Barrier probabilities on a driftless path are **geometry**. For a symmetric
random walk P(+MR before −1R) = 1/(1+M); every Table C figure must be read
against that identity, and it will be printed beside each one.

## 12. Confirmation

**No strategy P&L will be read during RP-009 Stage 1.** No expectancy, profit
factor, win rate, drawdown or trade result. No strategy module will be imported
by the Stage 1 code. Sealed NQ dates will not be read. 2016–2020 will not be
opened. No allocator will be built.

Stage 1 will not run until the specification is approved.
