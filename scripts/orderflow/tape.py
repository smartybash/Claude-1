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
import shutil
import zipfile
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


def open_maybe_brotli(path: Path):
    """A binary stream for a .csv.gz or a .csv.br.

    The recorder writes gzip while a session runs, because that happens on the
    market-data thread and has to be cheap, then recompresses to Brotli when it
    bundles -- at which point the session is over and the cost does not matter.
    Brotli is 27% smaller on the same bytes, which is what keeps all four
    streams in one zip.

    Decompression goes through pyarrow rather than a `brotli` module, which is
    not installed and need not be: pyarrow is already a dependency and carries
    the codec.
    """
    if path.suffix == ".br":
        import pyarrow as pa
        return pa.CompressedInputStream(pa.memory_map(str(path), "rb"), "brotli")
    return gzip.open(path, "rb")


def _encoded(path: Path) -> bool:
    try:
        with open_maybe_brotli(path) as f:
            return f.read(5) == b"#fmt="
    except (OSError, ValueError):
        return False


def load_day(path: Path) -> pd.DataFrame:
    # Recorder 2026-09-16.r writes a compact encoding behind a "#fmt=" header:
    # integer tick prices and delta-encoded microsecond times. Older files have
    # no header and are read as before.
    if path.suffix == ".br" or _encoded(path):
        from codec import load_any
        df = load_any(path)
        df = df.dropna(subset=["time"]).sort_values("time", kind="stable")
        df = df.reset_index(drop=True)
        df["sign"] = np.where(df.aggressor == "B", 1,
                              np.where(df.aggressor == "S", -1, 0))
        df["signed"] = df["sign"] * df["volume"]
        return df
    return _load_day_plain(path)


def _load_day_plain(path: Path) -> pd.DataFrame:
    # Columns are matched by name, so the recorder adding a leading `seq` or
    # trailing `datatype`/`oi`/order-id columns changes nothing here. Only the
    # four the analysis uses are typed.
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


def unpack_bundles(folder: Path = None) -> int:
    """Expand any NQ_<date>.zip the recorder produced into loose files.

    The recorder now folds a session's three outputs into one zip, because a
    five-file upload limit against three files a day means a day and a half per
    upload. Nothing downstream needs to know: the parts inside are the same
    gzipped CSVs as before, so they are extracted once into the same folders
    the loaders already read and everything after this point is unchanged.

    Extraction is skipped when the part is already present, so this is cheap to
    call on every load and safe to call twice.
    """
    folder = folder or TAPE.parent
    n = 0
    for z in sorted(folder.rglob("*.zip")):
        try:
            with zipfile.ZipFile(z) as zf:
                for name in zf.namelist():
                    base = Path(name).name
                    if not (base.endswith(".csv.gz") or
                            base.endswith(".csv.br") or
                            base.startswith("_status")):
                        continue
                    if base.startswith("TAPE_"):
                        dest = TAPE / base
                    elif base.startswith("L2_"):
                        dest = folder / "depth" / base
                    elif base.startswith("CUM_"):
                        dest = folder / "cum" / base
                    elif base.startswith("BBO_"):
                        dest = folder / "bbo" / base
                    elif base.startswith("MBO_"):
                        dest = folder / "mbo" / base
                    elif base.startswith("_status"):
                        # Provenance: which settings and what resolution this
                        # session was recorded at. Kept beside the data rather
                        # than discarded, which is the whole reason it is now
                        # bundled.
                        dest = folder / "status" / base
                    else:
                        continue
                    if dest.exists():
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out)
                    n += 1
        except (zipfile.BadZipFile, OSError) as e:
            print(f"  could not read {z.name}: {e}")
    if n:
        print(f"  unpacked {n} file(s) from session bundles")
    return n


