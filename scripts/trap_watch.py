"""Flag qualifying liquidity-trap setups (gated Marco playbook) and journal them.

Usage: python3 scripts/trap_watch.py [YYYY-MM-DD]

Rules implemented (reports/liquidity_playbook.md, "Implementable version"):
  - levels: prior-day RTH high/low (respected: prior close >= 0.15 ATR away,
    not consumed by an opening gap) and overnight high/low
  - regime gate: entry only after 11:00 ET and only on CHOP/NEUTRAL read
  - sweep of the level, then a 15-min bar CLOSE back inside it
  - sweep deeper than 0.45 ATR past the level invalidates the trap
  - entry = reclaim close; stop = sweep extreme -/+ 0.05 ATR;
    target = nearest pool (prior close first); time exit 15:59

Appends flagged setups to journal/trades.csv (deduped) and resolves outcomes
when the session's remaining bars are available.
"""

import sys
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regime.data import load_ibkr_json
from regime.filter import read_1100
from regime.indicators import atr

DATA = Path(__file__).resolve().parents[1] / "data"
JOURNAL = Path(__file__).resolve().parents[1] / "journal" / "trades.csv"
COLS = ["date", "instrument", "side", "level_name", "level", "sweep_ext", "entry",
        "stop", "target", "regime", "status", "pnl_pts", "pnl_atr"]


def futures_atr(etf_daily: pd.DataFrame, fut_prior_close: float, date: pd.Timestamp) -> float:
    idx = pd.to_datetime(etf_daily.index.date)
    m = idx <= pd.Timestamp((date - pd.offsets.BDay(1)).date())
    return float(atr(etf_daily, 20)[m].iloc[-1]) * fut_prior_close / float(etf_daily["close"][m].iloc[-1])


