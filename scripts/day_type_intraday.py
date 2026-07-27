"""Clean trend / rotation day frequency — INTRADAY version.

The daily-bar study (day_type_frequency.py) can't see whether the intraday
PATH was clean. This one does, using per-session intraday features that daily
OHLC cannot produce:

  * Kaufman EFFICIENCY RATIO  er = |close-open| / sum|bar-to-bar close change|
      er -> 1.0 = a straight, one-way (clean trend) path
      er -> 0.0 = lots of back-and-forth (chop / rotation)
    This is the metric a strict day trader actually cares about, and it is the
    whole reason daily bars are an approximation.
  * close location in range  cl = (close-L)/range
  * range vs trailing 20-session average range  rr

Definitions (per RTH session):
  CLEAN TREND (continuation): er >= EER  AND (cl >= CE or cl <= 1-CE) AND rr >= EXP
  CLEAN ROTATION (fade):      er <= RER  AND MIDLO <= cl <= MIDHI      AND rr <= ROT
  else NEUTRAL

Run across QQQ+SPY at 30/15/60-min so the reader sees the number is stable to
bar size. HONEST LIMITATION: the MCP feed caps at 1000 bars with no backward
paging, so the intraday sample is MONTHS (30m ~77 sessions), not the 5 years
the daily study had. Intraday truth, smaller sample - the opposite trade-off.
Years of intraday needs the local-TWS fetch (scripts/fetch_intraday.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ET = "America/New_York"
TDAYS = 21.0


def load_rth(name: str) -> pd.DataFrame:
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    df = df[~df.index.duplicated(keep="last")].sort_index()
    t = df.index.time
    return df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]


def session_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, g in df.groupby(df.index.date):
        if len(g) < 5:
            continue
        o, c = g["open"].iloc[0], g["close"].iloc[-1]
        H, L = g["high"].max(), g["low"].min()
        rng = H - L
        if rng <= 0:
            continue
        moves = g["close"].diff().abs().sum()
        er = abs(c - o) / moves if moves > 0 else 0.0
        rows.append(dict(date=pd.Timestamp(d), er=er, cl=(c - L) / rng, rng=rng))
    f = pd.DataFrame(rows).set_index("date")
    f["avg_rng"] = f["rng"].rolling(20, min_periods=10).mean()
    f["rr"] = f["rng"] / f["avg_rng"]
    return f.dropna(subset=["rr"])


def classify(f: pd.DataFrame, EER, CE, EXP, RER, MIDLO, MIDHI, ROT) -> pd.Series:
    trend = (f["er"] >= EER) & ((f["cl"] >= CE) | (f["cl"] <= 1 - CE)) & (f["rr"] >= EXP)
    rot = (f["er"] <= RER) & (f["cl"] >= MIDLO) & (f["cl"] <= MIDHI) & (f["rr"] <= ROT)
    out = pd.Series("neutral", index=f.index)
    out[rot & ~trend] = "rotation"
    out[trend] = "trend"
    return out


PRESETS = {
    "strict": dict(EER=0.55, CE=0.80, EXP=1.20, RER=0.25, MIDLO=0.33, MIDHI=0.67, ROT=0.90),
    "base":   dict(EER=0.45, CE=0.75, EXP=1.10, RER=0.32, MIDLO=0.30, MIDHI=0.70, ROT=1.00),
    "loose":  dict(EER=0.38, CE=0.70, EXP=1.00, RER=0.38, MIDLO=0.28, MIDHI=0.72, ROT=1.10),
}

SETS = {
    "NQ 1h":   "nq_1h.json",     "ES 1h":   "es_1h.json",
    "QQQ 1h":  "qqq_1h.json",    "SPY 1h":  "spy_1h.json",
    "QQQ 30m": "qqq_30min.json", "SPY 30m": "spy_30min.json",
    "QQQ 15m": "qqq_15min.json", "SPY 15m": "spy_15min.json",
}
POOL_1H = ["NQ 1h", "ES 1h", "QQQ 1h", "SPY 1h"]  # 4-instrument breadth pool


def main():
    print("Clean day-type frequency — INTRADAY (efficiency-ratio) classifier\n")
    print(f"{'set':9s} {'preset':7s} {'sess':5s} {'trend%':7s} {'rot%':6s} "
          f"{'trend/mo':8s} {'rot/mo':7s} {'both/mo':7s}  {'span'}")
    print("-" * 82)
    feats = {}
    for lbl, fn in SETS.items():
        try:
            f = session_features(load_rth(fn))
        except FileNotFoundError:
            continue
        feats[lbl] = f
        for pr, kw in PRESETS.items():
            lab = classify(f, **kw); n = len(lab); vc = lab.value_counts()
            tr, ro = int(vc.get("trend", 0)), int(vc.get("rotation", 0))
            span = f"{f.index.min().date()}->{f.index.max().date()}"
            print(f"{lbl:9s} {pr:7s} {n:<5d} {tr/n:<7.1%} {ro/n:<6.1%} "
                  f"{tr/n*TDAYS:<8.1f} {ro/n*TDAYS:<7.1f} {(tr+ro)/n*TDAYS:<7.1f}  {span}")
        print()

    # pooled across the 4-instrument 1h breadth sample (NQ+ES+QQQ+SPY)
    print("=== POOLED 4-instrument 1h sample (NQ+ES+QQQ+SPY) ===")
    for pr, kw in PRESETS.items():
        tot_tr = tot_ro = tot_n = 0
        for lbl in POOL_1H:
            if lbl not in feats:
                continue
            lab = classify(feats[lbl], **kw); vc = lab.value_counts()
            tot_tr += int(vc.get("trend", 0)); tot_ro += int(vc.get("rotation", 0)); tot_n += len(lab)
        print(f"  {pr:7s}: ~{tot_tr/tot_n*TDAYS:.1f} trend + ~{tot_ro/tot_n*TDAYS:.1f} rotation "
              f"= ~{(tot_tr+tot_ro)/tot_n*TDAYS:.1f} clean days/month   (n={tot_n} session-obs)")


if __name__ == "__main__":
    main()
