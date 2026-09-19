# What we actually hold for 07:00–16:00 UTC

Data question answered before anything is pre-registered or run. **Nothing was
run.** Sealed NQ days were not read — the inventory below reads file headers and
timestamps only, and the usable-session list excludes them at construction.

---

## 1. The short answer

**21 NQ tick sessions. That is all.** It is not enough to screen on.

One part of the premise is wrong in your favour, though: **the NQ tape
recordings are 24-hour, not RTH-only.** I had been filtering them to the US cash
session in code, which is not the same as them only containing it.

---

## 2. NQ tick recordings — full European coverage, tiny sample

```
TAPE_NQ_20260617.csv.gz   492,001 rows   00:01 .. 23:59 UTC   07-16h rows 208,442 (42.4%)
TAPE_NQ_20260618.csv.gz   497,026 rows   00:01 .. 23:59 UTC   07-16h rows 270,143 (54.4%)
```

The recorder captured the whole day. Roughly **half of every recording is the
European session**, at 200,000–270,000 prints per session.

| | |
|---|---|
| tape files on disk | 87 |
| distinct dates | 64 |
| at true 0.25 resolution | **31** |
| of those, covering ≥90% of the 540 European minutes | **31** (min 539 of 540) |
| **after excluding the 8 sealed June days and 23 July** | **21** |

```
20260701 20260702 20260703 20260706 20260707 20260708 20260709 20260710
20260713 20260714 20260715 20260716 20260717 20260720 20260721 20260722
20260724 20260727 20260728 20260812 20260820
```

**21, not 20.** The extra date is **3 July 2026** — a US half session, which the
US full-session test correctly rejected, and a completely normal European
session. A genuine gain, and it is also the size of the gain.

---

## 3. Futures bar history — too coarse and too short

| file | bars | span | days | bars in 07–16 UTC |
|---|---|---|---|---|
| `nq_30min_eth.json` | 2,001 | 2026-06-17 → 2026-08-18 | 54 | 787 |
| `nq_1h_eth.json` | 1,448 | 2026-05-12 → 2026-08-10 | 78 | 569 |
| `nq_5min_eth_live.json` | 1,400 | 2026-08-21 → 2026-08-28 | 7 | 540 |
| `data/parquet/NQ_5min.parquet` | 2,174 | 2026-06-17 → 2026-07-06 | ~14 | US hours |

The `_eth` files do cover European hours — that is what "ETH" means — but they
are **30-minute and 1-hour bars over 54 to 78 days**. The calibration gate
already established that 5-minute bars were borderline for a rule with a ~10 bps
stop, failing outright at the tight stop. Thirty-minute bars are not in the
conversation. The one 5-minute ETH file covers **7 days**.

---

## 4. Everything else is the US cash session

| dataset | sessions | hours |
|---|---|---|
| `QQQ_1m.parquet` | 1,421 | 09:30–16:00 ET only |
| `QQQ_5m.parquet` | 2,680 | 09:30–16:00 ET only |
| SPY, IWM, XLB…XLY basket, IGV, SMH, MAGS | various | US-listed, US hours |

**The 1,418-session sample that carried the last three screens cannot be pointed
at European hours at all.** It does not contain them.

---

## 5. External sources — nothing reachable on current access

Probed rather than assumed:

| source | result |
|---|---|
| **FMP** `indexes` (DAX intraday) | `ACCESS DENIED` — requires Starter or above |
| **FMP** `chart` (EXS1.DE intraday) | `ACCESS DENIED` — same |
| **Alpha Vantage** `SYMBOL_SEARCH` | European listings exist: `DAX.PAR`, `DAXX.LON`, `AL8F.DEX` |
| **Alpha Vantage** `TIME_SERIES_INTRADAY` on `DAXX.LON` | rejected — the intraday endpoint is US equities only |
| **IBKR** `search_contracts` "DAX" | DAX 40 Index, EUREX, contract `825711`, with a FUT ladder |
| **IBKR** `get_price_history` DAX, 1-minute, 1 year | `Combination of period and step will provide more then allowed 3500 data points` |
| **IBKR** DAX hourly, one day | **works** — `07:00 → 15:40 UTC`, exactly the target window, `delayed: 900` |

**IBKR has the right instrument at the right hours and cannot deliver depth.**
The API caps at **3,500 bars per request** and takes only `period`/`step_count`
anchored to *now* — there is no `from_date`. So it reaches back:

- **1-minute: ~6 European sessions**
- **5-minute: ~22–32 sessions**
- 30-minute: ~194 sessions, at a resolution already ruled out

There is no paging parameter to walk further back. The data is also 15-minute
delayed, which implies no Eurex market-data subscription on the account.

---

## 6. Minimum detectable effect, stated before any result

Per-session dispersion measured on the same rule (ORB, 1.0 ATR stop, 3R/4R
targets) across the QQQ runs:

