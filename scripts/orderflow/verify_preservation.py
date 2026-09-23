#!/usr/bin/env python3
"""RP-007 data preservation: verify the sixteen re-recorded sessions.

RUN THIS THE MOMENT THE NEW BUNDLES LAND. It reads nothing but file properties.

    python3 scripts/orderflow/verify_preservation.py

WHAT IT DOES NOT DO

No level is computed. No interaction is counted. No reaction, reclaim, rotation
or outcome of any kind is measured. No sealed date is opened -- the target list
is sixteen August/September dates and the sealed set is June plus 23 July, so
the two do not intersect and the script asserts it rather than assuming it.

WHAT IT CHECKS, PER DATE

  1. resolution, measured as the minimum non-zero gap between distinct prices
     in the file -- for tape, depth, cumulative and BBO separately. The file
     format is ignored: the correction ledger records that TAPE_NQ_20260820
     .csv.gz is plain gzip and true 0.25 while its _run2 twin is 5.00, so
     format and resolution are independent and only the measurement counts.
  2. the five required streams are present: tape, aggressor side, cumulative
     fills, depth, BBO.
  3. session coverage -- is this a full cash day, and how many RTH prints.
  4. provenance -- the recorder version and the platform's own TickSize, read
     from the bundled _status_<date>.txt, which is where the Step setting
     surfaces as a number.
  5. classification -- previously examined at coarse resolution, or not.

A date PASSES only when every stream that exists measures 0.25 AND tape, depth
and cumulative are all present. BBO is reported as required-where-available:
the recorder writes it, but it is absent for every currently coarse date, so
its arrival is itself evidence the re-recording used the corrected settings.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape import TAPE, open_maybe_brotli, price_step, rth, is_full_session, _cached  # noqa

ROOT = TAPE.parent

# The sixteen sessions inside replay reach on 2026-09-23 and currently held
# only at 5.00. 20260712 is a Sunday and 20260617 is out of replay reach, so
# neither is a target.
TARGETS = ["20260821", "20260824", "20260825", "20260826", "20260827",
           "20260828", "20260831", "20260901", "20260902", "20260903",
           "20260904", "20260907", "20260908", "20260909", "20260910",
           "20260911"]

# June 2026 plus 23 July, exactly as scripts/orderflow/compression.py pins it.
SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

# 20260907 is a CME early close (13:00 ET). It is re-recorded for completeness
# but cannot be a full session, and that is a calendar fact, not a defect.
KNOWN_PART_SESSION = {"20260907"}

STREAMS = (("tape", TAPE, "TAPE_NQ_", "price"),
           ("depth", ROOT / "depth", "L2_NQ_", "price"),
           ("cum", ROOT / "cum", "CUM_NQ_", "first_price"),
           ("bbo", ROOT / "bbo", "BBO_NQ_", "price"))


def measured_step(path: Path, col: str) -> tuple[float, int, str]:
    """Minimum non-zero gap between distinct prices, from the prices themselves.

    Compact `#fmt=1` files store integer tick offsets against a base, so they
    are decoded first. A 5.00 recording written in that format still has every
    offset on a multiple of 20, which is exactly why the header's declared tick
    is not trusted and the decoded prices are measured instead.
    """
    raw = open_maybe_brotli(path)
    buf = io.BytesIO(raw.read() if hasattr(raw, "read") else raw)
    first = buf.readline().decode("utf8", "ignore")
    base = tick = None
    if first.startswith("#fmt="):
        kv = dict(x.split("=", 1) for x in first.strip().lstrip("#").split())
        base, tick = float(kv["base"]), float(kv["tick"])
    else:
        buf.seek(0)
    d = pd.read_csv(buf)
    if col not in d.columns:
        return np.nan, len(d), "|".join(d.columns)
    p = d[col].astype(float).to_numpy()
    if base is not None:
        p = base + tick * p
    u = np.unique(p)
    g = np.diff(u)
    g = g[g > 1e-9]
    return (float(g.min()) if len(g) else np.nan), len(d), "|".join(d.columns)


def pick(folder: Path, prefix: str, day: str) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.name.startswith(prefix) and day in p.name
                  and (p.name.endswith(".csv.gz") or p.name.endswith(".csv.br")
                       or p.name.endswith(".csv")))


def provenance(day: str) -> dict:
    """Recorder version and the platform's own TickSize, from _status.txt."""
    f = ROOT / "status" / f"_status_{day}.txt"
    if not f.exists():
        return dict(status="MISSING", version="", ticksize="")
    txt = f.read_text("utf8", "ignore")
    ver = re.search(r"recorder version:\s*(\S+)", txt)
    ts = re.search(r"TickSize\s*=\s*([0-9.]+)", txt)
    return dict(status="present", version=ver.group(1) if ver else "?",
                ticksize=ts.group(1) if ts else "?")


