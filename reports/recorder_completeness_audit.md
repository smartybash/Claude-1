# Recorder completeness audit

No strategy test was run for this document and no performance number appears in
it. Every figure is a property of the recorder source or the recorded files.

---

## Part 1 — the source inventory: BLOCKED HERE, and the fix is shipped

**I cannot do Part 1 in this environment, and I am not going to fake it.**

The ATAS assemblies are not in the repository. `L2Recorder.csproj` resolves
them at build time from the ATAS install directory on your Windows machine:

```xml
<Reference Include="$(AtasDir)\ATAS.*.dll" Private="false" />
<Reference Include="$(AtasDir)\OFT.*.dll"  Private="false" />
```

Searched: no `ATAS*.dll` or `OFT*.dll` anywhere on this filesystem, no NuGet
cache, no .NET SDK. No captured reflection dump is stored in the repo either —
the recorder's `DescribeApi()` writes its output only into `_status.txt`, and
**`_status.txt` is not included in the session zip** (`BundleIfDone` packs the
depth, tape and cumulative files only), so none of it was ever retained.

You asked specifically not to work from memory or documentation. Working from
either would produce a list that looks right and may not match your build, and
a plausible list is worse than no list because it gets trusted.

**So Part 1 is delivered as `atas/ApiProbe.cs`** — a probe that answers it from
your assemblies, on your machine, in one run. It writes `_api_inventory.txt`
alongside the recorder's output containing:

1. every ATAS/OFT/Utils assembly loaded, **with version** — provenance
2. **every overridable method on the whole Indicator chain**, full signatures.
   Not the trade-and-depth subset the recorder already prints: the complete
   callback surface, which is the actual question
3. every public property, field and method of every type those signatures
   mention
4. every market-data type in the ATAS and OFT assemblies matched on name
   (Trade, Depth, Book, Quote, Tick, Market, Instrument, Level, Cumulative,
   Candle, Order, Security, Session), enums expanded to values
5. the **live `InstrumentInfo` with current values** — where the price step
   appears as a number, which also independently confirms the Step=20 finding

Add it to any chart, let one bar close, send me `_api_inventory.txt`. Parts 1
and 4 can then be finished properly rather than guessed.

---

## Part 2 — diff against what we write

From the recorder source, which I do have.

### Events subscribed

| callback | subscribed | what is done with it |
|---|---|---|
| `OnNewTrade(MarketDataArg)` | yes | writes `time, price, volume, aggressor` |
| `MarketDepthChanged(MarketDataArg)` | yes | **the argument is discarded except for `.Time`** — see below |
| `OnCumulativeTrade(CumulativeTrade)` | yes | deferred one order, then written |
| `OnUpdateCumulativeTrade(CumulativeTrade)` | yes | replaces the pending order |
| `OnCalculate(int, decimal)` | yes | status file and flush only; no market data |
| everything else on the chain | **no** | unknown until the probe runs |

### The finding that matters most in this part

**Depth is not an event stream. It is a polled snapshot, throttled to 250 ms.**

```csharp
if ((now - _lastSnapshot).TotalMilliseconds < SnapshotMs) return;
var snap = MarketDepthInfo.GetMarketDepthSnapshot();
```

`MarketDepthChanged` fires, the recorder checks a clock, and if less than
250 ms has passed it **returns without reading anything**. When it does
proceed, it ignores the event and re-reads the entire book.

Consequences, in order of severity:

- **Order book event type — add, change, remove — is never captured.** Not
  lossily: it is never looked at. The recorder sees only the *resulting state*
  of the book at 3.6 snapshots a second. Whether size appeared, was modified,
  or was pulled is not recoverable, and the `level == -1, volume = 0` rows are
  the recorder's *own inference* about what left the top of the book, not a
  platform remove event.
- **Incremental vs snapshot:** the file format is incremental (changed levels
  only, with keyframes), but the *source* is a snapshot. The incremental
  encoding is a compression of polled states, not a capture of the exchange's
  incremental feed.
