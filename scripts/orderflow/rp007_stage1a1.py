#!/usr/bin/env python3
"""RP-007 Stage 1A1 -- broad level validity on QQQ. PRICE ONLY. DESCRIPTIVE.

Pre-registered at a72fe50 (reports/rp007_stage1a1_preregistration.md), written
and committed before this script existed.

NO NQ data. No footprint, delta, cumulative fills, depth or absorption. No P&L,
expectancy, profit factor or drawdown. No trading rule.

Frozen by the pre-registration, none varied here:

    theta       0.1435          zone FULL width / prior-session mean 1-min TR
    shifts      10/3, 20/3      zone widths, both signs
    round       $2.50
    primary     reclaim within 10 minutes
    alpha       0.05/30 = 0.001667   (15 families x 2 sides)
    freq bar    12 first interactions per month
    score       0.35 rotation / 0.20 frequency / 0.20 balance
                / 0.15 year consistency / 0.10 first-vs-repeated

Sample: QQQ 1-minute, 2021-01-04 .. 2026-08-31. DISCOVERY ONLY, forever.
"""
from __future__ import annotations

import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RTH = ROOT / "data/intraday_long/QQQ_1m.parquet"
ETH = ROOT / "data/intraday_long/QQQ_1m_eth.parquet"
OUT = ROOT / "reports"

THETA = 0.1435
SHIFT_W = (10 / 3, 20 / 3)
ROUND_STEP = 2.50
RECLAIM_H = (1, 3, 5, 10, 15)
ROT_H = (5, 10, 15, 30)
PRIMARY_K = 10
WIN = 30
NDRAW = 200
SEED = 20260923
VA_PCT = 0.70

FAMS = ["PDH", "PDL", "PDC", "PDVWAP", "VAH", "VAL", "POC",
        "XH", "XL", "XM", "IBH", "IBL", "IBM", "VWAP", "ROUND"]


# --------------------------------------------------------------------------
def value_area(px, vol):
    """POC, VAL, VAH. 70%, conventional two-price-pair expansion.

    POC ties break toward the session's volume-weighted mean, then to the
    lower price -- declared in the pre-registration, not chosen here.
    """
    h = {}
    for p, v in zip(px, vol):
        k = round(float(p), 2)
        h[k] = h.get(k, 0.0) + float(v)
    if not h:
        return np.nan, np.nan, np.nan
    keys = np.array(sorted(h))
    vals = np.array([h[k] for k in keys])
    tot = vals.sum()
    if tot <= 0:
        return np.nan, np.nan, np.nan
    cand = np.where(vals == vals.max())[0]
    if len(cand) == 1:
        poc_i = int(cand[0])
    else:
        vwm = float((keys * vals).sum() / tot)
        dd = np.abs(keys[cand] - vwm)
        poc_i = int(cand[dd == dd.min()][0])
    lo = hi = poc_i
    acc = vals[poc_i]
    n = len(keys)
    while acc < VA_PCT * tot and (lo > 0 or hi < n - 1):
        up = vals[hi + 1:hi + 3].sum() if hi < n - 1 else -1.0
        dn = vals[max(lo - 2, 0):lo].sum() if lo > 0 else -1.0
        if up < 0 and dn < 0:
            break
        if up >= dn:
            acc += vals[hi + 1:hi + 3].sum()
            hi = min(hi + 2, n - 1)
        else:
            acc += vals[max(lo - 2, 0):lo].sum()
            lo = max(lo - 2, 0)
    return float(keys[poc_i]), float(keys[lo]), float(keys[hi])


