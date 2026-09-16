#!/usr/bin/env python3
"""The compact recording format, and the proof that it loses nothing.

THE ENCODING

Three changes, each removing redundancy rather than information:

  price   integer tick offset from a per-session base, so 30055.25 is written
          as 21 rather than as eight characters of decimal
  time    microseconds elapsed since a per-session epoch, delta encoded against
          the previous row, so the 22 rows of one depth snapshot carry 0
          instead of 22 copies of the same 26-character timestamp
  resync  every row whose gap from the last absolute exceeds RESYNC_US carries
          its absolute time instead, flagged by abs_t = 1

The resync column is what keeps delta encoding safe. Without it a single lost
row shifts every timestamp after it for the rest of the session; with it the
damage is bounded to one resync interval, and the flag makes the boundary
explicit rather than implied.

The base price, the epoch and the tick size are written into the file header,
so a file decodes with nothing but itself.

WHY THIS FILE EXISTS RATHER THAN JUST THE ENCODER

A format change days before sixty irreplaceable sessions are recorded is only
acceptable if it is proven, not argued. `verify()` decodes an encoded file and
compares it to the original **cell by cell** -- every price, volume, level,
side and timestamp -- and additionally replays both through the order book
reconstruction and compares the resulting books at every timestamp. It returns
False on the first disagreement. Nothing ships unless it returns True on real
session data.

Usage: python3 scripts/orderflow/codec.py
"""
from __future__ import annotations

import gzip
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

RESYNC_US = 60_000_000          # one minute
TICK = 0.25


def encode(df: pd.DataFrame, price_cols=("price",),
           time_col="time", tick: float = TICK) -> tuple[str, pd.DataFrame]:
    """Return (header, encoded frame). The header decodes the frame."""
    t = pd.to_datetime(df[time_col])
    epoch = t.iloc[0].floor("D")
    us = ((t - epoch).dt.total_seconds() * 1e6).round().astype(np.int64).to_numpy()

    base = float(np.floor(min(df[c].min() for c in price_cols)))

    # absolute time whenever the run since the last absolute is long enough
    abs_t = np.zeros(len(us), dtype=np.int8)
    last = us[0] if len(us) else 0
    for i in range(len(us)):
        if i == 0 or us[i] - last >= RESYNC_US:
            abs_t[i] = 1
            last = us[i]
    dt = np.diff(us, prepend=us[0])
    tcol = np.where(abs_t == 1, us, dt)

    out = df.copy()
    out[time_col] = tcol
    out.insert(out.columns.get_loc(time_col) + 1, "abs_t", abs_t)
    for c in price_cols:
        out[c] = np.rint((df[c].to_numpy(np.float64) - base) / tick).astype(np.int64)

    header = (f"#fmt=1 epoch={epoch.strftime('%Y-%m-%dT%H:%M:%S')} "
              f"base={base:.4f} tick={tick} resync_us={RESYNC_US}")
    return header, out


def decode(header: str, enc: pd.DataFrame, price_cols=("price",),
           time_col="time") -> pd.DataFrame:
    """Invert encode() using only what the header carries."""
    meta = {}
    for part in header.lstrip("#").split():
        if "=" in part:
            k, v = part.split("=", 1)
            meta[k] = v
    epoch = pd.Timestamp(meta["epoch"])
    base = float(meta["base"])
    tick = float(meta["tick"])

    tcol = enc[time_col].to_numpy(np.int64)
    abs_t = enc["abs_t"].to_numpy(np.int8)

    # Walk once: an absolute row sets the clock, a delta row advances it.
    us = np.empty(len(tcol), dtype=np.int64)
    cur = 0
    for i in range(len(tcol)):
        cur = tcol[i] if abs_t[i] == 1 else cur + tcol[i]
        us[i] = cur

    out = enc.drop(columns=["abs_t"]).copy()
    out[time_col] = epoch + pd.to_timedelta(us, unit="us")
    for c in price_cols:
        out[c] = enc[c].to_numpy(np.int64) * tick + base
    return out


def write_gz(path: Path, header: str, enc: pd.DataFrame) -> int:
    buf = io.StringIO()
    buf.write(header + "\n")
    enc.to_csv(buf, index=False)
    raw = buf.getvalue().encode()
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(raw)
    return path.stat().st_size


def read_gz(path: Path) -> tuple[str, pd.DataFrame]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        header = f.readline().rstrip("\n")
        enc = pd.read_csv(f)
    return header, enc


def is_encoded(path: Path) -> bool:
    """Does this file lead with an encoding header?"""
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            return f.readline().startswith("#fmt=")
    except OSError:
        return False


