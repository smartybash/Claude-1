# Power of 3 (ICT accumulation → manipulation → distribution) — pre-registration

Registered **before any Power of 3 rule touches any bar**. Approved by the user
(decision P1): the most canonical variant is the **single primary**, the other
two are secondary and Holm-adjusted; run **once** on 2010–2026, labelled
**seen data**; the kill criteria plus the random-direction baseline; **pass =
forward paper-tracking only; fail = close.**

## Data role

NQ 1-minute bars (Databento pull A), 2010-06-07 → 2026-09-24. **Seen data:**
every NQ intraday day in this range has been read by studies (a)–(e) and step 4.
Nothing here is out-of-sample and nothing is promoted on it. A pass only starts
forward paper-tracking from the registration date.

## Variants (as drafted in P1; nothing changed)

| | **V2 · midnight open (PRIMARY)** | V1 · NY-open Judas (secondary) | V3 · Asian-range sweep (secondary) |
|---|---|---|---|
| reference | 00:00 ET open (ICT "true day open") | 09:30 ET open | Asian range: high / low of 18:00–00:00 ET |
| manipulation window | 09:30–11:00 ET | 09:30–10:30 ET | 02:00–05:00 ET |
| manipulation | trades beyond the reference by ≥ 0.10 × ATR14 | same | trades beyond the Asian high / low by ≥ 0.10 × ATR14 |
| reclaim | first 1-min close back through the reference, inside the window | same | first 1-min close back inside the Asian range, inside the window |
| entry | next bar's open, opposite the manipulation | same | same |
| stop | manipulation extreme ± 1 tick | same | same |
| exit | target = prior-day RTH high (long) / low (short); skipped if < 1R away; else flat 15:59 | 2R, else flat 15:59 | flat 15:59 |

**Why V2 is the canonical one.** ICT's Power of 3 is read against the "true
day open" at midnight New York; the Judas swing runs against it in the morning
session and the distribution targets the opposing liquidity (the prior day's
extreme). V1 uses a session open that ICT treats as secondary; V3 is the London
variant.

## Mechanics, fixed now

- **ATR14** = mean of the prior 14 RTH daily true ranges (full sessions only),
  known before the session (study (e)'s `atr14`).
- **Manipulation side** = the first side on which the threshold is reached inside
  the window. The reclaim may happen on the same bar; the manipulation extreme is
  the extreme from the window start up to and including the reclaim bar. If one bar
  crosses the threshold on **both** sides before any manipulation is set, the order
  is unknowable and the day is skipped.
- **One trade per variant per day.** Excluded: half days, sessions whose bars from
  the reference time to 15:59 span two contracts, V2 sessions whose prior RTH
  session is a different contract (the target would not be a price of this
  contract), and sessions missing the reference bar (V2: a bar at 00:00–00:04 ET).
- **Honest fills:** entry at the next bar's open; a stop gapped through fills at
  the bar's open; stop checked before target within a bar (study (c)/(d)'s
  `exit_path`).
- **Costs:** NQ $2.25 + 1 tick per side ($14.50 round trip); MNQ $0.62 + 1 tick.

## Tests and kill criteria (fixed now)

- **Random-direction baseline:** each trade is replaced by its **mirror** (same
  entry time, stop and target reflected through the entry price, same exit rule)
  with probability ½; 5,000 simulations; p = share of simulated Sharpe ≥ actual.
- **Holm** across the three variants; the primary is judged at its Holm p.
- **Kill (all must hold to pass):** Sharpe ≥ 0.8; profit factor ≥ 1.3; beats the
  random-direction null at Holm p ≤ 0.05; Sharpe above the **ORB baseline**
  (−0.37, the best full-sample Sharpe of the 16 frozen ORB + VWAP variants on NQ,
  step 4 B07).
- **Pass (primary)** → forward paper-tracking only, from the registration date.
  **Fail** → Power of 3 is closed. Secondary variants are reported, Holm-adjusted,
  and cannot rescue a failed primary.
- Reported: trades, win rate, Sharpe, CAGR, profit factor, max drawdown $/NQ and
  $/MNQ, per year.
