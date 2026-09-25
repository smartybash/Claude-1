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
- Step 4 is complete except T18 (RP-010), held with P6; B03, B30, A13 not rerun
  (reasons in the table); X01-X08 need depth, options or other instruments.
- OF-1..OF-4 all failed discovery, so none goes to the holdout. The D2 holdout
  is still unread; it is reserved for RP-011 if P6 lets RP-011 run.
- **P7**: whether to register a forward-only test of the three multi-day daily
  effects that replicate on NQ.
- **P2** (early November): top-up of fresh sessions from 2026-09-25 as a
  confirmation-only holdout, within the cap.
"""


def fmtn(x, f):
    return "" if pd.isna(x) else format(x, f)


def main():
    d = pd.read_csv(C.RESULTS)
    trade = d[d.p_study.notna() & ~d.id.isin(["T08"])]
    nbh = int(d.get("in_bh", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    nrev = int(d.get("final_verdict", pd.Series(dtype=str)).astype(str).str.startswith("REVIVED").sum())
    L = [f"**Result: {nrev} of {nbh} trading claims revived after Benjamini-Hochberg (q = 0.05). "
         "Every closed study stays closed on NQ.** Rows reported: "
         f"{len(d)} (tape, bar, archive, descriptive). The closest misses: B15 IB-by-rejection "
         "(+4.6 NQ pt/trade after costs, daily-P&L p 0.054, fails its frozen t > 3) and B31 IB re-entry "
         "(p 0.085). Descriptive replications on NQ: FOMC-afternoon volatility (B01), the opening "
         "block's larger excursions (B02), and mean-reverting VWAP-displacement / cumulative-delta "
         "correlations at 15 minutes (T09) that no frozen trade converts into profit. Archive "
         "positives that replicate (A10 daily FVG, A11 compression breakout, A12 oversold bounce) are "
         "unregistered multi-day effects and cannot be revived; see decision P7.", "",
         "| id | study | old verdict | net pt/trade | Sharpe | study p | BH p | final verdict |",
         "|---|---|---|---|---|---|---|---|"]
    for r in d.sort_values("id").itertuples():
        fv = getattr(r, "final_verdict", r.new_verdict_pre_bh)
        L.append(f"| {r.id} | {r.study} | {r.old_verdict} | {fmtn(r.net_pts, '+.2f')} | "
                 f"{fmtn(r.sharpe, '+.2f')} | {fmtn(r.p_study, '.4f')} | "
                 f"{fmtn(getattr(r, 'p_bh', float('nan')), '.3f')} | {fv} |")
    of = C.ROOT / "reports/of_h_discovery_results.csv"
    if of.exists():
        o = pd.read_csv(of)
        L += ["", "## 4b. Order-flow hypotheses OF-1..OF-4 — discovery (provisional)", "",
              "Pre-registered at `665c1e4` (`reports/orderflow_h_preregistration.md`). Data-inspired "
              "by the step-4 tape reruns, so discovery is a development set; the holdout (read once, "
              "at the very end) and the P2 top-up are the real tests.", "",
              "| hypothesis | trades | net pt/trade | Sharpe | daily-P&L t | Holm p | discovery |",
              "|---|---|---|---|---|---|---|"]
        for r in o.itertuples():
            L.append(f"| {r.hypothesis} | {r.n} | {r.net_pts:+.2f} | {r.sharpe:+.2f} | {r.t_daily:+.2f} | "
                     f"{r.p_holm:.4f} | {'passes (to holdout)' if r.passes else 'fails'} |")
    out = C.ROOT / "results/databento_rerun.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(HEAD + "\n".join(L) + "\n" + TAIL)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
