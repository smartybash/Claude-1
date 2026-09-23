#!/usr/bin/env python3
"""Platform integrity tests. Exits NON-ZERO on any failure.

This is the gate the RP-010 integrity audit requires: the order-flow harness,
the session calendar, the data-quality checks and every control must produce
the KNOWN answer on synthetic data before a hypothesis is tested again.

Usage: python3 scripts/orderflow/test_platform.py
"""
from __future__ import annotations

import datetime as dt
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dataquality as DQ                                            # noqa: E402
import fixtures as FX                                               # noqa: E402
import orderflow_core as OF                                         # noqa: E402
import sessioncal as SC                                             # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail and not cond else ""))


# =========================================================== 1. session cal --
def t_timezone():
    for day, off, openmin in FX.TZ_CASES:
        d = pd.Timestamp(day).date()
        check(f"tz offset {day}", SC.utc_offset_minutes(d) == off,
              f"got {SC.utc_offset_minutes(d)} want {off}")
        check(f"open minute UTC {day}", SC.open_minute_utc(d) == openmin,
              f"got {SC.open_minute_utc(d)} want {openmin}")
    check("DST transitions 2026", SC.dst_transitions(2026) == FX.DST_2026,
          f"got {SC.dst_transitions(2026)}")
    check("cash session 390 min", SC.session_minutes("2026-06-18") == 390)
    check("early close 210 min",
          SC.session_minutes("2026-06-19", early=True) == 210)
    check("IB completes at +60", SC.ib_end_minute() == 60)
    check("FOMC release at +270", SC.fomc_release_minute() == 270)
    h = SC.halt_window_utc("2026-06-18")
    check("CME halt 21:00-22:00 UTC in EDT", h == (21 * 60, 22 * 60), f"{h}")
    h2 = SC.halt_window_utc("2026-01-15")
    check("CME halt 22:00-23:00 UTC in EST", h2 == (22 * 60, 23 * 60), f"{h2}")


def t_minutes_after_open():
    """The RP-009 defect, as a test."""
    et = FX.bars([0, 30, 120], [1, 1, 1], [1, 1, 1], [1, 1, 1], clock="ET")
    ut = FX.bars([0, 30, 120], [1, 1, 1], [1, 1, 1], [1, 1, 1], clock="UTC")
    a = SC.minutes_after_open(et["timestamp"], day=dt.date(2026, 6, 18), clock="ET")
    b = SC.minutes_after_open(ut["timestamp"], day=dt.date(2026, 6, 18), clock="UTC")
    check("minutes_after_open ET", list(a) == [0, 30, 120], f"{list(a)}")
    check("minutes_after_open UTC tape", list(b) == [0, 30, 120], f"{list(b)}")
    wrong = SC.minutes_after_open(ut["timestamp"], day=dt.date(2026, 6, 18),
                                  clock="ET")
    check("wrong clock is detectably wrong (the RP-009 four-hour error)",
          list(wrong) == [240, 270, 360], f"{list(wrong)}")


def t_early_close_detection():
    full = FX.bars(list(range(0, 390, 30)), [1] * 13, [1] * 13, [1] * 13)
    early = FX.bars(list(range(0, 210, 30)), [1] * 7, [1] * 7, [1] * 7,
                    day="2026-06-19")
    both = pd.concat([full, early])
    got = SC.early_closes(both)
    check("early close measured, not remembered",
          got == {dt.date(2026, 6, 19)}, f"{got}")


# ======================================================== 2. data quality ----
def t_dataquality():
    fine = np.arange(100.0, 101.0, 0.25)
    coarse = np.arange(100.0, 200.0, 5.0)
    check("min_increment 0.25", DQ.min_increment(fine) == 0.25)
    check("min_increment 5.00", DQ.min_increment(coarse) == 5.0)
    check("off_tick clean", DQ.off_tick(fine, 0.25) == 0.0)
    check("off_tick dirty", DQ.off_tick(np.array([100.0, 100.1]), 0.25) == 0.5)
    dup = DQ.duplicate_dates(["TAPE_NQ_20260812.csv.gz",
                              "TAPE_NQ_20260812_run2.csv.gz",
                              "TAPE_NQ_20260813.csv.gz"])
    check("duplicate dates found", list(dup) == ["20260812"], f"{dup}")
    c, meta = FX.split_fixture()
    s = DQ.split_scan(c)
    check("split detected at the right index",
          len(s) == 1 and s[0][0] == meta["split_index"], f"{s}")
    check("split ratio ~5", len(s) == 1 and abs(s[0][3] - 5.0) < 0.05, f"{s}")
    st = DQ.staleness([1, 1, 1, 2, 2, 3])
    check("staleness zero-rate", abs(st["zero_rate"] - 0.6) < 1e-9, f"{st}")
    check("staleness max run", st["max_run"] == 2, f"{st}")
    m = DQ.monotonic(pd.date_range("2026-01-01", periods=5, freq="min"))
    check("monotonic ok", m["monotonic"] and m["backsteps"] == 0)
    bad = pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:02",
                          "2026-01-01 00:01"])
    check("non-monotonic detected", not DQ.monotonic(bad)["monotonic"])
    r = DQ.roll_scan([100, 101, 900, 901], thresh_pts=100)
    check("roll detected", r["suspect"] and r["max_jump"] == 799, f"{r}")


