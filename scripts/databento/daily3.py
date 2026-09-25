#!/usr/bin/env python3
"""Three daily effects (reports/daily3_preregistration.md, 3390a46).

  --context   seen-data context run, 2010-06-07 -> 2026-09-24, archived and
              repaired rules, exposure-matched null (context only, not a test)
  --forward   paper-tracking from 2026-09-25 on the forward bars pulled monthly
              by forward_pull.py (P8 standing approval); add --review at the
              first review (2027-09-25) for the registered null test

IMPLEMENTATION (fixed before the first run):
  * bars: data/clean/step4/NQ_1m.parquet (RTH 09:30-15:59, naive ET, ratio
    back-adjusted); real points = adjusted points / the entry session's factor.
    A trade whose exit session has a different factor crossed a roll and pays one
    extra round trip.
  * daily bar = RTH open/high/low/close; a day needs >= 300 one-minute bars.
  * ARCHIVED versions reproduce the archive code at daily resolution: fill at the
    level, filters and stop may use bar i, exit search from day i+1 on daily bars
    (stop first, as archived). REPAIRED versions apply R1-R7 and follow the
    1-minute path from the fill minute.
  * null: each random trade keeps one actual trade's direction, sessions held,
    entry and exit minute-of-day and round-trip cost; its start session is
    uniform over the sessions from which the hold fits in the window; prices are
    1-minute closes at those minutes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step4_common as C                                           # noqa: E402

S4 = C.ROOT / "data/clean/step4"
OUT = C.ROOT / "reports"
A0, A1 = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-09-24")
MIN_GAP, K, TREND, MAX_ATR, NBOX, BOX_K, TGT = 0.0003, 5, 20, 2.5, 5, 2.0, 3.0
RT = C.RT_STD_PTS["NQ"]
N_SIM = 5000
SEED = 20260925


def load():
    d = pd.read_parquet(S4 / "NQ_1m.parquet")
    d["day"] = d.timestamp.dt.normalize()
    d["mm"] = (d.timestamp.dt.hour * 60 + d.timestamp.dt.minute - 570).astype(int)
    cnt = d.groupby("day").size()
    d = d[d.day.isin(cnt[cnt >= 300].index)].reset_index(drop=True)
    f = pd.read_parquet(S4 / "NQ_factor.parquet")
    fac = pd.Series(f.factor.to_numpy(), index=pd.to_datetime(f.day))
    days = pd.Index(sorted(d.day.unique()))
    g = d.groupby("day")
    D = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    c58 = d[d.mm == 388].set_index("day").close
    D["c58"] = c58.reindex(D.index)
    D["fac"] = fac.reindex(D.index).to_numpy()
    start = np.searchsorted(d.day.to_numpy(), days.to_numpy())
    end = np.append(start[1:], len(d))
    # minute-of-day price grid for the null (1-minute closes; NaN where no bar)
    P = np.full((len(days), 390), np.nan)
    di = np.searchsorted(days.to_numpy(), d.day.to_numpy())
    P[di, d.mm.clip(0, 389).to_numpy()] = d.close.to_numpy()
    P = pd.DataFrame(P).ffill(axis=1).bfill(axis=1).to_numpy()
    arr = {k: d[k].to_numpy() for k in ("open", "high", "low", "close", "mm")}
    return d, D, days, start, end, arr, P


def wilder_atr(h, l, c, n=14):
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[h[0] - l[0]], tr])
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def walk_minutes(arr, k0, side, stop, tgt):
    """From minute index k0 (inclusive): stop before target within a minute; a
    minute that opens through the stop fills at its open. Returns (price, index)."""
    o, h, l = arr["open"], arr["high"], arr["low"]
    n = len(o)
    step = 20000
    k = k0
    while k < n:
        e = min(n, k + step)
        if side > 0:
            hs = np.flatnonzero(l[k:e] <= stop)
            ht = np.flatnonzero(h[k:e] >= tgt)
        else:
            hs = np.flatnonzero(h[k:e] >= stop)
            ht = np.flatnonzero(l[k:e] <= tgt)
        i_s = hs[0] if len(hs) else None
        i_t = ht[0] if len(ht) else None
        if i_s is not None and (i_t is None or i_s <= i_t):
            j = k + i_s
            px = o[j] if (side > 0 and o[j] <= stop) or (side < 0 and o[j] >= stop) else stop
            return px, j, "stop"
        if i_t is not None:
            j = k + i_t
            gap = (side > 0 and o[j] >= tgt) or (side < 0 and o[j] <= tgt)
            return (o[j] if gap else tgt), j, "target"
        k = e
    return arr["close"][-1], n - 1, "open"


def fill_minute(arr, a, b, side, level, kind):
    """First minute in [a, b) where a resting order at `level` fills.
    kind 'limit': buy limit (side>0) fills when low <= level; 'stop': buy stop
    fills when high >= level. Returns (fill price, index) or None."""
    o, h, l = arr["open"][a:b], arr["high"][a:b], arr["low"][a:b]
    if kind == "limit":
        hit = (l <= level) if side > 0 else (h >= level)
    else:
        hit = (h >= level) if side > 0 else (l <= level)
    idx = np.flatnonzero(hit)
    if not len(idx):
        return None
    j = idx[0]
    op = o[j]
    if kind == "limit":
        px = min(level, op) if side > 0 else max(level, op)
    else:
        px = max(level, op) if side > 0 else min(level, op)
    return px, a + j


def fvg_signals(D, repaired):
    h, l, c = D.h.to_numpy(), D.l.to_numpy(), D.c.to_numpy()
    n = len(D)
    sma = pd.Series(c).rolling(TREND).mean().to_numpy()
    atr = wilder_atr(h, l, c)
    bb, bt, rt_, rb = [np.nan] * 3, [np.nan] * 3, [np.nan] * 3, [np.nan] * 3
    out = []
    for i in range(n):
        pbb, pbt, prt, prb = bb[:], bt[:], rt_[:], rb[:]
        nb = i >= 2 and l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP
        nr = i >= 2 and h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP
        if nb:
            bb, bt = [h[i - 2], pbb[0], pbb[1]], [l[i], pbt[0], pbt[1]]
        else:
            for k in range(3):
                if np.isnan(pbb[k]) or l[i] <= pbb[k]:
                    bb[k] = bt[k] = np.nan
                else:
                    bb[k], bt[k] = pbb[k], pbt[k]
        if nr:
            rt_, rb = [l[i - 2], prt[0], prt[1]], [h[i], prb[0], prb[1]]
        else:
            for k in range(3):
                if np.isnan(prt[k]) or h[i] >= prt[k]:
                    rt_[k] = rb[k] = np.nan
                else:
                    rt_[k], rb[k] = prt[k], prb[k]
        if i < TREND + 1:
            continue
        if repaired:
            up = c[i - 1] > sma[i - 1]
            a_ = atr[i - 1]
        else:
            if np.isnan(sma[i]):
                continue
            up = c[i] > sma[i]
            a_ = atr[i]
        bT = (not nb) and any(not np.isnan(bt[k]) and l[i] <= bt[k] and l[i - 1] > bt[k] for k in range(3))
        rT = (not nr) and any(not np.isnan(rb[k]) and h[i] >= rb[k] and h[i - 1] < rb[k] for k in range(3))
        if bT and up:
            e = max(bt[k] for k in range(3) if not np.isnan(bt[k]) and l[i] <= bt[k] and l[i - 1] > bt[k])
            st = l[max(0, i - K):i].min() if repaired else l[max(0, i - K):i + 1].min()
            if e - st > 0 and not (a_ and (e - st) / a_ > MAX_ATR):
                out.append((i, 1, e, st))
        if rT and not up:
            e = min(rb[k] for k in range(3) if not np.isnan(rb[k]) and h[i] >= rb[k] and h[i - 1] < rb[k])
            st = h[max(0, i - K):i].max() if repaired else h[max(0, i - K):i + 1].max()
            if st - e > 0 and not (a_ and (st - e) / a_ > MAX_ATR):
                out.append((i, -1, e, st))
    return out


def box_signals(D, repaired):
    h, l, c = D.h.to_numpy(), D.l.to_numpy(), D.c.to_numpy()
    atr = wilder_atr(h, l, c)
    bh = pd.Series(h).rolling(NBOX).max().shift(1).to_numpy()
    bl = pd.Series(l).rolling(NBOX).min().shift(1).to_numpy()
    out = []
    for i in range(NBOX + 60, len(D)):
        a_ = atr[i - 1] if repaired else atr[i]
        if np.isnan(a_) or np.isnan(bh[i]) or bh[i] - bl[i] <= 0 or bh[i] - bl[i] > BOX_K * a_:
            continue
        for side, brk in ((1, h[i] > bh[i]), (-1, l[i] < bl[i])):
            if brk:
                out.append((i, side, bh[i] if side > 0 else bl[i], bl[i] if side > 0 else bh[i]))
    return out


def trades_level(D, days, start, end, arr, sigs, kind, repaired):
    """kind: 'limit' (FVG) or 'stop' (breakout). Returns trade rows."""
    rows = []
    taken_day = set()
    h, l, c, o = D.h.to_numpy(), D.l.to_numpy(), D.c.to_numpy(), D.o.to_numpy()
    for i, side, lvl, st in sigs:
        risk = abs(lvl - st)
        if repaired:
            if kind == "stop":
                if i in taken_day:
                    continue
                both = [s for s in sigs if s[0] == i]
                if len(both) == 2:            # R6: the side reached first
                    fills = [(fill_minute(arr, start[i], end[i], s[1], s[2], kind), s) for s in both]
                    fills = [x for x in fills if x[0] is not None]
                    if not fills:
                        continue
                    fm, sg = min(fills, key=lambda x: x[0][1])
                    if sg[1] != side:
                        continue
                    taken_day.add(i)
            fm = fill_minute(arr, start[i], end[i], side, lvl, kind)
            if fm is None:
                continue
            e, k0 = fm
            risk = abs(e - st)
            if (side > 0 and st >= e) or (side < 0 and st <= e):
                continue
            tgt = e + side * TGT * risk
            px, kx, why = walk_minutes(arr, k0, side, st, tgt)
            ex_day = int(np.searchsorted(start, kx, side="right") - 1)
            rows.append(dict(i=i, side=side, entry=e, exit=px, xday=ex_day, why=why,
                             m_in=int(arr["mm"][k0]), m_out=int(arr["mm"][kx])))
        else:
            e = lvl
            tgt = e + side * TGT * risk
            px, xd, why = e + side * (c[-1] - e) * side, len(D) - 1, "open"
            for j in range(i + 1, len(D)):
                if (side > 0 and l[j] <= st) or (side < 0 and h[j] >= st):
                    px, xd, why = st, j, "stop"
                    break
                if (side > 0 and h[j] >= tgt) or (side < 0 and l[j] <= tgt):
                    px, xd, why = tgt, j, "target"
                    break
            else:
                px = c[-1]
            rows.append(dict(i=i, side=side, entry=e, exit=px, xday=xd, why=why, m_in=0, m_out=389))
    return rows


def trades_oversold(D, repaired):
    c = D.c.to_numpy()
    sig = D.c58.to_numpy() if repaired else c
    rows = []
    for i in range(3, len(D) - 1):
        if sig[i] < c[i - 1] and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3]:
            rows.append(dict(i=i, side=1, entry=c[i], exit=c[i + 1], xday=i + 1, why="close",
                             m_in=389, m_out=389))
    return rows


def pnl_frame(rows, D, days):
    T = pd.DataFrame(rows)
    if T.empty:
        return T
    fac = D.fac.to_numpy()
    T["day"] = days[T.i.to_numpy()]
    T["xdate"] = days[T.xday.to_numpy()]
    T["gross"] = T.side * (T.exit - T.entry) / fac[T.i.to_numpy()]
    T["rolls"] = (fac[T.i.to_numpy()] != fac[T.xday.to_numpy()]).astype(int)
    T["net_usd"] = (T.gross - RT * (1 + T.rolls)) * 20.0
    T["hold"] = T.xday - T.i
    return T


def null_p(T, D, days, P, rng, lo, hi):
    """Exposure-matched random-entry null: total net $ of 5,000 random lists."""
    n_days = len(days)
    fac = D.fac.to_numpy()
    first = int(np.searchsorted(days, lo))
    last = int(np.searchsorted(days, hi, side="right")) - 1
    side, hold = T.side.to_numpy(), T.hold.to_numpy()
    mi, mo = T.m_in.clip(0, 389).to_numpy(), T.m_out.clip(0, 389).to_numpy()
    cost = RT * (1 + T.rolls.to_numpy())
    tot = np.empty(N_SIM)
    for s_ in range(N_SIM):
        u = rng.random(len(T))
        span = np.maximum(1, last - hold - first + 1)
        st = first + (u * span).astype(int)
        en = np.minimum(st + hold, n_days - 1)
        g = side * (P[en, mo] - P[st, mi]) / fac[st]
        tot[s_] = ((g - cost) * 20.0).sum()
    actual = T.net_usd.sum()
    return actual, float((1 + (tot >= actual).sum()) / (N_SIM + 1)), float(np.percentile(tot, 95))


def summarise(T, D, days, lo, hi, P, rng, label):
    T = T[(T.day >= lo) & (T.day <= hi)]
    if T.empty:
        return f"  {label:<44} no trades", None
    close = pd.Series(D.c.to_numpy() / D.fac.to_numpy() , index=days)
    ev = C.evaluate(pd.Index(T.xdate), T.gross.to_numpy() - RT * T.rolls.to_numpy(),
                    days[(days >= lo) & (days <= hi)], close_by_session=close)
    act, p, p95 = null_p(T, D, days, P, rng, lo, hi)
    yrs = (hi - lo).days / 365.25
    line = (f"  {label:<44} n {len(T):>4} ({len(T)/yrs:.0f}/yr, long {int((T.side>0).sum())}) | "
            f"${T.net_usd.mean():+,.0f}/trade | win {100*(T.net_usd>0).mean():.1f}% | PF {ev['pf']:.2f} | "
            f"Sharpe {ev['sharpe']:+.2f} | maxDD ${ev['dd_NQ']:,.0f}/NQ ${ev['dd_MNQ']:,.0f}/MNQ | "
            f"total ${act:,.0f} vs null 95th ${p95:,.0f}, p {p:.4f}")
    return line, dict(n=len(T), total=act, p=p, sharpe=ev["sharpe"], pf=ev["pf"])


def build_all(D, days, start, end, arr):
    out = {}
    for rep in (False, True):
        tag = "repaired" if rep else "archived"
        out[("D1 daily FVG continuation", tag)] = pnl_frame(
            trades_level(D, days, start, end, arr, fvg_signals(D, rep), "limit", rep), D, days)
        out[("D2 5-day compression breakout", tag)] = pnl_frame(
            trades_level(D, days, start, end, arr, box_signals(D, rep), "stop", rep), D, days)
        out[("D3 oversold bounce", tag)] = pnl_frame(trades_oversold(D, rep), D, days)
    return out


def context():
    d, D, days, start, end, arr, P = load()
    rng = np.random.default_rng(SEED)
    res = build_all(D, days, start, end, arr)
    L = ["THREE DAILY EFFECTS -- SEEN-DATA CONTEXT (NOT A TEST), NQ 2010-06-07 -> 2026-09-24",
         "Pre-registered 3390a46. Costs NQ $2.25 + 1 tick per side (+1 round trip per roll crossed).",
         "Null: 5,000 exposure-matched random-entry lists (same direction, hold, minute-of-day, cost).", ""]
    rows = []
    for (name, tag), T in res.items():
        line, r = summarise(T, D, days, A0, A1, P, rng, f"{name} [{tag}]")
        L.append(line)
        if r:
            rows.append(dict(rule=name, version=tag, **r))
        if not T.empty:
            T.to_csv(C.OUT / "frozen" / f"daily3_{name.split()[0]}_{tag}_trades.csv", index=False)
    txt = "\n".join(L)
    print(txt)
    (OUT / "daily3_context_output.txt").write_text(txt)
    pd.DataFrame(rows).to_csv(OUT / "daily3_context_results.csv", index=False)


FWD0 = pd.Timestamp("2026-09-25")          # paper-tracking starts (registration date)


def forward(since=FWD0, out=OUT, review=False):
    """Paper-track the three repaired rules from `since`: every trade whose entry
    session is on or after it. Open trades are marked to market and flagged.
    Writes out/daily3_paper_ledger.csv (no price levels; committed) and
    out/daily3_paper_ledger_full.csv (with prices; Databento-derived, gitignored),
    plus out/daily3_paper_status.md. --review adds the registered null test."""
    d, D, days, start, end, arr, P = load()
    if days[-1] < since:
        print(f"No forward sessions yet: bars end {days[-1].date()}, paper-tracking starts {since.date()}. "
              "Forward bars come from scripts/databento/forward_pull.py (P8, monthly).")
        return None
    res = {k: v for k, v in build_all(D, days, start, end, arr).items() if k[1] == "repaired"}
    c, c58 = D.c.to_numpy(), D.c58.to_numpy()
    rows = []
    for (name, _), T in res.items():
        T = T[T.day >= since]
        for r in T.itertuples():
            rows.append(dict(rule=name.split()[0], day=r.day.date(), side=int(r.side),
                             entry_time=(r.day + pd.Timedelta(minutes=570 + int(r.m_in))).strftime("%H:%M"),
                             exit_date=r.xdate.date(),
                             exit_time=(pd.Timedelta(minutes=570 + int(r.m_out)) + r.xdate).strftime("%H:%M"),
                             status="OPEN, marked to market" if r.why == "open" else r.why,
                             rolls=int(r.rolls), gross_pts=round(float(r.gross), 2),
                             net_usd_NQ=round(float(r.net_usd), 2), entry_adj=r.entry, exit_adj=r.exit))
    i = len(D) - 1                               # D3 signal on the last session: entered, exit pending
    if days[i] >= since and c58[i] < c[i - 1] and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3]:
        rows.append(dict(rule="D3", day=days[i].date(), side=1, entry_time="15:59", exit_date=None,
                         exit_time="15:59", status="OPEN, exits next session", rolls=0, gross_pts=0.0,
                         net_usd_NQ=round(-RT * 20.0, 2), entry_adj=c[i], exit_adj=np.nan))
    L = pd.DataFrame(rows, columns=["rule", "day", "side", "entry_time", "exit_date", "exit_time", "status",
                                    "rolls", "gross_pts", "net_usd_NQ", "entry_adj", "exit_adj"])
    L = L.sort_values(["day", "rule"], kind="stable").reset_index(drop=True)
    L.to_csv(out / "daily3_paper_ledger_full.csv", index=False)
    L.drop(columns=["entry_adj", "exit_adj"]).to_csv(out / "daily3_paper_ledger.csv", index=False)
    M = [f"# Three daily effects: paper-tracking status", "",
         f"Registered 3390a46. Window {since.date()} to {days[-1].date()} ({int((days >= since).sum())} sessions). "
         "Costs NQ $2.25 + 1 tick per side. First review 2027-09-25.", "",
         "| rule | trades | closed | open | net $ NQ (closed) | net $ NQ incl. open |", "|---|---|---|---|---|---|"]
    for k in ("D1", "D2", "D3"):
        x = L[L.rule == k]
        op = x.status.str.startswith("OPEN")
        M.append(f"| {k} | {len(x)} | {int((~op).sum())} | {int(op.sum())} | "
                 f"{x.net_usd_NQ[~op].sum():+,.0f} | {x.net_usd_NQ.sum():+,.0f} |")
    if review:
        rng = np.random.default_rng(SEED)
        M += ["", "## Review: exposure-matched null (registered test)", ""]
        ps = {}
        for (name, _), T in res.items():
            line, r = summarise(T, D, days, since, days[-1], P, rng, name)
            M.append("    " + line.strip())
            if r:
                ps[name] = r["p"] if r["total"] > 0 else 1.0
        if ps:
            adj = C.holm(list(ps.values()))
            M.append("")
            M += [f"- {k}: p {p:.4f}, Holm {a:.4f} -> {'PASS' if a <= 0.05 else 'not demonstrated'}"
                  for (k, p), a in zip(ps.items(), adj)]
    txt = "\n".join(M)
    (out / "daily3_paper_status.md").write_text(txt + "\n")
    print(txt)
    return L


if __name__ == "__main__":
    if "--forward" in sys.argv:
        forward(review="--review" in sys.argv)
    else:
        context()
