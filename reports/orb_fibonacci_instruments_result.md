# ORB + Fibonacci: the instrument extension closes the family

Frozen continuation rule from `5612140` / `c9196d1`, **unchanged**, on SPY,
IWM, IJH and EFA. 1-minute bars, 2021-01-04 .. 2025-12-31.

**ORB15 band A and ORB30 band A only.** Bands A and B share 86–90% of their
sessions and are not independent tests, so band B is dropped rather than
reported as a second observation.

**2016–2020 remains unread. Sealed NQ days were not read.**

---

## 1. The decision, against the rule you declared

> *"If the pooled non-QQQ estimate is positive with the interval excluding
> zero, and survives the strengthened concentration test, the family stays open
> and I will consider the holdout. Otherwise close it."*

| variant | positive | interval excludes 0 | survives concentration | verdict |
|---|---|---|---|---|
| ORB15 band A | **no** (−0.0589) | **no** | **no** | **CLOSE** |
| ORB30 band A | yes (+0.0235) | **no** | **no** | **CLOSE** |
| both pooled | **no** (−0.0272) | **no** | **no** | **CLOSE** |

**All three criteria fail on every variant. The family closes.** The holdout
is not spent.

---

## 2. A data-fetch decision worth stating

The frozen rule is defined in **bars** — Y = 30, Z = 5, swing fractal k = 2 —
on a 1-minute grid. The 5-minute files already on disk from the IB family would
have silently redefined all three (Y → 150 minutes, Z → 25 minutes, swings → 10
minutes wide). **That is not the frozen rule.** 1-minute data was fetched for
all four instruments instead: 240 instrument-months, ~1.94M bars.

| instrument | bars | sessions loaded | first | last |
|---|---|---|---|---|
| SPY | 489,326 | 1,253 | 2021-01-04 | 2025-12-31 |
| IWM | 488,984 | 1,249 | 2021-01-04 | 2025-12-31 |
| **IJH** | 476,294 | **1,161** | 2021-01-04 | 2025-12-31 |
| EFA | 487,595 | 1,244 | 2021-01-04 | 2025-12-31 |

**IJH loses 94 sessions to the 360-bar minimum** where the others lose 2–11.
It is the least liquid instrument in the set and has minutes with no prints.
Flagged rather than silently accepted; it does not change the verdict, since
IJH is negative on one variant and near zero on the other.

---

## 3. Counts first

| variant | instrument | sessions | trades | rate | lookahead | ambiguous |
|---|---|---|---|---|---|---|
| ORB15 A | SPY | 1,253 | 105 | 8.4% | 0 | 2.9% |
| ORB15 A | IWM | 1,249 | 89 | 7.1% | 0 | 1.1% |
| ORB15 A | IJH | 1,161 | 113 | 9.7% | 0 | 0.0% |
| ORB15 A | EFA | 1,244 | 142 | 11.4% | 0 | 1.4% |
| ORB15 A | *QQQ* | *1,396* | *112* | *8.0%* | *0* | *0.0%* |
| ORB30 A | SPY | 1,253 | 73 | 5.8% | 0 | 1.4% |
| ORB30 A | IWM | 1,249 | 47 | 3.8% | 0 | 0.0% |
| ORB30 A | IJH | 1,161 | 65 | 5.6% | 0 | 1.5% |
| ORB30 A | EFA | 1,244 | 95 | 7.6% | 0 | 0.0% |
| ORB30 A | *QQQ* | *1,396* | *76* | *5.4%* | *0* | *2.6%* |

**Entry lookahead is 0 on all ten cells.** Trade rates on the new instruments
bracket QQQ's, so the rule is firing at a comparable frequency — it transferred
mechanically even though it did not transfer economically.

---

## 4. Per-instrument breakdown, clustered SE

