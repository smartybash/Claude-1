# RP-010 Stage 1 — order-flow impact, absorption and exhaustion

**Descriptive only.** No entry, stop, target or strategy is defined. No
expectancy, profit factor or drawdown is computed. The event window is excluded
from every forward outcome. Stage 2 is not opened.

Pre-registered at `reports/rp010_stage0_proposal.md`, commit **`bf57706`**.
Platform infrastructure at **`b3a9649`**. Harness `scripts/orderflow/rp010_stage1.py`,
report `scripts/orderflow/rp010_stage1_report.py`, raw output
`reports/rp010_stage1_output.txt`.

---

## 0. The gate, before any Stage 1 number

The reserved-pandas-column lint was implemented first, as instructed. It has two
halves, because the failure has taken two forms:

| half | what it does |
|---|---|
| `dataquality.assert_safe_columns(df)` | **raises** if any column of a built frame shadows a public `DataFrame` attribute. Every RP-010 frame passes through it |
| `dataquality.lint_reserved_columns(paths)` | **static AST scan** for `dict(agg=...)`, `{"pivot": ...}` and `df["mod"] = ...` in source |

`RESERVED` is derived from `dir(pd.DataFrame)` at import — **203 names** — not
from a remembered list. Bracket indexing is explicitly rejected as a fix in the
error message, because it only works if you remember to use it.

Full suite rerun after adding it:

```
PLATFORM GATE: PASS 115   FAIL 0
```

**115 assertions, 0 failures.** The harness runs the suite itself as a
subprocess and `sys.exit(2)`s if it fails, so a Stage 1 number cannot be
produced without it. The five platform conditions are all enforced in code:
the calendar owns every time window (`sessioncal.minutes_after_open(..., clock="UTC")`),
`orderflow_core` computes every aggression and impact figure, the suite gates
the run, the data-quality block is §1 below, and no overnight variable is read.

### Amendment declared before the amended run

The first pass of this harness omitted three items the brief asks for. They were
added and the harness rerun **before** this report was written; the declaration
sits in the script docstring above the code that computes them.

| added | why it is a diagnostic, not a change of construction |
|---|---|
| forward same-direction aggressive volume | a new *measurement* on the same events |
| near vs away from named levels | the brief itself marks it "diagnostic only"; levels are causal (prior RTH high/low/close, cumulative session VWAP, IB high/low after minute 60, round 50s) and contain no overnight variable |
| by-week at 15 min, by-session distribution | further cuts of the same outcomes |

**Nothing about the labels, thresholds, cooldown, cap or primary outcomes
changed.** The rerun reproduced every count and every primary figure exactly:
414 initiative candidates, 584 absorption candidates, 204 events, identical
means to three decimals.

---

## 1. Data quality (condition 4)

| check | measured |
|---|---|
| sessions measured | **44** |
| tick size, from actual prices | **0.25 on 44 of 44** |
| prices off the 0.25 grid | **0.000000** (max over sessions) |
| aggressor labels present | **`B`/`S` on 44 of 44** |
| aggressor nulls | **0** |
| timestamps monotonic | **True on all 44** |
| largest consecutive-print jump | **51.00 points** against a 100-point roll threshold → **no contract roll** |
| median RTH prints per session | **354,695** |

Resolution is measured from prices, never inferred from the filename. No
5-point recording is used. Sealed dates (June 2026 and 2026-07-23) remain
unread.

---

## 2. Counts, before any forward outcome

| | |
|---|---|
| NQ dates on disk | 64 |
| excluded — measured resolution 5.00 | 18 |
| excluded — not a full cash session | 2 |
| **sessions used** | **44** |
| threshold warm-up sessions excluded | 10 |
| **sessions producing labelled windows** | **34** |

Discovery block: **2026-07-06 → 2026-08-20**, 34 contiguous sessions, all
previously examined and so treated as discovery only. No out-of-sample block
was opened.

