# Databento register — data roles, waivers, spend rules

Committed **before** any Databento data is requested. Nothing here may change
after a Databento file is read, except by a new, dated entry below the old one.

## 1. Budget

- Lifetime Databento spend on this account ≤ **USD 125**; plan ≤ **USD 115**.
  Prior spend at registration: **$0** (no `data/raw/`, no ledger).
- `get_cost` for every pull → one plan table → user writes "approved" → only that
  exact plan is executed. Any change needs a new approval.
- Batch jobs only. Every job is logged in `data/databento_ledger.csv` (job id,
  schema, symbols, range, estimate, billed, timestamp). **Stop if billed > estimate.**
- Batch files re-download free for 30 days; all tick-level work finishes inside that
  window.

## 2. Tick split for pull B (NQ trades) — decision D2

| role | dates | why |
|---|---|---|
| **discovery** | **2026-03-02 → 2026-05-29** | never read by any study in this repository |
| **excluded** | **2026-06-01 → 2026-08-20** | June is in the sealed register (`holdout.py`, prefix `202606`) and was consumed by RP-010; 2026-06-18 → 2026-08-20 was RP-010's sample |
| **holdout** | **2026-08-21 → latest** | never read (the ATAS recordings of these dates are 5-point and were never analysed for order flow) |

- The holdout is **read once, at the very end**, for RP-011 and every other tick
  hypothesis **together**. No tick hypothesis sees it earlier.
- The loader enforces the exclusion in code: dates in the excluded window raise,
  exactly as `holdout.assert_unsealed` does for the sealed register.

## 3. RP-011 waiver — decision D3

**Waived: only** the ATAS recorder-status-file requirement of the RP-011
forward-recording quality gate.

**Replaced by a Databento integrity check**, per session:
1. **coverage** — full RTH session present, first and last trades inside the cash window;
2. **gaps** — no interval between consecutive trades longer than a threshold stated
   before reading (60 s during RTH), reported per session;
3. **volume reconciliation** — the session's summed trade volume reconciled to the
   statistics schema (pull C) daily volume for the same instrument; the tolerance and
   the treatment of spread/implied trades are stated in the integrity script's
   docstring before it runs.

**All other RP-011 gates stand**: measured 0.25 grid, full cash session, aggressor
labels with zero nulls (Databento side `N` counts as a null for this gate),
monotonic timestamps, no duplicate-date ambiguity, no previous research use, ≥ 50
fresh sessions, and the seven-condition counts gate before any outcome.

## 4. What counts as seen

Per the user's rule: **any date already used by a QQQ or NQ study in this
repository counts as seen**, because QQQ and NQ track the same index. This applies
across resolutions: a date read at daily resolution is seen for daily studies.

---

## 5. Decision logged 2026-09-25 — the 2010–2020 block for studies (a) and (b)

**Option 1 chosen.** 2010–2020 is used as the best available out-of-sample block
for the overnight-drift overlay (a) and the regime switch (b), and is reported
**separately**, labelled:

> **never used for this hypothesis; read by other daily studies, incl. overnight
> gap base rates**

Basis: QQQ daily 1999–2026 was read by the oversold bounce (`5a5051a`), gap-fill
base rates (`e6e42c4`), daily FVG (`0761d41`) and the daily range breakout
(`2fed2b4`); QQQ 1-minute 2016–2020 by the IB-pullback holdout and RP-13. The
strict reading of §4 would leave (a) and (b) with no historical block; it was
considered and not chosen.

**The only true out-of-sample data for (a) is data after its registration date**,
evaluated later. **Nothing is promoted on backtest alone.**

**(b) is a strict one-shot replication.** Its prior is this repository's closed
result — regime forecastability 0 of 14, and `reports/trend_regime_study.md`
(daily ADX / efficiency ratio do not predict trend vs chop). If (b) fails it is
closed permanently with no re-tuning. If it passes, the conflict with
`trend_regime_study.md` must be explained before anything else is done with it.

---

## 6. Approved pull plan — logged 2026-09-25, before submission

Approved with one change to B: trimmed to the discovery window, the holdout window
(2026-08-21 session onward) and five RTH sessions from the excluded window for the
ATAS aggressor cross-check (spread June → 08-20, including the busiest, 2026-07-29,
539,648 ATAS RTH prints). Re-quoted total ≤ USD 95, so it runs without a further
approval, as instructed. **The ~USD 27 saved stays unspent.**

| job | schema | symbols | start (UTC) | end (UTC) | GB | est. USD |
|---|---|---|---|---|---|---|
| A | `ohlcv-1m` | `NQ.v.0,ES.v.0` | 2010-06-06 | 2026-09-24T20:30:00Z | 0.628 | 40.9756 |
| B1 | `trades` | `NQ.v.0` | 2026-03-01T23:00:00Z | 2026-05-29T21:00:00Z | 1.193 | 31.1119 |
| B2 | `trades` | `NQ.v.0` | 2026-08-20T22:00:00Z | 2026-09-24T20:30:00Z | 0.399 | 10.4055 |
| B3-06-24 | `trades` | `NQ.v.0` | 2026-06-24T13:30:00Z | 2026-06-24T20:00:00Z | 0.017 | 0.4361 |
| B3-07-09 | `trades` | `NQ.v.0` | 2026-07-09T13:30:00Z | 2026-07-09T20:00:00Z | 0.011 | 0.2884 |
| B3-07-29 | `trades` | `NQ.v.0` | 2026-07-29T13:30:00Z | 2026-07-29T20:00:00Z | 0.021 | 0.5572 |
| B3-08-06 | `trades` | `NQ.v.0` | 2026-08-06T13:30:00Z | 2026-08-06T20:00:00Z | 0.015 | 0.3785 |
| B3-08-19 | `trades` | `NQ.v.0` | 2026-08-19T13:30:00Z | 2026-08-19T20:00:00Z | 0.014 | 0.3555 |
| C | `statistics` | `NQ.v.0` | 2026-03-01 | 2026-09-24T20:30:00Z | 0.032 | 0.0300 |
| | | | | | **total** | **84.5386** |

B3 sessions are **data-quality only** (Databento side vs ATAS aggressor label on the
same prints). They enter no test, hypothesis or feature.

**Top-up, noted for later:** once 30+ fresh sessions exist after 2026-09-25 (early
November), propose a second, confirmation-only holdout within the USD 125 cap.

---

## 7. Seen status after studies (a) and (b) — logged 2026-09-25

Study (b) traded NQ 1-minute bars across its approved decisive block,
2010-07-20 → 2020-12-31. Under §4, **every NQ intraday day 2010–2020 is now
seen**. With QQQ 1-minute 2016-01 → 2026-08-31 already seen, **no unseen
intraday block of useful length remains** (2026-09-01 → 2026-09-24 is a stub).

Consequence for later studies: new intraday studies (c) and (d) use the same
treatment you approved for (a) and (b). 2010-06 → 2020-12 is reported
separately, labelled **"never used for this hypothesis; read by other studies,
incl. study (b)"**; 2021 → registration is reported as seen and not decisive;
forward data after registration is the only true out-of-sample. The Power of 3
holdout question (P1) is updated accordingly in `decisions_pending.md`.
