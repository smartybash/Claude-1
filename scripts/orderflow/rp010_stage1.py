#!/usr/bin/env python3
"""RP-010 Stage 1 -- order-flow impact, absorption and exhaustion. DESCRIPTIVE.

Pre-registered at reports/rp010_stage0_proposal.md. No entry, stop, target or
strategy is defined. No expectancy, profit factor or drawdown is computed.

PLATFORM CONDITIONS (all mandatory, all enforced in code):
  1. every time window comes from sessioncal
  2. every aggression / impact figure comes from orderflow_core
  3. test_platform.py must pass before this runs; the count is reported
  4. dataquality output appears in the report
  5. no overnight variable is read

FROZEN:
  windows     30 s, NON-OVERLAPPING, cash only, first and last 5 min excluded
  cooldown    5 minutes after an identified event
  cap         6 events per session
  thresholds  aggression p90 / high impact p80 / low impact p20, all from the
              trailing TEN COMPLETED sessions only
  horizons    30 s, 1, 3, 5, 10, 15 minutes, strictly AFTER the event window

DECLARED BEFORE THE AMENDED RUN (diagnostics only; no label, threshold, event
or primary outcome changes):
  forward aggressive volume   direction-adjusted net aggressive contracts in the
                              forward slice, per horizon -- the brief's
                              "additional same direction aggressive volume"
  named-level proximity       the brief's "near versus away from named levels,
                              as a diagnostic only". Levels are CAUSAL and
                              contain NO overnight variable (condition 5):
                                prior regular session high / low / close
                                current-session VWAP, cumulative to the event
                                IB high / low, eligible only after minute 60
                                round 50-point prices
                              near = terminal price within 10 ticks (2.5 pts) of
                              any eligible level. The primary result does not
                              use levels, by construction (RP-007 closed them).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataquality as DQ                                            # noqa: E402
import orderflow_core as OF                                         # noqa: E402
import sessioncal as SC                                             # noqa: E402
from tape import load_all, price_step, rth, is_full_session         # noqa: E402

WIN_S = 30
EXCL_HEAD_MIN, EXCL_TAIL_MIN = 5, 5
COOLDOWN_MIN = 5
MAX_EVENTS = 6
TRAIL_SESS = 10
P_AGG, P_HI, P_LO = 90.0, 80.0, 20.0
HZ_S = [30, 60, 180, 300, 600, 900]
TICK = 0.25
COST_PTS = 2.0
SEED = 20260923


def gate():
    """Condition 3: the platform suite must pass before anything runs."""
    r = subprocess.run([sys.executable, str(HERE / "test_platform.py")],
                       capture_output=True, text=True)
    tail = [ln for ln in r.stdout.splitlines() if "PASS " in ln and "FAIL" in ln]
    line = tail[-1].strip() if tail else "(no summary)"
    if r.returncode != 0:
        print(f"PLATFORM TESTS FAILED -- {line}")
        sys.exit(2)
    return line


def session_frames():
    """The 44 full 0.25 NQ cash sessions, with data-quality output."""
    days = load_all()
    keep, excluded = [], []
    for d, x in sorted(days.items()):
        step = price_step(x)
        if step > 1:
            excluded.append((str(d), f"resolution {step:.2f}"))
            continue
        if not is_full_session(x):
            excluded.append((str(d), "not a full cash session"))
            continue
        keep.append((str(d), x))
    return keep, excluded


def build():
    keep, excluded = session_frames()
    rng = np.random.default_rng(SEED)
    wins, dq = [], []

    for ds, x in keep:
        day = pd.Timestamp(f"{ds[:4]}-{ds[4:6]}-{ds[6:]}").date()
        s = rth(x).sort_values("time").reset_index(drop=True)
        px = s["price"].to_numpy(float)
        # CONDITION 5 / data quality, measured not assumed
        dq.append(dict(day=ds, tick=DQ.min_increment(px),
                       off_tick=DQ.off_tick(px, TICK),
                       prints=len(s),
                       side_labels="".join(sorted(set(
                           s["aggressor"].dropna().astype(str)))),
                       side_nulls=int(s["aggressor"].isna().sum()),
                       monotonic=DQ.monotonic(s["time"])["monotonic"],
                       max_jump=DQ.roll_scan(px, 100.0)["max_jump"]))
        # CONDITION 1: the calendar owns the clock. The tape is UTC.
        m = SC.minutes_after_open(s["time"], day=day, clock="UTC")
        span = SC.session_minutes(day)
        body = (m >= EXCL_HEAD_MIN) & (m < span - EXCL_TAIL_MIN)
        s = s.loc[body].reset_index(drop=True)
        mm = m[body]
        # local volatility: sd of 30-second log returns over the session
        lv = float(np.std(np.diff(np.log(s["price"].to_numpy(float)[::100]))))

        for k, g in OF.windows(s, WIN_S):
            a = OF.aggression(g)
            p = OF.progress(g, TICK)
            i = OF.impact(a, p)
            j0 = int(g.index[0])
            wins.append(dict(
                day=ds, wk=pd.Timestamp(day).isocalendar().week,
                widx=int(k), tod=float(mm[j0]), i_end=int(g.index[-1]),
                buy=a["buy_vol"], sell=a["sell_vol"], delta=a["delta"],
                total=a["total"], imb=a["imbalance"],
                n_trades=a["n_trades"], n_prices=a["n_prices"],
                vol_term=a["vol_at_terminal"], trades_term=a["trades_at_terminal"],
                signed=p["signed"], ticks=p["ticks"],
                prog_with=(p["max_up"] if a["delta"] >= 0 else p["max_dn"]),
                prog_against=(p["max_dn"] if a["delta"] >= 0 else p["max_up"]),
                tpk=i["ticks_per_1k"], tpd=i["ticks_per_delta"],
                aligned=i["aligned"], loc_vol=lv,
                w_first=p["first"], w_last=p["last"],
                w_hi=float(g["price"].max()), w_lo=float(g["price"].min())))
    W = pd.DataFrame(wins)
    DQ.assert_safe_columns(W, "RP-010 window frame")
    Q = pd.DataFrame(dq)
    DQ.assert_safe_columns(Q, "RP-010 data-quality frame")
    return W, Q, excluded, keep


def label(W):
    """Causal thresholds from the trailing TEN COMPLETED sessions only."""
    days = sorted(W["day"].unique())
    W = W.sort_values(["day", "widx"]).reset_index(drop=True)
    state = np.array(["WARMUP"] * len(W), dtype=object)
    thr = []
    for di, d in enumerate(days):
        if di < TRAIL_SESS:
            continue
        hist = W[W["day"].isin(days[di - TRAIL_SESS:di])]
        a_thr = float(np.percentile(hist["imb"], P_AGG))
        h = hist[hist["imb"] >= a_thr]
        hi_thr = float(np.percentile(h["tpk"], P_HI))
        lo_thr = float(np.percentile(h["tpk"], P_LO))
        thr.append(dict(day=d, a_thr=a_thr, hi_thr=hi_thr, lo_thr=lo_thr,
                        hist_windows=len(hist)))
        cur = W["day"] == d
        agg = cur & (W["imb"] >= a_thr)
        ini = agg & (W["tpk"] >= hi_thr) & W["aligned"]
        abso = agg & (W["tpk"] <= lo_thr)
        state[np.flatnonzero(cur.to_numpy())] = "ORDINARY"
        state[np.flatnonzero(abso.to_numpy())] = "ABSORPTION"
        state[np.flatnonzero(ini.to_numpy())] = "INITIATIVE"
    W = W.assign(state=state)
    W["side"] = np.where(W["delta"] > 0, "buy",
                         np.where(W["delta"] < 0, "sell", "flat"))
    return W, pd.DataFrame(thr)


def cooldown(W):
    """5-minute cooldown, 6-event cap, direction-flip and saturation flags."""
    W = W.sort_values(["day", "widx"]).reset_index(drop=True)
    keep = np.zeros(len(W), bool)
    why = np.array([""] * len(W), dtype=object)
    for d, g in W.groupby("day"):
        last_t, last_side, n = -1e9, None, 0
        for idx in g.index:
            st = W.at[idx, "state"]
            if st not in ("INITIATIVE", "ABSORPTION"):
                continue
            t = W.at[idx, "tod"]
            side = W.at[idx, "side"]
            if t - last_t < COOLDOWN_MIN:
                why[idx] = "flipped" if side != last_side else "extended"
                continue
            if n >= MAX_EVENTS:
                why[idx] = "capped"
                continue
            keep[idx] = True
            why[idx] = "event"
            last_t, last_side, n = t, side, n + 1
    return W.assign(event=keep, drop_reason=why)


def outcomes(W, keep, mask=None):
    """Forward paths, strictly AFTER the event window.

    Computed for EVERY non-warm-up window, not only events, so that every
    control in the pre-registration is exact rather than sampled. The forward
    slice is bounded to the longest horizon, which is what makes that feasible.
    """
    by = {d: rth(x).sort_values("time").reset_index(drop=True)
          for d, x in keep}
    order = [d for d, _ in keep]
    prior = {}
    for i, d in enumerate(order):
        if i == 0:
            continue
        pp = by[order[i - 1]]["price"].to_numpy(float)
        prior[d] = (float(pp.max()), float(pp.min()), float(pp[-1]))
    HMAX = max(HZ_S)
    sel = W if mask is None else W[mask]
    rows = []
    for d, g in sel.groupby("day"):
        s = by[d]
        px = s["price"].to_numpy(float)
        vol = s["volume"].to_numpy(float)
        # signed aggressive volume, from the loader: +volume when the buyer
        # lifted the offer, -volume when the seller hit the bid, 0 otherwise
        sv = s["signed"].to_numpy(float)
        # --- causal named levels, diagnostic only, no overnight variable -----
        day_d = pd.Timestamp(f"{d[:4]}-{d[4:6]}-{d[6:]}").date()
        mo = SC.minutes_after_open(s["time"], day=day_d, clock="UTC")
        vwap = np.cumsum(px * vol) / np.maximum(np.cumsum(vol), 1e-9)
        ib = mo < 60
        ib_hi = float(px[ib].max()) if ib.any() else np.nan
        ib_lo = float(px[ib].min()) if ib.any() else np.nan
        ph, pl, pc = prior.get(d, (np.nan, np.nan, np.nan))
        # UNIT-AGNOSTIC. The tape is stored at MICROSECOND resolution, so
        # dividing asi8 by 1e9 as if it were nanoseconds made every elapsed
        # time 1000x too small and collapsed every horizon onto the whole
        # session. Never assume the unit; let pandas do the subtraction.
        ti = pd.DatetimeIndex(s["time"])
        tt = (ti - ti[0]).total_seconds().to_numpy()
        n = len(px)
        for _, r in g.iterrows():
            j = int(r["i_end"])
            if j + 1 >= n:
                continue
            p0 = float(px[j])
            t0 = tt[j]
            hi = int(np.searchsorted(tt, t0 + HMAX, "right"))
            fwd, secs = px[j + 1:hi], tt[j + 1:hi] - t0
            fsv = sv[j + 1:hi]
            if len(fwd) < 10:
                continue
            sgn = 1.0 if r["delta"] > 0 else (-1.0 if r["delta"] < 0 else 0.0)
            if sgn == 0.0:
                continue
            out = dict(day=d, wk=r["wk"], tod=r["tod"], state=r["state"],
                       side=r["side"], is_event=bool(r["event"]),
                       delta=r["delta"], total=r["total"], imb=r["imb"],
                       tpk=r["tpk"], ticks=r["ticks"], loc_vol=r["loc_vol"],
                       p0=p0, n_fwd=len(fwd))
            for h in HZ_S:
                m = secs <= h
                if not m.any():
                    out[f"r{h}"] = out[f"mfe{h}"] = out[f"mae{h}"] = np.nan
                    out[f"av{h}"] = np.nan
                    continue
                seg = fwd[m]
                adv = sgn * (seg - p0)
                out[f"r{h}"] = float(adv[-1])
                out[f"mfe{h}"] = float(adv.max())
                out[f"mae{h}"] = float(-adv.min())
                # additional SAME-DIRECTION aggressive volume after the event
                out[f"av{h}"] = float(sgn * fsv[m].sum())
            adv = sgn * (fwd - p0)
            hp = np.flatnonzero(adv >= 6.0)
            hm = np.flatnonzero(adv <= -6.0)
            out["t_cont"] = float(secs[hp[0]]) if len(hp) else np.nan
            out["t_rev"] = float(secs[hm[0]]) if len(hm) else np.nan
            back = np.flatnonzero(np.abs(fwd - float(r["w_first"])) < TICK / 2)
            out["t_origin"] = float(secs[back[0]]) if len(back) else np.nan
            ext = (r["w_hi"] if sgn > 0 else r["w_lo"])
            br = np.flatnonzero((fwd > ext) if sgn > 0 else (fwd < ext))
            out["t_break"] = float(secs[br[0]]) if len(br) else np.nan
            # named-level proximity, diagnostic only
            lv = [ph, pl, pc, float(vwap[j]), round(p0 / 50.0) * 50.0]
            if r["tod"] >= 60:
                lv += [ib_hi, ib_lo]
            dd = [abs(p0 - v) for v in lv if v == v]
            out["lvl_dist"] = float(min(dd)) if dd else np.nan
            out["near_level"] = bool(dd and min(dd) <= 2.5)
            rows.append(out)
    O = pd.DataFrame(rows)
    DQ.assert_safe_columns(O, "RP-010 outcome frame")
    return O


if __name__ == "__main__":
    line = gate()
    print(f"PLATFORM GATE: {line}")
    W, Q, excluded, keep = build()
    print(f"windows {W.shape}  sessions {W.day.nunique()}  excluded {len(excluded)}")
    W, THR = label(W)
    W = cooldown(W)
    O = outcomes(W, keep, mask=(W["state"] != "WARMUP"))
    out = ROOT / "reports"
    W.to_parquet(out / "rp010_windows.parquet")
    Q.to_parquet(out / "rp010_dataquality.parquet")
    THR.to_parquet(out / "rp010_thresholds.parquet")
    O.to_parquet(out / "rp010_events.parquet")
    pd.DataFrame(excluded, columns=["day", "reason"]).to_csv(
        out / "rp010_excluded.csv", index=False)
    print(W.groupby("state").size().to_string())
    print(f"events after cooldown/cap: {int(W.event.sum())}  "
          f"outcome rows: {len(O)}")
