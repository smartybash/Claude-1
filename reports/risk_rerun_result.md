# Risk-managed rerun of the stop-less rules — result (Phase 1)

Registered `reports/risk_rerun_preregistration.md` (2155a6e) before the run. Run
once on 2026-09-30. Output: `reports/risk_rerun_output.txt`. All data is seen
(2010-06 → 2026-09).

**The risk block**, the same for every rule and fixed in advance:
- a hard stop at entry, 0.5 × ADR20 × √(hold ÷ 390);
- $250 risk per trade, at most 10 micros; a trade that needs more than $250 at
  1 micro is skipped;
- a $500 daily cap;
- micro costs.

The random baselines were run under the same block.

| rule | trades taken (skipped) | $/trade | total | stopped out | p | Holm p | verdict |
|---|---|---|---|---|---|---|---|
| D3-G/A (NQ overnight) | 190 (142) | +$14.8 | +$2,820 | 29% | 0.234 | 1.000 | FAIL |
| D3-G/B | 199 (133) | +$1.9 | +$380 | 17% | 0.523 | 1.000 | FAIL |
| ES-G/A | 264 (77) | +$13.5 | +$3,553 | 30% | 0.143 | 0.857 | FAIL |
| D3P (open → close) | 260 (72) | −$1.7 | −$443 | 49% | 0.597 | 1.000 | FAIL |
| H1 (15:30 → close, daily) | 4,036 (0) | −$12.5 | −$50,345 | 37% | 0.468 | 1.000 | FAIL |
| **H1-B** (15:45 → close, big days) | 424 (0) | +$18.8 | **+$7,953** | 49% | 0.0016 | **0.011** | **PASS** |
| H2 (turn-of-month) | 446 (332) | +$5.3 | +$2,382 | 25% | 0.536 | 1.000 | FAIL |

No trade lost more than $276: the stop and the sizing capped every loss, gaps
included.

## What this changes

1. **D3-G, the one surviving edge, is not tradable at prop size with a proper
   stop.**
   - An overnight NQ hold needs about a 357-point stop at 2026 prices, or $714
     per micro. Every 2024–26 NQ trade exceeds the $250 risk limit and is
     skipped.
   - The trades that could be taken earn nothing special (p 0.23), and the
     2018+ trades lose.
   - The stop-less D3-G stays in paper-tracking only as a record, **flagged:
     not tradable on a 50K account.**
2. **H1-B passes, but look at when it made the money.**
   - 2010–2020, the years its settings were fitted on: +$11,544.
   - 2021–26: **−$3,591**, losing in 2024 (−$4,511), 2025 (−$601) and 2026
     (−$1,457). 2020 alone made +$8,129.
   - The stop does improve it (without one, 2021–26 lost −$12,528), but the
     post-fit years still lose.
   - By the registered rule it goes to forward paper-tracking from 2026-10-01
     (`risk_rerun.py --forward`). **My read: probably a fit to 2020. Only the
     forward record can say otherwise.**
   - Prop simulator: 19% pass within a year against 11% failing. It is the
     first rule where passing beats failing, but the median time to pass is
     179 days.
3. **H1 is bad for a prop account.** It loses 90% of evaluations; the
   simulator's fail rate within a year is 90%.

## Phase 2 (not yet done)

The 13 earlier order-flow and tape studies that were judged on fixed exit times
(T01–T06, T10, T13, T14, T15, B15, B17, B19) saved only point totals, with no
entry times or directions. Putting the risk block on them means changing each
study's code to record its trades, then running the same stop engine on the
tick data (56–61 discovery sessions).
