#!/usr/bin/env python3
"""TRENDLINE REVERSAL — BOUNDED RECONSTRUCTION FROM THE AUTHOR'S DISCLOSED RULES.

THIS IS NOT A REPLICATION. The pivot strength/length and the stop ATR multiplier
were never disclosed, so nine mechanical specifications are built and all nine
are reported. Nothing is optimised and nothing is fitted to the advertised P&L.

DISCLOSED AND FIXED
  NQ 5-minute · Wilder ATR 14 on completed bars · TP = 1.2 x ATR14
  entries intrabar at a pivot-derived trendline · Reverse on · re-entry wait 0
  session 24h

BOUNDED GRID (the only reconstruction freedom)
  pivot left/right in {2/2, 3/3, 5/5}   x   stop in {0.5, 1.0, 1.2} x ATR14

CAUSALITY
  ta.pivothigh(high,L,R) confirms only R complete bars later. A line is built
  from the two latest CONFIRMED pivots and is never available at the historical
  pivot bar. Line values are never revised backwards.

THREE EXECUTION MODELS
  A  TradingView style. Fill at the line value on touch/cross. Same-bar reversal
     at the opposite line value. Stop and reversal in one bar -> reversal wins.
  B  Causal. Completed bar CLOSE beyond the line; fill at the NEXT bar open.
     Honest gap fills. No fill at a price already crossed earlier in the bar.
  C  Tick. True timestamp ordering from the tape. A crossing is valid only when
     the tape first trades through the causal line value. Reversal only after
     the current position has genuinely exited.

Sealed NQ days are not read. 2016-2020 is not read.

Usage: python3 scripts/orderflow/trendline_recon.py
"""
from __future__ import annotations

import glob
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codec import is_encoded, load_any                                  # noqa

ROOT = Path(__file__).resolve().parents[2]
TAPE = ROOT / "data/tape"
TICK = 0.25
PT = 20.0                       # 1 NQ = $20/point

SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

PIVOTS = [2, 3, 5]              # left == right
STOPS = [0.5, 1.0, 1.2]
TP_MULT = 1.2
ATR_N = 14
BAR = "5min"

# cost in POINTS per round turn; reconciled against the supplied ledger
# (7.99 -> 7.77 -> 7.27 -> 5.67 gross points per trade)
COSTS = {"none": 0.00, "commission": 0.22,
         "comm+1tick": 0.72, "comm+2.1pt": 2.32}


# --------------------------------------------------------------- data ----

def sessions():
    out = []
    for f in sorted(glob.glob(str(TAPE / "TAPE_NQ_*"))):
        m = re.search(r"(20\d{6})", os.path.basename(f))
        if not m:
            continue
        d = m.group(1)
        if d.startswith(SEALED_PREFIX) or d in SEALED_DATES:
            continue
        if not is_encoded(f):          # plain files are 5-point quantised
            continue
        out.append((d, f))
    return out


def build_day(path):
    """5-minute bars plus the price-change event stream, from ticks."""
    df = load_any(path)
    t = pd.to_datetime(df["time"]).to_numpy()
    p = df["price"].astype(float).to_numpy()
    keep = np.empty(len(p), bool)
    keep[0] = True
    np.not_equal(p[1:], p[:-1], out=keep[1:])
    t, p = t[keep], p[keep]                       # price-change events only
    b = pd.Series(t).dt.floor(BAR).to_numpy()
    uniq, start = np.unique(b, return_index=True)
    order = np.argsort(start)
    uniq, start = uniq[order], start[order]
    end = np.append(start[1:], len(p))
    o = np.array([p[a] for a in start])
    c = np.array([p[z - 1] for z in end])
    h = np.array([p[a:z].max() for a, z in zip(start, end)])
    l = np.array([p[a:z].min() for a, z in zip(start, end)])
    n = end - start
    ok = n >= 2
    return dict(t=uniq[ok], o=o[ok], h=h[ok], l=l[ok], c=c[ok],
                s=start[ok], e=end[ok], px=p, tick_t=t)


