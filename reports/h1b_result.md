# H1-B: late-day momentum on bigger days — result

Exploration on 2010–2020 only (plan b0a6556); frozen rule committed (bb1f2db);
holdout read once on 2026-09-30. Outputs: `reports/h1b_exploration_output.txt`,
`reports/h1b_exploration_grid.csv`, `reports/h1b_holdout_output.txt`.

**Verdict: FAIL → H1-B closed for good.**

| | trades | $/trade | total | p |
|---|---|---|---|---|
| Discovery 2010–2020, fitted: 15:45 entry, top-10% \|r\| days | 281 | +$97 | +$27,350 | (inflated by selection) |
| **Holdout 2021–2026, same frozen rule** | **143** | **−$88** | **−$12,528** | **0.851** |
| ES holdout, same rule | 139 | −$101 | −$14,088 | — |

## What happened

- **The fitted edge was one year.** In discovery, 2020 made $20,935 of the
  $27,350. In the holdout only 2022, the other big volatile year, made money
  (+$13,961). Every other holdout year lost: 2024 −$7,166, 2025 −$6,598, 2026
  −$11,192.
- **The direction call has no edge out of sample.** On the same big days,
  random directions do as well (sign-flip p 0.75). Shorts lost −$275 a trade.
- **Discovery warned about this, and the checks said so beforehand.** The
  original top-quintile observation had t +0.83 (95% CI −$44 to +$106 a trade),
  and 40 of the 45 grid configurations beat the cost-burdened null. That means
  the discovery p-values could not tell a real filter from a lucky one.
  Fitting found the configuration that suited 2020 best.

## Lesson for the desk

The pattern in the data was not clear; it was a few volatile days. Fitting on
2010–2020 and checking on 2021–2026 caught that before any money was at risk.
Fitting on all 16 years would have produced a backtest showing +$15k and a
filter with no edge.
