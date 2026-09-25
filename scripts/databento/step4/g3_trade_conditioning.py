#!/usr/bin/env python3
"""Step 4, G3 -- B19 conditioning existing trade sets on pre-open variables
(trade_conditioning.py at fb2b87e, pre-registered 242c9c4) on NQ.

PORT NOTE (committed before this file first ran)
------------------------------------------------
The frozen script regenerates two frozen trade families (reopen_study Test 1 at
1R-4R, orb_fib continuation ORB15/30 band A) and partitions them by the six
pre-open conditions of preopen.py. Data paths only: reopen_study.SRC and
orb_fib.SRC -> NQ 1-minute 2021 window; orb_fib.BUFFER one QQQ cent -> 0.41 NQ
points (x41); preopen RTH/ETH -> NQ 2021 files (its VIX and FOMC inputs start in
2021, so the whole study runs on 2021-01-04 -> 2026-08-31). Costs: the frozen
cost (2 pt at 30,000 as a fraction of price) is at least 0.83 NQ points
everywhere in this window, above the NQ standard 0.725, so the frozen R is
already costed at the step-4 rule.
Registered bar: n >= 150, mean R > 0, positive after removing max(10, ceil(0.10n)),
>= 4 of 6 years positive, AND the best subset beats the 95th percentile of the
permuted maximum t (5,000 permutations). The p entering BH is the frozen
control's empirical p of the observed maximum (one-sided by construction).
Old verdict: the direction closes (nothing beat the permuted maximum).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def main():
    import orb_fib as OF
    import preopen as PO
    import reopen_study as RS
    RS.SRC = OF.SRC = BL.NQ_2021
    OF.BUFFER = 0.01 * 41.0
    PO.RTH, PO.ETH = BL.NQ_2021, BL.NQ_ETH_2021
    _, txt = C.run_frozen("trade_conditioning", [], "B19_frozen_output.txt")
    tail = "\n".join(txt.splitlines()[-14:])
    print(tail)
    p = re.findall(r"empirical p of the observed max\s+([0-9.]+)", txt)
    beats = re.findall(r"beats the control\?\s+(\S+)", txt)
    obs = re.findall(r"observed best t across all subsets\s+([+\-0-9.]+)", txt)
    sub = re.findall(r"that subset\s+(.+)", txt)
    pv = float(p[-1]) if p else float("nan")
    C.record(dict(id="B19", study="trade conditioning on pre-open variables", primary=(sub[-1].strip() if sub else "n/a"),
                  t=float(obs[-1]) if obs else float("nan"), p_one=pv, p_study=pv,
                  pass_bar=bool(beats and beats[-1].upper().startswith("YES")),
                  old_verdict="direction closes (nothing beat the permuted maximum)",
                  new_verdict_pre_bh=f"beats control: {beats[-1] if beats else 'n/a'}; permutation p {pv:.4f}"))


if __name__ == "__main__":
    main()
