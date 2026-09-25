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

---

## P4. RP-011 "zero null aggressor labels" — interpretation applied (review)

Databento side N appears 83 times in discovery: 65 at the 18:00 ET Globex reopen
auction, a few at 07:05 / 08:30 / 18:3x, and **one in RTH**. Read literally over
the whole Globex session, the gate would fail 64 of 65 sessions because of the
reopen auction, which RP-011 never reads. I applied it to the **RTH data RP-011
reads**: a session with any RTH N print fails. This is an interpretation, not a
waiver. Say if you want the literal whole-session reading instead (which would
block RP-011).

---

## P5. RP-011 Stage 1 outcome protocol — adopted from RP-010 (review)

RP-011's frozen spec fixed the construction and the counts gate but no Stage 1
outcome protocol. Rather than invent one, I adopted **RP-010's approved Stage 1
structure** (horizons, controls, load-bearing tests, eleven pass and ten kill
conditions), applied per time block. I added a 15-minute primary horizon, Holm
across the four blocks, and a ±2% tolerance on the D3 volume reconciliation.
Registered in `reports/rp011_stage1_preregistration.md` before any RP-011 window was
built. Override any of it if you disagree; nothing has been read yet.

---

## P6. RP-011 stopped at the quality gate — volume reconciliation (decide)

Details: `reports/rp011_stage1_result.md`. **27 of 65 discovery sessions pass;
50 are needed.** 60 pass everything except the ±2% volume check. Tick volume is
**always below** CME cleared volume (median −2.1%, never above; Good Friday
−0.01%), which fits cleared volume including block and spread-leg trades that the
outright feed does not carry. ATAS matched Databento to within 0.01%, so the
original ATAS data would have failed this check too. No RP-011 window has been
built.

**Options:**
1. **Accept the stop.** RP-011 stays frozen; no Databento-based Stage 1.
2. **Amend the volume criterion, declared before any window is built** (my
   recommendation): **one-sided** — trades ≤ cleared volume (no invented prints),
   with a shortfall of at most 5%. 56 sessions pass, so the gate clears and Stage 1
   runs unchanged otherwise. Caveat: the 5% figure is chosen after seeing the
   deviation distribution (not any outcome). ±4% gives the same 56; ±3% gives 49,
   which fails the gate.
3. **Buy the NQ calendar-spread trades** for the discovery window, to subtract
   spread-leg volume and keep ±2%. Needs a quote and your approval; block trades
   would still be unexplained, so ±2% may fail anyway.

RP-011 Stage 1 is on hold until you choose. The holdout is untouched.

**P6 addendum — disclosure (added after step-4 tape reruns T01–T17).** After
RP-011 stopped at its gate I moved on to step 4, and the repository's closed tape
studies have now read forward returns on the **same 61 discovery sessions**. T01
(absorption: heavy delta with no price progress) is close to RP-011's absorption
state. So if you choose option 2, RP-011's discovery read would **not** be clean;
the D2 holdout (23 sessions, untouched) would carry the whole confirmatory
weight. Your queue put RP-011 before step 4, and I took its registered stop as
the end of that item. Say if you would have wanted the tape reruns held. **T18
(RP-010 itself, RP-011's direct predecessor) is held until you decide P6.**

**P3 note (added 2026-09-25).** Commit `31428d8` pushed five RP-009 frozen-output
tables (`reports/step4/frozen/rp009_*.parquet`: per-session barrier excursions
in bps and barrier outcomes, derived from Databento bars, no prices or volumes).
They are now untracked and ignored, but remain in the public history. If you
want them purged from history too, that needs a force-push rewrite, which I have
not done.

---

## P7. Three multi-day daily effects replicate on NQ (decide whether to pursue)

Step 4's archive reruns (verdict agreement only; nothing revived) show three
**positive, never-registered daily effects** holding on 16 years of NQ:

| effect | QQQ (repo, 27y) | NQ 2010–2026 (gross; daily risk makes costs negligible) |
|---|---|---|
| daily FVG continuation (3R) | +0.476R, t 5.14 | +0.542R, t 4.71, 286 trades |
| 5-day compression breakout (3R) | positive | +0.366R, t 5.88, 927 trades |
| oversold bounce (3+ down closes, next close) | the one real daily effect | +25 bp, t 3.19, positive in every 5-year block |

They are **multi-day or overnight holds** — Topstep 50K bans overnight holds
(RP-012C), so personal capital only. Every NQ day is already seen, so the only
admissible test is **forward**: a fresh pre-registration, frozen specs, evaluated
on sessions after its registration date (the P2 top-up would serve for daily bars
too — daily OHLCV from the statistics/ohlcv schemas is cheap).

**Options:** 1) pre-register a forward-only evaluation of the three (I draft,
you approve); 2) leave them as context; 3) close them.
