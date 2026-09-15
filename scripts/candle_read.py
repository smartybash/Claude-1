"""Multi-timeframe candlestick read with entry/stop/target at the key levels.

Reads the cached 5-min NQ data, resamples to 10/15/30-min, detects the usual
price-action patterns (engulfing, pin/rejection, inside bar, momentum/
displacement, doji) on recent bars of each timeframe, and - crucially - only
treats a pattern as ACTIONABLE when it prints AT a key level (overnight
VAH/POC/VAL, prior-day H/L) in the direction the multi-week trend gate allows.

Output per timeframe: the last few bars tagged with any pattern, and a synthesis
line giving a concrete entry / stop / target for the best current signal.

This is a DISCRETIONARY read as-of the last cached bar - not a validated edge
and not a live tape. Entries are candle-based (stop beyond the signal bar),
which is the tight-stop execution the level tools can't express on their own.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import volume_profile

ET = "America/New_York"


def load5() -> pd.DataFrame:
    r = json.loads((ROOT / "data" / "nq_5min_eth_live.json").read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    o = df.resample(rule, origin="start_day", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna()


def patterns(g: pd.DataFrame) -> list[tuple]:
    """Tag each bar with any pattern. Returns [(ts, tag, signalprice, dir), ...]
    dir: +1 bullish, -1 bearish, 0 neutral."""
    out = []
    b = g.reset_index()
    ac = (b["close"] - b["open"]).abs()
    avg_body = ac.rolling(10, min_periods=3).mean()
    for i in range(1, len(b)):
        o, h, l, c = b.loc[i, ["open", "high", "low", "close"]]
        po, ph, pl, pc = b.loc[i - 1, ["open", "high", "low", "close"]]
        rng = h - l
        body = abs(c - o)
        if rng <= 0:
            continue
        uw, lw = h - max(o, c), min(o, c) - l
        tags = []
        # engulfing
        if c > o and pc < po and c >= po and o <= pc:
            tags.append(("bull engulf", l, +1))
        if c < o and pc > po and c <= po and o >= pc:
            tags.append(("bear engulf", h, -1))
        # pin / rejection
        if lw >= 2 * body and uw <= body and body > 0:
            tags.append(("hammer (rej low)", l, +1))
        if uw >= 2 * body and lw <= body and body > 0:
            tags.append(("shooting star (rej high)", h, -1))
        # momentum / displacement
        if avg_body[i] and body >= 1.5 * avg_body[i] and body / rng >= 0.65:
            tags.append((f"momentum {'up' if c > o else 'down'}", l if c > o else h, 1 if c > o else -1))
        # inside bar / doji
        if h < ph and l > pl:
            tags.append(("inside bar", c, 0))
        if body <= 0.1 * rng:
            tags.append(("doji", c, 0))
        for t, sp, d in tags:
            out.append((b.loc[i, "index"], t, float(sp), d))
    return out


def main():
    df = load5()
    now = df.index[-1]
    cur = now.normalize()
    # overnight VAH/POC/VAL for today
    on = df[(df.index >= (cur - pd.Timedelta(days=1)).replace(hour=18)) &
            (df.index < cur.replace(hour=9, minute=30))]
    poc, vah, val = volume_profile(on, 50) if len(on) >= 10 else (None, None, None)
    levels = {"VAH": vah, "POC": poc, "VAL": val}
    cur_px = float(df["close"].iloc[-1])
    tol = 0.0012 * cur_px  # "at a level" = within ~0.12%

    print(f"NQ candlestick read — as of {now:%a %Y-%m-%d %H:%M} ET   price {cur_px:.0f}")
    if vah:
        print(f"levels: VAH {vah:.0f} | POC {poc:.0f} | VAL {val:.0f}   (at-level tol +-{tol:.0f}pt)")
    print()

    signals = []
    for rule, lbl in [("5min", "5m"), ("10min", "10m"), ("15min", "15m"), ("30min", "30m")]:
        g = resample(df, rule)
        g = g[g.index.normalize() == cur]  # today's session bars
        if len(g) < 3:
            continue
        pats = patterns(g)
        recent = [p for p in pats if p[0] >= now - pd.Timedelta(hours=2)]
        print(f"--- {lbl} (last {min(6,len(g))} bars) ---")
        for ts, row in g.tail(6).iterrows():
            tag = ", ".join(t for (pt, t, sp, d) in [(p[0], p[1], p[2], p[3]) for p in pats] if pt == ts)
            arrow = "^" if row["close"] >= row["open"] else "v"
            print(f"  {ts:%H:%M} {arrow} O{row['open']:.0f} H{row['high']:.0f} L{row['low']:.0f} C{row['close']:.0f}"
                  + (f"   << {tag}" if tag else ""))
        # actionable: recent pattern printing AT a level
        for ts, t, sp, d in recent:
            if d == 0:
                continue
            for lname, lv in levels.items():
                if lv and abs(sp - lv) <= tol:
                    signals.append((lbl, ts, t, d, lname, lv, sp))
        print()

    print("=== ACTIONABLE candle signals AT a level (last 2h) ===")
    if not signals:
        print("  none — no directional pattern printed at VAH/POC/VAL in the window.")
    for lbl, ts, t, d, lname, lv, sp in signals:
        side = "LONG" if d > 0 else "SHORT"
        if d > 0:
            entry, stop = float(df["close"].asof(ts)), sp - 8
            tgt = poc if lname == "VAL" else vah
        else:
            entry, stop = float(df["close"].asof(ts)), sp + 8
            tgt = poc if lname == "VAH" else val
        risk = abs(entry - stop)
        rr = abs(entry - tgt) / risk if risk else float("nan")
        print(f"  [{lbl}] {ts:%H:%M} {t} at {lname} {lv:.0f} -> {side} "
              f"entry~{entry:.0f} stop {stop:.0f} (risk {risk:.0f}pt) target {tgt:.0f} = {rr:.1f}R")


if __name__ == "__main__":
    main()
