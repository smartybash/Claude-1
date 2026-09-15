#!/usr/bin/env python3
"""Validate the weight rule the two ways that matter before believing it.

The rule returned +7.58 points a trade at 67%, which annualises to something
absurd on a single contract. A number that size found in nine sessions is a
reason for suspicion, not celebration, so this attacks it twice more.

  A  THRESHOLD SENSITIVITY. The 10,000 cutoff came from a tercile of this very
     data. If the mechanism is real, any cutoff that separates heavy from light
     should work and the curve should be a broad plateau. If 10,000 is the only
     value that works, it is a fitted parameter and the result is noise wearing
     a threshold.

  B  LEAVE ONE SESSION OUT. Nine sessions is few enough that one good day could
     carry the whole thing. Dropping each in turn shows whether it does.

Usage: python3 scripts/orderflow/validate_weight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from level_weight import COST_PTS, STOP, TARGET, build                  # noqa
from sweep2 import trade                                                # noqa
from tape import load_all, rth                                          # noqa


def main():
    full = load_all()
    days = {d: rth(f) for d, f in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    keys = sorted(days)
    pairs = [(a, b) for a, b in zip(keys, keys[1:])
             if len(pd.bdate_range(a, b)) == 2]
    T = build(days, pairs)

    print("=" * 82, flush=True)
    print("A  THRESHOLD SENSITIVITY — spike means fitted, plateau means real",
          flush=True)
    print("=" * 82, flush=True)
    print(f"  {'cutoff':>11}{'n':>7}{'mean pt':>10}{'win%':>7}{'t':>7}",
          flush=True)
    for thr in (2000, 4000, 6000, 8000, 10000, 12000, 15000,
                20000, 30000, 50000, 10 ** 9):
        sel = (T.lvl_vol < thr).values
        if sel.sum() < 10:
            continue
        v = trade(days, T, STOP, TARGET, True, sel) - COST_PTS
        if len(v) < 20:
            continue
        t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
        lbl = "no filter" if thr > 10 ** 8 else f"{thr:,}"
        mark = "  <-- frozen" if thr == 10000 else ""
        print(f"  {lbl:>11}{len(v):>7}{v.mean():>10.2f}"
              f"{100*(v>0).mean():>7.1f}{t:>7.2f}{mark}", flush=True)

    print("\n" + "=" * 82, flush=True)
    print("B  LEAVE ONE SESSION OUT", flush=True)
    print("=" * 82, flush=True)
    base = trade(days, T, STOP, TARGET, True, T.light.values) - COST_PTS
    print(f"  all sessions   n={len(base):<4} {base.mean():+7.2f}pt", flush=True)
    for d in sorted(T[T.light].day.unique()):
        v = trade(days, T, STOP, TARGET, True,
                  (T.light & (T.day != d)).values) - COST_PTS
        if len(v) < 10:
            continue
        t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
        print(f"    without {d}  n={len(v):<4} {v.mean():+7.2f}pt  "
              f"win {100*(v>0).mean():4.1f}%  t={t:+5.2f}", flush=True)


if __name__ == "__main__":
    main()