| | |
|---|---|
| total 30-second windows | 33,437 |
| warm-up windows (unlabelled) | 7,598 |
| ORDINARY windows | 24,841 |
| INITIATIVE candidates before cooldown | 414 |
| ABSORPTION candidates before cooldown | 584 |
| **events after cooldown and cap** | **204** |
| excluded as capped | 725 |
| excluded as extended (same side inside 5 min) | 37 |
| excluded as flipped (opposite side inside 5 min) | 32 |
| **events per session** | **6.00** |
| events per month | 102.0 over 2 months |

| state | buy | sell | total | sessions | per session |
|---|---|---|---|---|---|
| INITIATIVE | 38 | 46 | **84** | 33 | 2.47 |
| ABSORPTION | 66 | 54 | **120** | 34 | 3.53 |

Both states appear in **more than 20 independent sessions** (33 and 34), so
neither is exploratory under the brief's rule and mechanism claims are
admissible.

**The cap binds on every single session — exactly 6.00 events per session.**
998 candidates compete for 204 slots and 725 are discarded as capped. The cap
is therefore not a safety valve, it is a **first-come filter**: the surviving
events are the earliest six of each session. That is visible directly:

| block (minutes after open) | INITIATIVE | ABSORPTION |
|---|---|---|
| 05–30 open | 1 | 5 |
| 30–120 morning | 33 | 56 |
| 120–270 midday | 50 | 59 |
| **270–385 close** | **0** | **0** |

**Zero events in the closing block, on all 34 sessions.** This is a property of
the frozen construction, not of the market. It was frozen before the run and is
not changed now, but it bounds every reading below: RP-010 measures the *first
six* order-flow extremes of a session, and says nothing about the close.

Causal thresholds, trailing ten completed sessions only:

| threshold | median | range |
|---|---|---|
| aggression, p90 imbalance | 0.2496 | [0.2258, 0.2588] |
| high impact, p80 ticks/1k | 154.67 | [115.37, 182.34] |
| low impact, p20 ticks/1k | 47.25 | [39.67, 60.67] |

**Zero cases, as the brief requires them stated.** Zero total volume →
imbalance 0.0, never NaN (0 windows occur). Zero delta → `ticks_per_delta` 0.0
and the window is **excluded from forward outcomes** because it has no
aggression direction (257 windows). Zero price progress → impact 0.0. Zero
displayed depth is not used at all: depth is a diagnostic stream and **no
RP-010 figure divides by it**, so the degenerate case cannot arise.

---

## 3. Multiple-testing burden and MDE, stated before the results

The forward grid is 2 states × 6 horizons = **12 primary cells**. With the
mandatory buy/sell split that becomes 24, the eight control arms add 48, and the
load-bearing block adds 42 — roughly **150 displayed forward-outcome cells**.
Bonferroni over the 12 primary cells alone requires |t| ≈ **3.2**.

Minimum detectable effect at 80% power, two-sided 5%, computed from the
**session-clustered** standard error (the session is the independence unit, so
n = 33 or 34, not 84 or 120):

| state | horizon | clustered SE | MDE (2.80 × SE) |
|---|---|---|---|
| INITIATIVE | 300 s | 3.26 pts | **±9.1 pts** |
| INITIATIVE | 900 s | 4.58 pts | **±12.8 pts** |
| ABSORPTION | 300 s | 3.50 pts | **±9.8 pts** |
| ABSORPTION | 900 s | 6.17 pts | **±17.3 pts** |

**Stated before the results: this design cannot detect anything smaller than
about 9 to 17 NQ points at 34 sessions.** The commercially interesting effect
is 6 points. The study is therefore powered to detect only an effect far larger
than the one it would need to find, and any cell that does not clear its MDE
must be read as *not established*, whichever way it points.

---

## 4. Forward outcomes — direction-adjusted, NQ points

Positive = price continued in the aggression direction. Event window excluded.

**INITIATIVE (n = 84)**

