"""Confluence backtest — MULTI-INSTRUMENT, MULTI-TIMEFRAME, with a null.

Answers honestly: do confluence zones hold better than chance, and which
filters (score, #sources) actually matter - on a sample big enough to trust.

Method, per instrument x timeframe series:
  * split into RTH sessions; for each session (after warmup) build confluence
    zones AS-OF the open from that instrument's own prior bars (no lookahead):
    swing pivots (k=3 & k=6), ~10-session composite value area, prior-session
    H/L/C, round numbers -> cluster -> score & #distinct-sources.
  * walk the session; on first touch of a zone test a FADE: reverse >= TGT
    (0.14% of price) = HOLD, or push THROUGH >= BRK (0.09%) = FAIL, within
    HORIZON bars.
  * NULL: same test on random price levels (same count/session) -> baseline.

Pools NQ(1h,30m) + QQQ(1h,30m) + SPY(1h,30m). Report hold-rate by score bucket
and by #sources, each with n, vs the random null. Honest scope: ~Dec-Jul,
correlated equity-index instruments - a real sample (hundreds of events) but
not multi-year-independent.
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
TGT_F, BRK_F, HORIZON = 0.0012, 0.0012, 5  # symmetric 1:1: reverse=hold vs through=fail, within HORIZON bars
RNG = np.random.default_rng(20260730)

# (file, is_futures, bars_per_rth_session)
SERIES = [
    ("nq_1h_eth.json", True, 7), ("nq_30min_eth.json", True, 13),
    ("qqq_1h.json", False, 7), ("qqq_30min.json", False, 13),
    ("spy_1h.json", False, 7), ("spy_30min.json", False, 13),
]


def load(name):
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def swings(df, k, recent):
    h, l = df["high"].values, df["low"].values
    n = len(df); out = []
    for i in range(k, n - k):
        if h[i] == max(h[i - k:i + k + 1]): out.append((float(h[i]), i))
        if l[i] == min(l[i - k:i + k + 1]): out.append((float(l[i]), i))
    return [p for p, i in out if i >= n - recent]


def shelves(df, k=8, lookback=600, disp=0.012):
    """Congestion shelves price LEFT on an impulse (supply/demand memory):
    a significant fractal high/low (extreme over 2k+1 bars) that price then
    displaced away from by >=disp within the next ~2k bars. A swing high price
    later dropped >=disp below = breakdown supply; a swing low price later
    rallied >=disp above = breakout demand. Long lookback so ETH bars (~37/session)
    don't erase multi-day structure the way the short swing window does."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(df); out = []
    lo = max(k, n - lookback)
    for i in range(lo, n - k):
        fwd = c[i + 1: min(i + 2 * k + 1, n)]
        if len(fwd) == 0:
            continue
        if h[i] == max(h[i - k:i + k + 1]) and (h[i] - fwd.min()) >= disp * h[i]:
            out.append(float(h[i]))          # broke DOWN from here -> supply
        if l[i] == min(l[i - k:i + k + 1]) and (fwd.max() - l[i]) >= disp * l[i]:
            out.append(float(l[i]))          # broke UP from here -> demand
    return out


def channel_fit(close, lookback=150, k=2.0, min_len=14):
    """Linear-regression channel over the current leg (objective, no lookahead).
    Anchor at the leg origin (window min for an up-leg / max for a down-leg),
    regress closes to now, rails = fit +/- k*residual-sigma."""
    close = np.asarray(close, float)
    n = len(close)
    lb = min(lookback, n)
    w = close[-lb:]; base = n - lb
    anchor = base + (int(np.argmin(w)) if close[-1] >= w[0] else int(np.argmax(w)))
    if n - anchor < min_len:
        anchor = base
    x = np.arange(anchor, n)
    slope, intercept = np.polyfit(x, close[anchor:], 1)
    mid = slope * x + intercept
    sd = float((close[anchor:] - mid).std())
    return dict(anchor=anchor, slope=float(slope), intercept=float(intercept), sd=sd, k=k)


def zone_rail_conf(close, zone_price, n_ahead, tol):
    """True if a channel rail sweeps within tol of zone_price across the next
    n_ahead bars (i.e. rail meets the horizontal level during the session)."""
    ch = channel_fit(close)
    n = len(close); b = ch["intercept"]; s = ch["slope"]; off = ch["k"] * ch["sd"]
    x0, x1 = n - 1, n - 1 + n_ahead
    for sign in (+1, -1):                       # upper, lower rail
        a = s * x0 + b + sign * off
        c = s * x1 + b + sign * off
        if min(a, c) - tol <= zone_price <= max(a, c) + tol:
            return True
    return False


def build(hist, prior_sess, bps):
    px = float(hist["close"].iloc[-1])
    lv = []
    for p in swings(hist, 6, 80): lv.append((p, "sw_hi", 3.0))
    for p in swings(hist, 3, 120): lv.append((p, "sw_lo", 2.0))
    for p in shelves(hist): lv.append((p, "shelf", 3.0))
    if len(hist) > bps * 3:
        poc, vah, val = volume_profile(hist.iloc[-bps * 10:], 50)
        lv += [(vah, "cVAH", 2.5), (poc, "cPOC", 2.5), (val, "cVAL", 2.5)]
    if prior_sess is not None and len(prior_sess) > 3:
        lv += [(float(prior_sess["high"].max()), "PDH", 2.0),
               (float(prior_sess["low"].min()), "PDL", 2.0),
               (float(prior_sess["close"].iloc[-1]), "PDC", 1.5)]
    for p in round_numbers(px, round_step(px), 3): lv.append((p, "round", 1.0))
    lv.sort(); tol = 0.0018 * px
    zones, cl = [], [lv[0]]
    for x in lv[1:]:
        if x[0] - cl[-1][0] <= tol: cl.append(x)
        else: zones.append(cl); cl = [x]
    zones.append(cl)
    out = []
    for z in zones:
        w = sum(a[2] for a in z)
        out.append(dict(price=sum(a[0] * a[2] for a in z) / w, lo=min(a[0] for a in z),
                        hi=max(a[0] for a in z), w=w, nt=len({a[1] for a in z})))
    return out, px


