# Two economic sleeves — result

Registered `reports/econ2_preregistration.md` (87099a2) before any run. Run once on
2026-09-30. Output: `reports/econ2_output.txt`.

**Verdict: both CLOSED at discovery. The holdout (2021-01-01 → 2026-09-24) was not
read, as registered.**

| hypothesis (NQ, discovery 2010-06 → 2020-12) | trades | $/trade | total | null median / 95th pct | p | Holm p |
|---|---|---|---|---|---|---|
| H1 late-day momentum (15:30 → 15:59, direction of the day so far) | 2,627 | +$0.5 | +$1,308 | −$39,152 / −$646 | 0.041 | **0.082** |
| H2 turn-of-month (18:00 → RTH close, sessions −1 … +3) | 508 | +$86 | +$43,634 | +$33,008 / +$90,099 | 0.378 | **0.378** |

## What the numbers say

- **H1: the momentum is there, but costs take all of it.**
  - The signal picks the last half-hour's direction better than chance. The
    random lists, which are charged the same costs, lose $39,152, and the rule
    finishes flat.
  - The gross edge is about 0.75 NQ points a trade ($15), about the size of the
    round-trip cost. After Holm it is not significant, and it earns nothing.
  - The first discovery half lost money (−$14,646). ES loses too (−$35,398).
  - Descriptive only: the gain grows with the size of the day's move (top
    |r| quintile +$29 a trade, bottom −$23), as the hedging-demand mechanism
    predicts. The registration closes H1, so no big-day filter is tried now.
    A filter chosen after seeing this result would be tuning.
  - The Gao et al. first-half-hour predictor lost too: −$3.9 a trade.
- **H2: turn-of-month sessions are not special.**
  - They make +$86 a trade, but random Globex sessions make about +$65, the
    ordinary overnight and intraday drift. The difference is noise.
  - 2020 alone contributes $42,209 of the $43,634 total. ES: +$39 a trade, same
    picture.

## Status

Both are closed; no variants. The holdout stays unread for these hypotheses. The
desk still lacks a higher-frequency sleeve. D3-G (about 21 trades a year) remains
the only surviving candidate, now in paper-tracking.
