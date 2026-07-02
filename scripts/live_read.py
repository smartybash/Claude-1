"""The 11:00 ET regime read for a given session, plus the ex-post grade.

Usage: python3 scripts/live_read.py [YYYY-MM-DD]   (default: latest session)

QQQ/SPY read from hourly RTH bars with the 5y daily ATR context. NQ/ES read
from 30-min RTH bars; their ATR20 is the ETF ATR scaled by the prior-close
price ratio (justified by the 0.999/0.997 RTH return correlation).
"""

import sys
from datetime import time as dtime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json, rth_only
from regime.filter import read_1100
from regime.indicators import atr, directional_range_capture, label_day_type

DATA = Path(__file__).resolve().parents[1] / "data"


def day_bars(intra: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    bars = rth_only(intra)
    return bars[pd.to_datetime(pd.Series(bars.index.date, index=bars.index)) == date]


def grade(day: pd.DataFrame, atr20: float) -> str:
    o, c = day["open"].iloc[0], day["close"].iloc[-1]
    hi, lo = day["high"].max(), day["low"].min()
    drc = abs(c - o) / (hi - lo) if hi > lo else 0.0
    rng = (hi - lo) / atr20
    if drc >= 0.60 and rng >= 0.80:
        label = "TREND"
    elif drc <= 0.35 or rng <= 0.70:
        label = "CHOP"
    else:
        label = "NEUTRAL"
    direction = "up" if c > o else "down"
    return (f"became {label} ({direction}): open {o:.2f} close {c:.2f}, "
            f"DRC {drc:.2f}, range {rng:.2f} ATR")


def read_instrument(name: str, intra_file: str, date: pd.Timestamp,
                    atr20: float, prior_close: float, atr_ratio: float):
    intra = load_ibkr_json(DATA / intra_file)
    day = day_bars(intra, date)
    if day.empty or day.index[0].time() != dtime(9, 30):
        print(f"{name}: no complete session bars for {date.date()}")
        return
    fh = day[day.index.time < dtime(11, 0)]
    o = float(fh["open"].iloc[0])
    closes = fh["close"]
    path = float(closes.diff().abs().sum() + abs(closes.iloc[0] - o))
    r = read_1100(
        atr20=atr20,
        session_open=o,
        fh_high=float(fh["high"].max()),
        fh_low=float(fh["low"].min()),
        fh_close=float(closes.iloc[-1]),
        fh_path=path,
        gap_atr=abs(o - prior_close) / atr20,
        atr_ratio=atr_ratio,
    )
    print(f"\n{name}  [{date.date()} 11:00 ET]  ATR20 ref = {atr20:.2f}")
    print(f"  state = {r.state}   score = {r.score}/100")
    print(f"  first-90-min: range {r.range_atr} ATR | close position {r.pos} | ER {r.er}"
          + (f" | {'; '.join(r.notes)}" if r.notes else ""))
    if day.index[-1].time() >= dtime(15, 0):
        print(f"  ex-post: {grade(day, atr20)}")


def main():
    qqq_d = load_ibkr_json(DATA / "qqq_daily_5y.json")
    spy_d = load_ibkr_json(DATA / "spy_daily_5y.json")

    if len(sys.argv) > 1:
        date = pd.Timestamp(sys.argv[1])
    else:
        date = pd.Timestamp(qqq_d.index[-1].date())

    ctx = {}
    for sym, d in [("QQQ", qqq_d), ("SPY", spy_d)]:
        a20 = atr(d, 20).shift(1)
        a5 = atr(d, 5).shift(1)
        idx = pd.to_datetime(d.index.date)
        i = idx.get_loc(date)
        ctx[sym] = {
            "atr20": float(a20.iloc[i]),
            "prior_close": float(d["close"].iloc[i - 1]),
            "atr_ratio": float(a5.iloc[i] / a20.iloc[i]),
        }
        read_instrument(sym, f"{sym.lower()}_1h.json", date, **ctx[sym])

    # futures: scale the ETF ATR by the prior-session close ratio
    for name, fn, proxy in [("NQ (Sep26)", "nq_30min.json", "QQQ"),
                            ("ES (Sep26)", "es_30min.json", "SPY")]:
        intra = load_ibkr_json(DATA / fn)
        bars = rth_only(intra)
        dates = pd.to_datetime(pd.Series(bars.index.date, index=bars.index))
        prior_dates = sorted(set(dates[dates < date]))
        if not prior_dates:
            print(f"{name}: no prior session for ATR scaling")
            continue
        prior_close = float(bars[dates == prior_dates[-1]]["close"].iloc[-1])
        scale = prior_close / ctx[proxy]["prior_close"]
        read_instrument(name, fn, date,
                        atr20=ctx[proxy]["atr20"] * scale,
                        prior_close=prior_close,
                        atr_ratio=ctx[proxy]["atr_ratio"])


if __name__ == "__main__":
    main()
