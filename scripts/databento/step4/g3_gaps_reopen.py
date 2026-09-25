#!/usr/bin/env python3
"""Step 4, G3 -- B29 gap structure trade (gapstructure.py at 9f23f33), B31 the
two reopened families (reopen_study.py at d12d677, pre-registered 40f4727), and
B30 recorded as not rerun.

PORT NOTE (committed before this file first ran)
------------------------------------------------
B29: the frozen script reads QQQ 5-minute RTH bars. NQ 5-minute bars in the same
    schema are built from the NQ 1-minute file (bins from 09:30, open first, high
    max, low min, close last, volume sum; only bars that exist). Constants are
    percentages of price or NQ points at 29,400 (fraction of price) and are kept.
    One field (gross move, price, risk) is added to the per-trade dict by source
    patch. Primary: "2 HLs + BOS as drawn", target the gap level, and the frozen
    control (blind entry at the open, same sessions, fixed median-risk stop).
    Pass: mean R > 0 after NQ costs, trade t > 3, and it beats the control.
    Old verdict: closed (structure beats the blind control but the trade loses).
B31: reopen_study.SRC -> NQ file. Test 1 (IB by rejection with one re-entry) and
    Test 2 (VWAP hold, first two signals) x exits 1R/2R/3R/close = 8 cells.
    Gross points = R x risk + frozen cost (px x fraction). Decision rule (section
    7), full sample, after NQ costs, all five: positive; PF > 1.15; positive in
    >= 4 calendar years (literal); positive after removing the best 1%; positive
    at +50% cost. p for BH: one-sided daily-P&L t, Holm across 8.
    Old verdict: one candidate frozen, its holdout exactly break-even, closed.
B30 gapfill.py: not rerun. Its trade was the same gap-structure entry on five
    tape sessions, superseded inside the repository by B29 (2,680 sessions); its
    other output is a descriptive gap-fill base rate with no verdict.
"""
from __future__ import annotations

import sys
import types
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bar_lib as BL                                               # noqa: E402
C = BL.C


