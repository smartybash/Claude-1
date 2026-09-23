# Pre-registration: Minimum Viable Edge Bar for a $50,000 Prop Evaluation

Commit this document before any future candidate search or evaluation purchase.

Any candidate that fails even one mandatory requirement below is not deployed,
regardless of how attractive its backtest, equity curve, win rate, or profit
factor appears.

This document does not authorise a new strategy search. It defines the
commercial standard that every future candidate must clear.

---

## 1. Purpose

The objective is to determine whether a strategy has enough out of sample edge,
trade frequency, and drawdown control to justify purchasing a $50,000 futures
prop evaluation.

The evaluation is a commercial deployment test, not a substitute for strategy
research.

No evaluation fee or personal capital may be committed to a strategy that is
still being developed, filtered, rescaled, or optimised.

---

## 2. Capital structure

| Capital path | Amount | Purpose |
|---|---|---|
| Evaluation research budget | $1,800 | Maximum research and evaluation expense |
| Maximum evaluation attempts | 10 | At approximately $165 per attempt |
| Evaluation fee allocation | $1,650 | Ten attempts at $165 |
| Contingency | $150 | Data, execution, reset, or fee variation |
| Prop account label | $50,000 | Evaluation and funded account proving ground |
| Personal capital | $50,000 | Deployment layer after live validation |

The sequence is mandatory:

1. Strategy clears all analytical requirements.
2. Strategy is tested on the exact selected evaluation program.
3. Strategy is deployed to one live evaluation.
4. Personal capital remains untouched until a live evaluation is passed.
5. Personal and prop deployment must not begin simultaneously.

---

## 3. Exact evaluation specification

Do not test against a generic blend of prop firm rules.

Before evaluating any candidate, identify one exact evaluation product and
freeze its current rules.

Record:

- Evaluation provider
- Account and program name
- Rule verification date
- Profit target
- Drawdown amount
- Drawdown method: intraday trailing, end of day trailing, or static
- Whether the drawdown stops trailing
- Daily loss limit
- Consistency rule and exact calculation
- Minimum trading days
- Maximum trading days, if applicable
- Maximum contract size
- Contract scaling rules
- Overnight position restrictions
- Scheduled news restrictions
- Evaluation fee
- Reset fee
- Recurring subscription fee
- Activation fee after passing
- Funded stage rules
- Payout eligibility conditions

Until an exact program is selected, use the following provisional conservative
specification for research:

| Rule | Provisional value |
|---|---|
| Profit target | $3,000 |
| Maximum trailing drawdown | $2,000 |
| Daily loss limit | $1,000 |
| Consistency limit | No single day above 40% of total evaluation profit |
| Minimum trading days | 10 |
| Planning evaluation fee | $165 |

Final pass probability must be recalculated against the exact selected
evaluation rules before any fee is paid.

---

## 4. The five mandatory analytical bars

### 4.1 Out of sample expectancy

A candidate must demonstrate:

- Net out of sample expectancy of at least **+0.10R per trade** after
  commissions and realistic slippage
- Lower bound of the 90% confidence interval strictly above zero
- At least **150 out of sample trades**
- At least **12 calendar months** of out of sample coverage
- Positive expectancy for both long and short trades if both directions are
  traded

A candidate with fewer than 150 trades may only proceed if a pre registered
power and commercial analysis demonstrates that the available sample can resolve
the required edge. **This exception must be declared before the results are
viewed.**

Formal statistical results belong in an appendix. The main report must lead with
expectancy, drawdown, trade frequency, cost, market stability, and evaluation
viability.

### 4.2 Trade frequency

The strategy must produce:

- Median rolling three month frequency of at least **12 trades per month**
- No rolling three month period below **8 trades per month** unless the strategy
  was structurally inactive for a pre declared reason
- Sufficient live opportunities to complete the evaluation without forcing
  marginal trades

Use rolling trade frequency rather than only the full sample average. A strategy
averaging 12 trades per month historically but currently producing 4 trades per
month is not commercially suitable for an evaluation.

