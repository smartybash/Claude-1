"""Backtest the confluence zones over NQ history: which zones actually hold?

For each session, build confluence zones AS-OF that session's open (no
lookahead), walk the session's 30-min bars, and for each first-touch of a zone
test whether a FADE off it worked: did price reverse >=TGT off the zone before
breaking THROUGH by >=BRK? Aggregate the hold-rate by score bucket, by key
constituent, and by day-regime -> learn the filter for the strongest setups.

Honest scope: ~1 month of 30-min NQ (front contract) = ~20 sessions, many
touch-events. Diagnostic, not statistically validated - a small sample, one
instrument. Directional learning only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import round_numbers, round_step, volume_profile

ET = "America/New_York"
TGT, BRK, HORIZON = 40.0, 25.0, 6  # reverse 40pt = hold; 25pt beyond = fail; within 6 bars


def load(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def swings(df, k, recent):
    h, l = df["high"].values, df["low"].values
    n = len(df); out = []
    for i in range(k, n - k):
        if h[i] == max(h[i - k:i + k + 1]):
            out.append((float(h[i]), i))
        if l[i] == min(l[i - k:i + k + 1]):
            out.append((float(l[i]), i))
    return [p for p, i in out if i >= n - recent]


def zones_asof(hist, sessions_prior):
    """Confluence zones from 30m history up to (not incl) the session open."""
    px = float(hist["close"].iloc[-1])
    lv = []
    for p in swings(hist, 6, 80): lv.append((p, "sw4h", 3.0))   # coarse swing ~ 4h
    for p in swings(hist, 3, 120): lv.append((p, "sw1h", 2.0))  # finer swing ~ 1h
    poc, vah, val = volume_profile(hist.iloc[-10 * 13:], 60)     # ~10-session composite
    lv += [(vah, "cVAH", 2.5), (poc, "cPOC", 2.5), (val, "cVAL", 2.5)]
    if sessions_prior:
        pg = sessions_prior[-1]
        lv += [(float(pg["high"].max()), "PDH", 2.0), (float(pg["low"].min()), "PDL", 2.0),
               (float(pg["close"].iloc[-1]), "PDC", 1.5)]
    for p in round_numbers(px, round_step(px), 3): lv.append((p, "round", 1.0))
    lv.sort()
    tol = 0.0018 * px
    zones, cl = [], [lv[0]]
    for x in lv[1:]:
        if x[0] - cl[-1][0] <= tol: cl.append(x)
        else: zones.append(cl); cl = [x]
    zones.append(cl)
    out = []
    for z in zones:
        w = sum(a[2] for a in z)
        price = sum(a[0] * a[2] for a in z) / w
        out.append(dict(price=price, lo=min(a[0] for a in z), hi=max(a[0] for a in z),
                        w=w, labs=set(a[1] for a in z)))
    return out


def qqq_zones_asof(qh1, cutoff):
    """QQQ confluence zone centers (score>=5) as-of cutoff, from QQQ 1h."""
    hist = qh1[qh1.index < cutoff]
    if len(hist) < 60:
        return [], None
    qpx = float(hist["close"].iloc[-1])
    lv = []
    for p in swings(hist, 6, 80): lv.append((p, 3.0))
    for p in swings(hist, 3, 120): lv.append((p, 2.0))
    poc, vah, val = volume_profile(hist.iloc[-70:], 50)
    lv += [(vah, 2.5), (poc, 2.5), (val, 2.5)]
    for p in round_numbers(qpx, round_step(qpx), 3): lv.append((p, 1.0))
    lv.sort(); tol = 0.0018 * qpx
    zones, cl = [], [lv[0]]
    for x in lv[1:]:
        if x[0] - cl[-1][0] <= tol: cl.append(x)
        else: zones.append(cl); cl = [x]
    zones.append(cl)
    strong = [sum(a[0] * a[1] for a in z) / sum(a[1] for a in z) for z in zones if sum(a[1] for a in z) >= 5]
    return strong, qpx


def main():
    df = load("nq_30min_eth.json")
    try:
        qh1 = load("qqq_1h.json")
    except FileNotFoundError:
        qh1 = None
    df["sess"] = pd.Series(df.index.date, index=df.index)
    ev = df.index.hour >= 18
    df.loc[ev, "sess"] = (df.index[ev] + pd.Timedelta(days=1)).date
    sess_ids = sorted(df["sess"].unique())
    by_sess = {s: df[df["sess"] == s] for s in sess_ids}

    events = []
    for i, s in enumerate(sess_ids):
        if i < 6:  # warmup for swings/composite
            continue
        hist = df[df.index < pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)]
        if len(hist) < 60:
            continue
        prior = [by_sess[x] for x in sess_ids[:i]]
        zs = zones_asof(hist, prior)
        rth = by_sess[s]
        rth = rth[(rth.index.time >= pd.Timestamp("09:30").time()) &
                  (rth.index.time < pd.Timestamp("16:00").time())]
        if len(rth) < 6:
            continue
        # QQQ cross-ref: scaled QQQ strong-zone centers as-of this session
        q_scaled = []
        if qh1 is not None:
            cutoff = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            qstrong, qpx = qqq_zones_asof(qh1, cutoff)
            if qpx:
                scale = float(rth["open"].iloc[0]) / qpx
                q_scaled = [qp * scale for qp in qstrong]
        for z in zs:
            z["qconf"] = any(z["lo"] - 20 <= qp <= z["hi"] + 20 for qp in q_scaled)
        # day regime (efficiency ratio)
        o, c = rth["close"].iloc[0], rth["close"].iloc[-1]
        er = abs(c - o) / rth["close"].diff().abs().sum() if rth["close"].diff().abs().sum() else 0
        regime = "trend" if er >= 0.4 else "balance"
        touched = set()
        arr = rth.reset_index()
        for bi in range(len(arr)):
            hi, lo = arr["high"][bi], arr["low"][bi]
            for zi, z in enumerate(zs):
                if zi in touched:
                    continue
                res = z["price"] > c if False else None  # side by touch direction
                # resistance touch (approach from below): bar high enters zone
                if lo < z["lo"] and hi >= z["lo"]:
                    side = "res"; edge_far = z["hi"]
                elif hi > z["hi"] and lo <= z["hi"]:
                    side = "sup"; edge_far = z["lo"]
                else:
                    continue
                touched.add(zi)
                # outcome over next HORIZON bars
                fut = arr.iloc[bi:bi + HORIZON + 1]
                hold = fail = False
                if side == "res":
                    for _, fr in fut.iterrows():
                        if fr["low"] <= z["lo"] - TGT: hold = True; break
                        if fr["high"] >= edge_far + BRK: fail = True; break
                else:
                    for _, fr in fut.iterrows():
                        if fr["high"] >= z["hi"] + TGT: hold = True; break
                        if fr["low"] <= edge_far - BRK: fail = True; break
                if hold or fail:
                    events.append(dict(score=z["w"], labs=z["labs"], regime=regime,
                                       side=side, hold=hold, qconf=z.get("qconf", False),
                                       nlabs=len(z["labs"])))
    e = pd.DataFrame(events)
    if e.empty:
        print("no events"); return
    print(f"CONFLUENCE BACKTEST — {len(e)} touch-events over {len(sess_ids)-6} sessions "
          f"(fade: reverse {TGT:.0f}pt=hold vs {BRK:.0f}pt-through=fail)\n")

    print("HOLD-RATE by score bucket:")
    for name, m in [("<5", e.score < 5), ("5-8", (e.score >= 5) & (e.score < 8)), (">=8 (A+)", e.score >= 8)]:
        g = e[m]
        if len(g): print(f"  score {name:9s}: {g.hold.mean():.0%} hold  (n={len(g)})")

    print("\nHOLD-RATE by grade (QQQ cross-ref):")
    a = e[e.score >= 8]
    for name, m in [("A++ (>=8 & QQQ-confirmed)", a[a.qconf]), ("A+ (>=8, NQ-only)", a[~a.qconf]),
                    ("weak (<8)", e[e.score < 8])]:
        if len(m): print(f"  {name:28s}: {m.hold.mean():.0%} hold  (n={len(m)})")

    print("\nHOLD-RATE by # distinct level-types in zone:")
    for lo, hiq, lab in [(1, 1, "1 (lone level - noise)"), (2, 3, "2-3"), (4, 99, "4+ (dense)")]:
        g = e[(e.nlabs >= lo) & (e.nlabs <= hiq)]
        if len(g): print(f"  {lab:24s}: {g.hold.mean():.0%} hold  (n={len(g)})")

    print("\nHOLD-RATE by regime (A+ only, score>=8):")
    a = e[e.score >= 8]
    for r in ("balance", "trend"):
        g = a[a.regime == r]
        if len(g): print(f"  {r:8s}: {g.hold.mean():.0%} hold  (n={len(g)})")

    print("\nHOLD-RATE by constituent (score>=5):")
    s5 = e[e.score >= 5]
    for lab in ["cVAH", "cVAL", "cPOC", "sw4h", "sw1h", "PDH", "PDL", "round"]:
        g = s5[s5.labs.apply(lambda x: lab in x)]
        if len(g) >= 4: print(f"  contains {lab:6s}: {g.hold.mean():.0%} hold  (n={len(g)})")

    # recommended filter
    best = e[(e.score >= 8)]
    bt = best[best.regime == "balance"]
    print(f"\nSTRONGEST FILTER (A+ score>=8 on balance days): "
          f"{bt.hold.mean():.0%} hold, n={len(bt)}  vs baseline all-events {e.hold.mean():.0%}")


if __name__ == "__main__":
    main()
