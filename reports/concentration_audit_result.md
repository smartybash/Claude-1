# Retroactive concentration audit: all nine prior passes fail

**No new hypotheses were run.** Every variant below was already run and already
in the ledger. The only thing that changed is which concentration rule is
applied to the same trades. The other four rejection rules are untouched.

> **OLD:** positive after removing the best 1% → `ceil(0.01 n)` trades
> **NEW:** positive after removing the best 10 **or** the top decile, whichever
> is stricter → `max(10, ceil(0.10 n))`

**66 variants audited across all eight screens that ever used the 1% rule.**
Sealed NQ days were not read. 2016–2020 remains unread.

---

## 1. The answer

| | |
|---|---|
| variants audited | **66** |
| passed under the old rule | **9** |
| of those, n < 300 | **2** |
| **flip to fail under the new rule** | **9 of 9** |

**Every single pass in the project's history fails the strengthened test.**

And the scope you set — n below 300 — turns out to be the wrong place to have
looked. **Seven of the nine flips are at n between 577 and 736**, well above
that floor. The weakness was not a small-sample problem; it was present at
every sample size.

| n range | variants | trades removed, old | trades removed, new | ratio |
|---|---|---|---|---|
| n < 100 | 6 | 1.0 | 10.0 | **10.0×** |
| 100 ≤ n < 300 | 2 | 2.0 | 11.5 | 5.8× |
| 300 ≤ n < 1000 | 12 | 7.3 | 68.7 | **9.4×** |
| n ≥ 1000 | 46 | 22.1 | 216.0 | **9.8×** |

The old rule removed about a tenth as many trades at *every* sample size. It
was uniformly weak, not weak only where n was small.

---

## 2. Every prior pass, and its fate

| family | variant | n | mean R | after new rule | verdict | n<300? |
|---|---|---|---|---|---|---|
| reopen_study | IB re-entry 1R | 736 | +0.0628 | **−0.0412** | **FAILS** | no |
| reopen_study | IB re-entry 2R | 719 | +0.0628 | **−0.1050** | **FAILS** | no |
| reopen_study | IB re-entry 3R | 718 | +0.0632 | **−0.1093** | **FAILS** | no |
| reopen_study | IB re-entry 4R | 718 | +0.0610 | **−0.1093** | **FAILS** | no |
| related_inst | IB 1R **XLK** | 592 | +0.0637 | **−0.0412** | **FAILS** | no |
| related_inst | IB 1R **EFA** | 577 | +0.0579 | **−0.0462** | **FAILS** | no |
| **FROZEN** | **IB 1R QQQ single** | **685** | **+0.0612** | **−0.0433** | **FAILS** | no |
| orb_fib | cont ORB15 A | 112 | +0.1154 | −0.1084 | FAILS | yes |
| orb_fib | cont ORB30 A | 76 | +0.2071 | −0.0616 | FAILS | yes |

The last two were already corrected in the previous run. **The other seven are
new, and one of them is the frozen candidate.**

### The frozen candidate fails

It reproduces the ledger exactly — **n = 685, mean +0.0612, sd 0.7175,
t +2.231, PF 1.22, 5 of 6 years** — and lands at **−0.0433** once the top
decile is removed.

This was the only live trade-level candidate in the project. Under the rule you
have now adopted, **it does not survive its own screen.**

| | |
|---|---|
| win rate | 55.9% |
| exit mix | close 407, target 143, stop 135 |
| top decile (69 trades) mean | **+0.994** |
| the remaining 616 trades, mean | **−0.043** |
| share of total R sitting in the top decile | **164%** |

The top decile carries more than all of the profit; the other 90% of trades
lose money in aggregate. That is the fact the old rule could not see, because
it only ever removed **7 trades**.

### A correction I made during this audit

My first pass reproduced the frozen candidate through `related_instruments.run`
on **QQQ 5-minute** bars and got n = 675, +0.0578. **That was the wrong bar
resolution** — the candidate was frozen on 1-minute bars in `reopen_study`. The
single-trade rule is exactly `test1` restricted to the first entry (`seq == 1`);
`test1`'s own re-entry control is `taken < 2`. Corrected, it reproduces the
ledger to four decimals. The verdict was the same either way (−0.047 vs
−0.0433), but the figures are now exact rather than approximately right.

---

## 3. What the new rule actually is, and you should decide if you want it

Before accepting "all nine fail", it is worth knowing what the test does
arithmetically. For a barrier trade with target `M × risk`, removing the top
decile is close to a **win-rate threshold**:

