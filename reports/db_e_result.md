# Study (e) — simple intraday rules: result

Pre-registered at `reports/db_e_preregistration.md` (`3b5f631`). Harness
`scripts/databento/study_e.py`; raw output `reports/db_e_output.txt`. NQ `ohlcv-1m`;
costs per side NQ $2.25 + 1 tick, MNQ $0.62 + 1 tick.

## Decisive block — 2010–2020
*Never used for this hypothesis; read by other studies, incl. study (b).*

| rule | Sharpe | CAGR | PF | trades | win | max DD $/NQ · $/MNQ | null Holm p |
|---|---|---|---|---|---|---|---|
| gap-and-go | −0.09 | 0.04% | 0.94 | 210 | 39.5% | 9,340 · 1,055 | 0.99 |
| gap-fade | +0.01 | 0.25% | 1.01 | 279 | 27.2% | 8,692 · 889 | 0.99 |
| PDH/PDL breakout | −0.16 | −2.31% | 0.97 | 2,107 | 43.9% | 38,102 · 4,678 | 0.90 |
| intraday Donchian | +0.14 | −0.56% | 1.03 | 2,620 | 41.6% | 26,534 · 3,674 | 0.54 |

## Seen block — 2021 → 2026-09-24 (not decisive)

gap-and-go +0.43 (null p 0.033), gap-fade +0.34, PDH/PDL breakout −0.00, Donchian
+0.05. Gap-and-go is again stronger in the seen period than in the decade before.

## Verdict

> **All four killed.** None clears any kill criterion in the decisive block. The
> gap rules trade rarely (the 0.5 × ATR14 gap floor gives ~20–25 trades a year),
> and the two breakout rules trade often but net nothing after costs.

The two rules in (e) that reuse frozen repository specs — ADR/VWAP pullbacks and
the multi-day box breakout — run in step 4 with the other closed studies.
