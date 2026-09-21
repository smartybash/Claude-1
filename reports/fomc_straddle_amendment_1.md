# FOMC straddle — Amendment 1, declared before the run

Amends `reports/fomc_straddle_preregistration.md` (`a971882`). The original is
left intact; this document is the record of what changed and why.

**Nothing here was informed by any P&L.** No event P&L has been computed beyond
the single disclosed plumbing probe in §10 of the pre-registration.

---

## A. A specification error in the pre-registration, found and corrected

§4 fixed entry to **Tuesday close** and exit to **Wednesday close**, and §9 set a
verification gate requiring **every announcement date to be a Wednesday.**

**That gate is wrong and would have rejected a valid event.**
**2024-11-07 is a Thursday.** The November 2024 meeting was moved to Wed–Thu
around the 5 November election. The same shift occurs twice in the OOS block:

| event | weekday | cause | same-week Friday | exit DTE |
|---|---|---|---|---|
| 2018-11-08 | Thursday | 6 Nov midterm | 2018-11-09 | **1** |
| 2020-11-05 | Thursday | 3 Nov election | 2020-11-06 | **1** |
| 2024-11-07 | Thursday | 5 Nov election | 2024-11-08 | **1** |

All other 81 events are Wednesdays with exit DTE 2.

### Corrected definition — announcement-relative, not weekday-hardcoded

| | |
|---|---|
| **Entry** | close of the **trading session immediately preceding the announcement day** |
| **Exit** | close of the **announcement day** |
| Expiry | **Friday of the announcement week** (unchanged) |
| Placebos | ±1 week from the announcement date, **preserving its weekday** — a Thursday event takes Thursday placebos |

This reduces to Tuesday→Wednesday for 81 of 84 events and is correct for all 84.

### Verification gate, corrected

Every announcement date must be a **Wednesday, or a Thursday in an election or
midterm week**. Any other weekday halts the run and is enumerated. Every date
must be a valid QQQ session; the count must be 8 per year.

### The DTE inhomogeneity is reported, not filtered

The three Thursday events exit at DTE 1 rather than 2, which is a materially
different gamma/theta profile. **They remain in the sample** — dropping events
is a filter and this desk does not filter. The Thursday/Wednesday split is
**reported as a diagnostic and excluded from promotion**, on the same footing as
the quarterly-expiry split and the concentration diagnostic. It is not a
decision arm and must not become a subset search.

---

## B. Provenance of the 2016–2020 event dates

`data/events/fomc.csv` holds no pre-2021 dates. Every external source is
unreachable from this environment:

| source | result |
|---|---|
| `federalreserve.gov` historical FOMC calendars | **egress-blocked** (curl and WebFetch) |
| `cdn.alphavantage.co` | **egress-blocked** |
| FMP `economics-calendar` | **plan-gated**, access denied |
| Alpha Vantage `FEDERAL_FUNDS_RATE` | monthly rate series; **contains no meeting dates** |

The dates are therefore **recalled, and the recall method is validated rather
than assumed.**

### The validation, and why it is not circular

The 2021–2026 dates were recalled **independently and then diffed against the
existing `fomc.csv`**, which was built from a source and not from recall:

| check | result |
|---|---|
| recalled 2021–2026 events | 45 |
| file events in span | 45 |
| missing from recall | **none** |
| invented by recall | **none** |
| **exact match** | **True — 45/45** |

An adjacent block of the same length, reproduced exactly. Structural checks on
the recalled 2016–2020 set:

| check | result |
|---|---|
| event count | **40 (8.0/yr)** |
| all valid QQQ sessions | **yes**, checked against `QQQ_5m.parquet` |
| inter-meeting gaps | **5.9 – 8.0 weeks** (mean 6.5), consistent with 8/yr |
| non-Wednesday | exactly the two predicted election-week shifts |

**Explicitly ruled out: validating event dates against realised volatility.**
Selecting dates by a vol signature and then testing whether options underprice
realised moves on those dates would contaminate the estimand. No date was
checked against price behaviour of any kind.

**Recorded as a limitation:** the 2016–2020 dates are recall-sourced with
structural verification, not source-verified. If any later result depends on a
single event, that event's date is to be confirmed before the result is claimed.

### Frozen 2016–2020 event set (40 announced, 39 used)

```
2016  01-27  03-16  04-27  06-15  07-27  09-21  11-02  12-14
2017  02-01  03-15  05-03  06-14  07-26  09-20  11-01  12-13
2018  01-31  03-21  05-02  06-13  08-01  09-26  11-08* 12-19
2019  01-30  03-20  05-01  06-19  07-31  09-18  10-30  12-11
2020  01-29  03-18† 04-29  06-10  07-29  09-16  11-05* 12-16
                                              * Thursday   † excluded
```

**2020-03-18 is excluded** per §9 of the pre-registration: the scheduled
17–18 March meeting was cancelled and the action was the emergency Sunday cut of
15 March, announced outside market hours. **2020 contributes 7 events.**

**Final counts: discovery 45 · OOS 39 · pooled 84.**

---

## C. Data plumbing — resolved, recorded for reproducibility

`HISTORICAL_OPTIONS` with an `expiration` filter returns ~40KB inline, which is
too expensive to repeat at scale. **Called with `return_full_data=true` and no
expiration filter**, the full chain (~1.0MB, 7,000 rows, 29 expirations) exceeds
the response limit and is written to the MCP `tool-results` directory at ~300
tokens. Verified end to end on 2024-09-17: the ATM extraction reproduces the
individually-pulled quotes exactly (474 call 4.72/4.75, put 4.76/4.79).

**Budget: one call per date.** Discovery 45 events × 2 dates + 90 placebos × 2
dates = 270; OOS 39 × 2 + 78 × 2 = 234. **~504 date-pulls ≈ 150k tokens** for the
±1-week design. The ±2-week robustness diagnostic would add ~504 more and is run
only if it does not displace the primary result.

Raw chains are parsed to the two ATM contracts and discarded, so disk stays
bounded.

---

## D. Unchanged

Everything else in `a971882` stands: one grid point · `r_exec` headline with
`r_mid` beside · RV/IV diagnostic only · placebo-estimated σ · the ρ > 0.25
paired/unpaired switch · two-stage discovery-then-OOS with pooled promotion and
OOS sign agreement · the one-sided promotion rule · no strangle, delta overlay,
VIX filter, skew tilt or moneyness search · **after this test, no future family
uses 2016–2020 as OOS.**

---

Committed before `scripts/orderflow/fomc_straddle.py` was written or run.
