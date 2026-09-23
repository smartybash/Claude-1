# Correction ledger

Every factual or implementation error found in this project, what it affected,
whether the affected result was rerun, and where the corrected result sits.

**Reruns were decided by dependency, not by reflex.** Where an error provably
could not change a verdict, that is stated and the result was not rerun.

---

## 1. ATAS Step multiplier confused with an absolute price increment

**My error, 2026-09-21.** I instructed "set price step to 0.25". `Step` is a
**tick multiplier**, not a price. The proof was already available to me:

- `OFT.Platform.Core.ViewModels.Charting.CandleDataSeriesScaler` exposes
  **`Int32 Step { get; set; }`** — an integer, which cannot express 0.25.
- `TickSize` is **`Decimal TickSize { get; }`** — read-only, no setter.
- Step 20 × 0.25 = 5.00 and Step 1 × 0.25 = 0.25, matching the observed
  recordings exactly.

**Worse: this repo already recorded the answer.** Commit `5509fcc` states the
old files had *"a five point price step, twenty times the real tick"*. I
contradicted a finding already in the project instead of checking it.

| | |
|---|---|
| affected results | **none** — it was an instruction, never executed |
| affected documents | `reports/trendline_forward_audit.md` §1 |
| rerun | n/a |
| corrected in | this commit |

**Correct setting: ATAS Step = 1. Required measured output gap: exactly 0.25.**

---

## 2. File format used as a proxy for resolution

`.br` was treated as true-tick and `.gz` as degraded. Invalid:
`TAPE_NQ_20260820.csv.gz` is plain **and** full 0.25 resolution with the same
505,997 prints as the `.br`. Conversely `TAPE_NQ_20260820_run2.csv.gz` is 5.00.
**Format and resolution are independent.**

| | |
|---|---|
| affected results | the bounded reconstruction's session selection (`a2148d2`) |
| **dependency check** | re-measured every non-sealed date by actual price gap: **36 dates at 0.25 ending 2026-08-20, 17 at 5.00, none at 0.25 after 2026-08-20** — identical to the format-based set |
| rerun | **not required.** The selected sessions are the same files; no input changed |
| corrected in | `f1190aa`, refined this commit |

---

## 3. Verification return code discarded

`main()` returned a status code that `__main__` threw away, so the Step 1 gate
printed `*** STOP ***` and exited 0. A gate that cannot fail the process is not
a gate.

| | |
|---|---|
| affected results | **none** — the gate had never been run in anger |
| rerun | n/a |
| corrected in | `f1190aa` (`sys.exit(main() or 0)`) |

---

## 4. Loader selecting files by date or format rather than measured quality

`true_tick_files()` keyed on the encoded-format flag. Now it measures every
candidate and selects **the finest valid grid, then the most prints** — the
"best verified coverage" tie-break, which previously was claimed in the printed
label but not implemented in the code.

| | |
|---|---|
| affected results | reconstruction session set (`a2148d2`) |
| **dependency check** | selection is unchanged on every date (see §2) |
| rerun | **not required** |
| corrected in | this commit |

---

## 5. Coverage computed as total tape span over an RTH denominator

The recorder divided the whole-data span by the RTH window length, so an
overnight recording reported **400%** coverage — and every good file would have.

| | |
|---|---|
| affected results | the recorder's own status reporting, and any session-inventory decision made from it |
| corrected behaviour | window clock tracked separately from data clock; two lines printed — total span **explicitly labelled "not a coverage figure"** — and RTH coverage against the configured window with a short-session warning under 97% |
| rerun | **yes** — the affected sessions were re-inventoried; see §6 for the set change |
| corrected in | **`7792edb`** |

---

## 6. BBO gated differently from the tape

**A real bug, not a reporting one.** Best bid/ask was gated on `InSession`
while the tape was gated on `TapeAllHours`. With all-hours tape the recorder
**kept every overnight trade and discarded every overnight quote.**

| | |
|---|---|
| affected results | BBO coverage on all sessions recorded before the fix — the reason BBO spans fewer dates than the tape |
| corrected behaviour | the quote now shares the tape's gate and on/off switch; off-session rejections counted per stream |
| rerun | **not re-derivable** — discarded quotes cannot be recovered. Affected dates carry reduced BBO coverage permanently, which is why the forward audit resolves on the tape and treats BBO as a diagnostic |
| corrected in | **`7792edb`** |

---

