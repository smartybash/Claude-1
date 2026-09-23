#!/usr/bin/env python3
"""Does the RP-010 closure verdict depend on the sealed dates it should not
have read?

RP-010 Stage 1 (commit 3c5bcff) loaded all nine sealed NQ sessions: eight June
dates as threshold warm-up and 23 July as a full discovery session contributing
6 of 204 events. The seal was stated in every proposal and enforced in no
loader.

This script compares the committed run with a rerun in which
`holdout.is_sealed` excludes them at the loader. It reads only the two harness
outputs; it defines no strategy and computes no expectancy.

A rejection can only be made SAFER by removing data it should not have had, but
"can only" is an argument, not a measurement. This is the measurement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "reports"
HZ = [30, 60, 180, 300, 600, 900]
L = []
p = L.append


def clustered(df, col):
    g = df.groupby("day")[col].mean().dropna()
    if len(g) < 3:
        return np.nan, np.nan, 0
    return float(g.mean()), float(g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))), len(g)


def arm(O):
    E = O[O.is_event]
    d = {}
    for st in ("INITIATIVE", "ABSORPTION"):
        g = E[E.state == st]
        d[st] = g
    d["ORDINARY"] = O[O.state == "ORDINARY"]
    return E, d


def matched_random(O, E):
    pool = O[O.state == "ORDINARY"]
    rows, un = [], 0
    for _, r in E.iterrows():
        c = pool[(pool.day == r.day) & (abs(pool.tod - r.tod) <= 30)
                 & (abs(pool.delta.abs() - abs(r.delta)) <= 0.25 * abs(r.delta))]
        if not len(c):
            un += 1
            continue
        rows.append(c.sample(1, random_state=int(r.tod) % 9973).iloc[0])
    return pd.DataFrame(rows), un


def main():
    A = pd.read_parquet(OUT / "rp010_events.parquet")            # as committed
    B = pd.read_parquet(OUT / "rp010_events_desealed.parquet")   # sealed removed
    WA = pd.read_parquet(OUT / "rp010_windows.parquet")
    WB = pd.read_parquet(OUT / "rp010_windows_desealed.parquet")

    p("RP-010 SENSITIVITY: WITH vs WITHOUT THE SEALED SESSIONS")
    p("  A = committed run (3c5bcff), sealed dates wrongly included")
    p("  B = rerun with holdout.is_sealed enforced at the loader")
    p("  Descriptive only. No strategy, entry, stop, target or expectancy.")
    p("")
    for tag, W in (("A", WA), ("B", WB)):
        lab = W[W.state != "WARMUP"]
        p(f"  {tag}: sessions loaded {W.day.nunique()}  warm-up "
          f"{W[W.state=='WARMUP'].day.nunique()}  discovery {lab.day.nunique()}"
          f"  events {int(W.event.sum())}")
    p("")

    EA, _ = arm(A)
    EB, _ = arm(B)
    p("=== forward outcomes, direction-adjusted NQ points ===")
    p(f"  {'state':<12}{'run':<4}{'n':>6}" + "".join(f"{('r'+str(h)):>10}" for h in HZ))
    for st in ("INITIATIVE", "ABSORPTION", "ORDINARY"):
        for tag, O, E in (("A", A, EA), ("B", B, EB)):
            g = E[E.state == st] if st != "ORDINARY" else O[O.state == "ORDINARY"]
            p(f"  {st:<12}{tag:<4}{len(g):>6}"
              + "".join(f"{g[f'r{h}'].mean():>+10.3f}" for h in HZ))
    p("")
    p("=== buy / sell asymmetry at 900 s ===")
    p(f"  {'state':<12}{'run':<4}{'buy n':>7}{'buy':>10}{'sell n':>8}{'sell':>10}")
    for st in ("INITIATIVE", "ABSORPTION"):
        for tag, E in (("A", EA), ("B", EB)):
            b = E[(E.state == st) & (E.side == "buy")]
            s = E[(E.state == st) & (E.side == "sell")]
            p(f"  {st:<12}{tag:<4}{len(b):>7}{b.r900.mean():>+10.3f}"
              f"{len(s):>8}{s.r900.mean():>+10.3f}")
    p("")
    p("=== load-bearing: single variables vs the combined state, 900 s ===")
    p(f"  {'selector':<34}{'run':<4}{'n':>7}{'r900':>10}")
    for tag, O, E in (("A", A, EA), ("B", B, EB)):
        for nm, g in (("delta magnitude alone", O[O.delta.abs() >= O.delta.abs().quantile(.9)]),
                      ("price progress alone", O[O.ticks.abs() >= O.ticks.abs().quantile(.9)]),
                      ("total volume alone", O[O.total >= O.total.quantile(.9)]),
                      ("impact alone", O[O.tpk >= O.tpk.quantile(.9)]),
                      ("INITIATIVE", E[E.state == "INITIATIVE"]),
                      ("ABSORPTION", E[E.state == "ABSORPTION"])):
            p(f"  {nm:<34}{tag:<4}{len(g):>7}{g.r900.mean():>+10.3f}")
        p("")
    p("=== matched random times (the control that beat the treatment) ===")
    for tag, O, E in (("A", A, EA), ("B", B, EB)):
        M, un = matched_random(O, E)
        p(f"  {tag}  n {len(M)} of {len(E)} ({100*len(M)/len(E):.1f}% coverage)"
          f"  r300 {M.r300.mean():+.3f}  r900 {M.r900.mean():+.3f}")
    p("")
    p("=== concentration: does the one positive cell survive? ===")
    p(f"  {'state':<12}{'hz':<6}{'run':<4}{'clustered':>11}{'t':>7}{'sess':>6}"
      f"{'sess +':>8}{'-best3':>9}{'best3 share':>13}")
    for st in ("INITIATIVE", "ABSORPTION"):
        for h in (300, 900):
            for tag, E in (("A", EA), ("B", EB)):
                g = E[E.state == st]
                col = f"r{h}"
                sess = g.groupby("day")[col].mean().dropna()
                m, t, ns = clustered(g, col)
                o = sess.sort_values(ascending=False)
                b3 = sess.drop(o.index[:3]).mean()
                tot = sess.sum()
                share = (o.iloc[:3].sum() / tot * 100) if tot != 0 else np.nan
                p(f"  {st:<12}{str(h)+'s':<6}{tag:<4}{m:>+11.3f}{t:>+7.2f}"
                  f"{ns:>6}{int((sess>0).sum()):>8}{b3:>+9.3f}{share:>12.1f}%")
    p("")
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp010_desealed_sensitivity.txt").write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
