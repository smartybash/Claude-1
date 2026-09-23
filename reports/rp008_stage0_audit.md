# RP-008 Stage 0 — data, strategy and feasibility audit

**Counts only.** No conditional performance was computed. No strategy was split
by regime. No allocator was defined. No Monte Carlo was run. No closed strategy
was reopened as a standalone candidate.

Unconditional expectancy, profit factor and drawdown appear because §5 of the
brief requires them. They are unconditional and nothing below is conditioned on
anything.

Reproduced by `scripts/orderflow/rp008_stage0.py` and
`scripts/orderflow/rp008_stage0_cells.py`.

---

## 1. Ledger reproduction — the gate before everything else

Every frozen runner was executed and its committed output regenerated. **The git
working tree stayed clean after all seven runs**, which is the strictest form of
the reproduction test: the trade sets are byte-identical to the committed
ledgers.

| runner | exit | committed ledger | reproduces |
|---|---|---|---|
| `setup_grading.py` | 0 | `setup_grading_trades.csv`, 13,840 rows | **exact** |
| `ib_pullback_native.py` | 0 | `ib_pullback_native_result.md` | **exact** |
| `ib_pullback_holdout.py` | 0 | `ib_pullback_holdout_trades.csv`, 132 rows | **exact** |
| `compression_run.py` | 0 | `compression_variants.csv`, 18 rows | **exact** |
| `orb_fib_study.py` | 0 | `orb_fib_continuation_trades.csv`, 354 rows | **exact** |
| `orb_vwap.py` | 0 | `orb_vwap_result.md` | **exact** |
| `pullback.py` | 0 | `pullback_preregistration_v2.md` result | **exact** |
| `ib_rejection.py` | 0 | measurement module, emits nothing | n/a |

Spot checks against the committed prose: the holdout reproduces 132 trades,
2.20/month, expectancy **+0.0002 R**, profit factor **1.000**; compression
reproduces empirical p **0.7065** and 0 of 6 survivors; the native transfer
reproduces QQQ frozen **+0.185 R** on 164 trades and pooled non-QQQ **−0.004 R**
on 667.

**Kill condition 1 does not fire.** Far more than two strategies reproduce.

### Entry timestamps

None of the committed trade CSVs carry an entry timestamp except
`setup_grading_trades.csv`, which carries `mins` since the cash open. For the
other families the entry bar was recovered by **wrapping** the frozen trade
builders — the wrapper records the entry index the runner already chose and then
delegates unchanged. No rule was altered and the regenerated outputs are
identical.

**Entry-time regime variables are available for all thirteen trade sets. Kill
condition 2 does not fire.**

---

## 2. Strategy inventory — unconditional

QQQ 1-minute, 2021-01-04 → 2026-08-31 unless stated. Costs and fills are each
strategy's own frozen model.

| strategy | trades | sessions | months | /mo | **uncond. expR** | PF | maxDD (R) | long | short |
|---|---|---|---|---|---|---|---|---|---|
| ORB OR15 R3 | 2,619 | 1,398 | 67 | 39.1 | **−0.026** | 0.97 | 67.8 | — | — |
| ORB OR15 R4 | 2,600 | 1,398 | 67 | 38.8 | **−0.003** | 1.00 | 88.3 | — | — |
| ORB OR30 R3 | 2,577 | 1,379 | 67 | 38.5 | **−0.095** | 0.89 | 260.4 | — | — |
| ORB OR30 R4 | 2,556 | 1,379 | 67 | 38.1 | **−0.110** | 0.88 | 281.8 | — | — |
| pullback OR15 R3 | 2,065 | 1,156 | 67 | 30.8 | **−0.057** | 0.92 | 155.9 | — | — |
| pullback OR30 R3 | 1,423 | 851 | 67 | 21.2 | **−0.051** | 0.93 | 91.6 | — | — |
| IB 1R re-entry | 736 | 685 | 68 | 10.8 | **+0.063** | 1.22 | 10.4 | 403 | 333 |
| IB 1R single | 685 | 685 | 68 | 10.1 | **+0.061** | 1.22 | 11.0 | 378 | 307 |
| IB-mid pullback R2 (native) | 233 | 233 | 58 | 4.0 | **+0.124** | 1.23 | 15.3 | 130 | 103 |
| Compression D=10:30 flat | 208 | 208 | 61 | 3.4 | **+0.006** | 1.07 | 3.4 | 132 | 76 |
| Compression D=10:00 flat | 200 | 200 | 62 | 3.2 | **−0.001** | 0.99 | 4.4 | 126 | 74 |
| ORB-Fib cont ORB15 A | 112 | 112 | 58 | 1.9 | **+0.115** | 1.23 | 8.5 | 52 | 60 |
| ORB-Fib cont ORB30 A | 76 | 76 | 45 | 1.7 | **+0.207** | 1.53 | 5.4 | 24 | 52 |