| horizon | mean | median | MFE | MAE | cont% | rev% | clustered t |
|---|---|---|---|---|---|---|---|
| 30 s | **+1.363** | +0.125 | 9.78 | 7.28 | 50.0 | 50.0 | +1.71 |
| 60 s | **+2.012** | +2.375 | 13.50 | 10.38 | 57.1 | 42.9 | +1.42 |
| 180 s | **−4.161** | −1.250 | 21.41 | 22.10 | 45.2 | 54.8 | −1.00 |
| 300 s | **−5.333** | −6.375 | 25.77 | 29.48 | 40.5 | 59.5 | −1.08 |
| 600 s | **−6.598** | −6.625 | 34.48 | 39.24 | 40.5 | 59.5 | −1.30 |
| 900 s | **−3.330** | −1.125 | 39.65 | 43.24 | 48.8 | 51.2 | −0.73 |

**ABSORPTION (n = 120)**

| horizon | mean | median | MFE | MAE | cont% | rev% | clustered t |
|---|---|---|---|---|---|---|---|
| 30 s | +0.487 | +1.250 | 8.50 | 8.80 | 55.0 | 44.2 | +1.05 |
| 60 s | +1.123 | +1.500 | 12.73 | 12.65 | 54.2 | 45.0 | +0.76 |
| 180 s | −0.463 | +1.125 | 20.36 | 20.44 | 51.7 | 47.5 | +0.16 |
| 300 s | −0.106 | −0.875 | 24.98 | 24.53 | 49.2 | 50.8 | +0.45 |
| 600 s | +3.783 | +7.125 | 34.26 | 32.75 | 52.5 | 47.5 | +0.88 |
| 900 s | **+8.673** | +7.125 | 43.13 | 37.36 | 56.7 | 43.3 | +1.72 |

**ORDINARY (n = 24,630)**

| horizon | mean | median | cont% | clustered t |
|---|---|---|---|---|
| 30 s | −0.140 | +0.000 | 49.0 | −1.60 |
| 60 s | −0.228 | +0.000 | 49.2 | −2.25 |
| 180 s | −0.380 | −0.250 | 49.1 | −2.87 |
| 300 s | −0.461 | −0.250 | 49.6 | −2.63 |
| 600 s | +0.829 | +0.000 | 50.0 | +2.86 |
| 900 s | **+2.070** | +1.000 | 50.9 | **+4.75** |

**Both states point the wrong way.** Initiative — the state defined by heavy
one-sided aggression that *moves* price — continues for 60 seconds and then
**reverses**, giving back the early gain and ending −3.3 to −6.6 points behind.
Absorption — heavy one-sided aggression that *fails* to move price — does not
fail; it **continues**, ending +8.7 points ahead at fifteen minutes. The
hypothesis predicted exactly the opposite in both cases.

The ORDINARY column is the reason to be careful with both: on 24,630 windows the
ordinary drift at 900 s is **+2.070 with t = +4.75**, far more significant than
either treatment, which tells you the 900-second window has a mechanical
direction-adjusted drift that every state inherits.

Path landmarks, median seconds:

| state | t continue (+6 pts) | t reverse (−6 pts) | t back to origin | % broke event extreme | % returned to origin |
|---|---|---|---|---|---|
| INITIATIVE | 10 | 28 | 193 | 85.7 | **90.5** |
| ABSORPTION | 21 | 28 | 357 | 73.3 | 72.5 |
| ORDINARY | 29 | 28 | 260 | 80.4 | 73.7 |

Initiative reaches ±6 points fastest (10 s) **and returns to its own origin most
often (90.5%)** — a fast move that is then given back, which is the same story
the mean tells.

### Additional same-direction aggressive volume after the event

Direction-adjusted net aggressive contracts in the forward slice, mean per event:

| state | 30 s | 60 s | 180 s | 300 s | 600 s | 900 s |
|---|---|---|---|---|---|---|
| INITIATIVE | +13.2 | +15.5 | −22.5 | −14.9 | +22.4 | +87.0 |
| ABSORPTION | −21.2 | −19.8 | −48.1 | −51.2 | +20.0 | +146.0 |
| ORDINARY | −0.3 | −0.6 | −0.3 | +1.5 | +20.8 | +40.5 |