`w* = (0.1M + 1) / (1 + M)`

| target | break-even win rate under the NEW rule | random-walk rate |
|---|---|---|
| 1R | **55.0%** | 50.0% |
| 2R | **40.0%** | 33.3% |
| 3R | **32.5%** | 25.0% |
| 4R | **28.0%** | 20.0% |

**The new rule is approximately "beat the random-walk rate by 5 percentage
points".** That is a demanding bar, and it is not a neutral robustness check —
it will reject a strategy whose edge is real but thin and carried by the tail.

**I am not arguing against it.** The rule is defensible precisely because it
asks the edge to be spread across the distribution rather than concentrated in
a handful of outcomes, and the frozen candidate's 164%-in-the-top-decile is
exactly the pathology it is designed to catch. But it is a *stronger* claim
than "survives removing outliers", and the ledger should record it as such:
**the families below are not merely un-robust, they are being held to a
win-rate bar about 5 points above chance.**

The frozen candidate's 55.9% win rate sits just above the 55.0% threshold, and
it still fails — because 59% of its exits are time-exits at the close rather
than clean ±1R barriers, so the binary approximation understates how much of
the edge is tail-driven.

---

## 4. The corrected ledger

| screen | sample | outcome, corrected |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| regime forecastability, gamma | 336 sessions, 4 combinations | closed, 0 of 4 |
| levels, predictive | 1,414 + 336 sessions, 13 tests | closed, 0 of 13 |
| setup grading | 13,840 trades, 6 sets | closed, worse than random |
| calendar classification | 1,418 sessions, 52 tests | closed, 1 of 52 |
| **FOMC family** | 48 dates, 20 tests | **decisive pass — post/pre rv 3.14×, 6 of 6 years. Descriptive volatility, not a trade rule; the concentration rule does not apply.** |
| IB by rejection, Stages 1–3 | 1,418 sessions | 86% is the geometric identity |
| **IB 1R, reopened family** | **736 trades, 4 exits** | **CORRECTED — was 4 passes; now 0 of 4. Fails at −0.041 to −0.109.** |
| **IB 1R, frozen candidate** | **685 trades** | **CORRECTED — was the live candidate; now FAILS at −0.0433. No longer frozen; the family closes.** |
| **IB 1R, related instruments** | 5 instruments, 2,983 trades | **CORRECTED — XLK and EFA were recorded as passing 5 of 5; both now fail. Pooled estimate already closed the family.** |
| ORB + Fib, continuation | 5 instruments, 1,570 trades | closed; pooled non-QQQ −0.0272, and both QQQ passes already corrected |
| ORB + Fib, reversal | 13–39 setups vs a floor of 150 | not resolvable — needs ~5,400 sessions; not a failure |

### What this leaves

**Zero surviving trade-level candidates.** Before this audit the project had
one: the frozen IB 1R. It no longer passes its own screen.

The **FOMC result stands** — it is the only decisive pass in the ledger and the
concentration rule has nothing to say about it, because it is a descriptive
volatility statement (post/pre realised-vol ratio 3.14×, 6 of 6 years) and not
a trade rule with a trade distribution.

### Standing methodology changes, consolidated

| change | from | to | effective |
|---|---|---|---|
| exit constraint | flat 18:30 UTC | flat 16:00 ET | before the IB reopen |
| concentration test | remove best 1% | **remove max(10, top decile)** | now, all families, **retroactively** |
| SE convention | per-trade | clustered by date where instruments are pooled | IB family onward |

---

## 5. Two things worth saying plainly

**First: nothing was lost that was real.** The IB 1R candidate was already
under pressure — the related-instrument check had put the pooled non-QQQ
estimate at +0.0269 with an interval spanning zero. This audit explains *why*
that check came back flat: the QQQ effect was never distributed across its
trades, so there was nothing for another instrument to reproduce.

**Second: the 100% flip rate is itself informative.** Nine passes, nine
failures, at sample sizes from 76 to 736. If the old rule had been doing real
work, some passes would have survived the stricter version. None did. That is
consistent with the old rule never having been a binding constraint on
anything — it removed 1% of trades from distributions whose edge sat in the top
10%, and so it could only ever have rubber-stamped them.

**2016–2020 remains unread and unspent**, and there is now nothing frozen that
would justify opening it.

Reproduce: `python3 scripts/orderflow/concentration_audit.py`.
Full output in `reports/concentration_audit_output.txt`; per-variant detail in
`reports/concentration_audit.csv`.