Entry / stop / target / window / cost / fill are each family's frozen
definitions: ORB and pullback — opening range OR15 or OR30, stop 1.0 × ATR₁ₘ,
target 3R or 4R, honest fills at `max(trigger, bar open)`, entry bar excluded,
0.667 bps round turn; IB — 09:30–10:30 balance, first-timestamp extreme, entry
on the expected-break level, stop at the opposite boundary, 2.0 pt round turn;
IB-mid — 0–25% ending zone, midpoint band ±0.05 IB, R2 rejection, 1.5R target,
13:00 expiry, native buffer and stop limits; compression — prior 3-session
range, `k ≤ 1.00`, `W ≥ 150 bps`, resolved and held at D, stop at the opposite
edge; ORB-Fib — band A (0.382/0.618), one trade per session.

### Excluded from the library

| strategy | reason |
|---|---|
| **VWAP stretch / ORB+VWAP** | All 16 variants unconditionally negative (best **+0.012 R**, most −0.08 to −0.36), and the family's own slippage audit shows a **+0.04 to +0.16 R phantom** from the naive fill. §5 admits it "only if a corrected and economically valid implementation exists". **It does not.** This matters for the midday prior — see §6. |
| **NQ-native pullback** (`pullback.py`) | 49 trades over 35 NQ sessions, 0 of 12 variants survived its own rejection criteria. Below every sample floor. |
| **ORB-Fib reversal** | 39 / 34 / 17 / 13 sessions against its own declared 150-session resolvability floor. Descriptive only, by its own report. |
| **RP-007 level rejection** | Closed. Contributes nothing, as instructed. |

---

## 3. Trades by frozen time-of-day block — the central Stage 0 finding

Blocks assigned by entry timestamp: open 09:30–10:00, morning 10:00–11:30,
midday 11:30–14:00, close 14:00–16:00.

| strategy | trades | **open** | **morning** | **midday** | **close** |
|---|---|---|---|---|---|
| ORB OR15 R3 | 2,619 | 1,534 | 994 | 91 | **0** |
| ORB OR15 R4 | 2,600 | 1,531 | 973 | 96 | **0** |
| ORB OR30 R3 | 2,577 | **0** | 2,362 | 215 | **0** |
| ORB OR30 R4 | 2,556 | **0** | 2,333 | 223 | **0** |
| pullback OR15 R3 | 2,065 | 249 | 1,335 | 481 | **0** |
| pullback OR30 R3 | 1,423 | **0** | 848 | 575 | **0** |
| IB 1R re-entry | 736 | **0** | 633 | 62 | 41 |
| IB 1R single | 685 | **0** | 631 | 43 | 11 |
| IB-mid pullback R2 | 233 | **0** | 157 | 76 | **0** |
| Compression D=10:30 | 208 | **0** | 208 | **0** | **0** |
| Compression D=10:00 | 200 | **0** | 200 | **0** | **0** |
| ORB-Fib cont ORB15 A | 112 | 5 | 99 | 6 | 2 |
| ORB-Fib cont ORB30 A | 76 | **0** | 65 | 8 | 3 |
| **TOTAL** | **13,890** | **3,319** | **9,838** | **1,876** | **57** |

**The library does not have time-of-day diversity.**

* **95% of all trades are before 11:30.** 71% are in the morning block alone.
* **The closing block holds 57 trades out of 13,890 — 0.41%.** Nine of the
  thirteen strategies never enter after 14:00 at all, and the four that do
  produce 41, 11, 3 and 2 trades across five and a half years.
