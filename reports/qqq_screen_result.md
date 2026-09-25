# QQQ broad screen: 0 of 16, on 1,418 sessions

Grid and rejection criteria pre-registered at `697fd55`, sections 6 and 7,
before this ran. Neither was changed. The bar-resolution gate that licenses
one-minute data is at `reports/bar_resolution_gate.md`.

---

## 1. Counts, before any performance number

| | |
|---|---|
| sessions used | **1,418** — 2021-01-04 to 2026-08-31 |
| dropped | 3 (short, half day, or not reaching the flat time) |
| per year | 250 / 250 / 250 / 252 / 250 / 166 (2026 to August) |
| sessions producing a trade | 1,169 at `OR_MIN` 15, 861 at `OR_MIN` 30 |
| trades per variant | 1,425 to 2,175 |
| trades per trading session | 1.66 to 1.86, against a cap of 2.00 |
| cost | 0.667 bps round turn, the NQ figure restated |
| median risk | 6.2–7.1 bps (`STOP_ATR` 0.5), 10.1–11.1 bps (1.0) |

That is **70 times the NQ sample**, and it is the whole reason for the detour.

## 2. Ambiguity, per variant, as asked

| stop | 1.0R | 2.0R | 3.0R | 4.0R |
|---|---|---|---|---|
| `SATR` 0.5, OR15 | 0.97% | 0.19% | 0.05% | 0.05% |
| `SATR` 1.0, OR15 | 0.23% | 0.09% | 0.05% | 0.05% |
| `SATR` 0.5, OR30 | 0.93% | 0.20% | 0.07% | 0.00% |
| `SATR` 1.0, OR30 | 0.20% | 0.00% | 0.00% | 0.00% |

Under 1% everywhere, against a 20% bar. On QQQ the stop-to-target span is many
multiples of a one-minute bar, so this was never going to be the binding
problem — and the gate's real value turned out to be the defect it exposed,
not the number it was designed to produce.

## 3. Performance

Expectancy in R after costs. `t` is across sessions, with zero-trade sessions
counted as zero.

| variant | n | exp R | win% | PF | sess t | +ve years |
|---|---|---|---|---|---|---|
| OR15 SATR0.5 R1.0 | 2,175 | −0.097 | 50.5 | 0.82 | **−4.54** | 0/6 |
| OR15 SATR0.5 R2.0 | 2,161 | −0.068 | 34.8 | 0.91 | −2.20 | 1/6 |
| OR15 SATR0.5 R3.0 | 2,141 | −0.086 | 26.2 | 0.89 | −2.26 | 2/6 |
| OR15 SATR0.5 R4.0 | 2,138 | −0.089 | 21.9 | 0.90 | −2.10 | 2/6 |
| OR15 SATR1.0 R1.0 | 2,151 | −0.024 | 52.0 | 0.95 | −1.11 | 1/6 |
| OR15 SATR1.0 R2.0 | 2,107 | −0.071 | 33.9 | 0.90 | −2.30 | 2/6 |
| OR15 SATR1.0 R3.0 | 2,086 | −0.059 | 27.9 | 0.92 | −1.63 | 3/6 |
| OR15 SATR1.0 R4.0 | 2,072 | −0.049 | 25.9 | 0.94 | −1.22 | 3/6 |
| OR30 SATR0.5 R1.0 | 1,513 | −0.095 | 51.3 | 0.82 | −3.68 | 1/6 |
| OR30 SATR0.5 R2.0 | 1,493 | −0.127 | 33.4 | 0.83 | −3.48 | 1/6 |
| OR30 SATR0.5 R3.0 | 1,483 | −0.154 | 24.9 | 0.82 | −3.41 | 0/6 |
| OR30 SATR0.5 R4.0 | 1,464 | −0.094 | 22.0 | 0.89 | −1.78 | 2/6 |
| OR30 SATR1.0 R1.0 | 1,504 | −0.051 | 51.1 | 0.90 | −2.01 | 1/6 |
| OR30 SATR1.0 R2.0 | 1,467 | −0.061 | 34.4 | 0.91 | −1.65 | 2/6 |
| OR30 SATR1.0 R3.0 | 1,437 | −0.051 | 28.3 | 0.93 | −1.15 | 1/6 |
| OR30 SATR1.0 R4.0 | 1,425 | −0.036 | 26.0 | 0.95 | −0.73 | 3/6 |

**Every variant is negative. Four are significantly negative** (t between −3.4
and −4.5). Not one of the sixteen is positive in even four of the six years.

### The win rates are the clearest way to read it

| target | win rate observed | random-walk rate | gap |
|---|---|---|---|
| 1.0R | 50.5–52.0% | 50.0% | +0.5 to +2.0 |
| 2.0R | 33.4–34.8% | 33.3% | +0.1 to +1.5 |
| 3.0R | 24.9–28.3% | 25.0% | −0.1 to +3.3 |
| 4.0R | 21.9–26.0% | 20.0% | +1.9 to +6.0 |

**The rule hits its target at almost exactly the rate a coin does**, and the
cost — 0.667 bps against a 6 to 11 bps stop, so 6% to 11% of risk — turns that
coin into a loser. The small positive gaps at 3R and 4R are not enough to pay
for it, and they are not statistically distinguishable from zero.

## 4. Verdict against the pre-registered criteria

All sixteen fail criterion 1 (expectancy > 0), criterion 2 (t > 3), criterion 3
(PF > 1.15), criterion 4 (top-1% independence) and criterion 5 (positive in at
least four years). **Every variant fails every criterion.**

**Survivors: 0 of 16.**

No step-3 verification on the NQ tick sessions is required, because nothing
survived to verify.

## 5. What this settles, and what it does not

**Settles:** the pullback-continuation family is finished. On 20 NQ sessions it
was a coin flip that could not be distinguished from noise; the honest reading
then was "not yet killed". On 1,418 sessions of the closest available proxy it
is killed, and killed with a sample large enough that the absence of an edge is
a measurement rather than a shrug. The extension to 3R and 4R targets — the
cells that need the least edge and that grid 2 never reached — did not rescue
it.

**Does not settle:** NQ's overnight auction. QQQ's cash open follows a closed
book. If the pullback works on NQ specifically *because* the opening range
forms against an overnight session, this screen could not have seen it. That
was named as the largest untestable difference before the run and it still is.
It is, however, a narrow escape hatch: it requires the edge to live entirely in
a feature QQQ lacks, while the rule itself performs at coin-flip rates on
1,418 sessions of an instrument tracking the same index.

**And a methodological result worth more than either:** the screen's first run
showed 16 of 16 surviving at t between +5.8 and +16.5, every year positive, a
74% win rate at a 1R target. That was a fill assumption — a stop order credited
with its own trigger price on bars that had already opened past it, worth
+0.56R against expectancies of +0.24R to +0.55R. Extraordinary results were
treated as defects until proven otherwise, and both times they were defects.

## 6. Ledger

| family | sample | outcome |
|---|---|---|
| order flow | 20 NQ sessions | closed |
| pullback grid 1 | 20 NQ sessions | rejected, broken spec |
| pullback grid 2 | 20 NQ sessions | closed, coin flip |
| **pullback, QQQ screen** | **1,418 QQQ sessions, 16 variants** | **closed, 0 of 16, four significantly negative** |

Sealed days: still sealed. Eight June days and 23 July have never been read,
by this run or any other.
