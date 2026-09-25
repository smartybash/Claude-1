#!/usr/bin/env python3
"""Build the derived Databento datasets and the data-quality numbers.

Outputs (Parquet, split by month so no file approaches 50 MB):

  data/clean/bars_1m/{SYM}_{YYYY-MM}.parquet    raw unadjusted 1-minute bars
  data/clean/bars_5m/{SYM}_{YYYY-MM}.parquet    5-minute bars built from them
  data/clean/daily/{SYM}_daily.parquet          Globex + RTH daily, roll flags,
                                                ratio back-adjust factor
  data/clean/rolls/{SYM}_rolls.csv              every instrument_id change
  data/clean/ticks/{window}/footprint_{YYYY-MM}.parquet
                                                1-min volume at price, split by
                                                aggressor side
  data/clean/ticks/{window}/big_orders.parquet  recombined aggressor orders above
                                                the discovery 99th percentile
  data/clean/ticks/{window}/session_quality.csv per-session integrity numbers

Windows: `discovery` (B1), `holdout` (B2, under data/clean/holdout/ -- NOT to be
read before the final evaluation), `atas_xcheck` (B3, data-quality only).

Conventions, fixed here:
  * UTC -> America/New_York with DST. Globex session date = ET timestamp + 6 h,
    so 18:00 ET belongs to the next session. RTH = 09:30 <= ET < 16:00.
  * Minutes with no trades have no bar. Nothing is forward-filled or invented.
  * Continuous prices are UNADJUSTED; instrument_id is kept on every row.
  * Side: B = buy aggressor, A = sell aggressor, N = unknown (to be confirmed
    empirically by the ATAS cross-check, not assumed).
  * A recombined aggressor order = all prints sharing (instrument_id, ts_event,
    side).
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
import dataquality as DQ                                            # noqa: E402
import sessioncal as SC                                             # noqa: E402

RAW, CLEAN = ROOT / "data/raw", ROOT / "data/clean"
ET = "America/New_York"
TICK = 0.25
Q_BIG = 99.0
NOTES = {}


def et_cols(ts_utc: pd.Series) -> pd.DataFrame:
    et = ts_utc.dt.tz_convert(ET)
    sess = (et + pd.Timedelta(hours=6)).dt.normalize().dt.tz_localize(None)
    mins = et.dt.hour * 60 + et.dt.minute
    return pd.DataFrame({"ts_et": et.dt.tz_localize(None), "session": sess,
                         "rth": (mins >= 570) & (mins < 960)})


# ------------------------------------------------------------------ bars ----
def load_bars():
    fs = sorted(glob.glob(str(RAW / "A/*/*.ohlcv-1m.dbn.zst")))
    d = pd.concat([db.DBNStore.from_file(f).to_df().reset_index() for f in fs],
                  ignore_index=True)
    d = d[["ts_event", "symbol", "instrument_id", "open", "high", "low", "close",
           "volume"]].rename(columns={"ts_event": "ts_utc"})
    d["symbol"] = d["symbol"].str.replace(".v.0", "", regex=False)
    return d.sort_values(["symbol", "ts_utc"]).reset_index(drop=True)


def bar_quality(d, sym):
    x = d[d.symbol == sym]
    dup = int(x.duplicated(["ts_utc"]).sum())
    bad_ohlc = int(((x.low > x[["open", "close"]].min(axis=1)) |
                    (x.high < x[["open", "close"]].max(axis=1)) |
                    (x.low > x.high)).sum())
    off = float(max(DQ.off_tick(x[c].to_numpy(), TICK) for c in ("open", "high", "low", "close")))
    rng = (x.high - x.low)
    med = rng.rolling(1000, min_periods=100).median()
    spikes = int((rng > 20 * med).sum())
    zero_vol = int((x.volume == 0).sum())
    return dict(rows=len(x), first=str(x.ts_utc.min()), last=str(x.ts_utc.max()),
                duplicates=dup, bad_ohlc=bad_ohlc, off_tick_share=off,
                range_spikes_gt20x_median=spikes, zero_volume_bars=zero_vol)


def rolls(d, sym):
    x = d[d.symbol == sym].reset_index(drop=True)
    ch = np.flatnonzero(x.instrument_id.to_numpy()[1:] != x.instrument_id.to_numpy()[:-1]) + 1
    rows = []
    for i in ch:
        a, b = x.iloc[i - 1], x.iloc[i]
        gap_min = (b.ts_utc - a.ts_utc).total_seconds() / 60
        rows.append(dict(ts_old_last=a.ts_utc, ts_new_first=b.ts_utc, gap_min=gap_min,
                         old_id=int(a.instrument_id), new_id=int(b.instrument_id),
                         old_close=a.close, new_open=b.open, ratio=b.open / a.close,
                         ratio_valid=gap_min <= 5))
    return pd.DataFrame(rows)


def write_monthly(df, outdir, prefix, tcol):
    outdir.mkdir(parents=True, exist_ok=True)
    sizes = []
    for per, g in df.groupby(df[tcol].dt.strftime("%Y-%m")):
        p = outdir / f"{prefix}_{per}.parquet"
        g.to_parquet(p, index=False, compression="zstd")
        sizes.append(p.stat().st_size)
    return len(sizes), sum(sizes), max(sizes) if sizes else 0


def build_bars():
    d = load_bars()
    d = pd.concat([d, et_cols(d.ts_utc)], axis=1)
    DQ.assert_safe_columns(d, "1m bars")
    summary = {}
    for sym in ("NQ", "ES"):
        x = d[d.symbol == sym].drop(columns="symbol")
        summary[sym] = bar_quality(d, sym)
        R = rolls(d, sym)
        (CLEAN / "rolls").mkdir(parents=True, exist_ok=True)
        R.to_csv(CLEAN / "rolls" / f"{sym}_rolls.csv", index=False)
        summary[sym]["rolls"] = len(R)
        summary[sym]["rolls_ratio_invalid"] = int((~R.ratio_valid).sum()) if len(R) else 0
        summary[sym]["files_1m"] = write_monthly(x, CLEAN / "bars_1m", sym, "ts_et")
        # 5-minute bars within (instrument, session); only from bars that exist
        g5 = x.assign(b5=x.ts_et.dt.floor("5min")).groupby(
            ["instrument_id", "session", "b5"], sort=True)
        b5 = g5.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                    close=("close", "last"), volume=("volume", "sum"),
                    n_1m=("open", "size")).reset_index().rename(columns={"b5": "ts_et"})
        b5["rth"] = (b5.ts_et.dt.hour * 60 + b5.ts_et.dt.minute).between(570, 955)
        summary[sym]["files_5m"] = write_monthly(b5, CLEAN / "bars_5m", sym, "ts_et")
        # daily: Globex session and RTH, plus the RTH-close contract
        gl = x.groupby("session").agg(g_open=("open", "first"), g_high=("high", "max"),
                                      g_low=("low", "min"), g_close=("close", "last"),
                                      g_volume=("volume", "sum"))
        r = x[x.rth].groupby("session").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"),
            close=("close", "last"), volume=("volume", "sum"), n_rth_bars=("open", "size"),
            id_open=("instrument_id", "first"), id_close=("instrument_id", "last"),
            first_rth=("ts_et", "min"), last_rth=("ts_et", "max"))
        D = gl.join(r, how="left").reset_index()
        half = {pd.Timestamp(v) for v in SC.early_closes(
            x[x.rth].rename(columns={"ts_et": "timestamp"}), ts_col="timestamp", clock="ET")}
        D["half_day"] = D.session.isin(half)
        D["roll_in_session"] = D.id_open != D.id_close
        # ratio back-adjust factor for RTH closes: product of later valid ratios
        D["adj_factor"] = 1.0
        for rr in R.itertuples():
            if rr.ratio_valid:
                D.loc[D.last_rth < rr.ts_new_first.tz_convert(ET).tz_localize(None),
                      "adj_factor"] *= rr.ratio
        D["close_adj"] = D.close * D.adj_factor
        DQ.assert_safe_columns(D, f"{sym} daily")
        (CLEAN / "daily").mkdir(parents=True, exist_ok=True)
        D.to_parquet(CLEAN / "daily" / f"{sym}_daily.parquet", index=False)
        summary[sym]["sessions"] = int(len(D))
        summary[sym]["half_days"] = int(D.half_day.sum())
    NOTES["bars"] = summary


# ------------------------------------------------------------------ ticks ---
def load_ticks(tag):
    fs = sorted(glob.glob(str(RAW / tag / "*/*.trades.dbn.zst")))
    parts = []
    for f in fs:
        t = db.DBNStore.from_file(f).to_df().reset_index()
        parts.append(t[["ts_event", "instrument_id", "side", "price", "size",
                        "flags", "sequence"]])
    # `size` and `flags` shadow DataFrame.size / DataFrame.flags -- caught by
    # the reserved-name guard on the first run; renamed, never bracket-indexed
    t = pd.concat(parts, ignore_index=True).rename(
        columns={"ts_event": "ts_utc", "size": "qty", "flags": "rflags"})
    t = t.sort_values(["ts_utc", "sequence"]).reset_index(drop=True)
    return pd.concat([t, et_cols(t.ts_utc)], axis=1)


def recombine(t):
    g = t.groupby(["instrument_id", "ts_utc", "side"], sort=False)
    o = g.agg(qty=("qty", "sum"), n_prints=("qty", "size"),
              p_first=("price", "first"), p_last=("price", "last"),
              p_min=("price", "min"), p_max=("price", "max"),
              seq_first=("sequence", "min"), seq_last=("sequence", "max"),
              session=("session", "first"), rth=("rth", "first"),
              ts_et=("ts_et", "first")).reset_index()
    return o


def recombine_check(t, o, n=2000, seed=1):
    """Verify, on a sample of multi-print orders, that grouped prints are one
    sweep: contiguous sequence numbers and prices moving monotonically in the
    aggressor's direction."""
    m = o[o.n_prints > 1].sample(min(n, int((o.n_prints > 1).sum())), random_state=seed)
    key = t.set_index(["instrument_id", "ts_utc", "side"]).sort_index()
    contiguous = monotone = 0
    for r in m.itertuples():
        x = key.loc[(r.instrument_id, r.ts_utc, r.side)]
        seq = np.sort(x.sequence.to_numpy())
        contiguous += int(seq[-1] - seq[0] + 1 == len(seq) or np.all(np.diff(seq) > 0))
        p = x.sort_values("sequence").price.to_numpy()
        monotone += int(np.all(np.diff(p) >= 0) if r.side == "B" else
                        np.all(np.diff(p) <= 0) if r.side == "A" else True)
    return dict(sampled=len(m), ordered_sequence=contiguous,
                monotone_in_aggressor_direction=monotone)


