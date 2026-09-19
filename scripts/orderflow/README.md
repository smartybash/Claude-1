# Order flow — the live line of work

Everything here runs on the ATAS recordings in `data/tape` and `data/depth`.
Scripts read `.csv` and `.csv.gz` interchangeably.

Run them from this folder.

## The pipeline

| Script | What it does |
|---|---|
| `tape.py` | Loads the tick tape and **audits it before handing it on** — aggressor balance, the clock, tick grid, continuity. Also holds the RTH window and the volume profile. |
| `depth_audit.py` | Same for the Level 2 files: duplication, crossed books, snapshot rate, ladder reach, coverage. |
| `book.py` | Rebuilds the order book from the change-only depth format. Carries a **round-trip self-test** — run it directly and it proves the reconstruction is exact before you trust anything built on it. |
| `session_map.py` | Per-session structure from ticks: profile, POC/VAH/VAL, initial balance, CVD, and the levels carried into the next session. |

## The tests, in the order they were run

| Script | Hypothesis | Verdict |
|---|---|---|
| `absorption.py` | Aggression that fails to move price reverses | **Dead.** All four cells of the 2×2 negative. |
| `sweep_tape.py` | ~20 hypotheses over the tape | **Dead**, except one cell that led to the next script. |
| `divergence_audit.py` | CVD divergence at 60m extremes | **Dead.** t fell +5.12 → +1.00 once de-overlapped; the CVD condition added nothing over price alone. |
| `imbalance.py` | Book imbalance predicts direction | **Dead.** +0.09 to +0.26 pts gross against a 2-pt cost. |
| `pull_vs_fill.py` | Size that refills after being hit is real absorption | **Dead** as a signal. Produced one keeper: at the touch, **filled beats cancelled ~5:1**. |
| `levels.py` + `levels_audit.py` | Fading fixed prior-session levels | **Underpowered, not disproven.** See below. |

## Why the audit scripts exist

Three findings in this project looked real and were not. The pattern each time
was the same: overlapping observations inflating the sample, one day carrying
the result, or a control that was never run. `divergence_audit.py` and
`levels_audit.py` exist to attack a positive result before it is believed, and
both succeeded in killing what they were pointed at.

Any new finding goes through the same four questions:

1. How many **independent** observations, after de-overlapping?
2. Do the individual sessions **agree in sign**?
3. Does a **control** without the clever part do just as well?
4. How many trades supply most of the profit?

## Where it stands

`levels.py` is the only live hypothesis. A 15-point stop with a 30-point target
gives +8.52 points at t=+2.51 over 43 de-overlapped trades, and every cell of
the stop/target grid has a positive mean — but per-trade dispersion is 22.3
points, so three sessions cannot resolve anything under 9.9 points per trade.
The effect is below the resolution of the sample. Twelve sessions resolves
5 points, twenty resolves 3.8.
