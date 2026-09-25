#!/usr/bin/env python3
"""Step 4 data adapters (reports/step4_preregistration.md section 3).

Bars -- NQ 1-minute in the schema of data/intraday_long/QQQ_1m.parquet (naive ET,
09:30-15:59, open/high/low/close/volume) and QQQ_1m_eth.parquet (calendar date,
04:00-19:59 ET, plus a `date` string). Prices are ratio back-adjusted by
instrument; `NQ_factor.parquet` maps every RTH session to its cumulative factor so
that dollar P&L = adjusted points / factor * $20.

Tape -- Databento discovery prints (61 registered sessions) in the tape.load_all()
format: time (ET + 4 h, so tape.rth's fixed 13:30-20:00 window is 09:30-16:00 ET
all year), price, volume, aggressor (B/S), sign, signed. Recombined aggressive
orders (grouped by ts_event and side) are written alongside for studies that read
the ATAS cumulative-trade stream.

Written to data/clean/step4/ -- Databento-derived, gitignored, never pushed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data/clean"
OUT = CLEAN / "step4"
DISC_EXCLUDED = {"2026-03-16", "2026-03-17", "2026-04-03", "2026-05-25"}
DISC = ("2026-03-02", "2026-05-29")


def instrument_factors(sym="NQ"):
    r = pd.read_csv(CLEAN / "rolls" / f"{sym}_rolls.csv")
    f = {int(r.new_id.iloc[-1]): 1.0}
    for x in r.iloc[::-1].itertuples():
        f[int(x.old_id)] = f[int(x.new_id)] * (x.ratio if x.ratio_valid else 1.0)
    return f


def load_1m(sym="NQ"):
    fs = sorted((CLEAN / "bars_1m").glob(f"{sym}_*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


def build_bars(sym="NQ"):
    OUT.mkdir(parents=True, exist_ok=True)
    b = load_1m(sym)
    fac = instrument_factors(sym)
    missing = set(b.instrument_id.unique()) - set(fac)
    assert not missing, f"no factor for instruments {missing}"
    b["factor"] = b.instrument_id.map(fac).astype(float)
    for c in ("open", "high", "low", "close"):
        b[c] = b[c] * b["factor"]
    b["timestamp"] = b.ts_et.astype("datetime64[us]")
    b["volume"] = b.volume.astype("int64")
    cols = ["timestamp", "open", "high", "low", "close", "volume"]

    rth = b[b.rth].sort_values("timestamp")
    assert rth.timestamp.is_unique
    rth[cols].to_parquet(OUT / f"{sym}_1m.parquet", index=False)
    fa = rth.groupby(rth.timestamp.dt.normalize()).agg(
        factor=("factor", "first"), n_factor=("factor", "nunique"),
        instrument_id=("instrument_id", "first"))
    fa.index.name = "day"
    assert (fa.n_factor == 1).all(), "an RTH session spans two instruments"
    fa.drop(columns="n_factor").reset_index().to_parquet(OUT / f"{sym}_factor.parquet",
                                                          index=False)

    t = b.timestamp
    mins = t.dt.hour * 60 + t.dt.minute
    eth = b[(mins >= 240) & (mins < 1200)].sort_values(["timestamp", "instrument_id"])
    # a calendar date carries one instrument in 04:00-19:59 except on roll days,
    # where the evening belongs to the new contract; keep the RTH instrument
    day = eth.timestamp.dt.normalize()
    rth_id = fa.instrument_id
    keep = eth.instrument_id.to_numpy() == day.map(rth_id).to_numpy()
    eth = eth[keep | day.map(rth_id).isna().to_numpy()]
    eth = eth.drop_duplicates("timestamp")
    e = eth[cols].copy()
    e["date"] = e.timestamp.dt.strftime("%Y%m%d")
    e.to_parquet(OUT / f"{sym}_1m_eth.parquet", index=False)
    return dict(rth_rows=len(rth), rth_sessions=int(fa.shape[0]), eth_rows=len(e),
                first=str(rth.timestamp.min()), last=str(rth.timestamp.max()))


def build_tape():
    import build_derived as BD
    d = OUT / "tape"
    d.mkdir(parents=True, exist_ok=True)
    t = BD.load_ticks("B1")
    t["day"] = t.session.dt.strftime("%Y-%m-%d")
    t = t[(t.day >= DISC[0]) & (t.day <= DISC[1]) & ~t.day.isin(DISC_EXCLUDED)]
    n = 0
    for day, x in t.groupby("day"):
        x = x.sort_values(["ts_utc", "sequence"], kind="stable")
        o = pd.DataFrame({
            "time": (x.ts_et + pd.Timedelta(hours=4)).astype("datetime64[us]").to_numpy(),
            "price": x.price.to_numpy(float),
            "volume": x["qty"].to_numpy("int64"),
            "aggressor": np.where(x.side == "B", "B", np.where(x.side == "A", "S", "N"))})
        o["sign"] = np.where(o.aggressor == "B", 1, np.where(o.aggressor == "S", -1, 0))
        o["signed"] = o["sign"] * o["volume"]
        o.to_parquet(d / f"TAPE_NQ_{day.replace('-', '')}.parquet", index=False)
        c = BD.recombine(x)
        c = pd.DataFrame({
            "time": (c.ts_et + pd.Timedelta(hours=4)).astype("datetime64[us]").to_numpy(),
            "first_price": c.p_first.to_numpy(float), "last_price": c.p_last.to_numpy(float),
            "volume": c["qty"].to_numpy("int64"), "fills": c.n_prints.to_numpy("int64"),
            "aggressor": np.where(c.side == "B", "B", np.where(c.side == "A", "S", "N"))})
        c.sort_values("time", kind="stable").to_parquet(
            d / f"CUM_NQ_{day.replace('-', '')}.parquet", index=False)
        n += 1
    return dict(tape_sessions=n)


def load_tape_all() -> dict[str, pd.DataFrame]:
    """Drop-in for tape.load_all(): {YYYYMMDD: DataFrame}, discovery only."""
    return {p.stem.split("_")[-1]: pd.read_parquet(p)
            for p in sorted((OUT / "tape").glob("TAPE_NQ_*.parquet"))}


def load_cum_all() -> dict[str, pd.DataFrame]:
    return {p.stem.split("_")[-1]: pd.read_parquet(p)
            for p in sorted((OUT / "tape").glob("CUM_NQ_*.parquet"))}


if __name__ == "__main__":
    print(build_bars("NQ"))
    print(build_bars("ES"))
    print(build_tape())
