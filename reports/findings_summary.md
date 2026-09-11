# Findings — what was tested, what failed, what is left

Written 2026-09-11. This is the record of record: if the session is gone, this
file is what survives.

---

## Bottom line

**There is no validated setup in this repository.** Nine strategies have been
mechanised and tested. All nine were rejected. Nothing here should be traded
with real size on the strength of a backtest.

The last one to fall — the value-area fade — appeared to work for most of a
week. It did not. Its apparent edge was a **lookahead bug** in the entry price,
and that bug was also in the original `backtest_va_fade.py` result that
everything else was built on.

---

## The lookahead, in one paragraph

The rule takes the trade when a 5-minute bar **closes back through** a level.
Every version of the test then filled the entry **at the level** — a price from
earlier in that same bar. Both facts cannot be known at once: when price touches
the level, the bar has not closed and the rejection has not happened. The
backtest was buying at a price that the rule's own information had not yet
identified as a buy.

Removing it (`backtest_aplus4.py`) collapses the result:

| stop 0.15% (44 NQ pts) | n | win | mean R | PF | t |
|---|---|---|---|---|---|
| entry at LEVEL (lookahead) | 400 | 50% | **+0.628R** | 2.26 | **+4.68** |
| entry at CLOSE (realistic) | 395 | 45% | −0.047R | 0.91 | −0.66 |
| resting LIMIT, every touch | 500 | 20% | −0.513R | 0.36 | −10.30 |
| CLOSE + bar delta ≥10% | 337 | 48% | −0.049R | 0.90 | −0.73 |

**Any result in this repo that enters at a level price on a bar-close condition
is suspect and must be re-derived before it is believed.**

---

## The nine rejected

| Strategy | Script | Result |
|---|---|---|
| ICT prior-day sweep + reclaim | `backtest_ict_sweep.py` | −0.19R, t=−2.78, 63% stop-out |
| NWOG weekend gap fade (1,351 gaps, 27y) | `backtest_nwog.py` | −0.34R, t=−13.2 |
| 15-min ORB + FVG | `backtest_orb15.py` | PF 1.01; the imbalance filter made it worse (0.87) |
| Initial Balance breakout (full sweep) | `backtest_initial_balance.py` | 98% break rate, no configuration pays |
| VWAP retest | `backtest_vwap_retest.py` | +0.049R — noise |
| MAGS/SMH/IGV breadth veto | `backtest_breadth_filter.py` | backwards: blocked signals won 72%, kept won 62% |
| Value-area fade | `backtest_va_fade.py` | +0.334R / t=+3.80 — **invalidated by the lookahead** |
| VA fade + wide Initial Balance | `backtest_ib_regime_filter.py` | +0.482R / PF 2.51 — **same lookahead** |
| Fixed-level fade, all variants | `backtest_aplus*.py` | flat to negative under every honest entry |

The last row covers: prior-day VAH/VAL/High/Low, 20-session composite
VAH/POC/VAL, naked POCs; both sides; stop widths from 44 to 206 NQ points; time
window; wide-IB filter; session-CVD filter; trigger-bar delta filter; and three
entry conventions. 523 sessions. Nothing survived.

The final entry attempt — wait for the rejection bar to close, then rest a limit
back at the level for K bars — is in `backtest_aplus5.py`. Best of sixteen cells
searched was +0.196R at t=+1.68, which is not significant before accounting for
having searched sixteen cells. Its out-of-sample half is **−0.235R, t=−2.02**.

---

## Two findings that did survive

Both are negative results, and both are worth more than another failed setup.

**1. Fading fixed levels blindly loses money, reliably.**
A resting limit at prior-day VAH/VAL/High/Low, filled on every touch:
**−0.513R at t=−10.30 over 500 trades.** This is the most statistically solid
number in the whole repo. Those levels are not support and resistance in the
way they are usually taught.

**2. The rejection bar carries real information — it just cannot be monetised
on 5-minute bars.**
Going from "every touch" (−0.513R) to "only touches where the bar closes back
through" (−0.047R) recovers **0.47R per trade**. The poke-and-close-back pattern
genuinely separates the touches that hold from the ones that do not. By the time
the bar closes and you can act, the price is gone.

That is a precise diagnosis: **the read is right, the execution window is the
problem.** It is also the one gap that tick-level order flow could plausibly
close — at the tick you may see absorption *while* it happens instead of after
the fact. That claim cannot be tested on 5-minute bars.

---

## Data limitations that bound all of the above

- **QQQ, not NQ.** 523 sessions of QQQ 5-min RTH (2024-07 to 2026-07) is the
  only intraday history deep enough to test on; NQ has 11 days. Same index,
  but tick size, spread and slippage differ.
- **No aggressor tag.** QQQ bars carry no bid/ask split, so per-bar delta is a
  proxy — `((close-open)/(high-low)) * volume`. Every flow-filtered number
  inherits that approximation. Real CVD and real footprint imbalance have not
  been tested at all.
- **RTH only.** No overnight/Globex high and low, which are part of the fixed
  level set in live use.
- **No commissions or slippage** are modelled. At the R:R levels involved this
  is small, but it is not zero.

---

## What is left

**ATAS Market Replay, Ticks + DOM mode, 20–30 sessions, one setup, executions
logged to the Trading Journal.**

This is not a consolation prize. It is the only way to test the one claim that
the bar data cannot reach: whether tick-level order flow gives an entry that
5-minute bars cannot. Everything else has been falsified.

Rules for it to be worth anything:
1. One setup at a time. No switching mid-sample.
2. Log every trade, including the ones you skipped and why.
3. Ticks + DOM mode — generated-tick modes do not reproduce absorption.
4. 20–30 sessions before drawing any conclusion.
5. If you cannot execute the trigger cleanly under live speed, it is not an
   edge you own, regardless of what the sample says.
