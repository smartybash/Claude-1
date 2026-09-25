#!/usr/bin/env python3
"""Download every completed job in the ledger into data/raw/<tag>/.

Never re-downloads a file that is already present with the right size (batch
files are free to re-download for 30 days, but there is no reason to). The key
is read from DATABENTO_API_KEY or .env and never printed.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_plan import LEDGER, ROOT, key  # noqa: E402

RAW = ROOT / "data/raw"


def main():
    c = db.Historical(key())
    with open(LEDGER) as f:
        rows = [r for r in csv.DictReader(f) if r["job_tag"] != "pre-existing"]
    for r in rows:
        if r["state"] != "done":
            print(f"{r['job_tag']}: state {r['state']}, not downloaded yet")
            continue
        out = RAW / r["job_tag"]
        out.mkdir(parents=True, exist_ok=True)
        files = c.batch.list_files(r["job_id"])
        def have(f):
            hits = list(out.rglob(f["filename"]))   # files land under <job_id>/
            return bool(hits) and hits[0].stat().st_size == f["size"]
        todo = [f for f in files if not have(f)]
        if todo:
            c.batch.download(job_id=r["job_id"], output_dir=out)
        got = sum(1 for f in files if list(out.rglob(f["filename"])))
        size = sum(f["size"] for f in files)
        print(f"{r['job_tag']}: {got}/{len(files)} files, {size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
