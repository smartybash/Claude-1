# D3P: prop-compatible oversold bounce — result (seen data)

Registered `reports/d3p_preregistration.md` (ebb6680) before the first run. Run once
on 2026-09-25. Output: `reports/d3p_output.txt`.

**Verdict: FAIL → closed.** The rule makes money after costs, but not
significantly more than random long open-to-close days (p 0.068 > 0.05). It is not
added to paper-tracking and will not be re-tuned.

| | value |
|---|---|
| trades | 339 (21 a year), all long, 1 NQ, flat overnight |
| net per trade | +$228 NQ (+$21.99 MNQ) |
| win rate / profit factor / Sharpe | 50.4% / 1.31 / +0.37 |
| total net | **+$77,229** |
| null (5,000 random long open→close lists) | median +$7,457, 95th percentile +$83,525 |
| **p** | **0.0684** |
| max drawdown | $35,002 per NQ ($3,505 per MNQ) |
| worst single trade | −$11,604 per NQ (−$1,161 per MNQ) |

## What the descriptive lines show (they do not change the verdict)

- **Most of D3's edge is overnight.** On the same signals, D3's overnight leg
  (15:59 close → next RTH open) averages **+19.8 real points** gross, and the
  day leg that D3P trades averages **+12.1**. Being flat overnight gives up the
  larger part of the edge.
- **The two halves disagree.** 2010-06 to 2018-06: +$23 per trade, PF 1.08,
  essentially flat. 2018-07 to 2026-09: +$452 per trade, PF 1.37. 2022 alone
  contributes +$47,490 of the +$77,229 total.
- **MNQ costs:** +$7,455 per MNQ over 16 years.
- **Prop fit:** the worst single day was −$11,604 per NQ, which is larger than
  typical prop daily-loss limits at 1 NQ. At MNQ size it was −$1,161.

## Status

D3 itself (overnight hold) stays in forward paper-tracking, as registered. D3P is
closed.
