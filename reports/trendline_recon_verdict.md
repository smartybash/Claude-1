# Trendline reversal — bounded reconstruction. NOT a replication.

Nine mechanical specifications (3 pivot settings × 3 stop multipliers), three
execution models, four cost levels, on **36 true-tick NQ sessions
(2026-07-01 → 2026-08-20)**. 9,720 five-minute bars built from the tape itself,
so the three models differ **only** in execution assumption.

**Pivot strength/length and the stop multiplier were never disclosed.** This is
a bounded reconstruction from the author's stated rules, not the strategy.

**Sealed days excluded. 2016–2020 unread.** Positions are flattened at each tape
day's end because the archive is not contiguous — declared, not hidden.

---

## 1. Calibration: the structure reconstructs, the profit does not

| ledger | reconstruction (Model A, no cost) | verdict |
|---|---|---|
| **28.6 trades/session** | **28.6** at pivot 3/3, stop 1.2 | **matches exactly** |
| avg win 31.5 pts (⇒ TP ≈ 1.2×ATR14, ATR ≈ 26) | **TP distance 31–33 pts** | **matches** |
| **20.4% reversal-affected** | **21.1%** at pivot 5/5, stop 1.2 | **matches** |
| 57% win rate | **30.9 – 47.4%** | **fails** |
| **+7.99 gross pts/trade** | **−0.18 to −2.35** | **fails** |

Three of five calibration checks land within a few percent at plausible pivot
settings. **So the reconstruction is not wildly wrong — and it still loses
money under the optimistic fill model.**

---

## 2. Model A — the optimistic reconstruction — is negative on all nine

| pivot | stop | n | /sess | win% | pts/trade | PF | P&L (no cost) | rev% | $ from reversals | $ from the rest |
|---|---|---|---|---|---|---|---|---|---|---|
| 2/2 | 0.5 | 1707 | 47.4 | 32.4 | −0.77 | — | −$26k | 20.3 | — | — |
| 3/3 | 0.5 | 1352 | 37.6 | 31.9 | −0.18 | 0.98 | **−$4,919** | 14.5 | −$58,516 | +$53,597 |
| 3/3 | 1.0 | 1088 | 30.2 | 43.1 | −0.86 | 0.94 | −$18,801 | 23.9 | −$88,382 | +$69,581 |
| **3/3** | **1.2** | **1029** | **28.6** | 45.5 | −1.01 | 0.94 | −$20,696 | 26.5 | −$95,684 | +$74,987 |
| 5/5 | 1.0 | 792 | 22.0 | 43.9 | −0.52 | 0.97 | −$8,169 | 18.1 | −$51,510 | +$43,341 |
| **5/5** | **1.2** | **739** | 20.5 | 47.4 | −0.69 | 0.96 | −$10,261 | **21.1** | −$60,017 | +$49,756 |

**Range across all nine: −$4,919 to −$63,710. Not one is positive.**

### The reversal sign is inverted

The ledger says reversal bookkeeping **adds $77,572**. In every reconstruction
it **subtracts** — −$36,613 to −$108,351 — while the non-reversal trades carry
what little there is.

**Why:** the opposite trendline usually sits *further* from entry than the stop.
Exiting at the line is then **worse** than the stop, not better. The ledger's
claim that "the opposite trade opened between entry and stop" requires the
opposite line to fall inside the stop distance, and with a causally-built line
it mostly does not.

---

## 3. Models B and C

At **commission + 1 tick each side**:

| spec | B P&L | B PF | C P&L | C PF | verdict |
|---|---|---|---|---|---|
| 2/2 0.5 | −$5,469 | 0.98 | −$84,523 | 0.83 | fail |
| 2/2 1.0 | +$8,364 | 1.03 | −$95,001 | 0.81 | fail |
| 2/2 1.2 | +$2,740 | 1.01 | −$88,597 | 0.83 | fail |
| 3/3 0.5 | −$12,857 | 0.93 | −$60,858 | 0.85 | fail |
| 3/3 1.0 | −$17,456 | 0.93 | −$45,441 | 0.89 | fail |
| 3/3 1.2 | −$19,673 | 0.92 | −$42,262 | 0.89 | fail |
| 5/5 0.5 | −$6,306 | 0.95 | −$38,561 | 0.88 | fail |
| 5/5 1.0 | +$1,803 | 1.01 | −$16,857 | 0.94 | fail |
| **5/5 1.2** | **+$5,525** | **1.03** | **−$13,076** | **0.96** | fail |