Follow-on aggression tracks the price path and does not lead it. Absorption is
followed by **net opposing** aggression for the first five minutes (−51 contracts
at 300 s) while its price is flat, then by same-direction aggression at 900 s
once the price has already moved. Nothing here identifies an event early.

### Buy and sell separately — never pooled

| state | side | n | 30 s | 60 s | 180 s | 300 s | 600 s | 900 s |
|---|---|---|---|---|---|---|---|---|
| INITIATIVE | buy | 38 | +1.941 | +2.645 | −0.553 | +0.401 | −2.658 | **−2.263** |
| INITIATIVE | sell | 46 | +0.886 | +1.489 | −7.141 | −10.071 | −9.853 | **−4.212** |
| ABSORPTION | buy | 66 | +1.871 | +1.027 | +2.985 | +4.989 | +11.326 | **+18.742** |
| ABSORPTION | sell | 54 | −1.204 | +1.241 | −4.676 | −6.333 | −5.435 | **−3.634** |

**Absorption is entirely one-sided.** The whole +8.673 at 900 s is buy
absorption at +18.742; sell absorption is **−3.634**, the opposite sign. A
mechanism that only works when the aggressor is a buyer, on 66 events across two
summer months, is a directional bet on the sample, not a microstructure effect.

---

## 5. Controls

Every control's synthetic fixture passes in `test_platform.py`. Sample size and
matching coverage are reported before the outcome, as required.

Matched-random coverage: **190 of 204 events (93.1%)**, 14 unmatched.

| control | arm | n | 180 s | 300 s | 600 s | 900 s |
|---|---|---|---|---|---|---|
| 1 impact labels shuffled | INITIATIVE | 414 | +0.955 | +0.431 | +1.667 | +3.611 |
| 1 impact labels shuffled | ABSORPTION | 584 | +0.047 | +0.637 | +0.053 | −0.619 |
| 2 same progress, ordinary aggression | INITIATIVE-like | 5,644 | −1.048 | −0.933 | +2.958 | **+7.118** |
| 2 same progress, ordinary aggression | ABSORPTION-like | 20,230 | −0.247 | −0.343 | −0.111 | +0.245 |
| 3 matched random times | matched | 190 | −1.989 | +1.441 | +4.593 | **+13.442** |
| 4 high volume, balanced delta | — | 1,441 | −1.685 | −1.567 | +6.601 | **+6.602** |
| 5 opposite direction | INITIATIVE | 84 | +4.161 | +5.333 | +6.598 | +3.330 |
| 5 opposite direction | ABSORPTION | 120 | +0.463 | +0.106 | −3.783 | −8.673 |
| **TREATMENT** | **INITIATIVE** | **84** | **−4.161** | **−5.333** | **−6.598** | **−3.330** |
| **TREATMENT** | **ABSORPTION** | **120** | **−0.463** | **−0.106** | **+3.783** | **+8.673** |

**The decisive row is control 3.** Random times inside the same sessions,
matched on time of day (±30 min) and on |delta| decile, return **+13.442 points
at 900 s — larger than absorption's +8.673 and with the opposite sign to
initiative's −3.330.** Volatility-and-time matching does not weaken the
treatment; it **beats** it. Control 4 (high volume, balanced delta — volume
without one-sidedness) returns +6.602, three-quarters of absorption's figure
with none of its defining property.

Control 5 is an identity by construction (the negative of the treatment) and is
reported for completeness only; it carries no independent information.

### Near versus away from a named level — diagnostic only

Median distance from an event's terminal price to the nearest eligible causal
level: **8.03 points**. Near = within 10 ticks.

| state | where | n | 300 s | 900 s |
|---|---|---|---|---|
| INITIATIVE | near | 15 | −2.683 | −2.617 |
| INITIATIVE | away | 69 | −5.909 | −3.486 |
| ABSORPTION | near | 25 | −0.650 | **+13.710** |
| ABSORPTION | away | 95 | +0.037 | +7.347 |

