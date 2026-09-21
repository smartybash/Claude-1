# The holdout, read once: exactly break-even

2016–2020 QQQ, frozen native specification, **one run**. No optimisation, no
second candidate, no reinterpretation. The specification was imported from
`ib_pullback_native` unchanged.

---

## 0. Recorded first, as instructed

1. The original cross-instrument test **was economically mismatched**.
2. Native normalisation improved the pooled result from **−0.046R to
   approximately zero**.
3. The setup is **not portable** across the related instruments tested.
4. QQQ remained positive under **both** the frozen and native implementations.
5. **All four mechanism controls remained weaker than the QQQ base rule.**
6. Classification at that point: **QQQ-specific and unresolved, not closed.**

That is why the holdout was authorised, and it has now been spent.

---

## 1. A data note, before the result

**The 1-minute holdout did not exist and had to be fetched.** `QQQ_1m.parquet`
starts 2021-01-04; 2016–2020 existed only at 5-minute resolution. The frozen
rule is defined in 1-minute bars — R2 rejection, ATR14, next-bar-open entry —
so running it on 5-minute data would have been **a different rule**, the exact
error caught earlier with the frozen IB candidate.

60 months were fetched at 1-minute RTH: **489,865 bars, 1,259 sessions,
2016-01-04 → 2020-12-31**, matching the expected holdout size exactly. The rule
was then run once.

---

## 2. Trading results

| | |
|---|---|
| sessions | 1,248 |
| qualifying at 10:30 | **632 (50.6%)** |
| reached the midpoint zone | 284 |
| **trades** | **132** |
| **trades per month** | **2.20** |
| win rate | 43.2% |
| average winner | +1.373 R |
| average loser | −1.043 R |
| **EXPECTANCY** | **+0.0002 R** |
| **profit factor** | **1.0003** |
| max drawdown | 16.5 R |
| max losing streak | 7 |
| median risk | 17.61 bps (2.77 × ATR1m) |
| median cost as % of risk | 5.23% |
| exit mix | stop 73 · target 53 · close 6 |
| ambiguous bars | 0.0% |

**Gross profit 78.2715 R. Gross loss 78.2513 R. Total: +0.0202 R across 132
trades over five years.**

### Long and short

| | n | exp R | PF |
|---|---|---|---|
| long | 74 | **+0.0049** | 1.01 |
| short | 58 | **−0.0060** | 0.99 |

### By year

| year | n | exp R | PF | win% |
|---|---|---|---|---|
| 2016 | 15 | **−0.3787** | 0.50 | 26.7 |
| 2017 | 16 | **+0.5576** | 2.67 | 68.8 |
| 2018 | 34 | **−0.3267** | 0.56 | 29.4 |
| 2019 | 27 | **+0.2519** | 1.55 | 55.6 |
| 2020 | 40 | **+0.0272** | 1.05 | 42.5 |

**3 of 5 years positive**, but the swings are ±0.5 R on 15–34 trades a year.

### Stress tests

| | |
|---|---|
| after removing the best 5 | **−0.0581 R** |
| after removing the best 10 | **−0.1207 R** |
| with 50% higher costs | **−0.0277 R** |
| top 5 share of gross profit | 9.5% |
| top 10 share of gross profit | 18.8% |

**Concentration is genuinely low** — the top 5 trades carry under 10% of gross
profit. This result is not a few lucky trades. It is a flat distribution that
sums to nothing.

### Against the 2021–2025 native discovery

| | discovery | **holdout** |
|---|---|---|
| trades | 233 | **132** |
| trades/month | 3.9 | **2.20** |
| win rate | 46.4% | 43.2% |
| **expectancy** | **+0.124 R** | **+0.0002 R** |
| profit factor | 1.23 | **1.0003** |
| max drawdown | 15.3 R | 16.5 R |
| positive years | 4/5 | 3/5 |
| after best-5 removal | +0.094 | **−0.058** |
| at +50% costs | +0.110 | **−0.028** |

**The discovery effect did not appear. +0.124 R became +0.0002 R.**

---

## 3. Verdict

# CLOSED

Against the declared criteria:

| verdict | requirement | result |
|---|---|---|
| **Validated for paper trading** | PF ≥ 1.10 | **1.0003 — fails** |
| | positive after removing best 5 | **−0.058 — fails** |
| | positive at +50% costs | **−0.028 — fails** |
| **Marginal but alive** | positive, with **one** robustness failure | **three failed** |
| **Closed** | expectancy negative, PF < 1.00, or dependent on a few trades | see below |

**The letter of the closure rule is not quite met** — expectancy is +0.0002
rather than negative, PF is 1.0003 rather than below 1.00, and concentration is
low rather than extreme. I am recording that precisely rather than rounding it
into the verdict I am about to give.

**But "Marginal but alive" permits one robustness failure and three occurred**,
and a profit factor of 1.0003 on 132 trades is not a small edge — it is gross
profit and gross loss agreeing to four significant figures. The rule earned
**+0.0202 R in five years**. Under any of the three declared stress tests it is
negative. **There is nothing here to paper trade.**

**Statistical significance is not being used as the reason.** The reason is the
trading economics: **zero expectancy, PF 1.000, and negative under every stress
test.** The appendix figures are consistent but not load-bearing.

---

## 4. One structural observation, offered as fact and not as an excuse

The cost floor binds far harder in the early holdout years because cost is
per-share and QQQ traded at roughly a third of its later price:

| year | trades | median risk | risk / ATR1m | cost % of risk |
|---|---|---|---|---|
| 2016 | 15 | 19.32 bps | **3.23** | **7.41%** |
| 2017 | 16 | 16.32 | 3.57 | 7.10 |
| 2018 | 34 | 15.34 | 2.39 | 6.43 |
| 2019 | 27 | 16.83 | 3.19 | 5.31 |
| 2020 | 40 | 22.10 | **2.05** | **3.05** |
| *2021–25 (discovery)* | *233* | *17.67* | *2.27* | *2.58* |

At $100 QQQ the $0.017 round turn is 1.7 bps, forcing a minimum stop of 17 bps
≈ 3.2 × ATR; at $375 it is 0.45 bps and the ATR floor binds instead. **The rule
is therefore not scale-neutral across a 3.7× change in price level**, which is
why 2016 produced 15 trades and 2020 produced 40.

**This is recorded as a fact about the specification, not as a reason to
re-run, re-scale, or reinterpret.** The holdout was authorised once on a frozen
rule and has been spent once on that rule. The answer stands.

---

## 5. Ledger entry

| screen | sample | outcome |
|---|---|---|
| **IB midpoint pullback + R2, 1.5R — holdout** | 1,248 sessions, 132 trades, 2016–2020 QQQ | **CLOSED. Expectancy +0.0002 R, PF 1.0003, gross profit 78.27 against gross loss 78.25. Negative after removing the best 5 (−0.058), the best 10 (−0.121), and at +50% costs (−0.028). Discovery's +0.124 R did not appear. Concentration was low, so this is a flat distribution summing to nothing rather than a few lucky trades.** |

**The 2016–2020 holdout is now spent.** It was spent once, on a frozen rule,
with the criteria declared in advance. Sealed NQ dates remain unread.

---

## Appendix — formal statistics

| | |
|---|---|
| n | 132 |
| mean R | +0.0002 |
| SE | 0.1057 |
| **t** | **+0.00** |
| p (two-sided, single test) | 0.9988 |
| top-decile diagnostic (drop 14) | −0.1743 |

Reproduce: `python3 scripts/orderflow/ib_pullback_holdout.py`.
Trades in `reports/ib_pullback_holdout_trades.csv`.
