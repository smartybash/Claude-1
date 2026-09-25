# Power of 3 — result: CLOSED

Pre-registered at `856328c` (`reports/po3_preregistration.md`). NQ 1-minute,
2010-06-07 → 2026-09-24, **seen data**, run once. Raw output `reports/po3_output.txt`.
Costs per side NQ $2.25 + 1 tick, MNQ $0.62 + 1 tick.

| variant | trades | Sharpe | PF | win | CAGR | max DD $/NQ · $/MNQ | null p (Holm) | verdict |
|---|---|---|---|---|---|---|---|---|
| **V2 midnight open (primary)** | 1,059 | **−0.43** | 0.84 | 36.7% | −2.8% | 95,806 · 10,147 | 0.60 (1.00) | **fails** |
| V1 NY-open Judas | 2,589 | −0.54 | 0.88 | 33.8% | −5.8% | 148,492 · 16,844 | 0.99 (1.00) | fails |
| V3 Asian-range sweep | 787 | −0.18 | 0.91 | 18.7% | −2.1% | 52,103 · 5,648 | 0.42 (1.00) | fails |

The primary loses after costs in 10 of 17 years. It does not beat random
direction with the same geometry, and it is below the ORB baseline (−0.37).

> **Verdict: Power of 3 is closed** (decision P1: fail = close). The secondary
> variants also fail and cannot rescue it. This repeats the repository's earlier
> sweep-and-reclaim result (`9fb43f9`) and study (d) on NQ.
