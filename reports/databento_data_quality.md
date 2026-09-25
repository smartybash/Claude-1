# Databento data-quality note

Pull: `GLBX.MDP3`, jobs A, B1, B2, B3, C: all done. Lifetime billed
**$84.54**, exactly the approved plan. Built by `scripts/databento/build_derived.py`;
cross-check by `scripts/databento/atas_xcheck.py`. **Only statistics are committed**
— the repository is public, so no Databento prices or volumes (decision P3 pending).

## 1-minute bars (job A), 2010-06-07 → 2026-09-24

| | NQ | ES |
|---|---|---|
| rows | 5,524,493 | 5,699,283 |
| Globex sessions | 4,199 | 4,199 |
| duplicates · bad OHLC · off-tick prices · zero-volume bars | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| rolls (instrument_id changes) | 66 | 66 |
| rolls failing the ≤ 5-minute ratio rule | 1 (2013-03-12, 6-minute gap, ratio 0.9986, left unadjusted) | 0 |
| short sessions | 128 | 128 |

- **Roll switches** happen with a median 1-minute gap between the old contract's last
  bar and the new one's first, so the ratio back-adjustment is clean.
- **Short sessions** = CME's abbreviated sessions on stock-market holidays (halt
  12:59 ET) plus the true half days (13:14 ET). All excluded from trading.
- **Bad prints:** four isolated 1-minute closes moved more than 1% against both
  neighbours. All four are genuine: the reopen after the 2018-12-05 closure, the
  2020-03-16 limit-down open, and the 2022-12-13 CPI release (two bars).
- **No bars invented:** minutes without trades have no bar. 5-minute and daily bars
  are built only from bars that exist.

## Ticks (jobs B1 discovery, B2 holdout)

| | discovery (2026-03-02 → 05-29) | holdout (2026-08-21 → 09-24) |
|---|---|---|
| prints | 24,855,765 | 8,313,095 |
| recombined aggressor orders | 21,374,417 (1.16 prints each) | 7,290,362 (1.14) |
| side A · B · N | 50.05% · 49.95% · 0.0003% | 50.03% · 49.97% · 0.0003% |
| sessions | 65 | 25 |
| big-order threshold (discovery 99th pct) | **10 contracts** | same threshold |
| footprint RTH volume vs tick RTH volume | **25,084,439 = 25,084,439** | reconciled by construction |

- **Side N** (83 prints in discovery): 65 at the 18:00 ET Globex reopen, a few at
  07:05, 08:30 and 18:3x, **one in RTH** (a 09:30 open).
- **Recombination** (prints sharing instrument, `ts_event` and side → one order):
  **75.1%** of multi-print orders share a single CME sequence number, and **2,000 of
  2,000** sampled move monotonically in the aggressor's direction. That is one
  aggressive order walking the book.

### Sessions excluded from every tick hypothesis — rule registered before any

| window | session | reason |
|---|---|---|
| discovery | 2026-04-03 | Good Friday, no RTH |
| discovery | 2026-05-25 | Memorial Day short session |
| discovery | **2026-03-16, 2026-03-17** | **roll lag**: RTH prints 129,013 and 37,733 against a median of 269,638 — the continuous series still tracks the expiring contract |
| holdout | 2026-09-07 | Labor Day short session |
| holdout | **2026-09-15** | **roll lag**: 42,378 against a median of 250,376 |

**Rule:** a session is excluded if its continuous-contract RTH print count is below
50% of the window median, or if it is a short or holiday session. Discovery keeps
**61** sessions and the holdout **23**. The rule will be re-checked against the
statistics schema (job C) daily volume when C lands.

## ATAS cross-check (job B3, data-quality only)

| | 06-24 | 07-09 | 07-29 | 08-06 | 08-19 |
|---|---|---|---|---|---|
| RTH volume ATAS / Databento | 461,075 / 461,023 | 318,495 / 318,468 | 579,762 / 579,744 | 400,310 / 400,309 | 391,358 / 391,356 |
| per-minute volume correlation | 0.999997 | 0.999999 | 0.999999 | 1.000000 | 1.000000 |
| clock offset | 0 s | 0 s | 0 s | 0 s | 0 s |
| footprint agreement, **B = buy** | 99.99% | 99.99% | 99.99% | 100.00% | 100.00% |
| footprint agreement, A = buy | 61.9% | 63.5% | 66.2% | 65.0% | 66.7% |

**Side convention confirmed empirically: B = buy aggressor, A = sell aggressor.**
ATAS records individual fills (428k prints on 06-24); Databento aggregates per price
level within a match event (348k), and recombination gives 288k aggressor orders.
The RP-010 aggressor labels, which came from ATAS, are corroborated by an
independent feed. All five sessions agree; zero side-N prints in any of them.