def interactions(H, L, lo_b, hi_b, W, start=0):
    """Every qualifying interaction with one zone, in order. [(bar, side)].

    side +1 = SUPPORT test (approached from ABOVE, the level sits below price),
    -1 = RESISTANCE test (approached from BELOW, the level sits above price).

    `start` is the first bar at which the level is KNOWN. The Initial Balance
    levels are not defined until 10:30 and must not be interacted with before
    the bar that defines them, which is the difference between a level and a
    look-ahead.

    lo_b/hi_b are arrays so that a MOVING level -- the causal session VWAP --
    uses the same mechanics as a static one, with the boundary evaluated at
    each bar rather than once.

    A session that opens inside the zone yields no interaction on that
    approach: there is no approach side, and inventing one would put a coin
    flip into the outcome statistics. The zone re-arms once price clears it by
    a full zone width -- the same rule that separates first from repeated.
    """
    lo_b = np.broadcast_to(np.asarray(lo_b, float), H.shape)
    hi_b = np.broadcast_to(np.asarray(hi_b, float), H.shape)
    inside = (L <= hi_b) & (H >= lo_b)
    out = []
    armed = not inside[start]
    for i in range(start + 1, len(H)):
        if inside[i]:
            if armed and not inside[i - 1]:
                # previous bar entirely BELOW the zone -> approached from
                # below -> the level is overhead -> RESISTANCE test.
                side = (-1 if H[i - 1] < lo_b[i - 1]
                        else (1 if L[i - 1] > hi_b[i - 1] else 0))
                if side:
                    out.append((i, side))
                armed = False
        elif not armed and (L[i] > hi_b[i] + W or H[i] < lo_b[i] - W):
            armed = True
    return out


def first_grid(H, L, prices, h):
    """Vectorised FIRST interaction for many candidate prices at once.

    Candidates whose zone contains the opening bar are dropped (bar = -1):
    they have no approach side, exactly as for a genuine level, and excluding
    them here keeps the control arm on the same footing as the genuine arm.
    """
    p = np.asarray(prices, float)[:, None]
    inside = (L[None, :] <= p + h) & (H[None, :] >= p - h)
    ok = ~inside[:, 0] & inside.any(axis=1)
    bar = np.where(ok, inside.argmax(axis=1), -1)
    side = np.zeros(len(p), int)
    j = np.where(bar > 0)[0]
    if len(j):
        b = bar[j]
        pu = p[j, 0]
        side[j] = np.where(H[b - 1] < pu - h, -1,
                           np.where(L[b - 1] > pu + h, 1, 0))
    bar = np.where(side == 0, -1, bar)
    return bar, side


def crossed(H, L, lo_b, hi_b):
    lo_b = np.broadcast_to(np.asarray(lo_b, float), H.shape)
    hi_b = np.broadcast_to(np.asarray(hi_b, float), H.shape)
    inside = (L <= hi_b) & (H >= lo_b)
    a = ~inside[:-1] & ~inside[1:]
    up = (H[:-1] < lo_b[:-1]) & (L[1:] > hi_b[1:])
    dn = (L[:-1] > hi_b[:-1]) & (H[1:] < lo_b[1:])
    return int((a & (up | dn)).sum())


def outcome(H, L, C, i, side, lo_b, hi_b, atr, n):
    """Everything measured after one interaction. ATR units where scaled.

    Boundaries are evaluated bar by bar, so a moving level is measured against
    where it actually was at each moment rather than where it was at the touch.
    """
    lo_b = np.broadcast_to(np.asarray(lo_b, float), H.shape)
    hi_b = np.broadcast_to(np.asarray(hi_b, float), H.shape)
    end = min(i + WIN, n - 1)
    s = slice(i, end + 1)
    hh, ll, cc, lb, hb = H[s], L[s], C[s], lo_b[s], hi_b[s]
    r = dict(bar=i, side=side, ref=float(C[i]))
    if side == 1:
        pen = np.flatnonzero(ll < lb)
        r["max_excursion"] = float((lb - ll).max()) / atr
        r["mfe"] = float(hh.max() - C[i]) / atr
        r["mae"] = float(C[i] - ll.min()) / atr
        rec = None
        if len(pen):
            p = int(pen[0])
            a = np.flatnonzero(cc[p:] > hb[p:])
            if len(a):
                rec = p + int(a[0])
        sgn = 1.0
    else:
        pen = np.flatnonzero(hh > hb)
        r["max_excursion"] = float((hh - hb).max()) / atr
        r["mfe"] = float(C[i] - ll.min()) / atr
        r["mae"] = float(hh.max() - C[i]) / atr
        rec = None
        if len(pen):
            p = int(pen[0])
            a = np.flatnonzero(cc[p:] < lb[p:])
            if len(a):
                rec = p + int(a[0])
        sgn = -1.0
    r["penetrated"] = bool(len(pen))
    for k in RECLAIM_H:
        r[f"rec{k}"] = bool(rec is not None and rec <= k)
    for m in ROT_H:
        r[f"rot{m}"] = np.nan
    if rec is not None and rec <= PRIMARY_K:
        for m in ROT_H:
            j = i + rec + m
            if j <= n - 1:
                b = hi_b[j] if side == 1 else lo_b[j]
                r[f"rot{m}"] = sgn * float(C[j] - b) / atr
    return r


