# IB ending zone + pullback rejection continuation — pre-registered

**A new trade construction.** The prior IB expectancy result is not reused and
is not evidence for or against this. The ending zone is a **qualification
state only** — no claim is made that it is itself an edge, and the high
boundary-break rate is explicitly not treated as evidence, since it was already
shown to be the geometric identity `P(break) ≈ (100 − EZ)%`.

**Data: QQQ 1-minute, 2021-01-04 → 2026-08-31. 2016–2020 is not opened. Sealed
NQ dates are not read.**

---

## 1. Unit conversion, measured not assumed

The rules are specified in NQ points; the discovery data is QQQ. Measured over
four true-tick sessions:

| date | QQQ close | NQ mean | ratio |
|---|---|---|---|
| 2026-07-15 | 717.70 | 29,713 | 41.40 |
| 2026-08-03 | 700.06 | 28,705 | 41.00 |
| 2026-08-17 | 729.85 | 30,187 | 41.36 |
| 2026-08-20 | 710.95 | 29,372 | 41.31 |

**NQ = QQQ × 41.27.** All NQ-point quantities convert per session as
`bps = 1e4 × pts / (QQQ_price × 41.27)`.

### The consequence, declared before running

A **fixed NQ point floor is a shrinking relative floor** as the index rises:

| era | QQQ | NQ | 8 pts | 40 pts | 2 ticks |
|---|---|---|---|---|---|
| 2021 | ~330 | ~13,600 | **5.87 bps** | 29.37 bps | 0.367 bps |
| 2026 | ~600 | ~24,800 | **3.23 bps** | 16.15 bps | 0.202 bps |

### And the cost rule binds harder than the stated floor, in every year

Round-trip cost is **0.667 bps** (`COST_F = 2.00/30000`). The rule
*"round trip cost exceeds 10% of initial risk"* requires **risk ≥ 6.67 bps**.

| era | 8-pt floor | 10%-cost floor | which binds |
|---|---|---|---|
| 2021 | 5.87 bps | **6.67 bps** | **cost** |
| 2026 | 3.23 bps | **6.67 bps** | **cost** |

**The 8-point floor never binds. The effective minimum stop is set by cost** —
about 9.1 NQ points in 2021 and 16.5 in 2026. Stated now so it is not
discovered in the results.

---

## 2. Qualification

1. IB = 09:30–10:30 ET. IBH/IBL = extremes of that window.
2. Which formed first = **first timestamp at which the final extreme was
   reached** (`argmax`/`argmin` return the first occurrence).
3. **Both extremes in the same 1-minute bar → session unresolved, no trade.**
4. IB Low first → expected direction **long** toward/through IBH.
   IB High first → expected direction **short** toward/through IBL.
5. `EZ = 100 × |close_10:30 − expected boundary| / (IBH − IBL)`;
   **0% = expected breakout boundary, 100% = boundary that formed first.**
6. **Qualifies only when 0% ≤ EZ ≤ 25%.**

---

## 3. Entry construction

**No entry on the initial break.** After 10:30, wait for a pullback into a zone,
then a mechanical rejection.

### Zones (tested separately, never combined into a score)

| zone | band | availability |
|---|---|---|
| **A · VWAP** | session VWAP from 09:30, running, ± **0.10 × IB range** | always |
| **B · IB midpoint** | `(IBH+IBL)/2` ± **0.05 × IB range** | always |
| **C · boundary retest** | broken expected boundary ± **0.05 × IB range** | **only after** the expected boundary has broken |

**Zone C is reported separately from A and B** — it is a breakout retest, they
are pullbacks inside the IB.

Overlap priority, fixed: **boundary retest → VWAP → IB midpoint.**
Overlap counts reported so it is visible whether these are distinct setups.

### Rejection (a touch alone is never an entry)

- **R1, one bar.** Price enters the zone; the same or a later bar closes
  **above the top of the zone** (long) **and** closes **above its own
  midpoint**. Mirror for short.
