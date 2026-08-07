"""Turn a raw IBKR get_price_history payload into a clean data/*.json — WITHOUT
hand-transcribing bars.

WHY: the slow part of a rerun was re-emitting big price arrays through the
editor. Instead, when an MCP get_price_history result is large it auto-saves to
a file on disk; even when it's inline you can paste it into a scratch file. This
script reads that raw payload, normalises it to the canonical 6-key columnar
shape {time,open,high,low,close,volume}, VALIDATES equal array lengths, and
writes data/<name>.json. No manual retyping of bars.

USAGE:
  python3 scripts/ingest_ibkr.py <raw_payload_path> <out_name.json>
  # raw_payload_path: the saved tool-result .txt/.json, or a scratch paste.
  # out_name.json    : written under data/.

Accepts either shape:
  * columnar dict: {"time":[...], "open":[...], ...}  (already our shape)
  * list of bar records: [{"t":..,"o":..,"h":..,"l":..,"c":..,"v":..}, ...]
    (also accepts time/open/high/low/close/volume or datetime/price keys)
Epoch ms/s timestamps are converted to ISO-8601 UTC.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
KEYS = ("time", "open", "high", "low", "close", "volume")
ALIASES = {
    "t": "time", "date": "time", "datetime": "time",
    "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
    "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
}


def _to_iso(vals):
    s = pd.Series(vals)
    if pd.api.types.is_numeric_dtype(s):
        unit = "ms" if float(s.iloc[0]) > 1e11 else "s"
        ts = pd.to_datetime(s, unit=unit, utc=True)
    else:
        ts = pd.to_datetime(s, utc=True)
    return [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in ts]


def normalise(raw) -> dict:
    # unwrap common envelopes
    if isinstance(raw, dict):
        for k in ("data", "bars", "result", "prices", "priceHistory"):
            if k in raw and isinstance(raw[k], (list, dict)):
                raw = raw[k]
                break
    if isinstance(raw, dict):                      # columnar
        cols = {ALIASES.get(k, k): v for k, v in raw.items()}
        out = {k: list(cols[k]) for k in KEYS if k in cols}
    elif isinstance(raw, list):                    # records
        recs = [{ALIASES.get(k, k): v for k, v in r.items()} for r in raw]
        out = {k: [r.get(k) for r in recs] for k in KEYS}
    else:
        raise ValueError("unrecognised payload (not dict or list)")

    # volume is optional (indices like VIX have none) — backfill zeros
    if "volume" not in out or out["volume"] is None or len(out.get("volume", [])) == 0:
        out["volume"] = [0] * len(out.get("time", []))
    required = ("time", "open", "high", "low", "close")
    missing = [k for k in required if k not in out or out[k] is None or len(out[k]) == 0]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    out["time"] = _to_iso(out["time"])
    n = len(out["time"])
    bad = {k: len(out[k]) for k in KEYS if len(out[k]) != n}
    if bad:
        raise ValueError(f"array length mismatch vs time={n}: {bad}")
    # sort by time, drop dup timestamps (keep last)
    df = pd.DataFrame(out).drop_duplicates("time", keep="last").sort_values("time")
    return {k: df[k].tolist() for k in KEYS}


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    raw = json.loads(Path(sys.argv[1]).read_text())
    clean = normalise(raw)
    out = ROOT / "data" / sys.argv[2]
    out.write_text(json.dumps(clean))
    print(f"wrote {out}  ({len(clean['time'])} bars, "
          f"{clean['time'][0]} -> {clean['time'][-1]})")


if __name__ == "__main__":
    main()
