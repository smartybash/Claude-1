#!/usr/bin/env python3
"""Submit the approved Databento plan, one batch job at a time.

The plan is `reports/databento_register.md` §6. After each submission the billed
cost is compared with its estimate. If billed > estimate the script STOPS and
submits nothing further. Every job is appended to data/databento_ledger.csv.
The API key is read from DATABENTO_API_KEY or .env and never printed.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys
from pathlib import Path

import databento as db

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data/databento_ledger.csv"
END = "2026-09-24T20:30:00Z"
PLAN = [
    ("A", "ohlcv-1m", ["NQ.v.0", "ES.v.0"], "2010-06-06", END, "month", 40.9756),
    ("B1", "trades", ["NQ.v.0"], "2026-03-01T23:00:00Z", "2026-05-29T21:00:00Z", "day", 31.1119),
    ("B2", "trades", ["NQ.v.0"], "2026-08-20T22:00:00Z", END, "day", 10.4055),
    ("B3-06-24", "trades", ["NQ.v.0"], "2026-06-24T13:30:00Z", "2026-06-24T20:00:00Z", "day", 0.4361),
    ("B3-07-09", "trades", ["NQ.v.0"], "2026-07-09T13:30:00Z", "2026-07-09T20:00:00Z", "day", 0.2884),
    ("B3-07-29", "trades", ["NQ.v.0"], "2026-07-29T13:30:00Z", "2026-07-29T20:00:00Z", "day", 0.5572),
    ("B3-08-06", "trades", ["NQ.v.0"], "2026-08-06T13:30:00Z", "2026-08-06T20:00:00Z", "day", 0.3785),
    ("B3-08-19", "trades", ["NQ.v.0"], "2026-08-19T13:30:00Z", "2026-08-19T20:00:00Z", "day", 0.3555),
    ("C", "statistics", ["NQ.v.0"], "2026-03-01", END, "day", 0.0300),
]
CAP = 125.0


def key():
    k = os.environ.get("DATABENTO_API_KEY")
    if k:
        return k
    for line in open(ROOT / ".env"):
        if line.startswith("DATABENTO_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("no API key")


def done_tags():
    """Tags already submitted. Billed cost is only known after processing."""
    with open(LEDGER) as f:
        return {r["job_tag"]: float(r["billed_usd"] or 0) for r in csv.DictReader(f)
                if r["job_tag"] != "pre-existing"}


def wait_billed(c, job_id, est, poll=30, limit=3600):
    """Block until the job is processed and its real cost_usd is known."""
    import time
    t0 = time.time()
    while time.time() - t0 < limit:
        j = [x for x in c.batch.list_jobs(states=["queued", "processing", "done"])
             if x["id"] == job_id][0]
        if j["state"] == "done" and j.get("cost_usd") is not None:
            return float(j["cost_usd"])
        time.sleep(poll)
    sys.exit(f"STOP: {job_id} not billed within {limit}s")


def main():
    c = db.Historical(key())
    prior = done_tags()
    spent = sum(prior.values())
    for tag, sch, sym, s, e, split, est in PLAN:
        if tag in prior:
            print(f"{tag}: already in ledger, skipped (never pay twice)")
            continue
        # re-verify the quote at submission time
        q = c.metadata.get_cost(dataset="GLBX.MDP3", schema=sch, symbols=sym,
                                stype_in="continuous", start=s, end=e)
        # estimates are stored to 4 dp, so allow the half-unit rounding margin
        if q > est + 5e-5:
            sys.exit(f"STOP: {tag} quote {q:.4f} now above the approved {est:.4f}")
        if spent + q > CAP:
            sys.exit(f"STOP: {tag} would take lifetime spend above ${CAP}")
        j = c.batch.submit_job(dataset="GLBX.MDP3", symbols=sym, schema=sch,
                               stype_in="continuous", start=s, end=e,
                               encoding="dbn", compression="zstd",
                               split_duration=split)
        billed = wait_billed(c, j["id"], est)
        spent += billed
        with open(LEDGER, "a", newline="") as f:
            csv.writer(f).writerow([dt.datetime.utcnow().isoformat(timespec="seconds"),
                                    tag, j["id"], sch, ",".join(sym), s, e, split,
                                    f"{est:.4f}", f"{billed:.4f}", j.get("state", ""),
                                    ""])
        print(f"{tag}: job {j['id']}  est ${est:.4f}  billed ${billed:.4f}  "
              f"state {j.get('state')}  lifetime ${spent:.4f}")
        if billed > est + 5e-5:   # stored estimates are 4 dp
            sys.exit(f"STOP: {tag} billed {billed:.4f} above estimate {est:.4f}")
    print(f"all submitted; lifetime spend ${spent:.4f}")


if __name__ == "__main__":
    main()
