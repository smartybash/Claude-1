# LDM: price-triggered late-day momentum — result

Registered `reports/ldm_preregistration.md` (e54ee8d) before the fit. Fit run once
on 2026-09-30 on NQ and ES 2010-06-07 → 2020-12-31 only. Outputs:
`reports/ldm_fit_output.txt`, `reports/ldm_grid.csv`.

**Verdict: no configuration met the pre-set robustness bar → nothing frozen, LDM
closed, nothing paper-tracked.**

## The desk rules that were fitted

- Resting stop entry on a fresh cross of prior close ± X% (0.5, 0.75, 1.0, 1.5%),
  in the direction of the break.
- Afternoon window from 13:00 or 14:30 to 15:50.
- Stop 0.15, 0.25 or 0.40 × ADR20, in points at the day's price (about 7 NQ
  points in 2010, 53 in 2020).
- Target 1R, 2R or hold to the close. Stop checked before target; flat every
  night; $14.50 per round trip.

## What the fit showed

- 28 of 72 configurations are net positive over 2010–2020. **None is positive
  in both halves on NQ and positive on ES** (the pre-set bar also required
  ≥ 25 trades a year and a positive total without the best year).
- **The first half (2010-06 → 2015-09) is negative in 70 of 72 configurations.**
  The two exceptions (1.5%, from 14:30, stop 0.25/0.40, hold to close: +$177
  and +$270 a year) lose on ES.
- Example, X 1.0%, from 13:00, stop 0.25 ADR, hold to close: +2.20 points a trade
  gross overall, **0.00 in 2010–2015** and +4.30 in 2015–2020.
- The best-looking cells (1.5%, 13:00, hold to close: +$90 to +$98 a trade) are
  positive only because of the second half, the same 2015–2020 concentration
  that made H1-B look good and then fail.
- **Engine check on real data:** 200 sampled trades, 0 rule violations (fill at
  the level or a gap open, fresh cross inside the window, exits in order).

## Reading

With desk-style entries, stops and targets, late-day momentum on NQ has no
consistent edge over 2010–2020. It shows up in some years and not others. The
pre-set bar was built to catch exactly that before any money or forward time
went into it.
