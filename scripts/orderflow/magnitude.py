#!/usr/bin/env python3
"""ARE WE HUNTING THE HARD THING AND IGNORING THE EASY ONE?

Every test in this project has asked WHICH WAY price goes. Six gates have died
asking it. This asks a different question of the same data: HOW FAR does price
go, regardless of direction.

There is a strong prior that the second is far more predictable. Volatility
clusters -- busy minutes follow busy minutes -- and it is among the most
durable facts in finance, while intraday direction is close to the least. If
that holds here, it reframes the whole search, because the trade has not been
failing for lack of a direction filter:

    the structure trade loses about 2 points to cost on a 30-point stop
    it needs the move to be large enough to pay for itself
    "is the move large" is a magnitude question, not a direction one

So this measures both, on identical features and identical bars:

    SIGNED    IC against the next 15 minutes' move, up or down
    ABSOLUTE  IC against the SIZE of that move, sign discarded

and then asks the question that matters for the trade: if the expected range
is predictable, does taking structure breaks ONLY when it is high turn the
coin into something that clears cost?

Same discipline as everything else here: IC computed per session, t across
sessions, and the trade result reported in points after cost rather than as a
correlation. A correlation has never yet survived that conversion in this
project.

Usage: python3 scripts/orderflow/magnitude.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bigorder import collect                                              # noqa
from ic_harness import features, spearman                                 # noqa
from structure_cvd import bars                                            # noqa
from tape import load_all, rth                                            # noqa

HORIZON = 15
COST_PTS = 2.0


def panel():
    full = load_all()
    days = {d: rth(x) for d, x in sorted(full.items())}
    days = {d: s for d, s in days.items() if len(s) > 5000}
    out = []
    for d, s in days.items():
        f = features(s)
        if f is None:
            continue
        px = s.set_index("time").resample("1min").price.last().reindex(f.index)
        f = f.assign(day=d, px=px)
        out.append(f)
    F = pd.concat(out)
    F["fwd_pts"] = F[f"fwd{HORIZON}"] * F.px
    F["abs_pts"] = F.fwd_pts.abs()
    return F.replace([np.inf, -np.inf], np.nan), days


def ic_table(F, cols):
    rows = []
    for c in cols:
        sg, ab = [], []
        for d, g in F.groupby("day"):
            x = g[c].to_numpy(float)
            for target, store in (("fwd_pts", sg), ("abs_pts", ab)):
                y = g[target].to_numpy(float)
                m = np.isfinite(x) & np.isfinite(y)
                if m.sum() < 50:
                    continue
                v = spearman(x[m], y[m])
                if np.isfinite(v):
                    store.append(v)
        if len(sg) < 8 or len(ab) < 8:
            continue
        sg, ab = np.array(sg), np.array(ab)
        rows.append(dict(
            feature=c,
            sic=sg.mean(), st=sg.mean() / (sg.std(ddof=1) / np.sqrt(len(sg))),
            aic=ab.mean(), at=ab.mean() / (ab.std(ddof=1) / np.sqrt(len(ab)))))
    return pd.DataFrame(rows)


def main():
    F, days = panel()
    cols = [c for c in F.columns
            if c not in ("day", "px", "fwd_pts", "abs_pts")
            and not c.startswith("fwd")]
    print("=" * 96)
    print(f"DIRECTION vs MAGNITUDE — {F.day.nunique()} sessions, {len(F):,} bars")
    print("=" * 96)
    print("  Same features, same bars, same horizon. The only difference is")
    print("  whether the sign of the next move is kept or thrown away.\n")

    T = ic_table(F, cols).sort_values("at", key=abs, ascending=False)
    print(f"  {'feature':<16}{'signed IC':>12}{'t':>8}{'|move| IC':>12}{'t':>8}")
    for _, r in T.head(10).iterrows():
        # r.at collides with the DataFrame indexer, so take columns by key
        print("  %-16s%+12.4f%+8.2f%+12.4f%+8.2f" % (
            r["feature"], r["sic"], r["st"], r["aic"], r["at"]))
    print()
    print("  strongest |t| on DIRECTION: %.2f" % T["st"].abs().max())
    print("  strongest |t| on MAGNITUDE: %.2f" % T["at"].abs().max())
    print()
    print("  If magnitude is far more predictable than direction, the search")
    print("  has been aimed at the harder half of the problem.")

    # ---- does a range filter rescue the structure trade? ------------------
    print("\n" + "=" * 96)
    print("DOES TAKING BREAKS ONLY WHEN THE EXPECTED MOVE IS LARGE HELP?")
    print("=" * 96)
    print("  The structure trade loses to cost on a 30-point stop. It does not")
    print("  need to know direction better -- it needs the move to be big")
    print("  enough to pay. This is that filter, and nothing else changes.\n")

    ks = sorted(days)
    allp = [(a, b) for a, b in zip(ks, ks[1:])
            if len(pd.bdate_range(a, b)) == 2]
    # The range forecast is the volatility-clustering prior in one line: the
    # mean bar range over the last 20 bars, shifted so the current bar is not
    # in its own forecast. Nothing is fitted.
    from structure_trade import levels_of, next_level, signals
    rows = []
    for d0, d1 in allp:
        if d1 not in days or d0 not in days:
            continue
        s = days[d1]
        b = bars(s, 3)
        if len(b) < 25:
            continue
        lv = levels_of(bars(days[d0], 3), 2.0)
        rng = (b.h - b.l).rolling(20, min_periods=8).mean().shift(1).to_numpy()
        px_all, tm_all = s.price.to_numpy(), s.time.to_numpy()
        for sig in signals(b):
            i = sig["i"]
            entry, stop, up = sig["price"], sig["stop"], sig["up"]
            risk = abs(entry - stop)
            if risk <= 0 or not np.isfinite(rng[i]) or rng[i] <= 0:
                continue
            tgt = next_level(lv, entry, up, 2.0)
            if tgt is None:
                continue
            start = int(np.searchsorted(tm_all,
                                        np.datetime64(b.timestamp.iloc[i]), "right"))
            pnl = None
            for j in range(start, len(px_all)):
                if up:
                    if px_all[j] <= stop:
                        pnl = -risk; break
                    if px_all[j] >= tgt:
                        pnl = abs(tgt - entry); break
                else:
                    if px_all[j] >= stop:
                        pnl = -risk; break
                    if px_all[j] <= tgt:
                        pnl = abs(tgt - entry); break
            if pnl is None:
                pnl = (px_all[-1] - entry) if up else (entry - px_all[-1])
            rows.append(dict(day=d1, pts=pnl - COST_PTS,
                             R=pnl / risk - COST_PTS / risk,
                             rng=rng[i], risk=risk,
                             rr=abs(tgt - entry) / risk))
    T2 = pd.DataFrame(rows)
    print(f"  {len(T2)} breaks, {T2.day.nunique()} sessions\n")
    print(f"    {'recent 20-bar range':<28}{'n':>6}{'pts':>9}{'R':>9}{'win':>8}")
    q = pd.qcut(T2.rng, 4, labels=False, duplicates="drop")
    for i in sorted(pd.Series(q).dropna().unique()):
        m = q == i
        g = T2[m]
        print(f"    quartile {int(i)} (<= {g.rng.max():5.1f} pts){'':<6}"
              f"{len(g):>6}{g.pts.mean():>+9.2f}{g.R.mean():>+9.3f}"
              f"{100*(g.pts > 0).mean():>7.1f}%")
    per = T2.groupby("day").pts.mean()
    print(f"\n    all breaks: {T2.pts.mean():+.2f} pts, per-session t "
          f"{per.mean() / (per.std(ddof=1) / np.sqrt(len(per))):+.2f}")


if __name__ == "__main__":
    main()