* **Seven of thirteen strategies have a structurally empty opening block**, and
  not by accident — see §4.

### Kill condition 7: the regime boundaries restate the entry rules

The 10:00 and 10:30 boundaries are **not independent of the strategies**:

| strategy | why its opening block is empty |
|---|---|
| ORB OR30, pullback OR30 | the 30-minute opening range is not complete until **10:00** |
| Compression D=10:00 / D=10:30 | the decision bar **is** 10:00 or 10:30; entry is the next bar, so the entry minute is a constant (31 or 61), not a distribution |
| IB 1R, IB-mid pullback | the Initial Balance closes at **10:30** |
| ORB-Fib ORB30 | opening range complete at 10:00 |

For six of thirteen strategies the "time-of-day regime" at the 10:00 boundary
**is the strategy's own entry window, restated**. Allocating ORB OR30 to the
morning block is not a regime decision; it is the only block in which the rule
can fire.

**Kill condition 7 fires for those six.** It does not fire for ORB OR15,
pullback OR15 or IB 1R, which spread across blocks for reasons other than their
own definitions.

---

## 4. Regime variable inventory

### Available and causally joinable at the entry timestamp

| variable | source | status |
|---|---|---|
| prior-session realised volatility | QQQ 1-min, prior session close-to-close | **available.** Labelled causally on 1,357 of 1,418 sessions (61 lost to the 60-session warm-up) |
| opening gap in bps | `preopen.build()` (`gap_raw`) | **available** |
| prior-session range vs trailing distribution | `or_height.or_ratio`, trailing-20 mean, shifted | **available** |
| prior-session close location in its range | `preopen` (`prior_loc`) | **available** |
| **FOMC flag** | `data/events/fomc.csv`, 48 verified dates 2021-01-27 → 2026-12-09 | **available and verified** |
| realised volatility to the entry timestamp | QQQ 1-min prefix | **available** |
| realised-vol percentile vs prior completed sessions | rolling causal | **available** |
| net displacement ÷ path length to entry | QQQ 1-min prefix | **available** |
| opening range vs trailing distribution | `or_height.or_ratio` | **available** |
| distance from session VWAP in ATR units | causal VWAP prefix | **available** |
| time-of-day block | entry timestamp | **available** |

Causal tercile labelling was verified end to end: prior-session realised
volatility, rolling 250-session terciles, 60-session minimum warm-up, no
same-day input. Coverage 1,357 of 1,418 sessions (LO 513, MID 394, HI 450).

### Not available

| variable | why |
|---|---|
| **overnight range** (`on_range`) | `preopen.py` computes it **raw**, with no cleaning at all. §7 permits it only with an independently frozen and validated cleaning method, and the correction ledger records that the second-extreme method was defective — it changed 98.1% of sessions and cut mean range 117.6 → 91.7 bps. **No validated cleaning method exists, so the variable is excluded.** |
| **overnight net displacement** (`on_disp`) | same source, same exclusion |

`vix_lvl` and `vix_chg` exist in `preopen` and are causal, but they are **not in
the §7 list** and are not introduced here.

**Every permitted regime variable is callable at the trade timestamp on QQQ.**

---

## 5. Proposed regime structure and cell sizes

Hierarchy as specified: fixed time-of-day block → causal rolling volatility
tercile → directional efficiency only where the cell still holds ≥150.

Cell sizes, strategy × block × causal prior-session volatility tercile:

