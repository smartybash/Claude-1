"""VWAP + FVG, traded the realistic way: STRUCTURE stops (swing low/high, not the
gap edge) and how the setup is actually managed. Reuses the v1 data helpers.

Two archetypes, each with a structure stop (swing low/high of the prior K bars):

  CONTINUATION (with VWAP bias): long a bullish FVG when price is ABOVE VWAP
    (short a bearish FVG below VWAP). Exits tested:
      - fixed 2R
      - ride until a close back through VWAP (trend failed), else EOD
  REVERSION (fade an extension back to VWAP): long a bullish FVG when price is
    BELOW VWAP, target = VWAP; short a bearish FVG above VWAP, target = VWAP.

Entry = limit fill at the gap near-edge (no look-ahead). Stop = structure. All on
123 sessions of real 5-min QQQ. Reported overall and split by gamma regime.
No costs modelled.
"""

from __future__ import annotations

import pandas as pd

from backtest_vwap_fvg import load_intraday, regime_map, session_vwap, stats, MIN_GAP

K = 5   # bars back for the swing-structure stop


def simulate(mode, exit_spec):
    intr = load_intraday()
    days = sorted(intr["day"].unique())
    reg = regime_map(days)
    trades = []
    for day in days:
        b = intr[intr["day"] == day].reset_index()
        if len(b) < K + 3:
            continue
        vwap = session_vwap(b).values
        o, h, l, c = b["open"].values, b["high"].values, b["low"].values, b["close"].values
        n = len(b); net = reg.get(day)
        fvgs = []
        for i in range(n):
            if i >= 2:
                if l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bull", "top": l[i], "bot": h[i - 2], "formed": i, "used": False})
                if h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bear", "top": l[i - 2], "bot": h[i], "formed": i, "used": False})
            for f in fvgs:
                if f["used"] or i <= f["formed"] or i < K:
                    continue
                if f["side"] == "bull" and l[i] <= f["top"]:
                    above = c[i] > vwap[i]
                    want = (mode == "cont" and above) or (mode == "rev" and not above)
                    if not want:
                        continue
                    entry = f["top"]; stop = min(l[i - K:i + 1]) ; risk = entry - stop
                    if risk <= 0 or l[i] <= stop:
                        continue
                    f["used"] = True
                    trades.append(_walk(b, vwap, i, "long", entry, stop, risk, mode, exit_spec, net, day))
                elif f["side"] == "bear" and h[i] >= f["bot"]:
                    below = c[i] < vwap[i]
                    want = (mode == "cont" and below) or (mode == "rev" and not below)
                    if not want:
                        continue
                    entry = f["bot"]; stop = max(h[i - K:i + 1]); risk = stop - entry
                    if risk <= 0 or h[i] >= stop:
                        continue
                    f["used"] = True
                    trades.append(_walk(b, vwap, i, "short", entry, stop, risk, mode, exit_spec, net, day))
            fvgs = [f for f in fvgs if f["used"] or not (
                (f["side"] == "bull" and l[i] <= f["bot"]) or
                (f["side"] == "bear" and h[i] >= f["top"]))]
    return pd.DataFrame([t for t in trades if t])


def _walk(b, vwap, i, dirn, entry, stop, risk, mode, exit_spec, net, day):
    h, l, c = b["high"].values, b["low"].values, b["close"].values
    n = len(b)
    tgt = None
    if exit_spec.startswith("fixed"):
        M = float(exit_spec[5:])
        tgt = entry + M * risk if dirn == "long" else entry - M * risk
    for j in range(i + 1, n):
        if dirn == "long":
            if l[j] <= stop:
                r = -1.0; break
            if tgt is not None and h[j] >= tgt:
                r = (tgt - entry) / risk; break
            if exit_spec == "vwap_cross" and c[j] < vwap[j]:
                r = (c[j] - entry) / risk; break
            if exit_spec == "vwap_target" and h[j] >= vwap[j]:
                r = (vwap[j] - entry) / risk; break
        else:
            if h[j] >= stop:
                r = -1.0; break
            if tgt is not None and l[j] <= tgt:
                r = (entry - tgt) / risk; break
            if exit_spec == "vwap_cross" and c[j] > vwap[j]:
                r = (entry - c[j]) / risk; break
            if exit_spec == "vwap_target" and l[j] <= vwap[j]:
                r = (entry - vwap[j]) / risk; break
    else:
        r = ((c[-1] - entry) if dirn == "long" else (entry - c[-1])) / risk
    return {"day": day, "dir": dirn, "R": r, "net": net}


