# ATAS Order-Flow Layer — Imbalance Confirmation on Our Levels

**What this adds.** Our system gives you *where* to act (VAH / POC / VAL, dealer
call wall / put wall, gamma flip) and *what regime* you're in (above flip =
range/fade, below flip = trend/go-with). It does **not** tell you *when* the level
is actually holding or breaking in real time. That's the gap ATAS fills: the
footprint (cluster) chart shows the bid×ask trade at every price, and **stacked
imbalances** show where aggressive orders are stacking — the timing/confirmation
trigger to act at one of our levels instead of guessing.

Rule of thumb: **our level is the WHERE, the imbalance is the WHEN. No level, no
trade — an imbalance in the middle of nowhere is noise.**

---

## 0. Before this works at all (honest prerequisites)

- **You need a real order-flow feed.** Footprint/imbalance needs bid/ask
  aggressor data: **Rithmic, CQG, or dxFeed** for CME futures (MNQ/MES). ATAS on
  a delayed or top-of-book feed will *not* give you real imbalances. Budget for
  ATAS sub + a data feed (~$50–100/mo range all-in; check current pricing).
- **OI Analyzer is useless here.** That indicator only works on **Moscow
  Exchange** futures (real-time OI). It does nothing for MNQ/MES — ignore every
  mention of it in the ATAS article.
- **Read the FULL-SIZE contract's footprint, trade the micro.** NQ/ES full-size
  have far richer order flow than MNQ/MES. Load the **NQ**/**ES** footprint for
  the read, place the order in **MNQ**/**MES**. Micros can print thin, misleading
  clusters on their own.
- **Every threshold below is a STARTING POINT.** Cluster/imbalance volume numbers
  depend on your feed and the session's activity. Watch one session, note typical
  vs. outlier cluster sizes, then set thresholds at the "outlier" level.

---

## 1. The setups (regime-gated, level-anchored, imbalance-confirmed)

Each setup = **regime gate → our level → ATAS confirmation → entry/stop/target.**
Always skip the first hour (09:30–10:30 ET) — worst window in our backtests.

### A) FADE-SHORT at VAH / call wall  *(positive gamma / above flip)*
- **Gate:** price ABOVE gamma flip (range/fade regime). This is our tested edge
  (2nd VAH rejection → POC +0.68R, 73% win).
- **Level:** price rallies UP into prior **VAH** (≈ call wall on a pos-gamma day),
  **2nd tag**, after 10:00 ET.
- **ATAS confirmation at the level (need ≥2):**
  - stacked **SELL** imbalance at/just under the highs (asks getting absorbed,
    bids stacking on the sell side),
  - **delta turns negative** on the tag bar,
  - big **sell cluster** (Cluster Search) at the level,
  - **buyers trapped at the bar extremum** (longs stuck at the high) — the classic
    "imbalance at the extreme = level rejected" tell,
  - on a reversal/range chart: long **upper shadow**.
- **Entry:** limit sell at VAH once the stacked sell-imbalance prints and delta is
  red. (If price never tags your limit → not your trade.)
- **Stop:** above VAH — our 0.25% buffer, or just above the imbalance-stack high,
  whichever is tighter and still structurally valid.
- **Targets:** **POC (T1)** → **VAL (T2)**. Pos gamma **pins at POC** — bank POC,
  don't chase VAL unless it breaks (then it's a neg-gamma run).

### B) FADE-LONG at VAL / put wall  *(positive gamma / above flip)*
- Mirror of A. Price drops into **VAL / put wall**, pos gamma.
- **Confirmation:** stacked **BUY** imbalance at the lows, **delta turns green**,
  big **buy cluster**, **shorts trapped at the bar low**.
- **Entry:** limit buy at VAL/put wall. **Stop** below. **Target** POC.