| variant | per-session R sd |
|---|---|
| OR15 SATR1.0 R3.0 | 2.362 |
| OR15 SATR1.0 R4.0 | 2.773 |
| OR30 SATR1.0 R3.0 | 2.307 |
| OR30 SATR1.0 R4.0 | 2.714 |
| **median** | **2.538 R** |

`MDE = 2.80 × sd / √n` at 80% power, two-sided 5%:

| n sessions | MDE (80% power) | MDE for t > 3 |
|---|---|---|
| **21** | **+1.551 R/session** | **+1.662** |
| 100 | +0.711 | +0.762 |
| 250 | +0.450 | +0.482 |
| 500 | +0.318 | +0.341 |
| 1,000 | +0.225 | +0.241 |
| 1,418 | +0.189 | +0.202 |

**At 21 sessions the smallest detectable effect is +1.55 R per session.** With a
cap of two trades a session that is roughly **+0.78 R per trade**.

**The largest per-session effect any variant produced across three QQQ screens
was about 0.04 R.** So 21 sessions can only find something roughly **39 times
larger than anything this project has ever measured.** A rule that good would be
visible without a backtest.

### Sessions required

| edge to detect | sessions needed | ≈ years |
|---|---|---|
| 0.50 R/session | 202 | 0.8 |
| 0.30 R/session | 561 | 2.2 |
| **0.20 R/session** | **1,262** | **5.0** |
| 0.10 R/session | 5,049 | 20 |

**Roughly 500 to 1,300 sessions, which is two to five years.**

---

## 7. Recommendation: do not run this

Running 8 variants on 21 sessions would produce numbers. They would be
uninterpretable in both directions — unable to confirm anything, and unable to
reject anything either, because failure at this sample size is the expected
outcome whether or not an edge exists. It would also spend the European-session
novelty of these 21 sessions on a test that cannot use them.

**The 21 sessions are not a proxy for a screen and I am not going to present
them as one.**

### What they *can* honestly do

Not a performance test, and it cannot be turned into one: a **descriptive
measurement** of the European session against the US session on the same
instrument and the same 21 dates — range, realised volatility, ATR in bps,
opening-range height, how many breakout and pullback signals the existing rules
would even generate, and what risk per trade looks like. That tells you whether
the session is structurally different enough to be worth acquiring data for,
before spending money. It produces no expectancy, no win rate and no verdict,
and I would report it with those columns absent rather than greyed out.

---

## 8. What would need to be acquired

**Target: 500–1,300 sessions of 1-minute or finer bars on a European index
instrument covering 07:00–16:00 UTC.**

**Instrument.** `FDAX` or `FESX` — Eurex DAX 40 and EuroStoxx 50 futures. These
are the European analogue of NQ: index futures, genuine European participant
mix, deep book. FTSE 100 futures (`Z`/ICE) are a second option. For a *screen*
specifically, the **DAX cash index** is also defensible and avoids contract-roll
stitching entirely — the same reasoning that made QQQ acceptable as a stand-in
for NQ.

**Sources, ranked by fit to what this project already does:**

1. **Databento** — Eurex historical, 1-minute through full MBO. Pay per GB,
   no subscription. Closest match to the tick work already built, and the only
   option that could eventually support the order-flow instrumentation.
2. **FirstRate Data** or **Kibot** — flat-fee historical intraday futures,
   FDAX/FESX 1-minute, 10+ years, continuous contracts pre-stitched. Cheapest
   route to 1,300 sessions and sufficient for a bar screen.
3. **Dukascopy** — free historical tick and 1-minute on DAX/EuroStoxx.
   **The cost of this one, stated plainly:** it is CFD-derived, so the prices,
   the spread and the session boundaries are a broker's, not an exchange's.
   Usable for a first screen, not for anything that turns into a fill model.
4. **IBKR** — already connected, right instrument, right hours, wrong depth.
   6 sessions at 1-minute. Rules itself out.
5. **ATAS forward recording** — your own recorder, already writing 24-hour
   tapes. Replay reaches back 3 months. At one session a day, 500 sessions is
   two years of waiting. Worth starting in the background regardless, since the
   recordings are already 24-hour and cost nothing extra.

**My recommendation: FirstRate Data or Kibot for FDAX 1-minute, 5+ years.** It
is a one-off flat fee, needs no subscription, and 1,300 sessions of 1-minute
bars is exactly the sample the MDE table says is required. Databento if the
order-flow work is ever to be revived on European hours.

---

## 9. Standing items

The families being proposed — opening range breakout and pullback continuation —
are fully specified and their code runs unchanged apart from the session anchor,
so **no re-specification work is needed and nothing is lost by waiting for
data.** The pre-registration for a European screen can be written the day the
data lands.

Sealed NQ days remain sealed and unread.
