# Desk Playbook — NQ / ES on ATAS

Written from mechanism, not from curve-fitting. The organising question is not
"what pattern works" but **"who is forced to act, and where."**

---

## 1. Where a desk's odds actually come from

A desk does not predict. It positions where the **invalidation is small and
specific** and the **payoff has a mechanism behind it** — someone trapped who
must cover, or an auction that is unfinished and must travel.

Three questions, in this order. All three must agree or there is no trade.

| # | Question | Answered by |
|---|---|---|
| **1. LOCATION** | Is price at a reference where risk was transferred? | your pre-market map |
| **2. CONTEXT** | Is the market accepting or rejecting price here? | auction / open type |
| **3. FLOW** | Is aggression being absorbed, or meeting nothing? | ATAS footprint |

Retail has 1 and sometimes 2. **ATAS is the only part of your stack that answers
3** — that is the entire reason to pay for it. Question 3 is what converts "a
level" into "a level someone is defending with size."

**The asymmetry rule.** Only take trades where you can name the price that proves
you wrong, and that price is close. If you cannot state the invalidation in one
sentence, you do not have a trade — you have an opinion.

---

## 2. The map — drawn before 09:30, never during

These are the prices where risk changed hands. Mark them and do not add more.

**From ATAS Market Profile & TPO / Session Volume Profile:**
- Prior day **VAH / POC / VAL**
- Prior day **High / Low**
- **Naked POCs** — POCs from earlier sessions never revisited. Unfinished
  business; price is drawn to them.
- **HVN** (high-volume node) — thick shelf = acceptance = price *sticks*
- **LVN** (low-volume node) — thin gap = rejection = price *travels fast*

**From the overnight session:**
- **Globex High / Low** (the most-run stops of the morning)

**Added at 10:30:**
- **Initial Balance High / Low** (Market Profile & TPO draws it natively)

**Always on:** session **VWAP** — real because execution algos are benchmarked to
it, so size genuinely defends it.

> **The HVN/LVN distinction is the most underused edge on this list.** LVNs are
> not support — they are vacuum. Never set a target *short of* an LVN and never
> expect one to hold. HVNs are where rotations die: that is where you take profit.

---

## 3. Context — decided in the first 30 minutes

Where price opens relative to **prior day's value area** sets the day's script.

| Open location | What it means | What you may trade |
|---|---|---|
| **Inside** prior value, stays inside | balance / rotation | Setups **1 & 2** (fade the edges) |
| **Outside** value, holds outside (accepted) | initiative / trend | Setup **3 only — never fade** |
| **Outside** value, then trades **back inside** | failed auction | Setup **1**, and target the *far side* of value |

That third row is the single highest-quality day-type in auction trading. Price
tried to leave, was rejected, and re-entered the range — the rotation across the
whole value area is the trade.

---

## 4. The three setups

Each is a **mechanism**, not a pattern. If you cannot name who is trapped or what
is unfinished, skip it.

---

### SETUP 1 — FAILED AUCTION / TRAP  *(primary; reversal)*

**Mechanism:** traders entered on a breakout that failed. They are offside and
must cover. Their stops are your fuel.

**Where:** any map level — Globex H/L, prior day H/L, IB H/L, VAH/VAL.

**Sequence to watch:**
1. Price **extends beyond** the level.
2. Aggression follows it out — **delta pushes in the break direction**.
3. **No acceptance**: price fails to build volume out there; the push stalls.
4. Price **closes back inside** the level.

**ATAS confirmation (need 2):**
- **Cluster Search** — outsized cluster at the extreme (someone big took the other side)
- **Delta / CVD divergence** — CVD makes a new extreme, price does not
- **Stacked Imbalance** now printing in the **reverse** direction
- **Speed of Tape** spikes on the break, then dies

**TRIGGER:** the 1- or 5-min candle that **closes back inside the level**.

**ENTRY:** limit at/just inside the reclaimed level on the retest.
**STOP:** beyond the failed extreme + 2–3 ticks. *This is the real invalidation —
if price trades back out, the auction was not failed.*
**T1:** opposite side of the immediate range, or POC.
**T2:** far side of value / next naked POC / next liquidity pool.

**Why the odds tilt:** you are positioned against a group with a known, clustered
stop location, and your own risk is defined by the same extreme that defines
theirs. Small, specific invalidation; mechanical payoff.

---

### SETUP 2 — ABSORPTION AT A LEVEL  *(reversal, no breakout required)*

**Mechanism:** aggressive orders are hitting a wall of passive size. The passive
side is usually the informed one. When aggression exhausts, price reverts.

**Where:** HVN, POC, VAH/VAL, or a level flagged by the **Absorption** indicator.

**Sequence to watch:**
1. Price grinds **into** the level with clear aggression (delta strongly one way).
2. Each push makes **no new ground** — highs stop extending.
3. The **cluster at that price swells** while price stays flat = passive fills.
4. Imbalances **fail to stack** in the push direction.

