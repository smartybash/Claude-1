# Trading after the earnings reaction

You asked whether it works better to trade after the report, once the
first full RTH hour (or something similarly concrete) has shown how the
market took the news. I wrote the rules down and committed them before
computing any result (`reports/post_earnings_preregistration.md`, commit
013f68a), then tested them once.

**Short answer.** Waiting does buy you a direction signal, but it's a
small one:

- **Post-earnings drift is real.** Entering at the reaction-session close
  in the direction of the move was right 53.3% of the time over the next
  five sessions (1,299 reports, p = 0.010). It held on the six holdout
  stocks too.
- **It's worth about +0.3% over five days.** That's a small tilt for a
  stock position, nowhere near enough for an option to 10x.
- **The 10:30 first-hour rule failed.** "The first hour confirms the gap,
  ride it to the close" had a 57% hit rate but averaged −0.06% per trade,
  because the losses were bigger than the wins. The opposite rule (fade a
  gap the first hour rejects) also failed.

## 1. What was tested

Universe: the same 14 stocks as the pre-announcement study. The
reaction session is resolved by volume, prices are split-adjusted, and
"typical move" is the stock's mean absolute reaction over its previous 8
reports. Every direction was fixed in advance as continuation (or as a
fade, for the REJECT case), so nothing was fitted to the data.

| Rule | Entry | Direction | Exit | Role |
|---|---|---|---|---|
| D2 | reaction-session close | sign of the reaction | close +5 sessions | **primary (daily)** |
| D1 | reaction-session open | sign of the gap | same-day close | secondary |
| D3 | reaction-session close | sign of the reaction | close +20 sessions | secondary |
| I1 | **10:30 ET** on the reaction session | gap direction, if the first hour CONFIRMS | same-day close | **primary (intraday)** |
| I2 | 10:30 ET | against the gap, if the first hour REJECTS | same-day close | secondary |

**The 10:30 read** uses 5-minute RTH bars. G is the overnight gap and F is
the 09:30 to 10:30 return. P is where the 10:30 price sits in the
first-hour range, from 0 (the low) to 1 (the high). An event qualifies only
if |G| ≥ 0.5 × the stock's typical move.
- **CONFIRM:** F has the same sign as G, and the price sits in the 30% of
  the range on the gap's side.
- **REJECT:** F has the opposite sign, and the price sits in the other 30%.

Daily data covers 2000–2026. The intraday test covers every reaction
session from January 2024 to September 2026: 152 sessions, all 152 with
bars, 114 qualifying. The bars come from Alpha Vantage, one month per
request, and each file was checked against the stock's daily returns.

## 2. Daily results

Each test is one-sided against the sample's own base rate. "Signed" is
the average return in the predicted direction; "/typ" is the same in
units of the stock's typical earnings move.

| Rule | n | Hit | Base | p | Signed | /typ |
|---|---|---|---|---|---|---|
| **D2 reaction → +5 sessions** | **1,299** | **53.3%** | **50.0%** | **0.010** | **+0.33%** | **+0.06** |
| holdout stocks only | 578 | 54.5% | 50.2% | 0.020 | +0.30% | +0.02 |
| large reactions (≥ typical) | 572 | 54.2% | 50.1% | 0.028 | +0.59% | +0.10 |
| D1 gap → same-day close | 1,293 | 51.8% | 49.5% | 0.049 | +0.14% | +0.01 |
| D3 reaction → +20 sessions | 1,303 | 52.6% | 49.9% | 0.029 | +0.27% | −0.01 |

**D2 is confirmed** under the pre-registered rule. This is classic
post-earnings drift, and the effect is consistent: the hit rate is above
the base rate in all three sub-samples (train stocks before 2017, train
stocks since 2017, holdout stocks), though only the holdout one is
individually significant. It's also small. A stock that moved on the
report keeps drifting the same way about 53% of the time, worth roughly
a third of a percent over a week.

## 3. Intraday results (10:30 entry)

| Rule | n | Hit | Base | p | Signed | Avg win | Avg loss |
|---|---|---|---|---|---|---|---|
| **I1 CONFIRM → with the gap** | **42** | **57.1%** | **50.9%** | **0.26** | **−0.06%** | +1.43% | −2.04% |
| I2 REJECT → against the gap | 33 | 60.6% | 50.7% | 0.17 | +0.00% | +1.38% | −2.10% |
| All qualifying, with the gap (ref.) | 114 | 43.0% | 50.4% | — | −0.28% | | |

**I1 is not confirmed, and I2 isn't either.** Both rules were right more
often than not, but the average losing day was about 40–50% larger than
the average winning day, so neither made money. The CONFIRM hit rate
also wasn't stable from year to year: 14 of 22 in 2024, 3 of 8 in 2025,
7 of 12 in 2026.

