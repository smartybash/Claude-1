#!/usr/bin/env python3
"""Loader and audit for the ATAS tick tape.

Every downstream study depends on two things being right: the clock and the
aggressor flag. Both are assumptions until checked, so this module checks them
before it hands any data on.

The clock matters because the recorder writes whatever timezone the ATAS
platform is set to, which is a user setting, not a fact about the data. The
whole edge lives in RTH, so a two-and-a-half hour error would put every session
window on the wrong bars while still looking perfectly plausible. It is pinned
here by finding the volume spike that only the cash open produces.

The aggressor flag matters because it is the entire reason for recording tape
rather than bars. If it were mislabelled, or systematically one-sided, every
delta number built on it would be fiction.

Usage: python3 scripts/tape.py
"""
from __future__ import annotations

import gzip
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
TAPE = ROOT / "data" / "tape"

TICK = 0.25          # NQ minimum price increment
POINT_USD = 20.0     # NQ dollars per index point


def read_maybe_truncated(path: Path) -> io.BytesIO:
    """Read a .gz whose tail may be missing.

    A recording copied while the recorder still had the file open loses the
    gzip end-of-stream marker, and pandas then refuses the whole file. One such
    recording still held 97% of its session, so the salvageable part is worth
    having: everything decoded before the error is kept, and the final partial
    line is dropped.
    """
    if path.suffix != ".gz":
        return path
    buf = io.BytesIO()
    try:
        with gzip.open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 22)
                if not chunk:
                    break
                buf.write(chunk)
    except (EOFError, OSError, gzip.BadGzipFile) as e:
        print(f"  {path.name}: truncated ({type(e).__name__}), "
              f"keeping the {buf.tell()/1e6:.0f} MB that decoded")
    data = buf.getvalue()
    cut = data.rfind(b"\n")
    return io.BytesIO(data[:cut + 1] if cut > 0 else data)


def load_day(path: Path) -> pd.DataFrame:
    df = pd.read_csv(read_maybe_truncated(path), encoding="utf-8-sig",
                     dtype={"price": np.float64, "volume": np.int64,
                            "aggressor": "string"})
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S.%f")
    df = df.dropna(subset=["time"]).sort_values("time", kind="stable")
    df = df.reset_index(drop=True)
    # Signed volume: +1 when the buyer lifted the offer, -1 when the seller hit
    # the bid. Anything else is dropped from delta but kept in volume.
    df["sign"] = np.where(df.aggressor == "B", 1,
                          np.where(df.aggressor == "S", -1, 0))
    df["signed"] = df["sign"] * df["volume"]
    return df


CACHE = ROOT / "data" / "cache"