def session_quality(t, o):
    rows = []
    for s, x in t.groupby("session"):
        r = x[x.rth]
        gaps = r.ts_utc.diff().dt.total_seconds()
        rows.append(dict(session=s.date(), prints=len(x), rth_prints=len(r),
                         volume=int(x["qty"].sum()), rth_volume=int(r["qty"].sum()),
                         first_rth=str(r.ts_et.min().time()) if len(r) else "",
                         last_rth=str(r.ts_et.max().time()) if len(r) else "",
                         max_rth_gap_s=float(gaps.max()) if len(r) > 1 else np.nan,
                         side_N=int((x.side == "N").sum()),
                         off_tick=float(DQ.off_tick(x.price.to_numpy(), TICK)),
                         instruments=len(x.instrument_id.unique()),
                         duplicate_seq=int(x.sequence.duplicated().sum())))
    return pd.DataFrame(rows)


def footprint(t):
    t = t.assign(minute=t.ts_et.dt.floor("1min"))
    f = t.pivot_table(index=["instrument_id", "session", "minute", "price"],
                      columns="side", values="qty", aggfunc="sum", fill_value=0)
    f = f.rename(columns={"B": "buy_aggr_vol", "A": "sell_aggr_vol", "N": "unk_vol"})
    for c in ("buy_aggr_vol", "sell_aggr_vol", "unk_vol"):
        if c not in f.columns:
            f[c] = 0
    f = f.reset_index()
    f["rth"] = (f.minute.dt.hour * 60 + f.minute.dt.minute).between(570, 959)
    f.columns.name = None
    return f


