# IB 1R live review protocol — declared before the first live trade

**This file is written before any live trade is taken.** Its purpose is to fix
the review criteria so they cannot drift once the live numbers are visible.
Nothing here may be changed after trading starts except by a dated, committed
amendment that states what changed and why, in the same way every amendment in
this project has been made.

**No backtest was re-run to produce this file. 2016–2020 remains unread. Sealed
NQ days remain sealed.**

---

## 0. What is being tested, and what is not

**This rule already failed its own screen.** Under the strengthened
concentration rule adopted at `6c99ff1`:

| | |
|---|---|
| discovery, QQQ 1-minute | n = 685, mean **+0.0612 R**, t +2.23, PF 1.22, 5 of 6 years |
| after removing max(10, ⌈0.10n⌉) = 69 trades | **−0.0433 R** |
| share of total R in the top decile | **164%** |
| the other 616 trades, in aggregate | **negative** |
| pooled non-QQQ estimate (SPY, IWM, IJH, EFA) | **+0.0269**, CI spans zero |

**The live allocation is a data-collection exercise on a rule that did not
survive.** The review below is not a search for a reason to keep it. It is a
test with a pre-committed outcome map, and the most likely honest result is
that the live sample confirms the audit.

**Instrument change, recorded now:** discovery was on **QQQ 1-minute**; live is
on **NQ futures**. These are correlated but not the same instrument, tick
structure or cost basis. **Any live-versus-backtest comparison is
cross-instrument**, and that is a limitation of the exercise, not something the
review can correct for.

---

## 1. When the review happens

**At 100 completed trades**, where "completed" means a filled entry with a
recorded exit. Qualified-but-invalidated sessions and no-trade sessions are
logged but do **not** count toward the 100.

**No interim review is performed and no interim number is acted on.** At roughly
49% of sessions producing a qualifying setup and ~21 sessions a month, 100
trades is about **10 months**. If the rule is stopped early for any reason, the
review runs on whatever n exists and **the reduced power is stated**, not
glossed.

---

## 2. Power, stated before the data exists

Per-trade sd on the discovery set was **0.7175 R**.

| n | SE of mean R | two-sided 95% MDE |
|---|---|---|
| 50 | 0.101 | ±0.199 |
| **100** | **0.072** | **±0.141** |
| 200 | 0.051 | ±0.099 |
| 685 (discovery) | 0.027 | ±0.054 |

**This is the single most important number in this document.** The discovery
effect was **+0.061 R**. At n = 100 the MDE is **±0.141**, which is **2.3× the
effect being looked for.**

> **100 live trades CANNOT confirm this rule.** It is not powered to. A positive
> result at n = 100 will be indistinguishable from noise, and will be reported
> as such.

**What 100 trades *can* do, and is the actual purpose:**

1. **Falsify it.** A live mean of −0.15 R or worse is outside the interval the
   discovery estimate implies and would be informative.
2. **Verify the implementation.** Do the live IB high, IB low, which-formed-first
   and ending zone match what the rule computes? This is a correctness test and
   it does not need statistical power.
3. **Measure the qualifying rate.** Discovery qualified on ~49% of sessions. If
   live qualifies on 20% or 80%, the implementation or the instrument differs
   and that is knowable long before 100 trades.
4. **Measure the concentration profile out of sample.** See §5.

---

## 3. The six things computed at review, all fixed now

### 3.1 Honest costs

R is computed net of a **round-trip cost charged at the actual fill**, not a
modelled one: commission plus the realised slippage between the trigger level
and the fill, taken from the broker record. The backtest used
`COST_F = 2.00/30000` of price, i.e. **0.667 bps**, and **cost as a share of
risk is reported as a headline** so it can be compared with the discovery
set's **0.77–1.16%**. If live cost/risk exceeds 1.5%, that alone materially
changes the economics and is reported before any expectancy number.

### 3.2 Random-walk benchmark at the realised reward-to-risk

Not 50%. For a barrier trade at target `M × risk`, a driftless random walk gives

```
P(target first) = 1 / (1 + M)
```

At 1R that is **50.0%**. But the discovery set exited at the **close** on 59% of
trades, so the realised structure is not a clean ±1R barrier. **The benchmark is
therefore computed from the live realised mix**: for each trade the realised
reward-to-risk at exit, and the win rate is compared with `1/(1+M)` at the
sample's own realised `M`. **The gap to the random-walk rate is the number
reported, never the raw win rate.**

### 3.3 Clustered standard errors

Clustered by **date**:

```
SE = sqrt( (g/(g−1)) × Σ (cluster sums)² ) / n
```

The single-trade rule gives roughly one trade per date, so clustering will be
close to the plain SE. It is computed anyway, and reported, because the
convention is fixed across the project.

### 3.4 The concentration profile — the test this rule already failed

Reported in full, not as a pass/fail flag:

| | |
|---|---|
| mean R after removing **max(10, ⌈0.10n⌉)** trades | the standing rule; at n = 100 this removes **10** |
| mean R after removing the best **1, 3, 5, 10, 20** trades | the shape, not just the verdict |
| **share of total R in the top decile** | discovery was **164%** |
| mean R of the bottom 90% | discovery was **−0.043** |
| exit mix (close / target / stop) | discovery was 407 / 143 / 135 |

**The pre-committed comparison:** if the live top decile carries a
**materially lower** share than 164%, that is evidence the discovery
concentration was a sample artefact and is worth knowing. If it carries a
**similar or higher** share, the audit is confirmed out of sample and the rule
closes permanently.

**Declared now:** at n = 100 the `max(10, ·)` arm binds at exactly the decile,
so this is a clean top-decile removal with no small-sample distortion.

