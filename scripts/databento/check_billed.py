#!/usr/bin/env python3
"""Wait for submitted jobs to process, write their real billed cost into the
ledger, and exit non-zero if any billed cost exceeds its estimate."""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_plan import LEDGER, key  # noqa: E402


def main(limit=5400, poll=30):
    c = db.Historical(key())
    t0 = time.time()
    while True:
        rows = list(csv.DictReader(open(LEDGER)))
        mine = [r for r in rows if r["job_tag"] != "pre-existing"]
        jobs = {j["id"]: j for j in c.batch.list_jobs(states=["queued", "processing", "done"])}
        pending = []
        for r in mine:
            j = jobs.get(r["job_id"])
            if j and j["state"] == "done" and j.get("cost_usd") is not None:
                r["billed_usd"] = f"{float(j['cost_usd']):.4f}"
                r["state"] = "done"
                r["notes"] = ""
            else:
                pending.append(r["job_tag"])
                r["state"] = j["state"] if j else "missing"
        w = csv.DictWriter(open(LEDGER, "w", newline=""), fieldnames=list(rows[0].keys()))
        w.writeheader()
        [w.writerow(r) for r in rows]
        if not pending:
            break
        if time.time() - t0 > limit:
            print(f"TIMEOUT, still pending: {pending}")
            return 3
        time.sleep(poll)
    over = [(r["job_tag"], r["est_usd"], r["billed_usd"]) for r in mine
            if float(r["billed_usd"]) > float(r["est_usd"]) + 5e-5]
    total = sum(float(r["billed_usd"]) for r in rows)
    for r in mine:
        print(f"{r['job_tag']:<10} est {r['est_usd']:>8}  billed {r['billed_usd']:>8}")
    print(f"lifetime billed ${total:.4f}")
    if over:
        print(f"STOP: billed above estimate: {over}")
        return 2
    print("all billed <= estimate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
