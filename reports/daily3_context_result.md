# Three daily effects — seen-data context (NOT a test)

Pre-registered at `3390a46`. NQ 2010-06-07 → 2026-09-24, **seen**, context only;
the test is forward paper-tracking from 2026-09-25 with the first review in 12
months. Raw output: `reports/daily3_context_output.txt`. Costs NQ $2.25 + 1 tick
per side, plus one round trip per roll crossed. Null: 5,000 exposure-matched
random-entry lists (same direction, sessions held, minute of day and cost).

| rule | version | trades/yr | $/trade (NQ) | Sharpe | PF | max DD $/NQ | null p |
|---|---|---|---|---|---|---|---|
| D1 daily FVG | archived (look-ahead) | 17 | +1,782 | +0.78 | 2.12 | 53,391 | 0.007 |
| D1 daily FVG | **repaired (frozen)** | 15 | +1,309 | +0.48 | 1.61 | 63,720 | **0.078** |
| D2 compression breakout | archived (look-ahead) | 55 | +1,807 | +0.81 | 1.55 | 255,580 | 0.031 |
| D2 compression breakout | **repaired (frozen)** | 53 | +1,534 | +0.64 | 1.41 | 345,423 | **0.277** |
| D3 oversold bounce | archived | 21 | +636 | +0.88 | 1.92 | 19,009 | 0.001 |
| D3 oversold bounce | **repaired (frozen)** | 21 | +622 | +0.84 | 1.86 | 23,728 | **0.002** |

What the context says, before any forward data:
- **The look-ahead was worth a lot.** Repaired, D1 loses about a quarter of its
  per-trade edge and no longer clearly beats the null (p 0.08). D2 is still
  positive but **no better than random entries with the same exposure** (p 0.28):
  most of its profit is NQ's upward drift over positions that overlap heavily
  (drawdown $345k on one contract, because signals stack).
- **D3 survives both.** The oversold bounce beats the exposure-matched null by a
  wide margin (p 0.002) with the causal 15:58 signal.
- All three are paper-tracked forward exactly as registered; nothing here changes
  a rule or a verdict.
