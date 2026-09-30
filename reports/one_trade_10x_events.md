# $10,000 → $100,000 in one trade, any underlying, odds on our side

Research on real chains priced at the 2026-09-29 close, replayed against
every past earnings event for each stock. Reproduce with
`scripts/event_10x.py`; engine tests in `tests/test_event_10x.py`.

**Result: no trade meets the brief.** A 10x can't be likely to win — the
ceiling is 10% for any fairly priced long position. The only reachable form
of "odds on our side" is positive expected value, and after scanning every
option and 1,153 vertical spreads across the only two catalysts in the
window, **zero positions** have an edge that survives robustness checks.
What *can* be done is to pick the structure with the best odds of hitting
10x: about 1 in 13.

## 1. What 10x allows

For any long option position bought at a fair price, Markov's inequality
caps the probability that it pays 10x its cost at 1/10:

```
P(payoff ≥ 10 × cost) ≤ E[payoff] / (10 × cost) = 10%
```

This holds for any underlying, strike, expiry or structure. So "odds on
our side" can't mean likely to win; the most it can mean is that the true
probability beats the market's, making the expected value positive. That's
what this looks for.

## 2. Where a 10x could come from this week

Over three to five sessions, only a scheduled jump is plausibly big enough.
Scanning the earnings calendar for 2026-09-30 through 10-07 turns up two
liquid names whose Friday 10/02 weekly options span the event:

| Name | Report | Spot | Implied move to Fri | Realised since 2013 | Realised / implied |
|---|---|---|---|---|---|
| Micron (MU) | **tonight**, after close | $1,065.08 | ±7.58% | 6.55% | 0.86 |
| Nike (NKE) | Thu 10/01, after close | $35.84 | ±8.65% | 6.15% | 0.71 |

Both straddles are priced above what these stocks typically do on
earnings. That's the normal state of affairs (event options are usually
rich), and Nike is especially expensive.

## 3. How each trade was tested

Each option, plus every liquid vertical spread (both legs with open
interest ≥ 100, long leg at the ask, short leg at the bid, IBKR commissions
included), was sized as a $10,000 all-in position. Each one was then
checked against:

- **The market.** Model-free probability of reaching the $100k level, read
  from adjacent-strike spreads. A call spread between neighbouring strikes
  is a digital option, and its price is the market's probability.
- **History.** Every past report for the same stock (106 each, back to
  2000), replayed over the identical window and applied to today's spot.
- **Robustness.** Expected value above the $10k stake had to hold on all
  events, on the modern era (2013+), with the single best event removed from
  each sample, and in ≥ 90% of bootstrap resamples. The single-event checks
  were added after the first pass surfaced a false positive (§4).

## 4. The apparent edge that wasn't

Micron's deep crash puts looked like the find. The 900 put (−16.9% needed):

| Sample | P(10x) | Expected value per $10k |
|---|---|---|
| Market | 2.1% | — |
| All 106 events | 6.6% | $29,805 (+198%) |
| 2013+ (54 events) | 3.7% | $11,118 (+11%) |
| 2013+, **without June 2015** | — | **$2,103 (−79%)** |

All of it comes from the crash tail. On 25 years of data Micron fell more
than 15% through an earnings window about 7 times in 106. Most of those
were in the 2000s memory-bust era. In the modern era the whole edge rests
on one quarter: June 2015, −22%. Deep put spreads on the same thesis go to
**$0** once that event is removed.

This is also a multiple-comparisons trap. I scanned hundreds of correlated
positions and picked the best, which will make noise look like signal. The
first version of the scanner ranked by the 12 most recent events and showed
"+125% EV" on Nike puts. That came from one quarter (June 2024, −20.5%).
Both checks are now built into the script so it can't report that kind of
result on its own.

## 5. Final scan

| | Micron | Nike |
|---|---|---|
| Best market-implied P(10x) | **7.5%** (vertical) | 4.0% (naked; no spread data) |
| Best naked-option P(10x) | ~2–3% | ~4% |
| Positions passing every robustness check | **0** of ~1,300 | **0** |

The market probabilities come from call and put spreads between adjacent
strikes. Where options trade in pennies those spreads are noisy: Nike's 44
call was marked above its 44.5, which implied a spurious 8% digital. The
estimates are therefore forced to be monotone in strike (isotonic
regression) before use. Without that step Nike showed 5.9%.

## 6. Best-structured 10x available (not an edge)

A naked OTM option is the worst way to buy a 10x, because most of its value
sits in outcomes far beyond the level you need. A vertical spread that costs
~10% of its width pays 10x on a much smaller move, and its probability can
get close to the 10% ceiling:

**MU +1200 / −1215 call spread, Oct 2 expiry** (the 1200/1220 is
effectively identical)
- $1.35 debit (1200 call at the ask, 1215 call at the bid) × 73 spreads ≈
  $9,950 all-in
- Max value ≈ $109,000 if MU closes Friday at or above $1,215
- Worth $100,000 at MU ≈ $1,214 (+14.0%)
- Market-implied odds **7.5%** (about 1 in 13). Micron did +14% or more in
  5 of 54 modern earnings windows (9.3%). Recent examples: Dec 2025 +14.4%,
  Sep 2024 +14.4%, Mar 2024 +17.2%.
- Expected value on modern history ≈ **$10,130 per $10,000: breakeven.**
  Without the single best modern event it drops to $8,257. That makes it a
  fairly priced 1-in-13 bet, with odds about 2.5× better than any naked
  option offering the same payoff.

Practical constraints if taken:
- **Prices are from last night's close.** Micron reports after today's
  close, so the position has to be opened during today's session at live
  prices. Re-run the scanner on today's chain first.
- **Close before expiry.** If MU finishes between 1200 and 1215, only the
  long leg is in the money. Exercising 7,300 shares means ~$8.8M of stock,
  which a $10k account can't carry, so IBKR would liquidate.
- **Most likely outcome: the ~$9,950 goes to zero** (~92% of the time).

## 7. Bottom line

Nothing here puts 10x odds on your side. The market prices both events
roughly correctly in the modern era, and the one apparent mispricing was a
single 2015 quarter. The best-odds 10x structure is a ~1-in-13 shot at
roughly zero expected value before any edge — and zero is the best case,
since it assumes you get filled at the prices above. It's reasonable only as an amount you'd be
comfortable losing, not the whole account.

## Reproduce

```
python scripts/event_10x.py --chain data/mu_chain_20260929.json \
    --daily data/mu_daily.json --earnings data/mu_earnings_dates.json \
    --chain-date 2026-09-29 --expiry 2026-10-02
python scripts/event_10x.py --chain data/nke_chain_20260929.json \
    --daily data/nke_daily.json --earnings data/nke_earnings_dates.json \
    --chain-date 2026-09-29 --expiry 2026-10-02
```

Data: Alpha Vantage `HISTORICAL_OPTIONS` (2026-09-29 close, 10/02 expiry),
`TIME_SERIES_DAILY` (1999-11-01 to 2026-09-29, splits detected and
back-adjusted: MU 2000; NKE 2007, 2012, 2015), `EARNINGS` and
`EARNINGS_CALENDAR`. The Nike chain is a transcribed OTM/ATM subset without
bid or open interest, so the vertical scan was run on Micron only.