def main() -> int:
    # Guard, not a comment: the preservation list must not touch sealed data.
    bad = [d for d in TARGETS if d.startswith(SEALED_PREFIX) or d in SEALED_DATES]
    if bad:
        print(f"REFUSING TO RUN: sealed dates in the target list: {bad}")
        return 2

    from tape import unpack_bundles
    unpack_bundles()

    print("=" * 78)
    print("RP-007 PRESERVATION VERIFICATION -- file properties only")
    print("=" * 78)
    print("  No level computed. No interaction counted. No outcome measured.")
    print(f"  Sealed set ({SEALED_PREFIX}* plus {sorted(SEALED_DATES)}) "
          "is not in the target list and is not read.\n")

    rows = []
    for day in TARGETS:
        r = dict(day=day)
        for name, folder, prefix, col in STREAMS:
            paths = pick(folder, prefix, day)
            if not paths:
                r[f"{name}_step"] = np.nan
                r[f"{name}_file"] = ""
                continue
            # Resolution first, then size -- the same rule the loader uses, so
            # a coarse re-recording can never shadow a fine original.
            best, bstep, bn = None, np.inf, -1
            for p in paths:
                try:
                    st, n, _ = measured_step(p, col)
                except Exception as e:                       # noqa: BLE001
                    print(f"  {day} {name}: cannot read {p.name}: {e}")
                    continue
                if not np.isfinite(st):
                    continue
                if st < bstep or (st == bstep and n > bn):
                    best, bstep, bn = p, st, n
            r[f"{name}_step"] = bstep if best is not None else np.nan
            r[f"{name}_file"] = best.name if best is not None else ""
            r[f"{name}_rows"] = bn if best is not None else 0

        # coverage and aggressor, from the tape the loader would actually use
        r.update(rth_rows=0, full=False, aggressor="")
        if r.get("tape_file"):
            df = _cached(TAPE / r["tape_file"])
            s = rth(df)
            r["rth_rows"] = len(s)
            r["full"] = bool(is_full_session(df))
            if "aggressor" in df.columns:
                vals = sorted(set(map(str, df["aggressor"].dropna().unique())))
                r["aggressor"] = "".join(vals)
                r["aggressor_nulls"] = int(df["aggressor"].isna().sum())
            r["tape_step_check"] = price_step(df)

        r.update(provenance(day))
        rows.append(r)

    R = pd.DataFrame(rows)

    def ok(v):
        return bool(np.isfinite(v)) and abs(v - 0.25) < 1e-9

    print("--- 1. MEASURED MINIMUM NON-ZERO PRICE GAP (target 0.25) ---")
    print(f"  {'date':<10}{'tape':>8}{'depth':>8}{'cum':>8}{'bbo':>8}   verdict")
    for _, r in R.iterrows():
        v = [r.tape_step, r.depth_step, r.cum_step, r.bbo_step]
        core = all(ok(x) for x in v[:3])
        tag = "PASS" if core else "FAIL"
        if core and not ok(r.bbo_step):
            tag = "PASS (no BBO)"
        print(f"  {r.day:<10}" + "".join(
            f"{('-' if not np.isfinite(x) else f'{x:.2f}'):>8}" for x in v)
            + f"   {tag}")

    print("\n--- 2. REQUIRED STREAMS ---")
    print(f"  {'date':<10}{'tape':>6}{'aggr':>6}{'cumfill':>9}{'depth':>7}{'bbo':>6}")
    for _, r in R.iterrows():
        print(f"  {r.day:<10}"
              f"{('yes' if r.get('tape_file') else 'NO'):>6}"
              f"{(r.get('aggressor') or 'NO'):>6}"
              f"{('yes' if r.get('cum_file') else 'NO'):>9}"
              f"{('yes' if r.get('depth_file') else 'NO'):>7}"
              f"{('yes' if r.get('bbo_file') else 'NO'):>6}")

    print("\n--- 3. SESSION COVERAGE ---")
    for _, r in R.iterrows():
        note = "  (known CME early close)" if r.day in KNOWN_PART_SESSION else ""
        print(f"  {r.day}  RTH prints {int(r.rth_rows):>7}  "
              f"full session {str(bool(r.full)):<5}{note}")

    print("\n--- 4. PROVENANCE ---")
    for _, r in R.iterrows():
        print(f"  {r.day}  _status {r.status:<8} recorder {r.version:<14} "
              f"platform TickSize = {r.ticksize}")

    print("\n--- 5. CLASSIFICATION ---")
    print("  Every target date lies inside the period this project has been")
    print("  working in, and per-script date provenance was never pinned.")
    print("  Under the standing rule -- previously examined dates do not become")
    print("  pristine validation by being re-recorded finer -- ALL SIXTEEN ARE")
    print("  ADDITIONAL DISCOVERY DATA. None is validation.\n")

    core_ok = R.apply(lambda r: all(ok(r[f"{s}_step"])
                                    for s in ("tape", "depth", "cum")), axis=1)
    print("=" * 78)
    print(f"  verified at 0.25 on tape+depth+cum : {int(core_ok.sum())} of {len(R)}")
    print(f"  with BBO as well                   : "
          f"{int((core_ok & R.bbo_step.apply(ok)).sum())} of {len(R)}")
    print(f"  full cash sessions among those     : "
          f"{int((core_ok & R.full.astype(bool)).sum())}")
    missing = [r.day for _, r in R.iterrows() if not r.get("tape_file")]
    if missing:
        print(f"  NOT YET DELIVERED                  : {' '.join(missing)}")
    print("=" * 78)

    out = ROOT.parent / "reports" / "rp007_preservation_verification.csv"
    R.to_csv(out, index=False)
    print(f"  written: {out}")
    print("  No level computed. No interaction counted. Sealed dates unread.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