| strategy | block | LO | MID | HI | all |
|---|---|---|---|---|---|
| ORB OR15 R3 | **open** | **532** | **443** | **518** | 1,534 |
| ORB OR15 R3 | morning | **392** | **265** | **300** | 994 |
| ORB OR15 R3 | midday | 37 | 32 | 21 | 91 |
| ORB OR30 R3 | morning | **852** | **672** | **763** | 2,362 |
| ORB OR30 R3 | midday | 91 | 56 | 64 | 215 |
| pullback OR15 R3 | open | 92 | 75 | 72 | 249 |
| pullback OR15 R3 | morning | **492** | **364** | **438** | 1,335 |
| pullback OR15 R3 | midday | **162** | **161** | 146 | 481 |
| pullback OR30 R3 | morning | **312** | **227** | **287** | 848 |
| pullback OR30 R3 | midday | **205** | **183** | **172** | 575 |
| IB 1R single | morning | **222** | **178** | **204** | 631 |
| IB 1R single | midday | 14 | 10 | 17 | 43 |
| IB 1R single | close | 3 | 6 | 2 | 11 |
| IB-mid pullback R2 | morning | 58 | 41 | 49 | 157 |
| IB-mid pullback R2 | midday | 26 | 21 | 25 | 76 |
| Compression D=10:00 | morning | 72 | 65 | 56 | 200 |
| Compression D=10:30 | morning | 79 | 64 | 56 | 208 |
| ORB-Fib cont ORB15 A | morning | 36 | 27 | 29 | 99 |
| ORB-Fib cont ORB30 A | morning | 30 | 17 | 14 | 65 |

**Cells clearing 150 (primary interpretation): 22**, all belonging to ORB OR15,
ORB OR30, pullback OR15, pullback OR30 and IB 1R.

**Cells at 75–149 (exploratory): 6** — pullback OR15 midday HI (146), ORB OR30
midday LO (91), ORB-Fib ORB15 morning LO (36 — no, below), compression morning
LO ×2 (72, 79), pullback OR15 open LO/MID (92, 75).

**Cells below 75: everything else** — every IB-mid cell, every ORB-Fib cell,
every IB 1R midday and close cell, every ORB OR15 midday cell.

### The arithmetic that decides RP-008

| | unconditional expectancy | cells ≥150 |
|---|---|---|
| ORB OR15 R3 / R4 | **−0.026 / −0.003** | 6 |
| ORB OR30 R3 / R4 | **−0.095 / −0.110** | 3 |
| pullback OR15 R3 | **−0.057** | 5 |
| pullback OR30 R3 | **−0.051** | 6 |
| IB 1R single | **+0.061** | 3 |
| IB-mid pullback R2 | **+0.124** | **0** |
| ORB-Fib ORB15 / ORB30 | **+0.115 / +0.207** | **0** |
| Compression D=10:30 | **+0.006** | **0** |

**The three strategies with the strongest unconditional economics cannot reach
the sample floor in any regime cell, and the strategies that reach the floor
everywhere are unconditionally negative.**

IB 1R is the sole exception — positive at +0.061 R with three cells over 150 —
and all three are in the **same time-of-day block**, so time of day cannot
discriminate among them. That is a volatility split of one strategy in one
block, not an allocator.

---

## 6. Predeclared primary and backup assignments, and what they collide with

Declared from mechanism only. **No conditional outcome was viewed.**

| # | regime (observable before entry) | primary | backup | mechanism | cells ≥150? |
|---|---|---|---|---|---|
| R1 | **open 09:30–10:00, HI volatility** | ORB OR15 R4 | none | a large opening impulse may reflect urgent repricing and forced participation; the breakout is the only frozen rule that can fire before 10:00 | **518 ✓** |
| R2 | **open 09:30–10:00, LO/MID volatility** | **no trade** | none | §13: no trade at a low-volatility open unless a frozen mean-reversion strategy has independent support. None exists | n/a |
| R3 | **morning 10:00–11:30, MID volatility, high causal efficiency** | pullback OR15 R3 | IB 1R single | orderly directional displacement supports continuation after retracement; IB 1R is the backup because it fires only when the balance resolves, which is a disjoint setup | 364 → **≈182 after the efficiency split ✓ (marginal)** |
| R4 | **morning 10:00–11:30, HI volatility** | ORB OR30 R3 | none | the 30-minute range completes at 10:00; a wide-range break in high volatility is the same urgency mechanism as R1 one block later | **763 ✓** |
| R5 | **midday 11:30–14:00, low efficiency** | **no trade** | none | the prior calls for a corrected mean-reversion strategy. **The library contains none** — see §2 | n/a |
| R6 | **close 14:00–16:00, and FOMC after 14:00** | **no trade** | none | RP-005 rejected the close-specific continuation mechanism; the FOMC finding was volatility expansion without directional edge. **57 trades exist in this block in the whole library anyway** | n/a |

**Six regimes, three primary pairings, one backup pairing, three no-trade
allocations.**

### Declared search burden (§17)