def scan(name: str, fut_file: str, etf_file: str, date: pd.Timestamp) -> list[dict]:
    fut = load_ibkr_json(DATA / fut_file)
    prior = date - pd.offsets.BDay(1)
    dts = pd.Series(fut.index.date, index=fut.index)
    prior_rth = fut[(dts == prior.date()) & (fut.index.time >= dtime(9, 30)) & (fut.index.time < dtime(16, 0))]
    on = fut[(fut.index >= pd.Timestamp(f"{prior.date()} 18:00", tz="America/New_York"))
             & (fut.index < pd.Timestamp(f"{date.date()} 09:30", tz="America/New_York"))]
    rth = fut[(dts == date.date()) & (fut.index.time >= dtime(9, 30)) & (fut.index.time < dtime(16, 0))]
    if prior_rth.empty or rth.empty:
        print(f"{name}: insufficient data for {date.date()}")
        return []

    pc = float(prior_rth["close"].iloc[-1])
    a = futures_atr(load_ibkr_json(DATA / etf_file), pc, date)
    o = float(rth["open"].iloc[0])

    # regime read from the first 90 minutes (needs the window complete)
    fh = rth[rth.index.time < dtime(11, 0)]
    if fh.index[-1].time() < dtime(10, 55):
        print(f"{name}: first-90-min window incomplete — regime read pending, no flags yet")
        return []
    c30 = fh["close"].resample("30min", origin=fh.index[0]).last().dropna()
    path = float(c30.diff().abs().sum() + abs(c30.iloc[0] - float(fh["open"].iloc[0])))
    reg = read_1100(a, o, float(fh["high"].max()), float(fh["low"].min()),
                    float(fh["close"].iloc[-1]), fh_path=path)
    print(f"{name} {date.date()}: regime {reg.state} (range {reg.range_atr} ATR, pos {reg.pos}) | ATR {a:,.0f}")
    if reg.state.startswith("TREND"):
        print(f"   TREND read — trap setups OFF today")
        return []

    levels = []
    for lname, lvl, respected in [
        ("prior_day_low", float(prior_rth["low"].min()), abs(pc - float(prior_rth["low"].min())) >= 0.15 * a),
        ("prior_day_high", float(prior_rth["high"].max()), abs(pc - float(prior_rth["high"].max())) >= 0.15 * a),
        ("overnight_low", float(on["low"].min()) if len(on) else np.nan, True),
        ("overnight_high", float(on["high"].max()) if len(on) else np.nan, True),
    ]:
        if np.isnan(lvl) or not respected:
            continue
        side = "long" if "low" in lname else "short"
        if (side == "long" and o <= lvl) or (side == "short" and o >= lvl):
            continue  # gap through: level consumed
        levels.append((lname, lvl, side))

    b15 = pd.DataFrame({
        "open": rth["open"].resample("15min", origin=rth.index[0]).first(),
        "high": rth["high"].resample("15min", origin=rth.index[0]).max(),
        "low": rth["low"].resample("15min", origin=rth.index[0]).min(),
        "close": rth["close"].resample("15min", origin=rth.index[0]).last(),
    }).dropna()

    out = []
    for lname, lvl, side in levels:
        sgn = 1 if side == "long" else -1
        breached = b15["low"] < lvl if side == "long" else b15["high"] > lvl
        if not breached.any():
            continue
        t0 = breached.idxmax()
        after = b15.loc[t0:]
        reclaimed = after["close"] > lvl if side == "long" else after["close"] < lvl
        reclaimed = reclaimed[reclaimed]
        if not len(reclaimed):
            continue
        # the FIRST reclaim is the trade; it must fall at/after 11:00 (regime
        # gate) or the setup is skipped — never re-time to a later close
        e_ts = reclaimed.index[0]
        if e_ts.time() < dtime(11, 0):
            continue
        seg = b15.loc[t0:e_ts]
        ext = float(seg["low"].min()) if side == "long" else float(seg["high"].max())
        if abs(ext - lvl) > 0.45 * a:
            continue  # trap invalidated: sweep ran too deep
        entry = float(b15.loc[e_ts, "close"])
        stop = ext - sgn * 0.05 * a
        pools = [pc] + [l for n, l, s in levels if n != lname]
        prof = [p for p in pools if sgn * (p - entry) > 0.05 * a]
        if not prof:
            continue
        target = min(prof, key=lambda p: abs(p - entry))

        status, pnl = "open", np.nan
        for ts, bar in rth.loc[e_ts + pd.Timedelta(minutes=15):].iterrows():
            if (side == "long" and bar["low"] <= stop) or (side == "short" and bar["high"] >= stop):
                status, pnl = "stopped", sgn * (stop - entry)
                break
            if (side == "long" and bar["high"] >= target) or (side == "short" and bar["low"] <= target):
                status, pnl = "target", sgn * (target - entry)
                break
        if status == "open" and rth.index[-1].time() >= dtime(15, 55):
            status, pnl = "moc", sgn * (float(rth["close"].iloc[-1]) - entry)

        rec = {"date": str(date.date()), "instrument": name, "side": side,
               "level_name": lname, "level": round(lvl, 2), "sweep_ext": round(ext, 2),
               "entry": round(entry, 2), "stop": round(stop, 2), "target": round(target, 2),
               "regime": reg.state, "status": status,
               "pnl_pts": round(pnl, 2) if not np.isnan(pnl) else "",
               "pnl_atr": round(pnl / a, 3) if not np.isnan(pnl) else ""}
        out.append(rec)
        far = [p for p in pools if sgn * (p - entry) > 0.05 * a]
        far_t = max(far, key=lambda p: abs(p - entry)) if far else target
        tight_stop = ext - sgn * 0.03 * a
        print(f"   SETUP {side.upper()} @ {lname} {lvl:,.2f}: swept to {ext:,.2f}, reclaimed {e_ts.strftime('%H:%M')} "
              f"-> entry {entry:,.2f} stop {stop:,.2f} target {target:,.2f} [{status}"
              + (f" {pnl:+,.2f} pts" if not np.isnan(pnl) else "") + "]")
        print(f"      Marco-style alt (unvalidated at our data resolution — needs 1-min): "
              f"retest limit {lvl:,.2f}, tight stop {tight_stop:,.2f} "
              f"({abs(lvl - tight_stop):,.1f} pts risk), runner target {far_t:,.2f} "
              f"({abs(far_t - lvl) / max(abs(lvl - tight_stop), 1e-9):.1f}R)")
    if not out:
        print("   no qualifying setups")
    return out


def main():
    date = pd.Timestamp(sys.argv[1]) if len(sys.argv) > 1 else pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
    recs = []
    recs += scan("NQ", "nq_5min_live.json", "qqq_daily_5y.json", date)
    recs += scan("ES", "es_5min_live.json", "spy_daily_5y.json", date)
    if recs:
        JOURNAL.parent.mkdir(exist_ok=True)
        old = pd.read_csv(JOURNAL) if JOURNAL.exists() else pd.DataFrame(columns=COLS)
        new = pd.DataFrame(recs)[COLS]
        key = ["date", "instrument", "level_name", "side"]
        merged = pd.concat([old[~old.set_index(key).index.isin(new.set_index(key).index)], new])
        merged.to_csv(JOURNAL, index=False)
        print(f"\njournal: {len(merged)} rows -> {JOURNAL.relative_to(JOURNAL.parents[1])}")


if __name__ == "__main__":
    main()
