#!/usr/bin/env python3
"""Step 4, G3 -- B27 level rules on the long bar history (levels_long.py at
b68f379) and B28 structure trade by timeframe (structure_trade.py at 5c1ba8d),
on NQ 1-minute bars.

PORT NOTE (committed before this file first ran)
------------------------------------------------
Both scripts express stops, bands, buckets and cost as NQ points AT 29,400 and
convert them by the day's own price (k = px / 29,400), i.e. as fixed fractions of
price. On NQ bars that conversion is kept exactly as frozen (30 pt stop = 10.2
bps). BARS -> NQ 1-minute file (full; 2021 line). Each frozen per-trade dict gets
ONE added field by source patch -- the gross move in (adjusted) price units, and
the price it is measured against -- so trades can be costed at max(frozen 2 pt x
px/29,400, NQ 0.725 pt) in real points. No other line changes.
B27 primary cells (15): fade every level; fade POC/VAH/VAL/PDH/PDL/PDC; fade the
    lightest / middle / heaviest third; go with every break; go with the
    PDH/PDL/POC/PDC break. Frozen bar: |t| >= 3 across trades; here pass = net >
    0 after NQ costs and trade t >= 3. Old verdict: the fade loses; the PDH/PDL
    break tilt (52.8%) is smaller than cost.
B28 primary cells (10): timeframes 1/3/5/15/30 min, every signal and R:R >= 2
    only. Pass = mean R > 0 after NQ costs and trade t > 3. Old verdict: negative
    at every timeframe; flat at best after the R:R filter.
p for BH: one-sided daily-P&L t, Holm within each study.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def load_patched(fname, old, new, name):
    p = C.ROOT / "scripts/orderflow" / fname
    src = p.read_text()
    assert src.count(old) == 1, (fname, old)
    src = src.replace(old, new)
    m = types.ModuleType(name)
    m.__file__ = str(p)
    exec(compile(src, str(p), "exec"), m.__dict__)
    return m


def cell(day, gross_adj, px_adj, window, nq_price):
    day = pd.to_datetime(pd.Index(day).astype(str))
    frozen = 2.0 * np.asarray(px_adj, float) / nq_price
    return BL.evaluate_adj(day, gross_adj, window, frozen), day, frozen


def trade_t(day, gross_adj, frozen_adj, risk_adj=None):
    fac = BL.factor().reindex(day).to_numpy()
    net = np.asarray(gross_adj, float) / fac - np.maximum(np.asarray(frozen_adj) / fac, C.RT_STD_PTS["NQ"])
    x = net if risk_adj is None else net / (np.asarray(risk_adj, float) / fac)
    return x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def b27():
    LL = load_patched("levels_long.py",
                      'rows.append(dict(day=d1, name=h["name"], weight=wt[h["name"]],',
                      'rows.append(dict(day=d1, name=h["name"], weight=wt[h["name"]], gross=pnl, ggross=gp, px=px,',
                      "levels_long_pts")
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        LL.BARS = src
        days = LL.sessions()
        keys = sorted(days)
        rows = []
        for d0, d1 in zip(keys, keys[1:]):
            prev, b = days[d0], days[d1]
            px = float(b.o.iloc[0])
            k = px / LL.NQ_PRICE
            lv, wt = LL.levels_from(prev, LL.BUCKET_NQ * k)
            for h in LL.first_touches(b, lv, LL.BAND_NQ * k):
                entry, buy = h["price"], h["from_above"]
                sd, td = LL.STOP_NQ * k, LL.TARGET_NQ * k
                pnl, _ = LL.walk(b, h["i"], entry, entry - sd if buy else entry + sd,
                                 entry + td if buy else entry - td, buy)
                gp, _ = LL.walk(b, h["i"], entry, entry + sd if buy else entry - sd,
                                entry - td if buy else entry + td, not buy)
                rows.append(dict(day=d1, name=h["name"], weight=wt[h["name"]],
                                 gross=pnl, ggross=gp, px=px))
        R = pd.DataFrame(rows)
        R["pct"] = R.groupby("day").weight.rank(pct=True)
        cells = {"fade every level": (R, "gross")}
        for nm in ("POC", "VAH", "VAL", "PDH", "PDL", "PDC"):
            cells[f"fade {nm}"] = (R[R.name == nm], "gross")
        for lo, hi, lab in ((0, .34, "lightest"), (.34, .67, "middle"), (.67, 1.01, "heaviest")):
            cells[f"fade {lab} third"] = (R[(R.pct >= lo) & (R.pct < hi)], "gross")
        cells["break every level"] = (R, "ggross")
        for nm in ("PDH", "PDL", "POC", "PDC"):
            cells[f"break {nm}"] = (R[R.name == nm], "ggross")
        for k2, (X, col) in cells.items():
            m, day, frozen = cell(X.day, X[col], X.px, window, LL.NQ_PRICE)
            res.setdefault(k2, {})[window] = m
            if window == "full":
                mean, tt = trade_t(day, X[col].to_numpy(), frozen)
                flags[k2] = bool(mean > 0 and tt >= 3)
                notes.append(f"{k2}: n {len(X)} net {mean:+.2f} pt t {tt:+.2f}")
    BL.report_bar("B27", "level rules, fade and break (15 cells)", res, list(res), flags,
                  old="fade loses; PDH/PDL break tilt < cost", note=" | ".join(notes))


def b28():
    ST = load_patched("structure_trade.py",
                      'rows.append(dict(day=d1, tf=minutes, kind=s["kind"],',
                      'rows.append(dict(day=d1, tf=minutes, kind=s["kind"], gross=pnl, entry=entry, risk=risk,',
                      "structure_trade_pts")
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        ST.BARS = src
        days = ST.sessions()
        keys = sorted(days)
        for tf in ST.TIMEFRAMES:
            rows = pd.DataFrame(ST.run_tf(days, keys, tf))
            for lab, X in ((f"{tf}-min every signal", rows), (f"{tf}-min R:R >= 2", rows[rows.rr >= 2])):
                m, day, frozen = cell(X.day, X.gross, X.entry, window, ST.NQ_PRICE)
                res.setdefault(lab, {})[window] = m
                if window == "full":
                    mean, tt = trade_t(day, X.gross.to_numpy(), frozen, X.risk.to_numpy())
                    flags[lab] = bool(mean > 0 and tt > 3)
                    notes.append(f"{lab}: n {len(X)} R {mean:+.3f} t {tt:+.2f}")
    BL.report_bar("B28", "structure trade by timeframe (10 cells)", res, list(res), flags,
                  old="negative at every timeframe", note=" | ".join(notes))


def main():
    b27()
    b28()


if __name__ == "__main__":
    main()
