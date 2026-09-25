# Step 4 — the repository's closed studies rerun on NQ: pre-registration

Registered **before any closed study is run on Databento data**. The inventory,
with one row per study and its class, is `reports/step4_inventory.csv`. The
rules come from your instruction: frozen specs, no re-tuning, small-sample
closures first, tape studies on discovery sessions only, Benjamini-Hochberg FDR
across the batch, and a revived study needs its own fresh holdout.

## 1. What this batch is, and what it is not

- It is a **replication across instruments**, not a discovery. Every NQ intraday
  day from 2010 to 2026 has already been read by studies (a)–(e)
  (`databento_register.md` §7). **Nothing here is promoted on these results.**
- The question for each study is: **does the closed verdict hold on NQ?** Each
  gets an old verdict, a new verdict, and whether they agree.

## 2. Scope

| class | rows | data |
|---|---|---|
| tape (G1) | T01–T18 | Databento NQ trades, **61 discovery sessions only** (2026-03-02 → 05-29, register §8). The holdout is not touched. |
| bar, small sample (G2) | B01–B03 | NQ 1-minute, job A |
| bar, registered (G3) | B04–B32 | NQ 1-minute, job A |
| bar, archive (G4) | A01–A13 | NQ 1-minute and daily, job A |
| not portable (X) | X01–X08 | reported as not rerun, with the reason (depth, options, other instruments) |
| meta (M) | M01 | audits of other studies, not hypotheses |

**Order:** G1, then G2, then G3, then G4. Within a group, the inventory order.

## 3. Data adapters (fixed now)

- **Bars.** NQ 1-minute RTH bars written in the schema of
  `data/intraday_long/QQQ_1m.parquet`: naive ET timestamps, 09:30–15:59, open,
  high, low, close, volume. An ETH file follows `QQQ_1m_eth.parquet` in the same
  way.
- **Prices** are **ratio back-adjusted** (register data-handling rule) so that
  prior-day levels and ATRs are continuous across rolls. **Dollar P&L** uses the
  unadjusted move: adjusted points ÷ the bar's cumulative adjustment factor.
- **Only bars that exist.** No bar is invented or forward-filled.
- **Tape.** Databento discovery prints in the `tape.load_all()` format: `time`,
  `price`, `volume`, `aggressor` (B → B, A → S), `sign`, `signed`. `time` is
  written as ET + 4 h, so the loader's fixed 13:30–20:00 RTH window lands on
  09:30–16:00 ET all year. That covers the five EST sessions before 2026-03-08.
- **Aggressive orders.** Studies that read ATAS's cumulative-trade stream (T11)
  get Databento's recombined orders (prints grouped by `ts_event` and side).
- **Print granularity.** Databento prints are aggregated per price level within a
  match; ATAS recorded individual fills. Volume and side are identical (see the
  cross-check). Studies that count prints, rather than volume, carry a note saying so.

## 4. Frozen specification

- Each study runs from **its script at the commit that closed it**. Only the
  following may change:
  - the data path;
  - instrument constants (tick 0.25, $20 per point);
  - the cost model (§5);
  - price constants written in QQQ dollars, converted to NQ points by × 41 (the
    NDX/QQQ ratio, about 41 throughout 2010–2026);
  - constants written in ticks, which stay in ticks.
- Every change is listed in a **port note committed before that study runs**.
  The port note also names the study's primary statistic (§6).
- **No threshold, grid, window or filter is re-tuned.** If a study cannot run
  without a design decision beyond these rules, it is marked **not ported**, with
  the reason, and nothing is invented.

## 5. Costs

Per side: **NQ $2.25 + 1 tick** ($5.00), **MNQ $0.62 + 1 tick** ($0.50). If the
frozen spec's own cost is stricter (for example the tape studies' 2.0-point round
trip), the stricter one applies.

## 6. Statistics

- **Primary statistic per study:** its own registered primary test. For an
  unregistered study it is the statistic its closure rested on (named in the port
  note). A grid study is corrected within itself first, with its own frozen
  correction or else Holm, and **the study's p is its smallest adjusted p**.
- **Samples.** Bar studies: primary = **full NQ history, 2010-06-07 →
  2026-09-24**; secondary = the study's original date window, like for like.
  Tape studies: the 61 discovery sessions.
- **Reported for every trading rule:** trade count, Sharpe, CAGR, max drawdown in
  $ per NQ and per MNQ, mean per trade after costs, and the adjusted p. Non-trading
  studies (forecastability, descriptive) report their own statistic.
