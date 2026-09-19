"""How often do CLEAN trend-continuation vs trend-fade (rotation) days occur?

Mechanical day-type classifier on daily OHLC, run over 5 years of QQQ and SPY
(the program's validated NQ/ES proxies - a single NQ futures contract has only
a few liquid months, not enough for a multi-year count). Cross-checks the two
instruments and reports a sensitivity band, because 'clean' is a definitional
choice and the honest answer is a range, not a false-precision single number.

Definitions (per session, ATR20 = 20-day average true range):
  range = H-L ; body = |C-O| ; cl = (C-L)/range ; ol = (O-L)/range

  CLEAN TREND (continuation-tradeable): a one-way expansion day
    range >= EXP*ATR20  AND  body/range >= BODY
    AND (up:   cl >= EDGE and ol <= 1-EDGE)
         (down: cl <= 1-EDGE and ol >= EDGE)

  CLEAN ROTATION/FADE (fade-to-value-tradeable): a balanced day
    range <= ROT*ATR20  AND  MIDLO <= cl <= MIDHI
    AND (H-O) >= SIDE*range AND (O-L) >= SIDE*range   (traded both sides of open)

  else NEUTRAL/mixed (not cleanly tradeable by either playbook)

Reports % of sessions and days-per-month (x ~21 trading days).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TDAYS_PER_MONTH = 21.0


def load_daily(name: str) -> pd.DataFrame:
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True))
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def atr(df: pd.DataFrame, n: int = 20) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def classify(df: pd.DataFrame, EXP, BODY, EDGE, ROT, MIDLO, MIDHI, SIDE) -> pd.Series:
    a = atr(df)
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    cl = (df["close"] - df["low"]) / rng
    ol = (df["open"] - df["low"]) / rng
    body = (df["close"] - df["open"]).abs() / rng
    up_ho = (df["high"] - df["open"]) / rng
    dn_ol = (df["open"] - df["low"]) / rng

    trend_up = (rng >= EXP * a) & (body >= BODY) & (cl >= EDGE) & (ol <= 1 - EDGE)
    trend_dn = (rng >= EXP * a) & (body >= BODY) & (cl <= 1 - EDGE) & (ol >= EDGE)
    trend = trend_up | trend_dn
    rot = (rng <= ROT * a) & (cl >= MIDLO) & (cl <= MIDHI) & (up_ho >= SIDE) & (dn_ol >= SIDE)

    out = pd.Series("neutral", index=df.index)
    out[rot & ~trend] = "rotation"
    out[trend] = "trend"
    return out[a.notna()]


PRESETS = {
    "strict": dict(EXP=1.3, BODY=0.55, EDGE=0.78, ROT=0.85, MIDLO=0.33, MIDHI=0.67, SIDE=0.30),
    "base":   dict(EXP=1.2, BODY=0.50, EDGE=0.72, ROT=1.00, MIDLO=0.30, MIDHI=0.70, SIDE=0.25),
    "loose":  dict(EXP=1.1, BODY=0.45, EDGE=0.68, ROT=1.15, MIDLO=0.28, MIDHI=0.72, SIDE=0.20),
}


def summarize(lbl: pd.Series) -> dict:
    n = len(lbl)
    vc = lbl.value_counts()
    tr, ro = int(vc.get("trend", 0)), int(vc.get("rotation", 0))
    return dict(n=n, trend_pct=tr/n, rot_pct=ro/n,
                trend_pm=tr/n*TDAYS_PER_MONTH, rot_pm=ro/n*TDAYS_PER_MONTH,
                both_pm=(tr+ro)/n*TDAYS_PER_MONTH)


def main():
    files = {"QQQ (5y)": "qqq_daily_5y.json", "SPY (5y)": "spy_daily_5y.json"}
    print("Clean day-type frequency — 5-year daily, NQ/ES proxies\n")
    print(f"{'instrument':11s} {'preset':7s} {'sessions':8s} {'trend%':7s} {'rot%':6s} "
          f"{'trend/mo':8s} {'rot/mo':7s} {'both/mo':7s}")
    print("-" * 72)
    agg = {}
    for lbl, fn in files.items():
        df = load_daily(fn)
        for pr, kw in PRESETS.items():
            s = summarize(classify(df, **kw))
            agg.setdefault(pr, []).append(s)
            print(f"{lbl:11s} {pr:7s} {s['n']:<8d} {s['trend_pct']:<7.1%} {s['rot_pct']:<6.1%} "
                  f"{s['trend_pm']:<8.1f} {s['rot_pm']:<7.1f} {s['both_pm']:<7.1f}")
        print()

    print("=== POOLED (QQQ+SPY) realistic ranges ===")
    for pr in PRESETS:
        rows = agg[pr]
        tpm = np.mean([r["trend_pm"] for r in rows]); rpm = np.mean([r["rot_pm"] for r in rows])
        print(f"  {pr:7s}: ~{tpm:.1f} trend + ~{rpm:.1f} rotation = ~{tpm+rpm:.1f} clean days/month")

    # span for context
    q = load_daily("qqq_daily_5y.json")
    print(f"\nspan: {q.index.min().date()} -> {q.index.max().date()} "
          f"({len(q)} sessions ~ {len(q)/TDAYS_PER_MONTH:.0f} months)")


if __name__ == "__main__":
    main()