### 3.5 Excess over buy-and-hold

The drift-adjusted number, using the definition corrected at `02e0746`:

```
excess_R = R − d × drift × entry_price / risk
```

where `drift` is the **unconditional** mean fractional move from the entry clock
to 16:00 ET across all sessions in the live window — **not** the traded
sessions' own moves, and **not** a long-only benchmark, which is wrong for the
short arm. **`excess_R` leads every table. Raw R is reported beside it, never in
front of it.**

### 3.6 Long and short arms, separately

Reported apart before any pooled row, as required from `02e0746` onward. The
discovery set was direction-balanced by construction — the trade direction is
set by which IB extreme formed first — so a large live imbalance is itself a
finding about the live sample.

---

## 4. The pre-outcome note, and why it is the point

Every row carries a **free-text note written before the outcome is known.**
Entry, stop, risk and target are recorded at 10:30–10:40; the note is written
then and is never edited afterwards.

**This is what makes the live log auditable to the same standard as the
archive.** The archive's protection against hindsight is that every rule was
pre-registered with a commit hash. A live log has no equivalent unless the
operator's read of the session is fixed before the result exists. Without it,
every losing trade acquires a retrospective explanation and the log becomes
unusable as evidence.

**Enforcement:** the log is committed **daily**, before the US close where
possible and on the same day in all cases. A row whose note is added or changed
after the exit is recorded is **marked as such and excluded from the primary
review**, then reported separately with its count. Git history is the audit
trail; this only works if the commits are daily.

---

## 5. The outcome map, fixed in advance

Evaluated at n = 100 on `excess_R`, long and short reported separately first.

| live result | what is concluded | what happens |
|---|---|---|
| mean **≤ −0.141** (below the MDE, negative) | consistent with the audit; the discovery effect does not appear live | **closed permanently.** No further allocation. |
| mean between **−0.141 and +0.141** | **the expected outcome.** Indistinguishable from zero *and* from the discovery estimate — 100 trades cannot separate them | **not a pass.** Continue only if the concentration profile improved materially (§3.4) and the implementation checks in §6 all passed. Otherwise close. |
| mean **≥ +0.141** | larger than the discovery effect itself (+0.061) | treat with **suspicion, not enthusiasm.** An effect 2.3× discovery on 100 trades is more likely an implementation divergence or a lucky tail than a real improvement. Required before any increase in size: the concentration profile, the exit mix and the qualifying rate must all be consistent with discovery, **and** the result must survive removing the top decile. |
| **fails the concentration test at any mean** | the pathology reproduces out of sample | **closed permanently**, whatever the headline. This is the pre-committed answer and it overrides the mean. |

**No size increase is authorised by this protocol under any outcome.** A size
decision is a separate decision, taken separately, and nothing in a 100-trade
sample can justify one.

---

## 6. Implementation checks, run at 10 trades and again at 100

These need no statistical power and catch the failures that have actually
occurred in this project.

| check | pass condition |
|---|---|
| **bar resolution** | chart is 1-minute on every logged session. The rule is defined in bars; on another grid *which extreme formed first* changes and it is a different rule. |
| **session window** | first IB candle timestamps at the configured start on every session. Catches the **daylight-saving** shift in March and November, when 09:30 ET moves between 13:30 and 14:30 UTC. |
| **qualifying rate** | share of sessions reaching QUALIFIED, against discovery's ~49%. A large gap means the implementation or the instrument differs. |
| **same-bar extremes** | rate of sessions skipped because IBH and IBL printed on one bar, logged and compared. |
| **invalidation rate** | share of qualified sessions that go INVALIDATED before entry. |
| **entry-bar stops** | count of trades stopped on the entry bar. **The backtest excludes the entry bar from its exit search, so these do not exist there.** If this count is material, the live and backtest conventions are not comparable and the review must say so. |
| **ambiguous bars** | stop and target touched in the same candle. Discovery logged the rate; live must too. |

---

## 7. What this protocol deliberately does not permit

- **No re-optimisation.** Not the ending-zone band, not the target, not the IB
  length, not the flat time. The rule is frozen; changing it restarts the count
  at zero and requires a new pre-registration.
- **No conditioning the live log on anything.** Conditioning was tested three
  ways and closed at `fb2b87e`: 152 subsets, best t +2.263 against a
  random-label bar of +3.777, the observed best below the *median* random
  search. Applying a filter to the live trades would repeat a closed test on a
  smaller sample.
- **No interim stop-outs on P&L.** The review is at 100 trades. A drawdown is
  not new information about a rule already known to lose money on 90% of its
  trades.
- **No opening 2016–2020.** The holdout is not a tiebreaker for a live result
  and nothing in this exercise can justify spending it. There is currently
  **nothing frozen in the ledger that would justify opening it at all.**

---

## 8. Ledger entry, recorded now

| screen | sample | outcome |
|---|---|---|
| **IB 1R, live out-of-sample collection** | target 100 trades, NQ futures, began 2026-09 | **open — data collection only.** The rule FAILED the concentration audit (−0.0433 after top-decile removal; 164% of R in the top decile) and is not a validated strategy. Review criteria fixed in advance at this commit. **n = 100 is under-powered by 2.3× against the discovery effect and cannot confirm the rule; it can only falsify it, verify the implementation, and measure the out-of-sample concentration profile.** |

---

Deliverables: `atas/IbOneR.cs` (indicator, display only),
`atas/ib1r_guide.svg` (one-page visual guide),
`journal/ib1r_trade_log.csv` (log template), this file (review protocol).
