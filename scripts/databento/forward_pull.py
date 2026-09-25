#!/usr/bin/env python3
"""Monthly forward pull of NQ 1-minute bars (decision P8, standing approval).

    python3 scripts/databento/forward_pull.py [--dry-run]

Rule (P8, user, 2026-09-25): one pull a month of `ohlcv-1m` `NQ.v.0`
(GLBX.MDP3), **max USD 1 per pull**, logged in data/databento_ledger.csv, no
per-pull approval. Lifetime cap unchanged (USD 125). The budget checks are kept:
  1. window = from the end of the last NQ ohlcv-1m pull in the ledger to 00:00 UTC
     on the 1st of the current month (whole months only; nothing if none has
     completed);
  2. quote with metadata.get_cost; STOP if the quote > $1.00 or lifetime + quote >
     $125;
  3. one batch job; wait until billed; append to the ledger; STOP (exit 2) if
     billed > quote;
  4. download to data/raw/FWD-YYYY-MM/, append the bars to data/clean/bars_1m
     (same schema as build_derived.py), recompute NQ rolls and rebuild the step-4
     RTH series (data/clean/step4/NQ_1m.parquet + factors).
Everything written is Databento-derived and gitignored. The API key comes from
DATABENTO_API_KEY or .env and is never printed.
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_plan import CAP, LEDGER, ROOT, key, wait_billed          # noqa: E402

MAX_PULL = 1.00
SYM = "NQ.v.0"
RAW, CLEAN = ROOT / "data/raw", ROOT / "data/clean"


def ledger_rows():
    with open(LEDGER) as f:
        return list(csv.DictReader(f))


def window(now=None):
    rows = [r for r in ledger_rows() if r["schema"] == "ohlcv-1m" and "NQ.v.0" in r["symbols"]
            and r["state"] == "done"]
    start = max(pd.Timestamp(r["end"]) for r in rows)
    now = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    end = pd.Timestamp(year=now.year, month=now.month, day=1, tz="UTC")
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    return start, end


def build(tag):
    import databento as db
    import build_derived as BD
    import step4_adapters as AD
    fs = sorted((RAW / tag).rglob("*.ohlcv-1m.dbn.zst"))
    if not fs:
        sys.exit(f"STOP: no files downloaded for {tag}")
    d = pd.concat([db.DBNStore.from_file(str(f)).to_df().reset_index() for f in fs], ignore_index=True)
    d = d[["ts_event", "instrument_id", "open", "high", "low", "close", "volume"]] \
        .rename(columns={"ts_event": "ts_utc"})
    d = pd.concat([d, BD.et_cols(d.ts_utc)], axis=1)
    written = []
    for per, g in d.groupby(d.ts_et.dt.strftime("%Y-%m")):
        p = CLEAN / "bars_1m" / f"NQ_{per}.parquet"
        if p.exists():
            old = pd.read_parquet(p)
            g = pd.concat([old, g[old.columns]], ignore_index=True)
        g = g.drop_duplicates("ts_utc", keep="first").sort_values("ts_utc")
        g.to_parquet(p, index=False, compression="zstd")
        written.append((p.name, len(g)))
    # rolls over the whole NQ history, then the step-4 RTH series and factors
    allb = AD.load_1m("NQ").sort_values("ts_utc").reset_index(drop=True)
    R = BD.rolls(allb.assign(symbol="NQ"), "NQ")
    R.to_csv(CLEAN / "rolls" / "NQ_rolls.csv", index=False)
    info = AD.build_bars("NQ")
    return written, len(R), info


def main(dry=False):
    import databento as db
    start, end = window()
    if end <= start + pd.Timedelta(hours=1):
        print(f"nothing to pull: last NQ bars end {start}, no whole month completed since")
        return 0
    tag = f"FWD-{(end - pd.Timedelta(days=1)).strftime('%Y-%m')}"
    if tag in {r["job_tag"] for r in ledger_rows()}:
        print(f"{tag} already in the ledger; never pay twice")
        return 0
    c = db.Historical(key())
    s, e = start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
    avail = pd.Timestamp(c.metadata.get_dataset_range(dataset="GLBX.MDP3")["end"])
    if avail < end:
        print(f"{tag}: data available only to {avail}; the month is not complete at Databento yet, retry later")
        return 0
    q = float(c.metadata.get_cost(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[SYM],
                                  stype_in="continuous", start=s, end=e))
    spent = sum(float(r["billed_usd"] or 0) for r in ledger_rows())
    print(f"{tag}: {SYM} ohlcv-1m {s} -> {e}  quote ${q:.4f}  lifetime ${spent:.4f}")
    if q > MAX_PULL:
        sys.exit(f"STOP: quote ${q:.4f} above the P8 limit ${MAX_PULL:.2f}")
    if spent + q > CAP:
        sys.exit(f"STOP: lifetime would reach ${spent + q:.4f} > ${CAP}")
    if dry:
        print("dry run: nothing submitted")
        return 0
    est = round(q, 4)
    j = c.batch.submit_job(dataset="GLBX.MDP3", symbols=[SYM], schema="ohlcv-1m",
                           stype_in="continuous", start=s, end=e, encoding="dbn",
                           compression="zstd", split_duration="month")
    billed = wait_billed(c, j["id"], est)
    with open(LEDGER, "a", newline="") as f:
        csv.writer(f).writerow([dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), tag,
                                j["id"], "ohlcv-1m", SYM, s, e, "month", f"{est:.4f}", f"{billed:.4f}",
                                "done", "P8 standing monthly forward pull"])
    print(f"{tag}: job {j['id']} est ${est:.4f} billed ${billed:.4f} lifetime ${spent + billed:.4f}")
    if billed > est + 5e-5:
        print(f"STOP: billed ${billed:.4f} above estimate ${est:.4f}")
        return 2
    out = RAW / tag
    out.mkdir(parents=True, exist_ok=True)
    c.batch.download(job_id=j["id"], output_dir=out)
    written, n_rolls, info = build(tag)
    print(f"bars written {written}; NQ rolls {n_rolls}; step-4 RTH series {info}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv))
