# Related-instrument check, completed: the family closes

Frozen IB 1R, single trade, run unchanged on **five** instruments over
**2021-01-04 .. 2025-12-31**, 1,255 sessions each. Rule, cost convention,
honest fills and entry-bar exclusion all unchanged from the freeze.

**This is a related-instrument check, not a replication.** Same period as
discovery, so the macro regime is shared and only the instrument differs. A
pass here would have been weaker evidence than a true out-of-period holdout.

**2016–2020 was not read. Sealed NQ days were not read.**

---

## 1. Counts first

| instrument | sessions | qualifying | trades | trade rate |
|---|---|---|---|---|
| SPY | 1,255 | 676 | 600 | 47.8% |
| IWM | 1,255 | 689 | 599 | 47.7% |
| XLK | 1,255 | 673 | 592 | 47.2% |
| IJH | 1,255 | 695 | 615 | 49.0% |
| EFA | 1,255 | 670 | 577 | 46.0% |
| **total** | **6,275** | **3,403** | **2,983** | |

Entry lookahead **0** on every instrument. Ambiguous-bar rate 0.0% except SPY
at 0.2%. Naive-vs-honest fill correction ≤ 0.0003 R everywhere — these are
liquid instruments and the fill assumption is doing no work.

IWM was extended from the partial 2021-01..2023-06 sample to the full five
years; XLK, IJH and EFA were fetched from scratch. All five now cover the
identical 1,255 sessions.

---

## 2. The standard error has to be clustered by date, and that was declared before the numbers

All five instruments trade **the same 1,255 calendar sessions** and are driven
by the same market. Treating 2,983 trades as 2,983 independent observations is
simply wrong — the effective sample is far closer to the number of **dates**.

| | naive per-trade SE | date-clustered SE |
|---|---|---|
| headline set | 0.0148 | **0.0219** |
| all five | 0.0132 | **0.0207** |

The naive SE understates by about **50%**. Every figure below uses the
clustered one.

---

## 3. Per-instrument breakdown

| instrument | mean R | clus SE | PF | t | yrs + | ex-top-1% | +50% cost | med risk | cost/R |
|---|---|---|---|---|---|---|---|---|---|
| SPY | +0.0143 | 0.0326 | 1.04 | +0.44 | 3/5 | +2.6 | +0.0075 | 57.7 bps | 1.16% |
| IWM | +0.0205 | 0.0270 | 1.08 | +0.76 | 3/5 | +6.3 | +0.0171 | 105.9 bps | 0.63% |
| **XLK** | **+0.0637** | 0.0292 | 1.23 | +2.18 | 5/5 | +31.7 | +0.0600 | 99.9 bps | 0.67% |
| IJH | +0.0164 | 0.0277 | 1.06 | +0.59 | 3/5 | +3.1 | +0.0124 | 86.2 bps | 0.77% |
| EFA | +0.0579 | 0.0309 | 1.20 | +1.87 | 5/5 | +27.4 | +0.0500 | 47.8 bps | 1.40% |
| *QQQ, discovery* | *+0.0612* | — | *1.22* | *+2.23* | *5/6* | — | — | — | — |

### XLK is not an independent market, and it is the one that "passes"

**XLK holds the large-cap US technology names that dominate QQQ by weight.**
It is the least independent instrument in the set. It returns +0.0637, within
0.003 R of the QQQ discovery figure of +0.0612 — which is what you would
expect from a largely overlapping basket, and is **not** corroboration. It is
excluded from the headline pooled estimate and reported separately, exactly as
instructed.

Strip XLK out and the three genuinely independent US instruments — SPY, IWM,
IJH — return **+0.0143, +0.0205, +0.0164**. That is a tight cluster at roughly
**one quarter** of the discovery effect, and none is individually distinguishable
from zero.

EFA at +0.0579 is the one real surprise, and it is the least similar market in
the set. Taken with the three flat US instruments it reads as dispersion rather
than signal: a single instrument at +0.058 with SE 0.031 is a ~1.9σ result
before any correction for having looked at five.

---

## 4. The pooled non-QQQ estimate

| set | trades | dates | mean R | clus SE | t | **95% CI** |
|---|---|---|---|---|---|---|
| **HEADLINE — SPY, IWM, IJH, EFA** | 2,391 | 981 | **+0.0269** | 0.0219 | +1.23 | **[−0.0160, +0.0698]** |
| all five, incl. XLK | 2,983 | 1,057 | +0.0342 | 0.0207 | +1.66 | [−0.0063, +0.0747] |

**The headline pooled estimate is +0.0269 R per trade, and its 95% confidence
interval spans zero.** Including XLK — which the instruction says should not be
weighted as a separate market — lifts it to +0.0342 and the interval *still*
spans zero.