- **Multiplicity:** Benjamini-Hochberg across every study with a primary p,
  **q = 0.05**, computed once, when the batch is complete.

## 7. Verdicts

- **Stays closed:** BH-adjusted p > 0.05, or the study's own frozen pass bar is
  not met after NQ costs.
- **Revived candidate:** BH-adjusted p ≤ 0.05 **and** the frozen pass bar is met
  on the primary sample after NQ costs. Nothing more. It then needs **its own
  fresh holdout**:
  - bar studies: sessions after 2026-09-24 (the confirmation top-up, P2);
  - tape studies: the D2 tick holdout, read once at the very end together with
    every tick hypothesis.
- **Not ported / not portable:** listed, with the reason.

## 8. Output

Per study: raw output in `reports/step4/<id>_output.txt`. Summary table (old
verdict, new verdict, agreement, statistics, BH-adjusted p) in
`results/databento_rerun.md`.

---

## Clarification 1 — declared after T01–T03 ran, before any BH computation

§6 did not say whether the study p is one- or two-sided. For trading rules, the
p that enters Benjamini-Hochberg is **one-sided in the profitable direction**
(H1: net mean > 0), and a grid study's best cell is the one with the smallest
one-sided Holm-adjusted p. A two-sided p would let significantly losing rules
feed small p-values into BH and loosen the threshold for every other study.
This is stricter than the two-sided reading and changes no verdict of T01–T03:
all three lose after costs. Non-trading studies keep their own registered test.
CAGR for the tape studies uses the NQ RTH close from the daily table as notional.

## Clarification 2 — declared before any BH computation (after G1, before G2)

Benjamini-Hochberg runs over **studies with a trading claim** only. Studies
with no trading claim — descriptive, forecastability or correlation studies
(T09, B01 FOMC, B03, B09, B13 and any like them) — are judged against their own
registered test and reported, but kept out of the BH family. So is T08, whose
frozen design has lookahead and cannot be traded. Reason: a large descriptive
effect (for example FOMC-afternoon volatility) would enter BH with a tiny p and
loosen the threshold for every trading rule. This makes the batch stricter, not
looser.

**Bar-study windows.** The primary sample is the full NQ file (2010-06-07 →
2026-09-24). The like-for-like secondary is 2021-01-04 → 2026-08-31, QQQ's
window; each is written as its own file in the QQQ_1m schema.

## Clarification 3 — declared before any BH computation (after B07 exposed it)

The session-clustered p used so far was the t of **per-session mean** net points
over sessions with a trade. When the number of trades in a session depends on
their outcome — at most two trades, the second only after the first closes, so a
quick loser invites a second trade and a big winner does not — the mean of
session means can be positive while the rule loses money. B07's OR15 SATR1.0 R4.0
showed exactly that: t +5.8 with a pooled −0.54 pt per trade.

From here on, and recomputed for every study already reported, the p for a
trading rule is the **one-sided t-test of daily net P&L** — the per-session sum,
zero on sessions without a trade, over every session in the sample. That is the
test behind the Sharpe ratio, and it is what the repository's own frozen
criteria use ("zero-trade sessions count as zero"). The per-session-mean
statistic stays in the output as a diagnostic only. No BH has been computed.

## Clarification 4 — G4 archive scripts, declared before any of them runs

The thirteen archive rows (A01–A13) were never pre-registered: their scripts are
their only specification, and they carry no registered pass bar. Under §7 a
study can be revived only if its frozen pass bar is met, so **no G4 study can
be revived**, whatever its NQ result. They are rerun for **verdict agreement
only** — the headline statistic each closure rested on, old against new — and
are **kept out of BH** (no registered test). Data: the shared QQQ 5-minute
loader (`backtest_tos_fvg.load_sessions`) and the daily loaders are pointed at
NQ 5-minute RTH bars (built from the NQ 1-minute file) and NQ daily RTH bars
(ratio back-adjusted); price constants written in QQQ dollars are converted
×41 and listed per script; percentage constants are unchanged. Costs as §5.
A script that needs data NQ does not have (gamma, breadth, VIX) runs without
that input only if the script itself treats it as optional; otherwise it is
marked not ported.

## Erratum to the inventory (after G4 ran)

A10 (daily FVG continuation, `0761d41`) and A11 (daily range / compression
breakout, `2fed2b4`) were listed as "rejected". They were not: both were
**positive, unregistered** daily results in this repository. They are reported
as such in the results; the error was in my inventory, not in the studies.