def build_ticks(big_thr=None):
    out = {}
    for tag, window, base in (("B1", "discovery", CLEAN / "ticks"),
                              ("B2", "holdout", CLEAN / "holdout" / "ticks")):
        t = load_ticks(tag)
        DQ.assert_safe_columns(t, f"{window} ticks")
        o = recombine(t)
        if window == "discovery":
            big_thr = float(np.percentile(o["qty"], Q_BIG))
            rc = recombine_check(t, o)
        d = base / window
        d.mkdir(parents=True, exist_ok=True)
        fp = footprint(t)
        nfp = write_monthly(fp, d, "footprint", "minute")
        o[o["qty"] >= big_thr].to_parquet(d / "big_orders.parquet", index=False,
                                           compression="zstd")
        q = session_quality(t, o)
        q.to_csv(d / "session_quality.csv", index=False)
        out[window] = dict(prints=len(t), orders=len(o),
                           prints_per_order=len(t) / len(o),
                           side_share={k: round(v, 6) for k, v in
                                       t.side.value_counts(normalize=True).items()},
                           sessions=int(q.session.nunique()),
                           big_threshold_contracts=big_thr,
                           big_orders=int((o["qty"] >= big_thr).sum()),
                           footprint_files=nfp,
                           instruments=[int(i) for i in t.instrument_id.unique()])
        if window == "discovery":
            out[window]["recombination_check"] = rc
    NOTES["ticks"] = out
    return big_thr


if __name__ == "__main__":
    build_bars()
    build_ticks()
    (CLEAN).mkdir(parents=True, exist_ok=True)
    (CLEAN / "build_notes.json").write_text(json.dumps(NOTES, indent=2, default=str))
    print(json.dumps(NOTES, indent=2, default=str))