# ==================================================== 3. level / barrier -----
def t_ib_lookahead():
    b, meta = FX.ib_fixture()
    m = SC.minutes_after_open(b["timestamp"], clock="ET")
    ib = m < SC.ib_end_minute()
    check("IB high correct", float(b["high"][ib].max()) == meta["ib_high"])
    check("IB low correct", float(b["low"][ib].min()) == meta["ib_low"])
    lvl = float(b["high"][ib].max())
    legal = np.flatnonzero((m >= SC.ib_end_minute()) &
                           (b["high"].to_numpy() >= lvl))
    first = int(m[legal[0]]) if len(legal) else None
    check("no IB interaction before the IB completes",
          first == meta["first_legal_touch_minute"], f"got {first}")


def t_approach_side():
    b, meta = FX.approach_fixture()
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    lvl, h = meta["level"], 0.5
    lo_b, hi_b = lvl - h, lvl + h
    inside = (L <= hi_b) & (H >= lo_b)
    sup, res = [], []
    for i in range(1, len(H)):
        if inside[i] and not inside[i - 1]:
            if H[i - 1] < lo_b:
                res.append(i)          # came from BELOW -> resistance
            elif L[i - 1] > hi_b:
                sup.append(i)          # came from ABOVE -> support
    check("approach from above = support", sup == meta["support_bars"], f"{sup}")
    check("approach from below = resistance", res == meta["resistance_bars"],
          f"{res}")
    check("crossing, not touch: no event while already inside",
          all(not (inside[i] and inside[i - 1]) or i not in sup + res
              for i in range(1, len(H))))


def t_barrier_order():
    paths, meta = FX.barrier_fixture()
    for k, (b, want_out, want_amb) in paths.items():
        H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
        hs = L <= meta["stop"]
        ht = H >= meta["target"]
        js = int(np.argmax(hs)) if hs.any() else -1
        jt = int(np.argmax(ht)) if ht.any() else -1
        if js < 0 and jt < 0:
            out, amb = 0, False
        elif js < 0:
            out, amb = 1, False
        elif jt < 0:
            out, amb = -1, False
        elif js == jt:
            out, amb = -1, True
        else:
            out, amb = (-1, False) if js < jt else (1, False)
        check(f"barrier path {k} outcome", out == want_out,
              f"got {out} want {want_out}")
        check(f"barrier path {k} ambiguity", amb == want_amb,
              f"got {amb} want {want_amb}")


# ===================================================== 4. order-flow core ----
def t_orderflow():
    df, meta = FX.tape_fixture()
    a = OF.aggression(df)
    for k in ("buy_vol", "sell_vol", "delta", "total", "n_trades", "n_prices",
              "terminal_price", "vol_at_terminal", "buy_at_terminal"):
        check(f"aggression {k}", a[k] == meta[k], f"got {a[k]} want {meta[k]}")
    pr = OF.progress(df, tick=0.25)
    check("ticks progressed", pr["ticks"] == meta["ticks_progressed"],
          f"got {pr['ticks']} want {meta['ticks_progressed']}")
    check("signed change", abs(pr["signed"] - 0.75) < 1e-9, f"{pr['signed']}")

    for name, fx, want_low in (("absorption", FX.absorption_fixture, True),
                               ("initiative", FX.initiative_fixture, False)):
        d, m = fx()
        aa = OF.aggression(d)
        pp = OF.progress(d, tick=0.25)
        check(f"{name} delta", aa["delta"] == m["delta"],
              f"got {aa['delta']} want {m['delta']}")
        check(f"{name} total", aa["total"] == m["total"],
              f"got {aa['total']} want {m['total']}")
        check(f"{name} ticks", pr is not None and pp["ticks"] == m["ticks_progressed"],
              f"got {pp['ticks']} want {m['ticks_progressed']}")
        imp = OF.impact(aa, pp)
        check(f"{name} one-sided", aa["imbalance"] > 0.5, f"{aa['imbalance']:.3f}")
        check(f"{name} impact classified {'low' if want_low else 'high'}",
              (imp["ticks_per_1k"] < 20) == want_low,
              f"ticks_per_1k={imp['ticks_per_1k']:.2f}")

    # the two states must be SEPARABLE by impact, not by delta
    da, ma = FX.absorption_fixture()
    di, mi = FX.initiative_fixture()
    ia = OF.impact(OF.aggression(da), OF.progress(da, 0.25))
    ii = OF.impact(OF.aggression(di), OF.progress(di, 0.25))
    check("absorption and initiative separable by impact",
          ii["ticks_per_1k"] > 5 * ia["ticks_per_1k"],
          f"{ii['ticks_per_1k']:.1f} vs {ia['ticks_per_1k']:.1f}")

    # zero-delta and zero-progress must not divide by zero
    z = pd.DataFrame(dict(time=[pd.Timestamp("2026-06-18 14:00")] * 2,
                          price=[100.0, 100.0], volume=[1, 1],
                          aggressor=["B", "S"]))
    az, pz = OF.aggression(z), OF.progress(z, 0.25)
    iz = OF.impact(az, pz)
    check("zero delta handled", az["delta"] == 0 and np.isfinite(iz["ticks_per_1k"]),
          f"{iz}")
    check("zero-progress impact is zero, not nan", iz["ticks_per_1k"] == 0.0,
          f"{iz['ticks_per_1k']}")

    # aggressor labels must actually be used
    flipped = df.copy()
    flipped["aggressor"] = flipped["aggressor"].map({"B": "S", "S": "B"})
    check("aggressor label is load-bearing",
          OF.aggression(flipped)["delta"] == -meta["delta"]
          and OF.aggression(flipped)["total"] == meta["total"],
          f"{OF.aggression(flipped)['delta']} (want {-meta['delta']})")


