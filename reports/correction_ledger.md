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
