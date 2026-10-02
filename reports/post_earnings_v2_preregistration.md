# Pre-registration v2: first hour versus the market, after the earnings gap

Written and committed on 2026-10-02. At that point:
- the 2001–2012 discovery sample had been explored freely;
- no 2013–2023 intraday bar had been downloaded;
- the 2024–26 sample had been seen only in the v1 test (I1/I2), not with this rule.

The rule and the test below are fixed and will not change after validation results are seen.

## How the rule was found (discovery, 2001–2012)

The data is 5-minute RTH bars from Alpha Vantage for 14 stocks plus SPY: 532 reaction sessions with bars (`data/intraday_sessions/`).

I compared roughly a dozen candidate reads, mostly at 10:30, with 10:00 and 11:00 also tried:
- raw first-hour direction;
- position in the first-hour range;
- VWAP side;
- how much of the gap is kept;
- gap size;
- gap up versus gap down;
- pre-market versus post-market report timing;
- the stock's first-hour move against SPY;
- fade variants;
- hold periods running past the close.

Most reads either had no effect or worked in only one sub-period. One read held up in every sub-period: **the stock beating SPY over the first hour in the direction of the gap**. Discovery results:

| Sub-sample | n | Hit | Hedged mean |
|---|---|---|---|
| 2001–2004 | 50 | 70% | +1.28% |
| 2005–2008 | 60 | 70% | +0.49% |
| 2009–2012 | 58 | 62% | +0.69% |
| **All** | **168** | **67.3%** | **+0.80%** (t 5.2) |

It was positive in 10 of the 12 stocks with at least 5 events, for both gap-up and gap-down events, and after removing the top 5 outcomes (+0.63%).

The v1 rule I1 used the raw first-hour direction plus range position. This rule differs in three ways: it measures the move against the market, it has no range filter, and it is hedged.

Caveat noted before validation: the raw continuation effect weakens over 2001–2012, and v1 found no continuation in 2024–26. The validation sample decides whether the rule is still alive.

## Rule V1 (primary)

Universe and definitions are the same as v1: `resolve_reactions`, typical move = mean |reaction| of the previous 8 reports, and the first 4 reports of each stock are skipped.

1. G = reaction-session open / previous close − 1 (daily bars). The event qualifies if |G| ≥ 0.5 × typical.
2. At 10:30 ET, using the close of the 10:25 bar:
   idio = sign(G) × [(stock₁₀:₃₀ / stock_open − 1) − (SPY₁₀:₃₀ / SPY_open − 1)].
   Both opens are the first 5-minute bar's open.
3. If idio > 0, enter in G's direction at the 10:30 price, hedged one-for-one in notional with SPY. Exit both legs at the last 5-minute bar of the session. If idio ≤ 0, there is no trade.
4. Outcome h = sign(G) × [(stock_close / stock₁₀:₃₀ − 1) − (SPY_close / SPY₁₀:₃₀ − 1)].
5. Session usable: both the stock and SPY have a 09:30 first bar, a 10:25 bar, and a last bar at or after 15:30.

## Test

- **Validation sample:** every reaction session from 2013-01-01 to 2023-12-31 in the same 14 stocks.
- **V1 is CONFIRMED only if both hold:**
  - the share of V1 trades with h > 0 exceeds 50% (exact one-sided binomial test, p < 0.05);
  - the mean h after a 0.10% round-trip cost is above zero.
- Secondary checks, each at α = 0.05 but reported without the power to override the primary verdict:
  - **V2:** the same trades unhedged.
  - **V3:** after a V1 trade, fading from the close to the next open.
  - **V4:** the stronger subset, idio > 0.1 × typical.
- **2024-01 to 2026-09:** reported as a second out-of-sample check with identical code. This needs SPY bars for those months, which have not been downloaded yet.

Implementation: `scripts/post_earnings_v2.py`, committed with this file. `python scripts/post_earnings_v2.py --period discovery` reproduces the discovery table above.

## Decision rule

If V1 is confirmed, it becomes the validated intraday entry for the reaction session. Otherwise the post-announcement toolkit stays at D2 drift only.
