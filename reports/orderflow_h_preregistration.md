# Order-flow hypotheses OF-1 to OF-4 on the Databento ticks — pre-registration (PROVISIONAL)

Registered **before any of these four trades is computed on any data.** The user
asked for at most five order-flow hypotheses on the discovery ticks, all labelled
provisional, and for a view on whether multi-year ticks are worth buying.

## 0. Honesty first: these are data-inspired

The 61 discovery sessions (2026-03-02 → 05-29) have already been read by the
step-4 tape reruns (T01–T17). Those reruns measured **correlations** on these
sessions, and every hypothesis below comes from them. That makes discovery a
**development set here, not evidence**. The only tests that count are:

1. the **D2 holdout** (23 sessions, 2026-08-21 → 09-24), read **once**, at the
   very end, together with RP-011 and every other tick hypothesis;
2. the **P2 top-up** of fresh sessions from 2026-09-25, if you approve it.

Everything reported before those reads is labelled **provisional**.

## 1. What the discovery reruns showed (the only inputs to this design)

| feature (15-minute horizon) | IC | t across 61 sessions | sessions with the sign |
|---|---|---|---|
| VWAP displacement (`vwap_disp`) | −0.255 | −15.1 | 100% |
| session cumulative delta (`cvd`) | −0.254 | −12.5 | 95% |
| sweep net share, ≥ 2 ticks (C1) | −0.064 | −5.2 | — |

All three are **mean-reverting**. No frozen trade built on them has paid after
costs (T10, T15). An IC is not an edge (T09): these trades test whether the
correlation survives a 2-point round trip.

## 2. The four hypotheses (a fifth is not proposed; nothing else has support)

Common rules: RTH only (09:30–16:00 ET); 1-minute evaluation grid; features from
`ic_harness.features` exactly as frozen; entry at the **close of the signal
minute** (last trade price), exit by clock; **one position at a time**, no entry
in the first 30 or last 20 minutes; cost **2.0 NQ points round trip** (stricter
than the NQ standard 0.725; MNQ 2.0 as well); thresholds from the **prior 10
sessions only** (no same-session or future statistics).

| id | signal | trade |
|---|---|---|
| **OF-1** VWAP reversion | `vwap_disp` beyond its prior-10-session 95th / 5th percentile | fade: short above, long below; hold 15 min |
| **OF-2** CVD reversion | `cvd_share` beyond its prior-10-session 95th / 5th percentile | fade; hold 15 min |
| **OF-3** sweep reversal | 5-minute sweep net share (C1) beyond its prior-10-session 95th / 5th percentile | fade the sweep side; hold 15 min |
| **OF-4** opening flow on gap days | gap ≥ 10 points; at **10:00** the first-30-minute net aggressor share agrees with a move toward the prior close | enter at 10:00 toward the prior close; stop 30 pt, target the prior close, flat 16:00 |

OF-4 is the **lookahead-free** version of T08: the flow is read over 09:30–10:00
and the trade starts at 10:00, never earlier.

## 3. Statistics and bars (fixed now)

- **Primary:** net points per trade after 2.0 points; the p is the one-sided
  t-test of **daily net P&L** (zero on days without a trade), Holm across the four.
- **Discovery (provisional) bar:** net > 0 and Holm p ≤ 0.05. Passing it earns a
  hypothesis a place in the holdout read, nothing more.
- **Holdout bar (the real one):** the same sign, net > 0 after 2.0 points, and
  one-sided daily-P&L p ≤ 0.05 on the 23 holdout sessions, for each hypothesis
  that passed discovery (Holm across those).
- **Power, stated before any result.** Twenty-three sessions resolve only large
  daily effects: if a hypothesis's discovery daily-P&L Sharpe is S (annualised),
  the holdout t is about S × √(23/252) ≈ 0.30 S. An annualised Sharpe below
  about 5.5 cannot reach t = 1.65 on the holdout. **A holdout null will
  therefore be weak evidence**, and it will be reported as that. The P2 top-up is
  what could make it strong.
- Also reported for each: trade count, win rate, Sharpe, max drawdown $/NQ and
  $/MNQ, by-week results, and the result without the best three sessions.

## 4. Are multi-year ticks worth buying?

Quotes taken today with `metadata.get_cost` (free; nothing bought):

| NQ trades, continuous front | quote |
|---|---|
| 3 months (Dec 2025 → Feb 2026) | $26.78 |
| 1 year (Mar 2025 → Feb 2026) | $115.93 |
| 5+ years (2021 → Feb 2026) | $616.76 |

The cap leaves **$40.46**. A year of ticks alone would break it. On the evidence
as well: every order-flow family re-tested on 61 sessions stayed closed, and the
only robust tick-level finding is a mean-reverting correlation that has not yet
cleared costs in any frozen trade. **Recommendation: do not buy multi-year
ticks.** If OF-1 to OF-4 pass discovery and hold on the holdout, the P2 top-up
(fresh sessions, within the cap) is the right next purchase, not history.
