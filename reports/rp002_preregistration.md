# RP-002 Opening Auction Inventory Rebalancing — pre-registration

**Stage gate document. No performance computed. No Stage 1 run.**
Subject to `a94e717` (deployment standard) and `84704f8` (clarifications).

---

## 1. Data inventory — measured, not assumed

| Role | Instrument | Dates | Resolution | Status |
|---|---|---|---|---|
| **Discovery** | QQQ | 2021-01-04 → **2024-12-31** | 1-min RTH + ETH 04:00–19:59 | **Available** |
| **Internal validation** | QQQ | **2025-01-02 → 2026-08-31** | same | **Available** |
| Portability | SPY, IWM, IJH, EFA | 2021-01-04 → 2025-12-31 | 1-min **RTH only** | **MISSING ETH — unusable as specified** |
| **Final out-of-sample** | NQ / MNQ | — | 1-min + overnight | **MISSING** |

Measured holdings:

| file | rows | sessions | span | window |
|---|---|---|---|---|
| `QQQ_1m.parquet` | 553,973 | 1,421 | 2021-01-04 → 2026-08-31 | 09:30–15:59 |
| `QQQ_1m_eth.parquet` | 1,268,949 | 1,399 | 2021-01-04 → 2026-08-31 | 04:00–19:59 |
| SPY / IWM / IJH / EFA `_1m` | ~488k each | 1,255 each | 2021-01-04 → 2025-12-31 | **09:30–15:59 only** |
| NQ / ES 5-min | 2,174 each | **15** | 2026-06-17 → 2026-07-06 | — |
| RTY | — | **0** | — | absent |

**Frozen discovery universe = RTH ∩ ETH = 1,399 sessions, 67 months, median 21
sessions/month.** 22 RTH sessions lack ETH coverage and are excluded by rule,
not by inspection. Pre-open (04:00–09:29) coverage is **100% of sessions at ≥120
bars**, median 322, 99.1% at ≥200 — the overnight window is genuinely populated.

**Two gate findings:**

1. **The related instruments have no extended-hours data.** Overnight range,
   close-location-in-range and open-location-in-range all require ETH. The
   portability check is **not executable** until SPY/IWM/IJH/EFA ETH is acquired
   (feasible: same Alpha Vantage route that built QQQ ETH, ~240 monthly pulls).
2. **No NQ history exists.** See §6.

---

## 2. Overnight cleaning — frozen, zero tunable parameters

**Rule: an overnight extreme is admitted only if at least two distinct 1-minute
bars traded at or beyond it.** Operationally, cleaned ON high = second-highest
distinct bar high in 04:00–09:29; cleaned ON low = second-lowest.

Chosen because it has **no free parameter** — no threshold, no k, no MAD, no
window — so it cannot be tuned toward a result. It targets the documented defect
exactly: a range set by *one* print has no confirming second bar. It is mildly
conservative on clean sessions, which is stated here rather than discovered.

Reported before any performance: sessions affected, prints removed, raw vs
cleaned range distributions. **Raw extremes are a data-quality diagnostic only.**

---

## 3. State definitions — frozen, six states, exhaustive and non-overlapping

All measured **direction-adjusted** by `d = sign(overnight return)`. Direction is
preserved as a *reported split* (§11), not a state dimension — a symmetric
mechanism should not need separate states, and splitting it would double the
grid to 12 and halve n per cell.

`q` = percentile of `|overnight return|` within its **trailing 60 sessions**
(causal). `L` = cash open in the directionally-corresponding **outer third** of
the cleaned overnight range.

| state | inventory | open location | role |
|---|---|---|---|
| **S1** | q ≥ 0.67 | outer third | **primary** |
| **S2** | 0.33 ≤ q < 0.67 | outer third | secondary |
| S3 | q < 0.33 | outer third | **inventory control** |
| S4 | q ≥ 0.67 | middle third | **location control** |
| S5 | 0.33 ≤ q < 0.67 | middle third | — |
| S6 | q < 0.33 | middle third | — |

First-15-minute **extension vs rejection** is reported as a within-state split,
not a seventh state — it is what separates continuation from reversal at Stage 2.

---

## 4. Expected firing rate — declared before results

`P(q ≥ 0.67) = 0.333` by construction. `P(L)` is unknown; prior **0.60–0.70**,
rising with q, because a material overnight trend usually leaves the pre-open
close near the extreme and the open near the pre-open close.

| | expected share | expected sessions | expected trades/month |
|---|---|---|---|
| **S1** | **~23%** | **~325** | ~4.9 (both branches) |
| S1 + S2 | ~43% | ~600 | ~9.0 |

**S1 at ~325 sessions clears the ≥300 Stage-2 threshold; it is expected to clear
it by a small margin.** Trade frequency of ~4.9/month qualifies as a **portfolio
component (≥4/month), not a standalone (≥12/month)**. That is stated now, not
after.

---

## 5. Mechanism controls

| control | realised as |
|---|---|
| Without the inventory condition | **S3** (q < 0.33, same location) |
| Opening location shifted to middle | **S4** (same q, middle third) |
| Reversed direction | sign-flipped `d`, whole construction mirrored |
| Random dates matched on overnight volatility | matched-σ random sample |
| Uncleaned overnight extremes | **diagnostic only**, never a trade arm |

Controls are never promoted. Stage 1 stops if S1 does not differ economically
from S3 and S4.

---

## 6. Validation path — the blocking issue

150 OOS trades at the expected **4.9/month is 30.6 months**; at 12/month it is
12.5. **Forward collection alone is a ~2.5–3 year path.**

| path | delivers 150 OOS trades in | verdict |
|---|---|---|
| **Acquire NQ/MNQ 1-min + overnight 2021–2025** | immediately, on the deployment instrument | **the only path under 12 months** |
| Forward collection on NQ | ~31 months at 4.9/month | credible but slow |
| Related instruments | never — it is portability, not out-of-time, and ETH is missing | not OOS |
| QQQ 2016–2020 | **spent** | prohibited |

**Per §3 of `84704f8`, the data that must be obtained is named: NQ (or MNQ)
1-minute history including the overnight session, 2021–2025, with the contract
roll and back-adjustment convention frozen in writing before use.** Acquisition
feasibility is *not* established — Alpha Vantage carries no futures; IBKR holds
futures history but the roll convention is an unresolved specification choice.

---

## 7. Approval requested

| item | as declared above |
|---|---|
| Data roles | §1 — discovery 2021-01→2024-12, internal validation 2025-01→2026-08, 1,399-session universe |
| Overnight cleaning | §2 — two-bar confirmation, zero parameters |
| State definitions | §3 — six states, direction-adjusted, trailing-60 terciles |
| Expected firing rate | §4 — S1 ~23%, ~325 sessions, ~4.9 trades/month |
| Validation path | §6 — **NQ acquisition required, or a ~31-month forward path** |
| Mechanism controls | §5 — S3, S4, reversed, matched-random, raw-as-diagnostic |

**Stage 1 is not authorised by this document.** Three items need a ruling before
it runs: whether to acquire NQ history, whether to acquire ETF extended-hours
data for the portability check, and whether a ~4.9/month portfolio component is
worth the discovery spend given the OOS path length.
