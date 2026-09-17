# NQ: European vs US session, 21 dates — descriptive only

**No expectancy, no win rate, no profit factor, no verdict on any rule.** P&L
fields are deleted at source in `session_profile.py` before anything is
aggregated, so no performance number can reach this report even by accident.
21 sessions cannot support a performance claim — the MDE there is +1.55
R/session against a largest observed effect of ~0.04 — and this run is not a
covert test of one.

Sessions: 21, 1 July to 20 August 2026. Sealed June days and 23 July excluded
at construction and never opened.

---

## 1. The window overlap, handled rather than hidden

07:00–16:00 UTC and 13:30–20:00 UTC share 150 minutes, and those 150 minutes
are the US cash open — the most violent part of the day and not European in
character. The headline 07:00–16:00 window is therefore **28% US session by
time and much more than that by activity**, which is why it looks bigger than
the US window on every size measure.

**The clean comparison is `EU- 07:00–13:30`, strictly before the US open.** It
is also length-matched to `US 13:30–20:00` at 390 minutes. Everything below
leads with that pair.

---

## 2. Size and shape, median across the 21 sessions

| window | mins | range bps | realised vol bps | path bps | **efficiency** |
|---|---|---|---|---|---|
| EU 07:00–16:00 | 540 | 137.00 | 93.41 | 1475.42 | 0.04 |
| **EU- 07:00–13:30** | 390 | **73.16** | **55.63** | **769.96** | **0.05** |
| **US 13:30–20:00** | 390 | **134.81** | **96.10** | **1393.83** | **0.05** |
| US* 13:30–18:30 | 300 | 110.27 | 86.09 | 1140.94 | 0.05 |

`efficiency = |net move| / path length`. High means it trends, low means it
chops.

| bar scale | ATR bps | OR15 bps | OR30 bps | **OR30 as % of session range** |
|---|---|---|---|---|
| EU- 07:00–13:30 | **3.91** | 17.56 | **25.21** | **34%** |
| US 13:30–20:00 | **7.44** | 56.96 | **73.79** | **55%** |
| US* 13:30–18:30 | 7.74 | 56.96 | 73.79 | 67% |

| activity | prints/min | contracts/min |
|---|---|---|
| EU- 07:00–13:30 | **129.9** | **149.0** |
| US 13:30–20:00 | **847.1** | **917.4** |

### Length-matched ratios, EU- against US 13:30–20:00

| range | realised vol | path | **efficiency** | ATR | OR30 | prints | volume |
|---|---|---|---|---|---|---|---|
| 0.54 | 0.58 | 0.55 | **1.00** | 0.53 | **0.34** | **0.15** | **0.16** |

---

## 3. Signal counts — how often the existing rules fire

Each rule anchored to its own window's open, last entry 30 minutes before the
window ends, two-trade cap.

| window | rule | sessions firing | trades | per session | median risk bps |
|---|---|---|---|---|---|
| EU- 07:00–13:30 | ORB OR15 | **21/21** | 41 | 1.95 | **4.10** |
| EU- 07:00–13:30 | ORB OR30 | **21/21** | 42 | 2.00 | **4.18** |
| EU- 07:00–13:30 | pullback OR15 | **21/21** | 41 | 1.95 | **5.38** |
| EU- 07:00–13:30 | pullback OR30 | **20/21** | 38 | 1.81 | **5.73** |
| US 13:30–20:00 | ORB OR15 | 21/21 | 41 | 1.95 | **13.43** |
| US 13:30–20:00 | ORB OR30 | 21/21 | 40 | 1.90 | **10.61** |
| US 13:30–20:00 | pullback OR15 | **17/21** | 28 | 1.33 | **13.74** |
| US 13:30–20:00 | pullback OR30 | **11/21** | 20 | 0.95 | **12.64** |

Two things stand out, and only one of them is good news.

**The pullback rule fires far more often in Europe** — 21/21 and 20/21 sessions
against 17/21 and 11/21, length-matched. That is a real structural difference,
not a window-length artifact: the European opening range is small relative to
its session, so the excursion threshold (half the OR height) is easier to clear.