Absorption near a level reads better than absorption away from one, but on **25
events** against an MDE of ±17 points this is noise, and RP-007 already closed
the level family on the grounds that named levels do not outperform nearby
arbitrary prices. **The primary result uses no level at all**, as the brief
requires.

---

## 6. Is impact load-bearing?

Each row is the top decile of one variable, direction-adjusted, over all
labelled windows — the brief's test of whether progress-per-unit-volume adds
anything beyond its components.

| selector | n | 300 s | 600 s | 900 s |
|---|---|---|---|---|
| delta magnitude alone | 2,585 | +0.513 | +9.247 | **+15.733** |
| price progress alone | 2,638 | −1.065 | +8.330 | **+15.292** |
| total volume alone | 2,571 | +0.081 | +12.289 | **+15.537** |
| local volatility alone | 3,015 | −0.124 | +2.029 | +5.069 |
| impact alone (ticks/1k) | 2,563 | −0.839 | −0.020 | +2.345 |
| **INITIATIVE** (aggression AND high impact) | 84 | −5.333 | −6.598 | **−3.330** |
| **ABSORPTION** (aggression AND low impact) | 120 | −0.106 | +3.783 | **+8.673** |

**This is the clearest result in the study, and it is a negative one.** Every
one of the three single variables the brief named — delta magnitude, price
progress, total volume — returns **+15.3 to +15.7 points at 900 s on ~2,600
windows each**. The combined states return −3.3 and +8.7 on 84 and 120 events.

The brief's rule is explicit: *"If either delta alone or price progress alone
performs equally well, the combined mechanism fails."* They do not perform
equally well — **they perform roughly twice as well, on thirty times the
sample**. Impact alone, the variable the whole family is built on, is the
**weakest** selector in the table at +2.345, barely above the ordinary drift of
+2.070.

Conditioning on impact does not add information to aggression. It **destroys**
information that raw aggression already carried.

---

## 7. Independence and concentration

The session is the independence unit.

| state | horizon | event mean | clustered | t | sessions | sessions + | LOO min | LOO max | −best 1 | −best 3 | best-3 share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| INITIATIVE | 300 s | −5.333 | −3.518 | −1.08 | 33 | 13 | −4.827 | −2.511 | −4.827 | −7.082 | −83.0% |
| INITIATIVE | 900 s | −3.330 | −3.341 | −0.73 | 33 | 16 | −4.750 | −0.805 | −4.750 | −6.917 | −88.2% |
| ABSORPTION | 300 s | −0.106 | +1.573 | +0.45 | 34 | 17 | −0.240 | +2.689 | −0.240 | −2.603 | 250.9% |
| ABSORPTION | 900 s | **+8.673** | **+10.608** | **+1.72** | 34 | 20 | +7.495 | +12.524 | +7.495 | **+3.287** | **71.7%** |

**No cell survives clustering.** The largest |t| in the study is **1.72**,
against 1.96 unadjusted and ≈3.2 after Bonferroni over the 12 primary cells. The
best cell (+10.608) sits well below its own MDE of ±17.3.

**Absorption at 900 s does not survive removal of the best three sessions:
+10.608 → +3.287.** Three sessions out of 34 carry **71.7%** of the total. At
300 s the concentration is worse than total: the best three contribute 250.9% of
a near-zero sum, i.e. the remaining 31 sessions are collectively negative.

Sessions pointing the right way: 20 of 34 for the best cell — a 59% hit rate on
a coin-flip baseline.

By ISO week (mean points per event):

