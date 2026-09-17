#!/usr/bin/env python3
"""THE BAR-RESOLUTION GATE, run before any QQQ number exists.

Pre-registered in `reports/qqq_screen_preregistration.md` at 697fd55:

    the proxy is usable for a given stop setting if the ambiguous fraction is
    BELOW 20% and the expectancy difference is BELOW 0.25R. A setting that
    fails is NOT screened on QQQ at all.

The question is whether a one-minute (or five-minute) bar can stand in for the
tape when the rule's stop is roughly the size of one bar. The only place both
exist is the 20 NQ discovery sessions, so the identical rule runs there twice:
once on the tick tape at one-second resolution -- the truth -- and once on bars
built from that same tape.

TWO THINGS GET CONFLATED IF YOU ONLY RUN IT ONCE, SO IT IS RUN TWICE

  PANEL A  end to end. The whole state machine on each grid. Coarser bars
           change WHICH TRADES EXIST -- the opening range, the excursion and
           the pullback extreme are all read off bar highs and lows -- as well
           as how they resolve. This is what the QQQ screen actually suffers.

  PANEL B  exits only. Every trade found by the truth run is handed to the
           proxy grid with its entry, stop and target already fixed, and only
           the EXIT is re-decided. One trade in, one trade out, so the four
           numbers the gate asks for are measured on matched pairs rather than
           on two different trade populations.

Panel B starts at the bar AFTER the one containing the entry, because a
bar-only backtest that included the entry bar would charge the trade with
price action that happened before it existed. Trades that resolve inside the
entry bar in truth are therefore invisible to the proxy, and they are counted
and reported separately rather than dropped quietly.

Sealed days are never read: the session list comes from `roster.split`, which
excludes them at construction.

Usage: python3 scripts/orderflow/calibrate.py
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pullback import (COST_PTS, MAX_MIN, EXC_FIXED, run_session,      # noqa
                      second_bars)
from roster import split                                              # noqa
from tape import load_all, price_step, rth                            # noqa

# The grid the screen would use, with the target axis extended to 3R and 4R.
CAL_OR_MIN = (15, 30)
CAL_STOP_ATR = (0.5, 1.0)
CAL_TGT_R = (1.0, 2.0, 3.0, 4.0)

TRUTH = "1s"
PROXIES = ("1min", "5min")

AMB_MAX = 0.20      # pre-registered, not adjustable
DEXP_MAX = 0.25     # R


# ---------------------------------------------------------------- panel B --

def resolve_on(bars, direction, entry, stop, target, entry_t, inclusive=False):
    """Re-decide one already-entered trade's exit on a coarser grid.

    Returns the pessimistic exit (stop wins a bar that spans both), the
    optimistic one (target wins), and whether the deciding bar was ambiguous.
    """
    t, hi, lo, _open_t, _flat_t, _atr = bars
    n = len(t)
    start = int(np.searchsorted(t, entry_t, "right"))
    if inclusive:
        start = max(0, start - 1)
    expires = entry_t + np.timedelta64(MAX_MIN, "m")

    # A trade that opened and closed before the next proxy bar even begins is
    # invisible to a bar-only backtest. It is not "resolved differently", it
    # simply cannot happen on that grid, and it is counted rather than dropped.
    nxt = t[start] if start < n else None

    for i in range(start, n):
        h, l, now = hi[i], lo[i], t[i]
        stopped = l <= stop if direction > 0 else h >= stop
        hit_tgt = h >= target if direction > 0 else l <= target
        if stopped or hit_tgt:
            amb = bool(stopped and hit_tgt)
            pess = stop if stopped else target
            opt = target if hit_tgt else stop
            why = "stop" if stopped else "target"
            return dict(why=why, pess=pess, opt=opt, amb=amb, seen=True,
                        nxt=nxt)
        if now >= expires:
            mid = (h + l) / 2.0
            return dict(why="expiry", pess=mid, opt=mid, amb=False,
                        seen=True, nxt=nxt)

    if n == 0 or start >= n:
        return dict(why="unseen", pess=np.nan, opt=np.nan, amb=False,
                    seen=False, nxt=None)
    mid = (hi[-1] + lo[-1]) / 2.0
    return dict(why="flat", pess=mid, opt=mid, amb=False, seen=True, nxt=nxt)


def panel_b(per, freq, inclusive=False):
    """Truth trades, proxy exits. One row per truth trade."""
    rows = []
    for or_min, satr, tgt in product(CAL_OR_MIN, CAL_STOP_ATR, CAL_TGT_R):
        for d, grids in per.items():
            truth = run_session(grids[TRUTH], or_min, satr, tgt)
            pb = grids.get(freq)
            if pb is None:
                continue
            for k, tr in enumerate(truth):
                r = resolve_on(pb, tr["dir"], tr["entry"], tr["stop"],
                               tr["target"], tr["entry_t"], inclusive)
                risk = tr["risk"]
                t_R = tr["pnl"] / risk
                if r["seen"]:
                    p_R = (tr["dir"] * (r["pess"] - tr["entry"]) -
                           COST_PTS) / risk
                    o_R = (tr["dir"] * (r["opt"] - tr["entry"]) -
                           COST_PTS) / risk
                else:
                    p_R = o_R = np.nan
                rows.append(dict(day=d, k=k, or_min=or_min, satr=satr, tgt=tgt,
                                 risk=risk, truth_why=tr["why"], truth_R=t_R,
                                 truth_amb=tr["ambiguous"],
                                 proxy_why=r["why"], proxy_R=p_R,
                                 proxy_opt_R=o_R, amb=r["amb"],
                                 seen=r["seen"],
                                 invisible=bool(r["nxt"] is not None and
                                                tr["exit_t"] < r["nxt"])))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- panel A --

def panel_a(per, freq, entry_bar_exit=True):
    """The whole machine on one grid. One row per trade it produces."""
    rows = []
    for or_min, satr, tgt in product(CAL_OR_MIN, CAL_STOP_ATR, CAL_TGT_R):
        for d, grids in per.items():
            b = grids.get(freq)
            if b is None:
                continue
            for k, tr in enumerate(run_session(b, or_min, satr, tgt,
                                               entry_bar_exit=entry_bar_exit)):
                rows.append(dict(day=d, k=k, or_min=or_min, satr=satr,
                                 tgt=tgt, why=tr["why"], amb=tr["ambiguous"],
                                 R=tr["pnl"] / tr["risk"], risk=tr["risk"],
                                 pnl=tr["pnl"], entry_t=tr["entry_t"]))
    return pd.DataFrame(rows)


# ------------------------------------------------------- panel C, reversed --

def reverse_panel(per, freq):
    """PROXY trades, TRUTH exits. The decisive direction, and the one Panel B
    cannot answer.

    Panel B asks "does the tape's trade survive bar resolution". Panel C asks
    the question that actually matters for a screen: **a bar-data backtest
    hands you a set of trades and a number -- is that number real?** So every
    trade the proxy grid produced is taken at its own entry, stop and target,
    the moment of fill is located on the tape (the first second the trigger
    price actually traded), and the outcome is decided by the tape from there.

    Nothing here is hypothetical. The entry is a resting stop order at a price
    the proxy itself chose, so if the tape says it filled, it filled.
    """
    rows = []
    for or_min, satr, tgt in product(CAL_OR_MIN, CAL_STOP_ATR, CAL_TGT_R):
        for d, grids in per.items():
            pb = grids.get(freq)
            if pb is None:
                continue
            tt, thi, tlo = grids[TRUTH][0], grids[TRUTH][1], grids[TRUTH][2]
            for tr in run_session(pb, or_min, satr, tgt):
                dirn, e, st, tg = tr["dir"], tr["entry"], tr["stop"], tr["target"]
                # locate the real fill second: the proxy bar is labelled at its
                # left edge, so the fill is at or after that label
                j = int(np.searchsorted(tt, tr["entry_t"], "left"))
                fill = -1
                for i in range(j, len(tt)):
                    if (thi[i] >= e) if dirn > 0 else (tlo[i] <= e):
                        fill = i
                        break
                if fill < 0:
                    continue
                exp = tt[fill] + np.timedelta64(MAX_MIN, "m")
                why, px = "flat", None
                for i in range(fill, len(tt)):
                    h, l, now = thi[i], tlo[i], tt[i]
                    stopped = l <= st if dirn > 0 else h >= st
                    hit = h >= tg if dirn > 0 else l <= tg
                    if stopped:
                        why, px = "stop", st
                        break
                    if hit:
                        why, px = "target", tg
                        break
                    if now >= exp:
                        why, px = "expiry", (h + l) / 2.0
                        break
                if px is None:
                    px = (thi[-1] + tlo[-1]) / 2.0
                risk = tr["risk"]
                rows.append(dict(day=d, or_min=or_min, satr=satr, tgt=tgt,
                                 proxy_R=tr["pnl"] / risk, proxy_why=tr["why"],
                                 true_R=(dirn * (px - e) - COST_PTS) / risk,
                                 true_why=why, risk=risk))
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- run --

def build():
    days = load_all()
    disc, _hold, _bad = split(days)
    per = {}
    for d in sorted(disc):
        if price_step(disc[d]) >= 1.0:
            continue
        s = rth(disc[d])
        grids = {}
        for f in (TRUTH,) + PROXIES:
            b = second_bars(s, f)
            if b is not None:
                grids[f] = b
        if TRUTH in grids:
            per[d] = grids
    return per


def report_gate(B, freq):
    """The four items, per stop setting, exactly as asked."""
    print(f"\n{'=' * 100}")
    print(f"  GATE — NQ tick truth vs NQ {freq} bars, matched trade by trade")
    print(f"{'=' * 100}")
    verdicts = {}
    for satr in CAL_STOP_ATR:
        S = B[B.satr == satr]
        seen = S[S.seen]
        med_risk = S.risk.median()
        amb_rate = seen.amb.mean() if len(seen) else np.nan
        d_exp = (seen.proxy_R.mean() - seen.truth_R.mean()) if len(seen) else np.nan

        dis = seen[seen.truth_why != seen.proxy_why]
        pess_way = int(((seen.truth_why == "target") &
                        (seen.proxy_why == "stop")).sum())
        opt_way = int(((seen.truth_why == "stop") &
                       (seen.proxy_why == "target")).sum())

        amb_rows = seen[seen.amb]
        if len(amb_rows):
            conv_cost = (amb_rows.proxy_R - amb_rows.proxy_opt_R).mean()
            conv_total = (seen.proxy_R.mean() - seen.proxy_opt_R.mean())
        else:
            conv_cost = conv_total = 0.0

        ok = (amb_rate < AMB_MAX) and (abs(d_exp) < DEXP_MAX)
        verdicts[satr] = ok

        inv = int(S.invisible.sum())
        print(f"\n  STOP_ATR {satr}   median risk {med_risk:.1f} pts   "
              f"truth trades {len(S)}   resolvable on {freq} {len(seen)}")
        print(f"    0. truth trades that opened AND closed before the next "
              f"{freq} bar began: {inv} "
              f"({100 * inv / max(len(S), 1):.1f}%) — invisible to bar data")
        print(f"    1. bars spanning both stop and target : "
              f"{100 * amb_rate:5.1f}%   of {len(seen)} trades"
              f"   [bar < {100 * AMB_MAX:.0f}%]")
        print(f"    2. expectancy, truth {seen.truth_R.mean():+.3f}R   "
              f"proxy {seen.proxy_R.mean():+.3f}R   "
              f"difference {d_exp:+.3f}R   [bar < {DEXP_MAX}R]")
        print(f"    3. outcome disagreements : {len(dis)} of {len(seen)} "
              f"({100 * len(dis) / max(len(seen), 1):.1f}%)")
        print(f"         truth target -> proxy stop   {pess_way:4d}"
              f"   (proxy too harsh)")
        print(f"         truth stop   -> proxy target {opt_way:4d}"
              f"   (proxy too kind)")
        other = len(dis) - pess_way - opt_way
        print(f"         other (expiry/flat boundary)  {other:4d}")
        print(f"    4. stop-before-target convention : on the {len(amb_rows)} "
              f"ambiguous bars it costs {conv_cost:+.3f}R each,")
        print(f"         which is {conv_total:+.3f}R across all trades. "
              f"Expected sign negative; measured "
              f"{'negative' if conv_total < 0 else 'non-negative'}.")
        print(f"    VERDICT: {'PASS' if ok else 'FAIL'}")

    print(f"\n  by target, same panel (target distance drives ambiguity):")
    print(f"    {'stop':>6}{'tgt':>6}{'n':>7}{'amb%':>8}{'truthR':>9}"
          f"{'proxyR':>9}{'dR':>8}")
    for satr, tgt in product(CAL_STOP_ATR, CAL_TGT_R):
        S = B[(B.satr == satr) & (B.tgt == tgt) & B.seen]
        if not len(S):
            continue
        print(f"    {satr:>6}{tgt:>6}{len(S):>7}{100 * S.amb.mean():>8.1f}"
              f"{S.truth_R.mean():>+9.3f}{S.proxy_R.mean():>+9.3f}"
              f"{S.proxy_R.mean() - S.truth_R.mean():>+8.3f}")
    return verdicts


def main():
    per = build()
    days = sorted(per)
    print("=" * 100)
    print("BAR-RESOLUTION CALIBRATION GATE")
    print("=" * 100)
    print(f"  sessions ({len(days)}): {' '.join(d[4:] for d in days)}")
    print("  0.25 tick recordings, discovery pile only. Sealed days not read.")
    print(f"  grid calibrated: OR {CAL_OR_MIN}  STOP_ATR {CAL_STOP_ATR}  "
          f"TGT_R {CAL_TGT_R}  EXC {EXC_FIXED}")
    print(f"  {len(CAL_OR_MIN) * len(CAL_STOP_ATR) * len(CAL_TGT_R)} variants "
          f"x {len(days)} sessions, run once per resolution")
    print(f"  pass: ambiguous < {100 * AMB_MAX:.0f}% AND |d expectancy| < "
          f"{DEXP_MAX}R, applied PER STOP SETTING\n")

    # ---- counts before any performance number ----
    print("  TRADE AND SESSION COUNTS, before anything else:\n")
    print(f"  {'grid':>8}{'bars/session':>15}{'trades':>9}{'sessions':>10}"
          f"{'trades/session':>16}")
    A, AO = {}, {}
    for f in (TRUTH,) + PROXIES:
        A[f] = panel_a(per, f)
        AO[f] = panel_a(per, f, entry_bar_exit=False)
        nb = int(np.mean([len(per[d][f][0]) for d in days if f in per[d]]))
        T = A[f]
        print(f"  {f:>8}{nb:>15,}{len(T):>9}{T.day.nunique():>10}"
              f"{len(T) / (T.day.nunique() * 16):>16.2f}")
    print("\n  (trades/session is across all 16 variants combined, so the cap "
          "of two\n   per session per variant means the ceiling is 2.00)")

    results = {}
    for f in PROXIES:
        B = panel_b(per, f)
        results[f] = report_gate(B, f)

        # Panel A, the end-to-end difference. Reported because it is what the
        # QQQ screen would actually suffer, but it is NOT the pre-registered
        # gate and is not used to pass or fail anything.
        print(f"\n  PANEL A, end to end on {f} — the whole machine, so this is"
              f" the trade SET and not just the exits:")
        print(f"    {'stop':>6}{'truth n':>9}{'proxy n':>9}{'truth R':>10}"
              f"{'proxy R':>10}{'dR':>8}{'amb%':>7}   convention")
        for satr in CAL_STOP_ATR:
            t0 = A[TRUTH][A[TRUTH].satr == satr]
            for lbl, tab in (("stop wins the entry bar", A[f]),
                             ("entry bar skipped", AO[f])):
                p0 = tab[tab.satr == satr]
                print(f"    {satr:>6}{len(t0):>9}{len(p0):>9}"
                      f"{t0.R.mean():>+10.3f}{p0.R.mean():>+10.3f}"
                      f"{p0.R.mean() - t0.R.mean():>+8.3f}"
                      f"{100 * p0.amb.mean():>7.1f}   {lbl}")

        if all(results[f].values()):
            print(f"\n  >>> {f} clears the pre-registered gate at every stop "
                  f"setting.")
        elif any(results[f].values()):
            passing = [s for s, ok in results[f].items() if ok]
            print(f"\n  >>> {f} clears it only at STOP_ATR {passing}. "
                  f"The others are untestable on {f} bars.")
        else:
            print(f"\n  >>> {f} fails at every stop setting.")

    print("\n" + "=" * 100)
    print("  OUTCOME")
    print("=" * 100)
    any_pass = any(ok for v in results.values() for ok in v.values())
    for f, v in results.items():
        for satr, ok in v.items():
            print(f"  {f:>6}  STOP_ATR {satr}   "
                  f"{'PASS — may be screened on QQQ' if ok else 'FAIL — not screened'}")
    if not any_pass:
        print("\n  Every stop setting fails at every resolution tested. The "
              "QQQ screen\n  does not happen. The threshold is the "
              "pre-registered one and is not\n  being moved to produce a "
              "workable answer.")


if __name__ == "__main__":
    main()