**Positive specifications by cost level:**

| cost | Model A | Model B | Model C |
|---|---|---|---|
| none | **0/9** | 6/9 | 1/9 |
| commission | **0/9** | 5/9 | 0/9 |
| comm + 1 tick | **0/9** | 4/9 | **0/9** |
| comm + 2.1 pt | **0/9** | **0/9** | **0/9** |

**Model C is negative on 9 of 9 at every realistic cost.** Model B's best
profit factor anywhere is **1.03**, against a 1.15 bar.

Model C also produces **40–100% more trades** than A or B (tick-level crossings
fire more often) and shows **30–48% same-bar exits/re-entries**, against 0% in
Model A — the same-bar mechanism is real in the tape, it simply does not pay.

---

## 4. The decision rule, applied

| condition | result |
|---|---|
| 1. positive in Model B after realistic costs | 4 of 9 — but see 3 |
| 2. positive in Model C | **0 of 9** |
| 3. PF > 1.15 in both | **0 of 9** (best is 1.03) |
| 4. reversal dependency ≤ 50% of profit | passes only trivially — dependency is **negative** (−205% to −1629%), i.e. reversals lose and the rest carries |
| 5. positive with reversal disabled | moot; 1–3 already fail |

# **0 of 9 specifications pass.**

---

## 5. What this does and does not establish

### Established

- **Under the disclosed rules with causally-confirmed pivots, no plausible
  specification is profitable** — not in the tick model, not in the causal bar
  model, and not even in the optimistic TradingView-style model.
- **The reported backtest is non-investable** by the stated rule.
- **The reversal bookkeeping does not generate profit in any causal
  reconstruction.** It destroys it, because the opposite line typically lies
  beyond the stop.

### Not established, and this matters

**Model A was supposed to approximately reproduce the advertised behaviour if
the pivot settings were close. It reproduced the frequency, the target distance
and the reversal share — and not the profit.** Two explanations, and the
evidence does not separate them:

1. **The published line was not causal.** My lines never exist before their
   pivots confirm. If the original draws from the pivot bar itself, every
   advertised entry used information from `right` bars in the future. This is
   the repaint question, listed as unknown and still unknown.
2. **My signal definition differs.** The spec says *descending* resistance and
   *ascending* support; I connected the last two pivots without filtering on
   slope. I also traded crossings as breakouts. If the original fades the line
   rather than breaking it, the sign of everything changes.

**Explanation 2 is untested and I am not going to sweep it** — that would be
optimising to reach a target, which was ruled out.

### A correction made during this run

My first pass fired signals on any **touch** of the extended line, giving 88–111
trades/session against the ledger's 28.6. The spec says *crosses*; I fixed it to
require the prior close on the other side, and frequency then landed at 28.6
exactly. **A second bug:** the decision loop compared `R.pivot` — which resolves
to the pandas `DataFrame.pivot` method, not the column — so every specification
was silently skipped and the table printed empty. Both are fixed; the tables
above are from the corrected run.

---

## 6. Verdict

# PAPER TRADE ONLY

Unchanged in label, **changed in weight.** The previous verdict rested on the
signal being unassessable. Nine plausible versions of it have now been assessed
and all nine lose under causal construction, including optimistically. That is
evidence against the signal, not absence of evidence.

I am not calling it dead only because you instructed me not to, and because the
reconstruction is bounded — the true pivot settings and the slope convention
remain unknown. **The burden has moved: it is now on the strategy to demonstrate
an edge, not on us to disprove one.**

### The test, unchanged and still requiring no anchor

Forward-record the live bot's **actual fills** against the chart's claimed fills.
At 20.4% reversal incidence, ~100 affected trades takes **~9 sessions**.

**Kill conditions, declared now — any one closes it:**

1. realised fills diverge from the chart beyond the cost band;
2. the ~80% of trades untouched by reversal bookkeeping fail to earn more than
   the $2–6/trade implied by the ledger's own arithmetic;
3. same-bar re-entries are not adverse roughly as often as favourable.

Size: broker minimum. The log is the deliverable, not the P&L.

Reproduce: `python3 scripts/orderflow/trendline_recon.py`.
Full tables in `reports/trendline_recon_output.txt`; per-specification detail in
`reports/trendline_recon.csv`.
