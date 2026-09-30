# Risk-managed rerun of the stop-less rules — pre-registration

**Registered 2026-09-30, before any rule below has been run with a stop.** User
instruction: "Sort your shit on the previous results." Every rule I tested
without a stop is rerun with the same desk risk block: a hard stop at entry,
position size from dollar risk, and a daily loss cap. The prop simulator judges
the survival odds. The entry and exit timing of each rule is unchanged; only
risk management is added. **One setting for the whole block, fixed here, no
grid:** there is nothing to tune.

## 1. Rules covered (Phase 1: the stop-less rules I designed)

| rule | entry → planned exit | market | window |
|---|---|---|---|
| D3-G/A | D3 signal → next Globex session: 18:00 reopen → RTH close | NQ | 2010-06 → 2026-09 |
| D3-G/B | same entry → next RTH open (09:30) | NQ | same |
| ES-G/A | as D3-G/A | ES | same |
| D3P | D3 signal → next RTH open → RTH close | NQ | same |
| H1 | every day: 15:30 open → 15:59 close, direction of prior close → 15:29 | NQ | same |
| H1-B | frozen rule: 15:45 open → 15:59 close on top-10% \|r\| days | NQ | same |
| H2 | turn-of-month sessions: 18:00 reopen → RTH close | NQ | same |

Not covered:
- **D3 and ES-D3** hold through the 16:00–18:00 close. Apex and Lucid forbid that
  with or without a stop, so they cannot be traded there at all.
- **RP-011** is a mechanism event study, not a trading rule.
- **LDM** already had stops.

**Phase 2** (after this) covers the 13 earlier order-flow and tape studies that
were judged on fixed exit times (`reports/step4/results.csv`: T01–T06, T10, T13,
T14, T15, B15, B17, B19).

## 2. The risk block (fixed)

1. **Hard stop at entry:** stop distance = **0.5 × ADR20 × √(H ÷ 390)**.
   - ADR20 = the mean RTH (high − low) ÷ close over the 20 RTH days before the
     trade, times the entry price (in points).
   - H = the planned hold in minutes (capped at 1,440).
   - The stop is half the range normally covered over the holding time; range
     grows with the square root of time. One constant (0.5) for every rule.
   - **Measured before the run, from price ranges only (no P&L):**

     | hold | NQ 2012 | NQ 2020 | NQ 2026 | ES 2026 |
     |---|---|---|---|---|
     | 15 min | 3.2 | 19.9 | 38.0 | 6.9 |
     | 29 min | 4.5 | 28.2 | 53.8 | 9.8 |
     | RTH day | 16.2 | 101.6 | 193.9 | 35.2 |
     | 18:00 → close | 29.8 | 187.0 | 356.8 | 64.8 |

     (Median stop, in points.)
   - **Consequence, stated now:** at the $250 risk limit, a stop wider than 125
     NQ points (50 ES points) cannot be traded even at 1 micro, so the trade is
     skipped. That skips 43% of all NQ 18:00 → close sessions and **100% of them
     in 2024–26**, 19% of NQ RTH-day trades (65% in 2024–26), and 56% of ES
     18:00 → close sessions in 2024–26. The late-day rules (15–29 minutes) are
     never skipped. This is part of the result: an overnight NQ hold is too big
     for a 50K account at today's prices once it carries a proper stop.
   - The stop fills at its level, or at a bar's open if the bar opens through it.
     The entry is at a bar's open, so the whole entry bar comes after the fill
     and is checked.
2. **Position size from risk:** $250 risk per trade (10% of Apex's $2,500
   drawdown; 12.5% of Lucid's $2,000).
   - Contracts = floor($250 ÷ (stop points × $ per point per micro)), in MNQ ($2
     a point) or MES ($5), capped at 10 micros. That is 1 NQ-equivalent, so no
     day can cost more than the cap even on a gap.
   - A trade whose stop needs more than $250 at 1 micro is **skipped**; the risk
     rule forbids it.
3. **Daily loss cap:** $500. Each rule trades at most once a day, so it only
   binds on a gap past the stop, but it is enforced and becomes binding when
   rules are combined.
4. **Costs:** step-4 micro costs, MNQ $2.24 and MES $3.74 per round trip per
   micro.
5. **Rolls** inside a Globex session: rolled at the roll prices (old close, new
   open), with one extra round trip. Stale rolls are dropped (one NQ roll in
   2013).

## 3. Test

- **Null (per rule):** 5,000 exposure-matched lists under the **same risk
  block**, on uniformly random eligible sessions of the window. Each random trade
  keeps one actual trade's direction and the rule's entry and exit times, with
  the same stop formula, sizing and costs.
- **Statistic:** total net $, as sized. p = (1 + number of random totals ≥
  actual) ÷ 5,001. Seed 20260930.
- **Holm across the 7 rules. Risk-managed pass:** total net > 0 **and** Holm p ≤
  0.05.
- **Everything here is seen data**, so no pass is proof.
  - **Pass →** the risk-managed version replaces the stop-less one in forward
    paper-tracking.
  - **Fail →** the rule is closed for prop use. A stop-less D3-G stays tracked
    only as a record, flagged as not tradable at prop size.
- **Prop simulator** for every rule, risk-sized: P(pass within 30/90/365 days),
  P(fail within 365 days), median days, across Apex intraday, Apex EOD and Lucid
  Flex. The simulator gains per-trade sizing; its selftest must still pass.
- **Descriptive:** trades taken and skipped, stop-outs, average contracts, the
  largest loss, per-year totals, and results before and after 2018.

Script: `scripts/databento/risk_rerun.py` (with `--selftest` for the stop engine
on synthetic bars), committed with this file before any real run.