| | count |
|---|---|
| regimes | **6** |
| primary pairings | **3** |
| backup pairings | **1** |
| controls (random labels, ToD only, vol only, efficiency only, neighbouring thresholds, prior classification, unconditional, no-trade) | **8** |
| **total conditional comparisons** | **4 pairings × (1 + 8) = 36** |

No additional pairing may be added after results are viewed.

### The problem with this table, stated now

**All three live primary pairings are filled by unconditionally negative
strategies**: ORB OR15 R4 at −0.003, pullback OR15 R3 at −0.057, ORB OR30 R3 at
−0.095. The only backup, IB 1R, is the one positive strategy with sample.

§15 requires each pairing to reach **+0.10 R after costs**. That demands the
regime move ORB OR15 R4 by **+0.103 R**, pullback OR15 by **+0.157 R** and ORB
OR30 by **+0.195 R** — from a volatility tercile known before the open.

**§25 kill condition 6** asks whether "the only possible allocator repeatedly
selects strategies already known to be negative without a defensible conditional
mechanism". The mechanisms above are defensible and were declared from theory,
not from outcomes. But three of three live cells are filled by negative
strategies, and the three strategies with positive unconditional economics are
excluded by sample size rather than by mechanism. **That is the condition
firing, or as close to firing as it gets without the conditional numbers.**

---

## 7. Data roles and the final out-of-sample path

| instrument | dates | resolution | session coverage | discovery status | previous use | discovery? | internal validation? | untouched final OOS? |
|---|---|---|---|---|---|---|---|---|
| **QQQ** | 2021-01-04 → 2026-08-31, 1,421 sessions | 1-min, $0.01 | RTH 09:30–15:59; ETH 04:00–19:59 on 1,399 | **spent** | every strategy in §2 was built and screened here; RP-007 also screened here | yes | **no** | **no** |
| **QQQ** | 2016-01-04 → 2020-12-31, 1,259 sessions | 1-min, $0.01 | RTH only | **spent** | the one authorised IB-mid holdout was run here; the FOMC ruling bars its reuse | no | **no** | **no** |
| **NQ** | 2026-06-18 → 2026-08-20, 46 dates (44 full) | true 0.25, verified per date | 24-hour tape, depth, cum, BBO | 36 examined, 10 sealed | RP-002/003/004, European profile, bar-resolution gate | the 36, yes | the 9 sealed, **falsification check only** | **no** |
| **NQ** | 2026-08-21 → 2026-09-11, 16 dates | 5.00 today; re-recording in progress | 24-hour | **additional discovery** when verified | inside the roster's discovery window | yes, once verified | **no** | **no** |
| **NQ / MNQ** | forward | 0.25 | — | does not exist | none | no | no | **the only possible source** |

**No previously viewed block is described as pristine. There is no untouched
final out-of-sample block in existence today.**

### The credible-path test (§4), answered

**A path exists, and it is long.**

* Every strategy in §2 is a **QQQ** implementation. §22 is explicit that QQQ
  cannot validate an MNQ deployment.
* NQ at usable resolution totals 46 dates now, 62 after preservation — about
  **three months**, all of it discovery or sealed.
* Therefore final validation must come from **forward collection under the
  fully frozen allocator**, starting after Stage 3 freezes.
* 12 untouched months ≈ **252 sessions**. At the portfolio floor of 12 trades
  per month that is 144 trades in 12 months, so **150 trades needs about 13
  months of forward recording**, and the clock cannot start until Stages 1–3
  complete.
* Realistic earliest completion: **late 2027 to early 2028.**

**A second, unbudgeted cost sits on that path.** No NQ-native implementation of
ORB, pullback, IB 1R or ORB-Fib exists with a reproducing ledger. The only
NQ-native runner, `pullback.py`, produced 49 trades on 35 sessions and survived
0 of 12 of its own criteria. Porting each surviving strategy to NQ is required
before forward collection can even begin, and the one transfer this project has
already measured — the IB-mid pullback to SPY, IWM, IJH and EFA — gave a pooled
**−0.004 R** with 2 of 4 instruments positive. **Transfer is not free and this
desk has already measured it failing once.**

---

## 8. Stage 0 kill conditions

