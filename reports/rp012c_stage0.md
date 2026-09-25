# RP-012C Stage 0 — multi-day swing and overnight risk premium

**Stage 0 and proposal only.** No signed return — overnight, intraday,
close-to-close or conditional — has been computed. The inventory script
(`scripts/orderflow/rp012c_stage0_inventory.py`) measures adjustment, dividends,
splits, missing dates, open fidelity and the **magnitude** of overnight gaps for
risk sizing; it computes nothing directional. Output:
`reports/rp012c_stage0_inventory.txt`. RP-011 stays frozen; forward tape
collection continues independently.

---

## 1. Data inventory

| instrument | file | basis | span | days | dividends | splits |
|---|---|---|---|---|---|---|
| QQQ | `data/qqq_daily_full.json` | **raw** (Alpha Vantage) | 1999-11-01 → 2026-08-13 | 6,736 | not included | 2:1 on **2000-03-20** visible as a jump |
| QQQ | `data/daily_long/QQQ.csv` | **split + dividend adjusted** | 1999-11-01 → 2026-09-11 | 6,756 | included, 89 factor steps, 4/yr | included |
| SPY | `data/spy_daily_full.json` | raw | 1999-11-01 → 2026-08-13 | 6,736 | not included | none |
| SPY | `data/daily_long/SPY.csv` | split + dividend adjusted | 1999-11-01 → 2026-09-11 | 6,756 | included, 108 steps, 4/yr | — |
| IWM | `data/iwm_daily_full.json` | **raw only** | 2000-05-26 → 2026-08-13 | 6,592 | **cannot be verified** | 2:1 on **2005-06-09**, unadjusted — appears as a 5,004 bp "gap" |
| IJH | 1-minute only | split-adjustable (5:1, 2024-02-22) | 2021-01-04 → 2025-12-31 | 1,255 | none on disk | measured |
| EFA | 1-minute only | raw | 2021-01-04 → 2025-12-31 | 1,255 | none on disk | none |
| NQ / MNQ | `nq_daily_3m.json` | live-chart cache | 2026-04-07 → 07-02 | **61** | n/a | n/a |

**Verified by measurement, not assumed:**

- The adjusted QQQ and SPY files apply **the same factor to open and close on
  100.00% of days**, so an adjusted overnight return (open_t / close_{t−1})
  carries the dividend correctly — a long held over an ex-date receives it.
- **Cash open:** the daily "open" matches the 09:30 one-minute bar's open with a
  median difference of **0.00 bps** (p95 0.45–1.57 bps) on 1,254–1,408 days where
  both exist. Cash close is the official close.
- **Missing dates:** QQQ, SPY and IWM share identical date sets. The only calendar
  gaps over 4 days are the 2001-09-11 closure and Hurricane Sandy. No flat or
  zero-open bars.
- **Overnight return availability:** complete for QQQ/SPY 1999–2026 on the
  adjusted basis. **IWM would need an adjusted series before any use**: its raw
  file omits dividends and still shows the unadjusted 2005 split.

**Not on disk and not verifiable here:** NQ/MNQ daily history of any useful
length; a risk-free rate series (needed because ETF returns are total returns,
futures returns are excess returns); short-borrow rates.

**Costs (assumptions, project convention):** ETF round trip $0.017/share —
≈ 0.25–0.35 bps for QQQ/SPY and ≈ 0.8 bps for IWM at 2024–26 prices, and less
when executed as closing and opening auction orders. **Short borrow:** QQQ, SPY
and IWM are general-collateral names; assume ~0.25–0.50%/yr (≈ 0.01–0.02 bps a
night) plus dividends owed on shorts — **an assumption, not a measured rate**.
**NQ/MNQ:** 2.0 points round trip ≈ 0.68 bps; no borrow; financing is embedded
in the futures price, which is why the ETF decomposition must be reported net of
the risk-free rate to be comparable.

### The 4,068 pre-2016 sessions — confirmed, and **not** unread

The count is right: **4,068** QQQ and SPY sessions before 2016 in `daily_long`.
My earlier proposal said they had never been read by any family. **Git history
says otherwise:**