### C) REVERSAL / EXHAUSTION at a day extreme or wall
- **Tell:** **multiple imbalances printing AT the bar extremum** during a trend =
  the move is exhausting (per the article's core rule). Also: delta shrinking
  while price makes new extremes (delta divergence), pullbacks off the extreme
  getting bigger.
- **Entry (conservative):** wait for the **reversal bar to close**, a stacked
  imbalance in the NEW direction, and **delta the same colour as the new
  imbalance** — then enter with a limit at the imbalance level.
- **Stop:** beyond the exhaustion extreme. **Target:** prior POC / opposite VA edge.

### D) BREAKOUT / GO-WITH  *(negative gamma / below flip — e.g. 2026-08-18)*
- **Gate:** price BELOW gamma flip = trend/expansion. **Do NOT fade.** Value area
  is now overhead resistance, the put wall is the downside magnet.
- **Level:** breakdown through VAL / prior consolidation, or a pullback that fails
  back into VAL from below.
- **Confirmation:** stacked **imbalance in the trend direction** on the pullback
  (sell-side stacks on a bounce into VAL), delta agrees, no opposing stacked
  imbalance defending the level.
- **Entry:** with the trend on the pullback. **Stop:** back inside the broken
  level. **Target:** next level down (put wall), trail with structure.

**Universal filters (from the article, they hold up):**
- Trade **with the most recent stacked imbalance**, not against it.
- **Multiple imbalances at extremes = rejection** of that price.
- In consolidation: sell the range high / buy the range low with limits; a
  stacked imbalance + delta flip on a range-edge break flips you to go-with.
- **If price didn't reach your limit, it wasn't your trade.** No chasing.

---

## 2. ATAS indicator settings sheet (starting points — calibrate to your feed)

Load a **Footprint (cluster) chart** plus these. Numbers are for CME micros/minis;
tune to observed volume in your first session.

| Indicator | Setting | MNQ / NQ start | MES / ES start | Notes |
|---|---|---|---|---|
| **Footprint imbalance** | Imbalance ratio | **300%** (3:1) | **300%** | 400% = stricter, fewer/higher-quality |
| | Diagonal compare | Bid vs Ask, adjacent price | same | standard footprint imbalance |
| | Min volume per cell | ~15–30 | ~10–20 | ignore tiny cells; raise if too noisy |
| **Stacked Imbalance** | Stack size (consecutive) | **3** | **3** | 4–5 = stronger S/R zones |
| | Imbalance ratio | 300% | 300% | keep same as footprint |
| | Volume filter | ~15 | ~10 | min per imbalanced cell |
| **Cluster Search ×2** | #1 SELL: bid ≥ | ~150–300 | ~100–200 | mark red — sell clusters |
| | #2 BUY: ask ≥ | ~150–300 | ~100–200 | mark green — buy clusters |
| | Search by | Bid / Ask (or Volume) | same | calibrate to session's big prints |
| **Delta** | per-bar delta colour | on | on | red/green aggressor dominance |
| **Daily HighLow** | on | on | on | real-time day H/L for extremes |

- **Chart type:** run a **Reversal (1/7)** or a **range/tick** chart to filter
  noise (as the article shows) **plus** a standard 5-min time chart — the 5-min is
  what our VAH/POC/VAL and gamma levels are computed on.
- **Alerts:** set the Stacked Imbalance alert to fire, and only act when it fires
  **within ~a few ticks of a level from the sheet.** That keeps you off random
  mid-range stacks.
- **Skip:** OI Analyzer (MoEx-only), Weis Waves/Renko unless you separately like
  them — not required for this playbook.

---

## 3. Morning workflow

1. Run the rerun → refresh gamma + intraday.
2. `python3 scripts/export_levels_atas.py` → today's **levels sheet**
   (`reports/atas/levels_YYYYMMDD.csv`). Draw those horizontal lines in ATAS
   (VAH red / POC yellow / VAL green / call+put walls / gamma flip).
3. Note the **regime**: price vs gamma flip decides fade (above) vs go-with (below).
4. Wait for price to reach a **sheet level** after 10:00 ET.
5. Take the setup **only if the ATAS imbalance/cluster/delta confirmation is
   there** (Section 1). Otherwise stand aside.
6. Manage to POC/VAL/next level per the regime.

---

## 4. Honest limits

- This is a **confirmation layer**, not a new edge on its own. The edge is our
  level + regime; ATAS improves *timing and conviction* and helps you hold.
- Imbalances can **repaint before a bar closes** on aggressive (market-order)
  entries — the article flags this. Prefer the limit-at-level + close-confirmation
  variants unless you're experienced.
- No order-flow feed = no real imbalances. Don't run this on delayed/eval data and
  expect the signals to mean anything.
- Micros can mislead on their own footprint — read the full-size contract.
