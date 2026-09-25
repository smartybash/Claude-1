# Study (a) — overnight drift overlay: result

Pre-registered at `reports/db_a_overnight_drift_prereg.md` (`7cf6513`) before any
Databento data was requested. Harness `scripts/databento/study_a_overnight.py`;
raw output `reports/db_a_overnight_drift_output.txt`. Databento `ohlcv-1m`,
`NQ.v.0` / `ES.v.0`, unadjusted prices; the SMA uses ratio back-adjusted RTH
closes; every traded return is within one contract. 300 roll and short-session
nights of 4,189 were skipped in every arm.

**Plumbing check:** NQ buy-and-hold earns $212,950 per contract over 2011–2020;
NQ rose about 10,900 points in that span (× $20 ≈ $218k).

## Decisive block — 2011-03-23 → 2020-12-31
*Never used for this hypothesis; read by other daily studies, incl. overnight gap
base rates.*

| | overlay | always overnight | buy and hold | null p (Holm) |
|---|---|---|---|---|
| **NQ** Sharpe | **+0.81** | **+0.81** | +0.84 | 0.32 (0.51) |
| NQ CAGR · PF · trades | 6.67% · 1.23 · 2,046 | 8.55% · 1.22 · 2,335 | 18.62% | |
| NQ max DD $/NQ · $/MNQ | 36,132 · 3,627 | 42,280 · 4,245 | 55,680 · 5,568 | |
| **ES** Sharpe | **+0.29** | +0.22 | +0.64 | 0.25 (0.51) |
| ES CAGR · PF · trades | 0.33% · 1.07 · 2,006 | 0.91% · 1.05 · 2,335 | 11.85% | |
| ES max DD $/ES · $/MES | 25,643 · 3,411 | 37,520 · 4,971 | 49,962 · 4,996 | |

**The 200-day SMA filter adds nothing on NQ**: the overlay's Sharpe equals the
unconditional overnight hold's. A random selection of the same number of nights
does as well (p = 0.32). On ES the overlay is barely positive.

## Seen block — 2021-01-01 → 2026-09-24 (not decisive)

| | overlay | always | B&H | null p |
|---|---|---|---|---|
| NQ Sharpe | +0.82 | +0.54 | +0.57 | **0.043** |
| ES Sharpe | +0.71 | +0.35 | +0.67 | **0.018** |

The period where the idea was first explored does show the filter working — the
earlier informal result was real **in that sample**. It does not exist in the
decade before. **By year**, the NQ overlay is negative in 2011, 2012, 2016 and
2022, and carries most of its total in 2020, 2024 and 2025.

## Kill criteria — 2010–2020 block

| | Sharpe ≥ 0.8 | PF ≥ 1.3 | null Holm p ≤ 0.05 | Sharpe ≥ B&H | verdict |
|---|---|---|---|---|---|
| NQ | +0.81 ✓ | 1.23 ✗ | 0.51 ✗ | +0.81 vs +0.84 ✗ | **KILLED** |
| ES | +0.29 ✗ | 1.07 ✗ | 0.51 ✗ | +0.29 vs +0.64 ✗ | **KILLED** |

## Verdict

> **Overnight drift overlay: killed on both instruments.** The unconditional
> overnight premium on NQ is real (Sharpe ≈ 0.8, 2011–2020). The 200-day SMA
> filter adds nothing to it out of sample, and neither version beats buy-and-hold
> or a random-night null.

No forward evaluation is needed: the forward block could only confirm a filter
that the 2011–2020 data already shows is not load-bearing.