def block(title, mode, exit_spec):
    df = simulate(mode, exit_spec)
    print(f"===== {title} =====")
    stats(df, "ALL")
    if len(df):
        stats(df[df["net"].notna() & (df["net"] > 0)], "  POSITIVE-gamma days")
        stats(df[df["net"].notna() & (df["net"] < 0)], "  NEGATIVE-gamma days")
    print()


def _tstat(x):
    import numpy as np
    x = np.array(x, float)
    return x.mean() / (x.std(ddof=1) / len(x) ** 0.5) if len(x) > 1 and x.std() else float("nan")


def focus():
    """Stress-test the one promising thread: CONTINUATION + ride, negative-gamma only."""
    import numpy as np
    df = simulate("cont", "vwap_cross")
    df = df[df["net"].notna()].copy()
    df["neg"] = df["net"] < 0
    print("===== STRESS TEST: continuation + ride to VWAP-loss, by gamma =====")
    for lab, sub in [("NEGATIVE-gamma (expansion)", df[df["neg"]]),
                     ("POSITIVE-gamma (compression)", df[~df["neg"]])]:
        r = sub["R"]
        print(f"  {lab:30s} n={len(sub):3d}  win {(r>0).mean():.0%}  mean {r.mean():+.3f}R  "
              f"median {r.median():+.2f}R  t {_tstat(r):+.2f}")
    neg = df[df["neg"]].sort_values("day")
    mid = neg["day"].iloc[len(neg) // 2]
    print("  split-half (NEG-gamma bucket):")
    for lb, part in [("first ", neg[neg["day"] < mid]), ("second", neg[neg["day"] >= mid])]:
        r = part["R"]
        print(f"    {lb}: n={len(part):3d}  mean {r.mean():+.3f}R  win {(r>0).mean():.0%}")
    # concentration check: is it a few monster winners?
    r = neg["R"]
    print(f"  NEG bucket: top-3 trades = {r.nlargest(3).sum():.1f}R of {r.sum():.1f}R total; "
          f"max single {r.max():.1f}R")
    print()


def earnings_reaction_days(days):
    """QQQ sessions that react to a MAG7 report (post->next day, pre->same day)."""
    from backtest_earnings_range import EARNINGS
    dset = set(pd.Timestamp(d).normalize() for d in days)
    dl = sorted(dset)
    out = set()
    for evs in EARNINGS.values():
        for d, t in evs:
            ts = pd.Timestamp(d).normalize()
            if t == "pre":
                if ts in dset:
                    out.add(ts)
            else:
                later = [x for x in dl if x > ts]
                if later:
                    out.add(later[0])
    return out


def combined():
    """Synthesis: does the continuation-ride edge live on EXPANSION days
    (negative gamma OR mega-cap earnings reaction) and die on COMPRESSION days?"""
    import numpy as np
    df = simulate("cont", "vwap_cross")
    df = df[df["net"].notna()].copy()
    er = earnings_reaction_days(sorted(df["day"].unique()))
    df["expansion"] = (df["net"] < 0) | df["day"].isin(er)
    print("===== SYNTHESIS: continuation-ride on EXPANSION vs COMPRESSION days =====")
    print("   expansion = negative-gamma OR mega-cap earnings-reaction day")
    for lab, sub in [("EXPANSION days", df[df["expansion"]]),
                     ("COMPRESSION days (pos-gamma, no earnings)", df[~df["expansion"]])]:
        r = sub["R"]
        t = r.mean() / (r.std(ddof=1) / len(r) ** 0.5) if len(r) > 1 and r.std() else float("nan")
        print(f"  {lab:42s} n={len(sub):3d}  win {(r>0).mean():.0%}  mean {r.mean():+.3f}R  t {t:+.2f}")
    print()


def main():
    block("CONTINUATION, structure stop, fixed 2R", "cont", "fixed2.0")
    block("CONTINUATION, structure stop, ride to VWAP-loss", "cont", "vwap_cross")
    block("REVERSION, structure stop, target VWAP", "rev", "vwap_target")
    focus()
    combined()
    print("read: the NEG-gamma continuation-ride bucket is only real if mean>0 with t>~2, "
          "BOTH split-halves positive, and NOT driven by 2-3 monster trades. The synthesis "
          "block tests whether pooling both expansion signals sharpens the separation.")


if __name__ == "__main__":
    main()