- **Measured capture rate:** 85,139 snapshots per RTH session. A book updating
  even 100 times a second would produce ~2.3 million states, so we are keeping
  order of **3–4%** of book states, by design.

### Field-by-field

| item | status |
|---|---|
| **exchange vs local timestamp** | The written stamp is `arg.Time`, the **data clock** — confirmed empirically: replay files carry historical session times, not wall-clock. `DateTime.Now` is used only for idle detection and never written. **Which of exchange-supplied or platform-receive time `arg.Time` is, cannot be resolved without the assemblies.** The probe answers it. |
| **timestamp precision** | `"yyyy-MM-dd HH:mm:ss.fff"` — **milliseconds, truncated**. Measured on 23 June: 436,854 prints over 249,204 distinct millisecond stamps, so **43% of prints share a millisecond**, up to **216 in one**. Intra-millisecond ordering is preserved only by row order, and any finer source precision is destroyed. |
| **aggressor side** | Captured, as `B`/`S`, from `arg.Direction`. Anything that is neither maps to `?` and is excluded from delta. Not lossy for the two real cases. |
| **book event type** | **Ignored entirely.** See above. |
| **incremental vs snapshot** | Snapshot source, incremental encoding. |
| **best bid / offer as an independent stream** | **Not captured.** No BBO stream exists. BBO is *derived* from the depth snapshot, so it inherits the 250 ms throttle and is only as good as the top of the polled ladder. Every quote change between snapshots is lost. |
| **cumulative trade fill detail** | **Lossy.** We write `time, aggressor, first_price, last_price, volume, fills` — six scalars. The `CumulativeTrade` object almost certainly exposes the **individual fills**, and we collapse them to first, last and a count. Per-fill price and size are discarded. The probe will confirm exactly what is on the object. |
| **sequence / event counter** | **None written, anywhere.** Counters (`_trades`, `_depthEvents`, `_rows`, `_cumTrades`) exist in memory and reach `_status.txt` only — and that file is not bundled with the data. |
| **depth `level` column** | **Subtly stale.** Under `ChangesOnly`, a level is re-written only when its *volume* changes. A price whose rank shifts but whose size does not is not rewritten, so the `level` value in the file can be out of date between keyframes. Price and volume are correct; **rank is not reliable.** |
| **volume-zero levels** | Skipped on read (`lvl.Volume <= 0`), then separately emitted as removals. Consistent, but it means a genuine zero-size level from the platform is indistinguishable from an inferred removal. |
| **`DepthLevels` cap** | 50 per side kept, the rest of the snapshot discarded. |

---

## Part 3 — can we prove nothing was dropped?

### Today: no.

There is **no counter in any data file**, and no platform-supplied sequence
number is captured, so a recording cannot be reconciled against anything. The
in-memory counters are written to `_status.txt`, which is overwritten
continuously and is **not bundled with the session**, so by the time a zip
reaches me the evidence is gone.

That is the gap, and it is the whole of Part 3's answer: **completeness is
currently unprovable, and nothing about the current format could ever prove
it.**

### Threading and blocking: measured, and better than feared

Every handler writes **inline, on the event thread, under one global
`lock (_sync)`**. Tape, depth and cumulative handlers contend on the same lock,
and gzip compression happens inside it. There is no queue, so the recorder
**cannot silently drop** — it can only block the caller. The real risks are
back-pressure into the platform and, if ATAS dispatches on one thread, delayed
processing.

Worst case actually on disk:

| session | peak tape | peak burst | depth snapshot interval (target 250 ms) |
|---|---|---|---|
| 23 Jun | 1,260/sec | 247 per 100 ms | median 268, p99 359, **max 678 ms** |
| 8 Sep | 768/sec | 347 per 100 ms | median 272, p99 407, **max 1,157 ms** |
| 20 Aug (0.25) | 706/sec | 402 per 100 ms | median 267, p99 395, **max 976 ms** |

