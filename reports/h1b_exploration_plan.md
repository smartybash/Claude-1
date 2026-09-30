# H1-B: late-day momentum on bigger days — exploration plan (fit on discovery only)

**Decision (user, 2026-09-30):** "I want to explore the bigger day filter and
refine what can be fitted." This overrides H1's registered closure
(`reports/econ2_preregistration.md` §4, "no other thresholds").

**H1-B is a new hypothesis, generated from H1's discovery descriptives.** In
2010–2020 the top |r| quintile made +$29 a trade and the bottom −$23. It is
handled as a hypothesis found in discovery data:

1. **Fitting uses discovery data only:** NQ and ES, trade days 2010-06-07 →
   2020-12-31. They are already read, so fitting on them costs nothing extra.
   The code refuses any date after 2020-12-31.
2. **The holdout (2021-01-01 → 2026-09-24) stays sealed** until one rule is
   frozen and committed. It is then read **once**. Its verdict is final: pass →
   paper-tracking and the prop simulator; fail → H1-B closed, and no second
   round.
3. The whole search grid and the selection rule are fixed here, before any
   fitting. Every configuration's result is reported, so the selection is
   visible.

Committed before the exploration runs.

## The grid (45 configurations)

- **Entry minute:** 15:30, 15:45, 15:50. The signal is measured at the close of
  the minute before entry; the exit is always the close of the 15:59 bar.
  Leveraged-ETF and dealer hedging flows are thought to concentrate close to
  the 16:00 cash close.
- **Size measure S**, with the direction taken from the sign of the same
  return:
  - (a) |r|, the prior RTH close → signal minute (H1's measure);
  - (b) |r| ÷ σ20, where σ20 is the standard deviation of the 20 previous daily
    close-to-close returns. Hedging and rebalancing flow scale with the move
    relative to normal;
  - (c) |r_open|, today's RTH open → signal minute. This leaves out the
    overnight gap, which the ETFs' rebalancing does include, so it serves as a
    contrast.
- **Threshold:** trade only when S is at or above its trailing percentile q ∈
  {50, 60, 70, 80, 90}. The percentile is computed on the prior 250 eligible days
  only, with at least 120 required, so it is causal. It adapts to volatility
  regimes, which a fixed percentage cannot.

Costs: the step-4 rule, NQ $14.50 per round trip ($29.50 ES); no loosening.

## Selection rule (fixed now)

- **Eligible:** at least 25 trades a year; NQ net total > 0 in **both** discovery
  halves (split at 2015-09-19); and ES discovery net total > 0 with the same
  configuration.
- **Choose:** the eligible configuration with the largest **smaller half**,
  meaning the minimum of the two halves' net $ per year on NQ. This rewards
  consistency over a single lucky period. Ties go to the higher threshold, then
  the later entry.
- **If none is eligible:** nothing is frozen, H1-B is closed, and the holdout
  stays sealed.

## Also reported (honesty checks, discovery only)

- The t-statistic of the original top-quintile result (whose quintiles used the
  whole sample), and a bootstrap 95% interval for its $/trade.
- The chosen configuration's discovery p against H1's null. This p is
  **inflated by the selection over 45 configurations**, so it is shown but
  cannot be used as evidence.
- The distribution of all 45 results: how many are positive after costs, and how
  many would clear p ≤ 0.05 by chance (expected about 2).

## The holdout test, fixed now for whichever rule is frozen

- **Null:** the H1 null. 5,000 lists; each random trade keeps one actual trade's
  direction and the same entry-minute → 15:59 window and cost, on a uniformly
  random eligible holdout day, whether or not that day is big. The filter and
  the direction are tested together against random late-day exposure.
- **Pass:** holdout total net > 0 **and** p ≤ 0.05. One test, with no
  multiplicity.
- **Descriptive:** a same-days sign-flip check (direction only), ES on the
  holdout, results by year, and MNQ.
- **Pass →** forward paper-tracking and the prop simulator. **Fail →** closed.

Scripts: `scripts/databento/h1b_explore.py` (now), then
`scripts/databento/h1b_holdout.py` (written and committed with the frozen rule,
before the holdout is read).