| # | condition | verdict |
|---|---|---|
| 1 | fewer than two strategies reproduce exactly | **does not fire** — thirteen sets reproduce byte-identically |
| 2 | entry-time regime variables unavailable | **does not fire** — entry minutes recovered for all thirteen; every permitted §7 variable is causally joinable |
| 3 | proposed pairings do not meet the sample floors | **partially fires** — R1, R3 and R4 clear 150; R3 only marginally after the efficiency split (≈182); the three strongest strategies clear 150 in **zero** cells |
| 4 | no credible final out-of-sample path | **does not fire, but the path is ~13 months of forward NQ collection plus an unbuilt NQ port** |
| 5 | priors cannot be declared without conditional outcomes | **does not fire** — §6 was declared from mechanism |
| 6 | the only possible allocator repeatedly selects strategies already known to be negative without a defensible conditional mechanism | **fires in substance.** All three live primary cells are filled by unconditionally negative strategies (−0.003, −0.057, −0.095); the positive strategies (+0.124, +0.207, +0.115, +0.061) are excluded by sample size, not by mechanism |
| 7 | regimes merely duplicate strategy entry rules | **fires for six of thirteen strategies** — the 10:00 and 10:30 block boundaries *are* the OR30, compression and IB entry windows |

**Two of seven kill conditions fire, one partially.**

---

## 9. Recommendation on feasibility

**RP-008 as specified is feasible to run and unlikely to be worth running. I
recommend a restricted Stage 1, not the full architecture.**

The reasons, in order of weight:

1. **The library has no time-of-day diversity.** 95% of 13,890 trades enter
   before 11:30 and 71% in a single ninety-minute block. A time-of-day allocator
   needs strategies that fire at different times; this library fires at one time.
   The closing block — a quarter of the trading day and one of the six proposed
   regimes — contains **57 trades in five and a half years**.

2. **Sample size and economics are anti-correlated.** The four strategies with
   positive unconditional expectancy (+0.006 to +0.207) reach 150 trades in
   **zero** regime cells between them, except IB 1R, whose three qualifying
   cells are all in the same block. The strategies that reach 150 everywhere are
   the five with negative expectancy. Any allocator that satisfies the sample
   floor is an allocator over losing strategies.

3. **Three of six regimes are no-trade by construction**, two because the brief
   says so and one (midday mean reversion) because **no valid mean-reversion
   strategy exists** — the VWAP family is unconditionally negative with a
   measured fill phantom, and RP-007 closed level rejection. The allocator
   therefore has at most three live cells before any result is seen.

4. **The regime axis partly restates the entry rules** for six of thirteen
   strategies, which is kill condition 7 and cannot be fixed by moving
   boundaries, because moving them after seeing this table is forbidden and
   moving them before would not change that OR30 cannot fire before 10:00.

5. **Deployment validation costs about thirteen months of forward NQ recording
   plus an NQ port that does not exist**, and the one cross-instrument transfer
   this desk has measured went from +0.185 R on QQQ to −0.004 R pooled
   elsewhere.

### What I recommend instead

**Authorise Stage 1 only, and only as the regime-validity question**: do the
frozen volatility and efficiency states create materially different forward
trading environments — different realised volatility, excursion distributions,
stop-out risk, holding time and path efficiency — measured **without any
strategy P&L**, exactly as §11 specifies.

That is cheap, it is the one question this data can answer well, and it is
strictly prerequisite. If the states do not separate, RP-008 closes at Stage 1
and nothing further is spent. If they do separate, the §6 sample table is still
waiting and the decision to proceed to Stage 2 can be taken with the regime
question already settled.

**I do not recommend proceeding to Stage 2 on the current library** without
first adding at least one frozen strategy that (a) fires outside 09:30–11:30 and
(b) is not unconditionally negative. No such strategy exists today, and
inventing one is outside RP-008 by §5.

---

## 10. Declared

No conditional expectancy was computed or viewed. No strategy was refitted, no
threshold moved, no target or stop changed, no filter added, no direction
altered. No closed strategy was reopened as a standalone candidate. Sealed NQ
dates were not read. 2016–2020 was not opened. No allocator was defined and no
Monte Carlo was run.

Stage 1 awaits separate approval.