## 7. Cumulative order events mixed with fill rows

Events and rows were summed as if the same unit. One depth snapshot writes a
row per changed level; one aggressive order writes a row for itself **plus one
per fill**. The totals never could balance.

| | |
|---|---|
| affected results | status-file row accounting only |
| corrected behaviour | per-stream block is **events only**, with the exact identity `recv = wrote + off-session + throttled` and an `UNACCOUNTED` marker when a path is uncounted; rows reported separately (`ORDER rows` and `FILL rows` are now distinct lines, fills carrying `parent_seq`) |
| rerun | **not required** — no analytical result consumed those totals |
| corrected in | **`7792edb`** |

---

## 8. Signal implemented as a touch instead of a crossing

In the bounded reconstruction, entries fired whenever a bar touched the extended
trendline, rather than crossing it. That produced **88–111 trades/session
against the ledger's 28.6.**

| | |
|---|---|
| affected results | the first calibration pass, **never reported as a result** |
| corrected behaviour | prior close must sit on the other side of the line |
| **effect of the fix** | frequency fell to **28.6/session at pivot 3/3, stop 1.2 — exactly the ledger figure** |
| rerun | **yes, in full.** Every number in `a2148d2` is post-fix |
| corrected in | **`a2148d2`** |

---

## 9. `DataFrame.pivot` method collision with the `pivot` column

`R.pivot == "3/3"` compared the pandas **method** to a string, always False, so
the decision loop skipped all nine specifications and printed an empty table.

| | |
|---|---|
| affected results | the decision table in the reconstruction run |
| **dependency check** | the per-specification statistics were already correct in `trendline_recon.csv`; only the summary loop was broken |
| rerun | **recomputed from the CSV.** The verdict — **0 of 9 pass** — was unchanged |
| corrected in | **`a2148d2`** (`R["pivot"]`) |

---

## 10. Strategy runners dropping or altering a pre-registered rule

**Searched; no undeclared instance found.** Three deviations exist and all three
were declared *before* the affected run:

| deviation | where | declared |
|---|---|---|
| ORB-Fib outburst measured against the required leg rather than the literal 50% rule | `orb_fib.py` | **yes** — amended at `c9196d1` on counts alone, before any expectancy was displayed, with the literal funnel reported alongside |
| compression runner flattens at each tape day's end (archive not contiguous) | `compression_run.py` | **yes** — printed in the run header and in the result |
| IB 1R indicator excludes the entry bar from the exit search | `IbOneR.cs` | **yes** — matches `run_trade`'s `i+1` scan so live reconciles with the backtest; flagged in red on the panel when it would have mattered |

One genuine self-caught error in this class: the **frozen candidate was first
reproduced at the wrong bar resolution** (QQQ 5-minute, n=675, +0.0578) when the
rule was frozen on 1-minute. Corrected to `reopen_study.test1` filtered to
`seq == 1`, reproducing the ledger to four decimals (n=685, +0.0612). Verdict
unchanged either way (−0.047 vs −0.0433). Corrected in **`6c99ff1`**.

---

## Summary

| # | error | result changed? | rerun |
|---|---|---|---|
| 1 | Step vs price increment | no — instruction only | n/a |
| 2 | format as resolution proxy | **no** — same 36 dates | not required |
| 3 | exit code discarded | no | n/a |
| 4 | loader selection rule | **no** — same files | not required |
| 5 | coverage denominator | yes, inventory | **done** (`7792edb`) |
| 6 | BBO gate | yes, permanently | **not recoverable** |
| 7 | events vs rows | no — reporting only | not required |
| 8 | touch vs crossing | yes, calibration | **done** (`a2148d2`) |
| 9 | `DataFrame.pivot` collision | **no** — verdict identical | recomputed |
| 10 | pre-registered rule altered | none undeclared | n/a |

**Two errors changed a reported number (5, 8). One is permanently
unrecoverable (6). The rest were caught before they could.**

## Contradicting evidence already committed to the repository

**2. FOMC announcement weekday hardcoded to Wednesday** (`a971882`, corrected
`b7becac`). The pre-registration fixed entry to Tuesday close, exit to Wednesday
close, and gated on every announcement date being a Wednesday. Three of the 84
events are Thursdays — the November meeting shifts to Wed-Thu in election and
midterm weeks (2018-11-08, 2020-11-05, 2024-11-07). The gate would have rejected
valid events and the fill construction was wrong for them.

