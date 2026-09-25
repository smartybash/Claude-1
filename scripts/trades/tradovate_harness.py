#!/usr/bin/env python3
"""Harness for the user's own Tradovate fills.

    python3 scripts/trades/tradovate_harness.py data/trades/FILLS.csv --tz America/Chicago \
        [--setups SETUPS.csv] [--sims 5000] [--pool-min 60] [--out reports/trades]

WHAT IT DOES
  1. Reads a Tradovate export. Two shapes are recognised automatically:
       fills / orders   one row per fill or filled order (Orders.csv, Fills.csv):
                        time (Fill Time / Timestamp, or Date + time), side (B/S,
                        Buy/Sell), filled quantity, fill price (Avg Fill Price /
                        avgPrice / Price), contract (NQZ6, MNQZ6); optional
                        Status (only filled rows are kept), commission, fill / order
                        id, account, and a setup tag (a column named setup, tag,
                        strategy, note or text). Round trips are rebuilt FIFO per
                        account and contract; partial fills, scale-ins/outs and
                        reversals are split into matched lots.
       performance      one row per closed trade (Performance.csv: buyPrice,
                        sellPrice, boughtTimestamp, soldTimestamp, qty, pnl); the
                        pairing is taken as given and Tradovate's pnl is checked
                        against ours (a mismatch means a wrong multiplier or side).
     A --setups CSV (first column: order id or fill id; second: setup) overrides
     the tags. NQ = $20/pt, MNQ = $2/pt.
  2. Timestamps are converted from --tz to ET. Tradovate writes them in the
     account's display time zone without an offset, so --tz is REQUIRED unless
     they carry one. If many fills fall outside their bar, other zones are tried
     and the best one is suggested (never applied silently).
  3. Every fill is matched to the Databento NQ 1-minute bar of its minute
     (data/clean/bars_1m: unadjusted continuous front month, all Globex hours;
     MNQ is priced off NQ). A fill more than 2 ticks outside its bar's
     [low, high] is flagged: a wrong --tz, a back-month contract, or no bar.
  4. Costs, two views, per round trip:
       step-4 rule   $2.25 (NQ) / $0.62 (MNQ) commission + 1 tick slippage per
                     side, charged on top of the real fills. The real fills
                     already contain slippage, so this view is conservative.
       actual        the CSV's commission if it has one, else the step-4
                     commission; no extra slippage.
  5. Random baselines on the step-4 basis (5,000 simulated trade lists):
       random entry  each trade keeps its direction, quantity, contract, costs,
                     entry and exit time of day and the number of sessions held,
                     and is placed on a uniformly random eligible session of the
                     window you traded (extended back to at least --pool-min
                     sessions). Same count, same time in the market, same
                     long/short mix: tests WHEN you trade. The exposure-matched
                     null of the P7 registration, applied to your trades.
       shuffled side the same entries and exits at your fill prices, directions
                     permuted across trades (mix preserved): tests WHICH WAY.
     p = (1 + #simulated totals >= yours) / (sims + 1).
  6. Breakdown by setup, ET time-of-day block of the entry (overnight,
     09:30-10:00, 10:00-11:30, 11:30-14:00, 14:00-16:00, after 16:00), setup x
     block, hold length, weekday, contract. Every group gets its own null p and a
     Holm-adjusted p within its breakdown: descriptive, read the Holm column.
     MFE / MAE come from the bars during each trade (whole bars, approximate).

Bars exist to 2026-09-24. Trades outside the bars are costed and reported but
left out of the bar checks and the random-entry null (counted in the report);
more bars need a forward pull (budget rule: quote, plan, approval).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data/clean/bars_1m"
TICK = 0.25
SPEC = {"NQ": dict(mult=20.0, comm=2.25), "MNQ": dict(mult=2.0, comm=0.62)}
BLOCKS = [(-10**6, 0, "overnight (before 09:30)"), (0, 30, "09:30-10:00"), (30, 120, "10:00-11:30"),
          (120, 270, "11:30-14:00"), (270, 390, "14:00-16:00"), (390, 10**6, "after 16:00")]
HOLDS = [(0, 5, "< 5 min"), (5, 15, "5-15 min"), (15, 60, "15-60 min"), (60, 240, "1-4 h"),
         (240, 10**9, "> 4 h")]
TZ_TRY = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC",
          "Europe/London", "Europe/Berlin", "Asia/Singapore", "Australia/Sydney"]
SESSION_SHIFT = pd.Timedelta(hours=6)      # Globex session = ET 18:00 (prior day) -> 17:00
MATCH_TOL = pd.Timedelta(minutes=5)        # random entry / exit: last bar at or before, within 5 min


# ----------------------------------------------------------------- parsing --
def _norm(c):
    return re.sub(r"[^a-z0-9]", "", str(c).lower())


def _find(cols, exact, contains=(), exclude=()):
    """First column whose normalised name equals one of `exact` (in order), else the
    first containing one of `contains` and none of `exclude`."""
    n = {}
    for c in cols:
        n.setdefault(_norm(c), c)
    for x in exact:
        if x in n:
            return n[x]
    for x in contains:
        for k, c in n.items():
            if x in k and not any(e in k for e in exclude):
                return c
    return None


def _num(s):
    """Numbers as Tradovate writes them: '21,345.25', '$(12.50)', ' 3'."""
    s = s.astype(str).str.strip()
    neg = s.str.contains(r"^\(.*\)$|^\$\(.*\)$|^-")
    v = pd.to_numeric(s.str.replace(r"[$,()\s-]", "", regex=True), errors="coerce")
    return v.where(~neg, -v)


def _times(raw, c_ts, c_date):
    ts = raw[c_ts].astype(str).str.strip()
    if c_date and c_date != c_ts and not ts.str.contains(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}").any():
        ts = raw[c_date].astype(str).str.strip() + " " + ts
    t = pd.to_datetime(ts, errors="coerce", format="mixed")
    if t.isna().any():
        raise SystemExit(f"{int(t.isna().sum())} timestamps could not be parsed, e.g. {ts[t.isna()].iloc[0]!r}")
    return t


def _to_et(t, tz):
    if t.dt.tz is None:
        if not tz:
            raise SystemExit("timestamps carry no offset: pass --tz (the Tradovate account's display time zone)")
        t = t.dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
        if t.isna().any():
            raise SystemExit(f"{int(t.isna().sum())} timestamps fall in the repeated DST hour of {tz}")
    return t.dt.tz_convert("America/New_York").dt.tz_localize(None).astype("datetime64[ns]")


def _root(con):
    con = con.astype(str).str.upper().str.strip()
    root = pd.Series(np.where(con.str.startswith("MNQ"), "MNQ", np.where(con.str.startswith("NQ"), "NQ", "")),
                     index=con.index)
    if (root == "").any():
        raise SystemExit(f"only NQ / MNQ supported; found {sorted(set(con[root == '']))[:10]}")
    return con, root


def parse_fills(path, tz, setups=None):
    """Returns (F, P, cols): F one row per fill; P pre-paired round trips (performance
    exports) or None; cols the columns used."""
    raw = pd.read_csv(path, skipinitialspace=True)
    cols = list(raw.columns)
    perf = {k: _find(cols, [k]) for k in ("buyprice", "sellprice", "boughttimestamp", "soldtimestamp")}
    if all(perf.values()):
        return _parse_performance(raw, cols, perf, tz, setups)

    c_ts = _find(cols, ["filltime", "timestamp", "datetime", "time", "exectime"], ["time"], ["format"])
    c_date = _find(cols, ["date", "tradedate"])
    c_side = _find(cols, ["bs", "side", "buysell", "action"], ["side", "action"])
    c_qty = _find(cols, ["filledqty", "fillqty", "qty", "quantity", "size"], ["filledqty", "qty"])
    c_px = _find(cols, ["avgfillprice", "fillprice", "avgprice", "price", "decimalfillavg"],
                 ["fillprice", "price"], ["format", "limit", "stop", "tick"])
    c_con = _find(cols, ["contract", "symbol", "instrument"], ["symbol", "instrument"])
    c_com = _find(cols, ["commission", "commissions", "fees", "fee"], ["commission"])
    c_fid = _find(cols, ["fillid", "id"])
    c_oid = _find(cols, ["orderid"])
    c_acc = _find(cols, ["account", "accountname", "accountid"])
    c_tag = _find(cols, ["setup", "tag", "strategy", "note", "notes", "text"])
    c_st = _find(cols, ["status", "ordstatus"])
    need = {"time": c_ts, "side": c_side, "quantity": c_qty, "price": c_px, "contract": c_con}
    miss = [k for k, v in need.items() if v is None]
    if miss:
        raise SystemExit(f"could not find columns {miss} in {cols}")
    if c_st:
        st = raw[c_st].astype(str).str.lower()
        raw = raw[st.str.contains("fill") & ~st.str.contains("cancel|reject")].copy()
    qty = _num(raw[c_qty]).abs()
    raw = raw[qty.fillna(0) > 0].copy()
    if raw.empty:
        raise SystemExit("no filled rows")
    t_raw = _times(raw, c_ts, c_date)
    side = raw[c_side].astype(str).str.strip().str.upper().str[0].map({"B": 1, "S": -1})
    if side.isna().any():
        raise SystemExit(f"unrecognised side values: {raw[c_side][side.isna()].unique()[:5]}")
    con, root = _root(raw[c_con])
    F = pd.DataFrame({
        "t_raw": t_raw, "side": side.astype(int), "qty": _num(raw[c_qty]).abs().astype(int),
        "price": _num(raw[c_px]).astype(float), "contract": con, "root": root,
        "account": raw[c_acc].astype(str) if c_acc else "account",
        "commission": _num(raw[c_com]).abs() if c_com else np.nan,
        "fill_id": raw[c_fid].astype(str) if c_fid else pd.Series(np.arange(len(raw)), index=raw.index).astype(str),
        "order_id": raw[c_oid].astype(str) if c_oid else "",
        "setup": raw[c_tag].fillna("untagged").astype(str).str.strip().replace("", "untagged")
                 if c_tag else "untagged",
        "row": np.arange(len(raw))})
    F = _apply_setups(F, setups)
    F["t"] = _to_et(F.t_raw, tz)
    key = pd.to_numeric(F.fill_id, errors="coerce")
    F["_k"] = key if key.notna().all() else F.row
    F = F.sort_values(["t", "_k"], kind="stable").drop(columns="_k").reset_index(drop=True)
    return F, None, dict(time=c_ts, date=c_date, side=c_side, qty=c_qty, price=c_px, contract=c_con,
                         commission=c_com, fill_id=c_fid, order_id=c_oid, account=c_acc, setup=c_tag,
                         status=c_st)


def _apply_setups(F, setups):
    if setups is None:
        return F
    m = pd.read_csv(setups, dtype=str)
    d = dict(zip(m.iloc[:, 0].str.strip(), m.iloc[:, 1].str.strip()))
    s = F.fill_id.map(d)
    if "order_id" in F:
        s = s.fillna(F.order_id.map(d))
    F["setup"] = s.fillna(F.setup)
    return F


def _parse_performance(raw, cols, perf, tz, setups):
    c_qty = _find(cols, ["qty", "quantity"], ["qty"])
    c_con = _find(cols, ["symbol", "contract", "instrument"])
    c_pnl = _find(cols, ["pnl", "profitloss", "netpnl"])
    c_bid, c_sid = _find(cols, ["buyfillid"]), _find(cols, ["sellfillid"])
    c_tag = _find(cols, ["setup", "tag", "strategy", "note", "notes", "text"])
    c_acc = _find(cols, ["account", "accountname", "accountid"])
    if not (c_qty and c_con):
        raise SystemExit(f"performance export without qty / symbol columns: {cols}")
    con, root = _root(raw[c_con])
    tb = _to_et(_times(raw, perf["boughttimestamp"], None), tz)
    ts = _to_et(_times(raw, perf["soldtimestamp"], None), tz)
    pb, ps = _num(raw[perf["buyprice"]]).astype(float), _num(raw[perf["sellprice"]]).astype(float)
    q = _num(raw[c_qty]).abs().astype(int)
    long_ = tb <= ts
    bid = raw[c_bid].astype(str) if c_bid else pd.Series([f"b{i}" for i in range(len(raw))], index=raw.index)
    sid = raw[c_sid].astype(str) if c_sid else pd.Series([f"s{i}" for i in range(len(raw))], index=raw.index)
    tag = (raw[c_tag].fillna("untagged").astype(str) if c_tag
           else pd.Series("untagged", index=raw.index))
    acc = raw[c_acc].astype(str) if c_acc else pd.Series("account", index=raw.index)
    P = pd.DataFrame({
        "account": acc, "contract": con, "root": root, "side": np.where(long_, 1, -1), "qty": q,
        "entry": np.where(long_, pb, ps), "exit": np.where(long_, ps, pb),
        "t_in": np.where(long_, tb, ts), "t_out": np.where(long_, ts, tb),
        "setup": tag.values, "comm_in": np.nan, "comm_out": np.nan,
        "id_in": np.where(long_, bid, sid), "id_out": np.where(long_, sid, bid),
        "tradovate_pnl": _num(raw[c_pnl]) if c_pnl else np.nan}).reset_index(drop=True)
    P["t_in"] = pd.to_datetime(P.t_in).astype("datetime64[ns]")
    P["t_out"] = pd.to_datetime(P.t_out).astype("datetime64[ns]")
    if setups is not None:
        m = pd.read_csv(setups, dtype=str)
        d = dict(zip(m.iloc[:, 0].str.strip(), m.iloc[:, 1].str.strip()))
        P["setup"] = P.id_in.map(d).fillna(P.setup)
    P["open"] = False
    F = pd.concat([
        pd.DataFrame({"t": P.t_in, "side": P.side, "qty": P.qty, "price": P.entry, "fill_id": P.id_in}),
        pd.DataFrame({"t": P.t_out, "side": -P.side, "qty": P.qty, "price": P.exit, "fill_id": P.id_out})],
        ignore_index=True)
    F = F.assign(contract=np.tile(P.contract, 2), root=np.tile(P.root, 2), account=np.tile(P.account, 2),
                 setup=np.tile(P.setup, 2), commission=np.nan, order_id="")
    rb, rs = _times(raw, perf["boughttimestamp"], None), _times(raw, perf["soldtimestamp"], None)
    F["t_raw"] = pd.concat([rb.where(long_, rs), rs.where(long_, rb)], ignore_index=True)
    F = F.sort_values("t", kind="stable").reset_index(drop=True)
    return F, P, dict(format="performance", qty=c_qty, contract=c_con, pnl=c_pnl, setup=c_tag, **perf)


# ------------------------------------------------------------ round trips --
def round_trips(F):
    """FIFO per account and contract. One row per matched lot (entry fill -> exit fill);
    lots still open at the end of the file are kept and flagged."""
    out = []
    for (acc, con), g in F.groupby(["account", "contract"], sort=False):
        book = []              # open lots: [side, qty, price, t, setup, commission/unit, fill_id, root]
        for r in g.itertuples():
            q = r.qty
            cpu = (r.commission / r.qty) if np.isfinite(r.commission) and r.qty else np.nan
            while q > 0 and book and book[0][0] == -r.side:
                lot = book[0]
                m = min(q, lot[1])
                out.append(dict(account=acc, contract=con, root=r.root, side=lot[0], qty=m, entry=lot[2],
                                exit=r.price, t_in=lot[3], t_out=r.t, setup=lot[4], comm_in=lot[5],
                                comm_out=cpu, id_in=lot[6], id_out=r.fill_id))
                lot[1] -= m
                q -= m
                if lot[1] == 0:
                    book.pop(0)
            if q > 0:
                book.append([r.side, q, r.price, r.t, r.setup, cpu, r.fill_id, r.root])
        for lot in book:
            out.append(dict(account=acc, contract=con, root=lot[7], side=lot[0], qty=lot[1], entry=lot[2],
                            exit=np.nan, t_in=lot[3], t_out=pd.NaT, setup=lot[4], comm_in=lot[5],
                            comm_out=np.nan, id_in=lot[6], id_out=None))
    T = pd.DataFrame(out)
    T["open"] = T.exit.isna()
    return T.sort_values(["t_in", "t_out"], kind="stable").reset_index(drop=True)


# ------------------------------------------------------------------- bars --
def load_bars(t0, t1):
    """NQ 1-minute bars covering ET times t0..t1 (files are UTC months)."""
    months = pd.period_range((t0 - pd.Timedelta(days=1)).to_period("M"),
                             (t1 + pd.Timedelta(days=1)).to_period("M"), freq="M")
    fs = [BARS / f"NQ_{m.strftime('%Y-%m')}.parquet" for m in months]
    fs = [f for f in fs if f.exists()]
    if not fs:
        return None
    b = pd.concat([pd.read_parquet(f, columns=["ts_et", "session", "instrument_id", "open", "high", "low",
                                               "close"]) for f in fs], ignore_index=True)
    b["ts_et"] = b.ts_et.astype("datetime64[ns]")
    b["session"] = b.session.astype("datetime64[ns]")
    return b.drop_duplicates("ts_et").sort_values("ts_et").set_index("ts_et")


def session_of(t):
    """Globex session date of ET times (18:00 ET starts the next day's session)."""
    return (t + SESSION_SHIFT).dt.normalize()


def _offbar(F, bars, tz_col="t"):
    j = bars.reindex(F[tz_col].dt.floor("min"))
    lo, hi = j.low.to_numpy(), j.high.to_numpy()
    dev = np.maximum(lo - F.price.to_numpy(), F.price.to_numpy() - hi).clip(min=0)
    has = np.isfinite(lo)
    return has, np.where(has, dev / TICK, np.nan)


def match_fills(F, bars):
    if bars is None:
        F["has_bar"], F["off_bar_ticks"], F["bar_ok"] = False, np.nan, np.nan
        return F, None
    j = bars.reindex(F.t.dt.floor("min"))
    F["bar_low"], F["bar_high"], F["bar_close"] = j.low.to_numpy(), j.high.to_numpy(), j.close.to_numpy()
    F["has_bar"], F["off_bar_ticks"] = _offbar(F, bars)
    F["bar_ok"] = np.where(F.has_bar, F.off_bar_ticks <= 2, np.nan)
    return F, tz_diagnostic(F, bars)


def tz_diagnostic(F, bars):
    """If more than 10% of fills lack a bar or sit > 2 ticks outside it, try other zones."""
    in_cov = (F.t >= bars.index[0]) & (F.t <= bars.index[-1])
    if in_cov.sum() == 0 or F.t_raw.dt.tz is not None:
        return None
    bad = (~F.has_bar | (F.off_bar_ticks > 2))[in_cov].mean()
    if bad <= 0.10:
        return None
    rows = []
    for z in TZ_TRY:
        try:
            t = F.t_raw.dt.tz_localize(z, ambiguous="NaT", nonexistent="shift_forward") \
                .dt.tz_convert("America/New_York").dt.tz_localize(None)
        except Exception:                                            # noqa: BLE001
            continue
        G = pd.DataFrame({"t": t, "price": F.price})[in_cov & t.notna()]
        has, off = _offbar(G, bars)
        rows.append((z, float((has & (off <= 2)).mean())))
    rows.sort(key=lambda x: -x[1])
    return dict(bad_share=float(bad), tried=rows)


# ------------------------------------------------------------------ costs --
def add_costs(T):
    mult = T.root.map(lambda r: SPEC[r]["mult"])
    comm = T.root.map(lambda r: SPEC[r]["comm"])
    T["gross_pts"] = T.side * (T.exit - T.entry)
    T["gross_usd"] = T.gross_pts * mult * T.qty
    T["cost_step4"] = (2 * comm + 2 * TICK * mult) * T.qty
    T["cost_actual"] = (T.comm_in.fillna(comm) + T.comm_out.fillna(comm)) * T.qty
    T["net_step4"] = T.gross_usd - T.cost_step4
    T["net_actual"] = T.gross_usd - T.cost_actual
    T["hold_min"] = (T.t_out - T.t_in).dt.total_seconds() / 60.0
    mm = T.t_in.dt.hour * 60 + T.t_in.dt.minute - 570
    T["tod_block"] = [next(lab for lo, hi, lab in BLOCKS if lo <= m < hi) for m in mm]
    T["hold_bin"] = [("open" if not np.isfinite(h) else next(lab for lo, hi, lab in HOLDS if lo <= h < hi))
                     for h in T.hold_min]
    T["weekday"] = T.t_in.dt.day_name()
    T["setup x block"] = T.setup + " | " + T.tod_block
    return T


def excursions(T, bars):
    T["mfe_pts"], T["mae_pts"], T["timing_net_step4"] = np.nan, np.nan, np.nan
    if bars is None:
        return T
    cl = bars.close
    mult = T.root.map(lambda r: SPEC[r]["mult"])
    for i, r in T.iterrows():
        if r.open:
            continue
        seg = bars.loc[r.t_in.floor("min"):r.t_out.floor("min")]
        if seg.empty:
            continue
        hi, lo = seg.high.max(), seg.low.min()
        T.at[i, "mfe_pts"] = (hi - r.entry) if r.side > 0 else (r.entry - lo)
        T.at[i, "mae_pts"] = (r.entry - lo) if r.side > 0 else (hi - r.entry)
        a, b = cl.get(r.t_in.floor("min")), cl.get(r.t_out.floor("min"))
        if a is not None and b is not None:
            T.at[i, "timing_net_step4"] = r.side * (b - a) * mult[i] * r.qty - r.cost_step4
    return T


# -------------------------------------------------------------- baselines --
def _ns(x):
    """datetime64 / timedelta64 values as int64 nanoseconds, whatever their stored unit."""
    a = np.asarray(x)
    return a.astype("timedelta64[ns]" if a.dtype.kind == "m" else "datetime64[ns]").astype("int64")


def random_entry_matrix(C, bars, pool_min):
    """For each closed trade and each candidate session of the pool: the step-4 net P&L
    of the same trade (direction, qty, costs, entry/exit time of day, sessions held)
    placed on that session; NaN where it cannot be placed (no bar within 5 minutes of
    either time, a roll between entry and exit, or the exit beyond the data)."""
    S = pd.DatetimeIndex(np.sort(bars.session.unique()))
    s_in, s_out = session_of(C.t_in), session_of(C.t_out)
    i_in, i_out = S.get_indexer(s_in), S.get_indexer(s_out)
    k = i_out - i_in
    off_in = _ns(C.t_in.dt.floor("min") - (s_in - SESSION_SHIFT))
    off_out = _ns(C.t_out.dt.floor("min") - (s_out - SESSION_SHIFT))
    lo_i, hi_i = i_in[i_in >= 0].min(initial=len(S)), i_in[i_in >= 0].max(initial=-1)
    if hi_i < 0:
        return None, None, 0
    lo_i = min(lo_i, max(0, hi_i + 1 - pool_min))
    pool = np.arange(lo_i, hi_i + 1)
    anchor = _ns(S - SESSION_SHIFT)
    bt = _ns(bars.index)
    bs = S.get_indexer(bars.session)
    bc, bi = bars.close.to_numpy(), bars.instrument_id.to_numpy()
    tol = MATCH_TOL.value

    def lookup(target, sess):
        pos = np.searchsorted(bt, target, side="right") - 1
        ok = (pos >= 0) & (sess < len(S))
        pos = np.clip(pos, 0, len(bt) - 1)
        ok &= (target - bt[pos] <= tol) & (bs[pos] == sess)
        return pos, ok

    n, P = len(C), len(pool)
    j_in = np.broadcast_to(pool[None, :], (n, P))
    j_out = j_in + k[:, None]
    valid_trade = (i_in >= 0) & (i_out >= 0)
    j_out_c = np.clip(j_out, 0, len(S) - 1)
    t_in = anchor[j_in] + off_in[:, None]
    t_out = anchor[j_out_c] + off_out[:, None]
    p_in, ok_in = lookup(t_in, j_in)
    p_out, ok_out = lookup(t_out, np.where(j_out < len(S), j_out, len(S)))
    ok = ok_in & ok_out & (bi[p_in] == bi[p_out]) & (p_out >= p_in) & valid_trade[:, None]
    mult = C.root.map(lambda r: SPEC[r]["mult"]).to_numpy()
    V = (C.side.to_numpy()[:, None] * (bc[p_out] - bc[p_in]) * (mult * C.qty.to_numpy())[:, None]
         - C.cost_step4.to_numpy()[:, None])
    V = np.where(ok, V, np.nan)
    return V, S[pool], P


def _holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (len(p) - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def baselines(T, bars, sims, rng, pool_min, groupings):
    """Returns {null name: dict(n, pool, groups: {grouping: DataFrame})}."""
    C = T[~T.open].reset_index(drop=True)
    res = {}
    draws = {}
    # random entry (exposure matched)
    if bars is not None and len(C):
        V, pool, P = random_entry_matrix(C, bars, pool_min)
        if V is not None:
            cnt = np.isfinite(V).sum(1)
            keep = cnt > 0
            Vs = np.take_along_axis(V, np.argsort(~np.isfinite(V), axis=1, kind="stable"), axis=1)[keep]
            ck = cnt[keep]
            nk = int(keep.sum())

            def gen_re(c):
                u = np.minimum((rng.random((c, nk)) * ck).astype(int), ck - 1)
                return Vs[np.arange(nk)[None, :], u]
            draws["random entry"] = (gen_re, C[keep], dict(pool=f"{len(pool)} sessions "
                                     f"{pool[0].date()} to {pool[-1].date()}" if len(pool) else "none",
                                     excluded=int((~keep).sum()),
                                     median_eligible=float(np.median(ck)) if nk else 0.0))
    # shuffled side
    if len(C) > 1:
        mult = C.root.map(lambda r: SPEC[r]["mult"]).to_numpy()
        mv = ((C.exit - C.entry).to_numpy() * mult * C.qty.to_numpy())
        side, cost = C.side.to_numpy(), C.cost_step4.to_numpy()

        def gen_ss(c):
            return rng.permuted(np.tile(side, (c, 1)), axis=1) * mv - cost
        draws["shuffled side"] = (gen_ss, C, dict(pool="same trades", excluded=0))

    for name, (gen, D, info) in draws.items():
        if len(D) == 0:
            continue
        codes = {g: pd.factorize(D[g]) for g in groupings}
        codes["all"] = (np.zeros(len(D), int), pd.Index(["all trades"]))
        onehot = {}
        for g, (cd, labs) in codes.items():
            onehot[g] = np.zeros((len(D), len(labs)))
            onehot[g][np.arange(len(D)), cd] = 1.0
        acc = {g: [] for g in codes}
        done, chunk = 0, max(1, min(1000, 2_000_000 // max(1, len(D))))
        while done < sims:
            c = min(chunk, sims - done)
            M = gen(c)
            for g in codes:
                acc[g].append(M @ onehot[g])
            done += c
        out = {}
        for g, (cd, labs) in codes.items():
            Z = np.vstack(acc[g])
            act = np.bincount(cd, weights=D.net_step4.to_numpy(), minlength=len(labs))
            ntr = np.bincount(cd, minlength=len(labs))
            p = (1 + (Z >= act[None, :]).sum(0)) / (sims + 1)
            df = pd.DataFrame({"trades": ntr, "your net $": act, "median random $": np.median(Z, 0),
                               "p": p}, index=pd.Index(labs, name=g))
            df["Holm p"] = _holm(p) if len(df) > 1 else p
            out[g] = df.sort_values("trades", ascending=False)
        res[name] = dict(n=len(D), groups=out, **info)
    return res


# ------------------------------------------------------------------ report --
def md_table(df, fmt=None):
    fmt = fmt or {}
    cols = [df.index.name or ""] + list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for idx, r in df.iterrows():
        cells = [str(idx)]
        for c in df.columns:
            v = r[c]
            f = fmt.get(c)
            if f and pd.notna(v):
                cells.append(f.format(v))
            elif isinstance(v, (float, np.floating)):
                cells.append("" if pd.isna(v) else f"{v:,.1f}")
            else:
                cells.append(str(v))
        L.append("| " + " | ".join(cells) + " |")
    return "\n".join(L)


def usd(x, dp=0):
    return "n/a" if not np.isfinite(x) else ("-" if x < 0 else "") + f"${abs(x):,.{dp}f}"


def summary(C):
    x = C.net_step4
    w, l_ = x[x > 0], x[x <= 0]
    daily = C.groupby(session_of(C.t_out)).net_step4.sum()
    eq = x.cumsum()
    dd = float((eq - eq.cummax()).min()) if len(eq) else 0.0
    t = (daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily))) if len(daily) > 1 and daily.std() > 0 \
        else np.nan
    return dict(trades=len(C), sessions=int(daily.size), win=100 * (x > 0).mean() if len(x) else np.nan,
                avg_win=w.mean(), avg_loss=l_.mean(),
                pf=(w.sum() / -l_.sum()) if l_.sum() < 0 else np.inf, exp=x.mean(), dd=dd, t=t)


def table(T, by):
    g = T[~T.open].groupby(by)
    out = pd.DataFrame({"trades": g.size(), "contracts": g.qty.sum(),
                        "win %": g.net_step4.apply(lambda x: 100 * (x > 0).mean()),
                        "net $ step-4": g.net_step4.sum(), "net $ actual": g.net_actual.sum(),
                        "$/trade step-4": g.net_step4.mean(), "median hold min": g.hold_min.median(),
                        "median MFE pt": g.mfe_pts.median(), "median MAE pt": g.mae_pts.median()})
    out.index.name = by
    return out.sort_values("trades", ascending=False)


def report(F, T, cols, base, tzd, P, out_dir, args):
    out_dir.mkdir(parents=True, exist_ok=True)
    C = T[~T.open]
    s = summary(C)
    in_cov = int(F.has_bar.sum())
    L = ["# Your Tradovate trades: harness report", "",
         f"Input `{Path(args.fills).name}`, time zone `{args.tz}`, {args.sims:,} simulations, seed {args.seed}.",
         f"Columns used: {', '.join(f'{k}={v!r}' for k, v in cols.items() if v)}.", "",
         "## Data checks", "",
         f"- fills {len(F)}; round-trip lots {len(C)} closed, {int(T.open.sum())} still open (open lots are "
         "listed in trades_matched.csv and left out of every figure)",
         f"- fills with a 1-minute bar: {in_cov} of {len(F)} (bars run to the last pulled session)",
         f"- fills more than 2 ticks outside their bar: {int((F.bar_ok == 0).sum())} "
         f"(median distance of those: {F.off_bar_ticks[F.bar_ok == 0].median():.0f} ticks)"
         if (F.bar_ok == 0).any() else "- fills more than 2 ticks outside their bar: 0"]
    if tzd:
        L.append(f"- **{100 * tzd['bad_share']:.0f}% of fills do not fit their bar under `{args.tz}`.** "
                 "Share fitting under other zones: " + ", ".join(f"{z} {100 * v:.0f}%" for z, v in tzd["tried"])
                 + ". Re-run with the best zone if it is clearly better.")
    if P is not None and P.tradovate_pnl.notna().any():
        d = (C.gross_usd - P.loc[C.index, "tradovate_pnl"]).abs()
        L.append(f"- Tradovate pnl vs ours (gross): {int((d > 0.01).sum())} of {len(C)} trades differ by more "
                 f"than $0.01 (max ${d.max():,.2f})")
    L += ["", "## Summary (closed trades)", "",
          f"- {s['trades']} trades over {s['sessions']} sessions; win rate {s['win']:.1f}% (step-4 basis)",
          f"- net P&L **{usd(C.net_step4.sum())} on the step-4 cost rule**; {usd(C.net_actual.sum())} with "
          + ("your CSV's commissions" if cols.get("commission") else "step-4 commissions (the CSV has none)")
          + f" and no extra slippage; gross {usd(C.gross_usd.sum())}",
          f"- step-4 costs total {usd(C.cost_step4.sum())} ({usd(C.cost_step4.mean(), 2)} per trade)",
          f"- expectancy {usd(s['exp'], 2)}/trade; average win {usd(s['avg_win'], 2)}, average loss "
          f"{usd(s['avg_loss'], 2)}; profit factor {s['pf']:.2f}; max drawdown {usd(s['dd'])}",
          f"- daily net P&L t = {s['t']:.2f} (one-sided test of the daily mean; descriptive here)"]
    tm = C.timing_net_step4
    if tm.notna().any():
        m = tm.notna()
        L.append(f"- execution: your fills vs the closes of the same minutes' bars, over {int(m.sum())} trades: "
                 f"{usd((C.net_step4[m] - tm[m]).sum())} (positive = your fills beat the bar closes)")
    L += ["", "## Against random entries (step-4 costs)", "",
          f"Your total against {args.sims:,} simulated trade lists. p small = beat the random lists; "
          "p near 1 = did worse.",
          "", "| baseline | trades | trade pool | your net $ | median random $ | p |", "|---|---|---|---|---|---|"]
    for k, r in base.items():
        a = r["groups"]["all"].iloc[0]
        L.append(f"| {k} | {r['n']} | {r['pool']} | {usd(a['your net $'])} | {usd(a['median random $'])} | "
                 f"{a['p']:.4f} |")
    if "random entry" in base and base["random entry"]["excluded"]:
        L.append(f"\n{base['random entry']['excluded']} trades could not be placed on any other session (outside "
                 "the bars) and are left out of the random-entry null only.")
    fmt = {"trades": "{:.0f}", "contracts": "{:.0f}", "p": "{:.4f}", "Holm p": "{:.4f}",
           "your net $": "{:,.0f}", "median random $": "{:,.0f}", "net $ step-4": "{:,.0f}",
           "net $ actual": "{:,.0f}", "$/trade step-4": "{:,.2f}"}
    for title, by in (("By setup", "setup"), ("By time of day (ET, at entry)", "tod_block"),
                      ("By setup and time of day", "setup x block"), ("By hold length", "hold_bin"),
                      ("By weekday", "weekday"), ("By contract", "root")):
        L += ["", f"## {title}", "", md_table(table(T, by), fmt)]
        for k, r in base.items():
            if by in r["groups"]:
                L += ["", f"*{k} null, per group (Holm within this breakdown):*", "",
                      md_table(r["groups"][by], fmt)]
    L += ["", "## Notes", "",
          "- The step-4 rule adds 1 tick per side to fills that already include slippage: it is the stricter "
          "of the two cost views, as used for every system in the programme.",
          "- Random entries are priced at the close of the bar of the entry and exit minute (last bar within 5 "
          "minutes); your trades at your fills. The execution line above measures that difference.",
          "- Per-group p-values are descriptive: many groups are tested. Only the Holm column controls that, "
          "and nothing here is a pre-registered test.",
          "- MFE / MAE use whole 1-minute bars from the entry to the exit minute, so they slightly overstate "
          "both."]
    txt = "\n".join(L)
    (out_dir / "trade_report.md").write_text(txt + "\n")
    T.to_csv(out_dir / "trades_matched.csv", index=False)
    F.to_csv(out_dir / "fills_checked.csv", index=False)
    return txt


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fills")
    ap.add_argument("--tz", default=None, help="time zone of naive timestamps, e.g. America/Chicago")
    ap.add_argument("--setups", default=None)
    ap.add_argument("--sims", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--pool-min", type=int, default=60)
    ap.add_argument("--out", default=str(ROOT / "reports/trades"))
    a = ap.parse_args(argv)
    F, P, cols = parse_fills(a.fills, a.tz, a.setups)
    bars = load_bars(F.t.min() - pd.Timedelta(days=2 * a.pool_min), F.t.max() + pd.Timedelta(days=10))
    F, tzd = match_fills(F, bars)
    T = P.copy() if P is not None else round_trips(F)
    T = excursions(add_costs(T), bars)
    base = baselines(T, bars, a.sims, np.random.default_rng(a.seed), a.pool_min,
                     ["setup", "tod_block", "setup x block", "hold_bin", "weekday", "root"])
    txt = report(F, T, cols, base, tzd, P, Path(a.out), a)
    return F, T, base, tzd, txt


if __name__ == "__main__":
    print(run()[-1])