def _cached(path: Path) -> pd.DataFrame:
    """Parsed frame for one session, from parquet when it is still valid.

    Parsing sixteen gzipped tapes costs about thirteen seconds cold and under
    two warm. That was never the bottleneck -- see prefix_sums below for what
    actually was -- but it is free to keep. The cache key is the source file's
    size and modification time, so a re-recorded session invalidates itself
    rather than being served stale.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    stamp = path.stat()
    key = f"{path.stem}_{stamp.st_size}_{int(stamp.st_mtime)}.parquet"
    cache = CACHE / key
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except Exception:
            cache.unlink(missing_ok=True)

    df = load_day(path)
    try:
        for old in CACHE.glob(f"{path.stem}_*.parquet"):
            old.unlink(missing_ok=True)
        df.to_parquet(cache, index=False)
    except Exception as e:
        print(f"  cache write failed for {path.name}: {e}")
    return df


def load_all() -> dict[str, pd.DataFrame]:
    out = {}
    # pandas decompresses .gz by extension, so both forms just work.
    paths = sorted(list(TAPE.glob("TAPE_*.csv")) + list(TAPE.glob("TAPE_*.csv.gz")))
    for p in paths:
        df = _cached(p)
        if len(df) < 1000:
            print(f"  skipping {p.name}: only {len(df)} rows")
            continue
        # Take the eight-digit date wherever it sits in the name. Splitting on
        # the last underscore turned TAPE_NQ_20260901_run2.csv.gz into a
        # session called "run2", which then sorted before every real date.
        m = re.search(r"(\d{8})", p.name)
        if not m:
            print(f"  skipping {p.name}: no date in the filename")
            continue
        out[m.group(1)] = df
    return out


# ----------------------------------------------------------------------------
# sessions
#
# The recorder writes the ATAS platform clock, which turned out to be UTC: the
# one-hour CME maintenance halt sits at 21:00-22:00 in the files, and that halt
# is 17:00-18:00 New York, so file time is ET+4 (during EDT). Both recorded days
# agree independently. Everything below is therefore in UTC.
# ----------------------------------------------------------------------------
RTH_OPEN = (13, 30)      # 09:30 ET cash open
RTH_CLOSE = (20, 0)      # 16:00 ET cash close
IB_END = (14, 30)        # end of the 60-minute initial balance


def _at(day: pd.Timestamp, hm) -> pd.Timestamp:
    return day.normalize() + pd.Timedelta(hours=hm[0], minutes=hm[1])


def rth(df: pd.DataFrame) -> pd.DataFrame:
    """The cash session only. Overnight is a different animal and is excluded."""
    d = df.time.iloc[0]
    m = (df.time >= _at(d, RTH_OPEN)) & (df.time < _at(d, RTH_CLOSE))
    return df.loc[m].reset_index(drop=True)


def volume_profile(df: pd.DataFrame, value_area: float = 0.70):
    """POC and value area from actual traded volume at price.

    This is the real thing rather than the approximation from bar highs and
    lows: every contract is counted at the price it printed. Value area grows
    outward from the POC, taking the heavier neighbour each step, until it
    covers the requested share of volume.
    """
    at_price = df.groupby("price").volume.sum().sort_index()
    if at_price.empty:
        return None
    prices = at_price.index.to_numpy()
    vols = at_price.to_numpy(dtype=np.float64)

    poc_i = int(np.argmax(vols))
    target = value_area * vols.sum()
    lo = hi = poc_i
    got = vols[poc_i]
    while got < target and (lo > 0 or hi < len(vols) - 1):
        below = vols[lo - 1] if lo > 0 else -1.0
        above = vols[hi + 1] if hi < len(vols) - 1 else -1.0
        if above >= below:
            hi += 1
            got += vols[hi]
        else:
            lo -= 1
            got += vols[lo]
    return dict(poc=float(prices[poc_i]),
                val=float(prices[lo]),
                vah=float(prices[hi]),
                at_price=at_price)


_PREFIX: dict[int, tuple] = {}


def prefix_sums(s: pd.DataFrame):
    """Running delta and volume for a session, as arrays indexed by trade.

    This is where the time actually went. Every study asked, for each of
    hundreds of touches, "what is the cumulative delta and volume up to this
    trade", and answered it with s.iloc[:i].sum() -- an O(n) pass over a
    300,000-row session, repeated per touch. That is tens of billions of row
    operations for a quantity that one cumulative sum answers in O(1).

    Cached by the frame's identity, so a session is scanned once per process
    however many studies ask for it.

    Returns (cumulative signed volume, cumulative volume, minutes since open),
    each aligned so index i is the state BEFORE trade i.
    """
    key = id(s)
    hit = _PREFIX.get(key)
    if hit is not None:
        return hit

    signed = np.concatenate([[0.0], s.signed.to_numpy(dtype=np.float64).cumsum()])
    vol = np.concatenate([[0.0], s.volume.to_numpy(dtype=np.float64).cumsum()])
    t = s.time.to_numpy()
    open_ = np.datetime64(_at(s.time.iloc[0], RTH_OPEN))
    mins = (t - open_) / np.timedelta64(1, "m")

    out = (signed, vol, mins)
    _PREFIX[key] = out
    return out


def audit(days: dict[str, pd.DataFrame]) -> None:
    print("=" * 78)
    print("1  WHAT ARRIVED")
    print("=" * 78)
    for d, df in days.items():
        span = df.time.iloc[-1] - df.time.iloc[0]
        print(f"  {d}  {len(df):>7,} trades  {df.volume.sum():>9,} contracts  "
              f"{df.time.iloc[0].time()} to {df.time.iloc[-1].time()}  "
              f"({span})")
        print(f"          price {df.price.min():,.2f} to {df.price.max():,.2f}"
              f"   range {df.price.max() - df.price.min():,.2f} pts")

    print("\n" + "=" * 78)
    print("2  THE CLOCK  (hourly contracts, to locate the cash open)")
    print("=" * 78)
    print("  The 09:30 New York open is the largest volume event of the day by a")
    print("  wide margin. Whichever hour column spikes IS 09:30 in this file.\n")
    for d, df in days.items():
        h = df.groupby(df.time.dt.hour).volume.sum()
        h = h.reindex(range(24), fill_value=0)
        peak = int(h.idxmax())
        tot = h.sum()
        print(f"  {d}   peak hour {peak:02d}:00 "
              f"({100 * h.max() / tot:.1f}% of the day's volume)")
        bars = "".join(
            "#" if v > 0.66 * h.max() else
            "+" if v > 0.33 * h.max() else
            "." if v > 0.05 * h.max() else " "
            for v in h.values)
        print(f"       hour 0..23  |{bars}|")

    print("\n" + "=" * 78)
    print("3  THE AGGRESSOR FLAG")
    print("=" * 78)
    print("  Buy and sell aggression must be near 50/50 over a full day: every")
    print("  contract bought is sold. A large skew would mean the tag is wrong.\n")
    for d, df in days.items():
        n = len(df)
        b = int((df.aggressor == "B").sum())
        s = int((df.aggressor == "S").sum())
        other = n - b - s
        bv = int(df.loc[df.aggressor == "B", "volume"].sum())
        sv = int(df.loc[df.aggressor == "S", "volume"].sum())
        print(f"  {d}  trades  B {100*b/n:5.2f}%  S {100*s/n:5.2f}%  "
              f"unclassified {other:,}")
        print(f"          volume  B {100*bv/(bv+sv):5.2f}%  S {100*sv/(bv+sv):5.2f}%"
              f"   day delta {bv - sv:+,}")

    print("\n" + "=" * 78)
    print("4  TICK GRID AND TRADE SIZE")
    print("=" * 78)
    for d, df in days.items():
        offgrid = int((np.abs(np.round(df.price / TICK) - df.price / TICK)
                       > 1e-6).sum())
        v = df.volume.values
        print(f"  {d}  off-tick-grid prices {offgrid}   "
              f"size mean {v.mean():.2f} median {np.median(v):.0f} "
              f"p99 {np.percentile(v, 99):.0f} max {v.max():,}")
        print(f"          singles {100*(v == 1).mean():.1f}% of trades, "
              f"{100*v[v == 1].sum()/v.sum():.1f}% of volume")

    print("\n" + "=" * 78)
    print("5  GAPS  (recording continuity)")
    print("=" * 78)
    for d, df in days.items():
        gap = df.time.diff().dt.total_seconds().values[1:]
        big = np.sort(gap)[-5:][::-1]
        print(f"  {d}  largest gaps between trades (s): "
              + ", ".join(f"{g:.0f}" for g in big))


if __name__ == "__main__":
    audit(load_all())
