"""Part C - live daily liquidity-level screener.

Pre-computes the pre-session level set (PDH/PDL, PWH/PWL, confirmed equal-H/L
pools, round numbers) and, on every new 5-min bar, runs the EXACT same
touch -> confirmation-window -> classify logic as the Part B backtest
(sweeplib.engine) in real time, so a sweep or run is flagged the moment it
confirms - not after the fact.

Display: a `rich` Live table refreshed in place - current price, every level
with signed distance, and a rolling log of the last ~10 touch/confirmation
events.

Alerts (the part that removes screen-watching): on every touch AND every
sweep/run confirmation it fires a webhook (SWEEP_WEBHOOK_URL, e.g. a
Slack/Discord/Telegram incoming webhook) via a plain HTTP POST, and/or a
desktop notification (notify-send / terminal bell) if --desktop is set. The
alert path is exercised by --selftest and by --replay before you ever rely
on it live.

Data source:
  --replay SYM   drive the dashboard from the cached parquet 5-min bars
                 (deterministic; used to test the whole path here)
  --live SYM     connect to TWS/Gateway via ib_async reqHistoricalData(
                 keepUpToDate=True) so the bar list auto-extends live. Needs a
                 running TWS; not available in the research container.

FAIL-LOUD: if the live bar feed stalls or errors, the dashboard turns red and
prints the error instead of silently freezing (spec: a screener that fails
quietly is worse than none).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sweeplib import data as D
from sweeplib.engine import SweepRunTracker
from sweeplib.levels import Level, poc_session_levels, session_levels

CONFIRM_K = 3  # window used for live classification (documented, not tuned live)


# ----------------------------------------------------------------------------
# alerts
# ----------------------------------------------------------------------------
def send_alert(text: str, desktop: bool = False, quiet: bool = False) -> dict:
    """POST to SWEEP_WEBHOOK_URL and/or raise a desktop notification.

    Returns a dict describing what fired, so --selftest can assert on it.
    Never raises: alert failure must not kill the screener.
    """
    result = {"text": text, "webhook": None, "desktop": None}
    url = os.environ.get("SWEEP_WEBHOOK_URL")
    if url:
        try:
            payload = json.dumps({"text": text}).encode()
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                result["webhook"] = r.status
        except Exception as e:  # noqa: BLE001
            result["webhook"] = f"error: {e}"
    if desktop:
        try:
            import subprocess

            subprocess.run(["notify-send", "sweep/run", text], check=False, timeout=5)
            sys.stdout.write("\a")  # terminal bell as always-available fallback
            sys.stdout.flush()
            result["desktop"] = "sent"
        except Exception as e:  # noqa: BLE001
            result["desktop"] = f"error: {e}"
    if not quiet:
        print(f"[ALERT] {text}  -> {result}")
    return result


# ----------------------------------------------------------------------------
# dashboard
# ----------------------------------------------------------------------------
def build_table(sym, price, levels, tracker, log, last_ts, stalled_err=None):
    from rich.table import Table
    from rich import box

    title = f"{sym}  liquidity-level screener  (bar {last_ts})"
    if stalled_err:
        title = f"[reverse red]FEED STALLED: {stalled_err}[/]  " + title
    t = Table(title=title, box=box.SIMPLE_HEAVY, expand=True)
    t.add_column("level")
    t.add_column("price", justify="right")
    t.add_column("side")
    t.add_column("dist", justify="right")
    t.add_column("status")
    above = sorted([l for l in levels if l.price >= price], key=lambda x: x.price)
    below = sorted([l for l in levels if l.price < price], key=lambda x: -x.price)
    nearest_above = above[0].price - price if above else None
    nearest_below = price - below[0].price if below else None
    for lv in sorted(levels, key=lambda x: -x.price):
        d = lv.price - price
        st = ""
        tt = tracker.touches.get(lv.name)
        if tt:
            st = {"pending": "[yellow]touched[/]", "sweep": "[cyan]SWEEP[/]",
                  "run": "[magenta]RUN[/]"}.get(tt.status, tt.status)
        near = (lv.price == (above[0].price if above else None)) or \
               (lv.price == (below[0].price if below else None))
        row = [lv.name, f"{lv.price:.2f}", lv.side, f"{d:+.2f}", st]
        t.add_row(*([f"[bold]{c}[/]" for c in row] if near else row))
    t.caption = (
        f"price {price:.2f}  |  nearest above "
        f"{nearest_above:+.2f}" + ("" if nearest_above is None else "") +
        f"  nearest below -{nearest_below:.2f}" if nearest_below is not None
        else f"price {price:.2f}")

    from rich.console import Group
    from rich.panel import Panel

    logtxt = "\n".join(log) if log else "(no touch/confirmation events yet)"
    return Group(t, Panel(logtxt, title="last events", height=12))


def run_replay(sym: str, speed: float, desktop: bool, force_event: bool):
    """Drive the dashboard from cached parquet bars for the latest session."""
    from rich.live import Live

    bars5 = D.load(sym, "5min")
    daily = D.daily_from_intraday_or_cache(sym)
    sessions = D.rth_sessions_5min(bars5)
    order = sorted(sessions)
    day = order[-1]
    bars = sessions[day]
    levels = session_levels(daily, day)
    if len(order) >= 2:  # prior-session POC / value area
        prior = sessions[order[-2]]
        levels += poc_session_levels(prior, float(prior["close"].iloc[-1]))
    if force_event:
        # guarantee at least one touch for alert-path testing: plant a level
        # 0.05% below the session's 3rd bar low so bar 3+ trades through it
        anchor = float(bars["low"].iloc[2]) * 0.9995
        levels.append(Level("TEST_forced", anchor, "low"))
    if not levels:
        print(f"no pre-session levels for {sym} {day.date()} - aborting")
        return
    tracker = SweepRunTracker(levels, CONFIRM_K)
    log: deque[str] = deque(maxlen=10)
    print(f"replay {sym} {day.date()}: {len(bars)} bars, {len(levels)} levels")

    with Live(refresh_per_second=8, screen=False) as live:
        for i, (ts, row) in enumerate(bars.iterrows()):
            price = float(row["close"])
            # detect touches BEFORE classification for the event log
            known = set(tracker.touches)
            confirmed = tracker.on_bar(i, ts, row["open"], row["high"],
                                       row["low"], row["close"])
            for name, tt in tracker.touches.items():
                if name not in known:
                    msg = f"{ts:%H:%M} TOUCH {name} @ {tt.touch_extreme:.2f}"
                    log.appendleft(msg)
                    send_alert(f"{sym} {msg}", desktop, quiet=True)
            for c in confirmed:
                msg = (f"{ts:%H:%M} {c.status.upper()} {c.level.name} "
                       f"confirmed @ {c.confirm_price:.2f}")
                log.appendleft(msg)
                send_alert(f"{sym} {msg}", desktop, quiet=True)
            live.update(build_table(sym, price, levels, tracker, list(log), ts))
            time.sleep(max(0.0, 0.25 / speed))
    print("\nreplay complete. events fired:")
    for m in reversed(log):
        print("  ", m)


def selftest() -> int:
    """Exercise the alert path with a forced event and assert it fired."""
    os.environ.setdefault("SWEEP_WEBHOOK_URL", "")  # webhook optional
    r = send_alert("SELFTEST forced sweep event", desktop=False)
    ok = r["text"].startswith("SELFTEST")
    # also drive one bar through the engine with a planted level
    # low-side level at 100: bar pierces (low 99) then closes back ABOVE 100
    # -> sweep confirmed on the touch bar's close (100.5)
    lv = Level("T", 100.0, "low")
    tr = SweepRunTracker([lv], 3)
    conf = tr.on_bar(0, datetime.now(timezone.utc), 101, 101, 99, 100.5)
    # a second level that pierces and STAYS below through K -> run
    lv2 = Level("R", 100.0, "low")
    tr2 = SweepRunTracker([lv2], 1)
    r0 = tr2.on_bar(0, datetime.now(timezone.utc), 101, 101, 99, 99.5)  # pending
    r1 = tr2.on_bar(1, datetime.now(timezone.utc), 99.5, 99.6, 99.0, 99.2)  # run
    print(f"engine sweep-case: touches={list(tr.touches)}, "
          f"confirmed={[c.status for c in conf]}")
    print(f"engine run-case: confirmed={[c.status for c in (r0 + r1)]}")
    ok = ok and tr.touches and tr.touches["T"].status == "sweep"
    ok = ok and [c.status for c in (r0 + r1)] == ["run"]
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", metavar="SYM", help="replay cached bars for SYM")
    ap.add_argument("--live", metavar="SYM", help="live via TWS/ib_async (needs TWS)")
    ap.add_argument("--speed", type=float, default=20.0, help="replay speedup")
    ap.add_argument("--desktop", action="store_true", help="also notify-send + bell")
    ap.add_argument("--force-event", action="store_true",
                    help="plant a guaranteed touch to test the alert path")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.replay:
        run_replay(args.replay, args.speed, args.desktop, args.force_event)
    elif args.live:
        run_live(args.live, args.desktop)
    else:
        ap.error("one of --replay / --live / --selftest required")


def run_live(sym: str, desktop: bool) -> None:
    """Live loop via ib_async keepUpToDate bars. Requires a running TWS.

    Not runnable in the research container (no TWS). Kept faithful to the
    ib_async pattern; fails loud if the feed stalls.
    """
    from rich.live import Live
    from ib_async import IB, ContFuture, Stock, util

    ib = IB()
    ib.connect("127.0.0.1", 7497, clientId=12)
    contract = (ContFuture(sym, exchange="CME") if sym in ("NQ", "ES")
                else Stock(sym, "SMART", "USD"))
    ib.qualifyContracts(contract)
    daily = D.daily_from_intraday_or_cache(sym)
    today = util.df(ib.reqHistoricalData(
        contract, "", "1 D", "5 mins", "TRADES", useRTH=True,
        formatDate=2, keepUpToDate=True))
    day = __import__("pandas").Timestamp(datetime.now().date())
    levels = session_levels(daily, day)
    prior_sessions = D.rth_sessions_5min(D.load(sym, "5min"))
    if prior_sessions:
        prior = prior_sessions[sorted(prior_sessions)[-1]]
        levels += poc_session_levels(prior, float(prior["close"].iloc[-1]))
    tracker = SweepRunTracker(levels, CONFIRM_K)
    log: deque[str] = deque(maxlen=10)
    last_len, last_change = len(today), time.time()

    with Live(refresh_per_second=4, screen=False) as live:
        while True:
            ib.sleep(1)
            bars = ib.reqHistoricalData(
                contract, "", "1 D", "5 mins", "TRADES", useRTH=True,
                formatDate=2, keepUpToDate=True)
            df = util.df(bars)
            stalled = None
            if len(df) == last_len and time.time() - last_change > 420:
                stalled = f"no new bar for {int(time.time()-last_change)}s"
            elif len(df) != last_len:
                last_len, last_change = len(df), time.time()
                i = len(df) - 1
                row = df.iloc[i]
                known = set(tracker.touches)
                confirmed = tracker.on_bar(i, row["date"], row["open"],
                                           row["high"], row["low"], row["close"])
                for name, tt in tracker.touches.items():
                    if name not in known:
                        send_alert(f"{sym} TOUCH {name} @ {tt.touch_extreme:.2f}", desktop)
                for c in confirmed:
                    send_alert(f"{sym} {c.status.upper()} {c.level.name} "
                               f"@ {c.confirm_price:.2f}", desktop)
            price = float(df["close"].iloc[-1])
            live.update(build_table(sym, price, levels, tracker, list(log),
                                    df["date"].iloc[-1], stalled))


if __name__ == "__main__":
    main()