Two more observations. These are descriptive only, not tested:

- **After a big gap there's still plenty of movement, but not in a
  predictable direction.** The median qualifying gap was 1.1× the
  stock's typical move. From 10:30 to the close the stock still moved
  1.6% on average (either way), about a quarter of a typical move.
- **Across all qualifying events, continuation from 10:30 was the
  minority outcome** (43%). If anything, mid-session reaction days lean
  slightly toward giving back part of the gap. This wasn't a
  pre-registered hypothesis, so it can't be claimed from this sample.
  It's a candidate for the next test.

**Sample size is the main limitation.** Two and a half years of 14
stocks gives only 42 CONFIRM events. Even if I1's +6-point lift were
real, about 400 CONFIRM events would be needed for an 80% chance of
detecting it at α = 0.05. Point 1 of §6 covers how to get there.

## 4. Worked example: Micron today (2026-10-01)

Micron reported after the close yesterday, so today was the reaction
session. Bars are from IBKR.

| | |
|---|---|
| Previous close → open | $1,065.11 → $1,053.15 (gap **−1.1%**) |
| Typical event move (last 8 reports) | 9.1% |
| Gap / typical | **0.12**: does not qualify (needs ≥ 0.5) |
| First hour | fell to $1,022.90; 10:30 price $1,032.98 (F −2.0%, P = 0.19) |
| 10:30 → close | **+6.3%** (official close $1,097.39, +3.0% on the day) |

The rule says **no trade**: the news barely moved the price relative to
what Micron normally does on earnings. If it had qualified, the first
hour would have read as a textbook CONFIRM to the downside (down from
the open and near the low at 10:30). That signal would have been short
going into a 6% rally. This is the I1 failure mode in miniature.

## 5. What this means for options

- **Drift is a stock-sized edge, not an option-sized one.** A 50-delta
  weekly option picks up roughly half of the +0.33% drift, about 0.17% of
  spot. Assume post-event implied vol of 35%. The ATM premium for five
  sessions is then about 0.4 × 0.35 × √(5/252) ≈ 2.0% of spot. So the
  drift adds about 8% to the premium's expected value, before spreads and
  assuming the options are otherwise fairly priced. That's a small,
  noisy tilt you'd need to repeat many times to collect. It isn't a
  single trade.
- **A post-event 10x is rarer than a pre-event one.** IV collapses after
  the report, and the scheduled jump has already happened. To pay 10x, a
  5-session ATM option bought at the reaction close needs roughly a +20%
  move in the reaction's direction. Since 2013 that has happened in
  **0.7%** of reports (5 in 762). A +10% drift happened 4.2% of the time,
  and a −10% reversal 3.7% of the time.
- **What does survive.** After the report, D2 is the one validated
  direction read. It can tilt a stock position or set which side of a
  spread to favour. It can't make a 10x likely.

## 6. How this fits the gate method

`reports/earnings_method.md` still returns no directional position
*before* the announcement. After the announcement:

| Window | Validated read | Use |
|---|---|---|
| Before the report | none (G1 fails) | no directional position |
| 10:30 on the reaction day | none (I1, I2 not confirmed) | no first-hour entry |
| Reaction-session close | **D2 continuation, +0.3% / 5 sessions** | tilt only; too small for options alone |

Next steps that could change this:

1. **A bigger intraday sample.** Alpha Vantage serves monthly 5-minute
   bars back to 2000. That would add about 1,300 reaction sessions for
   these 14 stocks, at one request per stock-month, and bring CONFIRM
   events to roughly 400: enough to detect an effect the size of I1's.
   Run it under a new pre-registration, including the "fade from 10:30"
   hypothesis that §3 raised.
2. **Condition D2 on the size of the surprise or reaction.** Large
   reactions drifted +0.59% (+0.10 typical) against +0.33% overall. This
   needs its own holdout before it can be used.

## Reproduce

```
python scripts/post_earnings_daily.py          # D1-D3 -> reports/post_earnings_daily_result.json
python scripts/post_earnings_intraday.py       # I1/I2 -> reports/post_earnings_intraday_result.json
python scripts/post_earnings_intraday.py --coverage
python -m pytest tests/test_post_earnings.py
```

Data: `data/daily/` (Alpha Vantage `TIME_SERIES_DAILY`) and
`data/intraday/{SYM}_{YYYY-MM}.json` (Alpha Vantage `TIME_SERIES_INTRADAY`,
5-minute RTH bars, one file per stock-month that contains a reaction
session). Intraday bars are dividend-adjusted, so every intraday
measurement is a ratio within a single session. On two days (AMD
2026-08-04 and ORCL 2026-06-10) the last 5-minute bar differs from the
official closing auction by about 1%. The tested exit uses the last bar
consistently.