def test_touch(z, arr, bi, px):
    hi, lo = arr["high"][bi], arr["low"][bi]
    tgt, brk = TGT_F * px, BRK_F * px
    if lo < z["lo"] and hi >= z["lo"]:
        side, far = "res", z["hi"]
    elif hi > z["hi"] and lo <= z["hi"]:
        side, far = "sup", z["lo"]
    else:
        return None
    for j in range(bi, min(bi + HORIZON + 1, len(arr))):
        if side == "res":
            if arr["low"][j] <= z["lo"] - tgt: return True
            if arr["high"][j] >= far + brk: return False
        else:
            if arr["high"][j] >= z["hi"] + tgt: return True
            if arr["low"][j] <= far - brk: return False
    return None


def main():
    ev, nullev = [], []
    n_sessions = 0
    for fname, fut, bps in SERIES:
        try:
            df = load(fname)
        except FileNotFoundError:
            continue
        if fut:
            sess = pd.Series(df.index.date, index=df.index)
            evb = df.index.hour >= 18
            sess[evb] = (df.index[evb] + pd.Timedelta(days=1)).date
        else:
            sess = pd.Series(df.index.date, index=df.index)
        df = df.assign(sess=pd.to_datetime(sess.values))
        sids = sorted(df["sess"].unique())
        bysess = {s: df[df["sess"] == s] for s in sids}
        for i, s in enumerate(sids):
            if i < 8:
                continue
            opent = pd.Timestamp(s).tz_localize(ET).replace(hour=9, minute=30)
            hist = df[df.index < opent]
            if len(hist) < 60:
                continue
            rth = bysess[s]
            rth = rth[(rth.index.time >= pd.Timestamp("09:30").time()) &
                      (rth.index.time < pd.Timestamp("16:00").time())]
            if len(rth) < 5:
                continue
            zs, px = build(hist, bysess[sids[i - 1]], bps)
            arr = rth.reset_index()
            o, c = rth["close"].iloc[0], rth["close"].iloc[-1]
            denom = rth["close"].diff().abs().sum()
            regime = "trend" if (denom and abs(c - o) / denom >= 0.4) else "balance"
            n_sessions += 1
            touched = set()
            for bi in range(len(arr)):
                for zi, z in enumerate(zs):
                    if zi in touched:
                        continue
                    r = test_touch(z, arr, bi, px)
                    if r is not None:
                        touched.add(zi)
                        ev.append(dict(score=z["w"], nt=z["nt"], regime=regime, hold=r))
            # null: random levels across the day's context range, same count
            rng_lo, rng_hi = hist["low"].iloc[-bps * 5:].min(), hist["high"].iloc[-bps * 5:].max()
            for _ in range(len(zs)):
                lvl = RNG.uniform(rng_lo, rng_hi)
                zf = dict(lo=lvl - 0.0009 * px, hi=lvl + 0.0009 * px)
                for bi in range(len(arr)):
                    r = test_touch(zf, arr, bi, px)
                    if r is not None:
                        nullev.append(r); break

    e = pd.DataFrame(ev); nn = pd.Series(nullev, dtype=bool)
    print(f"CONFLUENCE BACKTEST (multi-instrument) — {len(e)} zone touch-events over "
          f"{n_sessions} instrument-sessions\n(fade: reverse {TGT_F:.2%}=hold vs {BRK_F:.2%}-through=fail)\n")
    print(f"NULL (random levels, same test): {nn.mean():.0%} hold  (n={len(nn)})  <- luck baseline\n")

    def ci(g):
        p = g.mean(); n = len(g); se = (p * (1 - p) / n) ** 0.5 if n else 0
        return f"{p:.0%} +/-{1.96*se:.0%} (n={n})"

    print("HOLD-RATE by score bucket:")
    for name, m in [("<5", e.score < 5), ("5-8", (e.score >= 5) & (e.score < 8)), (">=8 (A+)", e.score >= 8)]:
        if m.sum(): print(f"  score {name:9s}: {ci(e[m].hold)}")
    print("\nHOLD-RATE by #distinct sources in zone:")
    for name, m in [("1 (lone)", e.nt == 1), ("2", e.nt == 2), ("3", e.nt == 3), (">=4", e.nt >= 4)]:
        if m.sum(): print(f"  {name:9s}: {ci(e[m].hold)}")
    print("\nHOLD-RATE A+ (>=8) & multi-source (>=2), by regime:")
    a = e[(e.score >= 8) & (e.nt >= 2)]
    for r in ("balance", "trend"):
        g = a[a.regime == r]
        if len(g): print(f"  {r:8s}: {ci(g.hold)}")
    print(f"\nBEST FILTER A+ & >=2 sources: {ci(a.hold)}  vs null {nn.mean():.0%}  "
          f"-> edge = +{a.hold.mean()-nn.mean():.0%}pts")


if __name__ == "__main__":
    main()
