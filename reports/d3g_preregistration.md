# D3-G (D3's overnight edge inside the Globex session), ES replication, prop-evaluation simulator — pre-registration

**Registered 2026-09-29, before any of the rules below has been computed on any
data.** Approved by the user on 2026-09-29 ("Yes go ahead"). No spend: the NQ and
ES 1-minute bars are already bought. All three tests run on **seen data,
2010-06-07 → 2026-09-24**, and are labelled that way. Pass = the rule joins forward
paper-tracking (from 2026-09-29; first review with the P7 family on 2027-09-25).
Fail = closed. No rule is re-tuned after its run.

## 0. Why, and what is already known

- **D3** (frozen oversold signal, `reports/daily3_preregistration.md` R7): on NQ,
  long from the 15:59 close to the next 15:59 close beats the exposure-matched null
  (seen data, p 0.0016). **D3P** (next RTH open → RTH close) failed (p 0.068,
  `reports/d3p_result.md`). The D3P run showed that on the same signals the
  overnight leg (15:59 → next 09:30 open) averages +19.8 real points and the day
  leg +12.1. So the overnight leg and D3 as a whole are both already seen. **What
  has not been computed** is the leg this test trades: from the 18:00 ET reopen to
  the next RTH close (or open). It leaves out 15:59 → 18:00. It has also never been
  put against a null.