def atr_wilder(h, l, c, n=ATR_N):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = np.full(len(tr), np.nan)
    if len(tr) <= n:
        return a
    a[n] = tr[1:n + 1].mean()
    for i in range(n + 1, len(tr)):
        a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a


# ------------------------------------------------------------- pivots ----

def lines(h, l, k):
    """Causal trendline values. res[i]/sup[i] use ONLY pivots confirmed by i."""
    n = len(h)
    res = np.full(n, np.nan)
    sup = np.full(n, np.nan)
    ph, pl = [], []                      # (bar_index, price), confirmed
    for i in range(n):
        j = i - k                        # the bar that may confirm at i
        if j - k >= 0:
            if h[j] > h[j - k:j].max() and h[j] > h[j + 1:i + 1].max():
                ph.append((j, h[j]))
            if l[j] < l[j - k:j].min() and l[j] < l[j + 1:i + 1].min():
                pl.append((j, l[j]))
        if len(ph) >= 2:
            (i1, p1), (i2, p2) = ph[-2], ph[-1]
            if i2 != i1:
                res[i] = p2 + (p2 - p1) / (i2 - i1) * (i - i2)
        if len(pl) >= 2:
            (i1, p1), (i2, p2) = pl[-2], pl[-1]
            if i2 != i1:
                sup[i] = p2 + (p2 - p1) / (i2 - i1) * (i - i2)
    return res, sup


# ------------------------------------------------------- the machines ----

def snap(x, up):
    return (np.ceil(x / TICK) if up else np.floor(x / TICK)) * TICK


def run_A(D, res, sup, atr, sm):
    """TradingView style. Fill AT the line. Reversal beats stop inside a bar."""
    h, l, o, c = D["h"], D["l"], D["o"], D["c"]
    T = []
    pos = 0
    ent = stop = tgt = 0.0
    eb = -1
    for i in range(len(h)):
        if not np.isfinite(atr[i - 1] if i else np.nan):
            continue
        a = atr[i - 1]
        # A CROSS, not a touch: the prior close must sit on the other side.
        pr = res[i - 1] if i else np.nan
        ps = sup[i - 1] if i else np.nan
        sig_L = (np.isfinite(res[i]) and np.isfinite(pr)
                 and c[i - 1] <= pr and h[i] >= res[i])
        sig_S = (np.isfinite(sup[i]) and np.isfinite(ps)
                 and c[i - 1] >= ps and l[i] <= sup[i])

        if pos != 0:
            rev = sig_S if pos > 0 else sig_L
            hit_s = l[i] <= stop if pos > 0 else h[i] >= stop
            hit_t = h[i] >= tgt if pos > 0 else l[i] <= tgt
            why = px = None
            if rev:                                  # REVERSAL WINS THE TIE
                px, why = (sup[i] if pos > 0 else res[i]), "rev"
            elif hit_s:
                px, why = stop, "sl"
            elif hit_t:
                px, why = tgt, "tp"
            if why:
                T.append(dict(bar=i, dirn=pos, ent=ent, ex=px, why=why,
                              pts=pos * (px - ent), rev=(why == "rev"),
                              same=(i == eb), risk=abs(ent - stop)))
                pos = 0
                if why == "rev":                     # re-entry wait 0
                    pos = -T[-1]["dirn"]
                    ent = px
                    stop = ent - pos * sm * a
                    tgt = ent + pos * TP_MULT * a
                    eb = i
                    continue
        if pos == 0 and (sig_L or sig_S):
            pos = 1 if sig_L else -1
            ent = res[i] if sig_L else sup[i]
            stop = ent - pos * sm * a
            tgt = ent + pos * TP_MULT * a
            eb = i
    return pd.DataFrame(T)


