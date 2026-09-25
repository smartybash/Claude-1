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
