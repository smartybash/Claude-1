# Deployment standard — clarifications to interpretation

**The pre-registration at `a94e717` is accepted and UNCHANGED.** This document
records clarifications to how it is to be read. It does not amend, relax or
extend any requirement. Where this document and `a94e717` appear to differ,
`a94e717` governs.

Two of the three implications offered on receipt of the standard were wrong.
They are corrected below rather than quietly dropped.

---

## 1. The next candidate does not need to be high frequency by itself

**Correction to a stated interpretation.** On receiving the standard I wrote that
§4.2 "redirects future search hard: the next candidate has to be a
high-frequency construction by design, not a selective one." **That is wrong,
and the error is not small.**

The deployment requirements apply to **the deployable strategy or portfolio, not
necessarily to each individual setup.**

A low-frequency setup may remain a research candidate if it has:

- Positive and independently validated expectancy
- A distinct mechanism
- Low correlation with the other portfolio components
- A combined portfolio frequency of at least 12 trades per month
- Combined production of at least 2R per month
- Portfolio drawdown within the registered limits

Therefore **do not redirect future research exclusively toward high-frequency
systems.** Doing so would repeat the earlier mistake of forcing the research
methodology to fit the deployment constraint — the constraint is a gate on what
gets deployed, not a specification for what gets studied.

Search may consider:

| structure | per-component frequency |
|---|---|
| One strategy | ≥ 12 trades per month |
| Two independent strategies | ≥ 6 trades per month each |
| Three independent strategies | ≥ 4 trades per month each |

The combined portfolio must still satisfy the expectancy, production, cost,
drawdown, pass probability, mechanism and execution requirements.

**Do not pool losing or unvalidated strategies merely to manufacture frequency.**

---

## 2. Related instruments are not automatically out-of-sample validation

**Correction to a stated interpretation.** I described SPY/IWM/IJH/EFA as "the
cheapest genuine OOS block left." **Too loose.** They are untouched as a
designated holdout for a new family, but being untouched is necessary and not
sufficient.

Those instruments are genuine out-of-sample data **only if**:

- The rule is fully frozen before any of those instruments are examined
- No parameter, threshold or mechanism decision was influenced by earlier studies
  on those instruments
- The proposed mechanism is expected to transfer across those instruments
- The economic definitions are instrument-native and comparable

**If the hypothesis is specifically about NQ or Nasdaq microstructure, unrelated
ETF performance is a portability test, not a replacement for out-of-time
validation on the intended instrument.**

Before every future search the pre-registration must explicitly designate:

- Discovery data
- Validation data
- Final out-of-sample data
- Intended deployment instrument
- Whether related instruments are being used for **validation**, **portability**
  or **mechanism testing**

**Data cannot change roles after results are viewed.**

---

## 3. The out-of-sample requirement must shape the research design before discovery

A future candidate requiring 150 out-of-sample trades **cannot be discovered
first and then have a convenient holdout found afterwards.**

Before any new family is tested:

1. Confirm that an untouched sample capable of producing at least 150 trades
   exists
2. Confirm that the sample covers at least 12 months
3. Estimate likely out-of-sample trade count from the rule's intended frequency
4. Confirm that the sample can evaluate the selected prop rules
5. **Reject the research proposal before discovery if no credible validation path
   exists**

Forward collection remains valid but is **not** the only path. New historical
data, a properly designated period on the deployment instrument, or a genuinely
transferable related-instrument sample may also be used.

> This is the rule that would have prevented the 2016–2020 situation: a family
> discovered first, then a holdout sourced to validate it, then the only clean
> block spent. Step 1 now precedes discovery, not follows it.

---

## 4. No immediate strategy search is authorised

The pre-registration defines the deployment standard. **It does not mean the next
task is to generate a high-frequency strategy.**

Before proposing any future candidate, provide a one-page research proposal
containing:

| Item | Required answer |
|---|---|
| Intended instrument | What will actually be traded |
| Mechanism | Who is on the other side and why |
| Expected frequency | Per month, before testing |
| Expected cost/risk | Before testing |
| Discovery sample | Exact files and dates |
| Validation sample | Exact files and dates |
| Final OOS sample | Exact files and dates |
| Expected OOS trades | Must support the registered requirement |
| Execution model | Entry, stop, target and intrabar ordering |
| Prop compatibility | News, overnight, contract and drawdown rules |
| Kill control | What result would falsify the mechanism |

**Do not run performance until the research proposal proves that a valid
deployment and validation path exists.**

---

## 5. Ledger updates

Recorded here, without editing the committed pre-registration:

| | status |
|---|---|
| 2016–2020 QQQ holdout | **Spent** on the IB midpoint pullback validation (`63dc38c`) |
| FOMC volatility result | **Descriptive only** — post/pre realised-vol ratio 3.14×, 6 of 6 years; not a trade rule |
| FOMC long straddle | **Negative and closed** (`c7aad00`) — −3.54% of premium paired, −6.89% unpaired, n=39 |
| Existing families | **None qualifies** under the deployment standard |
| Current candidates | **None authorised** for an evaluation |

---

## Status

No search is authorised. No candidate is proposed. No performance will be run
until a research proposal per §4 above demonstrates a valid deployment and
validation path.

---

## Transcription note

Clarifications recorded as supplied. The research proposal table in §4 arrived
with its header row run into the first data row and has been reconstructed as a
proper table. No requirement or wording has been altered. The corrections in §1
and §2 are to my own earlier interpretation, not to the standard.