def run_B(D, res, sup, atr, sm):
    """Causal. Close beyond the line; fill at the NEXT bar open."""
    h, l, o, c = D["h"], D["l"], D["o"], D["c"]
    T = []
    pos = 0
    ent = stop = tgt = 0.0
    eb = -1
    pend = 0
    for i in range(len(h)):
        if not np.isfinite(atr[i - 1] if i else np.nan):
            pend = 0
            continue
        a = atr[i - 1]
        if pend != 0 and pos == 0:                   # fill at THIS bar's open
            pos = pend
            ent = o[i]
            stop = ent - pos * sm * a
            tgt = ent + pos * TP_MULT * a
            eb = i
            pend = 0
        if pos != 0:
            hit_s = l[i] <= stop if pos > 0 else h[i] >= stop
            hit_t = h[i] >= tgt if pos > 0 else l[i] <= tgt
            why = px = None
            if hit_s:                                # stop first, honest gap
                px = min(stop, o[i]) if pos > 0 else max(stop, o[i])
                why = "sl"
            elif hit_t:
                px, why = tgt, "tp"
            if why:
                T.append(dict(bar=i, dirn=pos, ent=ent, ex=px, why=why,
                              pts=pos * (px - ent), rev=False,
                              same=(i == eb), risk=abs(ent - stop)))
                pos = 0
        # signals evaluated on the COMPLETED close
        pr = res[i - 1] if i else np.nan
        ps = sup[i - 1] if i else np.nan
        sig_L = (np.isfinite(res[i]) and np.isfinite(pr)
                 and c[i] > res[i] and c[i - 1] <= pr)
        sig_S = (np.isfinite(sup[i]) and np.isfinite(ps)
                 and c[i] < sup[i] and c[i - 1] >= ps)
        if pos != 0:
            rev = sig_S if pos > 0 else sig_L
            if rev and i + 1 < len(h):               # exit AND reverse next open
                px = o[i + 1]
                T.append(dict(bar=i, dirn=pos, ent=ent, ex=px, why="rev",
                              pts=pos * (px - ent), rev=True,
                              same=(i == eb), risk=abs(ent - stop)))
                pos = -pos
                ent = px
                stop = ent - pos * sm * a
                tgt = ent + pos * TP_MULT * a
                eb = i + 1
        elif sig_L or sig_S:
            pend = 1 if sig_L else -1
    return pd.DataFrame(T)


def run_C(D, res, sup, atr, sm):
    """Tick. True timestamp order, and a CROSS must come from the other side."""
    p = D["px"]
    s, e = D["s"], D["e"]
    T = []
    pos = 0
    ent = stop = tgt = 0.0
    eb = -1
    ab_r = ab_s = None                  # carried side state across bars
    for i in range(len(s)):
        if not np.isfinite(atr[i - 1] if i else np.nan):
            continue
        a = atr[i - 1]
        seg = p[s[i]:e[i]]
        m = len(seg)
        rv, sv = res[i], sup[i]
        # crossing masks: True only on the tick that moves through the line
        if np.isfinite(rv):
            ab = seg >= rv
            prev = ab_r if ab_r is not None else ab[0]
            xr = ab & ~np.concatenate(([prev], ab[:-1]))
            ab_r = bool(ab[-1])
        else:
            xr = np.zeros(m, bool)
        if np.isfinite(sv):
            bl = seg <= sv
            prev = ab_s if ab_s is not None else bl[0]
            xs = bl & ~np.concatenate(([prev], bl[:-1]))
            ab_s = bool(bl[-1])
        else:
            xs = np.zeros(m, bool)

        j = 0
        while j < m:
            v = seg[j:]
            cr, cs_ = xr[j:], xs[j:]
            if pos == 0:
                iL = np.argmax(cr) if cr.any() else m
                iS = np.argmax(cs_) if cs_.any() else m
                if iL == m and iS == m:
                    break
                if iL <= iS:
                    pos, ent, k = 1, float(v[iL]), iL
                else:
                    pos, ent, k = -1, float(v[iS]), iS
                stop = ent - pos * sm * a
                tgt = ent + pos * TP_MULT * a
                eb = i
                j += k + 1
                continue
            hs = (v <= stop) if pos > 0 else (v >= stop)
            ht = (v >= tgt) if pos > 0 else (v <= tgt)
            ho = cs_ if pos > 0 else cr
            iS_ = np.argmax(hs) if hs.any() else m
            iT_ = np.argmax(ht) if ht.any() else m
            iO_ = np.argmax(ho) if ho.any() else m
            k = min(iS_, iT_, iO_)
            if k == m:
                break
            if iS_ == k:
                px, why = float(v[iS_]), "sl"
            elif iT_ == k:
                px, why = float(v[iT_]), "tp"
            else:
                px, why = float(v[iO_]), "rev"
            T.append(dict(bar=i, dirn=pos, ent=ent, ex=px, why=why,
                          pts=pos * (px - ent), rev=(why == "rev"),
                          same=(i == eb), risk=abs(ent - stop)))
            pos = 0
            j += k + 1
            if why == "rev":            # reversal only AFTER a genuine exit
                pos = -T[-1]["dirn"]
                ent = px
                stop = ent - pos * sm * a
                tgt = ent + pos * TP_MULT * a
                eb = i
    return pd.DataFrame(T)


