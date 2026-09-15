"""VIX-divergence 'unhealthy market' test — Flow-Zone-Trader tell, honestly checked.

Alex's repeated read: when the index rises AND the VIX rises on the SAME day
(they're normally inverse), it's dealers hedging into strength = 'unhealthy',
and the up-move is more likely to stall / mean-revert.

TEST (daily, 5y, SPY + QQQ vs VIX):
  On every UP day for the index (ret_t > 0), split by whether VIX also rose:
    - VIX_UP  = index up & VIX up   (the 'unhealthy'/divergence day)
    - VIX_DN  = index up & VIX down (the 'healthy' day)
  Compare the FORWARD return (next 1 day, next 5 days) of each bucket, plus
  P(up). If the tell has merit, VIX_UP days should show materially weaker /
  more-negative forward returns than VIX_DN days (and than all up-days).
  Baseline = all days' mean forward return (the drift to beat).

Also reports the same split on DOWN days (index down & VIX down = complacent
selloff) for symmetry. Honest scope: SPY+QQQ daily, Aug-2021..Aug-2026.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    r = json.loads((ROOT / "data" / name).read_text())
    s = pd.Series(r["close"], index=pd.to_datetime([t[:10] for t in r["time"]]))
    return s[~s.index.duplicated(keep="last")].sort_index()


def analyse(px, vix, label, fwd=(1, 5)):
    df = pd.DataFrame({"px": px, "vix": vix}).dropna()
    df["ret"] = df["px"].pct_change()
    df["vret"] = df["vix"].pct_change()
    for k in fwd:
        df[f"f{k}"] = df["px"].shift(-k) / df["px"] - 1.0
    df = df.dropna(subset=["ret", "vret"])
    rows = []
    up = df[df["ret"] > 0]
    dn = df[df["ret"] < 0]
    buckets = {
        "up & VIX-UP (unhealthy)": up[up["vret"] > 0],
        "up & VIX-dn (healthy)  ": up[up["vret"] <= 0],
        "dn & VIX-dn (complacent)": dn[dn["vret"] <= 0],
        "dn & VIX-up (fear)     ": dn[dn["vret"] > 0],
        "ALL days (baseline)    ": df,
    }
    print(f"\n===== {label}  (n={len(df)} days) =====")
    hdr = f"{'bucket':26s} {'n':>4} | " + " | ".join(f"fwd{k}d mean  P(up)" for k in fwd)
    print(hdr); print("-" * len(hdr))
    for name, g in buckets.items():
        cells = []
        for k in fwd:
            m = g[f"f{k}"].mean(); pup = (g[f"f{k}"] > 0).mean()
            cells.append(f"{m:+.2%}  {pup:>4.0%}")
        print(f"{name:26s} {len(g):>4} | " + " | ".join(f"{c:>15s}" for c in cells))
    # the key contrast
    u = up[up["vret"] > 0]; h = up[up["vret"] <= 0]
    for k in fwd:
        diff = u[f"f{k}"].mean() - h[f"f{k}"].mean()
        # Welch-ish SE
        se = (u[f"f{k}"].var()/len(u) + h[f"f{k}"].var()/len(h)) ** 0.5
        z = diff / se if se else 0
        print(f"  fwd{k}d: unhealthy - healthy = {diff:+.2%}  (z={z:+.1f})")
    return df


def main():
    vix = load("vix_daily_5y.json")
    print("VIX-DIVERGENCE 'UNHEALTHY MARKET' TEST — daily, 5y")
    print("hypothesis: index-up + VIX-up (same day) -> weaker forward returns (fade/veto signal)")
    for pxf, lab in [("spy_daily_5y.json", "SPY vs VIX"), ("qqq_daily_5y.json", "QQQ vs VIX")]:
        try:
            analyse(load(pxf), vix, lab)
        except FileNotFoundError:
            print(f"  (missing {pxf})")
    print("\nread: if 'up & VIX-UP' fwd returns are clearly BELOW 'up & VIX-dn' (negative z),")
    print("the 'unhealthy' tell has predictive merit as a long-veto / fade filter.")


if __name__ == "__main__":
    main()
