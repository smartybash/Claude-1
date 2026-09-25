# Studies (c) and (d) — results

Pre-registered at `reports/db_cd_preregistration.md` (`e68b18c`) before either
rule touched any data. Harness `scripts/databento/study_cd.py`; raw output
`reports/db_cd_output.txt`. Costs per side NQ/ES $2.25 + 1 tick, MNQ/MES $0.62 +
1 tick; entry at the next bar's open; honest stop fills; stop first.

**A note on the null.** Random-direction entries pay the same costs, so the null
distribution sits well below zero when costs are material. A rule can "beat" it
while losing money — (d) does, at Sharpe −0.69 against a null 95th percentile of
−1.04. **The frozen Sharpe and profit-factor thresholds decide these studies, not
the null alone.**

## (c) Noise-boundary intraday momentum (Zarattini, Aziz & Barbon 2024)

| | Sharpe | CAGR | PF | trades | max DD $/contract · $/micro | null p |
|---|---|---|---|---|---|---|
| **ES, 2010–2020** (decisive) | **−0.24** | −2.76% | 0.95 | 2,538 | 36,248 · 5,093 | 0.012 |
| **NQ, 2010–2020** (decisive) | **+0.61** | 3.23% | 1.16 | 2,451 | 14,661 · 1,520 | 0.0006 |
| ES, 2021–2026 (seen) | +0.47 | 4.11% | 1.10 | 1,388 | 39,864 · 4,257 | 0.012 |
| NQ, 2021–2026 (seen) | +1.17 | 10.85% | 1.27 | 1,349 | 33,504 · 3,495 | 0.0014 |

- **On ES, the paper's own index, the rule loses** in 2010–2020 (Sharpe −0.24).
- **On NQ the direction carries real information.** Sharpe +0.61 against a null
  95th percentile of +0.16 (Holm p 0.0012). It is still **below the frozen bar**:
  Sharpe < 0.8 and PF 1.16 < 1.3.
- **Concentration:** 2018 contributes $37,942 of the NQ decisive block's $59,420.
  Five of eleven years are negative.
- 2021–2026 (seen, not decisive) is stronger on NQ (Sharpe 1.17). That pattern —
  strong where the idea is fashionable and weaker before — recurs across this batch.

**Verdict (c): KILLED on both instruments by the frozen criteria.** It is the
closest miss so far: genuine directional information on NQ, too little of it
after costs in the decisive block. **No rescue by re-tuning.** If you want it
pursued, the only admissible route is forward data under this exact frozen rule.

## (d) Liquidity sweep — PDH / PDL / ONH / ONL, fade the reclaim, 2R, NQ

| | Sharpe | CAGR | PF | trades | win | max DD $/NQ · $/MNQ |
|---|---|---|---|---|---|---|
| **2010–2020** (decisive) | **−0.69** | −4.02% | 0.89 | 3,709 | 34.7% | 33,002 · 6,001 |
| 2021–2026 (seen) | +0.04 | −0.15% | 1.01 | 2,049 | 32.9% | 44,168 · 5,194 |

Every level loses in the decisive block, $ per NQ trade after costs: **PDH −18.9,
PDL −11.7, ONH −3.6, ONL −0.9.** The strategy loses in 9 of 11 years.

**Verdict (d): KILLED.** It repeats this repository's closed QQQ result (`9fb43f9`,
−0.19R) on sixteen years of NQ.