# --------------------------------------------------------------------------
def run(limit=None, verbose=True):
    rng = np.random.default_rng(SEED)
    r = pd.read_parquet(RTH, columns=["timestamp", "open", "high", "low",
                                      "close", "volume"])
    r["ts"] = pd.to_datetime(r["timestamp"])
    r = r.sort_values("ts").reset_index(drop=True)
    r["d"] = r.ts.dt.normalize()
    e = pd.read_parquet(ETH, columns=["timestamp", "high", "low"])
    e["ts"] = pd.to_datetime(e["timestamp"])
    e["d"] = e.ts.dt.normalize()
    e["m"] = e.ts.dt.hour * 60 + e.ts.dt.minute
    ebyday = {d: g for d, g in e.groupby("d")}
    byday = {d: g for d, g in r.groupby("d")}
    days = sorted(byday)
    if limit:
        days = days[:limit]

    rows, ctrl, pools = [], [], []
    fun = dict(sessions=len(days), short=0, no_prior=0, no_eth=0, used=0)
    cl = dict(iso=0, c2=0, c3=0)
    cross_n = shift_gen = shift_excl = matched = unmatched = 0
    lvl_obs = {f: 0 for f in FAMS}
    prev = None

    for di, d in enumerate(days):
        if verbose and di % 200 == 0:
            print(f"  {di}/{len(days)} {str(d)[:10]} rows={len(rows)}", flush=True)
        g = byday[d]
        H = g["high"].to_numpy(float)
        L = g["low"].to_numpy(float)
        C = g["close"].to_numpy(float)
        O = g["open"].to_numpy(float)
        V = g["volume"].to_numpy(float)
        n = len(H)
        if n < 300:
            fun["short"] += 1
            prev = (d, g)
            continue
        if prev is None or (d - prev[0]).days > 10:
            fun["no_prior"] += 1
            prev = (d, g)
            continue

        pg = prev[1]
        pH, pL = pg["high"].to_numpy(float), pg["low"].to_numpy(float)
        pC, pV = pg["close"].to_numpy(float), pg["volume"].to_numpy(float)
        pc = np.concatenate([[pC[0]], pC[:-1]])
        atr = float(np.maximum(pH - pL, np.maximum(np.abs(pH - pc),
                                                   np.abs(pL - pc))).mean())
        if not np.isfinite(atr) or atr <= 0:
            fun["no_prior"] += 1
            prev = (d, g)
            continue
        W = THETA * atr
        h = W / 2.0

        lv = {"PDH": float(pH.max()), "PDL": float(pL.min()),
              "PDC": float(pC[-1])}
        typ = (pH + pL + pC) / 3.0
        lv["PDVWAP"] = float((typ * pV).sum() / pV.sum()) if pV.sum() > 0 else np.nan
        lv["POC"], lv["VAL"], lv["VAH"] = value_area(typ, pV)

        eg, epg = ebyday.get(d), ebyday.get(prev[0])
        xh = xl = np.nan
        if eg is not None and epg is not None:
            post = epg[(epg["m"] >= 960) & (epg["m"] < 1200)]
            pre = eg[(eg["m"] >= 240) & (eg["m"] < 570)]
            hs = [x["high"].max() for x in (post, pre) if len(x)]
            ls = [x["low"].min() for x in (post, pre) if len(x)]
            if hs and ls:
                xh, xl = float(max(hs)), float(min(ls))
        if not np.isfinite(xh):
            fun["no_eth"] += 1
        lv["XH"], lv["XL"] = xh, xl
        lv["XM"] = (xh + xl) / 2.0 if np.isfinite(xh) else np.nan

        ib = min(60, n)
        lv["IBH"], lv["IBL"] = float(H[:ib].max()), float(L[:ib].min())
        lv["IBM"] = (lv["IBH"] + lv["IBL"]) / 2.0

        rlo, rhi = float(L.min()), float(H.max())
        rounds = list(np.arange(math.floor(rlo / ROUND_STEP) * ROUND_STEP,
                                math.ceil(rhi / ROUND_STEP) * ROUND_STEP + 1e-9,
                                ROUND_STEP))
        rounds = [float(x) for x in rounds if rlo - W <= x <= rhi + W]

        static = [(f, lv[f]) for f in FAMS
                  if f not in ("VWAP", "ROUND") and np.isfinite(lv.get(f, np.nan))]
        for f, _ in static:
            lvl_obs[f] += 1
        lvl_obs["ROUND"] += len(rounds)
        static += [("ROUND", x) for x in rounds]
        static.sort(key=lambda t: t[1])

        clusters, cur = [], []
        for f, p in static:
            if cur and p - cur[-1][1] <= W:
                cur.append((f, p))
            else:
                if cur:
                    clusters.append(cur)
                cur = [(f, p)]
        if cur:
            clusters.append(cur)
        gp = [float(np.mean([p for _, p in c])) for c in clusters]

        cl_lo = np.minimum.accumulate(L)
        cl_hi = np.maximum.accumulate(H)
        lc = np.log(C)
        rv = pd.Series(np.concatenate([[np.nan], np.diff(lc)])).rolling(
            30, min_periods=10).std().to_numpy()

        # ---- candidate grid for the matched random control, once per session
        cands = np.arange(rlo + h, rhi - h, h)
        if len(cands):
            keep = np.array([not any(abs(q - x) <= W for x in gp) for q in cands])
            cands = cands[keep]
        cb, cs = (first_grid(H, L, cands, h) if len(cands)
                  else (np.array([], int), np.array([], int)))
        vmask = cb > 0
        cands, cb, cs = cands[vmask], cb[vmask], cs[vmask]
        cloc = ((cands - cl_lo[cb]) /
                np.maximum(cl_hi[cb] - cl_lo[cb], 1e-9)) if len(cands) else cands
        cdist = np.abs(cands - O[0]) if len(cands) else cands
        cvol = rv[cb] if len(cands) else cands

        # The causal session VWAP is a MOVING level. It cannot be folded into a
        # static cluster mean, so it is evaluated on its own and always counted
        # as isolated; whether a static cluster's zone overlapped it at the
        # moment of interaction is recorded as a flag for the confluence table.
        # It is also kept OUT of the contamination reference set: a level that
        # sweeps the whole session range would otherwise void every shifted
        # control in the study.
        ctyp = (H + L + C) / 3.0
        cvv = np.cumsum(V)
        vw = np.where(cvv > 0, np.cumsum(ctyp * V) / np.maximum(cvv, 1e-9), C)
        lvl_obs["VWAP"] += 1

        targets = []
        for c, cp in zip(clusters, gp):
            fs = sorted({f for f, _ in c})
            # a cluster containing an IB level is not knowable until 10:30
            st = ib if any(x in ("IBH", "IBL", "IBM") for x in fs) else 0
            targets.append((fs, len(c), cp - h, cp + h, None, st))
        targets.append((["VWAP"], 1, vw - h, vw + h, vw, 0))

        for fams, k, lo_b, hi_b, mov, st in targets:
            cp = None if mov is not None else float(lo_b + h)
            cl["iso" if k == 1 else ("c2" if k == 2 else "c3")] += 1
            cross_n += crossed(H, L, lo_b, hi_b)
            evs = interactions(H, L, lo_b, hi_b, W, start=st)
            if not evs:
                continue

            # shifted controls: one per shifted LEVEL per session
            for mult in SHIFT_W:
                for sg in (+1, -1):
                    off = sg * mult * W
                    sp = (mov + off) if mov is not None else (cp + off)
                    shift_gen += 1
                    ref = float(np.mean(sp)) if mov is not None else sp
                    if any(abs(ref - q) <= W for q in gp):
                        shift_excl += 1
                        continue
                    sev = interactions(H, L, sp - h, sp + h, W, start=st)
                    if not sev:
                        continue
                    # repeated interactions are stored for the control too, so
                    # that "first beats repeated" can be checked against an
                    # arbitrary price rather than asserted from the genuine arm
                    # alone. The primary comparison still uses first only.
                    for srank, (si, ss) in enumerate(sev):
                        spx = float(sp[si]) if mov is not None else sp
                        row = dict(d=d, yr=d.year, fams="|".join(fams),
                                   iso=(k == 1), arm=f"{sg * mult:+.4f}",
                                   atr=atr, first=(srank == 0), rank=srank,
                                   loc=(spx - cl_lo[si]) /
                                       max(cl_hi[si] - cl_lo[si], 1e-9),
                                   vol=float(rv[si]),
                                   dist_open=float(abs(spx - O[0])))
                        row.update(outcome(H, L, C, si, ss, sp - h, sp + h,
                                           atr, n))
                        ctrl.append(row)

            for rank, (i, side) in enumerate(evs):
                o = outcome(H, L, C, i, side, lo_b, hi_b, atr, n)
                px = float(mov[i]) if mov is not None else cp
                loc = (px - cl_lo[i]) / max(cl_hi[i] - cl_lo[i], 1e-9)
                base = dict(d=d, yr=d.year, mo=f"{d.year}-{d.month:02d}",
                            price=px, fams="|".join(fams), ksize=k,
                            iso=(k == 1), first=(rank == 0), rank=rank,
                            atr=atr, loc=loc, vol=float(rv[i]),
                            dist_open=float(abs(px - O[0])), arm="genuine",
                            vwap_overlap=bool(mov is None and
                                              abs(px - vw[i]) <= W))
                base.update(o)
                gi = len(rows)
                rows.append(base)

                if rank != 0 or not len(cands):
                    continue
                m = (np.abs(cb - i) <= 30) & (np.abs(cloc - loc) <= 0.05)
                d0 = base["dist_open"]
                m &= np.abs(cdist - d0) <= 0.10 * max(d0, 1e-9)
                v0 = base["vol"]
                if np.isfinite(v0) and v0 > 0:
                    m &= np.isfinite(cvol) & (np.abs(cvol - v0) <= 0.10 * v0)
                idx = np.flatnonzero(m)
                if not len(idx):
                    unmatched += 1
                    continue
                matched += 1
                pr, pt = [], []
                for t in idx:
                    q = float(cands[t])
                    qo = outcome(H, L, C, int(cb[t]), int(cs[t]),
                                 q - h, q + h, atr, n)
                    pr.append(qo[f"rec{PRIMARY_K}"])
                    pt.append(qo["rot30"])
                pools.append(dict(gi=gi, fams="|".join(fams), iso=(k == 1),
                                  yr=d.year, side=side,
                                  rec=np.array(pr, bool),
                                  rot=np.array(pt, float)))
        fun["used"] += 1
        prev = (d, g)

    return (pd.DataFrame(rows), pd.DataFrame(ctrl), pools,
            dict(fun=fun, cl=cl, cross=cross_n, shift_gen=shift_gen,
                 shift_excl=shift_excl, matched=matched, unmatched=unmatched,
                 lvl_obs=lvl_obs))


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    R, Cx, pools, meta = run(limit=lim)
    R.to_parquet(OUT / "rp007_1a1_genuine.parquet")
    Cx.to_parquet(OUT / "rp007_1a1_shifted.parquet")
    with open(OUT / "rp007_1a1_pools.pkl", "wb") as f:
        pickle.dump(pools, f)
    import json
    (OUT / "rp007_1a1_meta.json").write_text(json.dumps(meta, indent=1,
                                                        default=str))
    print("genuine", R.shape, "shifted", Cx.shape, "pools", len(pools))
    print(meta["fun"], meta["cl"])
    print("matched", meta["matched"], "unmatched", meta["unmatched"])
