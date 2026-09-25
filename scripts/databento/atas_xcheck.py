#!/usr/bin/env python3
"""ATAS vs Databento aggressor cross-check on the B3 sessions (RTH only).

Data-quality only: these sessions are in the excluded window and enter no test.

Questions, answered from the data rather than assumed:
  1. Do the two sources see the same trading? RTH volume, print counts,
     per-minute volume correlation.
  2. What is the clock offset between ATAS (recorder clock) and Databento
     ts_event (exchange)? Estimated by cross-correlating per-second volume.
  3. Which Databento side matches ATAS 'B' (buyer lifted the offer)? Footprint
     agreement at (minute, price) under both possible mappings.
  4. Are ATAS prints per fill or per aggressor order? Compare counts with
     Databento prints and recombined orders.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/orderflow"))
from tape import load_all, rth                                      # noqa: E402

OUT = ROOT / "reports"


def db_prints(day):
    fs = glob.glob(str(ROOT / f"data/raw/B3-{day[5:]}/*/*.trades.dbn.zst"))
    t = db.DBNStore.from_file(fs[0]).to_df().reset_index()
    t = t.rename(columns={"size": "qty"})
    t["ts"] = t.ts_event.dt.tz_localize(None)          # naive UTC, like the ATAS tape
    return t[["ts", "price", "qty", "side", "instrument_id"]]


def footprint_agree(a, d, dside):
    """Share of ATAS buy volume matched by Databento `dside` volume at the same
    (minute, price), and likewise for sells with the other side."""
    a = a.assign(minute=a.time.dt.floor("1min"))
    d = d.assign(minute=d.ts.dt.floor("1min"))
    other = "A" if dside == "B" else "B"
    ab = a[a.aggressor == "B"].groupby(["minute", "price"]).volume.sum()
    as_ = a[a.aggressor == "S"].groupby(["minute", "price"]).volume.sum()
    db_b = d[d.side == dside].groupby(["minute", "price"]).qty.sum()
    db_s = d[d.side == other].groupby(["minute", "price"]).qty.sum()
    jb = pd.concat([ab, db_b], axis=1, keys=["a", "d"]).fillna(0)
    js = pd.concat([as_, db_s], axis=1, keys=["a", "d"]).fillna(0)
    return (float(np.minimum(jb.a, jb.d).sum() / jb.a.sum()),
            float(np.minimum(js.a, js.d).sum() / js.a.sum()))


def clock_offset(a, d, max_lag=5):
    sa = a.set_index("time").volume.resample("1s").sum()
    sd = d.set_index("ts").qty.resample("1s").sum()
    j = pd.concat([sa, sd], axis=1, keys=["a", "d"]).fillna(0)
    best = max(range(-max_lag, max_lag + 1),
               key=lambda k: np.corrcoef(j.a, j.d.shift(k).fillna(0))[0, 1])
    return best, float(np.corrcoef(j.a, j.d.shift(best).fillna(0))[0, 1])


def main():
    days = ("2026-06-24", "2026-07-09", "2026-07-29", "2026-08-06", "2026-08-19")
    tape = load_all()
    rows = []
    for day in days:
        key = day.replace("-", "")
        fs = glob.glob(str(ROOT / f"data/raw/B3-{day[5:]}/*/*.trades.dbn.zst"))
        if not fs or key not in tape:
            rows.append(dict(day=day, status="not available"))
            continue
        a = rth(tape[key]).copy()
        d = db_prints(day)
        lo, hi = a.time.min().floor("1min"), a.time.max().ceil("1min")
        d = d[(d.ts >= lo) & (d.ts < hi)]
        lag, rho = clock_offset(a, d)
        ma = a.set_index("time").volume.resample("1min").sum()
        md = d.set_index("ts").qty.resample("1min").sum()
        mj = pd.concat([ma, md], axis=1, keys=["a", "d"]).fillna(0)
        dorders = d.groupby(["ts", "side"]).qty.sum()
        bb, ss = footprint_agree(a, d, "B")        # mapping 1: B = buy aggressor
        bb2, ss2 = footprint_agree(a, d, "A")      # mapping 2: A = buy aggressor
        rows.append(dict(
            day=day, status="ok",
            atas_volume=int(a.volume.sum()), db_volume=int(d.qty.sum()),
            atas_prints=len(a), db_prints=len(d), db_orders=len(dorders),
            minute_vol_corr=float(np.corrcoef(mj.a, mj.d)[0, 1]),
            clock_lag_s=lag, per_second_corr_at_lag=rho,
            agree_B_is_buy_buys=bb, agree_B_is_buy_sells=ss,
            agree_A_is_buy_buys=bb2, agree_A_is_buy_sells=ss2,
            db_side_N=int((d.side == "N").sum()),
            instruments=int(d.instrument_id.nunique())))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "databento_atas_xcheck.csv", index=False)
    print(R.to_string(index=False))
    return R


if __name__ == "__main__":
    main()
