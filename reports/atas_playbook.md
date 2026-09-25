# ATAS Day-Trading Playbook — NQ / ES

**One dial. Two setups. Three indicators.** Everything here is either measured on
our own data or is a native ATAS feature. Nothing in this playbook is taken on
someone's word.

---

## The dial: Initial Balance width (read once, at 10:30 ET)

At 10:30 ET the first hour is done. Measure the **Initial Balance** (09:30–10:30
range) against the **14-day ATR**. That single number tells you what kind of day
you're in and which setup to run.

| IB width | day type | what to run |
|---|---|---|
| **> 0.5× ATR** (wide) | day spent its range early → **balance / rotation** | **Setup A — Value Area Fade.** Full size. |
| **< 0.5× ATR** (narrow) | compression → day wants to **expand** | Setup A at **half size**, POC target only. Or stand aside. |

ATAS draws IB for you: **Market Profile & TPO** → enable Initial Balance.

**Why this dial and not the popular one.** Narrow-IB days break the IB range 98%
of the time (we reproduced the published stat exactly). That sounds like a
breakout edge and it is not — we swept every stop/target combination and the IB
breakout never paid (best PF 1.31 on a 4:1 risk:reward geometry; most cells
negative). A 98% break rate is a *statistic*, not an edge, because the day has
5½ hours to exceed a 1-hour range. **So we use IB to classify the day, never to
trigger a trade.**

---

## Setup A — Value Area Fade *(the primary; our strongest tested intraday edge)*

**Idea:** price pushes up into the prior session's Value Area High, fails, and
rotates back to the POC.

**Levels — ATAS gives these free.** Add **Market Profile & TPO** (or Session
Volume Profile), period = Daily. You want the **previous day's** VAH / POC / VAL.
No spreadsheet, no Python export needed.

**Trigger**
1. After **10:00 ET**, price tags the prior **VAH**.
2. Wait for the **2nd distinct tag** (price must pull ≥0.15% off VAH in between).
   The 2nd rejection is roughly 3× better than the 1st — this is the edge.
3. The tagging candle **closes back below VAH**.

**Order-flow confirmation at the level — need 2 of 4** (this is what ATAS is for)
- **Stacked Imbalance** printing on the sell side at/just under the high
- **Delta / CVD** turns negative on the tag bar
- **Cluster Search** or **Big Trades** shows a large sell cluster at the level
- buyers **trapped at the bar extreme** (imbalance right at the high = level rejected)

**Stop** — above VAH (0.25% buffer), or above the imbalance stack, whichever is
tighter and still structurally valid.

**Target** — **POC**. Then let gamma decide:
- positive gamma (above flip) → price **pins at POC**, bank it, don't chase VAL
- negative gamma (below flip) → let it run **POC → VAL → breakout**

**Measured performance** (QQQ 5-min, 139 qualifying days, target POC):

| filter | n | win% | mean R | PF |
|---|---|---|---|---|
| all signals | 139 | 71% | +0.334R | 2.20 |
| ≥2nd VAH attempt | 33 | 73% | +0.679R | 3.49 |
| **wide IB (>0.5× ATR)** | 58 | 67% | **+0.482R** | **2.51** |
| narrow IB (<0.5× ATR) | 81 | 74% | +0.228R | 1.91 |
| **wide IB + ≥2nd attempt** | 17 | 82% | **+1.160R** | 7.58 |

The wide-IB × 2nd-attempt cell is the sweet spot, but **n=17 — treat that exact
number as indicative, not gospel.** The robust claim is the direction: the fade
pays roughly **twice as much on wide-IB (balance) days**, and that split is
significant on the larger all-signals sample (t=2.84 vs 2.58).

---

## Setup B — FVG Continuation *(for trend days, when A is off)*

**Idea:** on a day that's going somewhere, join the trend on a pullback into a
fair-value gap — *with* the trend, never against it.

**Trigger**
1. 3-candle **imbalance/FVG** forms in the direction of the move (5-min).
2. Price retraces to the gap's near edge.
3. Close is on the **correct side of VWAP** (above for longs, below for shorts).
4. **No entries 09:30–10:30** — the first hour is the worst window in our testing.

**Stop** — structure swing low/high of the last 5 bars. **Target** — trail, or
fixed 2–3R.

**Measured:** validated on 2y of 5-min data, **t = 6.44**. ATAS gives you VWAP
natively; the footprint confirms the gap is being defended.

---

## ATAS setup — three indicators, that's it

| Indicator | Setting | NQ start | ES start |
|---|---|---|---|
| **Market Profile & TPO** | period Daily; show prev-day VAH/POC/VAL + Initial Balance | — | — |
| **Stacked Imbalance** | imbalance ratio **300%**, stack **3** consecutive levels | min vol/cell ~15 | ~10 |
| **Cluster Search** ×2 | #1 sell clusters (bid ≥ X, red), #2 buy clusters (ask ≥ X, green) | X ≈ 150–300 | X ≈ 100–200 |

Optional but useful: **Delta/CVD** (session reset) and **Big Trades**. Chart:
5-min for the levels (that's what the numbers were measured on), plus a footprint
chart for the confirmation read.

**Calibrate the volume thresholds on day one.** Watch one session, note typical
vs outlier cluster sizes, set the threshold at the outlier level. The numbers
above are starting points, not truth.

### Two things that will cost you if you skip them
- **Read the full-size NQ/ES footprint, trade the micro (MNQ/MES).** Micros print
  thin, misleading clusters on their own.
- **You need a real order-flow feed** — Rithmic, CQG or dxFeed. On delayed or
  eval data the imbalances are meaningless and Setup A degrades to a naked level
  trade.

---

## Risk

Fixed **dollar** risk per trade (0.5–1%); size the contracts off the stop
distance so a 40-point stop and a 15-point stop cost the same. One to two trades
a day. Skip the first hour. If the IB dial says narrow and nothing sets up
cleanly, not trading is a position.

---

## What we deliberately left out (all tested, all failed)

| idea | result |
|---|---|
| IB / opening-range breakout | no stop-target combo pays; 98% break rate is not an edge |
| ORB + 1-min imbalance filter | filter made it *worse* (PF 0.87 vs 1.01 plain) |
| VWAP-retest scalp (Rother) | −0.34R best case; 56% win ceiling, breakeven |
| ICT sweep + reclaim (Tempa) | −0.19R in its own 9:30–11:00 window, 63% stop-out |
| New Week Opening Gap draw | fill rate is a survivorship illusion; fade loses −0.34R |
| MAGS/SMH/IGV breadth veto | backwards — blocked trades won *more* |
| "A+" confluence scoring | held no better than random levels |

The point of the list: the two setups above are what survived.
