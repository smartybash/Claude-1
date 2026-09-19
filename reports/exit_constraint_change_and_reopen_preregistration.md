# Ledger: exit constraint changed, and two families reopened

## 1. The constraint change, recorded with its provenance

**Old:** flat by 18:30 UTC. **New:** flat at the US cash close, 16:00 ET. No
overnight positions.

**This was relaxed AFTER seeing IB Stage 3, and the reason is lifestyle, not
statistical.** That is a researcher degree of freedom exercised post-hoc, and it
is recorded here in those words so nobody later reads the change as evidence-led.
What it costs: any result that depends on the relaxation is discovery-grade only
and needs the holdout to mean anything.

**Reopened by this change: two families, named below. Nothing else.** Order flow,
ORB, pullback continuation, the grading scheme, regime conditioning and the
Reddit mechanisation were closed on evidence and stay closed.

## 2. Correction: Test 1 was never bound by the old constraint

`QQQ_1m.parquet` covers **09:30–15:59 only**, and the IB study's post-window was
`t_min >= 60` with **no upper bound**. It therefore already exited at 15:59 — the
new constraint, not the old one.

**So the previously reported IB Stage 3 figures already reflect flat-at-close:**
expectancy +0.061 to +0.072 R, PF 1.22–1.25, 5 of 6 years positive, **t = 2.23 to
2.33 against the standing bar of t > 3**. Relaxing the clock does not rescue Test
1, because the clock was never what constrained it.

**What is genuinely new in Test 1 is only the second trade per session.**

## 3. Test 1 — IB by rejection, unchanged but with re-entry

IB 09:30–10:30. Expected side = opposite the extreme that formed first. Require
the 10:30 close in the 0–25% ending zone adjacent to the expected break. Enter
only after that boundary actually breaks. **Honest fill at the first available
price — `max(trigger, bar open)` for a long, mirrored for a short — never at the
boundary.** Stop at the opposite IB boundary. One position at a time.

**Second trade:** after trade 1 closes, the setup re-arms only once price trades
back inside the IB, and entry is the next break of the **same** expected
boundary. Maximum two. Declared here so "two trades" cannot become "two bites at
whichever looked better".

Exits: 1R, 2R, 3R, hold-to-close. **All four reported. None selected on this run.**

## 4. Test 2 — VWAP hold to close, re-specified

### What the original was, and why this is not a re-run

The +21.70 points at t +2.14 was **45 NQ sessions**, entry on the top/bottom
quintile of `vwap_disp` on *every* minute bar — dozens of concurrent positions.
The signal is **mean-reverting**: IC to the close was **−0.5668**, so the trade is
long when price is far *below* VWAP and short when far *above*.

**This runs on QQQ, 1,418 sessions — a 30× larger sample and a different
instrument.** The 45-session NQ figure is *not* evidence for what follows and is
not carried forward. It is the reason the idea is being retested, nothing more.

### Signal, declared causally

`disp = (price − session VWAP) / session VWAP`, VWAP from the session's own bars
to that point. A bar qualifies when `|disp|` exceeds the **80th percentile of the
trailing 20 sessions' own |disp| values, shifted by one session** — the same
trailing-normalised convention used throughout this project. No full-sample
threshold, nothing computable only in hindsight.

### The free parameter, declared before running

**Which two signals are taken: the first two, chronologically.** Trade 1 is the
first qualifying bar after 09:30. Trade 2 arms only once trade 1 has closed and
is the next qualifying bar. **No ranking, no "strongest" signal, no lookahead.**
First-come-first-served is the only selection rule with zero fitted content, and
it is chosen for that reason rather than because it performed better — it has not
been run.

### Stop, declared and parameter-free

**The session extreme on the protective side as of the entry bar** — session low
for a long, session high for a short. Structural, causal, no tunable constant,
and deliberately the same *kind* of stop as Test 1's opposite IB boundary so the
two families are comparable.

### Exits

Hold-to-close (the specification), plus 1R, 2R, 3R for comparability with Test 1.

## 5. Variant budget

| | new variants |
|---|---|
| Test 1 | **0** — four exits and the two-trade cap were specified |
| Test 2 | **3** — the 1R/2R/3R exits added beside the specified hold-to-close |
| **spent** | **3 of 6** |
| **unspent** | **3** |

## 6. Standing diagnostics, both tests

Trade and session counts before any performance number. Mean and median stop
distance and cost as a % of risk. Mean adverse and favourable excursion. By year.
Excluding the best 1%. At 50% higher cost. Naive fill beside honest with the
correction stated. Entry lookahead check, entry bar excluded, ambiguous bar rate.

## 7. Decision rule, fixed now

A variant survives only if **all five** hold: positive after costs; PF > 1.15;
positive in ≥4 of 6 years; positive after removing the best 1% of trades;
positive at 50% higher cost. **If nothing survives in a family, that family
closes.**

If both families produce survivors, **one candidate freezes from each**: highest
session-level t; if two are within 0.15, prefer the simpler or lower target
multiple.

## 8. Holdout protocol

The **1,259 sessions of QQQ 5-minute, 2016–2020** are read **once**, for both
frozen candidates together, Bonferroni over two tests (α = 0.025 each). No
intermediate readings, no optimisation, no peeking at one while deciding the
other. One candidate → full α = 0.05.

**The minimum detectable effect there will be stated before the holdout is
opened, and if it cannot resolve the discovery effect size that will be said
before spending it, not after.**

Two degradations to note in advance: the holdout is **5-minute bars**, so "which
IB extreme formed first" rests on **12 bars** instead of 60, and its sessions end
**15:55**, not 15:59.

Sealed NQ days are not part of this and are not read.

Committed before either test was run.
