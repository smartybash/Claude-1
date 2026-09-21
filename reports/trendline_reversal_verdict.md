# Trendline reversal — desk go/no-go. Not a replication.

Benchmark corrected: **2 MNQ, commission case**. The +$343,262 figure was the
1 NQ **no-cost** case and is not used here.

| | 2 MNQ (commission) | 1 NQ equivalent |
|---|---|---|
| Reverse **on** | **+$63,414** | +$317,070 |
| Reverse **off** | **−$14,158** | −$70,790 |
| difference | **$77,572** | $387,860 |

Cross-check: $387,860 / $77,572 = **5.00**, exactly $20/pt vs $4/pt. And
15,854 pts / 2,147 trades = **7.38 pts/trade**, matching the stated figure.
The benchmark reconciles.

---

## 1. What the 438 trades must carry

| | |
|---|---|
| total P&L difference | **$77,572** (2 MNQ) · $387,860 (1 NQ) |
| **per affected trade** | **$177.11** (2 MNQ) · $885.53 (1 NQ) |
| **in NQ points per affected trade** | **44.28 pts** |
| **as a share of net profit** | **122.3%** |
| vs the system's own average trade | **6.0×** the +7.38 pts |

### Against intrabar geometry — 21 true-tick sessions, 5,676 five-minute bars

| best directional run per bar | pts |
|---|---|
| p25 | 15.00 |
| **p50** | **25.00** |
| p75 | 40.00 |
| p90 | 60.00 |

| | |
|---|---|
| required per affected trade | **44.28 pts** |
| **as a multiple of the median run** | **1.77×** |
| **percentile of available runs** | **80th** |
| bars physically offering ≥ 44.28 pts | **19.9%** (1,129 of 5,676) |

**Every one of the 438 trades must land on a bar in the top 20% by intrabar
travel and extract essentially all of it.** Not on average — on each one.

### Decomposition of the two populations

Assuming Reverse-off books those trades as full stops at the implied ~12-pt
risk (stated as an assumption, not a measurement):

| population | n | points each |
|---|---|---|
| unaffected | 1,709 | **+1.00** |
| **reversal-affected** | **438** | **+32.28** |

Robust across the plausible risk range: at 10 / 12 / 14-pt stops the unaffected
trades average **+0.49 / +1.00 / +1.52 pts** — i.e. **$2 to $6 a trade at
2 MNQ**, inside the cost and slippage band. **The 80% of trades that do not
touch reversal bookkeeping earn approximately nothing.**

---

## 2. Three conclusions

### A. Proven from the supplied report

1. **122.3% of net profit depends on same-bar reversal bookkeeping.** The swing
   exceeds the entire profit: remove it and the system loses money.
2. **The dependency is concentrated in 20.4% of trades** which must each deliver
   6.0× the average trade, purely from how the fill is booked.
3. **The required magnitude is at the 80th percentile of intrabar travel**, so
   it cannot be dismissed as rounding — it is near the top of what a 5-minute
   bar physically contains.
4. **Same-bar re-entry is favourable in every observed instance** (4 of 4 with a
   non-zero gap, 0 adverse, 22.4% of that day's P&L). An unbiased artefact would
   be adverse roughly half the time.
5. **The fills are not executable as recorded** — 27 of 30 in the supplied
   sample sit off the NQ 0.25 grid.
6. **The project's own 720-config sweep** put intrabar entry at a **median 4.3×**
   dollar inflation versus the no-lookahead run, with bar-close entry matching.
7. **Excluding reversal bookkeeping, the remaining 1,709 trades earn ~$2–6
   each** — below realistic costs.

### B. Unknown without the source or the entry-line definition

- Whether the signal has any edge at all. **It cannot be reconstructed, so it is
  not being called dead.**
- Whether the line repaints or uses future-confirmed pivots. If it does, the
  result is unimplementable rather than merely optimistic — and this is
  undecidable from the evidence supplied.
- Whether reversal exits are bounded by the stop. One observed `Rev` breached
  its own stop by ~4×, which contradicts the report's own description.
- Whether "Reverse off" re-prices the same trades or takes a different path. The
  $945/trade swing at 1 NQ is far larger than any stop distance, so it is almost
  certainly a path change — meaning the two runs are **not the same trades**.
- The true stop and target formulas, and therefore the real risk per trade.

### C. Classification

**The reported backtest is non-investable** — 122.3% > 100% by the stated rule.

**The reported results are an upper bound, not expected performance** — intrabar
assumptions move P&L by several multiples (4.3× median on the project's own
sweep; the reversal fork alone is a 122% swing).

---

## 3. Verdict

# PAPER TRADE ONLY

Not "reject completely", because that would amount to declaring the signal dead
and the signal cannot be reconstructed from the evidence available. Not a live
allocation, because the only documented edge sits in bookkeeping that a live
order cannot reproduce.

### The one test that needs no anchor

**The live bot already contains the missing information.** Forward-record its
actual fills against the chart's claimed fills, trade by trade. That settles the
entire execution question without anyone ever disclosing the trendline
definition, and the report already notes a **2.1-point execution gap** observed
live — a partial observation of exactly this.

**Pass condition, declared before collecting:** at 438/2,147 = 20.4% incidence,
roughly **100 reversal-affected trades takes ~9 sessions** at 28.6 trades a day.
The system is worth revisiting only if, on those:

1. realised fills match the chart within the cost band, **and**
2. the 80% of trades untouched by reversal bookkeeping earn more than ~$2–6
   each, **and**
3. same-bar re-entries are adverse roughly as often as favourable.

**Any one of those failing closes it.** Point 2 is the one to watch: that
population is the strategy without the artefact, and on the reported numbers it
earns nothing.

Size: the minimum the broker permits. The log is the deliverable, not the P&L.
