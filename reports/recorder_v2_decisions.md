# Recorder v2 — three answers and one recording list

Answered from `_api_inventory.txt` (ATAS 7.0.9.466) and the 18 June re-record.
No strategy test, no performance numbers.

---

## 1. Can depth be a true event stream? **YES.**

The API carries order-by-order data:

```
OnMarketByOrdersChanged(IEnumerable<MarketByOrder> values)

MarketByOrder
    DateTime                  Time
    MarketByOrderUpdateTypes  Type       Snapshot=0  New=1  Change=2  Delete=3
    MarketDataType            Side       Bid=0  Ask=1
    Int64                     Priority   queue position
    Int64                     ExchangeOrderId
    Decimal                   Price
    Decimal                   Volume
```

`New / Change / Delete` is exactly add / change / remove. It also carries
**queue priority** and a **stable order id**, which no ladder can express. This
is strictly more information than depth snapshots: the ladder is derivable from
the order stream, and the order stream is not derivable from the ladder.

So the 250 ms poll is not the best available — **it was never the only option**,
and the `level -1, volume 0` rows the recorder has been writing are its own
inference about what left the book, where `Delete` is the platform saying so.

**One caveat I will not paper over.** The callback existing does not mean the
feed fires it. CME publishes order-by-order on MDP 3.0, but many retail routes
deliver aggregated depth only, in which case `OnMarketByOrdersChanged` never
fires. I cannot settle that from the inventory — it is a property of your data
route, not of the assemblies.

So the recorder **writes the stream if it comes and counts it either way**. If
your route does not carry it, `_status.txt` will say, in these words:

```
NO MARKET-BY-ORDER DATA ON THIS ROUTE.
```

and the ladder poll remains the best available. Nothing is lost by trying: a
callback that never fires costs nothing.

**Also newly captured, and independent of that question:**

`OnBestBidAskChanged(MarketDataArg)` — a true BBO event stream, which the
recorder has never subscribed to. Every quote change between two depth
snapshots was being lost. It is now its own unthrottled file, so the spread and
the size at the touch are exact instead of sampled four times a second.

**Decision on the poll:** kept, unchanged at 250 ms, and now *counted*. With
BBO captured exactly and MBO captured when available, the ladder poll is no
longer load-bearing for anything time-critical, so tightening it would buy
little and cost file size. The status file now reports what percentage of book
updates the throttle kept, so the choice is visible rather than assumed.

---

## 2. CumulativeTrade and `arg.Time`

### Per-fill detail: confirmed, and it was being thrown away

```
CumulativeTrade
    Decimal              FirstPrice
    Decimal              Lastprice        (lowercase p)
    Decimal              Volume
    DateTime             Time
    TradeDirection       Direction
    List<MarketDataArg>  Ticks       <-- every individual fill
    MarketDataArg        PreviousAsk, PreviousBid, NewAsk, NewBid
```

`Ticks` is a full `List<MarketDataArg>` — each fill has its own **price, volume,
time, direction, and both exchange order ids**. The recorder walked that list
**only to count its length** and discarded the contents. An order sweeping four
levels became a first price, a last price and the number 4.

That is the single largest loss in the recording, and it is what made sweep
depth unusable on the coarse grid: with the shape discarded, all that remained
was `|last − first|`, which quantised to zero.

Also free and never captured: `PreviousBid/PreviousAsk` and `NewBid/NewAsk` —
**the book at the touch immediately before and after the order**. That is
absorption, measured directly rather than inferred.

### `arg.Time`: there is only one clock, and no receive timestamp exists

`MarketDataArg` exposes exactly one time field:

```
Price, OriginPrice, Volume, Time, Direction, DataType, OpenInterest,
IsAsk, IsBid, AggressorExchangeOrderId, ExchangeOrderId
```

**There is no second timestamp anywhere on the type, so platform receive time is
not exposed at all.** The question cannot be resolved by choosing the right
field, because there is only one.

What it *is*, demonstrably: in Market Replay the recorded timestamps are the
historical session's times, spanning 00:01–23:59 of the replayed date, not
today's wall clock. So `Time` is the **data clock** — the timestamp the data
provider carries, which for CME replay is exchange-sourced. `InstrumentInfo`
reports `TimeZone = 0`, confirming UTC and settling the clock question that was
previously inferred from the maintenance halt.

Live recording could in principle differ, and nothing in the inventory lets me
promise otherwise. I have not claimed it does.

