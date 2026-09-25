# Forward execution audit — harness built, one prerequisite blocking

Reconstruction is closed. No further grids, no parameter changes. This is the
apparatus for auditing the script's **own live alerts** against the tick tape.

**The engine is built and validated. It cannot start collecting because
true-tick recording stopped on 2026-08-20.**

---

## 1. The blocking prerequisite

| | |
|---|---|
| true-tick (`fmt=1`, 0.25 pt) recordings | **end 2026-08-20** |
| since then | `.gz` plain only — **quantised to 5.0 points** |
| newest tape file written | **2026-09-17** |
| today | 2026-09-21 |

Every date from 2026-08-21 to 2026-09-11 has **only** the degraded copy: 93–123
distinct prices in a whole session. The strategy's stop is ~12 points. **On a
5-point grid a 12-point stop is 2.4 cells** — whether it was touched before the
reversal is not resolvable, and that ordering *is* the audit.

Note the dates through 2026-08-20 have **both** formats — a `.br` at 0.25 and a
`.gz` at 5.0 for the same session. So this is a recorder *setting*, not a data
outage.

> **Restore `fmt=1` / 0.25-point recording before any alert is collected.**
> Alerts captured against quantised tape produce an executable ledger that
> cannot be trusted, and there is no way to repair it afterwards.

---

## 2. What is built and proven

`scripts/orderflow/trendline_audit.py` — two parallel ledgers, four group
breakdowns, seven metrics each, six pre-declared kill conditions.

**The causality rule is structural, not a filter:** the executable ledger calls
`first_after(t, p, alert_ts)`, which takes the first tick **strictly after** the
alert. A line price the market crossed earlier in the bar is unreachable by
construction and cannot be reintroduced by an oversight later.

### Self-test, on real tape with a deliberately arbitrary trigger

Not a strategy and it produces no verdict. Its job is to prove the accounting.
Chart entries were planted **3.00 points better than the market** and the chart
was made to book its target every time:

| assertion | result |
|---|---|
| entry slippage recovers the planted −3.00 | **−2.849** ✓ |
| exit slippage is adverse | **−10.579** ✓ |
| chart P&L exceeds executable P&L | $21,280 vs **$536** ✓ |
| every executable fill strictly after its alert | **True** ✓ |
| disagreement counter fires | 40.8% ✓ |

**SELF-TEST PASSED.**

**A bug it caught:** both slippage terms were sign-inverted — adverse slippage
was reporting as positive. Had the harness shipped unvalidated, every kill
condition touching slippage would have read backwards. Fixed and re-asserted.

---

## 3. Capturing the alerts

Alert type **"Order fills only"**, one alert per order. Message body:

```
{"ts":"{{timenow}}","act":"{{strategy.order.action}}",
 "px":{{strategy.order.price}},"pos":"{{strategy.market_position}}",
 "prev":"{{strategy.prev_market_position}}","id":"{{strategy.order.id}}",
 "cmt":"{{strategy.order.comment}}","mkt":{{close}}}
```

Three points that make this work:

- **`{{timenow}}` not `{{time}}`.** `{{time}}` is the bar's open; `{{timenow}}`
  is when the alert actually fired. The audit is built on the latter.
- **`{{strategy.prev_market_position}}` identifies a reversal** without any
  guesswork: previous position non-flat and opposite to the new one.
- **`{{strategy.order.price}}` on the EXIT alerts gives the stop and target
  prices directly.** The stop multiplier never has to be known — it is observed.

Order-level events pair mechanically into the trade-level schema in
`journal/trendline_alerts.csv` (10 columns, two worked example rows).

---

## 4. Stopping point and timeline

| | |
|---|---|
| required | **100 reversal-affected trades** |
| rate | 28.6 trades/session × 20.4% = **5.8/session** |
| **sessions needed** | **≈ 17** (~3.5 calendar weeks) |

Below 100 the harness prints **"INTERIM — IMPLEMENTATION CHECKING ONLY. NOT A
VERDICT."** and refuses to evaluate the kill conditions. That refusal is in the
code, not a convention to remember.

---

## 5. The six kill conditions, in code

| # | condition | reject if |
|---|---|---|
| 1 | executable expectancy | ≤ 0 after commission |
| 2 | executable profit factor | < 1.15 |
| 3 | chart profit lost | > half disappears |
| 4 | reversal trades in executable form | ≤ 0 |
| 5 | chart fills unavailable after the alert | > 50% of entries |
| 6 | same-bar advantage one-sided | > 70% favour the chart |

**Any one fires → reject.** If none fires → eligible for minimum-size paper
trading, **explicitly not validated** from this sample.

---

## 6. What happens next, in order

1. **Restore true-tick recording.** Nothing else can start.
2. Attach the alert with the message body above; append rows daily.
3. Run `python3 scripts/orderflow/trendline_audit.py audit` as often as you
   like — it will decline to give a verdict until 100 reversal trades exist.
4. At 100, the kill conditions evaluate themselves.

The audit needs no Pine source, no trade CSV, and no knowledge of the pivot
settings or the stop multiplier. **It needs the script's own alerts and a tape
that can resolve them.**

Reproduce the validation: `python3 scripts/orderflow/trendline_audit.py selftest`.
