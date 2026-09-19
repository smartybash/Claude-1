"""Rebuild data/parquet/ from every raw IBKR JSON fetch in data/.

Idempotent; run after any new fetch (MCP pull or scripts/fetch_intraday.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sweeplib.data import build_cache

if __name__ == "__main__":
    build_cache()