# ------------------------------------------------------------ reporting --

def stats(T, cost, n_sessions):
    if len(T) == 0:
        return None
    p = T.pts.to_numpy(float) - cost
    w, l = p[p > 0], p[p <= 0]
    gp, gl = w.sum(), -l.sum()
    eq = np.cumsum(p)
    dd = float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0
    rv = T.rev.to_numpy(bool)
    return dict(
        n=len(T), per_sess=len(T) / n_sessions,
        win=100.0 * len(w) / len(p),
        avg_w=w.mean() if len(w) else 0.0,
        avg_l=l.mean() if len(l) else 0.0,
        exp=p.mean(), pf=(gp / gl if gl > 0 else np.inf),
        dd_pts=dd, dd_usd=dd * PT, pnl=p.sum() * PT,
        rev_pct=100.0 * rv.mean(),
        same_pct=100.0 * T.same.mean(),
        pnl_rev=p[rv].sum() * PT, pnl_oth=p[~rv].sum() * PT,
        tp_dist=T[T.why == "tp"].pts.abs().median() if (T.why == "tp").any() else np.nan)


def main():
    S = sessions()
    print("=" * 118)
    print("  BOUNDED RECONSTRUCTION — NOT A REPLICATION")
    print("=" * 118)
    print(f"  true-tick sessions {len(S)}   {S[0][0]} .. {S[-1][0]}   "
          f"sealed days excluded, 2016-2020 unread")
    print(f"  grid: pivot L/R {PIVOTS} x stop {STOPS} x ATR14   TP fixed 1.2xATR14")
    print(f"  costs in points/round-turn: {COSTS}")
    print("  Positions are flattened at each tape day's end (the archive is not")
    print("  contiguous across weekends and excluded days). Declared, not hidden.")

    DAYS = []
    for d, f in S:
        D = build_day(f)
        D["atr"] = atr_wilder(D["h"], D["l"], D["c"])
        DAYS.append((d, D))
    nb = sum(len(D["h"]) for _, D in DAYS)
    print(f"  5-minute bars built from ticks: {nb}   "
          f"({nb/len(DAYS):.0f} a session)")

    LN = {}
    for k in PIVOTS:
        for d, D in DAYS:
            LN[(k, d)] = lines(D["h"], D["l"], k)

    rows = []
    for k in PIVOTS:
        for sm in STOPS:
            for mdl, fn in (("A", run_A), ("B", run_B), ("C", run_C)):
                parts = []
                for d, D in DAYS:
                    r, s_ = LN[(k, d)]
                    T = fn(D, r, s_, D["atr"], sm)
                    if len(T):
                        parts.append(T)
                T = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
                for cn, cv in COSTS.items():
                    st = stats(T, cv, len(DAYS))
                    if st is None:
                        continue
                    rows.append(dict(pivot=f"{k}/{k}", stop=sm, model=mdl,
                                     cost=cn, **st))
    R = pd.DataFrame(rows)
    R.to_csv(ROOT / "reports/trendline_recon.csv", index=False)

    # ------------------------------------------------ calibration check --
    print("\n" + "=" * 118)
    print("  CALIBRATION CHECK — Model A, no cost, against the supplied ledger")
    print("=" * 118)
    print("  ledger: 28.6 trades/session · 57% win · 7.99 gross pts/trade · "
          "20.4% reversal-affected")
    print(f"\n  {'pivot':<8}{'stop':>6}{'trades':>8}{'per sess':>10}{'win%':>8}"
          f"{'pts/trade':>11}{'rev%':>8}{'same%':>8}{'TP dist':>9}")
    A = R[(R.model == "A") & (R.cost == "none")]
    for _, r in A.iterrows():
        print(f"  {r['pivot']:<8}{r['stop']:>6.1f}{r['n']:>8.0f}"
              f"{r['per_sess']:>10.1f}{r['win']:>8.1f}{r['exp']:>11.2f}"
              f"{r['rev_pct']:>8.1f}{r['same_pct']:>8.1f}{r['tp_dist']:>9.2f}")

    # ------------------------------------------------------ full tables --
    for mdl in ("A", "B", "C"):
        print("\n" + "=" * 118)
        print(f"  MODEL {mdl}")
        print("=" * 118)
        print(f"  {'pivot':<8}{'stop':>6}{'cost':<12}{'n':>7}{'win%':>7}"
              f"{'avgW':>8}{'avgL':>8}{'exp':>8}{'PF':>7}{'maxDD$':>10}"
              f"{'P&L $':>12}{'rev%':>7}{'same%':>7}{'$rev':>11}{'$other':>11}")
        for _, r in R[R.model == mdl].iterrows():
            print(f"  {r['pivot']:<8}{r['stop']:>6.1f}{r['cost']:<12}"
                  f"{r['n']:>7.0f}{r['win']:>7.1f}{r['avg_w']:>8.2f}"
                  f"{r['avg_l']:>8.2f}{r['exp']:>8.3f}{r['pf']:>7.2f}"
                  f"{r['dd_usd']:>10,.0f}{r['pnl']:>12,.0f}"
                  f"{r['rev_pct']:>7.1f}{r['same_pct']:>7.1f}"
                  f"{r['pnl_rev']:>11,.0f}{r['pnl_oth']:>11,.0f}")

    # -------------------------------------------------- the decision ----
    print("\n" + "=" * 118)
    print("  THE DECLARED DECISION RULE")
    print("=" * 118)
    ok = []
    for k in PIVOTS:
        for sm in STOPS:
            b = R[(R["pivot"] == f"{k}/{k}") & (R.stop == sm) & (R.model == "B")
                  & (R.cost == "comm+1tick")]
            c = R[(R["pivot"] == f"{k}/{k}") & (R.stop == sm) & (R.model == "C")
                  & (R.cost == "comm+1tick")]
            if b.empty or c.empty:
                continue
            b, c = b.iloc[0], c.iloc[0]
            dep = (100.0 * b['pnl_rev'] / b['pnl']) if b['pnl'] > 0 else 999.0
            cond = (b['pnl'] > 0, c['pnl'] > 0, b['pf'] > 1.15 and c['pf'] > 1.15,
                    dep <= 50.0)
            if all(cond):
                ok.append((k, sm))
            print(f"  pivot {k}/{k} stop {sm}: B P&L ${b['pnl']:>10,.0f} PF {b['pf']:.2f} | "
                  f"C P&L ${c['pnl']:>10,.0f} PF {c['pf']:.2f} | "
                  f"rev-dependency {dep:>6.1f}%  -> "
                  f"{'PASS' if all(cond) else 'fail'}")
    print(f"\n  specifications passing all conditions: {len(ok)} of 9")
    print("\n  2016-2020 was not read. Sealed days were not read.")


if __name__ == "__main__":
    main()
