#!/usr/bin/env python3
"""FOMC event-vol straddle.

Pre-registered at `a971882`, amended at `b7becac` (announcement-relative entry,
dated provenance) and `648b45d` (provenance settled, quarterly promotion gate,
influence diagnostics). Written after all three were committed.

The trade, one grid point: QQQ ATM straddle on the Friday expiry of the
announcement week, bought at the close of the session before the announcement
and sold at the close of the announcement session. It spans the 14:00 ET
statement and the IV crush that follows.

This is the first test in the project that does not divide session magnitude
out. Everything before it was a directional barrier trade on a normalised R
scale, and the ledger says the ratio of net displacement to path length does not
condition on anything observable in advance.

What is deliberately NOT tested here: RV/IV. Realised variance is path length;
an unhedged straddle pays net displacement. The wedge between them is the
efficiency ratio, and a retail desk cannot hedge it inside the cost gate. RV/IV
is carried as a diagnostic and touches no decision.

Modes:
  dates    emit the unique chain dates to pull, and the event manifest
  harvest  fold spilled MCP payloads into a compact quote store
  run      compute the result

Chains are pulled with return_full_data=true and no expiration filter, which
puts ~1.0MB on disk per date at ~300 tokens instead of ~12k inline.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ROOT / "data/intraday_long/QQQ_5m.parquet"
FOMC_CSV = ROOT / "data/events/fomc.csv"
OUT = ROOT / "data/events"
RESULTS = Path(
    "/root/.claude/projects/-home-user-Claude-1/"
    "53a4adb9-543d-5460-95dd-0cda0b53172f/tool-results"
)
PREFIX = "mcp-Alpha_Vantage_MCP_Server-HISTORICAL_OPTIONS-"

# Frozen at amendment 1 §B. 2020-03-18 is absent by declaration: the scheduled
# 17-18 March meeting was cancelled and the action was the emergency Sunday cut
# of 15 March, announced outside market hours.
OOS_EVENTS = {
    2016: "01-27 03-16 04-27 06-15 07-27 09-21 11-02 12-14",
    2017: "02-01 03-15 05-03 06-14 07-26 09-20 11-01 12-13",
    2018: "01-31 03-21 05-02 06-13 08-01 09-26 11-08 12-19",
    2019: "01-30 03-20 05-01 06-19 07-31 09-18 10-30 12-11",
    2020: "01-29 04-29 06-10 07-29 09-16 11-05 12-16",
}

DISCOVERY = ("2021-01-01", "2026-08-31")
COMM_PER_LEG = 0.65 / 100.0          # $0.65 a contract, expressed per share
COMM = 4 * COMM_PER_LEG              # two legs in, two legs out
COST_FRAC_MAX = 0.10                 # cost above 10% of premium rejects the event
SIGMA_ASSUMED = 0.45                 # of premium; realised sigma comes from placebos


# ---------------------------------------------------------------- calendar

def sessions() -> pd.DataFrame:
    """Trading dates and their closing prices, 2016-2026.

    Five-minute bars, not one-minute, deliberately: the same grid serves both
    blocks, so strike selection is homogeneous and the diagnostic RV is
    computed the same way on either side of 2021.
    """
    d = pd.read_parquet(SESSIONS, columns=["timestamp", "close"])
    t = pd.to_datetime(d["timestamp"])
    d = d.assign(date=t.dt.normalize())
    close = d.groupby("date")["close"].last()
    return close


def third_friday(ts: pd.Timestamp) -> pd.Timestamp:
    first = pd.Timestamp(ts.year, ts.month, 1)
    return first + pd.Timedelta(days=(4 - first.dayofweek) % 7) + pd.Timedelta(days=14)


def standard_expiry(ts: pd.Timestamp, sess: pd.Index):
    """The month's standard expiry: third Friday, or the session before it.

    When the third Friday is an exchange holiday the monthly and quarterly
    contracts expire on the preceding Thursday. June 2026 is the case in this
    sample -- Juneteenth falls on Friday the 19th -- and calling that Thursday a
    weekly would misclassify a quarterly as a weekly and understate the
    quarterly split the promotion gate is defined on.
    """
    tf = third_friday(ts)
    if tf in sess:
        return tf
    prior = sess[sess < tf]
    return prior[-1] if len(prior) else None


def week_expiry(day: pd.Timestamp, sess: pd.Index):
    """Friday of the announcement week, or Thursday if that Friday is a holiday.

    Declared in the pre-registration §9. Returns None when neither exists, and
    the caller records the exclusion rather than dropping it silently.
    """
    fri = day + pd.Timedelta(days=(4 - day.dayofweek))
    if fri in sess:
        return fri
    thu = fri - pd.Timedelta(days=1)
    return thu if thu in sess else None


def events() -> pd.DataFrame:
    """Every event and placebo, with its entry day, exit day and expiry.

    Entry and exit are announcement-relative, never weekday-hardcoded. Three of
    the 84 events are Thursdays because the November meeting shifts in election
    and midterm weeks, and the repo already said so at `a306378` before the
    pre-registration contradicted it.
    """
    close = sessions()
    sess = close.index
    fomc = pd.read_csv(FOMC_CSV)
    disc = [
        pd.Timestamp(x) for x in fomc["date"]
        if DISCOVERY[0] <= x <= DISCOVERY[1]
    ]
    oos = [
        pd.Timestamp(f"{y}-{d}")
        for y, ds in OOS_EVENTS.items() for d in ds.split()
    ]
    all_fomc = set(disc) | set(oos)

    rows, skipped = [], []
    for block, evs in (("discovery", disc), ("oos", oos)):
        for a in evs:
            # the event, then its two matched placebos at the same weekday
            for kind, day in (
                ("event", a), ("placebo", a - pd.Timedelta(days=7)),
                ("placebo", a + pd.Timedelta(days=7)),
            ):
                if day not in sess:
                    skipped.append((block, kind, str(day.date()), "not a session"))
                    continue
                if kind == "placebo" and day in all_fomc:
                    skipped.append((block, kind, str(day.date()), "is an FOMC date"))
                    continue
                prior = sess[sess < day]
                if not len(prior):
                    skipped.append((block, kind, str(day.date()), "no prior session"))
                    continue
                exp = week_expiry(day, sess)
                if exp is None:
                    skipped.append((block, kind, str(day.date()), "no week expiry"))
                    continue
                std = standard_expiry(exp, sess)
                rows.append(dict(
                    block=block, kind=kind, anchor=a, day=day,
                    entry=prior[-1], exit=day, expiry=exp,
                    weekday=day.day_name(),
                    quarterly=bool(exp == std and exp.month in (3, 6, 9, 12)),
                    std_expiry=bool(exp == std),
                    exit_dte=int((exp - day).days),
                ))
    E = pd.DataFrame(rows)
    if skipped:
        print("EXCLUSIONS (recorded, not silent):")
        for s in skipped:
            print("   ", *s)
    return E


# ---------------------------------------------------------------- harvest

def payloads():
    """Every options chain sitting in the MCP tool-results directory."""
    for f in sorted(RESULTS.glob(PREFIX + "*.txt")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        body = j.get("result")
        if not body or j.get("preview"):      # previews are truncated; skip them
            continue
        try:
            df = pd.read_csv(io.StringIO(body))
        except Exception:
            continue
        if {"expiration", "strike", "type", "bid", "ask", "mark", "date"} <= set(df.columns):
            yield df


def harvest(E: pd.DataFrame) -> pd.DataFrame:
    """Keep only quotes near the money for the expiries the design asks for."""
    want = set()
    for _, r in E.iterrows():
        want.add((str(r["entry"].date()), str(r["expiry"].date())))
        want.add((str(r["exit"].date()), str(r["expiry"].date())))

    close = sessions()
    keep = []
    for df in payloads():
        d = str(df["date"].iloc[0])
        spot = close.get(pd.Timestamp(d))
        if spot is None or pd.isna(spot):
            continue
        for exp in df["expiration"].unique():
            if (d, str(exp)) not in want:
                continue
            sub = df[(df["expiration"] == exp)
                     & (df["strike"] - spot).abs().le(0.05 * spot)]
            keep.append(sub[["date", "expiration", "strike", "type", "bid", "ask",
                             "mark", "implied_volatility", "delta", "open_interest"]])
    if not keep:
        return pd.DataFrame()
    Q = pd.concat(keep, ignore_index=True).drop_duplicates(
        subset=["date", "expiration", "strike", "type"])
    print(f"harvested {len(Q)} quotes | "
          f"{Q.groupby(['date','expiration']).ngroups} of {len(want)} date-expiry pairs")
    return Q


# ---------------------------------------------------------------- pricing

def straddle(Q: pd.DataFrame, date, expiry, strike):
    """The two legs at one strike, or None if either is missing."""
    s = Q[(Q["date"] == str(date.date())) & (Q["expiration"] == str(expiry.date()))
          & (Q["strike"] == strike)]
    c, p = s[s["type"] == "call"], s[s["type"] == "put"]
    if len(c) != 1 or len(p) != 1:
        return None
    c, p = c.iloc[0], p.iloc[0]
    return dict(
        mid=float(c["mark"] + p["mark"]),
        ask=float(c["ask"] + p["ask"]),
        bid=float(c["bid"] + p["bid"]),
        iv=float((c["implied_volatility"] + p["implied_volatility"]) / 2),
        net_delta=float(c["delta"] + p["delta"]),
    )


def price(E: pd.DataFrame, Q: pd.DataFrame) -> pd.DataFrame:
    """Per-event P&L as a fraction of entry premium.

    r_exec crosses the spread adversely on both sides and is the headline.
    r_mid uses marks and is reported beside it, so it is visible whether the
    spread assumption is doing the work.
    """
    close = sessions()
    out, missing = [], []
    for _, r in E.iterrows():
        spot = close.get(r["entry"])
        if spot is None or pd.isna(spot):
            missing.append((str(r["entry"].date()), "no entry close"))
            continue
        avail = Q[(Q["date"] == str(r["entry"].date()))
                  & (Q["expiration"] == str(r["expiry"].date()))]
        if avail.empty:
            missing.append((str(r["entry"].date()), "no entry chain"))
            continue
        # single strike nearest the entry close; ties to the higher strike
        ks = np.sort(avail["strike"].unique())
        k = float(ks[np.lexsort((-ks, np.abs(ks - spot)))][0])

        en = straddle(Q, r["entry"], r["expiry"], k)
        ex = straddle(Q, r["exit"], r["expiry"], k)
        if en is None or ex is None:
            missing.append((str(r["entry"].date()), "leg missing at entry or exit"))
            continue

        cost = (en["ask"] - en["mid"]) + (ex["mid"] - ex["bid"]) + COMM
        out.append(dict(
            block=r["block"], kind=r["kind"], anchor=r["anchor"], day=r["day"],
            weekday=r["weekday"], quarterly=r["quarterly"], exit_dte=r["exit_dte"],
            strike=k, spot=spot, entry_mid=en["mid"], exit_mid=ex["mid"],
            entry_iv=en["iv"], exit_iv=ex["iv"], net_delta=en["net_delta"],
            prem_pct=100 * en["mid"] / spot,
            cost_frac=cost / en["mid"],
            r_mid=(ex["mid"] - en["mid"] - COMM) / en["mid"],
            r_exec=(ex["bid"] - en["ask"] - COMM) / en["mid"],
        ))
    if missing:
        print(f"UNPRICED: {len(missing)} (recorded)")
        for m in missing[:12]:
            print("   ", *m)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- reporting

def concentration(x: np.ndarray, n_drop: int) -> float:
    """Mean after removing the n_drop most extreme contributors at each tail."""
    if len(x) <= 2 * n_drop:
        return float("nan")
    s = np.sort(x)
    return float(s[n_drop:len(s) - n_drop].mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dates", "harvest", "run"])
    a = ap.parse_args()

    E = events()
    ev = E[E["kind"] == "event"]
    print(f"\nevents {len(ev)} (discovery {sum(ev.block=='discovery')}, "
          f"oos {sum(ev.block=='oos')}) | placebos {sum(E.kind=='placebo')}")
    print(f"quarterly {int(ev.quarterly.sum())} of {len(ev)} | "
          f"Thursday {int((ev.weekday=='Thursday').sum())}")

    if a.mode == "dates":
        # Emitted per block, and the OOS list is not to be pulled until the
        # discovery result is committed. Two-stage means two stages.
        E.to_parquet(OUT / "fomc_straddle_manifest.parquet")
        for block in ("discovery", "oos"):
            B = E[E["block"] == block]
            need = sorted({str(d.date()) for d in
                           pd.concat([B["entry"], B["exit"]]).unique()})
            p = OUT / f"fomc_straddle_chain_dates_{block}.txt"
            p.write_text("\n".join(need) + "\n")
            print(f"\n{block:9s} {len(need):3d} unique chain dates -> {p.name}")
        return 0

    Q = harvest(E)
    if Q.empty:
        print("\nno chains harvested yet; pull them first")
        return 1
    Q.to_parquet(OUT / "fomc_straddle_quotes.parquet")

    if a.mode == "harvest":
        return 0

    R = price(E, Q)
    if R.empty:
        print("\nnothing priced")
        return 1

    # the cost gate binds before any performance is read
    gated = R[R["cost_frac"] > COST_FRAC_MAX]
    print(f"\nCOST GATE: {len(gated)} of {len(R)} rejected above "
          f"{COST_FRAC_MAX:.0%} of premium")
    R = R[R["cost_frac"] <= COST_FRAC_MAX]

    print("\nCOUNTS BEFORE PERFORMANCE")
    for (b, k), g in R.groupby(["block", "kind"]):
        print(f"  {b:9s} {k:8s} n={len(g):3d}  premium {g.prem_pct.mean():.2f}% of spot"
              f"  cost {100*g.cost_frac.mean():.2f}% of premium"
              f"  |net delta| {g.net_delta.abs().mean():.3f}")

    R.to_parquet(OUT / "fomc_straddle_events.parquet")
    print("\nper-event rows written; see reports/ for the result document")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