The fact was **already in the repository**: the commit that added
`data/events/fomc.csv` (`a306378`, 2026-09-18) states that "the single non
Wednesday is the November 2024 meeting that shifted for the election, which is
correct rather than an error." The pre-registration was written three days later
and contradicted it.

Caught pre-run by independently recalling the 2021-2026 dates to validate the
recall method, which surfaced the weekday as a side effect. Nothing had been run,
so no result changed.

**This is the same failure mode as entry 1 (ATAS `Step` vs `TickSize`,
`5509fcc`): evidence already on disk, contradicted rather than checked.** Both are
specification errors. Neither would have raised an exception; both would have
produced plausible-looking numbers.

**3. Overnight cleaning estimator systematically removed genuine extremes**
(proposed `1a65e8c`, measured `rp002_stage1_result.md` §1). The two-bar
confirmation rule -- clean high = second-largest bar high, ties kept -- was
proposed as "mildly conservative on clean sessions" and as targeting the
documented bad-print defect "exactly". It did neither. The maximum of ~330
overnight bar highs is almost never tied, so the second-largest is almost always
strictly below it: the rule changed **98.1% of sessions** and cut the mean
overnight range from 117.6 to 91.7 bps, a 22% reduction.

The error was reaching for a zero-parameter rule. Removing bad prints needs a
**magnitude** test -- is the extreme far from its neighbours -- not a **count**
test. Trading away a tunable parameter introduced a systematic bias worse than
the parameter would have been.

Caught by reporting cleaning impact before any state comparison, as the
pre-registration required. The rule was frozen and was NOT changed after the
fact. It did not cause the RP-002 verdict -- all states share the estimator, so
the comparisons are internally consistent -- but it biases absolute ranges low
and makes the "outer third" marginally easier to reach, and it would have
contaminated any Stage 2. A future overnight-range family must not reuse it.

**4. `DataFrame.mod` column collision — a recurrence of entry 1's failure mode**
(`rp003_stage1.py`, caught pre-result). A column named `mod` (minute-of-day) was
accessed as `EXT.mod`, which resolved to the pandas `DataFrame.mod` **method**
rather than the column. This is the same class of error as the `R.pivot` bug in
the trendline work.

Two differences from the original. It raised `TypeError` immediately rather than
failing silently, so it cost nothing. And the fix was **renaming the column to
`tod_min` / `tod`** rather than switching to bracket indexing, because bracket
indexing relies on remembering to use it every time whereas a non-colliding name
cannot be got wrong.

Standing rule going forward: **never name a DataFrame column after a pandas
method** (`mod`, `pivot`, `min`, `max`, `sum`, `count`, `index`, `size`, `mean`,
`std`, `var`, `shift`, `rank`, `apply`, `all`, `any`).

**5. A completeness filter imported from a family where it was correct**
(`rp006_stage1.py`, caught at run time before any result was reported). The
>=380-aligned-bar session filter was carried from RP-003/RP-004, where the whole
one-minute return series was the object of study, into RP-006, where the design
reads only six timestamps per session.

IJH does not print in roughly 16 minutes of a typical session -- median 374 bars
against 390 for QQQ, SPY and IWM. Applied to the 4-way intersection the filter
dropped **292 of 503 sessions (58%)**, and the 79 surviving 2021 sessions were
consumed entirely by the 20+60 session warm-up, leaving a discovery block that
was **2022-only**. Pass condition 5 (present in both discovery years) was
unachievable by construction: the specification could not pass its own gate.

The filter was rejecting sessions for IJH's trade frequency, which the design
never reads. IJH's 10:00 print is stale on only 1.22% of sessions, comparable to
QQQ at 1.00%.

Two further errors in the same harness: the shuffled-rankings control permuted
outcome COLUMNS rather than the ranking identity, so its means were identical to
the true ranking to two decimals and it tested nothing; and the random-pair
control recorded a value only when the drawn pair coincided with the realised
pair, collapsing n from 129 to 34-45.

**Standing lesson: a filter is part of the hypothesis, not boilerplate.** Do not
carry a data-completeness rule between families without re-deriving it from what
the new design actually measures.

**Also recorded:** the >60% rank-domination threshold cannot be satisfied by a
three-instrument ranking. Each session places one instrument strongest and one
weakest, so two of three are at an extreme and the expected rate is 66.7% for
every instrument. The flag fires unconditionally. Domination tests must be stated
as deviations from the structural baseline, not as absolute percentages.

