# IB midpoint pullback — CLOSED. Completed research package.

**No further tests on this family.**

---

## Final conclusion

**Discovery.** QQQ IB midpoint pullback with R2 rejection and a 1.5R target
produced **+0.124R expectancy and PF 1.23** during 2021–2025.

**Untouched holdout.** The identical frozen rule produced **+0.0002R expectancy
and PF 1.0003** during 2016–2020 across **132 trades**.

**Stress tests.** Expectancy became **−0.058R** after removing the best five
trades, **−0.121R** after removing the best ten, and **−0.028R** with costs
increased by 50%.

**Verdict: CLOSED. The discovery edge did not reproduce out of time on the same
instrument.**

The changing cost and stop relationship across QQQ price levels is recorded as
**a limitation of the frozen specification, not grounds for modifying and
rerunning it after the holdout.**

---

## Standing prohibitions on this family

- **Do not rescale, refit, filter, reverse, or reinterpret.**
- **Do not reuse 2016–2020 as a holdout for any derivative of this strategy.**
  It is spent. Any future variant needs different out-of-sample data.
- No further tests.

---

## The package

| commit | stage | artefact |
|---|---|---|
| `417a012` | pre-registration | `reports/ib_pullback_preregistration.md` |
| `ebff421` | discovery, 18 variants | `reports/ib_pullback_result.md` · `scripts/orderflow/ib_pullback.py` |
| `1b0299c` | first related-instrument transfer | `reports/ib_pullback_instruments_result.md` · `scripts/orderflow/ib_pullback_instruments.py` |
| `146bcbc` | comparability audit | `reports/ib_pullback_comparability_audit.md` |
| `ec938f9` | native-normalised transfer | `reports/ib_pullback_native_result.md` · `scripts/orderflow/ib_pullback_native.py` |
| `63dc38c` | **holdout, read once** | `reports/ib_pullback_holdout_result.md` · `scripts/orderflow/ib_pullback_holdout.py` · `data/intraday_long/QQQ_1m_holdout.parquet` |

Supporting data: `reports/ib_pullback_output.txt`,
`reports/ib_pullback_variants.csv`,
`reports/ib_pullback_instruments_output.txt`,
`reports/ib_pullback_native_output.txt`,
`reports/ib_pullback_holdout_output.txt`,
`reports/ib_pullback_holdout_trades.csv`.

---

## What the sequence established, in order

1. **The 18-variant discovery** produced one variant meeting all ten stated
   criteria, at a best-of-18 t of 1.58 — a level a random search beats 65% of
   the time.
2. **The first cross-instrument transfer failed**, and the audit showed it was
   **economically mismatched**: NQ futures cost applied to five ETFs, a 6.62×
   spread in true cost as a share of risk.
3. **Native normalisation fixed the mismatch** — the pool moved from −0.046R to
   approximately zero and the comparability spreads collapsed — **and the setup
   was still not portable.**
4. **QQQ remained positive under both implementations**, with all four mechanism
   controls weaker than the base rule, which is why the family was classified
   QQQ-specific and unresolved rather than closed.
5. **The holdout answered it.** +0.124R became +0.0002R on the same instrument,
   out of time, on a rule frozen before the data was read.

---

## Ledger entry

| screen | sample | outcome |
|---|---|---|
| **IB midpoint pullback + R2 rejection, 1.5R target** | QQQ 2021–25: 233 trades · 4 related instruments: 667 trades · QQQ 2016–20 holdout: 132 trades | **CLOSED. Discovery +0.124R / PF 1.23 did not reproduce: holdout +0.0002R / PF 1.0003, negative under all three stress tests. Not portable across SPY, IWM, IJH, EFA after a valid native normalisation. Holdout spent and not reusable for any derivative.** |

**Sealed NQ dates remain unread.**
