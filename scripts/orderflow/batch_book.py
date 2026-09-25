#!/usr/bin/env python3
"""FAMILIES D and F: the order book, measured in points rather than levels.

D  BOOK IMBALANCE AT A REAL TICK DISTANCE
   Killed twice before, neither safely. The filter_survey version expressed
   its window in LEVELS on a five-point grid, so "ten levels" spanned fifty
   points and the label described nothing. The earlier imbalance.py version
   was at correct resolution but rested on four sessions. Here the window is a
   PRICE DISTANCE, which means the same thing on any grid.

F  PULL VERSUS FILL
   When size leaves the touch it was either traded or cancelled, and those mean
   opposite things. Killed at t = +1.50 and t = -0.91 on four sessions, which
   distinguishes a small effect from none about as well as a coin does.

Both are computed from the book reconstructed at each bar's close, and from
what happened to the touch price across the bar.

Scope: the explored-pile sessions at 0.25 holding a depth file. Sealed dates
are excluded when the list is built.

Usage: python3 scripts/orderflow/batch_book.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from book import replay                                                   # noqa
from codec import is_encoded, load_any                                    # noqa
from ic_harness import spearman                                           # noqa
from roster import split                                                  # noqa
from tape import ROOT, load_all, price_step, rth, session_day              # noqa

BAR_MIN = 5
HORIZON = 15
COST = 2.0
NEAR = 1.00      # points, family D1
WIDE = 5.00      # points, family D2


def depth_path(day: str):
    for ext in (".csv.br", ".csv.gz"):
        p = ROOT / "data" / "depth" / f"L2_NQ_{day}{ext}"
        if p.exists() and is_encoded(p):
            return p
    return None


def session_features(day: str, tape: pd.DataFrame):
    dp = depth_path(day)
    if dp is None:
        return None
    D = load_any(dp)
    s = rth(tape)
    if len(s) < 5000:
        return None
    t0 = session_day(s) + pd.Timedelta(hours=13, minutes=30)
    end = t0 + pd.Timedelta(hours=6, minutes=30)
    D = D[(D.time >= t0) & (D.time < end)]
    if D.empty:
        return None

    # bar close timestamps
    edges = pd.date_range(t0, end, freq=f"{BAR_MIN}min")
    want = list(edges[1:])
    rows = []
    wi = 0
    prev_bid = {}
    prev_best = None
    pulled = filled = 0.0

    # trades per price, to split a size decrease into traded and cancelled
    tr = s.assign(p=s.price.round(2))
    tr_idx = tr.time.to_numpy()

    for t, bids, asks in replay(D):
        if not bids or not asks:
            continue
        bb, ba = max(bids), min(asks)

        # what left the best bid since the last state, and why
        if prev_best is not None and prev_best in prev_bid:
            if prev_best in bids:
                gone = prev_bid[prev_best] - bids[prev_best]
            else:
                gone = prev_bid[prev_best]
            if gone > 0:
                lo = np.searchsorted(tr_idx, np.datetime64(prev_t), "left")
                hi = np.searchsorted(tr_idx, np.datetime64(t), "right")
                traded = float(tr.volume.to_numpy()[lo:hi][
                    tr.p.to_numpy()[lo:hi] == prev_best].sum())
                filled += min(gone, traded)
                pulled += max(0.0, gone - traded)
        prev_bid = dict(bids)
        prev_best = bb
        prev_t = t

        while wi < len(want) and t >= want[wi]:
            near_b = sum(v for p, v in bids.items() if p >= bb - NEAR)
            near_a = sum(v for p, v in asks.items() if p <= ba + NEAR)
            wide_b = sum(v for p, v in bids.items() if p >= bb - WIDE)
            wide_a = sum(v for p, v in asks.items() if p <= ba + WIDE)
            rows.append(dict(
                t=want[wi],
                D1=(near_b - near_a) / max(near_b + near_a, 1e-9),
                D2=(wide_b - wide_a) / max(wide_b + wide_a, 1e-9),
                pulled=pulled, filled=filled))
            pulled = filled = 0.0
            wi += 1
        if wi >= len(want):
            break

    if len(rows) < 40:
        return None
    F = pd.DataFrame(rows).set_index("t")

    bar = ((s.time - t0) // pd.Timedelta(minutes=BAR_MIN))
    px = s.assign(bar=bar).groupby("bar").price.last()
    vol = s.assign(bar=bar).groupby("bar").volume.sum()
    px.index = [t0 + pd.Timedelta(minutes=BAR_MIN * (i + 1)) for i in px.index]
    vol.index = px.index
    F = F.join(px.rename("px"), how="inner").join(vol.rename("vol"), how="inner")
    F["F1"] = F.pulled / F.vol.replace(0, np.nan)
    F["F2"] = F.filled / F.vol.replace(0, np.nan)
    k = max(1, HORIZON // BAR_MIN)
    F["fwd_pts"] = (F.px.shift(-k) / F.px - 1.0) * F.px
    return F.replace([np.inf, -np.inf], np.nan)


FEATS = {"D1": f"imbalance <={NEAR:.0f}pt", "D2": f"imbalance <={WIDE:.0f}pt",
         "F1": "size pulled", "F2": "size filled"}


def main():
    days = load_all()
    disc, hold, bad = split(days)
    per = {}
    for d in sorted(disc):
        if price_step(disc[d]) >= 1.0:
            continue
        F = session_features(d, disc[d])
        if F is not None:
            per[d] = F
    ds = sorted(per)
    print("=" * 96)
    print("FAMILIES D and F — BOOK IMBALANCE BY DISTANCE, AND PULL vs FILL")
    print("=" * 96)
    print(f"  sessions ({len(ds)}): {' '.join(x[4:] for x in ds)}")
    print(f"  resolution 0.25   bars {BAR_MIN}min   horizon {HORIZON}min")
    print(f"  windows {NEAR:.2f} and {WIDE:.2f} POINTS, not level counts "
          "(pre-registered)\n")

    A = pd.concat([F.assign(day=d) for d, F in per.items()])
    print(f"  bars: {len(A):,}")
    print(f"  median size pulled per bar : {A.pulled.median():,.0f} contracts")
    print(f"  median size filled per bar : {A.filled.median():,.0f}\n")

    rng = np.random.default_rng(0)
    print(f"  {'feature':<8}{'':<20}{'IC':>10}{'t':>8}{'null t':>9}{'sess':>7}")
    rows = []
    for c, label in FEATS.items():
        ics, nulls = [], []
        for d, F in per.items():
            x = F[c].to_numpy(float); y = F.fwd_pts.to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 30 or np.nanstd(x[m]) == 0:
                continue
            ics.append(spearman(x[m], y[m]))
            k = int(rng.integers(5, max(6, m.sum() - 5)))
            nulls.append(spearman(x[m], np.roll(y[m], k)))
        ics = np.array([v for v in ics if np.isfinite(v)])
        nulls = np.array([v for v in nulls if np.isfinite(v)])
        if len(ics) < 5:
            print(f"  {c:<8}{label:<20}  too few sessions")
            continue
        t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
        nt = nulls.mean() / (nulls.std(ddof=1) / np.sqrt(len(nulls)))
        rows.append((c, t))
        print(f"  {c:<8}{label:<20}{ics.mean():>+10.4f}{t:>+8.2f}"
              f"{nt:>+9.2f}{len(ics):>7}")
    print(f"\n  bar: |t| >= 3.0.  clearing it: "
          f"{sum(1 for _, t in rows if abs(t) >= 3.0)} of {len(rows)}")

    print("\n  --- priced, top/bottom quintile, after cost ---")
    for c, label in FEATS.items():
        G = A.dropna(subset=[c, "fwd_pts"])
        if G[c].nunique() < 5:
            print(f"  {c:<8}{label:<20} too few distinct values")
            continue
        q = pd.qcut(G[c].rank(method="first"), 5, labels=False)
        lo, hi = G[q == 0], G[q == 4]
        pnl = np.concatenate([hi.fwd_pts.to_numpy(),
                              -lo.fwd_pts.to_numpy()]) - COST
        dd = np.concatenate([hi.day.to_numpy(), lo.day.to_numpy()])
        ses = pd.Series(pnl).groupby(dd).mean()
        tt = ses.mean() / (ses.std(ddof=1) / np.sqrt(len(ses)))
        print(f"  {c:<8}{label:<20}{pnl.mean():>+8.2f} pts  t {tt:>+5.2f}  "
              f"sessions positive {int((ses > 0).sum())}/{len(ses)}")


if __name__ == "__main__":
    main()