| week | ABSORPTION 300 s | INITIATIVE 300 s | ABSORPTION 900 s | INITIATIVE 900 s |
|---|---|---|---|---|
| 28 | +6.03 | −5.73 | +33.00 | −4.40 |
| 29 | +9.67 | −4.15 | +32.50 | −7.71 |
| 30 | +7.03 | −6.52 | +11.15 | +5.66 |
| 31 | **−17.51** | −11.43 | **−34.25** | −28.75 |
| 32 | +6.08 | +9.90 | +19.44 | +18.58 |
| 33 | −6.03 | −5.90 | +11.63 | +7.10 |
| 34 | −1.40 | −14.42 | −1.77 | −8.64 |

Absorption at 900 s is positive in five weeks of seven and **−34.25 in week 31**,
a swing of 67 points between adjacent weeks. Initiative changes sign three times.

Per-session distribution at 900 s:

| state | sessions | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|
| INITIATIVE | 33 | −84.50 | −16.58 | −0.38 | +17.50 | +41.75 |
| ABSORPTION | 34 | −52.62 | −12.56 | +4.12 | +28.62 | **+113.33** |

One session contributes **+113.33 points per event**. The median session
contributes +4.12. This is not a distribution with a location; it is a
distribution with an outlier.

---

## 8. Commercial feasibility

| | |
|---|---|
| median local ATR (1-minute, measured) | **21.55 NQ points** |
| minimum viable container (RP-009, 1.2 × ATR) | 25.86 points = 103 ticks |
| round turn | 2.0 points = **7.7% of that risk** |
| movement needed to clear 3× cost | 6.00 points = 24 ticks |

6.00 points and 24 ticks are the same threshold in two units, so the brief's two
columns are reported once on MFE (was the move ever available) and once on the
terminal return (was it there at the horizon). The terminal column is the honest
one for a timed exit.

| state | horizon | median | mean | net of 2 pt | MFE ≥ 6 pt | terminal ≥ 6 pt | vs 1.2 ATR |
|---|---|---|---|---|---|---|---|
| INITIATIVE | 300 s | −6.375 | −5.333 | −7.333 | 82.1% | 35.7% | **−0.206** |
| INITIATIVE | 900 s | −1.125 | −3.330 | −5.330 | 91.7% | 41.7% | **−0.129** |
| ABSORPTION | 300 s | −0.875 | −0.106 | −2.106 | 88.3% | 40.8% | **−0.004** |
| ABSORPTION | 900 s | +7.125 | +8.673 | **+6.673** | 96.7% | 50.8% | **+0.335** |

Three of the four cells are **negative before costs**. The single positive cell,
absorption at fifteen minutes, nets +6.673 points — 0.335 of the minimum viable
container — and its terminal ≥ 6-point rate is **50.8%, a coin flip**. The gap
between the MFE column (96.7%) and the terminal column (50.8%) is the whole
problem: the move is usually available at some instant and usually gone by the
horizon, and Stage 1 is forbidden from defining the exit that would harvest it.

Frequency is not the binding constraint: **100.0%** of events occur with at
least 15 minutes before the close, and 102.0 events/month raw leaves **34.0/month**
at one-third retention, comfortably above the 4/month floor.

---

## 9. Pass conditions — 2 of 11

| # | condition | verdict |
|---|---|---|
| 1 | Initiative and absorption create different future paths | **met, weakly** — −3.330 vs +8.673 at 900 s, but neither separates from controls |
| 2 | Initiative predicts continuation | **FAIL** — continues 60 s, then reverses to −6.598; cont% 40.5 at 300 s |
| 3 | Absorption predicts failure or reversal | **FAIL** — absorption *continues*, +8.673, cont% 56.7 |
| 4 | Both buying and selling point correctly | **FAIL** — absorption buy +18.742, sell −3.634 |
| 5 | Progress-per-volume is load-bearing | **FAIL** — impact alone +2.345 is the weakest selector in the table |
| 6 | Matched controls materially weaker | **FAIL** — matched random times +13.442 exceeds the treatment |
| 7 | Survives session clustering | **FAIL** — max \|t\| = 1.72 |
| 8 | Survives removal of the best three sessions | **FAIL** — +10.608 → +3.287 |
| 9 | Appears across multiple weeks | **FAIL** — −34.25 in week 31; three sign changes |
| 10 | Clears 2-point costs with meaningful headroom | **FAIL** — one cell of four is positive, at 0.335 × container and a 50.8% terminal hit rate |
| 11 | Post-confirmation frequency ≥ 4/month | **met** — 34.0/month |