| commit | family | data | what it did |
|---|---|---|---|
| `2fed2b4` 2026-08-14 | daily range breakout | QQQ/SPY/IWM raw 1999–2026 | extended a multi-day breakout backtest to 27 years |
| `0761d41` 2026-08-14 | daily fair-value gap | same | "validated" a daily FVG edge on 27 years |
| `5a5051a` 2026-09-13 | **oversold bounce** | **`daily_long` 1999–2026** | buy after ≥ 3 down closes, sell next close; used 1999–2021 as "out-of-sample" |
| `e6e42c4` 2026-09-14 | gap fill | `daily_long` QQQ+SPY, ~13,500 sessions | gap-size buckets and fill rates across all 27 years |
| `7d58849`, `70449c6` | daily sweeps, strat_lab | 2021–2026 daily, sector basket | Tier-1/Tier-2 daily strategy sweeps |

**Every daily bar of QQQ and SPY from 1999 to 2026 has already influenced
multi-day strategy design in this project.** The oversold bounce is the sharpest
case: a **one-day reversal** result, never closed, described in
`findings_summary.md` as "the one real edge found anywhere in the project", mined
on the exact data and horizon where Mechanism A would test one-day
**continuation**. That is design influence, not a technicality. Recorded in the
ledger (§17) as a repeat of the provenance error I made about 2024–2025.

The **signed unconditional overnight premium** (Mechanism B) does not appear to
have been computed by any prior script or report — RP-002 used overnight return
only as a conditioning variable, and the gap-fill study measured intraday fill
rates. But its data has been read, and the hypothesis itself comes from a
published literature built on these same US index ETFs, so the data cannot be
called untouched for B either.

---

## 2. Prior-use and contamination audit, by block

| block | QQQ / SPY daily | IWM daily | IJH / EFA | status for RP-012C |
|---|---|---|---|---|
| 1999–2015 | range breakout, daily FVG, **oversold bounce** (as its "OOS"), gap fill | range breakout, FVG | none | **examined** |
| 2016–2020 | same families; also the spent intraday OOS | same | none | **examined**; standing rule bars it as OOS |
| 2021–2026 | all of the above + daily sweeps, strat_lab, QQQ-wide intraday work | same | 1-minute studies | **examined** |
| forward, after freeze | — | — | — | **the only untouched block** |

---

## 3. Prop-evaluation overnight rules — Topstep 50K Trading Combine

Selected because its parameters are exactly the provisional specification
already registered in `deployment_standard_preregistration.md` ($3,000 target,
$2,000 trailing drawdown, $1,000 daily loss).