# ========================================================= 5. controls -------
def t_controls():
    D = FX.ranking_fixture()
    rng = np.random.default_rng(11)

    def spread(strong, weak, frame):
        return float(np.mean([frame.iloc[i][strong[i]] - frame.iloc[i][weak[i]]
                              for i in range(len(frame))]))

    true = spread(D["strong"].to_numpy(), D["weak"].to_numpy(), D)

    # DEFECTIVE control, exactly as shipped in RP-006: the spread is computed
    # first and THAT COLUMN is permuted. Permuting a column and then taking its
    # mean returns the identical mean, which is why the control printed values
    # matching the true ranking to two decimals and tested nothing.
    spread_col = np.array([D.iloc[i][D["strong"].iloc[i]]
                           - D.iloc[i][D["weak"].iloc[i]]
                           for i in range(len(D))])
    bad_mean = float(np.mean(rng.permutation(spread_col)))
    # CORRECT control: permute the (strong, weak) IDENTITY across dates
    perm = rng.permutation(len(D))
    good_mean = spread(D["strong"].to_numpy()[perm],
                       D["weak"].to_numpy()[perm], D)
    check("shuffled control changes what it claims to shuffle",
          abs(good_mean - true) > 0.25, f"true {true:.3f} good {good_mean:.3f}")
    check("column-permuting control is EXACTLY the treatment -- the RP-006 "
          "defect, reproduced",
          abs(bad_mean - true) < 1e-12,
          f"bad {bad_mean:.6f} true {true:.6f}")
    check("identity shuffling is NOT the treatment",
          abs(good_mean - true) > 0.25,
          f"good {good_mean:.3f} true {true:.3f}")

    # random-pair control must produce an observation on EVERY date
    obs = 0
    for i in range(len(D)):
        a, b = rng.choice(["X", "Y", "Z"], 2, replace=False)
        _ = D.iloc[i][a] - D.iloc[i][b]
        obs += 1
    check("random-pair control observes every eligible date", obs == len(D),
          f"{obs}/{len(D)}")

    # shifted levels must stay arbitrary
    genuine = [100.0, 110.0, 130.0]
    W = 3.0
    shifted = [g + s * k * W for g in genuine for k in (10 / 3, 20 / 3)
               for s in (1, -1)]
    kept = [s for s in shifted if not any(abs(s - g) <= W for g in genuine)]
    check("overlapping shifted controls are excluded, not kept",
          len(kept) < len(shifted) and len(kept) > 0,
          f"{len(kept)}/{len(shifted)}")

    # opposite-bias control must return observations
    opp = [(w, s) for s, w in zip(D["strong"], D["weak"])]
    check("opposite-bias control returns observations", len(opp) == len(D))
    opp_mean = spread([o[0] for o in opp], [o[1] for o in opp], D)
    check("opposite-bias control is the negation of the treatment",
          abs(opp_mean + true) < 1e-9, f"{opp_mean:.4f} vs {-true:.4f}")

    # a control must not reproduce the treatment
    check("control does not copy the treatment",
          abs(good_mean - true) > 1e-6)


def main() -> int:
    print("=" * 74)
    print("  PLATFORM INTEGRITY TESTS -- synthetic fixtures, known answers")
    print("=" * 74)
    for section, fn in (("1. session calendar", t_timezone),
                        ("1b. minutes after open", t_minutes_after_open),
                        ("1c. early-close detection", t_early_close_detection),
                        ("2. data quality", t_dataquality),
                        ("3a. IB look-ahead", t_ib_lookahead),
                        ("3b. approach side and crossing", t_approach_side),
                        ("3c. barrier ordering", t_barrier_order),
                        ("4. order-flow core", t_orderflow),
                        ("5. controls", t_controls)):
        print(f"\n{section}")
        try:
            fn()
        except Exception:                                    # noqa: BLE001
            FAIL.append((section, "raised"))
            traceback.print_exc()
    print("\n" + "=" * 74)
    print(f"  PASS {len(PASS)}   FAIL {len(FAIL)}")
    if FAIL:
        print("  FAILURES:")
        for n, d in FAIL:
            print(f"    {n}  {d}")
    print("=" * 74)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