The pooled figure is **44% of the discovery effect** (+0.0612). It is not
significantly different from the discovery effect either; nor is it
significantly different from zero. The data cannot separate those two
hypotheses, which is itself the answer.

### One thing found along the way, reported and not acted on

Weighting each **date** equally instead of each **trade** equally moves the
headline estimate from +0.0269 to **+0.0061**. The reason:

| instruments qualifying that date (k) | dates | trades | mean R | share of trades |
|---|---|---|---|---|
| 1 | 266 | 266 | −0.0362 | 11.1% |
| 2 | 267 | 534 | −0.0340 | 22.3% |
| 3 | 201 | 603 | +0.0340 | 25.2% |
| 4 | 247 | 988 | **+0.0725** | 41.3% |

The entire pooled effect sits on the days when most instruments set up at once,
and those days also carry most of the trades, so per-trade weighting flatters
it. **The per-trade figure is the one carried forward**, because it matches the
discovery estimand — expected R per trade taken — and must be comparable to it.

**The k pattern is not actionable and is not being promoted.** It was found in
this data, it is a brand-new free parameter, and k is not knowable at 10:30
without watching four instruments simultaneously. Noting it is honest; trading
it would be exactly the sin the pre-registration discipline exists to prevent.
It does mean the +0.0269 is more fragile than its own confidence interval
suggests.

---

## 5. Implied holdout power at the pooled effect size, one-sided

Sealed holdout 2016–2020: 1,259 sessions. At the discovery trade rate of 48.3%
that is **~608 trades**. One candidate, one test, so no Bonferroni:
**one-sided α = 0.05, z = 1.645**, sd = 0.7175.

*No 2016–2020 data was read to produce this. It is arithmetic.*

| effect assumed | δ R | one-sided power | trades needed for 80% |
|---|---|---|---|
| discovery estimate (in-sample, QQQ) | +0.0612 | 68% | 850 |
| **pooled headline** | **+0.0269** | **24%** | **4,398** |
| — its CI lower bound | −0.0160 | n/a | never |
| — its CI upper bound | +0.0698 | 78% | 653 |
| pooled incl. XLK | +0.0342 | 32% | 2,720 |
| the decision threshold | +0.0500 | 53% | 1,274 |

**MDE on the holdout at 608 trades, one-sided, 80% power: +0.0724 R per trade.**

That is the number that settles it. The holdout can only reliably detect an
effect **larger than the in-sample discovery estimate**. At the pooled
non-QQQ effect size it has **24% power** — it would return a null about three
times in four even if the effect is real at +0.0269, and that null would mean
nothing while having spent the only clean sample in the project.

---

## 6. Applying the decision rule you declared in advance

> *"If the pooled non-QQQ estimate firms toward +0.05 or above with the interval
> excluding zero, the holdout becomes worth spending and I will authorise it.
> If it sits near +0.02 or the interval spans zero, close the family without
> opening 2016 to 2020."*

| condition | required | observed | met? |
|---|---|---|---|
| pooled ≥ +0.05 | +0.0500 | **+0.0269** | **no** |
| interval excludes zero | — | **[−0.0160, +0.0698]** | **no** |

**Both halves of the closing condition are satisfied, and neither half of the
authorising condition is.** The estimate did not firm toward +0.05 — it sits
just above the +0.02 you named as the closing case, and the interval spans zero
whether or not XLK is included.

### The family closes. The holdout stays sealed.

The one instrument that came close to the discovery figure is the one that
overlaps QQQ, which is not evidence. The three independent US instruments land
together near +0.017. The single high non-US reading is not enough to carry a
pooled estimate past its own confidence interval.

---

## 7. Where the ledger stands

| screen | sample | outcome |
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
| calendar classification | 1,418 sessions, 52 tests | closed, 1 of 52, mechanism families flat |
| FOMC family | 48 dates, 20 tests | **decisive pass** — post/pre rv 3.14×, 6 of 6 years |
| IB by rejection, Stages 1–3 | 1,418 sessions | 86% is the geometric identity; Stage 3 marginal |
| reopened families (16:00 ET exit) | 2 tests | IB 1R frozen, +0.0612, t +2.23 |
| **related-instrument check** | **5 instruments, 6,275 sessions, 2,983 trades** | **pooled +0.0269, CI spans zero — CLOSED** |

**2016–2020 remains unread and unspent.** It is still the only clean sample in
the project, and after this it is still worth exactly what it was worth before:
everything, precisely because nothing has been taken from it.

Reproduce: `python3 scripts/orderflow/related_instruments.py`.
Full output in `reports/related_instruments_output.txt`.