## 10. Kill conditions — 8 of 10 fire

| # | condition | fires? |
|---|---|---|
| 1 | Delta magnitude alone performs similarly | **YES** — +15.733 vs −3.330 / +8.673. It performs *better* |
| 2 | Price progress alone performs similarly | **YES** — +15.292 |
| 3 | Total volume alone performs similarly | **YES** — +15.537 |
| 4 | Only buying or only selling works | **YES** — absorption buy +18.742, sell −3.634 |
| 5 | A few sessions create most of the result | **YES** — best-3 share 71.7%; removing them leaves +3.287 |
| 6 | Volatility and time matching removes the relationship | **YES** — matched control +13.442 *exceeds* the treatment |
| 7 | Aggressor classification fails synthetic or real checks | **no** — 115/115 assertions pass; `B`/`S` on 44 of 44 sessions, zero nulls |
| 8 | Forward movement too small relative to costs and viable risk | **YES** — three of four cells negative before costs; the best is 0.335 × container |
| 9 | Controls reproduce the treatment result | **YES** — controls 2, 3 and 4 all exceed it at 900 s |
| 10 | Initiative and absorption do not produce opposite forward patterns | **no** — they *are* opposite. But each is the opposite of its own hypothesis |

Kill condition 10 is worth stating precisely rather than scoring loosely. The
two states do separate, and they separate in opposite directions — which is what
the condition asks. **The signs are simply inverted relative to the mechanism.**
That is not a rescue: an inverted, uncontrolled, concentrated, one-sided
separation that any single raw variable doubles is not evidence of a
microstructure effect. It is evidence that the 900-second window has a drift,
that the drift is larger when volume is larger, and that conditioning on impact
selects a smaller and noisier slice of it.

---

## 11. What this study did establish

Three things are worth carrying forward, none of them a tradeable edge:

1. **Raw aggression size carries more forward information than any impact
   ratio.** Top-decile delta, progress and volume all return ≈ +15.5 points at
   900 s on ~2,600 windows. That is a real, if unexploited, regularity of this
   sample, and it is the opposite of the footprint-reading premise.
2. **The 900-second direction-adjusted drift is mechanical.** ORDINARY returns
   +2.070 with t = +4.75 on 24,630 windows. Any future order-flow work must
   benchmark against that drift, not against zero.
3. **A six-event cap that binds on every session is a first-come filter, not a
   safety valve.** It removed the entire closing block from the study. Any
   future event-based design must size the cap against the observed candidate
   rate before freezing it, or stratify by block.

## 12. What this study cannot say

- Nothing about the **closing block** (zero events, by construction).
- Nothing about **out-of-sample behaviour**: 34 contiguous, previously examined
  sessions over two summer months are a discovery screen. No OOS block was
  opened and none is needed, because the family closes on discovery.
- Nothing about **MBO-based absorption**: `data/mbo/` is empty and no MBO claim
  was made.
- Nothing about **alternative percentiles, window lengths or cooldowns**. One
  construction was declared and one was run. The rejection is of *that*
  construction; it is not a proof that no order-flow construction can work.

---

## Verdict

> **Order flow mechanism rejected, close RP 010.**

Eight of ten kill conditions fire and nine of eleven pass conditions fail. The
two states point opposite to their hypotheses; absorption works only on the buy
side; three single raw variables each return roughly twice the best treatment
figure on thirty times the sample; matched random times inside the same sessions
beat both treatments; and three sessions out of 34 carry 71.7% of the only
positive cell, which does not survive their removal and never clears its own
minimum detectable effect.

No Stage 2. No absorption-reclaim or initiative-continuation confirmation is
proposed. No entry, stop or target was defined at any point in this stage.
