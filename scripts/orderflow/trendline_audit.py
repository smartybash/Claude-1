#!/usr/bin/env python3
"""FORWARD EXECUTION AUDIT — two parallel ledgers from the script's own alerts.

NO SIGNAL IS GENERATED HERE. Every trade originates from an alert emitted by
the actual TradingView script. This module only decides what each alert would
have COST, by resolving it against the tick tape.

  CHART LEDGER       exactly what TradingView books: entry at the chart line
                     price, reversal at the new chart entry price, re-entry
                     wait 0, reverse on, the chart's own stop and target.

  EXECUTABLE LEDGER  only prices available AFTER the alert timestamp: entry at
                     the first tick strictly after the alert, stop and target
                     resolved in true tick order, a reversal only when the
                     opposite alert arrives, the open position closed before
                     the opposite one opens, and commission charged.

THE CAUSALITY RULE THAT DOES THE WORK
  The executable ledger never reads a tick at or before the alert timestamp.
  A line price the market crossed earlier in the bar is therefore unreachable
  by construction, not by a filter that could be forgotten.

Sealed NQ days are not read. 2016-2020 is not read.

Usage:
  python3 scripts/orderflow/trendline_audit.py selftest   # engine validation
  python3 scripts/orderflow/trendline_audit.py audit      # the real ledgers
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
ALERTS = ROOT / "journal/trendline_alerts.csv"

TICK = 0.25
PT = 20.0                       # 1 NQ
COMMISSION_PTS = 0.22           # round turn, reconciled to the supplied ledger
SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}

MIN_REVERSALS = 100             # the declared stopping point
EXPECTED_TICK = 0.25            # NQ. NOT 1.0, NOT 5.0.

ALERT_COLS = [
    "alert_ts",        # 1  UTC, when the alert FIRED (not the bar time)
    "side",            # 2  long | short
    "chart_entry",     # 3  the trendline price the chart books
    "chart_stop",      # 5  chart stop price
    "chart_target",    # 6  chart target price
    "kind",            # 7  entry | reversal
    "pos_before",      # 8  flat | long | short
    "chart_exit_ts",   # 9a chart exit timestamp
    "chart_exit_px",   # 9b chart exit price
    "chart_exit_why",  #    tp | sl | rev
]


# ---------------------------------------------------------------- tape ----

def _grid(path):
    """Measured smallest price gap. Format flags are NOT trusted: a plain .gz
    can be full resolution and an encoded file could in principle be coarse.
    Only measurement decides."""
    from math import gcd
    px = load_any(path)["price"].astype(float)
    u = sorted(set((px * 4).round().astype(int)))
    if len(u) < 2:
        return float("inf")
    g = 0
    for a, b in zip(u[:-1], u[1:]):
        g = gcd(g, b - a)
    return g * 0.25 if g else float("inf")


def true_tick_files(cache=ROOT / "data/cache/tape_grid.json"):
    """Per date, the file with the FINEST measured grid, and only if it is
    0.25. Measurements are cached because they require a full decode."""
    import json
    seen = {}
    try:
        seen = json.loads(cache.read_text())
    except Exception:
        pass
    best, dirty = {}, False
    for f in sorted(glob.glob(str(TAPE / "TAPE_NQ_*"))):
        d = re.search(r"(20\d{6})", os.path.basename(f)).group(1)
        if d.startswith(SEALED_PREFIX) or d in SEALED_DATES:
            continue
        key = f"{os.path.basename(f)}:{os.path.getsize(f)}"
        if key not in seen:
            try:
                seen[key] = _grid(f)
            except Exception:
                seen[key] = float("inf")
            dirty = True
        g = seen[key]
        if g <= EXPECTED_TICK + 1e-9 and (d not in best or g < best[d][1]):
            best[d] = (f, g)
    if dirty:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(seen))
        except Exception:
            pass
    return {d: f for d, (f, _g) in best.items()}


def load_tape(dates):
    T = {}
    files = true_tick_files()
    for d in sorted(dates):
        if d not in files:
            continue
        df = load_any(files[d])
        t = pd.to_datetime(df["time"]).to_numpy()
        p = df["price"].astype(float).to_numpy()
        k = np.empty(len(p), bool)
        k[0] = True
        np.not_equal(p[1:], p[:-1], out=k[1:])
        T[d] = (t[k], p[k])
    return T


def first_after(t, p, ts):
    """First price strictly after ts. This is the whole causality rule."""
    i = int(np.searchsorted(t, np.datetime64(ts), side="right"))
    return (i, float(p[i])) if i < len(p) else (None, None)


def resolve(t, p, i0, side, stop, tgt, deadline):
    """Walk ticks from i0. Return (idx, price, why) for whichever of stop /
    target / the deadline comes FIRST in real time."""
    j1 = (int(np.searchsorted(t, np.datetime64(deadline), side="right"))
          if deadline is not None else len(p))
    v = p[i0:j1]
    if len(v) == 0:
        return None, None, "none"
    hs = (v <= stop) if side > 0 else (v >= stop)
    ht = (v >= tgt) if side > 0 else (v <= tgt)
    iS = int(np.argmax(hs)) if hs.any() else len(v)
    iT = int(np.argmax(ht)) if ht.any() else len(v)
    if iS == len(v) and iT == len(v):
        return None, None, "open"
    if iS <= iT:
        return i0 + iS, float(v[iS]), "sl"
    return i0 + iT, float(v[iT]), "tp"


# ------------------------------------------------------------- ledgers ----

def build(A, T):
    """A = alert frame (sorted). Returns the per-trade comparison frame."""
    rows = []
    for n, a in A.iterrows():
        d = pd.Timestamp(a.alert_ts).strftime("%Y%m%d")
        if d not in T:
            continue
        t, p = T[d]
        side = 1 if str(a.side).lower().startswith("l") else -1

        # ---- market price at the alert, and the executable entry ----------
        ie, ex_ent = first_after(t, p, a.alert_ts)
        if ie is None:
            continue
        mkt = ex_ent

        # ---- CHART ledger: exactly what TradingView books -----------------
        ch_pts = side * (float(a.chart_exit_px) - float(a.chart_entry))

        # ---- EXECUTABLE ledger --------------------------------------------
        # the reversal deadline is the NEXT opposite alert, if any
        nxt = A[(A.index > n) & (A.alert_ts > a.alert_ts)]
        dl = pd.Timestamp(nxt.alert_ts.iloc[0]) if len(nxt) else None
        jx, ex_exit, why = resolve(t, p, ie, side,
                                   float(a.chart_stop), float(a.chart_target), dl)
        if jx is None:
            # still open at the next alert -> the reversal closes it at the
            # first executable tick after THAT alert
            if dl is None:
                continue
            jx, ex_exit = first_after(t, p, dl)
            why = "rev"
            if jx is None:
                continue
        ex_pts = side * (ex_exit - ex_ent) - COMMISSION_PTS

        rows.append(dict(
            alert_ts=a.alert_ts, side=side, kind=a.kind,
            pos_before=a.pos_before,
            chart_entry=float(a.chart_entry), mkt_at_alert=mkt,
            chart_exit_px=float(a.chart_exit_px),
            chart_exit_why=a.chart_exit_why,
            exec_entry=ex_ent, exec_exit=ex_exit, exec_why=why,
            exec_exit_ts=pd.Timestamp(t[jx]),
            chart_pts=ch_pts, exec_pts=ex_pts, diff=ch_pts - ex_pts,
            # slippage in P&L terms: NEGATIVE means the executable fill is
            # worse than the chart's. The self-test asserts this sign.
            slip_entry=-side * (ex_ent - float(a.chart_entry)),
            slip_exit=side * (ex_exit - float(a.chart_exit_px)),
            disagree=(str(a.chart_exit_why) != why),
            same_bar=(pd.Timestamp(a.alert_ts).floor("5min")
                      == pd.Timestamp(a.chart_exit_ts).floor("5min")),
        ))
    return pd.DataFrame(rows)


def groups(R):
    if R.empty:
        return {}
    rev_first = (R.chart_exit_why == "rev") & (R.exec_why == "sl")
    return {
        "ordinary entries": R[R.kind == "entry"],
        "reversal entries": R[R.kind == "reversal"],
        "same-bar exit/re-entry": R[R.same_bar],
        "chart books rev before stop": R[rev_first],
        "ALL": R,
    }


def report(R):
    print("\n" + "=" * 112)
    print("  CHART LEDGER vs EXECUTABLE LEDGER")
    print("=" * 112)
    print(f"  {'group':<30}{'n':>6}{'chart $':>12}{'exec $':>12}"
          f"{'diff pts':>11}{'entry slip':>12}{'exit slip':>11}{'disagree':>10}")
    for g, S in groups(R).items():
        if len(S) == 0:
            print(f"  {g:<30}{0:>6}      -")
            continue
        print(f"  {g:<30}{len(S):>6}{S.chart_pts.sum()*PT:>12,.0f}"
              f"{S.exec_pts.sum()*PT:>12,.0f}{S['diff'].sum():>11,.1f}"
              f"{S.slip_entry.mean():>12.3f}{S.slip_exit.mean():>11.3f}"
              f"{100*S.disagree.mean():>9.1f}%")

    nrev = int((R.kind == "reversal").sum())
    print(f"\n  reversal-affected trades collected: {nrev} of "
          f"{MIN_REVERSALS} required")
    if nrev < MIN_REVERSALS:
        print("  *** INTERIM — IMPLEMENTATION CHECKING ONLY. NOT A VERDICT. ***")
        return

    # ------------------------------------------------ kill conditions ----
    E = R.exec_pts
    w, l = E[E > 0], E[E <= 0]
    pf = (w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.inf
    ch, ex = R.chart_pts.sum() * PT, R.exec_pts.sum() * PT
    rv = R[R.kind == "reversal"]
    sb = R[R.same_bar]
    unavail = (R.slip_entry.abs() > TICK / 2).mean()
    onesided = (sb.slip_entry < 0).mean() if len(sb) else np.nan

    K = [
        ("1 executable expectancy nonpositive", E.mean() <= 0, f"{E.mean():+.3f} pts"),
        ("2 executable profit factor < 1.15", pf < 1.15, f"PF {pf:.2f}"),
        ("3 >half of chart profit lost", (ch > 0 and ex < 0.5 * ch),
         f"${ch:,.0f} -> ${ex:,.0f}"),
        ("4 reversal trades negative in exec", rv.exec_pts.sum() <= 0,
         f"${rv.exec_pts.sum()*PT:,.0f}"),
        ("5 chart fills unavailable after alert", unavail > 0.5,
         f"{100*unavail:.0f}% of entries"),
        ("6 same-bar advantage one-sided", (onesided > 0.7 if np.isfinite(onesided) else False),
         f"{100*onesided:.0f}% favour the chart"),
    ]
    print("\n" + "=" * 112)
    print("  PRE-DECLARED KILL CONDITIONS")
    print("=" * 112)
    for name, hit, detail in K:
        print(f"  {'TRIGGERED' if hit else '   ok    '}  {name:<44} {detail}")
    if any(h for _, h, _ in K):
        print("\n  >>> REJECT the published strategy. At least one kill "
              "condition fired. <<<")
    else:
        print("\n  >>> Executable ledger survives. ELIGIBLE FOR MINIMUM-SIZE "
              "PAPER TRADING. <<<")
        print("  NOT validated from this sample.")


# ------------------------------------------------------------ selftest ----

def selftest():
    """Engine validation on real tape with a DELIBERATELY ARBITRARY trigger.

    This is not a strategy and produces no verdict. Its only job is to prove
    the two ledgers, the tick resolution, the slippage accounting and the
    disagreement counter behave correctly on known inputs.
    """
    files = true_tick_files()
    d = sorted(files)[0]
    T = load_tape([d])
    t, p = T[d]
    print("=" * 112)
    print("  ENGINE SELF-TEST — arbitrary trigger, real tape. NOT A STRATEGY.")
    print("=" * 112)
    print(f"  session {d}   ticks {len(p)}   {t[0]} .. {t[-1]}")

    # arbitrary: every 200th price-change event, alternating side, chart entry
    # deliberately set 3 points BETTER than the market so slippage is non-zero
    # and must show up with the correct sign.
    rows = []
    for k, i in enumerate(range(5000, len(p) - 5000, 4000)):
        side = 1 if k % 2 == 0 else -1
        mkt = p[i]
        ent = mkt - side * 3.0                    # unreachable, better price
        stop = ent - side * 12.0
        tgt = ent + side * 14.0
        rows.append(dict(alert_ts=pd.Timestamp(t[i]),
                         side="long" if side > 0 else "short",
                         chart_entry=ent, chart_stop=stop, chart_target=tgt,
                         kind="entry" if k % 3 else "reversal",
                         pos_before="flat",
                         chart_exit_ts=pd.Timestamp(t[i]), chart_exit_px=tgt,
                         chart_exit_why="tp"))
    A = pd.DataFrame(rows)
    print(f"  synthetic alerts: {len(A)}  (chart entry set 3.00 pts better "
          f"than market, chart always books the target)")
    R = build(A, T)
    print(f"  resolved: {len(R)}")
    print()
    ok = True
    m = R.slip_entry.mean()
    print(f"  entry slippage mean {m:+.3f} pts   expect ~ -3.000 (adverse)")
    ok &= (-3.6 < m < -2.4)
    me = R.slip_exit.mean()
    print(f"  exit  slippage mean {me:+.3f} pts   expect NEGATIVE (adverse)")
    ok &= me < 0
    print(f"  chart P&L  ${R.chart_pts.sum()*PT:>10,.0f}   "
          f"(always +14 pts by construction)")
    print(f"  exec  P&L  ${R.exec_pts.sum()*PT:>10,.0f}")
    ok &= R.chart_pts.sum() > R.exec_pts.sum()
    print(f"  disagreement rate {100*R.disagree.mean():.1f}%  "
          f"(chart says tp every time; the tape need not)")
    ok &= R.exec_entry.notna().all()
    after = all(pd.Timestamp(r.exec_exit_ts) >= pd.Timestamp(r.alert_ts)
                for _, r in R.iterrows())
    print(f"  every executable fill strictly after its alert: {after}")
    ok &= after
    print()
    print("  SELF-TEST", "PASSED" if ok else "FAILED")
    report(R)


# ------------------------------------------------------ step 1 / step 2 ----


def verify(path):
    """STEP 1. Report the five required facts and FAIL unless the grid is 0.25."""
    from math import gcd
    print("=" * 96)
    print("  STEP 1 — RECORDER VERIFICATION")
    print("=" * 96)
    if not os.path.exists(path):
        print(f"  file not found: {path}")
        return 2
    enc = is_encoded(path)
    df = load_any(path)
    t = pd.to_datetime(df["time"])
    px = df["price"].astype(float)
    u = sorted(set((px * 4).round().astype(int)))
    g = 0
    for a, b in zip(u[:-1], u[1:]):
        g = gcd(g, b - a)
    step = g * 0.25 if g else float("nan")

    d = re.search(r"(20\d{6})", os.path.basename(path))
    same_day = []
    if d:
        for f in glob.glob(str(TAPE / f"TAPE_NQ_{d.group(1)}*")):
            same_day.append((os.path.basename(f), is_encoded(f)))
    chosen = true_tick_files().get(d.group(1)) if d else None

    print(f"  file                     {os.path.basename(path)}")
    print(f"  format                   {'ENCODED fmt=1' if enc else 'PLAIN (degraded)'}")
    print(f"  first timestamp          {t.iloc[0]}")
    print(f"  last  timestamp          {t.iloc[-1]}")
    print(f"  rows                     {len(px):,}")
    print(f"  distinct traded prices   {len(u):,}")
    print(f"  smallest price gap       {step:.2f}")
    print(f"  price range              {px.min():.2f} .. {px.max():.2f}")
    print(f"  same-day files on disk   {same_day if same_day else 'none'}")
    print(f"  audit loader would pick  "
          f"{os.path.basename(chosen) if chosen else 'NOTHING (no file at 0.25 for this date)'}")
    print()
    if abs(step - 5.0) < 1e-9:
        print("  *** STOP. Smallest gap is 5.00. This is the degraded copy. ***")
        return 1
    if abs(step - EXPECTED_TICK) > 1e-9:
        print(f"  *** STOP. Smallest gap is {step:.2f}, expected {EXPECTED_TICK}. ***")
        print("  NQ trades on a 0.25 grid. Any coarser step is still quantised.")
        return 1
    if chosen is None or os.path.basename(chosen) != os.path.basename(path):
        print("  *** STOP. Grid is 0.25 but the loader would not select this "
              "file. ***")
        return 1
    print(f"  PASS — 0.25 grid, {'encoded' if enc else 'plain'} format, "
          f"loader selects THIS file over the same-day copies.")
    return 0


def check_alert(raw):
    """STEP 2. Reconcile ONE alert to the first executable tick."""
    import json
    print("=" * 96)
    print("  STEP 2 — SINGLE ALERT RECONCILIATION")
    print("=" * 96)
    try:
        a = json.loads(raw)
    except Exception as e:
        print(f"  JSON did not parse: {e}")
        return 2
    ok = True
    ts = pd.Timestamp(a.get("ts"))
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    print(f"  1 timestamp parses      {ts}   (tape clock is UTC — no conversion)")
    ok &= pd.notna(ts)

    act = str(a.get("act", "")).lower()
    pos = str(a.get("pos", "")).lower()
    prev = str(a.get("prev", "")).lower()
    side = 1 if pos.startswith("l") else (-1 if pos.startswith("s") else 0)
    print(f"  2 side                  act={act!r} pos={pos!r} -> "
          f"{'LONG' if side > 0 else 'SHORT' if side < 0 else 'FLAT (an exit)'}")
    ok &= act in ("buy", "sell")

    if prev in ("", "flat", "none"):
        kind = "entry"
    elif pos in ("", "flat", "none"):
        kind = "exit"
    elif prev != pos:
        kind = "REVERSAL"
    else:
        kind = "add/scale"
    print(f"  3 fresh entry vs reversal  prev={prev!r} -> {kind}")

    px = a.get("px")
    print(f"  4 chart order price     {px}")
    ok &= isinstance(px, (int, float))
    if isinstance(px, (int, float)):
        ongrid = abs(round(px / EXPECTED_TICK) * EXPECTED_TICK - px) < 1e-9
        print(f"    on the 0.25 grid?     {ongrid}"
              + ("" if ongrid else "   <- a line value, not a tradeable price"))

    cmt = str(a.get("cmt", "") or "")
    oid = str(a.get("id", "") or "")
    tag = next((k for k in ("tp", "target", "sl", "stop", "rev", "entry")
                if k in (cmt + " " + oid).lower()), None)
    print(f"  5 comment/id tag        cmt={cmt!r} id={oid!r} -> "
          f"{tag or 'NONE — fall back to the position transition above'}")

    d = ts.strftime("%Y%m%d")
    T = load_tape([d])
    if d not in T:
        print(f"  6 first executable tick  NO TRUE-TICK TAPE FOR {d}")
        print("    Cannot reconcile. Restore the recorder first.")
        return 1
    t_, p_ = T[d]
    i, fill = first_after(t_, p_, ts)
    if i is None:
        print("  6 first executable tick  none after the alert (end of tape)")
        return 1
    lag = (pd.Timestamp(t_[i]) - ts).total_seconds()
    print(f"  6 first executable tick  {pd.Timestamp(t_[i])}  @ {fill:.2f}"
          f"   (+{lag:.3f}s after the alert)")
    if isinstance(px, (int, float)) and side:
        slip = -side * (fill - float(px))
        print(f"    slippage vs chart      {slip:+.2f} pts"
              f"   ({'adverse' if slip < 0 else 'favourable'})")
    print()
    print("  RECONCILED" if ok else "  INCOMPLETE — see the lines above")
    return 0 if ok else 1


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if mode == "selftest":
        return selftest()
    if mode == "verify":
        return verify(sys.argv[2])
    if mode == "alert":
        return check_alert(sys.argv[2])
    if not ALERTS.exists():
        print(f"No alert file at {ALERTS}.")
        print("The forward audit cannot start until the script's own alerts "
              "are being captured. See reports/trendline_forward_audit.md.")
        return
    A = pd.read_csv(ALERTS, parse_dates=["alert_ts", "chart_exit_ts"])
    A = A.sort_values("alert_ts").reset_index(drop=True)
    dates = sorted({pd.Timestamp(x).strftime("%Y%m%d") for x in A.alert_ts})
    T = load_tape(dates)
    missing = [d for d in dates if d not in T]
    print(f"alerts {len(A)}   sessions {len(dates)}   "
          f"with true-tick tape {len(T)}")
    if missing:
        print(f"NO TRUE-TICK TAPE for {len(missing)} sessions: "
              f"{' '.join(missing[:10])}")
        print("Those alerts cannot be audited. Fix the recorder before "
              "collecting more.")
    report(build(A, T))


if __name__ == "__main__":
    sys.exit(main() or 0)