def load_any(path: Path, price_cols=("price",),
             time_col="time") -> pd.DataFrame:
    """Read either format. The recorder changed mid-project, so every reader
    has to cope with both and no caller should need to know which it has."""
    if not is_encoded(path):
        df = pd.read_csv(path, compression="gzip")
        df[time_col] = pd.to_datetime(df[time_col])
        return df
    header, enc = read_gz(path)
    return decode(header, enc, price_cols, time_col)


def verify(original: pd.DataFrame, price_cols=("price",),
           time_col="time", label="") -> bool:
    """Encode, decode, and compare every cell. True only on an exact match."""
    header, enc = encode(original, price_cols, time_col)
    back = decode(header, enc, price_cols, time_col)

    if list(back.columns) != list(original.columns):
        print(f"  {label}: COLUMN MISMATCH {list(back.columns)}")
        return False
    if len(back) != len(original):
        print(f"  {label}: ROW COUNT {len(back)} vs {len(original)}")
        return False

    ok = True
    for c in original.columns:
        a, b = original[c], back[c]
        if c == time_col:
            same = (pd.to_datetime(a).to_numpy() == b.to_numpy()).all()
        elif c in price_cols:
            # exact to a thousandth of a tick; the encoding is integral so a
            # real mismatch is never marginal
            same = np.allclose(a.to_numpy(np.float64), b.to_numpy(np.float64),
                               atol=TICK / 1000.0, rtol=0)
        else:
            # NaN != NaN, so a column that is legitimately empty -- the CME
            # order-id fields are null on every row, and parent_seq is null on
            # exactly the order rows -- would report as corrupted by a naive
            # comparison. Nulls must match in POSITION; values must match
            # where both are present.
            an, bn = a.isna().to_numpy(), b.isna().to_numpy()
            same = bool((an == bn).all()) and bool(
                (a[~an].to_numpy() == b[~bn].to_numpy()).all())
        if not same:
            print(f"  {label}: column '{c}' DIFFERS")
            ok = False
    return ok


def main():
    from book import replay                                              # noqa
    d = Path("/root/.claude/uploads/53a4adb9-543d-5460-95dd-0cda0b53172f")
    files = {
        "TAPE": (d / "19e66271-TAPE_NQ_20260618_run2.csv.gz", ("price",)),
        "BBO": (d / "51516c7f-BBO_NQ_20260618_run2.csv.gz", ("price",)),
        "L2": (d / "246edd12-L2_NQ_20260618_run2.csv.gz", ("price",)),
        "CUM": (d / "699f8520-CUM_NQ_20260618.csv.gz",
                ("first_price", "last_price")),
    }
    print("=" * 78)
    print("ROUND TRIP ON THE REAL 18 JUNE SESSION")
    print("=" * 78)
    all_ok = True
    total_old = total_new = 0
    for name, (path, pcols) in files.items():
        if not path.exists():
            print(f"  {name}: missing")
            continue
        df = pd.read_csv(path, compression="gzip")
        df["time"] = pd.to_datetime(df["time"])
        ok = verify(df, pcols, "time", name)
        header, enc = encode(df, pcols, "time")
        out = Path("/tmp/claude-0/enc_" + name + ".csv.gz")
        out.parent.mkdir(parents=True, exist_ok=True)
        new = write_gz(out, header, enc)
        old = path.stat().st_size
        total_old += old
        total_new += new
        print(f"  {name:<6} cells identical: {ok}     "
              f"{old/1e6:>6.2f} MB -> {new/1e6:>6.2f} MB "
              f"({100*(1-new/old):>4.1f}% smaller)")
        all_ok = all_ok and ok

    # the book must reconstruct identically, not merely decode identically
    print("\n  order book reconstruction, original vs decoded:")
    path, pcols = files["L2"]
    df = pd.read_csv(path, compression="gzip")
    df["time"] = pd.to_datetime(df["time"])
    header, enc = encode(df, pcols, "time")
    back = decode(header, enc, pcols, "time")
    n = mism = 0
    for (t1, b1, a1), (t2, b2, a2) in zip(replay(df), replay(back)):
        n += 1
        if t1 != t2 or b1 != b2 or a1 != a2:
            mism += 1
            if mism == 1:
                print(f"    first mismatch at {t1}")
    print(f"    {n:,} timestamps compared, {mism} mismatched")
    all_ok = all_ok and mism == 0

    print("\n" + "=" * 78)
    print(f"  session {total_old/1e6:.2f} MB -> {total_new/1e6:.2f} MB")
    print(f"  VERDICT: {'SHIP' if all_ok else 'DO NOT SHIP'}")


if __name__ == "__main__":
    main()