Intervals over 1 second: **one, across all three sessions.** Over 5 seconds:
**none.** Timestamps are strictly monotonic in both tape and depth, with zero
inversions. **The recorder kept up**, including on the 0.25 session, which
carried 2.4 million depth rows against ~1 million for a coarse day.

So the losses in this recording are *designed* (the 250 ms throttle, the 50
level cap, the millisecond truncation), not *accidental*. That is a meaningfully
better position than the reverse, because designed losses are ones we can
choose to stop taking.

### Instrumentation to add

1. **A per-stream counter row in every file**, written at each keyframe:
   events received, events written, events skipped by the throttle, events
   skipped as off-session. Then a recording reconciles against itself.
2. **A monotonic write sequence number** as the first column of every data row.
   Any gap proves loss; no gap proves none.
3. **Capture any platform sequence number** the probe finds on `MarketDataArg`
   or `CumulativeTrade` and write it. Only this can prove nothing was lost
   *upstream* of us.
4. **Bundle `_status.txt` into the session zip** — a one-line change to
   `BundleIfDone`. Provenance must travel with the data.
5. **Count throttle rejections explicitly.** Right now `_depthEvents` counts
   events received and `_rows` counts rows written, which are not comparable.
6. **A high-water mark for lock wait time**, so back-pressure becomes visible
   before it becomes a gap.

---

## Part 4 — the improved recorder

Specified as far as is honest. Items marked **(probe)** cannot be finalised
until `_api_inventory.txt` exists, because they depend on fields I have not
confirmed.

### Settings and provenance, written into every session

```
instrument, exchange, price step (as a number), tick size,
recorder version, ATAS assembly versions,
SnapshotMs, DepthLevels, ChangesOnly, KeyframeSeconds,
session window, replay mode, wall-clock start and end
```

A session that cannot state its own resolution is how the last four months
happened. This is the fix.

### Streams

| file | content | change from today |
|---|---|---|
| `TAPE_` | seq, time, price, volume, aggressor, **(probe)** any platform sequence/id | + seq, + precision below |
| `L2_` | seq, time, side, level, price, volume, **event kind** | **(probe)** — capture the event rather than polling, if the API allows |
| `CUM_` | seq, time, aggressor, first, last, volume, fills, **per-fill detail** | **(probe)** — stop collapsing fills |
| `BBO_` | seq, time, bid, bidsize, ask, asksize | **new stream** — every quote change, untied to the depth throttle |
| `_status.txt` | counters, min price gap, first/last timestamp, coverage %, gaps | bundled into the zip |

### Self-check written to `_status.txt`

- events **received / written / throttled / off-session**, per stream
- **minimum non-zero price gap observed** — catches a Step regression the same
  day rather than four months later
- first and last data timestamp, per stream
- **coverage percentage** against the expected session length
- any sequence gap, with the timestamps bracketing it
- maximum lock wait and maximum snapshot interval

### Expected size per session at 0.25

Measured, from the two dates recorded both ways:

| stream | coarse | at 0.25 | ratio |
|---|---|---|---|
| depth | 5.0 MB | **12.8 MB** | 2.6× |
| tape | 2.1–2.8 MB | 2.5–3.5 MB | ~1.2× |

With the throttle loosened and a BBO stream added the depth figure rises
further; at 100 ms it is roughly 2.5× the 250 ms figure, so **plan on 30–40 MB
a session** for a full-fidelity recording, against ~8 MB today.

---

## Part 5 — sequencing, given 17 June expires within days

**Record the expiring dates now, with the current recorder, at Step = 1.**

The re-record and the recorder improvements are **separable**, and this is the
key point: the resolution fix is a **settings change, not a code change**.
Setting the instrument step to 1 requires nothing from me and loses nothing
that the improved recorder would later add, because everything the improved
recorder adds — BBO stream, per-fill detail, sequence numbers, event kinds — is
*additional* data, not a correction to what the current one writes.

