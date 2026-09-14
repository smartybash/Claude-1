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
recorder version:   2026-09-13.e
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

Two files per instrument per day, in `Desktop\ATAS_Export\`:

| File | Columns |
|---|---|
| `L2_NQU6_20260914.csv` | `time, side, level, price, volume` |
| `TAPE_NQU6_20260914.csv` | `time, price, volume, aggressor` |

`side` is `B`/`A` for bid/ask, `level` is 0 for the touch and counts outward; a
`level` of `-1` with volume `0` means that price has left the top of the book.
`aggressor` is `B` when the buyer lifted the offer, `S` when the seller hit the
bid — the field no bar data contains, and the reason for the whole exercise.

## Settings

| Setting | Default | Notes |
|---|---|---|
| Output folder | `Desktop\ATAS_Export` | |
| Depth levels per side | 10 | |
| Snapshot interval (ms) | 250 | raise to 500 if files get unwieldy |
| Record tape | on | |
| Record depth | on | |
| RTH only | on | 13:30–20:00 **platform clock**, which is UTC here |
| RTH start/end | 13:30 / 20:00 | change only if your platform clock is not UTC |
| Only write changed levels | on | |
| Full ladder every N seconds | 60 | |

Leave the defaults. The RTH window is in the **platform's own clock**: the halt
in the recorded files sits at 21:00–22:00 and CME halts at 17:00–18:00 New York,
so this install runs on UTC and 13:30–20:00 is the cash session. If your status
file shows trades arriving outside that window, the platform clock is set to
something else and these four numbers need changing to match.

Depth snapshots are throttled because the book updates far faster than is worth
recording. Trades are never throttled: dropping them would bias the delta, which
is the one number that cannot be reconstructed afterwards.

## What to send back

**Put the whole `ATAS_Export` folder in Google Drive.** Nothing needs uploading
by hand and there is no size limit that way.

Twenty RTH sessions. Live or Market Replay both work; replay is faster and
several sessions fit in an afternoon.

### Two settings that matter more than the rest

**Price step = 1 tick on the recording chart.** ATAS applies the chart's price
step before the data reaches this indicator. The first recording was made at 20
ticks, so every price in it landed on a 5-point grid: 61 distinct prices across
a 300-point range. Delta and volume survived that; price resolution did not.

**Market Replay mode = Ticks + DOM.** The other modes carry no tick or depth
data at all.

## File size

Two changes keep a session small enough to move around:

- **RTH only** (default on). The first recording covered all 24 hours; the cash
  session is 27% of that and the rest is not analysed.
- **Changed levels only** (default on). A depth row is written only when that
  price's resting size actually changed, plus a full ladder every 60 seconds so
  the book can be re-anchored, plus a zero-volume row when a price leaves the
  top of the book. Consecutive snapshots in the first recording were
  byte-identical, which is what made this worth doing.

Together that takes a session from roughly 80 MB to under 10 MB. The format is
lossless: `scripts/book.py` rebuilds the exact ladder at every timestamp and
carries a round-trip test proving it.

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

---

# Level Plan — the second indicator

`LevelPlanner.cs` builds in the same DLL and appears separately in `Ctrl+I` as
**"Level Plan (weight rule)"**. It computes the weight rule live and writes the
plan; it draws nothing.

That is deliberate. The execution study measured a **median hold of 2.6 minutes
and a first quartile of 48 seconds**, so reacting to a chart is hopeless — but
the levels come from the *previous* session and are known before the open. The
trade is a resting limit with a bracket, placed in advance, so the useful output
is a list of prices, not a picture.

## What it writes

| File | Contents |
|---|---|
| `PLAN_{sym}_{date}.txt` | **The morning job.** Each level, its weight, LIGHT or heavy, and which to place orders at. |
| `PROFILE_{sym}_{date}.csv` | Volume at every price in the cash session — the raw material for tomorrow's levels. Survives a restart. |
| `SIGNALS_{sym}_{date}.csv` | One row per touch of a light level, with side, stop and target, so live behaviour can be checked against the study. |
| `_plan_status.txt` | Counters, the current plan, and the last error. |

## The rule it implements

```
levels      previous cash session high, low, close, VAH, POC, VAL
merge       levels within 5 points become one, at their mean
weight      volume traded within +/- 2 points of the level, previous session
LIGHT       under 10,000 contracts  -> place a bracketed limit
HEAVY       10,000 or more          -> leave it alone
side        approached from above -> buy limit; from below -> sell limit
stop/target 30 points each
```

Fading a heavy level lost 12 points a trade at a 33% win rate in the study, so
the heavy ones are not a weaker version of the trade — they are the wrong side
of it.

## It agrees with the backtest

`scripts/orderflow/verify_planner.py` re-implements this indicator's algorithm
in Python, line for line, and runs it against every recorded session alongside
the study's own code. **All twelve sessions agree to the tick.** If those two
ever diverge, the live rule and the tested rule are different rules and the
study describes something the trader is not doing — a failure that would
otherwise be invisible, since both sides would produce plausible-looking levels.

## First run

It needs one previous session's profile before it can plan anything. Day one it
writes `PROFILE_...` and reports "no previous session profile yet" in the status
file; from day two the plan appears. To skip that wait, run Market Replay over
yesterday once and the profile is written from that.
