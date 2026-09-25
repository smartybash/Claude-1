#!/usr/bin/env python3
"""FAMILY C: SWEEP DEPTH, FROM PER-FILL DETAIL.

The one place where the earlier null tells us nothing at all.

Sweep depth was computed as |last fill price - first fill price| on a 5-point
grid. 94-97% of multi-fill aggressive orders reported a span of zero, because
every fill of a four-level sweep landed in the same bucket. The gate was
mechanically off almost always, so its failure says nothing about sweeps. It
was never measured.

It is measurable now. The recorder writes one row per individual fill, each
with its own price, so an order's sweep depth is the real distance its fills
covered, in real ticks.

DEFINITIONS, fixed in the pre-registration before this ran:

    C1 sweep_net   signed contracts in orders whose fills spanned >= 2 ticks,
                   divided by the bar's volume
    C2 sweep_deep  the same at >= 8 ticks

Signed by the aggressor: a buy sweep is positive. Two features, one horizon,
and the thresholds are the conventional ones rather than anything chosen here.

Scope is the 16 explored-pile sessions at 0.25. The sealed dates are not read.

Usage: python3 scripts/orderflow/batch_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bigorder import cum_path                                             # noqa
from codec import is_encoded, load_any                                    # noqa
from ic_harness import spearman                                           # noqa
from roster import split                                                  # noqa
from tape import load_all, price_step, rth, session_day                    # noqa

BAR_MIN = 5
HORIZON = 15
COST = 2.0
TICK = 0.25
SHALLOW = 2      # ticks
DEEP = 8


def sessions() -> list[str]:
    """The explored-pile dates that hold a 0.25 tape AND per-fill cumulative.

    Sealed dates are excluded here, not filtered later, so there is no path by
    which one is read.
    """
    days = load_all()
    disc, hold, bad = split(days)
    out = []
    for d in sorted(disc):
        if price_step(disc[d]) >= 1.0:
            continue
        cp = cum_path(d)
        if cp is None or not is_encoded(cp):
            continue
        c = load_any(cp, ("first_price", "last_price"))
        if "kind" not in c.columns:
            continue
        out.append(d)
    return out


def features(day: str):
    """One row per 5-minute bar: the two sweep features and a forward return."""
    days = load_all()
    s = rth(days[day])
    if len(s) < 5000:
        return None
    t0 = session_day(s) + pd.Timedelta(hours=13, minutes=30)
    s = s.assign(bar=((s.time - t0) // pd.Timedelta(minutes=BAR_MIN)))

    px = s.groupby("bar").price.last()
    vol = s.groupby("bar").volume.sum()

    c = load_any(cum_path(day), ("first_price", "last_price"))
    c = c[(c.time >= t0) & (c.time < t0 + pd.Timedelta(hours=6, minutes=30))]
    orders = c[c.kind == "O"].copy()
    fills = c[c.kind == "F"].copy()
    if orders.empty or fills.empty:
        return None

    # Each fill belongs to the nearest preceding order row. parent_seq was
    # dropped from the format because row order carries it exactly, which was
    # verified against the 18 June file before the column was removed.
    c = c.reset_index(drop=True)
    is_order = (c.kind == "O").to_numpy()
    parent = np.where(is_order, np.arange(len(c)), np.nan)
    parent = pd.Series(parent).ffill().to_numpy()
    c["parent"] = parent

    f = c[c.kind == "F"]
    # sweep depth is what the FILLS actually covered, which is the whole point
    g = f.groupby("parent").first_price
    span = ((g.max() - g.min()) / TICK).rename("span")
    o = c[c.kind == "O"].copy()
    o["idx"] = o.index
    o = o.merge(span, left_on="idx", right_index=True, how="left")
    o["span"] = o["span"].fillna(0.0)
    o["sign"] = np.where(o.aggressor.astype(str).str[0] == "B", 1.0, -1.0)
    o["signed"] = o["sign"] * o.volume
    o["bar"] = (o.time - t0) // pd.Timedelta(minutes=BAR_MIN)

    out = pd.DataFrame(index=px.index)
    out["px"] = px
    out["vol"] = vol
    for name, lim in (("sweep_net", SHALLOW), ("sweep_deep", DEEP)):
        sel = o[o.span >= lim]
        out[name] = sel.groupby("bar").signed.sum()
    out = out.fillna({"sweep_net": 0.0, "sweep_deep": 0.0})
    for name in ("sweep_net", "sweep_deep"):
        out[name] = out[name] / out.vol.replace(0, np.nan)

    k = max(1, HORIZON // BAR_MIN)
    out["fwd"] = out.px.shift(-k) / out.px - 1.0
    out["fwd_pts"] = out.fwd * out.px
    return out.replace([np.inf, -np.inf], np.nan), o


def main():
    days = sessions()
    print("=" * 96)
    print("FAMILY C — SWEEP DEPTH FROM PER-FILL DETAIL")
    print("=" * 96)
    print(f"  sessions ({len(days)}): {' '.join(d[4:] for d in days)}")
    print(f"  resolution 0.25 verified per file   bars {BAR_MIN}min   "
          f"horizon {HORIZON}min")
    print(f"  thresholds: sweep >= {SHALLOW} ticks, deep >= {DEEP} ticks "
          "(pre-registered)\n")

    per, spans = {}, []
    for d in days:
        r = features(d)
        if r is None:
            continue
        F, o = r
        per[d] = F
        spans.append(o.span)
    S = pd.concat(spans)

    # First: is the field alive at all? This is what the 5-point grid destroyed.
    print("  --- is sweep depth measurable now? ---")
    print(f"  aggressive orders: {len(S):,}")
    print(f"  span 0 ticks : {100*(S == 0).mean():>5.1f}%   "
          f"(was 94-97% on the 5-point grid)")
    for lim in (1, 2, 4, 8, 16):
        print(f"  span >= {lim:>2} ticks: {100*(S >= lim).mean():>5.1f}%")
    print()

    rng = np.random.default_rng(0)
    print(f"  {'feature':<14}{'IC':>10}{'t':>8}{'null t':>9}{'sessions':>10}")
    rows = []
    for c in ("sweep_net", "sweep_deep"):
        ics, nulls = [], []
        for d, F in per.items():
            x = F[c].to_numpy(float)
            y = F["fwd_pts"].to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 30 or np.nanstd(x[m]) == 0:
                continue
            ics.append(spearman(x[m], y[m]))
            k = int(rng.integers(5, max(6, m.sum() - 5)))
            nulls.append(spearman(x[m], np.roll(y[m], k)))
        ics = np.array([v for v in ics if np.isfinite(v)])
        nulls = np.array([v for v in nulls if np.isfinite(v)])
        t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
        nt = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls)))
        rows.append((c, ics.mean(), t, nt, len(ics)))
        print(f"  {c:<14}{ics.mean():>+10.4f}{t:>+8.2f}{nt:>+9.2f}{len(ics):>10}")

    print(f"\n  bar: |t| >= 3.0 (Bonferroni over the batch's 12 tests)")
    live = [r for r in rows if abs(r[2]) >= 3.0]
    print(f"  clearing it: {len(live)} of 2")

    # Third gate: points after cost. Run regardless, so the size is on record.
    print("\n  --- priced, top/bottom quintile, 15-minute hold, after cost ---")
    A = pd.concat([F.assign(day=d) for d, F in per.items()])
    for c in ("sweep_net", "sweep_deep"):
        G = A.dropna(subset=[c, "fwd_pts"])
        if G[c].nunique() < 5:
            print(f"  {c:<14} too few distinct values to quintile")
            continue
        q = pd.qcut(G[c].rank(method="first"), 5, labels=False)
        long_, short_ = G[q == 4], G[q == 0]
        pnl = np.concatenate([long_.fwd_pts.to_numpy(),
                              -short_.fwd_pts.to_numpy()]) - COST
        dd = np.concatenate([long_.day.to_numpy(), short_.day.to_numpy()])
        ses = pd.Series(pnl).groupby(dd).mean()
        tt = ses.mean() / (ses.std(ddof=1) / np.sqrt(len(ses)))
        print(f"  {c:<14}{pnl.mean():>+8.2f} pts/trade  t {tt:>+5.2f}  "
              f"n={len(pnl):,}  sessions positive {int((ses > 0).sum())}/{len(ses)}")


if __name__ == "__main__":
    main()
