"""Measure the fade edge on the DEEPEST pool our existing data allows.

External deeper history is unavailable (IBKR is at its ~1000-bar/call ceiling;
FMP charts are plan-gated), so this squeezes the maximum sample out of the deep
1h files we already hold — swapping the shallow nq_1h_eth (78 sess) for nq_1h
(128) and adding every deep intraday file. Reuses the validated stretch_filter
machinery; reports fade expectancy vs stretch with CIs at the max sample.

Caveat printed below: 1h and 30m of the same calendar are correlated, so the
pooled n overstates the count of *independent* fades.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.stretch_filter_test as sf

sf.SERIES = [
    ("qqq_1h.json", False, 7), ("spy_1h.json", False, 7),
    ("es_1h.json", True, 7),   ("nq_1h.json", True, 7),
    ("nq_1h_eth.json", True, 7),
    ("qqq_30min.json", False, 13), ("spy_30min.json", False, 13),
    ("es_30min.json", True, 13),   ("nq_30min.json", True, 13),
    ("nq_30min_eth.json", True, 13),
    ("qqq_30m_live.json", False, 13), ("spy_30m_live.json", False, 13),
    ("es_30m_live.json", True, 13),
]

if __name__ == "__main__":
    print(f"DEEP POOL — {len(sf.SERIES)} intraday files (1h + 30m, NQ+ES+QQQ+SPY)\n")
    sf.main()
