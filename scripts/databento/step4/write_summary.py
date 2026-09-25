#!/usr/bin/env python3
"""Regenerate results/databento_rerun.md from the committed result files.

The static sections summarise the committed result reports; the step-4 table is
built from reports/step4/results.csv, so it can be refreshed after every study.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402

HEAD = """# Databento programme — results

Branch `claude/databento-rerun`. Lifetime Databento spend **$84.54** of the $125
cap (plan $84.54, every job billed at its estimate; ledger
`data/databento_ledger.csv`). Nothing here is promoted on a backtest.

## 1. New studies (a)–(e), against the kill criteria

Kill criteria for (a)–(e): Sharpe ≥ 0.8, profit factor ≥ 1.3, beats the random-direction null at
Holm p ≤ 0.05 (plus Sharpe ≥ buy-and-hold for the overlay). Decisive block
2010–2020, labelled *"never used for this hypothesis; read by other daily
studies, incl. overnight gap base rates"*.

| study | decisive-block result | verdict |
|---|---|---|
| (a) overnight drift overlay, NQ | Sharpe +0.81 = always-overnight +0.81; null p 0.32; buy-and-hold +0.84; PF 1.23 | **killed** (forward data is the only true test) |
| (b) regime switch, strict replication | Sharpe −1.00, PF 0.75, permutation p 0.99 | **closed permanently** |
| (c) Zarattini noise-boundary momentum | ES Sharpe −0.24; NQ +0.61 (null p 0.0006), PF 1.16 | **killed** (closest miss) |
| (d) liquidity sweep PDH/PDL/ONH/ONL | Sharpe −0.69, loses in 9 of 11 years | **killed** |
| (e) gap-and-go / gap-fade / PDH-PDL breakout / intraday Donchian | Sharpe −0.09 / +0.01 / −0.16 / +0.14 | **all killed** |

Details: `reports/db_a_overnight_drift_result.md`, `db_b_regime_switch_result.md`,
`db_cd_result.md`, `db_e_result.md`.

## 2. RP-011 on pull B

**Stopped at the registered quality gate:** 27 of 65 discovery sessions pass
(50 needed). 60 pass everything except the ±2% volume reconciliation to CME
cleared volume, which the tick feed misses by a steady 1–3.5% (block and
spread-leg volume not in the outright feed). No RP-011 window was built.
Decision **P6** in `reports/decisions_pending.md`; the holdout is untouched.
`reports/rp011_stage1_result.md`.

## 3. Power of 3

Specification drafted and waiting for your approval (**P1**). Not tested.

## 4. The repository's closed studies on NQ (step 4)

Pre-registered at `reports/step4_preregistration.md` (inventory
`reports/step4_inventory.csv`), with Clarification 1 (the p entering BH is
one-sided in the profitable direction) and Clarification 2 (BH covers trading
claims only; descriptive studies are judged on their own test). Tape studies use
the 61 discovery sessions; bar studies use NQ 1-minute, full 2010-06-07 →
2026-09-24, with 2021–2026 as the like-for-like line. Costs per side NQ $2.25 +
1 tick, MNQ $0.62 + 1 tick, or the frozen spec's own cost if stricter.

"""

TAIL = """
Per-study output: `reports/step4/<id>_output.txt`; frozen scripts' own output:
`reports/step4/<id>_frozen_output.txt`.

## 5. Next tests

- **P6** decides whether RP-011 runs (and on what footing, given the disclosure
  in its addendum). T18 (RP-010) waits for the same decision.
- Remaining step-4 studies continue in the registered order; BH is computed once,
  when the batch is complete.
- Order-flow hypotheses on the discovery ticks (at most five, provisional) are
  still to be registered.
- **P2** (early November): top-up of fresh sessions from 2026-09-25 as a
  confirmation-only holdout, within the cap.
"""


def fmtn(x, f):
    return "" if pd.isna(x) else format(x, f)


def main():
    d = pd.read_csv(C.RESULTS)
    trade = d[d.p_study.notna() & ~d.id.isin(["T08"])]
    L = [f"Studies reported so far: **{len(d)}** of 63 portable. Trading claims "
         f"with a p: **{len(trade)}**. Frozen pass bar met after NQ costs: "
         f"**{int(d.pass_bar.fillna(False).astype(bool).sum())}**. BH is computed "
         "once, when the batch is complete.", "",
         "| id | study | old verdict | net pt/trade | Sharpe | study p (1-sided, Holm) | new verdict (before BH) |",
         "|---|---|---|---|---|---|---|"]
    for r in d.sort_values("id").itertuples():
        L.append(f"| {r.id} | {r.study} | {r.old_verdict} | {fmtn(r.net_pts, '+.2f')} | "
                 f"{fmtn(r.sharpe, '+.2f')} | {fmtn(r.p_study, '.4f')} | {r.new_verdict_pre_bh} |")
    out = C.ROOT / "results/databento_rerun.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(HEAD + "\n".join(L) + "\n" + TAIL)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