- **Prop compatibility (checked 2026-09-29, third-party summaries, because the
  firms' own sites are blocked from this environment):**
  - **Apex:** flat by 16:59 ET; the trading day runs 18:00 ET → 16:59 ET.
  - **Lucid:** flat by 16:45 ET (auto-close); trading resumes 18:00 ET.
  - **News:** both allow news trading (Apex prohibits straddling a release, which
    this rule never does).

  A position opened at the 18:00 reopen and closed by 15:59 lies inside one
  trading day at both firms, with at least 46 minutes to spare. A Friday signal
  enters at the Sunday 18:00 reopen, so nothing is held over a weekend.
- **ES:** D3 has never been run on ES futures. The archive's oversold study used
  SPY and QQQ daily data (`reports/oversold_long.txt`), which is related but
  different evidence, and is disclosed as seen.

## 1. Data

Databento `GLBX.MDP3` continuous front month, `NQ.v.0` and `ES.v.0`.
- **Signals** use the RTH series and day filter of `scripts/databento/daily3.py`:
  back-adjusted RTH 1-minute bars (`data/clean/step4/{SYM}_1m.parquet`), days with
  ≥ 300 bars, daily open/high/low/close, and the 15:58 close.
- **Globex trades** are priced on the unadjusted all-hours bars
  (`data/clean/bars_1m`). A Globex session starts at 18:00 ET on the prior day;
  its date is the date of its RTH.
- **Rolls:** the continuous contract rolls at 19:00 or 20:00 ET, inside a Globex
  session. A trade open across a roll is rolled at the roll prices in
  `data/clean/rolls/{SYM}_rolls.csv` (old contract's last close, new contract's
  first open) and pays **one extra round trip**. A trade across a roll whose
  prices are stale (`ratio_valid` false, one NQ roll in 2013) is dropped, the
  same way from the actual list and the null.

## 2. The rules (frozen)

**Signal (D3, R7) at 15:59 ET on RTH day i:** the 15:58 bar's close < day i−1's
RTH close, **and** close(i−1) < close(i−2) < close(i−3).

**D3-G/A (NQ primary).** Long 1 contract at the **open of the first bar of the
next Globex session** (normally 18:00 ET on day i). Exit at the **close of that
session's last RTH bar** (normally 15:59 ET; earlier on a half day). No stop, no
target.

**D3-G/B (NQ secondary).** The same entry. Exit at the **open of that session's
first RTH bar** (09:30 ET).

**ES-D3 (ES replication).** D3 exactly as registered for NQ, on ES: long at day
i's RTH close, exit at the next RTH day's close, with a roll paying one extra
round trip.

**ES-G/A (ES replication).** D3-G/A on ES.

The next Globex session is the first session after day i with at least one RTH
bar. A signal whose next session is outside the window is not traded.

**Costs, per round trip** (the step-4 rule: $2.25 commission + 1 tick per side):
- NQ $14.50 (0.725 pt)
- ES $29.50 (0.59 pt)
- Descriptive only: MNQ $2.24, MES $3.74

## 3. Test (Tests 1 and 2)

- **Null:** 5,000 exposure-matched random-entry lists, with the same number of
  trades as the rule.
  - G rules: each random trade is long, enters at the first bar of a uniformly
    random eligible Globex session in the window, exits at that session's RTH
    close (A) or RTH open (B), and pays the same costs and roll treatment.
  - ES-D3: as in the P7 null (hold one RTH day, 15:59 → 15:59, uniformly random
    start day).

  The overnight drift of each market is matched, so a rule that only earns the
  market's overnight drift does not pass.
- **Statistic:** total net P&L in dollars (1 NQ or 1 ES per trade).
  p = (1 + number of random totals ≥ actual) ÷ 5,001. Seed 20260929.
- **Families and pass rule:**
  - **NQ family: D3-G/A and D3-G/B, Holm across the two.**
  - **ES family: ES-D3 and ES-G/A, Holm across the two.**
  - A rule passes if its **total net > 0 and its Holm-adjusted p ≤ 0.05**.
- **Pass →** the rule joins forward paper-tracking. ES-D3 is not prop-compatible,
  so a pass there counts as replication of the mechanism, and the rule is
  paper-tracked for evidence only.
- **Fail →** closed. No other entry times, exits, filters or regimes.
- **Descriptive (cannot change a verdict):**
  - $/trade, win rate, profit factor, Sharpe, max drawdown and worst trade, per
    contract and per micro;
  - the two halves of the window (split at 2018-07-01) and results by year;
  - the 15:59 → 18:00 slice the G rules give up, on the same signals;
  - a check that this code reproduces the registered NQ D3 context result;
  - the correlation of NQ and ES G/A trade P&L on shared signal sessions.

## 4. Test 3: prop-evaluation simulator (descriptive; no pass or fail)

**Purpose:** turn a trade stream into the odds of passing a prop evaluation at
each size. It runs on **every rule that passes Tests 1–2**. If none passes, it runs
on D3-G/A, labelled *failed rule, illustration only*. Later it will also run on
the user's own trades.

**Accounts** (50K, as summarised on 2026-09-29; the user should confirm in their
dashboards):

| account | target | drawdown | daily loss limit | other |
|---|---|---|---|---|
| Apex 50K, intraday trailing | +$3,000 | threshold = peak equity **including open profit** − $2,500; stops rising at $50,100; breached intraday | none | — |
| Apex 50K, EOD | +$3,000 | threshold = peak end-of-day balance − $2,500; stops at $50,100; breached intraday | $1,000: the position is closed at −$1,000 for the day; the account continues | — |
| Lucid Flex 50K | +$3,000 | threshold = peak end-of-day balance − $2,000; stops at $50,100 (assumed); **checked at the close only** | none | 50% consistency: the largest day's profit ≤ 50% of total profit to pass |

**Mechanics:**
- Sizes 1–10 micros (MNQ, or MES for ES rules), fixed through an evaluation.
- The full round-trip cost is charged at entry (conservative).
- Open profit and loss follow the 1-minute bars. Within a bar, the favourable
  extreme is taken **before** the adverse one: the trailing threshold rises
  first, then the bar's low is tested against it (conservative).
- The target is checked on the balance after each trade closes.
- **Starts:** an evaluation starts on every session of the window that has at
  least 365 days of data after it, and runs on the actual history until it passes
  or fails.

**Output**, per account × size:
- P(pass within 30 / 90 / 365 days)
- P(fail within 365 days)
- median days to pass

Test 3 is only a simulator. It cannot make a rule pass or fail.

## 5. Scripts and outputs

Scripts (committed with this file before any run):
- `scripts/databento/d3g.py` (Tests 1–2)
- `scripts/databento/prop_sim.py` (Test 3). Its engine is checked beforehand on
  synthetic trade streams only.

Outputs:
- `reports/d3g_output.txt` and `reports/d3g_result.md`
- `reports/prop_sim_output.txt`