- **R2, two bar.** Price enters the zone; a subsequent bar closes **above the
  high of the first bar that entered the zone** (long). Mirror for short.

**Entry at the next 1-minute bar open, honest gap fill. Never at a historical
zone price and never at the rejection bar's close.**

### Expiry

Opposite IB boundary breaks before entry · no valid rejection by **13:00 ET** ·
session end. **Maximum one trade per session.**

---

## 4. Stop, exits, viability

**Stop = pullback extreme ∓ 2 NQ ticks**, where the pullback extreme is the
min low (long) / max high (short) from the first zone-entry bar through the
confirmation bar. **Frozen at entry** — no trail, no breakeven, no averaging.

**Rejected before entry if:** risk < 8 NQ pts · risk > 40 NQ pts ·
cost > 10% of risk (the binding one, §1).

**Exits:** expected IB boundary · 1.5R · 2R. The boundary target must be beyond
entry **and ≥ 0.75R** away, else the trade is skipped. **Flat 16:00 ET.**

---

## 5. Grid and burden, before results

**3 zones × 2 rejections × 3 exits = 18 variants.** Complete. Nothing added.

| | |
|---|---|
| sessions available | ~1,396 |
| **Bonferroni α over 18** | **0.00278** |
| variants share entries within a zone | **not independent tests** |

### MDE before results

Per-trade sd in R for a barrier trade of this shape ≈ 0.9–1.2.

| n | sd 0.9 | sd 1.2 |
|---|---|---|
| 150 | ±0.144 | ±0.192 |
| 300 | ±0.102 | ±0.136 |
| 600 | ±0.072 | ±0.096 |

At the 150-trade floor the MDE is **±0.14 R**. A rule must show roughly
**+0.15 R per trade** to be distinguishable from zero — far above the IB
family's +0.061.

---

## 6. A conflict with the standing methodology, flagged before running

The decision rule asks for *"positive after removing the best five trades"*.
**The standing concentration rule adopted at `6c99ff1` and applied
retroactively to the entire ledger is `max(10, ⌈0.10n⌉)`.** At n = 150 that
removes 15 trades, not 5.

**Both will be reported.** The five-trade test is shown because it was asked
for; the standing rule is shown beside it because dropping it silently for one
family would make this result incomparable with every audited entry in the
ledger. **If a variant passes the five-trade test but fails the standing rule,
that is reported as a split verdict, not as a pass.**

---

## 7. Controls (same entry, stop and exit logic)

1. **No ending-zone condition** — all 10:30 closes, same direction rule.
2. **Touch without rejection** — enter next bar open after the touch.
3. **Shifted zone** — the selected zone moved **0.25 × IB range** away from its
   true level, everything else unchanged.
4. **Opposite directional bias** — mechanism check only. **Will not be promoted
   into a strategy if it performs better.**

---

## 8. Decision rules, fixed

Commercially interesting requires **all ten**: ≥150 trades · positive
expectancy after costs · PF ≥ 1.15 · positive in ≥4 of 6 years · positive after
removing the best 5 (and the standing rule reported) · positive at +50% costs ·
drawdown operationally reasonable vs average trade · beats the shifted-zone
control · rejection beats touch-only · the 0–25% condition beats the
no-ending-zone control.

**3–12 trades/month is acceptable.** Daily trading is not required.

### Verdicts

Tradeable candidate · Interesting but unresolved · No added value from
confluence · Rejection adds no value · Closed.

**A high boundary-break percentage is not evidence.** Only the trade taken
after the pullback and rejection is evaluated.

---

## 9. Fill integrity

Entry at the next bar open after confirmation · gap fills at the available open ·
**entry bar excluded from the exit search** · **stop before target when both
occur in one bar** · ambiguous-bar rate reported · naive trigger-price
performance reported beside honest fills · **zero entry lookahead**, asserted.

---

Committed before `scripts/orderflow/ib_pullback.py` was written or run.