**Fixed regardless:** timestamps were being truncated to milliseconds, where 43%
of prints share one and up to 216 land in the same millisecond. Now written at
**microsecond precision**. If the source only has milliseconds this costs three
zeroes a row; if it has more, we stop destroying it.

### Two more fields we were dropping

`AggressorExchangeOrderId` and `ExchangeOrderId` on every print — the only
identity the feed offers, and what would let a trade be joined to the order that
caused it. Now written. They may be null on CME, in which case the columns are
empty and the counter says so, which is itself the answer.

---

## 3. One ordered recording list

**One bulk job, with the improved recorder. Do not run two passes.**

The reasoning: the improved recorder is ready now, and every addition is a *new
stream or column*, not a change to what was already correct. So a session
recorded with v2 is a strict superset of one recorded with v1 — there is no
scenario where you record now and wish you had waited.

**18 June is already done at true 0.25** (1,997 distinct prices, L2 gap 0.25),
and it now loads in preference to its coarse twin.

### The window

16 June – 15 September, 66 business days. Never recorded at all: **16 June,
23 July, 14 and 15 September**. Three are half-days and not worth re-recording:
19 June, 3 July, 7 September.

### Order — strictly by expiry, most urgent first

**Tier 1, record today — these expire within days**

```
16 Jun*  17 Jun   22 Jun   23 Jun   24 Jun   25 Jun   26 Jun   29 Jun   30 Jun
```
`*` never recorded at any resolution.

Nine sessions. 16 June expires first and 17 June next; every day of delay costs
one more off the front. If you only get through part of this list today, take
them strictly in this order.

**Tier 2, this week**

```
1 Jul .. 31 Jul   (plus 23 Jul, never recorded)
```

**Tier 3, whenever**

```
August and September, plus 14 and 15 Sep
```

August and September do not expire for months. They are the ones to leave until
last, and the ones to skip entirely if the earlier data answers the question.

**Total needing a 0.25 recording: 60 sessions.** Two are already fine (12 and 20
August) and 18 June makes three.

### Settings for every recording, so provenance is unambiguous

```
instrument price step    1        (NOT 20 — this is the whole fix)
replay mode              Ticks + DOM
Record depth             true
Record market by order   true     (new; costs nothing if the feed lacks it)
Record individual fills  true     (new)
SnapshotMs               250      (unchanged)
DepthLevels              50       (unchanged)
```

Confirm on the first session: `_status.txt` must report **smallest gap actually
seen: 0.25**. If it reports 5.00, stop — the step did not take, and the session
is being wasted.

### Expected size

Measured on 18 June at 0.25: tape 3.3 MB, depth 12.9 MB, cumulative 2.1 MB =
**18.4 MB**, against 7.5 MB for the coarse recording of the same day. Adding the
BBO stream and per-fill rows should land around **25–35 MB a session**, so
**1.5–2 GB** for all 60. Files now arrive as one zip per day including
`_status.txt`.

---

## What changed in the recorder (`2026-09-16.o`)

| change | why |
|---|---|
| **`seq` first column of every stream** | dense by construction, so a gap in a file is a lost row and no gap proves none were lost |
| **per-stream counters in `_status.txt`** | received / written / throttled / off-session, with a `*** seq and written disagree ***` alarm |
| **`_status.txt` bundled into the zip** | provenance travels with the data. Copied, not moved, so the live file survives |
| **BBO stream** (`BBO_*.csv.gz`) | every quote change, unthrottled |
| **MBO stream** (`MBO_*.csv.gz`) | add/change/remove with queue priority and order id, when the feed carries it |
| **per-fill rows in CUM** | `kind` is `O` for an order, `F` for a fill; a fill joins its order on `parent_seq` |
| **microsecond timestamps** | 43% of prints shared a millisecond |
| **tape gains `datatype`, `oi`, `aggressor_order_id`, `order_id`** | fields `MarketDataArg` always carried |
| **coverage percentage** | against the configured session window |
| **throttle rejection count** | the poll's cost is now measured, not assumed |

Readers are unaffected: every loader matches columns by name, so a leading
`seq` and trailing columns are backward compatible. `bigorder.py` was updated to
take only `kind == "O"` rows, since summing the fill rows too would double-count
volume.

**Compiles out cleanly**: `-p:NoByOrder=true` drops the market-by-order part if
a future ATAS build changes that callback, exactly as `-p:NoCumulative=true`
already does.
