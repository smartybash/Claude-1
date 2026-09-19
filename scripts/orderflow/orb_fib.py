#!/usr/bin/env python3
"""ORB + FIBONACCI — CONTINUATION AND REVERSAL. Measurement module.

Pre-registered at `5612140` (`reports/orb_fibonacci_preregistration.md`)
before this file was written. Every parameter below is declared there and
NONE of them is swept.

    X = 1.00 x ORB height     outburst must travel this far beyond the break
    Y = 30 bars               and must get there within this many bars
    Z = 5 bars                extreme confirmed by this many bars of no new extreme
    k = 2                     swing fractal half-width, 5-bar fractal
    bands A (0.382, 0.618) and B (0.500, 0.786)   near edge = entry, deep = failure

CONTINUATION AND REVERSAL ARE NEVER POOLED. They are returned as separate
frames and the study script reports them in separate tables.

1-minute bars. Sealed dates excluded at construction. 2016-2020 unreachable:
this module reads only QQQ_1m.parquet, which begins 2021-01-04.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/intraday_long/QQQ_1m.parquet"

# ------------------------------------------------- declared, not swept ------
X_MULT = 1.00          # outburst size, multiples of ORB height
Y_BARS = 30            # bars allowed to reach X
Z_BARS = 5             # bars of no new extreme that confirm the extreme
K_FRAC = 2             # swing fractal half-width
BANDS = {"A": (0.382, 0.618), "B": (0.500, 0.786)}
ORB_MINS = (15, 30)    # 09:30-09:45 and 09:30-10:00
BUFFER = 0.01          # "beyond the outburst origin", one cent on QQQ
COST_F = 2.00 / 30000.0
FLAT_MIN = 390         # 16:00 ET, minutes from 09:30

SEALED_PREFIX, SEALED_DATES = "202606", {"20260723"}
MIN_BARS = 360


# ------------------------------------------------------------ primitives ----

def swing_lows(lo, k=K_FRAC):
    """Indices of k-fractal swing lows. Confirmed only after k later bars."""
    n = len(lo)
    out = []
    for i in range(k, n - k):
        v = lo[i]
        if all(v < lo[i - j] for j in range(1, k + 1)) and \
           all(v < lo[i + j] for j in range(1, k + 1)):
            out.append(i)
    return out


def swing_highs(hi, k=K_FRAC):
    n = len(hi)
    out = []
    for i in range(k, n - k):
        v = hi[i]
        if all(v > hi[i - j] for j in range(1, k + 1)) and \
           all(v > hi[i + j] for j in range(1, k + 1)):
            out.append(i)
    return out


def find_outburst(hi, lo, i_break, origin, need, direction, literal=False):
    """The declared outburst machine.

    Returns (i_extreme, extreme, i_confirmed) or None.

    direction +1 = up leg. `need` = X * ORB height, already multiplied.
    The 50% retracement invalidation applies from the break UNTIL X is
    reached; after that the leg is established and we only locate its
    terminal extreme via Z bars of no new extreme. Declared in advance.

    AMENDMENT 1 (`c9196d1`), made on counts alone before any expectancy was
    seen: the 50% retracement is measured against the REQUIRED leg length
    `need`, not against the run-so-far. Taken literally the rule is degenerate
    at leg inception -- on the break bar the leg is a few cents wide, so the
    next bar's ordinary range retraces half of it mechanically, killing 99% of
    attempts within 3 bars. Measuring against `need` is parameter-free (X and
    the ORB height are already declared) and preserves the source's intent:
    the impulse must not give back half the move it is making.

    `literal=True` restores the pre-amendment behaviour for the side-by-side
    funnel that the amendment requires be reported.
    """
    n = len(hi)
    ext = hi[i_break] if direction > 0 else lo[i_break]
    i_ext = i_break
    reached = False
    since = 0
    for j in range(i_break, n):
        cur = hi[j] if direction > 0 else lo[j]
        new = cur > ext if direction > 0 else cur < ext
        if new:
            ext, i_ext, since = cur, j, 0
        elif reached:
            since += 1
            if since >= Z_BARS:
                return i_ext, ext, j
        run = abs(ext - origin)
        if not reached:
            if run >= need:
                reached = True
                since = 0
                continue
            if j > i_break:
                # 50% invalidation while the leg forms
                back = lo[j] if direction > 0 else hi[j]
                base = run if literal else need
                if base > 0 and abs(ext - back) >= 0.50 * base:
                    return None
            if j - i_break >= Y_BARS:
                return None                      # Y exceeded before reaching X
    return None                                   # never confirmed before close


def _walk(hi, lo, op, cl, i_entry, fill, stop, direction, px, i_flat, honest):
    """One pass of the exit machine. Entry bar EXCLUDED.

    honest=True  : stop exits gap, filling at min(stop, bar open) for longs.
    honest=False : the NAIVE convention -- a stop credited at its own trigger
                   price. Reported alongside so the size of the flattery is
                   visible, never used for a verdict.

    Returns (scale-out R, exit reason, ambiguous, thirds filled, whole-position
    R at each of 1R/2R/3R).
    """
    risk = abs(fill - stop)
    cost = px * COST_F
    tg = [fill + direction * m * risk for m in (1, 2, 3)]
    filled = [False, False, False]
    realised, left, amb = 0.0, 1.0, False
    whole = {}
    end = min(len(hi), i_flat + 1)
    why = "close"
    for j in range(i_entry + 1, end):
        st = lo[j] <= stop if direction > 0 else hi[j] >= stop
        sx = stop if not honest else (min(stop, op[j]) if direction > 0
                                      else max(stop, op[j]))
        for m in range(3):
            ht = hi[j] >= tg[m] if direction > 0 else lo[j] <= tg[m]
            if ht and st:
                amb = True
            if m + 1 not in whole:                # first resolution wins
                if st:                            # stop-first convention
                    whole[m + 1] = direction * (sx - fill)
                elif ht:
                    whole[m + 1] = direction * (tg[m] - fill)
            if filled[m] or st:
                continue
            if ht:
                realised += (1.0 / 3.0) * direction * (tg[m] - fill)
                filled[m] = True
                left -= 1.0 / 3.0
        if st:
            realised += left * direction * (sx - fill)
            left, why = 0.0, "stop"
            break
        if left <= 1e-9:
            why = "3R"
            break
    else:
        realised += left * direction * (cl[end - 1] - fill)
    if why == "close" and left > 1e-9 and 0 < left < 1.0:
        why = "close-partial"
    for m in (1, 2, 3):
        if m not in whole:
            whole[m] = direction * (cl[end - 1] - fill)
    return ((realised - cost) / risk, why, amb, filled,
            {m: (v - cost) / risk for m, v in whole.items()}, risk, cost)


def manage(hi, lo, op, cl, i_entry, fill, stop, naive_fill, direction,
           px, i_flat):
    """Primary = honest fills. Naive reported alongside, never for a verdict."""
    R, why, amb, filled, whole, risk, cost = _walk(
        hi, lo, op, cl, i_entry, fill, stop, direction, px, i_flat, True)
    nR, _, _, _, nwhole, _, _ = _walk(
        hi, lo, op, cl, i_entry, naive_fill, stop, direction, px, i_flat, False)
    out = dict(R=R, naive_R=nR, why=why, amb=amb, risk=risk,
               risk_bps=1e4 * risk / px, cost_pct=100 * cost / risk,
               hit1=filled[0], hit2=filled[1], hit3=filled[2],
               slip_R=nR - R)
    for m in (1, 2, 3):
        out[f"R{m}"] = whole[m]
        out[f"naive_R{m}"] = nwhole[m]
    return out


# ------------------------------------------------------------- per session --

def session_setups(day, t, hi, lo, op, cl, orb_min, band, literal=False):
    """Return (continuation_trade_or_None, reversal_trade_or_None, diag)."""
    near, deep = BANDS[band]
    d = dict(orb_ok=0, broke=0, ob_try=0, ob_ok=0,
             cont_setup=0, cont_trade=0,
             fib_fail=0, shift_wick=0, shift_close=0,
             ob2_ok=0, rev_setup=0, rev_trade=0, look=0)
    orb = (t >= 0) & (t < orb_min)
    if orb.sum() < 3 or (t >= orb_min).sum() < 60:
        return None, None, d
    oh, ol = float(hi[orb].max()), float(lo[orb].min())
    rng = oh - ol
    if rng <= 0:
        return None, None, d
    d["orb_ok"] = 1
    px = float(op[0])
    i_flat = int(np.searchsorted(t, FLAT_MIN, "left")) - 1
    if i_flat <= 0:
        i_flat = len(t) - 1
    i0 = int(np.searchsorted(t, orb_min, "left"))
    n = len(t)

    # ---- first break of either boundary
    up = np.where(hi[i0:] > oh)[0]
    dn = np.where(lo[i0:] < ol)[0]
    if len(up) == 0 and len(dn) == 0:
        return None, None, d
    iu = i0 + int(up[0]) if len(up) else n + 1
    idn = i0 + int(dn[0]) if len(dn) else n + 1
    if iu == idn:
        return None, None, d                 # same bar, direction undefined
    direction = 1 if iu < idn else -1
    i_brk = min(iu, idn)
    origin = oh if direction > 0 else ol
    d["broke"] = 1

    # ---- outburst
    d["ob_try"] = 1
    ob = find_outburst(hi, lo, i_brk, origin, X_MULT * rng, direction, literal)
    if ob is None:
        return None, None, d
    i_ext, E, i_conf = ob
    d["ob_ok"] = 1
    L = abs(E - origin)
    if L <= 0:
        return None, None, d

    # ================================================== CONTINUATION =========
    cont = None
    entry_lvl = E - direction * near * L
    deep_lvl = E - direction * deep * L
    stop = origin - direction * BUFFER
    # entry only on bars strictly after confirmation
    i_e = None
    for j in range(i_conf + 1, i_flat + 1):
        touched = lo[j] <= entry_lvl if direction > 0 else hi[j] >= entry_lvl
        if touched:
            i_e = j
            break
    if i_e is not None:
        d["cont_setup"] = 1
        if i_e <= i_conf:
            d["look"] += 1
        # LIMIT fill: the limit price, or the open if the bar gapped past it
        fill = min(entry_lvl, op[i_e]) if direction > 0 else max(entry_lvl, op[i_e])
        if abs(fill - stop) > 0 and i_e < i_flat:
            r = manage(hi, lo, op, cl, i_e, fill, stop, entry_lvl,
                       direction, px, i_flat)
            r.update(day=day, year=day.year, dir=direction, setup="continuation",
                     orb_bps=1e4 * rng / px, leg_bps=1e4 * L / px)
            cont = r
            d["cont_trade"] = 1

    # ====================================================== REVERSAL =========
    rev = None
    # 3. Fib failure: a CLOSE beyond the deep edge of the band
    ff = None
    for j in range(i_conf + 1, i_flat + 1):
        beyond = cl[j] < deep_lvl if direction > 0 else cl[j] > deep_lvl
        if beyond:
            ff = j
            break
    if ff is None:
        return cont, None, d
    d["fib_fail"] = 1

    # 4. structure shift: CLOSE beyond the most recent confirmed swing formed
    #    during the outburst (between the break bar and the extreme)
    if direction > 0:
        sw = [i for i in swing_lows(lo) if i_brk <= i <= i_ext]
    else:
        sw = [i for i in swing_highs(hi) if i_brk <= i <= i_ext]
    if not sw:
        return cont, None, d
    shift = None
    for j in range(ff, i_flat + 1):
        cand = [i for i in sw if i + K_FRAC < j]      # confirmed before bar j
        if not cand:
            continue
        lvl = lo[cand[-1]] if direction > 0 else hi[cand[-1]]
        wick = lo[j] < lvl if direction > 0 else hi[j] > lvl
        clos = cl[j] < lvl if direction > 0 else cl[j] > lvl
        if wick and shift is None:
            d["shift_wick"] = 1
        if clos:
            shift = j
            break
    if shift is None:
        return cont, None, d
    d["shift_close"] = 1

    # 5. opposite outburst. O2 = the extreme between E and the reversal leg.
    rev_dir = -direction
    seg = slice(i_ext, shift + 1)
    O2 = float(hi[seg].max()) if direction > 0 else float(lo[seg].min())
    ob2 = find_outburst(hi, lo, shift, O2, X_MULT * rng, rev_dir, literal)
    if ob2 is None:
        return cont, None, d
    i_ext2, E2, i_conf2 = ob2
    d["ob2_ok"] = 1
    L2 = abs(E2 - O2)
    if L2 <= 0:
        return cont, None, d

    # 6-7. new Fib from O2 to E2, entry at the near edge, stop beyond O2
    entry2 = E2 - rev_dir * near * L2
    stop2 = O2 - rev_dir * BUFFER
    i_e2 = None
    for j in range(i_conf2 + 1, i_flat + 1):
        touched = lo[j] <= entry2 if rev_dir > 0 else hi[j] >= entry2
        if touched:
            i_e2 = j
            break
    if i_e2 is None:
        return cont, None, d
    d["rev_setup"] = 1
    if i_e2 <= i_conf2:
        d["look"] += 1
    fill2 = min(entry2, op[i_e2]) if rev_dir > 0 else max(entry2, op[i_e2])
    if abs(fill2 - stop2) > 0 and i_e2 < i_flat:
        r = manage(hi, lo, op, cl, i_e2, fill2, stop2, entry2,
                   rev_dir, px, i_flat)
        r.update(day=day, year=day.year, dir=rev_dir, setup="reversal",
                 orb_bps=1e4 * rng / px, leg_bps=1e4 * L2 / px)
        rev = r
        d["rev_trade"] = 1
    return cont, rev, d


# ------------------------------------------------------------------ driver --

def load():
    raw = pd.read_parquet(SRC)
    raw["day"] = raw.timestamp.dt.date
    keep = []
    for day, g in raw.groupby("day", sort=True):
        s = day.strftime("%Y%m%d")
        if s.startswith(SEALED_PREFIX) or s in SEALED_DATES:
            continue
        if len(g) < MIN_BARS:
            continue
        keep.append((day, g.sort_values("timestamp")))
    return keep


def run(sessions, orb_min, band, literal=False):
    C, R, D = [], [], []
    for day, g in sessions:
        o = pd.Timestamp(dt.datetime.combine(day, dt.time(9, 30)))
        t = (g.timestamp - o).dt.total_seconds().to_numpy() / 60.0
        c, r, d = session_setups(
            day, t, g.high.to_numpy(float), g.low.to_numpy(float),
            g.open.to_numpy(float), g.close.to_numpy(float), orb_min, band,
            literal)
        if c: C.append(c)
        if r: R.append(r)
        D.append(d)
    return (pd.DataFrame(C), pd.DataFrame(R),
            pd.DataFrame(D).sum().to_dict())