So the sequencing that avoids recording anything twice:

**Now, today, before anything else**

1. Set the instrument price step to **1** (from 20). Verify: the recorder's
   status file reports the smallest observed gap as 0.25.
2. Re-record in **strict expiry order** — 17 June first, then 18, 19, 22, 23,
   and onward. Each day lost is lost permanently; each day of delay costs one
   session off the far end.
3. Keep `RecordDepth = true`, `SnapshotMs` and `DepthLevels` as they are. Do
   not tune anything. The point of this pass is resolution, and resolution is
   the only thing that cannot be recovered later.

**In parallel, costing you nothing**

4. Add `ApiProbe` to any chart for one bar and send `_api_inventory.txt`.
   This is a minute of your time and it unblocks Parts 1 and 4.

**After the expiring window is rescued**

5. I build the improved recorder against what the probe reports.
6. Re-record **only** what the improvements actually require — the BBO stream
   and per-fill detail cannot be reconstructed, so sessions needing those must
   be recorded again. But that is a decision to take **once we know what the
   probe says those streams contain**, and it applies to whatever is still in
   the replay window then, not to all 61.

**What you would be recording twice, and why it is the right trade**

Sessions recorded in step 2 will lack BBO and per-fill detail. If those turn
out to matter, the ones still inside the replay window can be redone. Sessions
expiring this week can only be captured at 0.25-with-gaps or **not at all** —
and 0.25-with-gaps is strictly better than a 5-point recording of the same day,
which is what we would otherwise keep.

**One correction to make before recording anything**: the loader keys sessions
by date and takes the last file, so a coarse `_run2` shadows a fine original —
that is happening to 12 and 20 August right now. Re-recording 17 June while
that bug stands would work, but the moment any date is recorded twice the wrong
one may win. I will fix the keying to prefer the finer recording before the
first new file lands.

---

## Ingest, 17 September — five sessions re-recorded at true tick

`20260729, 20260730, 20260731, 20260803, 20260804`. Recorder version
`2026-09-17.z`. These five were already on disk from 15 September, so the
question was whether the new recordings are better, not whether they are new.

**They are, decisively. The recordings on disk were 5.0-point.**

| day | on disk: step | levels | new: step | levels | minutes |
|---|---|---|---|---|---|
| 20260729 | **5.00** | 196 | **0.25** | 3,888 | 1,379 → 1,380 |
| 20260730 | **5.00** | 222 | **0.25** | 4,424 | 1,379 → 1,380 |
| 20260731 | **5.00** | 131 | **0.25** | 2,585 | 1,259 → 1,260 |
| 20260803 | **5.00** | 133 | **0.25** | 2,636 | 1,379 → 1,380 |
| 20260804 | **5.00** | 226 | **0.25** | 4,499 | 1,379 → 1,380 |

A 5.0-point step is **20× the real NQ tick**, and it is why all five failed the
`step <= 0.25` gate in `reports/european_session_data_inventory.md` and were
absent from the 21-session set. They now pass.

> **Usable 0.25-tick sessions over the European window: 21 → 26.**
> `0701 0702 0703 0706 0707 0708 0709 0710 0713 0714 0715 0716 0717 0720 0721
> 0722 0724 0727 0728 **0729 0730 0731 0803 0804** 0812 0820`

Row counts are near-identical between the two recordings (e.g. 734,016 against
734,600 on 29 July), so the old files were not sparser — they were **rounded**.
Every print was there; its price was wrong by up to 20 ticks.

**All four streams arrived, and BBO is entirely new for these dates** — the
`data/bbo` archive previously stopped at 28 July.

