#!/usr/bin/env python3
"""WHAT DO WE ACTUALLY HAVE, PER SESSION.

Re-recording at 0.25 left every date potentially holding two of everything: a
fine recording beside its five-point original, sometimes under the same name
and sometimes not, sometimes gzip and sometimes Brotli. Three separate bugs in
the recorder's bundling then orphaned, duplicated or truncated individual
streams. The result is a data directory that cannot be judged by looking at it.

This judges it. One row per date:

    grid        the smallest price gap in the tape, so 0.25 or 5.00
    streams     which of tape, depth, cumulative and quote are present, at
                what resolution
    rows        tape prints, and whether the cumulative stream's fill count
                matches them -- it should, exactly, because every fill is a
                print and every print is somebody's fill
    verdict     COMPLETE, PARTIAL or COARSE

The fill check is the useful one. A cumulative file can be present, readable,
the right length and still belong to the wrong session; if its fills do not
count out against the tape, something crossed a day boundary.

Usage: python3 scripts/orderflow/inventory.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codec import is_encoded, load_any                                    # noqa
from tape import ROOT, is_full_session, load_all, price_step              # noqa

STREAMS = {
    "tape": ("tape", "TAPE_NQ_{d}", ("price",)),
    "depth": ("depth", "L2_NQ_{d}", ("price",)),
    "cum": ("cum", "CUM_NQ_{d}", ("first_price", "last_price")),
    "bbo": ("bbo", "BBO_NQ_{d}", ("price",)),
}


def best(folder: str, stem: str):
    """The finest file for this stream, or None.

    Encoded files come from the 0.25 era by construction, so they win over an
    unencoded one whatever the extension says -- the first 0.25 recordings
    were written as .csv.gz before the bundler learned to recompress.
    """
    d = ROOT / "data" / folder
    if not d.exists():
        return None
    cands = [p for p in d.iterdir()
             if p.name.startswith(stem) and
             (p.name.endswith(".csv.gz") or p.name.endswith(".csv.br"))]
    if not cands:
        return None
    enc = [p for p in cands if is_encoded(p)]
    pool = enc or cands
    return max(pool, key=lambda p: p.stat().st_size)


def dates() -> list[str]:
    out = set()
    for p in (ROOT / "data" / "tape").iterdir():
        m = re.search(r"(\d{8})", p.name)
        if m:
            out.add(m.group(1))
    return sorted(out)


def main():
    print("=" * 100)
    print("SESSION INVENTORY")
    print("=" * 100)
    print(f"  {'date':<10}{'grid':>6}{'tape rows':>12}{'streams':>26}"
          f"{'fills=prints':>14}{'verdict':>12}")
    counts = {"COMPLETE": 0, "PARTIAL": 0, "COARSE": 0}
    # The tape comes from load_all, not from picking a file here. Several
    # dates hold more than one 0.25 tape -- an early plain-format one and a
    # later encoded one -- and choosing differently from the loader meant this
    # report described a file no study would ever read. 18 June's fill count
    # failing to reconcile was exactly that: the report had one tape, the
    # cumulative stream belonged to another.
    loaded = load_all()
    for d in dates():
        tp = loaded.get(d)
        if tp is None:
            continue
        step = price_step(tp)
        have, fine = [], []
        for name, (folder, stem, _) in STREAMS.items():
            f = best(folder, stem.format(d=d))
            if f is not None:
                have.append(name)
                if is_encoded(f):
                    fine.append(name)

        # every fill is a print and every print is somebody's fill
        fill_ok = "-"
        cf = best("cum", f"CUM_NQ_{d}")
        if cf is not None and is_encoded(cf):
            try:
                c = load_any(cf, ("first_price", "last_price"))
                if "kind" in c.columns:
                    nf = int((c.kind == "F").sum())
                    diff = nf - len(tp)
                    # A handful either way is the session boundary: the two
                    # streams close on different events, so the last order can
                    # fall one side of the cut and its fills the other. A
                    # material gap means a file crossed a day.
                    if abs(diff) <= max(10, len(tp) // 1000):
                        fill_ok = "yes" if diff == 0 else f"{diff:+d}"
                    else:
                        fill_ok = f"NO {diff:+,}"
            except Exception:
                fill_ok = "err"

        if step > 1.0:
            verdict = "COARSE"
        elif len(fine) == 4 and not is_full_session(tp):
            verdict = "HALF DAY"
        elif len(fine) == 4:
            verdict = "COMPLETE"
        else:
            verdict = "PARTIAL"
        counts[verdict] = counts.get(verdict, 0) + 1
        print(f"  {d:<10}{step:>6.2f}{len(tp):>12,}"
              f"{'+'.join(fine) if fine else 'none':>26}"
              f"{fill_ok:>14}{verdict:>12}")

    print()
    for k, v in sorted(counts.items()):
        print(f"  {k:<12}{v}")


if __name__ == "__main__":
    main()
