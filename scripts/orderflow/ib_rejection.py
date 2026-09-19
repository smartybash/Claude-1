#!/usr/bin/env python3
"""INITIAL BALANCE BY REJECTION — measurement module.

IB = 09:30-10:30 ET. IBH/IBL = high/low of that window, with the timestamp of
the bar that made each. "High formed first" = IBH bar precedes IBL bar.

ENDING ZONE, exactly as specified:
    Low formed first  -> 0% = IBH, 100% = IBL   (expected break = UP)
    High formed first -> 0% = IBL, 100% = IBH   (expected break = DOWN)
    EZ = |close_10:30 - expected_break_level| / IB_range * 100

THE GEOMETRIC IDENTITY THAT GOVERNS THIS WHOLE FAMILY

close_10:30 always lies inside [IBL, IBH], so the distance to the expected
break level and the distance to the opposite level sum to exactly the IB range:

    d_expected = EZ% x IB_range        d_opposite = (100-EZ)% x IB_range

For a driftless random walk started at close_10:30 between two absorbing
barriers, P(hit expected side first) = d_opposite / (d_expected + d_opposite)
                                      = (100 - EZ)%.

So the random-walk break probability for the 0-25% bucket is ~87-88% BEFORE
any market behaviour. That is the benchmark. 50% is not.
"""
from __future__ import annotations
import datetime as dt, glob, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from codec import is_encoded, load_any                                  # noqa

QQQ = ROOT / "data/intraday_long/QQQ_1m.parquet"
MIN_BARS = 360
COST_F = 2.00 / 30000.0
SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}
BUCKETS = [(0, 25), (25, 50), (50, 75), (75, 100)]


def _measure(day, t_min, hi, lo, cl, op, px):
    """t_min = minutes from 09:30. Returns one session record or None."""
    ib = (t_min >= 0) & (t_min < 60)
    post = t_min >= 60
    if ib.sum() < 30 or post.sum() < 60:
        return None
    ih, il = hi[ib], lo[ib]
    tib = t_min[ib]
    i_h = int(np.argmax(ih)); i_l = int(np.argmin(il))
    ibh, ibl = float(ih[i_h]), float(il[i_l])
    rng = ibh - ibl
    if rng <= 0 or tib[i_h] == tib[i_l]:
        return None                                   # same bar: undefined order
    high_first = tib[i_h] < tib[i_l]
    close = float(cl[ib][-1])
    exp_lvl, opp_lvl = (ibl, ibh) if high_first else (ibh, ibl)
    d_exp = abs(close - exp_lvl)
    ez = 100.0 * d_exp / rng
    # which side breaks first after 10:30
    ph, pl, po = hi[post], lo[post], op[post]
    up = np.where(ph > ibh)[0]
    dn = np.where(pl < ibl)[0]
    iu = int(up[0]) if len(up) else 10 ** 9
    idn = int(dn[0]) if len(dn) else 10 ** 9
    if iu == idn:
        broke = "both"                                # same bar, unresolvable
    elif iu < idn:
        broke = "up"
    elif idn < iu:
        broke = "down"
    else:
        broke = "none"
    if iu == 10 ** 9 and idn == 10 ** 9:
        broke = "none"
    exp_side = "down" if high_first else "up"
    return dict(day=day, ibh=ibh, ibl=ibl, rng=rng, px=px, close=close,
                high_first=high_first, ez=ez, exp_side=exp_side, broke=broke,
                expected_broke_first=(broke == exp_side),
                rw_base=100.0 - ez,                   # the geometric benchmark
                _i_break=(iu if broke == "up" else idn if broke == "down" else -1),
                _post_hi=ph, _post_lo=pl, _post_op=po, _post_cl=cl[post])


def qqq_sessions():
    d = pd.read_parquet(QQQ)
    d["day"] = d.timestamp.dt.date
    out = []
    for day, g in d.groupby("day", sort=True):
        g = g.sort_values("timestamp")
        if len(g) < MIN_BARS:
            continue
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        tm = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        r = _measure(day, tm, g.high.to_numpy(float), g.low.to_numpy(float),
                     g.close.to_numpy(float), g.open.to_numpy(float),
                     float(g.open.iloc[0]))
        if r:
            out.append(r)
    return out


def nq_sessions():
    """NQ tick tapes, US RTH. Sealed days excluded AT CONSTRUCTION."""
    best = {}
    for f in sorted(glob.glob(str(ROOT / "data/tape/TAPE_NQ_*.csv.*"))):
        p = Path(f)
        day = p.name.split("_")[2].split(".")[0].split("_")[0]
        if day.startswith(SEALED_PREFIX) or day in SEALED_DATES:
            continue
        best.setdefault(day, []).append(p)
    out = []
    for day, paths in sorted(best.items()):
        fine = None
        for p in paths:
            try:
                x = load_any(p) if is_encoded(p) else pd.read_csv(p)
            except Exception:
                continue
            x = x.rename(columns={"timestamp": "time", "px": "price"})
            if "time" not in x or "price" not in x:
                continue
            x["time"] = pd.to_datetime(x.time, errors="coerce", format="mixed")
            x = x.dropna(subset=["time", "price"])
            u = np.unique(x.price.to_numpy(float))
            if len(u) < 2 or float(np.min(np.diff(np.sort(u)))) > 0.25:
                continue
            if fine is None or len(x) > len(fine):
                fine = x
        if fine is None:
            continue
        # US RTH in UTC: all tape dates are EDT, so 09:30 ET = 13:30 UTC
        d0 = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}")
        o = d0 + pd.Timedelta(hours=13, minutes=30)
        end = d0 + pd.Timedelta(hours=20)
        w = fine[(fine.time >= o) & (fine.time < end)]
        if len(w) < 5000:
            continue
        b = w.set_index("time").price.resample("1min")
        bars = pd.DataFrame({"hi": b.max(), "lo": b.min(),
                             "op": b.first(), "cl": b.last()}).dropna()
        tm = (bars.index - o).total_seconds().to_numpy() / 60.0
        r = _measure(day, tm, bars.hi.to_numpy(), bars.lo.to_numpy(),
                     bars.cl.to_numpy(), bars.op.to_numpy(),
                     float(bars.op.iloc[0]))
        if r:
            out.append(r)
    return out


def bucket_of(ez):
    for lo, hi in BUCKETS:
        if lo <= ez < hi or (hi == 100 and ez == 100):
            return f"{lo}-{hi}%"
    return None