| variant | inst | n | mean R | clus SE | t | PF | win% | RW% | gap |
|---|---|---|---|---|---|---|---|---|---|
| ORB15 A | SPY | 105 | +0.0287 | 0.1110 | +0.26 | 1.06 | 39.0 | 37.7 | +1.4 |
| ORB15 A | **IWM** | 89 | **−0.2647** | 0.1415 | −1.87 | 0.59 | 31.5 | 43.8 | −12.3 |
| ORB15 A | IJH | 113 | +0.0217 | 0.1119 | +0.19 | 1.04 | 40.7 | 39.7 | +1.0 |
| ORB15 A | EFA | 142 | −0.0587 | 0.1046 | −0.56 | 0.90 | 37.3 | 39.9 | −2.5 |
| ORB15 A | *QQQ* | *112* | *+0.1154* | *0.1162* | *+0.99* | *1.23* | *44.6* | *39.6* | *+5.0* |
| ORB30 A | SPY | 73 | +0.1400 | 0.1341 | +1.04 | 1.32 | 41.1 | 34.5 | +6.6 |
| ORB30 A | IWM | 47 | +0.0253 | 0.1655 | +0.15 | 1.05 | 42.6 | 41.3 | +1.2 |
| ORB30 A | IJH | 65 | −0.0861 | 0.1999 | −0.43 | 0.86 | 43.1 | 46.7 | −3.6 |
| ORB30 A | EFA | 95 | +0.0081 | 0.1131 | +0.07 | 1.02 | 44.2 | 43.8 | +0.4 |
| ORB30 A | *QQQ* | *76* | *+0.2071* | *0.1302* | *+1.59* | *1.53* | *50.0* | *39.6* | *+10.4* |

**Eight new instrument-variant cells. Three are negative, and the largest
single reading in the whole table is IWM at −0.265.** No instrument reproduces
the QQQ gap of +5.0 / +10.4 points over the random-walk rate; the new cells
range from −12.3 to +6.6 and straddle zero.

**QQQ remains the best cell in the table on both variants.** That is the
signature of a discovery-sample artifact, not of an effect that exists and was
merely measured noisily elsewhere.

---

## 5. Pooled non-QQQ estimate

| variant | trades | dates | mean R | sd | clus SE | t | **95% CI** | Bonferroni CI (α=0.025) |
|---|---|---|---|---|---|---|---|---|
| ORB15 A | 449 | 314 | **−0.0589** | 1.227 | 0.0658 | −0.90 | **[−0.1878, +0.0700]** | [−0.2062, +0.0885] |
| ORB30 A | 280 | 196 | **+0.0235** | 1.250 | 0.0865 | +0.27 | **[−0.1460, +0.1930]** | [−0.1703, +0.2173] |
| **both pooled** | **729** | **423** | **−0.0272** | 1.236 | 0.0588 | −0.46 | **[−0.1424, +0.0880]** | [−0.1590, +0.1045] |

SEs clustered by date, as in the IB study. Clustering inflates the SE by only
~13% here, because 729 trades spread over 423 dates is 1.7 per date — the four
instruments rarely set up simultaneously, so they are closer to independent
observations than they were in the IB family.

### The discovery estimates fall outside these intervals

| variant | QQQ discovery | non-QQQ 95% CI | inside? |
|---|---|---|---|
| ORB15 A | +0.1154 | [−0.1878, +0.0700] | **no** |
| ORB30 A | +0.2071 | [−0.1460, +0.1930] | **no** |

**This is the strongest statement the run supports.** The extension cannot
prove the effect is zero — the MDE is too wide for that — but it *can* and does
reject the discovery effect size on both variants. Whatever produced +0.115 and
+0.207 on QQQ is not present at that magnitude in four other instruments over
the same five years.

---

## 6. The strengthened concentration test — standing change

**Standing change, recorded here and applied from now on in every family:**

> **OLD:** remove the best 1% of trades.
> **NEW:** remove the best 10 trades **or** the top decile, **whichever is
> stricter** — i.e. remove `max(10, ceil(0.10 × n))`.

At n ≈ 100 the old rule stripped one or two trades and could not meaningfully
fail. Applied to the pooled estimates:

| set | n | mean R | median | k removed | after removal | survives |
|---|---|---|---|---|---|---|
| ORB15 A | 449 | −0.0589 | −0.3761 | 45 | **−0.2849** | **no** |
| ORB30 A | 280 | +0.0235 | −0.3602 | 28 | **−0.1928** | **no** |
| both pooled | 729 | −0.0272 | −0.3665 | 73 | **−0.2496** | **no** |