**ATAS confirmation (need 2):**
- **Big Trades** / **Smart Tape** — large prints on the passive side
  (Smart Tape re-aggregates split orders, so you see true size, not fragments)
- **Cluster Search** — the swelling cluster at one price
- **Delta divergence** — delta positive, price flat or lower
- **Absorption** indicator marking the level

**TRIGGER:** first candle that **closes against** the aggression direction.

**ENTRY:** on that close.
**STOP:** beyond the absorption cluster's extreme (this is tight — that is the point).
**T1:** POC / opposite value-area edge.
**T2:** through the next **LVN** — once price enters a vacuum it travels.

**Why the odds tilt:** you side with size that is willing to be patient, against
size that just paid the spread and got nowhere.

---

### SETUP 3 — INITIATIVE CONTINUATION  *(trend days; the only setup on an accepted breakout)*

**Mechanism:** the auction is unfinished. Price crossed an LVN with no defence
and must find acceptance further out.

**Where:** after price **breaks and holds** outside a reference level; entry on
the pullback into the last stacked-imbalance zone or the LVN it just crossed.

**Sequence to watch:**
1. Initiative drive with **stacked imbalances** in one direction.
2. **Thin clusters** through the move — nobody defending.
3. **Shallow pullback** that holds the zone; delta dries up (no opposing aggression).
4. Trend-direction **imbalance reappears**.

**ATAS confirmation (need 2):** stacked imbalances on the drive · thin volume
through the travelled area · **Speed of Tape** slowing on the pullback then
re-accelerating · no opposing Big Trades at the pullback low/high.

**TRIGGER:** trend-direction imbalance reappears while the zone holds.

**ENTRY:** at the zone (limit).
**STOP:** through the zone — if it fails, initiative is over, get out.
**T1:** next **HVN** (rotations die at shelves).
**T2:** measured move / next naked POC. Trail behind each new HVN.

**Why the odds tilt:** you are not chasing the break; you are buying the retest of
a vacuum that the market has already shown it will not defend.

---

## 5. The pre-click checklist

Say all five out loud. Any "no" = no trade.

1. Price is **at a level from my map** — not mid-range. ☐
2. **Context** supports the direction (day type from §3). ☐
3. **Flow confirms** — 2 of the setup's ATAS signals. ☐
4. I can state my **invalidation price in one sentence**. ☐
5. Target is a **real liquidity pool** (HVN / POC / opposite edge), not an R multiple. ☐

The checklist *is* the edge. A desk's advantage is not a better signal — it is
refusing to act when the conditions are only partly there.

---

## 6. Exits — decided before entry

- **Scale at T1.** Take half at the first liquidity pool, stop to breakeven, let
  the rest run to T2. Reversals pay quickly or not at all.
- **Hard invalidation** = the structural price, never an arbitrary R.
- **Time stop.** A trap or absorption trade should work within **15–20 minutes**.
  If the mechanism (trapped traders covering) hasn't shown, it isn't there —
  flatten flat. This single rule removes most slow bleeds.
- **Never move a stop away from price.** Ever.

---

## 7. Session discipline

| Window (ET) | What it is | Do |
|---|---|---|
| 09:30–10:00 | open drive, widest spreads | Setup 1 only, at Globex/prior-day levels |
| **10:00–11:30** | **prime window** — IB completes, traps resolve | all three setups |
| 11:30–14:00 | lunch, thin | stand down unless A+ at a major level |
| 14:00–15:30 | trend resumption | Setup 3, or Setup 1 at the day's extreme |
| 15:30–16:00 | MOC imbalances | flat unless you know the imbalance |

**Risk:** fixed **dollar** risk per trade (0.5–1%); size contracts off stop
distance so a 40-pt stop and a 12-pt stop cost the same. **Max 2–3 trades/day.
Two losses = done.** Flat over FOMC/CPI releases; the tape lies through them.

**Instrument:** read the **full-size NQ/ES footprint**, execute in **MNQ/MES**.
Micros print thin, misleading clusters on their own.

---

## 8. Prove it before you size up

These setups are built from auction and order-flow mechanics, **not from a
backtest of mine** — so validate them yourself before risking size:

**ATAS Market Replay** reconstructs real sessions tick-by-tick with a dedicated
replay account, and logs the trades to the Trading Journal (profit factor,
drawdown). Use **Ticks + DOM** mode for maximum accuracy — generated-tick modes
will not show you true absorption. Replay 20–30 sessions, one setup at a time,
and keep only the ones where *you* can execute the trigger cleanly in real time.

**A setup you cannot execute under speed is not an edge you own.**

---

### Feed requirement

Footprint imbalance and absorption need **aggressor-tagged tick data** — Rithmic,
CQG or dxFeed. On delayed or eval data these signals are noise, and all three
setups collapse into naked level-trading.