| day | tape | cum fills | reconcile | cum orders | BBO | depth |
|---|---|---|---|---|---|---|
| 20260729 | 734,600 | 734,600 | **exact** | 407,715 | 1,412,864 | 3,317,223 |
| 20260730 | 626,331 | 626,331 | **exact** | 369,091 | 1,404,782 | 2,615,116 |
| 20260731 | 598,579 | 598,579 | **exact** | 339,790 | 1,211,429 | 2,928,965 |
| 20260803 | 478,327 | 478,327 | **exact** | 272,491 | 1,078,454 | 2,215,068 |
| 20260804 | 561,238 | 561,238 | **exact** | 321,438 | 1,162,040 | 2,199,991 |

Every tape print reconciles one-to-one against a fill row in the cumulative
stream, on all five. That is the check worth having: it says no print was
dropped between the two independent streams.

### Two things in the status files that are not faults

1. **The counters read low against the files.** `_status_20260729.txt` reports
   495,077 tape rows where the file holds 734,600. Its own internal
   consistency is intact — it reports 495,078 fill rows against 495,077 tape
   rows, matching the exact reconciliation seen in the finished files. **The
   status file is a mid-recording snapshot, not a final tally.**
2. **`*** UNACCOUNTED 191321 ***` on the best bid/ask stream.** Same cause: the
   counters were written while the stream was still running. Flagged here
   because the recorder flags it itself, and because if it ever appears in a
   status file whose tape and fill counts *do* match the finished file, it
   would mean something different.

### Handling

The `.gz` 5-point recordings were **kept, not replaced**. The loader selects the
finest recording per date, so the coarse files are now inert but the provenance
of what was previously analysed stays on disk. This is the same convention used
for the June re-records.

Sealed NQ days were not read. None of these five is sealed.

## Ingest, 17 September — second set of five, same story

`20260805, 20260806, 20260807, 20260810, 20260811`. Recorder `2026-09-17.z`.
All five were already on disk from 15 September, all five at a 5.0-point step.

| day | on disk: step | levels | new: step | levels | rows old → new |
|---|---|---|---|---|---|
| 20260805 | **5.00** | 109 | **0.25** | 2,169 | 512,673 → 513,033 |
| 20260806 | **5.00** | 90 | **0.25** | 1,781 | 504,657 → 505,065 |
| 20260807 | **5.00** | 84 | **0.25** | 1,657 | 477,581 → 477,856 |
| 20260810 | **5.00** | 62 | **0.25** | 1,225 | 358,424 → 358,685 |
| 20260811 | **5.00** | 72 | **0.25** | 1,414 | 406,063 → 406,321 |

Rows within 0.1% again — rounded, not sparser. The level counts on the coarse
recordings are lower than the first batch's (62 to 109, against 131 to 226),
which is what a 5-point grid does to a quiet week rather than anything about the
new files.

> **Usable 0.25-tick sessions over the European window: 26 → 31.**
> `0701 0702 0703 0706 0707 0708 0709 0710 0713 0714 0715 0716 0717 0720 0721
> 0722 0724 0727 0728 0729 0730 0731 0803 0804 **0805 0806 0807 0810 0811**
> 0812 0820`

**BBO and the status files are new for all five** — neither existed on disk for
these dates in any form.

| day | tape | cum fills | reconcile | cum orders | BBO | depth |
|---|---|---|---|---|---|---|
| 20260805 | 513,033 | 513,033 | **exact** | 298,361 | 1,040,409 | 2,666,746 |
| 20260806 | 505,065 | 505,065 | **exact** | 298,080 | 1,175,512 | 2,652,305 |
| 20260807 | 477,856 | 477,856 | **exact** | 278,784 | 1,078,716 | 2,504,700 |
| 20260810 | 358,685 | 358,685 | **exact** | 210,214 | 936,255 | 2,106,912 |
| 20260811 | 406,321 | 406,321 | **exact** | 228,595 | 916,689 | 2,116,831 |

**7 August ends at 20:59:59**, as 31 July does. Both recordings of that date stop
there, so it is a recording fact rather than a regression, and it still covers
the European window in full.

Coarse `.gz` files kept, loader prefers the finer recording, same convention.
Sealed NQ days were not read; none of these five is sealed.