**And applied retroactively to the QQQ discovery cells, which is the point of
making it standing:**

| variant | instrument | old rule (ex-1%) | **new rule** | k |
|---|---|---|---|---|
| ORB15 A | QQQ | +0.0814 **pass** | **−0.1084 fail** | 12 |
| ORB30 A | QQQ | +0.1834 **pass** | **−0.0616 fail** | 10 |

**Both QQQ variants that "survived" the original screen fail the strengthened
test.** The two survivors reported in the previous run were survivors of a test
too weak to reject them. That is now corrected in the ledger.

**Every cell in this entire family — all ten — goes negative once the top
decile is removed.** Median R is negative on every single one.

---

## 7. MDE against the observed effect

| variant | n | clus SE | MDE | observed | QQQ discovery | detectable? |
|---|---|---|---|---|---|---|
| ORB15 A | 449 | 0.0658 | **+0.2027** | −0.0589 | +0.1154 | no |
| ORB30 A | 280 | 0.0865 | **+0.2665** | +0.0235 | +0.2071 | no |
| both pooled | 729 | 0.0588 | **+0.1812** | −0.0272 | — | no |

**The extension delivered the power it promised.** The MDE fell from **+0.39 to
+0.435** on the single-instrument discovery run to **+0.18** pooled — a little
better than halved, as the roughly four-fold sample increase predicts.

**And at that resolution the effect is not there.** The point estimate did not
merely fail to reach significance; it moved to **−0.027**, the wrong side of
zero, with the discovery values excluded from the interval. This is not an
underpowered null of the kind that means nothing — it is a null that is
informative about the discovery estimate, even though it cannot resolve an
effect of, say, +0.05.

---

## 8. The reversal family — closed on sample size, not on a failure

**Recorded as instructed: the reversal family is not resolvable with available
data, and is not a negative result.**

It requires a seven-link chain inside one session — break, outburst, Fib
failure, structure shift, opposite outburst, new Fib, retracement entry. On
1,396 QQQ sessions it fired **13–39 times** depending on variant, against a
declared floor of 150.

> **It would need roughly 5,400 sessions — about 21 years of a single
> instrument — to reach the floor. No sample this project can reach resolves
> it. Its expectancy was never evidence in either direction and is not recorded
> as a failure.**

---

## 9. Where the ledger stands

### Standing methodology changes

| change | from | to | effective |
|---|---|---|---|
| exit constraint | flat 18:30 UTC | flat 16:00 ET | before the IB reopen |
| **concentration test** | **remove best 1%** | **remove max(10, top decile)** | **now, all families** |
| SE convention | per-trade | **clustered by date where instruments are pooled** | IB family onward |

### Families

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| regime forecastability, gamma | 336 sessions, 4 combinations | closed, 0 of 4 |
| levels, predictive | 1,414 + 336 sessions, 13 tests | closed, 0 of 13 |
| setup grading | 13,840 trades, 6 sets | closed, worse than random |
| calendar classification | 1,418 sessions, 52 tests | closed, 1 of 52 |
| FOMC family | 48 dates, 20 tests | **decisive pass**, post/pre rv 3.14× |
| IB by rejection | 1,418 sessions | 86% is the geometric identity |
| IB 1R, related instruments | 5 instruments, 2,983 trades | closed, pooled +0.0269, CI spans zero |
| **ORB + Fib, continuation** | **5 instruments, 1,570 trades** | **CLOSED — pooled non-QQQ −0.0272, CI spans zero, fails concentration** |
| **ORB + Fib, reversal** | **13–39 setups vs a floor of 150** | **NOT RESOLVABLE — needs ~5,400 sessions; not a failure** |

**2016–2020 remains unread and unspent.** Fifteen families have now been
closed, one has passed decisively, and one is unresolvable — and the holdout is
still worth exactly what it was at the start, because nothing has been taken
from it.

Reproduce: `python3 scripts/orderflow/orb_fib_instruments.py`.
Full output in `reports/orb_fib_instruments_output.txt`; per-trade detail in
`reports/orb_fib_instruments_trades.csv`.