### 4.3 Combined production

Net expected monthly production must be at least **2.0R**:

```
Expected monthly production = median rolling trades per month × net expectancy per trade
```

Expectancy must separately satisfy the +0.10R minimum.

| Trades per month | Expectancy required for 2R monthly | Applicable minimum after the +0.10R floor |
|---|---|---|
| 12 | +0.167R | +0.167R |
| 15 | +0.133R | +0.133R |
| 20 | +0.100R | +0.100R |
| 30 | +0.067R | +0.100R |

A 30 trade per month strategy must still earn at least +0.10R per trade and
would therefore produce at least 3.0R monthly.

### 4.4 Drawdown shape

A candidate must demonstrate:

- Historical out of sample maximum peak to trough drawdown no greater than **6R**
- Monte Carlo 95th percentile maximum drawdown no greater than **7R**
- Maximum historical daily loss compatible with the selected evaluation's daily
  limit
- No single day responsible for more than 40% of total expected evaluation profit
- Drawdown recovery time compatible with the evaluation period and budget

The 7R Monte Carlo limit leaves 1R of operational headroom below an 8R
evaluation breach when risking $250 per R against a $2,000 drawdown.

Do not use the full $2,000 drawdown as an acceptable simulated result. Slippage,
platform differences, delayed fills, and calculation differences require a
buffer.

### 4.5 Evaluation pass probability

The strategy must demonstrate:

- Monte Carlo pass probability of at least **45% per attempt**
- Expected evaluation fee cost to first pass no greater than **$600**
- Acceptable probability of exhausting the ten attempt budget
- Acceptable median and 90th percentile days to pass

Expected evaluation fee cost is:

```
Evaluation fee ÷ pass probability
```

At a $165 fee and 45% pass probability:

```
165 ÷ 0.45 = $366.67
```

This calculation excludes activation, reset, subscription, tax, platform, market
data, and funded stage costs. Report both:

- Evaluation fee cost to first pass
- Total expected cost to first usable funded account

The second calculation must incorporate all known fees.

---

## 5. Cost and execution requirements

A candidate is rejected **before expectancy is assessed** if:

- Expected round trip cost exceeds 10% of initial risk
- Realistic slippage has not been measured or conservatively modelled
- Profit depends on fills at unavailable historical prices
- Same bar stop, target, entry, or reversal ordering is unresolved
- The backtest uses a different execution model from the intended platform
- The strategy relies materially on a small number of extreme fills

Every report must show:

- Gross expectancy
- Commission cost
- Slippage cost
- Net expectancy
- Median cost as a percentage of initial risk
- Result with costs increased by 50%
- Honest fill result beside the naive fill result

---

## 6. Evaluation simulation

Only candidates clearing Sections 4.1 through 4.4 proceed to simulation.

### 6.1 Simulation setup

Before simulation:

- Freeze the exact evaluation program
- Freeze the risk fraction
- Freeze the instruments and contract sizing
- Freeze the cost model
- Freeze the treatment of overnight, news, and restricted periods
- Freeze all risk controls

**No risk fraction or rule may be changed after results are viewed.**

### 6.2 Resampling procedure

**Do not independently resample individual trades.**

Instead:

- Group all out of sample trades by trading day
- Preserve the order of trades within each day
- Preserve same day correlation and daily profit concentration
- Resample complete trading days
- Where sample size permits, use blocks of consecutive trading days to preserve
  winning streaks, losing streaks, volatility clusters, and regime persistence
- Use at least 10,000 simulation paths

### 6.3 Intraday equity path

If the selected evaluation uses an intraday trailing drawdown or intraday daily
loss calculation, closed trade results alone are insufficient.

The simulation must include:

- Actual entry and exit sequence
- Open trade maximum adverse excursion
- Open trade maximum favourable excursion where the trailing drawdown depends on
  peak equity
- Intraday equity peaks
- Intraday drawdown breaches
- Commissions and stressed slippage
- Contract size changes, if the evaluation permits them

