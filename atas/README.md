# L2 Recorder — getting Level 2 out of ATAS

ATAS loads indicators as compiled `.dll` files, so a `.cs` on its own cannot be
added. These three files build it.

```
L2Recorder.cs        the indicator
L2Recorder.csproj    the build, pointed at your ATAS install
build.bat            double-click this
```

## Install

**1. Install the .NET SDK** (once) — <https://dotnet.microsoft.com/download>.
Take the **SDK**, not the Runtime. Version 8.0 or newer.

**2. Double-click `build.bat`.**

It compiles against `C:\Program Files (x86)\ATAS Platform` and copies
`L2Recorder.dll` into `Documents\ATAS\Indicators\`. Installed somewhere else?
Pass the folder: `build.bat "D:\Path\ATAS Platform"`.

**3. Restart ATAS**, open the NQ chart, `Ctrl+I`, add **"L2 Recorder (CSV)"**.

It draws nothing on the chart. That is correct.

**4. Market Replay must be in `Ticks + DOM` mode.** The other replay modes do
not carry tick or depth data, so there is genuinely nothing to record.

## Is it working?

**A folder named `ATAS_Export` appears on your Desktop** the moment the
indicator is added to a chart — before any market data arrives. Inside it,
`_status.txt` refreshes every couple of seconds:

```
recorder version:   2026-09-13.d
OnCalculate calls:  4821
trades received:    93102
depth updates:      511230
rows written:       688441
WRITING HERE:       C:\Users\lenovo\Desktop\ATAS_Export
last error:         (none)
```

| What it says | What it means |
|---|---|
| rows written climbing | working — leave it running |
| trades and depth both 0 | the platform is sending neither; replay is in the wrong mode (use **Ticks + DOM**) |
| trades above 0, rows 0 | writing is failing — `last error` names the reason |
| `recorder version` is not the latest | ATAS is running a stale DLL from an earlier build |
| no folder on the Desktop at all | the indicator is not actually on the chart |

Earlier versions defaulted to `Documents\ATAS_Export` and produced what looked
like total silence. **Windows routinely redirects `Documents` to OneDrive**, so
the literal path `C:\Users\<name>\Documents` is often not the folder the process
writes into — the files existed, just not where they were being looked for. The
Desktop is not redirected, and `WRITING HERE` in the status file now states the
resolved absolute path rather than leaving it to be guessed. If the Desktop is
not writable either, it falls back through the user profile and `%TEMP%`, and
records every rejection in `folder choice`.

If it is not working, send that file back. It says what went wrong instead of
leaving it to guesswork.

## Notes for anyone editing these files

**Never put a comment in `L2Recorder.csproj`.** XML forbids a double hyphen
inside a comment, and MSBuild rejects the entire project file with `MSB4025` if
one appears — the build dies before a single line of C# is read. That failure has
happened twice from prose written into that file. The csproj now contains no
comments at all; explanation lives here instead, where it cannot break a build:

- `TargetFramework` is `net8.0-windows` because **ATAS Platform 7.x runs on
  .NET 8**. ATAS X is a different product on .NET 10; compiling against that
  install raises `CS1705`, which is why `build.bat` hardcodes
  `C:\Program Files (x86)\ATAS Platform`.
- `CopyLocalLockFileAssemblies` is `false` and every `Reference` is
  `Private="false"` — ATAS supplies its own assemblies at runtime, and shipping
  copies alongside the indicator stops it loading.
- References are wildcards over `ATAS.*`, `OFT.*` and `Utils.*` because the
  split between those assemblies has moved between platform versions.
- `ATAS.DataFeedsCore` is deliberately **not** imported in the C#: it declares
  its own `TradeDirection` and `MarketDataType` alongside the ones in
  `ATAS.Indicators`, and importing both makes every use ambiguous (`CS0104`).

### If the build fails

Send back everything the window printed. The compiler error names the fix.

The one case worth pre-empting: if it cannot find `ATAS.Indicators.dll`, find the
folder your ATAS install keeps it in and run from this directory:

```
dotnet build -c Release -p:AtasDir="C:\Your\Path\ATAS Platform"
```

## Output

Two files per instrument per day, in `Documents\ATAS_Export\`:

| File | Columns |
|---|---|
| `L2_NQU6_20260914.csv` | `time, side, level, price, volume` |
| `TAPE_NQU6_20260914.csv` | `time, price, volume, aggressor` |

`side` is `B`/`A` for bid/ask, `level` is 0 for the touch and counts outward.
`aggressor` is `B` when the buyer lifted the offer, `S` when the seller hit the
bid — the field no bar data contains, and the reason for the whole exercise.

## Settings

| Setting | Default | Notes |
|---|---|---|
| Output folder | `Documents\ATAS_Export` | |
| Depth levels per side | 10 | |
| Snapshot interval (ms) | 250 | raise to 500 if files get unwieldy |
| Record tape | on | |
| Record depth | on | |

Leave the defaults for the first run. A full RTH session is roughly 1.9M depth
rows and 300k trades — about 15 MB per session once zipped.

Depth snapshots are throttled because the book updates far faster than is worth
recording. Trades are never throttled: dropping them would bias the delta, which
is the one number that cannot be reconstructed afterwards.

## What to send back

**Three to five full RTH sessions, zipped.** Live or Market Replay both work;
replay is faster and you can collect five sessions in an afternoon.

## What it answers

For every touch of a fixed level, the recording makes these measurable:

- resting size at the level in the seconds before price arrived
- whether that size was **pulled** or **replenished** as price approached
- how much volume the level absorbed, and the aggressor split of it
- whether the level then **held or broke**

Which turns "does resting size predict a hold" from a month of manual logging
into a measurement over thousands of touches, with no room to talk yourself into
a read. If it predicts, the trade gets built around it. If it does not, levels
are finished and the search moves on.