**The stop is less than half the size** — 4.1 to 5.7 bps against 10.6 to 14.3.
That is the whole problem, and section 4 is why.

---

## 4. The cost arithmetic, which is decisive

Cost is 2.0 NQ points round turn — **0.667 bps, fixed, regardless of session**.
The stop is a multiple of ATR, and European ATR is half. So cost as a share of
risk roughly triples.

| | EU- risk | cost/risk | US risk | cost/risk |
|---|---|---|---|---|
| ORB OR15 | 4.10 bps | **16.3%** | 13.43 bps | **5.0%** |
| pullback OR15 | 5.38 bps | **12.4%** | 13.74 bps | **4.9%** |

Breakeven win rate, `p = (1 + cost/risk) / (M + 1)`:

| rule | target | coin | **EU- breakeven** | **US breakeven** | EU edge needed | US edge needed |
|---|---|---|---|---|---|---|
| ORB OR15 | 3R | 25.0% | **29.1%** | 26.2% | **+4.1 pts** | +1.2 pts |
| ORB OR15 | 4R | 20.0% | **23.3%** | 21.0% | **+3.3 pts** | +1.0 pts |
| pullback OR15 | 3R | 25.0% | **28.1%** | 26.2% | **+3.1 pts** | +1.2 pts |
| pullback OR15 | 4R | 20.0% | **22.5%** | 20.9% | **+2.5 pts** | +0.9 pts |

**The European session demands 2.7× to 3.3× more edge over the coin than the US
session does**, for the same rule at the same target — purely because a fixed
dollar cost eats a smaller stop.

**And 0.667 bps is optimistic for Europe.** Liquidity there is **15% of US
levels** by print count and 16% by contract volume. The 2.0-point cost was
calibrated on US-session depth; in a book running at one-sixth the activity the
spread and slippage are worse, not equal. Every figure in the table above
understates the European hurdle.

---

## 5. The answer to the question asked

**It is the same market at a different hour, scaled down by about half, on
worse terms.**

The measure that decides it is the **efficiency ratio: 0.05 in both, a ratio of
1.00.** Every rule this project has tested is a continuation rule — a breakout
that holds, a pullback that resumes — and every one of them depends on the
market trending rather than chopping. On that specific property the European
session is *indistinguishable* from the US session. It is not a different
regime; it is the same shape at 55% of the size.

**Against that, two genuine structural differences, reported fairly:**

1. **The opening range is 34% of the session range in Europe against 55% in
   the US.** A European range break has substantially more room to run relative
   to the range it just broke. This is real and it points the favourable way.
2. **The pullback rule fires on 21 of 21 sessions against 17 of 21**,
   length-matched — roughly 45% more setups.

**And against those, the cost hurdle is three times worse and the liquidity is
one-sixth.** More setups on worse terms, with the same chop character, is not
obviously a better bet than fewer setups on better terms.

### What this measurement cannot tell you

Whether the European session has an edge. It measures the terms on which you
would go looking for one, and those terms are worse than the session already
screened — which returned 0 of 16, 0 of 16 and 0 of 4.

### Recommendation

**Do not buy data on this evidence.** Nothing here is an argument for spending
money, and the one favourable finding — a smaller opening range relative to the
session — is not worth 500 to 1,300 sessions of acquisition on its own.

**The recorder keeps running on 24-hour tapes**, which costs nothing and is
already happening: every recording made from here accumulates European-session
coverage at no extra effort. At one session a day that is 21 → ~65 by the time
ATAS replay's three-month window would otherwise have expired anyway.

If the European session is to be revisited, the thing that would change the
answer is not more of the same measurement — it is a cost structure where a
4 bps stop is viable, or a rule family that does not depend on the efficiency
ratio being higher than 0.05.

---

## 6. Raw output

Per-session figures: `reports/session_profile_raw.csv`,
`reports/session_profile_signals.csv`. Script: `scripts/orderflow/session_profile.py`.

Sealed NQ days remain sealed and unread.
