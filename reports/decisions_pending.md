# Decisions pending — waiting for the user (away until 11 Oct)

Everything that needs a decision goes here; work that does not need one carries
on. Budget and approval rules are unchanged (`reports/databento_register.md`).

---

## P1. Power of 3 — spec for approval (test only after "approved")

**Source.** The video transcript was tried **once**: YouTube redirected the
request to Google's bot-check page (`google.com/sorry`), which this environment
blocks. That is YouTube's usual block on cloud IPs. No proxy or paid service was
used, and nothing is inferred about what the video says. The spec below is drafted
from the **standard ICT definition** (accumulation → manipulation / Judas swing →
distribution).

**Relation to closed work.** The mechanical core — sweep a reference, reclaim,
reverse — was closed here once (`9fb43f9`, prior-day high/low sweep-and-reclaim on
QQQ 5-min, 523 sessions, −0.19R at 09:30–11:00). These variants differ in their
references (session opens and the Asian range) and their windows, but you should
know the prior is negative.

### Three ex-ante variants (NQ 1-minute, Databento A)

| | V1 · NY-open Judas | V2 · midnight open | V3 · Asian-range sweep |
|---|---|---|---|
| reference | 09:30 ET open | 00:00 ET open | Asian range, 18:00–00:00 ET high / low |
| manipulation window | 09:30–10:30 ET | 09:30–11:00 ET | 02:00–05:00 ET (London) |
| manipulation | trades beyond the reference by **≥ 0.10 × ATR14** | same | trades beyond the Asian high/low by **≥ 0.10 × ATR14** |
| reclaim (trigger) | first 1-min **close back through** the reference, inside the window | same | first 1-min close back **inside** the Asian range, inside the window |
| entry | next bar's open, **opposite** the manipulation | same | same |
| stop | manipulation extreme ± 1 tick | same | same |
| target / exit | **2R**, else flat at 15:59 | prior-day RTH high (longs) / low (shorts); skipped if < 1R away; else flat at 15:59 | none — flat at 15:59 (distribution into NY) |

- **ATR14** = mean of the prior 14 RTH daily true ranges, prior sessions only.
  **k = 0.10** is fixed and declared, not fitted.
- One trade per variant per day. Half days and roll days are excluded. Every
  return is within one contract.
- **No hindsight:** nothing is labelled "PO3" from the day's own close. Every input
  is known by the entry bar.
- **Costs:** NQ $2.25 + 1 tick per side; MNQ $0.62 + 1 tick.

### Baselines and tests

- **Same-time random-direction entries** with identical stop and exit geometry,
  5,000 simulations per variant.
- **The repository's ORB family** on NQ, with its frozen specs (from the rerun queue).
- **Holm** across the three variants.
- **Kill:** Sharpe ≥ 0.8, PF ≥ 1.3, beats the random-direction null at Holm
  p ≤ 0.05, and beats the ORB baseline. Otherwise closed.

### Data roles — this needs your confirmation

"Walk-forward from 2010 excluding seen windows" plus "a final holdout of the most
recent unseen ~12 months" has an awkward consequence. **Every intraday day from
2016-01-04 to 2026-08-31 is seen** (QQQ 1-minute, read by many studies), and QQQ
daily data to 2026-09-11 is seen as well.

| role | proposed block |
|---|---|
| walk-forward (anchored, 3y train / 1y test) | **2010-06 → 2014-12**, NQ 1-minute, never read by any intraday study |
| **final holdout, read once** | **2015-01 → 2015-12**, the most recent ~12-month unseen intraday block |
| recent unseen stub | 2026-09-12 → 2026-09-24, too short for anything |

**UPDATE 2026-09-25:** study (b) has since traded NQ 1-minute bars across
2010–2020, so **2015 is no longer unseen** (register §7). No unseen ~12-month
intraday block remains. **Revised question:** for Power of 3, choose between
(1) walk-forward on 2010–2020 labelled as read by other studies, with the final
holdout on **forward data** from registration, or (2) the same labelled block as
studies (a)–(d), with no final holdout until forward data accrues.

---

## P2. (early November) Top-up proposal

Once 30+ fresh sessions exist after 2026-09-25, propose a confirmation-only
holdout top-up within the USD 125 cap. Not due yet.

---

## P3. Committing Databento-derived data — held, because this repository is PUBLIC

You asked for the derived datasets (1-min, 5-min, daily bars; footprints; big
orders) to be committed. `smartybash/Claude-1` is **public**. Pushing them would
publish licensed Databento market data, which their licence almost certainly does
not permit, and a public push cannot be undone once it is cached. I have **not**
committed any Databento price or volume data.

- **Built and kept locally:** `data/clean/` — bars_1m 261 MB (392 monthly files,
  each < 1 MB), bars_5m 42 MB, daily bars, roll tables.
- **Committed:** only summary statistics (`data/clean/build_notes_*.json`, the
  data-quality note), which are not market data.
- **Nothing is at risk meanwhile.** The raw batch files re-download free until
  about 2026-10-25, and `scripts/databento/build_derived.py` rebuilds everything
  in minutes.

**Options:**
1. **Make the repository private**, then I commit the data as you asked, split by month.
2. Keep it public and commit **only** the scripts, results and summary statistics
   (the current state). Rebuild from raw while the 30-day window lasts.
3. Store the data somewhere private you control (for example a private repo or a
   drive), and I push it there.