If these inputs are unavailable, do not claim to simulate an intraday trailing
evaluation. Select an end of day or static drawdown program, or reject the
candidate as untestable for that program.

### 6.4 Rules enforced in every path

Apply:

- Profit target
- Drawdown method
- Daily loss limit
- Consistency rule
- Minimum trading days
- Maximum contract limit
- News restrictions
- Overnight position restrictions
- Evaluation expiry or billing period, if applicable
- Any scaling or funded stage transition rules relevant to the decision

### 6.5 Required outputs

Report:

- Pass probability
- Probability of failing by drawdown
- Probability of failing by daily loss
- Probability of failing the consistency rule
- Probability of failing through time expiry
- Probability of exhausting ten attempts
- Median attempts to first pass
- 90th percentile attempts to first pass
- Median evaluation fees to first pass
- 90th percentile evaluation fees to first pass
- Total expected cost to first usable funded account
- Median days to pass
- 90th percentile days to pass
- Median maximum drawdown
- 95th percentile maximum drawdown
- Pass probability under 50% higher transaction costs
- Pass probability after reducing expectancy by 25%

---

## 7. Risk fraction

The default evaluation risk fraction is **0.5% of the nominal $50,000 account,
equal to $250 per initial R**.

This risk fraction must be declared before simulation.

A different fraction may be used only if it is selected before simulation and
supported by the strategy's historical adverse excursion and drawdown profile.

**Risk must not be optimised to maximise the simulated pass probability.**

At $250 per R:

- An 8R drawdown equals $2,000
- A 7R operational ceiling equals $1,750
- A 2R monthly expectation equals $500
- A $3,000 target equals 12R

Therefore, a strategy producing 2R monthly would require approximately six
months on expectation to reach the target at 0.5% risk.

Any claim of a materially shorter expected completion time must be supported by
the frozen evaluation simulation rather than simple division.

---

## 8. Mechanism requirement

No strategy qualifies solely because its backtest is positive.

Every candidate must answer:

- Who is on the other side?
- Why are those participants trading?
- Why is the flow price insensitive or structurally disadvantaged?
- Why should the effect persist after costs?
- What observable control would falsify the mechanism?

The mechanism must be tested using at least one pre registered control.

A candidate fails if:

- The control performs similarly to the supposed mechanism
- A shifted or arbitrary reference performs as well as the proposed reference
- The result depends entirely on market drift
- The opposite directional control performs as well or better
- The mechanism effect reverses where it should be strongest

**Controls must never be promoted into new strategies after results are viewed.**

---

## 9. Promotion rule

A candidate is purchased for one live evaluation **if and only if all**
requirements below are satisfied:

- Out of sample expectancy is at least +0.10R after costs
- The 90% confidence interval lower bound is above zero
- At least 150 out of sample trades are available
- At least 12 calendar months are represented
- Median rolling three month trade frequency is at least 12 trades monthly
- Combined expected production is at least 2.0R monthly
- Historical out of sample drawdown is no greater than 6R
- Monte Carlo 95th percentile drawdown is no greater than 7R
- Monte Carlo pass probability is at least 45%
- Round trip cost is no greater than 10% of risk
- Expected evaluation fee cost to pass is no greater than $600
- Total expected cost to the first usable funded account is disclosed and accepted
- The mechanism and falsification control pass
- The exact evaluation rules have been simulated
- No unresolved fill, lookahead, repaint, or intrabar sequencing issue remains

**Failure of any one condition means no evaluation is purchased.**

---

## 10. Live evaluation rules

Once a candidate qualifies:

- Purchase one evaluation only
- Use the frozen strategy and risk fraction
- Do not alter stops, targets, filters, trading hours, or sizing
- Record every trade, including rejected and missed signals
- Record actual commission, slippage, maximum adverse excursion, and maximum
  favourable excursion
- Do not purchase another evaluation until the previous attempt is fully reviewed
- Every failed attempt must be classified by cause: ordinary variance, execution
  error, rule violation, or model failure