def build_5m(src, dst):
    if dst.exists():
        return dst
    d = pd.read_parquet(src)
    d["day"] = d.timestamp.dt.normalize()
    d["bin"] = d.day + ((d.timestamp - d.day - pd.Timedelta(hours=9, minutes=30))
                        // pd.Timedelta(minutes=5)) * pd.Timedelta(minutes=5) + pd.Timedelta(hours=9, minutes=30)
    g = d.groupby("bin", sort=True)
    o = pd.DataFrame({"timestamp": g.timestamp.first().index, "open": g.open.first().to_numpy(),
                      "high": g.high.max().to_numpy(), "low": g.low.min().to_numpy(),
                      "close": g.close.last().to_numpy(), "volume": g.volume.sum().to_numpy()})
    o.to_parquet(dst, index=False)
    return dst


def b29():
    p = C.ROOT / "scripts/orderflow/gapstructure.py"
    src = p.read_text()
    old = "rows.append(dict(day=d1, gap=gap, R=pnl / risk - COST_NQ / (risk / px * NQ_PRICE),"
    assert src.count(old) == 1
    src = src.replace(old, old.replace("rows.append(dict(day=d1, gap=gap,",
                                       "rows.append(dict(day=d1, gap=gap, gross=pnl, px=px, risk=risk,"))
    GS = types.ModuleType("gapstructure_pts")
    GS.__file__ = str(p)
    exec(compile(src, str(p), "exec"), GS.__dict__)
    res, flags, notes = {}, {}, []
    for window, src1 in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        GS.BARS = build_5m(src1, BL.S4 / f"NQ_5m{'' if window == 'full' else '_2021'}.parquet")
        days = GS.sessions()
        keys = sorted(days)
        base = pd.DataFrame(GS.collect(days, keys, 2, False, 1.0))
        med = float(np.median(base.risk_pct))
        ctrl = pd.DataFrame(GS.collect(days, keys, 2, False, 1.0, control=True,
                                       only_days=set(base.day), fixed_risk=med))
        for lab, X in (("2 HLs + BOS (as drawn)", base), ("control: open, fixed stop", ctrl)):
            day = pd.to_datetime(X.day.astype(str))
            frozen = 2.0 * X.px.to_numpy() / GS.NQ_PRICE
            res.setdefault(lab, {})[window] = BL.evaluate_adj(day, X.gross, window, frozen)
            if window == "full":
                fac = BL.factor().reindex(day).to_numpy()
                R = (X.gross.to_numpy() / fac - np.maximum(frozen / fac, C.RT_STD_PTS["NQ"])) \
                    / (X.risk.to_numpy() / fac)
                tt = R.mean() / (R.std(ddof=1) / np.sqrt(len(R)))
                notes.append(f"{lab}: n {len(R)} R {R.mean():+.3f} t {tt:+.2f}")
                res[lab]["_R"] = R.mean()
                res[lab]["_t"] = tt
    ok = bool(res["2 HLs + BOS (as drawn)"]["_R"] > 0 and res["2 HLs + BOS (as drawn)"]["_t"] > 3
              and res["2 HLs + BOS (as drawn)"]["_R"] > res["control: open, fixed stop"]["_R"])
    for v in res.values():
        v.pop("_R"), v.pop("_t")
    BL.report_bar("B29", "gap structure trade (as drawn, with control)", res,
                  ["2 HLs + BOS (as drawn)"], {"2 HLs + BOS (as drawn)": ok,
                                               "control: open, fixed stop": False},
                  old="closed: structure beats blind control but the trade loses", note=" | ".join(notes))


def b31():
    import reopen_study as RS
    res, flags, notes = {}, {}, []
    for window, src in (("full", BL.NQ_FULL), ("2021", BL.NQ_2021)):
        RS.SRC = src
        S = RS.load()
        pxm = {s["day"]: s["px"] for s in S}
        for (name, fn), (ek, tg) in product((("IB re-entry", RS.test1), ("VWAP hold", RS.test2)), RS.EXITS):
            k = f"{name} {ek}"
            T, _ = fn(S, tg)
            T = pd.DataFrame(T) if not isinstance(T, pd.DataFrame) else T
            px = T.day.map(pxm)
            cost = px * RS.COST_F
            gross = T.R * T.risk + cost
            day = pd.DatetimeIndex(pd.to_datetime(T.day.astype(str)))
            res.setdefault(k, {})[window] = BL.evaluate_adj(day, gross, window, cost)
            if window == "full":
                fac = BL.factor().reindex(day).to_numpy()
                base = np.maximum(cost.to_numpy() / fac, C.RT_STD_PTS["NQ"])
                R = (gross.to_numpy() / fac - base) / (T.risk.to_numpy() / fac)
                R50 = (gross.to_numpy() / fac - 1.5 * base) / (T.risk.to_numpy() / fac)
                w, l = R[R > 0], R[R <= 0]
                pf = w.sum() / -l.sum() if len(l) and l.sum() < 0 else np.inf
                yp = int((pd.Series(R).groupby(day.year.to_numpy()).mean() > 0).sum())
                ex1 = np.sort(R)[:len(R) - int(np.ceil(0.01 * len(R)))].sum()
                flags[k] = bool(R.mean() > 0 and pf > 1.15 and yp >= 4 and ex1 > 0 and R50.mean() > 0)
                notes.append(f"{k}: n {len(R)} R {R.mean():+.3f} PF {pf:.2f} +yrs {yp} ex1 {ex1:+.1f} "
                             f"+50%c {R50.mean():+.3f}")
    BL.report_bar("B31", "reopened IB re-entry and VWAP hold (8 cells)", res, list(res), flags,
                  old="one candidate frozen; holdout break-even; closed", note=" | ".join(notes))


def main():
    b29()
    b31()
    C.record(dict(id="B30", study="gap fill base rate / gap trade", primary="none", pass_bar=False,
                  old_verdict="base rate only; structure trade on 5 tape sessions",
                  new_verdict_pre_bh="not rerun: trade superseded by B29 (2,680 sessions); base rate is descriptive"))


if __name__ == "__main__":
    main()
