# LDM: price-triggered late-day momentum (desk rules) — pre-registration

**Registered 2026-09-30, before any rule below has been computed on any data.**
User decision (2026-09-30): build the late-day momentum trade as a desk would.
Entry is triggered by price crossing a percentage-change level, in the
direction of the day's move. Stops and targets are distance-based. **Validation
is option 2:** fit on 2010–2020 only, freeze, and judge **only on forward paper
trading from 2026-10-01.** No spend.

## 0. Disclosure

- H1 (clock entry at 15:30) and H1-B (clock entry on big days) are closed
  (`reports/econ2_result.md`, `reports/h1b_result.md`). **I have seen that
  late-day momentum lost in 2021–2026, especially short trades.** So 2021–2026
  is **not used at all here**: not for fitting, not for checking, not even
  descriptively. The code refuses any date after 2020-12-31 in fit mode.
- 2010–2020 has been read by H1 and H1-B. This is a fit, not a test. The only
  test is the forward record.

## 1. The trade (NQ; the ES version is used only as a robustness constraint)

- **Reference:** the prior RTH session's close (back-adjusted continuous series;
  days need ≥ 300 RTH bars). Day change = price ÷ prior close − 1.
- **Entry trigger (price, not clock):** a resting **buy stop** at prior close ×
  (1 + X) and a **sell stop** at prior close × (1 − X).
  - An order fills on a **fresh cross**: the previous bar closed inside the
    level and this bar trades through it.
  - If the day is already beyond the level when the window opens, there is no
    trade until price comes back inside and crosses again.
  - Fill at the level, or at the bar's open if the bar opens beyond it.
  - The first trigger of the day is the only trade.
- **Afternoon window:** triggers count from W to 15:50 ET. This is a
  constraint, not the entry: the forced flows (dealer gamma hedging,
  leveraged-ETF rebalancing) build into the close.
- **Stop:** k × ADR20 from the fill, against the position. ADR20 is the mean RTH
  (high − low) ÷ close over the prior 20 sessions, times the fill price. It is
  expressed in points at the day's price level, so the rule means the same
  thing when NQ is at 2,000 as at 25,000.
- **Target:** 1R or 2R (R = the stop distance), or none, holding to the 15:59
  close.
- **Exit:** at the stop, the target, or the 15:59 close, whichever comes first.
  Within a bar the stop is checked before the target. A bar that opens through
  a level fills at its open. On the entry bar, only the stop is checked (a
  touch counts). Flat every night.
- **Costs:** NQ $2.25 + 1 tick per side ($14.50 per round trip); ES $29.50.

## 2. The fitting grid (72 configurations, on 2010-06-07 → 2020-12-31)

| parameter | values |
|---|---|
| X, day-change trigger | 0.50%, 0.75%, 1.00%, 1.50% |
| W, window start | 13:00, 14:30 |
| k, stop, × ADR20 | 0.15, 0.25, 0.40 |
| target | 1R, 2R, none (close) |

## 3. Selection rule (fixed now; applied mechanically)

**Eligible**, all four required:
- at least 25 trades a year;
- NQ net total > 0 in both discovery halves (split at 2015-09-19);
- NQ net total > 0 without its single best year;
- ES net total > 0 with the same configuration.

**Choose** the eligible configuration with the highest **plateau score**: the
median, over the configuration and its grid neighbours (one step away in one
parameter), of the weaker half's net $ per year. This picks a stable region
rather than a lone peak. Ties go to more trades per year.

**If none is eligible:** nothing is frozen, LDM is closed, and nothing is
tracked.

The chosen configuration is written to `reports/ldm_frozen.md` and committed
before any forward session exists. Forward tracking starts with signals on
2026-10-01.

## 4. The forward test (the only evidence)

- **Paper trading from 2026-10-01** on the monthly P8 bars (`ldm.py --forward`),
  logged in `reports/ldm_paper_ledger.csv` with no price levels.
- **First review on or after 2027-10-01.**
- **Null:** 5,000 exposure-matched lists. Each random trade keeps one actual
  trade's direction, entry minute, stop and target distances (as % of price)
  and cost. It is placed at that minute on a uniformly random forward session
  and exits by the same rules. p = (1 + number of random totals ≥ actual) ÷
  5,001.
- **Pass:** forward total net > 0 **and** p ≤ 0.05 → LDM becomes a live
  candidate: prop simulator sizing, then micro size first. **Negative forward
  total at the review → closed.** Positive but p > 0.05 → reported with its
  power, and tracking continues one more year. Nothing is re-fitted.
- **Descriptive at review:** a same-days random-direction check (does the
  direction call matter?), long versus short, per MNQ.

## 5. Descriptive now (discovery; seen; not evidence)

- The full 72-configuration grid.
- For the chosen configuration: halves, results by year, long versus short, exit
  reasons, average stop in points at the 2020 price level, and its discovery p
  (inflated by selection over 72).
- The prop simulator on its discovery trades, per 1–10 MNQ.

## 6. Engine checks before any real run

The trade engine is checked on synthetic bars before touching real data:
fresh-cross fill, gap-through fill, no trade when already beyond the level, stop
before target within a bar, a stop on the entry bar, a target exit, a close exit,
the short mirror, and no trigger after 15:50.

Script: `scripts/databento/ldm.py` (fit, `--selftest`, `--forward`), committed
with this file before any run.