def load_all() -> dict[str, pd.DataFrame]:
    out = {}
    unpack_bundles()
    # pandas decompresses .gz by extension, so both forms just work.
    paths = sorted(list(TAPE.glob("TAPE_*.csv")) +
                   list(TAPE.glob("TAPE_*.csv.gz")) +
                   list(TAPE.glob("TAPE_*.csv.br")))
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
        day = m.group(1)

        # When a date was recorded more than once, keep the FINER recording.
        #
        # This used to be a plain assignment, so the last filename in sort
        # order won -- which meant a coarse "_run2" silently replaced a
        # true-0.25 original. That is exactly what was happening to 12 and 20
        # August: both were recorded at 0.25, both were re-recorded on a
        # 5-point grid, and every study since has been reading the coarse
        # twin while the fine one sat unused on disk.
        #
        # Resolution first, then row count. A re-recording is only preferred
        # when it is at least as fine and carries more data.
        if day in out:
            keep, step_new, step_old = None, price_step(df), price_step(out[day])
            if step_new < step_old:
                keep = "new"
            elif step_new > step_old:
                keep = "old"
            else:
                keep = "new" if len(df) > len(out[day]) else "old"
            if keep == "old":
                continue
        out[day] = df
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


def session_day(df: pd.DataFrame) -> pd.Timestamp:
    """The calendar day this recording is OF.

    Not the first row's date. A recording that runs around the clock begins
    the PREVIOUS evening -- the encoded files carry an epoch of the day before
    -- so taking the first timestamp put the cash window on the wrong day and
    found almost nothing in it. An 18 June tape was classified a half session
    that way, with 371,904 prints sitting inside the window it had just
    missed.

    The day with the most prints is the session, which is robust to a few
    hours of lead-in at either end.
    """
    counts = df.time.dt.normalize().value_counts()
    return counts.index[0]


def rth(df: pd.DataFrame) -> pd.DataFrame:
    """The cash session only. Overnight is a different animal and is excluded."""
    d = session_day(df)
    m = (df.time >= _at(d, RTH_OPEN)) & (df.time < _at(d, RTH_CLOSE))
    return df.loc[m].reset_index(drop=True)


def price_step(df: pd.DataFrame) -> float:
    """The price increment this recording actually uses.

    NQ trades in 0.25 and the constant TICK says so, but the recordings do not:
    every print, every cumulative trade and every depth level sits on a whole
    multiple of 5.00, with level 0 and level 1 of the book five points apart.
    The feed is delivering a grid twenty steps coarser than the instrument.

    Most of the work does not care -- bars, CVD, VWAP and levels are unaffected,
    and anything that divides one tick count by another has the error cancel.
    Anything that walks a price ladder one step at a time does care, and using
    0.25 there does not merely lose resolution, it invents structure: nineteen
    of every twenty rungs are empty, so every traded price sits next to a zero
    and compares favourably with it.

    So the step is measured rather than assumed.
    """
    p = np.unique(df.price.to_numpy(np.float64))
    if len(p) < 3:
        return TICK
    gaps = np.diff(p)
    gaps = gaps[gaps > 0]
    return float(np.min(gaps)) if len(gaps) else TICK


def is_full_session(df: pd.DataFrame) -> bool:
    """Does this recording cover a whole cash day?

    Four recordings in the pool do not, and until this was checked they were
    being counted as ordinary sessions by every study, because the usual guard
    is `len(s) > 5000` and a half day clears that easily.

    Three are CME early closes at 17:00 UTC (13:00 New York) -- 19 June, 3 July
    and 7 September -- which carry about 54% of a session and 27,000 ticks
    against a median of 346,000. The fourth, 12 July, is a Sunday with no cash
    session at all.

    They are excluded rather than shortened because a clock exit is undefined
    on them: the 19:00 UTC variant has no data, and the "close" variant means
    13:00 New York on those days and 16:00 on every other, which is not the
    same trade. The cut is on coverage and tick count, not on anything the
    session did, so it cannot be tuned by a result.
    """
    s = rth(df)
    if len(s) < 40_000:
        return False
    open_t = _at(session_day(df), RTH_OPEN)
    minutes = (s.time.iloc[-1] - open_t).total_seconds() / 60.0
    return minutes >= 0.97 * 390.0


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