---

## 6. Approach-side convention inverted, and IB levels read before they existed

Both found in RP-007 Stage 1A1 **before any outcome was read**, by looking at
the interaction counts. Both are recorded because the way they were caught is
the reusable part.

### 6a. The support/resistance label was backwards

`side = +1 if H[i-1] < lo_b` assigned **support** when the previous bar sat
entirely *below* the zone. Approaching from below puts the level overhead, which
is a **resistance** test. The outcome function then measured penetration and
reclaim in the wrong direction for every interaction in the study.

| | before | after |
|---|---|---|
| IB high | **1,307 support / 0 resistance** | 71 / 803 |
| prior-day high | 429 / 233 | 234 / 422 |
| extended-hours low | 27 / 449 | 441 / 30 |

**It was visible in the counts, not in the results.** A level defined as the
maximum of the morning cannot be approached from above 100% of the time. The
counts-before-outcomes rule is what surfaced it, and it is the second time in
this project that a table of counts caught a defect a table of performance
would have hidden.

### 6b. Initial Balance levels were interacted with before 10:30

IBH, IBL and IBM are defined by the first sixty bars and were being tested for
interaction from bar 1, so the first "interaction" with the IB high was often
the bar that **set** it. Straight look-ahead. The pre-registration said IB levels
are not eligible before 10:30; the code did not implement it. Fixed by gating
those levels and their shifted controls to bars >= 60.

The symptom was a 13-15% reclaim rate for IBH and IBL against 72-85% for every
other family -- an outlier large enough to be a bug rather than a finding, which
is how it was noticed.

**Standing lesson: a level has a birth time, and the eligibility gate belongs in
the interaction scan, not in the prose.** Any level computed from same-session
data must carry the bar index at which it becomes knowable, and that index must
be passed to the code that walks the tape.

### 6c. A condition that every family passes is an artefact until controlled

Not an error, but the practice that followed from one. All fifteen RP-007
families passed "first interactions outperform repeated interactions". Running
the identical comparison on the **shifted controls** returned **+2.68 points for
genuine levels and +2.68 points for arbitrary prices** -- identical to two
decimals on 12,893 and 43,903 observations.

The gradient is a property of the first touch of the day at any price, not of
levels. **A 15-of-15 pass is a reason to build a control, not a reason to
celebrate.**

---

## 7. A stop grid that saturated, and a pooled tercile that encoded the wrong axis

Both from RP-008 Stage 1. Neither changed a verdict; both are specification
defects of mine and both were visible in the counts.

### 7a. The two-sided stop-out columns carried no information

The pre-registration froze stop distances {0.5, 1.0, 1.5, 2.0} x ATR1m and asked
for P(adverse excursion >= d) on each side and for either side. Over a
60-minute forward window a random walk covers roughly sqrt(60) = 7.7 ATR1m, so
the EITHER-SIDE probability returned **95.7% to 100.0% in every cell at every
distance**. The column was saturated and tested nothing.

The one-sided columns worked (57.9% to 96.1%) and the pass condition was judged
on those. The grid was not changed after the fact.

**Standing lesson: check that a declared threshold grid spans the distribution
before freezing it.** A horizon and a threshold have to be chosen together; a
stop distance that is sensible for a 5-minute hold is a certainty over an hour.

### 7b. Pooled terciles partly encoded the instant, not the volatility

RV60 was defined as the last 60 minutes of regular trading before the
classification instant -- the prior session's 15:00-16:00 at the 09:30 instant,
and the same session's 10:30-11:30 at the 11:30 instant. Those two clock windows
have different volatility distributions (mean 4.47 vs 5.10 bps), so a tercile
boundary pooled across both **partly labels which instant the observation came
from**: 578 LO at 09:30 against 347 at 11:30, 521 HI at 11:30 against 359 at
09:30.

Caught in the cell-count table, before any forward outcome was computed, and
fixed by adding block-relative terciles as a declared diagnostic carried through
every table. The pooled labels stayed primary because they were frozen.

The same confound appeared again in the persistence control: the "extra R2 the
states add on top of RV60" read **0.4227**, which looked like a large
independent contribution and was almost entirely **the instant**, which the
state label carries and a linear fit on RV60 cannot. Decomposed properly the
tercile adds **+0.0014**.