---

## 11. Personal capital promotion

Personal capital remains untouched until:

- The strategy passes a live evaluation
- Live execution approximately matches the model
- No serious rule or fill discrepancy is discovered
- The funded stage does not introduce materially different constraints

Personal capital begins at 0.5% risk per trade.

Scaling to 1.0% risk is allowed only after:

- At least 60 live trades
- Positive realised expectancy after costs
- Realised drawdown no greater than 4R
- No material dependence on a few exceptional trades
- No breach of the live execution protocol

---

## 12. Kill conditions

Stop the entire deployment program if:

- The $1,800 research and evaluation budget is exhausted
- Ten evaluation attempts are consumed without a pass
- Two consecutive evaluations breach the trailing drawdown
- Live expectancy becomes nonpositive after a meaningful sample
- Actual execution costs materially exceed the cost model
- The live strategy differs from the tested strategy
- The mechanism control fails in live data

**Do not top up the evaluation budget.**

**Do not relax the requirements to justify another purchase.**

---

## 13. Standing research constraints

- Sealed NQ tape dates remain sealed unless a future pre registration explicitly
  authorises one frozen test
- The 2016 to 2020 QQQ holdout was spent on the IB midpoint pullback validation
  and cannot be reused as out of sample data
- The IB midpoint pullback family remains closed
- No rescaling, refitting, filtering, reversing, or reinterpretation of closed
  families
- Controls are never promoted into strategies
- Discovery data cannot become holdout data
- Any rule change creates a new strategy and requires new out of sample data
- All deliverables must be provided as text and tables in the conversation

---

## 14. Existing ledger implication

Applied to the current strategy ledger, **every family fails**.

Examples:

- The IB midpoint pullback fails trade frequency and failed the untouched QQQ
  holdout economically
- The compression family fails expectancy and mechanism controls
- FOMC produced a stable volatility timing result but no directional expectancy
- No completed family has demonstrated at least +0.10R net out of sample
  expectancy with the required monthly frequency and drawdown shape

This is the intended outcome of a commercial deployment standard.

If no future candidate clears the requirements, the conclusion is:

> The current research process has not identified a strategy capable of passing
> the selected $50,000 evaluation within the available cost, frequency, and
> drawdown constraints.

That conclusion protects both the $50,000 personal capital and the $1,800
evaluation budget.

---

## 15. Required output for every future candidate

Lead with a one page commercial decision table:

| Requirement | Required | Observed | Pass or fail |
|---|---|---|---|
| Net OOS expectancy | ≥ +0.10R | | |
| 90% CI lower bound | > 0 | | |
| OOS trades | ≥ 150 | | |
| OOS duration | ≥ 12 months | | |
| Median rolling frequency | ≥ 12 trades/month | | |
| Expected production | ≥ 2.0R/month | | |
| Historical OOS drawdown | ≤ 6R | | |
| MC 95th percentile drawdown | ≤ 7R | | |
| MC pass probability | ≥ 45% | | |
| Cost as percentage of risk | ≤ 10% | | |
| Expected evaluation fee cost | ≤ $600 | | |
| Mechanism control | Passed | | |
| Fill and execution audit | Passed | | |

Follow with:

1. Trading economics
2. Monthly frequency
3. Drawdown profile
4. Monte Carlo evaluation results
5. Mechanism control
6. Cost and fill audit
7. Formal statistical appendix

End with exactly one verdict:

- **Deploy to one evaluation**
- **Continue research, but do not deploy**
- **Reject and close**

---

Commit this pre registration before any future candidate search or evaluation
simulation. **Do not modify it after viewing candidate results.**

---

## Transcription note

Committed verbatim as supplied. The only change is formatting: several tables
arrived with their header row run into the first data row, and have been
reconstructed as proper tables. No requirement, threshold, or wording has been
altered. Arithmetic in §4.3, §4.5 and §7 was checked on receipt and is correct.