**Verification status, stated plainly:** this environment's network policy
blocks `topstep.com` and `help.topstep.com`, so I could not read the rule pages
directly. The rules below come from web-search results that returned Topstep's
own help-centre articles ("When and What Products Can I Trade?", "What is the
Maximum Loss Limit?", "Trading Combine Parameters", "Daily Loss Limit in the
Trading Combine and Express Funded Account"), corroborated by third-party
summaries. **They must be read from the primary pages and dated before any fee is
paid**, as the deployment standard already requires.

| question | Topstep 50K Trading Combine |
|---|---|
| **overnight holding permitted?** | **No.** All positions must be closed by **3:10 PM CT** each weekday; the risk desk begins flattening at 3:08 PM CT and open orders are cancelled. Applies to the Combine, Express Funded and Live Funded accounts |
| hold through the 16:00–17:00 CT maintenance halt? | **No** — follows from the 3:10 PM CT flat rule |
| hold through scheduled news? | **Not verified.** A "High Risk / High Volatility" risk-adjustment article exists; its content was not read |
| drawdown trails intraday or end of day? | **End of day** — the $2,000 Maximum Loss Limit updates from the end-of-day balance |
| do unrealised gains raise the threshold? | **No** intraday — it trails the closed end-of-day balance — but **unrealised losses count in real time** and breach liquidates immediately |
| do gap losses count against the daily loss rule? | **Moot** — no position can be open across a gap. The $1,000 DLL is optional in the Combine |
| maximum contracts | **5 minis** (equivalently 50 micros) |

**Consequence:** RP-012C **cannot be a Topstep evaluation strategy.** Per your
instruction it is classified as a **potential personal-capital strategy only**,
separate from the $50,000 evaluation framework, and it will **not** be modified to
exit before the close — that would recreate an intraday family.

I have not surveyed other evaluation providers, so I make no claim about whether
any permits overnight futures holds.

---

## 4. Discovery, validation and final out-of-sample blocks

| role | block | status |
|---|---|---|
| discovery | QQQ, SPY adjusted daily **1999-11-01 → 2015-12-31** (4,068 sessions) | **examined** — see §1 |
| internal validation | QQQ, SPY adjusted daily **2016–2020** (1,259) | examined; permitted as *validation*, never as OOS |
| secondary validation | QQQ, SPY adjusted daily **2021-01 → freeze date** | examined |
| **final untouched OOS** | **forward daily bars from the freeze date**, ETF and NQ | **the only untouched block**; ≥ 12 months |

IWM enters only after an adjusted series is acquired and verified. IJH and EFA
daily history before 2021 is not on disk; if acquired it would be a
**portability** test on the same calendar dates, not out-of-time validation
(clarifications §2). Historical NQ daily, if acquired, is **mechanism
confirmation** on overlapping dates, not OOS.

---

## 5. Mechanism definitions — separate, never pooled

### Mechanism B — overnight risk premium (unconditional)

- **Position:** long at the official cash close, flat at the next official cash
  open. Every eligible session. No signal.
- **Decomposition, measured in Stage 1 only:** close→open, open→close, and
  close→close, each on the **adjusted** basis and each **net of the daily
  risk-free rate**, so ETF total returns are comparable with futures excess
  returns.
- **Distinct from long equity exposure only if** the overnight component earns a
  disproportionate share of the return **per unit of risk**. The Stage 1 test is
  return-per-unit-volatility of overnight versus intraday versus full-day
  exposure — not the raw overnight mean, which would be long beta in a time
  slice.
- **Controls:** unconditional 24-hour long; intraday-only long; random direction
  with the same holding windows; weekend versus weekday nights separately;
  scheduled-announcement nights separately.
- **Short side:** the short-overnight mirror is measured, with borrow and
  dividends owed, as a control, not as a candidate.

### Mechanism A — multi-day continuation (conditional)

- **One frozen formation**, declared after this audit and before any outcome:
  the sign of the prior **5-session** close-to-close return, scaled by trailing
  20-session daily volatility, entering at the **next close** — so the signal
  day's move is never in the outcome — held **1, 2, 5 and 10** sessions,
  non-overlapping per instrument.
- **Controls:** unconditional long for the same holding periods; reversed
  direction; random direction; the same signal delayed one day;
  volatility-matched random entry dates.
- **Must improve on unconditional market exposure.** A result explained by
  long-run equity drift does not qualify.
- **Specific conflict to resolve before Stage 1:** the unclosed oversold-bounce
  result is a one-day **reversal** on the same data. A continuation study on that
  data is not independent of it.

---

## 6. Expected frequency

| | per instrument | 150 trades | 12-month data rule |
|---|---|---|---|
| **B**, unconditional overnight | ≈ 21 per month | ≈ 7 months | **binds: 12 months** |
| **A**, 1-day hold | ≈ 10–21 per month depending on signal sparsity | 7–15 months | binds |
| **A**, 5-day hold, non-overlapping | ≈ 4 per month | ≈ 37 months | 3 years |
| **A**, 10-day hold, non-overlapping | ≈ 2 per month | ≈ 75 months | 6 years |

Frequency is **construction arithmetic, not a measurement**. On two ETFs, A's
longer holds cannot produce 150 untouched forward trades in a credible period.
As a portfolio component, B's frequency is sufficient; A's 5–10 day holds are
not.

---

## 7. Cost and gap-risk feasibility

**Cost is not the constraint.** A B round trip costs ≈ 0.25–0.35 bps on
QQQ/SPY (0.68 bps on NQ) against a **median absolute overnight gap of 29–45
bps**.

**Gap risk is the constraint.** Overnight gap *magnitude* in units of trailing
20-day ATR (never signed):

| | median \|gap\| | p99 | max | gap > 1 ATR | gap > 2 ATR |
|---|---|---|---|---|---|
| QQQ 1999–2015 | 38 bp | 339 bp | 968 bp | 1.8% of nights | 0.1% |
| QQQ 2016–2020 | 35 bp | 341 bp | 946 bp | 3.8% | 0.6% |
| QQQ 2021–2026 | 42 bp | 283 bp | 536 bp | 3.5% | 0.2% |
| SPY 2016–2020 | 27 bp | 309 bp | 1,045 bp | 4.4% | 0.6% |
| SPY 2021–2026 | 31 bp | 225 bp | 399 bp | 3.6% | 0.3% |

(IWM's max of 5,004 bp is its unadjusted 2005 split — a data artefact.)

**Implications for risk treatment, all to be modelled in Stage 1:**

- An ETF stop cannot execute overnight; it executes at the next open. **A 1R stop
  at one daily ATR is gapped through on ≈ 2–4% of nights**, and the worst
  recorded gaps are **5.3 ATR** (QQQ, 2015-08-24) and **4.6 ATR** (SPY, 2001-09-17,
  the post-9/11 reopening) — a realised loss of ~5R on an intended 1R. The
  99.9th percentile is 2.3–2.4 ATR. Risk
  must be reported both as intended R and as realised loss after gaps.
- **Weekend gaps are not materially larger in median** (0.97–1.21× weekday), but
  they are three nights of information in one gap.
- **NQ differs structurally:** it trades through the night, so a futures stop can
  execute during Globex except across the **17:00–18:00 ET halt** and the
  **weekend**. Gap-beyond-R risk on NQ is therefore concentrated in weekends and
  thin overnight liquidity, not every night.
- Sizing must come from **daily** volatility and the gap tail, not intraday ATR;
  maximum concurrent risk must count ETF and futures exposure to the same index
  as one position.

---

## 8. Stage 0 kill conditions

| condition | status |
|---|---|
| no untouched validation block exists | **FIRES for all historical data.** Every daily block 1999–2026 has influenced design. Only a **forward** block can be untouched |
| price adjustment or dividend treatment cannot be verified | **passes for QQQ and SPY** (verified); **fails for IWM** until an adjusted series is acquired |
| overnight execution cannot be modelled honestly | **passes** — ETF: next-open fill with measured gap tails; NQ: Globex execution with halt and weekend gaps |
| selected prop program prohibits overnight holding and no personal-capital path is intended | Topstep prohibits it. **Fires unless you intend a personal-capital path** |
| 150 final OOS trades within a credible period | **B: yes** (~7 months, 12-month rule binds). **A at 5–10 day holds: no** (3–6 years) |
| the proposal merely repackages long equity exposure | **B is at risk by construction** — it passes only if overnight return per unit of risk is disproportionate. A must beat unconditional long |

---

## 9. Recommendation

**Not suitable for prop deployment.** The selected program, Topstep 50K,
requires every position flat by 3:10 PM CT.

**Mechanism A: neither.** Every daily bar it would use has already shaped
multi-day strategy design in this project, including an unclosed one-day
reversal result on the same data and horizon. Its forward path to 150 trades at
5–10 day holds is 3–6 years. I recommend **closing Mechanism A at Stage 0**.

**Mechanism B: personal-capital research only, and only as a forward study.** It
has never been measured here, its execution and gap risk can be modelled
honestly, its frequency reaches 150 trades well inside the 12-month rule, and its
data quality is verified for QQQ and SPY. But no untouched *historical* block
exists, so the historical 1999–2026 decomposition can only ever be examined
discovery. If you want to proceed, the honest design is: **freeze B's definition
and the Stage 1 descriptive tables now, run them on examined history as
discovery, and treat 12 months of forward daily data as the only validation.** If
a personal-capital path is not intended, **close RP-012C at Stage 0.**

Stage 1 will not run until separately approved.
