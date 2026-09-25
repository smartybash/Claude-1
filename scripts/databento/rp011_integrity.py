#!/usr/bin/env python3
"""RP-011 Stage 1, step 2 -- the per-session quality gate on Databento discovery
ticks, with the D3 integrity check replacing the ATAS recorder-status file
(reports/databento_register.md section 3; reports/rp011_stage1_preregistration.md).

Reads session statistics only: trade counts, volumes, timestamps, sides, price
grid. No RP-011 window, state or forward return is built or read here.

FIXED BEFORE THIS SCRIPT FIRST RAN
----------------------------------
Per session (Globex session date = ET + 6 h), RTH = 09:30:00-15:59:59.999 ET:
 1. grid         every print on the 0.25 grid
 2. full cash    not a short/holiday session (register section 8), first RTH
                 print before 09:31:00, last after 15:59:00
 3. side N       zero RTH prints with side N
 4. monotonic    ts_event non-decreasing in sequence order within the instrument
 5. dup dates    session date appears once
 6. prior use    session not in the excluded window or the sealed register, and
                 not read by any earlier order-flow/tick study (see note below)
 7. coverage     RTH prints in every RTH minute from 09:30 to 15:59
 8. gaps         no interval between consecutive RTH trades longer than 60 s
 9. volume       full Globex session volume of the continuous front instrument
                 reconciled to the statistics schema (pull C) CLEARED_VOLUME
                 (stat_type 6) for the same instrument_id, tolerance +/-2%
                 (registered in rp011_stage1_preregistration.md, cba8a50).
10. roll lag     registered exclusion (register section 8)

Treatment of spread/implied trades (register section 3 asks for it here): NO
adjustment. Pull B holds outright trades of the continuous front month only; the
calendar-spread instruments were not bought, so spread-leg, block and other
off-book volume that CME counts in CLEARED_VOLUME cannot be subtracted.

Trade-date mapping: CLEARED_VOLUME is keyed by CME trade date (ts_ref). A Globex
session held on an exchange holiday (e.g. 2026-05-25) has no trade date of its
own and clears with the next one, so the next session is reconciled against the
sum of both sessions' volume.

DISCLOSURE: before this script was written, an exploratory join of the committed
session_quality.csv volumes to CLEARED_VOLUME was run, so the deviation
distribution below was seen before the treatment above was written down. The
tolerance itself (+/-2%) was registered earlier, before pull C landed. No
RP-011 quantity has been computed at any point.

Note on prior use: studies (a)-(e) read NQ 1-minute OHLCV bars for 2021 ->
2026-09-24, which includes the discovery dates, as a "seen, not decisive" block.
No order-flow, aggressor or tick quantity on these dates has been read by any
study. Criterion 6 is applied to tick/order-flow use, as in RP-010's gate; the
bar-level overlap is reported, not hidden.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_derived as BD                                         # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports"
TOL = 0.02
MAX_GAP_S = 60.0
EXCLUDED = {"2026-03-16": "roll lag", "2026-03-17": "roll lag",
            "2026-04-03": "short session (Good Friday)",
            "2026-05-25": "holiday session (Memorial Day)"}
HOLIDAY_CARRY = {"2026-05-25": "2026-05-26"}       # clears with the next trade date
DISC = ("2026-03-02", "2026-05-29")


def cleared_volume():
    fs = sorted(glob.glob(str(ROOT / "data/raw/C/*/*.statistics.dbn.zst")))
    s = pd.concat([db.DBNStore.from_file(f).to_df() for f in fs]).reset_index()
    s = s[s.stat_type == 6].sort_values("ts_recv")
    cv = s.groupby(["instrument_id", "ts_ref"]).quantity.last().reset_index()
    cv["session"] = cv.ts_ref.dt.tz_convert(None).dt.strftime("%Y-%m-%d")
    return cv


def per_session(t):
    rows = []
    for s, x in t.groupby("session"):
        day = s.strftime("%Y-%m-%d")
        r = x[x.rth]
        mins = (r.ts_et.dt.hour * 60 + r.ts_et.dt.minute).unique()
        mono = all(np.all(np.diff(g.sort_values("sequence", kind="stable")
                                  .ts_utc.to_numpy().astype("int64")) >= 0)
                   for _, g in x.groupby("instrument_id"))
        gaps = r.ts_utc.diff().dt.total_seconds()
        front = x.groupby("instrument_id")["qty"].sum().idxmax()
        rows.append(dict(
            session=day, instrument_id=int(front),
            volume=int(x["qty"].sum()),
            volume_front=int(x.loc[x.instrument_id == front, "qty"].sum()),
            rth_prints=len(r),
            off_tick=int((np.round(x.price.to_numpy() / 0.25, 6) % 1 != 0).sum()),
            first_rth=r.ts_et.min().time() if len(r) else None,
            last_rth=r.ts_et.max().time() if len(r) else None,
            rth_side_N=int((r.side == "N").sum()),
            monotonic=bool(mono),
            rth_minutes_missing=int(390 - len(set(mins) & set(range(570, 960)))),
            max_rth_gap_s=float(gaps.max()) if len(r) > 1 else np.nan))
    return pd.DataFrame(rows)


def main():
    t = BD.load_ticks("B1")
    q = per_session(t)
    del t
    q = q[(q.session >= DISC[0]) & (q.session <= DISC[1])].reset_index(drop=True)
    cv = cleared_volume()
    vol = q.set_index("session").volume_front.copy()
    for hol, nxt in HOLIDAY_CARRY.items():
        if hol in vol.index and nxt in vol.index:
            vol[nxt] += vol[hol]
    q["recon_volume"] = q.session.map(vol)
    q = q.merge(cv[["instrument_id", "session", "quantity"]].rename(
        columns={"quantity": "cleared_volume"}), on=["instrument_id", "session"], how="left")
    q["recon_dev"] = q.recon_volume / q.cleared_volume - 1

    import datetime as dt
    c = pd.DataFrame(index=q.index)
    c["grid"] = q.off_tick == 0
    c["full_cash"] = (~q.session.isin([k for k, v in EXCLUDED.items() if "session" in v])
                      & q.first_rth.map(lambda v: v is not None and v < dt.time(9, 31))
                      & q.last_rth.map(lambda v: v is not None and v >= dt.time(15, 59)))
    c["side_N"] = q.rth_side_N == 0
    c["monotonic"] = q.monotonic
    c["dup_dates"] = ~q.session.duplicated(keep=False)
    c["prior_use"] = True           # whole window unseen at tick level (register section 2)
    c["coverage"] = q.rth_minutes_missing == 0
    c["gaps"] = q.max_rth_gap_s <= MAX_GAP_S
    c["volume"] = q.recon_dev.abs() <= TOL
    c["roll_lag"] = ~q.session.isin([k for k, v in EXCLUDED.items() if v == "roll lag"])
    q = pd.concat([q, c.add_prefix("ok_")], axis=1)
    q["passes"] = c.all(axis=1)
    q["passes_ex_volume"] = c.drop(columns="volume").all(axis=1)
    q.to_csv(OUT / "rp011_quality_gate.csv", index=False)

    L = ["RP-011 STAGE 1 -- QUALITY GATE (D3 integrity check), Databento discovery ticks",
         f"sessions in window: {len(q)}", ""]
    L.append("failures by criterion:")
    for k in c.columns:
        L.append(f"  {k:<10} {int((~c[k]).sum()):>3} fail")
    L += ["", f"sessions passing every criterion: {int(q.passes.sum())}",
          f"sessions passing every criterion except volume: {int(q.passes_ex_volume.sum())}",
          f"gate (>= 50 sessions): {'PASS' if q.passes.sum() >= 50 else 'FAIL -- RP-011 Stage 1 stops as registered'}",
          "", "volume reconciliation, trades / cleared - 1 (non-excluded sessions):"]
    v = q.loc[q.ok_roll_lag & q.ok_full_cash, "recon_dev"]
    L.append("  " + " | ".join(f"{k} {v.quantile(p):+.2%}" for k, p in
                               (("min", 0), ("p10", .1), ("p25", .25), ("median", .5),
                                ("p75", .75), ("p90", .9), ("max", 1))))
    L.append(f"  sessions with trades > cleared: {int((v > 0).sum())}")
    L += ["", q[["session", "volume_front", "recon_volume", "cleared_volume", "recon_dev",
                 "max_rth_gap_s", "rth_minutes_missing", "rth_side_N", "passes"]]
          .to_string(index=False, float_format=lambda x: f"{x:.4f}")]
    txt = "\n".join(L)
    print(txt)
    (OUT / "rp011_quality_gate_output.txt").write_text(txt)


if __name__ == "__main__":
    main()