**Standing lesson: when a state label is built from more than one axis, an R2
gain attributed to the label belongs to whichever axis the comparison model
omitted.** Decompose before interpreting.

---

## 8. `DataFrame.agg` collision — the THIRD recurrence of entry 1's failure mode

Caught live during the RP-010 integrity audit, in the audit's own inventory
script. A column named `agg` (aggressor labels) accessed as `R.agg` resolved to
the pandas `DataFrame.agg` **method**, exactly as `R.pivot` and `EXT.mod` did
before it.

| occurrence | column | study | how it failed |
|---|---|---|---|
| 1 | `pivot` | trendline reconstruction | silently, wrong values |
| 2 | `mod` | RP-003 | `TypeError`, immediately |
| 3 | **`agg`** | **RP-010 Stage 0 inventory** | **`AttributeError`, immediately** |

The standing rule from entry 4 was written and then broken by me in the very
document arguing for it. Two conclusions:

1. **A rule that depends on remembering is not a control.** The fix applied
   after entry 4 -- "rename the column" -- is the right fix but it is still
   enforced by memory.
2. **The test suite now enforces it.** `test_platform.py` is where the rule
   should have lived, and a lint check on reserved column names belongs there
   too. That is recorded as the one unresolved item in the audit.

Renamed to `side_labels`. Nothing downstream had been computed.

---

## 9. Microsecond timestamps divided as if they were nanoseconds

Caught in the **first** RP-010 Stage 1 run, before any figure was reported. The
forward-outcome loop converted tape timestamps to elapsed seconds with

```python
tt = pd.DatetimeIndex(s["time"]).view("int64") / 1e9        # WRONG
```

The ATAS tape is stored at **microsecond** resolution, which the Stage 0
inventory had already measured and printed. Dividing `asi8` by `1e9` therefore
made every elapsed time **1,000× too small**, so `secs <= h` was true for the
entire remaining session at every horizon.

| symptom | what it should have been |
|---|---|
| all six horizons returned **identical** numbers | six distinct paths |
| MFE ≈ 130 points at 30 seconds | ≈ 8–10 points |
| every landmark time 0 | 10–360 seconds |
| 100% break of the event extreme | 73–86% |

**It raised no exception and produced a full, well-formatted table.** Every cell
was wrong and nothing in the output said so.

| | |
|---|---|
| affected results | the first RP-010 Stage 1 run, **never reported** |
| rerun | **yes, in full.** Every number in `rp010_stage1_result.md` is post-fix |
| corrected in | this commit — `(ti - ti[0]).total_seconds()`, which is unit-agnostic |

**Two lessons, and the second is the reusable one.**

1. **Never convert a timestamp through its integer representation.** `asi8`,
   `.view("int64")` and `.astype(int)` all hand back a number whose unit is a
   property of the data, not of the code. `total_seconds()` cannot be got wrong.
2. **The tell was in the output, not in an error.** Six horizons returning the
   same value to three decimals is impossible for genuinely nested windows. The
   check that caught it was reading the table for internal consistency before
   reading it for a result — the same habit as counts-before-outcomes, applied
   one level down.

Test added: `t_timestamp_units()` in `test_platform.py` asserts correct elapsed
seconds at ns/us/ms/s resolution **and** asserts that the naive `asi8 / 1e9`
conversion is detectably wrong on a microsecond index, so the specific defect
cannot return silently. Suite: **115 assertions, 0 failures.**

---

## 10. Three frozen-spec outputs omitted from the first Stage 1 pass

Not a wrong number — a **missing** one. The RP-010 brief asked for additional
same-direction aggressive volume, a near-versus-away-from-levels diagnostic, and
results by week and by session. The first harness produced the first two not at
all and the third only at one horizon.

Declared in the script docstring **before** the amended run, added as
diagnostics, and the harness rerun in full. The rerun reproduced every count and
every primary figure exactly — 414 initiative candidates, 584 absorption
candidates, 204 events, identical means to three decimals — which is what makes
it an addition rather than an amendment to the construction.

**Standing lesson: check the report against the brief's output list before
running, not after.** A specification is a checklist of outputs as much as a
definition of method, and the cheapest time to notice a missing output is before
the two-minute run, not after the write-up has started.

---

## 11. Nine sealed sessions read — the seal existed only in prose

**The most serious error in this project so far.** RP-010 Stage 1 loaded every
sealed NQ session:

