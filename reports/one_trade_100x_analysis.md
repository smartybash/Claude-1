# $10,000 → $1,000,000 in one option trade: the research

Asked: research and implement a single 0DTE or 3–5 DTE option trade that turns
$10,000 into $1,000,000. This is that research, done on real chains and 25
years of price history. The reproducible version is `scripts/lottery_math.py`.

**Finding: the probability is at most 1%, is about 0.4% for the best real
strike available, and the required move has occurred zero times in 2,248
comparable sessions.** I did not select a trade to implement, because the
arithmetic below shows "solid" and "100x" cannot both be true of the same
position — not as a matter of caution, but as a consequence of how options
are priced.

## 1. The ceiling, model-free

An option's price is the risk-neutral expected value of its payoff. Markov's
inequality then gives, for any non-negative payoff `X` costing `price`:

```
P(X ≥ M × price) ≤ E[X] / (M × price) = 1/M
```

So **P(100x) ≤ 1% for any option, any strike, any expiry, any structure** —
single leg, spread, or basket — as long as it is long-only and bought at a
fair price. This is not a forecast that could be beaten by better analysis;
it follows from no-arbitrage pricing, and it is an upper bound *before*
spread and commissions.

Two corollaries worth internalising:

- **Choosing a different DTE cannot escape it.** A longer expiry gives the
  move more time but costs more premium, so it needs a bigger move for the
  same multiple. In risk-neutral terms those cancel exactly.
- **Splitting into a sequence cannot escape it either.** Seven consecutive
  fair doublings is 2⁷ = 128x, at probability (1/2)⁷ = 0.78% — the same
  order as the one-shot bound. The 1% ceiling is conserved across any path.

The only way to beat the bound is to find a genuinely mispriced option. The
volatility risk premium runs the other way: OTM options are, on average,
systematically *over*priced relative to what they pay out.

## 2. What the real chain requires

Real SPY 0DTE calls, priced at the 2026-09-28 close for the 2026-09-29
expiry, SPY spot 765.61. For each strike: contracts $10,000 buys at the ask,
the SPY close that makes the position worth $1M, and the market's own
probability of getting there (read off the delta curve, which *is* the
market's terminal distribution).

| Strike | Ask | Contracts | SPY needed | Move required | Market P(win) | Odds |
|---|---|---|---|---|---|---|
| 772 | 0.21 | 476 | 793.01 | +3.58% | 0.310% | 1 in 323 |
| 773 | 0.14 | 714 | 787.01 | +2.79% | 0.391% | 1 in 256 |
| **774** | **0.10** | **1,000** | **784.00** | **+2.40%** | **0.418%** | **1 in 239** |
| 775 | 0.07 | 1,428 | 782.00 | +2.14% | 0.397% | 1 in 252 |
| 779 | 0.03 | 3,333 | 782.00 | +2.14% | 0.397% | 1 in 252 |
| 782 | 0.02 | 5,000 | 784.00 | +2.40% | 0.418% | 1 in 239 |
| 790 | 0.01 | 10,000 | 791.00 | +3.32% | 0.327% | 1 in 306 |

The best strike on the board is ~1 in 239. Note the shape: buying further
out doesn't help. Cheaper contracts mean more of them, but the intrinsic
value each must reach rises in lockstep. The market has already priced away
the free lunch — which is exactly what the Markov bound predicts.

## 3. What history says

The unconditional 25-year frequency of a +2.40% SPY day is 2.19%, which looks
far friendlier than the market's 0.42%. That comparison is misleading: the
unconditional figure blends 2008 and 2020 into today's quiet tape. Today's
0DTE at-the-money implied vol is 12.2% annualized — a daily sigma of 0.77%,
making the required +2.40% a **3.1-sigma move**.

Splitting the history by trailing-20-day realized volatility:

| Horizon | Threshold | All regimes | Low-vol regimes (<11%) |
|---|---|---|---|
| 1 day | +2.14% | 2.846% | **0.089%** |
| 1 day | +2.40% | 2.194% | **0.000%** |
| 3 days | +2.40% | 7.680% | 0.934% |
| 5 days | +2.40% | 12.131% | 3.247% |
| 5 days | +3.00% | 7.949% | 1.068% |

**In 2,248 low-volatility sessions across 25 years, SPY has never once gained
2.40% in a single day.** The market's 0.42% is if anything generous — it
prices overnight gap risk this sample never realised.

The 3–5 DTE horizon genuinely has more room (3.2% of low-vol 5-day windows
clear +2.40%). But a 5 DTE option costs several times the 0DTE, so the move
needed for 100x rises correspondingly, and the Markov bound still binds at 1%.

## 4. Three practical traps that make it worse

- **You cannot exercise.** The high-contract-count strikes require 3,000–5,000
  contracts. Exercising 5,000 SPY calls means buying 500,000 shares — roughly
  $390M of stock. A $10,000 account cannot; IBKR would force-liquidate into
  the close. The $1M must be realised by *selling* into whatever bid exists
  for a penny option in the last minutes of its life.
- **The spread is up to 100%.** At strikes ≥ 781 the mark is $0.01 and the ask
  is $0.02. You pay double mid on entry, which halves the contract count and
  the payoff.
- **Per-contract commissions bite hard.** At IBKR's typical $0.65/contract,
  3,333 contracts costs ~$2,166 to enter — over 20% of the stake before the
  trade does anything. (IBKR caps options commissions at a percentage of trade
  value; check your specific schedule, because on penny options the cap is
  what stands between you and a severe drag.)

## 5. The honest expected outcome

On the best available strike: **99.6% chance the $10,000 is gone, 0.4% chance
it becomes about $1M.** Expected value is negative once spread and commissions
are paid. That is a lottery ticket with better odds than Powerball and worse
odds than a single number on roulette (2.7%).

## 6. What the arithmetic of the actual goal looks like

If the real objective is $10k → $1M rather than one specific trade, the
binding constraint is time, not cleverness. 100x requires:

| Annual return | Years to 100x |
|---|---|
| 30% | 17.6 |
| 50% | 11.4 |
| 100% (doubling every year) | 6.6 |

Doubling your money every single year — which would put you among the best
traders alive — still takes six and a half years. There is no arrangement of
options that compresses this honestly, which is precisely what section 1
proves.

The Vol Desk system in this repo is the real asset here: it has an edge
thesis, structural filters, and a mechanical stop framework. Its validated
edge came from *removing* the trades that blow up accounts. Running $10,000
through that with position sizing that survives a losing streak is a slower
answer, and it is the only one with positive expected value.

## Reproduce

```
python scripts/lottery_math.py <spy_daily.csv>
```

Chain data: Alpha Vantage `HISTORICAL_OPTIONS`, SPY, 2026-09-28 close,
2026-09-29 expiry. Price history: Alpha Vantage `TIME_SERIES_DAILY`, SPY,
6,768 sessions, 1999-11-01 to 2026-09-29.
