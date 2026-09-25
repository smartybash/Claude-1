# Archive — hypotheses that were tested and rejected

These are kept as the record, not as working tools. Every one was run,
measured, and failed. They are here so that a question already answered is not
answered again, and so the rejections can be re-checked.

The full write-up of what each showed is in `reports/findings_summary.md`.

Headline rejections, with the reason:

- **Value-area fade** — the original result, +0.334R at t=+3.80, was destroyed
  by a **lookahead bias**: entry was taken at the level price while the
  condition required the bar to close back through it. Corrected, the edge
  vanished (−0.047R). Everything built on that number went with it.
- **A+ setup permutations** (`backtest_aplus*.py`) — stop sweeps, flow filters,
  retest entries. Best out-of-sample cell was negative.
- **1-minute versus 5-minute levels** — fading improves with finer bars but
  never turns positive.
- **Intraday streaks** (`backtest_15m_streak.py`) — the daily oversold
  mechanism does not survive being put on an intraday clock, because the edge
  scales with bar volatility while costs do not.
- **Opening range, initial balance, FVG, sweep-reclaim, gamma and skew
  filters, breadth, cross-market vetoes** — all measured, none cleared the bar.

The one daily-bar survivor, the 27-year oversold-bounce study
(`backtest_oversold_long.py`), is real but holds overnight and fires about
twice a month, which does not serve a day trader.