| dates | how they were used |
|---|---|
| 2026-06-18, 06-22, 06-23, 06-24, 06-25, 06-26, 06-29, 06-30 | **threshold warm-up** — their flow distributions set the trailing p90/p80/p20 percentiles for the first discovery sessions |
| **2026-07-23** | **a full discovery session**, contributing **6 of the 204 events**, with forward outcomes computed and reported |

The sealed set had been declared in every proposal since the tape archive was
inventoried, restated by the user in this very conversation ("Sealed NQ dates
remain unread"), and asserted as fact in `findings_summary.md`: *"Eight June
days and 23 July have never been read."* That sentence is now false, and it was
made false by me.

**How it happened.** The seal was enforced in exactly one script,
`session_profile.py`, which kept a private copy of the list as two module
constants. RP-010's loader filtered on measured resolution and session
completeness and never asked the question. The Stage 0 proposal contradicted
itself one row apart — *"full cash sessions at 0.25 | 44 (2026-06-18 →
2026-08-20)"* directly above *"Sealed: June 2026 plus 2026-07-23 — unread"* —
and I wrote both lines without noticing that the first contains the second.

**This is the same failure mode as ledger entries 1, 4 and 8, at a higher cost.**
Entry 8 concluded that "a rule that depends on remembering is not a control" and
fixed the reserved-name problem with a lint. The seal was left as prose in the
same breath.

| | |
|---|---|
| affected results | the whole of RP-010 Stage 1 (`3c5bcff`) |
| **dependency check** | full rerun with the seal enforced: `rp010_desealed_sensitivity.txt` |
| **effect on the verdict** | **none — the rejection strengthens.** Absorption 900 s falls +8.673 → +5.529; clustered +10.608 → +6.696, t +1.72 → +0.98; removing the best three sessions now takes it **negative**, +3.287 → **−1.497**; buy/sell asymmetry widens, +18.742/−3.634 → +17.191/−7.689; delta alone +16.024, progress alone +14.679 and volume alone +16.030 still dwarf impact alone at +3.112; matched random times +6.481 still exceeds absorption's +5.529 |
| rerun | **yes, in full.** The committed result carries a correction banner and is left otherwise unaltered |
| corrected in | this commit |

**The irrecoverable cost is not the verdict, it is the holdout.** Nine sessions
that existed to falsify a frozen finding have been spent on a family that was
rejected anyway. `holdout.still_unread()` now returns the **empty set**, and
RP-011's planned falsification block does not exist. That cannot be undone by
rerunning anything.

**The fix is code, not a promise.** `scripts/orderflow/holdout.py` is the single
register; `assert_unsealed` raises; `rp010_stage1.py` filters at the loader and
records the exclusions in its own excluded-dates table. Platform tests section 7
asserts the guard, and asserts specifically that **the RP-010 sample would now
be refused**.

**Standing rule: a holdout that is not enforced by a function call is not a
holdout.** Any claim that data is unread must be backed by a guard that raises,
and the guard must live in the loader, because that is the only place every
study passes through.

---

## 12. A safety cap that was actually a sampling design

RP-010 capped events at six per session as an operational guard against
over-representing one session. It **bound on 100% of sessions**, discarded 725
of 929 candidates, and — because retention was chronological — **left the entire
closing block with zero events on all 34 sessions.**

The study then reported forward outcomes "by time of day" with one of its four
time blocks structurally empty. The cap was described in the proposal as a cap
and never characterised as what it was: a first-come filter that selects the
earliest six order-flow extremes of a session.

Not caught before the run. Caught in the counts table afterwards, reported in
the closure, and correctly identified by the user as limiting the *breadth* of
the closure rather than rescuing it.

| | |
|---|---|
| affected results | the generality of the RP-010 verdict, not its direction |
| rerun | not required — the tested sample failed the mechanism controls decisively on its own terms |
| corrected in | this commit, as platform assertions |

`dataquality.cap_diagnostics` now returns the five required figures — share of
sessions where the cap binds, candidates discarded, block distribution before
and after capping, blocks emptied, retained-versus-discarded difference — and
`assert_cap_is_declared` **raises** when capping empties a time block, because a
study cannot report on a block it retained no events in. Platform tests section
8 reproduces the RP-010 pattern on a fixture and asserts that it raises.

**Standing rule: any cap that binds on more than half of sessions is part of the
sampling design and must be reported as one before outcomes, with its block
distribution before and after.**
