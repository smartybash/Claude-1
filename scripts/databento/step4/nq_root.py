#!/usr/bin/env python3
"""Build a stand-in repository root for the G4 archive scripts (Clarification 4).

reports/step4/frozen/root_nq/data/ mirrors data/ by symlink, except that the
QQQ files the archive scripts read are replaced by NQ bars in the same format:
  qqq_daily_full.json, qqq_daily_5y.json   NQ daily RTH (dict of lists: time, OHLCV)
  daily_long/QQQ.csv                        NQ daily RTH (timestamp, OHLCV)
  intraday/qqq_5m_nq.csv                    NQ 5-minute RTH (the only qqq_5m_* file)
  intraday/qqq_1m_nq.csv                    NQ 1-minute RTH (the only qqq_1m_* file)
All prices are ratio back-adjusted NQ; timestamps naive ET. Local only (ignored).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import step4_common as C                                           # noqa: E402

S4 = C.ROOT / "data/clean/step4"
NQR = C.OUT / "frozen" / "root_nq"


def build():
    data = NQR / "data"
    if (data / ".built").exists():
        return NQR
    data.mkdir(parents=True, exist_ok=True)
    override_dirs = {"daily_long", "intraday"}
    override_files = {"qqq_daily_full.json", "qqq_daily_5y.json"}
    for p in (C.ROOT / "data").iterdir():
        if p.name in override_dirs or p.name in override_files:
            continue
        link = data / p.name
        if not link.exists():
            link.symlink_to(p)
    d1 = pd.read_parquet(S4 / "NQ_1m.parquet")
    d1["day"] = d1.timestamp.dt.normalize()
    g = d1.groupby("day")
    daily = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
                          "close": g.close.last(), "volume": g.volume.sum()})
    js = {"time": [t.strftime("%Y-%m-%d") for t in daily.index],
          **{c: daily[c].astype(float).tolist() for c in ("open", "high", "low", "close")},
          "volume": daily.volume.astype(int).tolist()}
    for name in override_files:
        (data / name).write_text(json.dumps(js))
    (data / "daily_long").mkdir(exist_ok=True)
    daily.rename_axis("timestamp").reset_index().to_csv(data / "daily_long/QQQ.csv", index=False)
    for p in (C.ROOT / "data/daily_long").iterdir():
        if p.name != "QQQ.csv" and not (data / "daily_long" / p.name).exists():
            (data / "daily_long" / p.name).symlink_to(p)
    (data / "intraday").mkdir(exist_ok=True)
    for p in (C.ROOT / "data/intraday").iterdir():
        if not (p.name.startswith("qqq_5m_") or p.name.startswith("qqq_1m_")):
            if not (data / "intraday" / p.name).exists():
                (data / "intraday" / p.name).symlink_to(p)
    d1.drop(columns="day").to_csv(data / "intraday/qqq_1m_nq.csv", index=False)
    b5 = pd.read_parquet(S4 / "NQ_5m.parquet") if (S4 / "NQ_5m.parquet").exists() else None
    if b5 is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import g3_gaps_reopen as GR
        b5 = pd.read_parquet(GR.build_5m(S4 / "NQ_1m.parquet", S4 / "NQ_5m.parquet"))
    b5.to_csv(data / "intraday/qqq_5m_nq.csv", index=False)
    (data / ".built").write_text("ok")
    return NQR


if __name__ == "__main__":
    print(build())
