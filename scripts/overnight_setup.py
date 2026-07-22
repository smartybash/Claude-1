"""Fixed daily failed-auction read: PREVIOUS completed session + CURRENT
overnight/premarket. Same recipe every run - the windows are derived
mechanically from the latest bar's clock, never hand-chosen, so the output
cannot be cherry-picked to whatever looks good.

Recipe (identical every time):
  * current session date  = date of the session the latest bar belongs to
    (pre-open bars belong to today's session; post-16:00 bars belong to the
    NEXT session that is now building overnight).
  * previous session      = the most recent COMPLETED RTH session before it.
  * overnight VP window    = (day before current session) 18:00 ET -> current
    session 09:30 ET, truncated at 'now' if still pre-open. VAH/POC/VAL come
    from this window (the strategy's overnight profile).
  * prior-day levels       = previous RTH session high / low / close (PDH/PDL).
  * chart span             = previous session 09:30 -> now (prev day + today).
  * failed-auction read    = touch VAH/VAL -> close back inside within K bars
    (the reclaim; absorption/order-flow is the trader's discretionary add-on).
  * R:R                    = to POC and to the opposite value-area edge, for a
    STRUCTURAL stop (beyond overnight extreme) and a TIGHT stop (fixed buffer,
    ~the 1-min entry) so the timeframe/stop tradeoff is explicit.

Usage:  python scripts/overnight_setup.py --symbol NQ
Reads data/{sym}_5min_eth_live.json (refresh it first with a live fetch).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import volume_profile

ET = ZoneInfo("America/New_York")
RTH_OPEN, RTH_CLOSE = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()
K = 3                      # confirmation window (bars) - fixed, not tuned live
TIGHT_BUFFER_FRAC = 0.0015  # ~tight 1-min stop, as a fraction of price
ON_EXPECTED_BARS = 186      # full 18:00->09:30 at 5-min, for "% formed"


def load(sym: str) -> pd.DataFrame:
    p = ROOT / "data" / f"{sym.lower()}_5min_eth_live.json"
    r = json.loads(p.read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def rth_dates(df: pd.DataFrame) -> list[pd.Timestamp]:
    t = df.index.time
    rth = df[(t >= RTH_OPEN) & (t < RTH_CLOSE)]
    return sorted({pd.Timestamp(d, tz=ET) for d, g in rth.groupby(rth.index.date) if len(g) >= 20})


def windows(df: pd.DataFrame):
    """Mechanically derive current & previous session and the overnight window."""
    now = df.index[-1]
    dates = rth_dates(df)
    if now.time() >= RTH_CLOSE:                       # session done -> next builds
        cur = (now + pd.Timedelta(days=1)).normalize()
    else:
        cur = now.normalize()
    prev = max([d for d in dates if d < cur], default=None)
    on_start = (cur - pd.Timedelta(days=1)).replace(hour=18, minute=0)
    on_end = min(now, cur.replace(hour=9, minute=30))
    return now, cur, prev, on_start, on_end


def reclaim(bars: pd.DataFrame, level: float, side: str):
    """First VAH/VAL touch that closes back inside within K bars = failed auction."""
    b = bars.reset_index(names="ts")
    for i in range(len(b)):
        pierced = b["high"][i] > level if side == "high" else b["low"][i] < level
        if pierced:
            ext = b["high"][i] if side == "high" else b["low"][i]
            for j in range(i, min(i + K + 1, len(b))):
                inside = b["close"][j] < level if side == "high" else b["close"][j] > level
                if inside:
                    return dict(poke_t=b["ts"][i], ext=ext, conf_t=b["ts"][j],
                                entry=float(b["close"][j]), status="reclaim")
            return dict(poke_t=b["ts"][i], ext=ext, status="acceptance")
    return None


def rr(entry, stop, t1, t2):
    risk = abs(entry - stop)
    return (abs(entry - t1) / risk if risk else np.nan,
            abs(entry - t2) / risk if risk else np.nan, risk)


def run(sym: str) -> None:
    df = load(sym)
    now, cur, prev, on_start, on_end = windows(df)
    on = df[(df.index >= on_start) & (df.index < on_end)]
    if len(on) < 10:
        print(f"{sym}: overnight window too thin ({len(on)} bars) - cannot read"); return
    poc, vah, val = volume_profile(on, 50)
    on_hi, on_lo = on["high"].max(), on["low"].min()
    formed = min(100, len(on) / ON_EXPECTED_BARS * 100)
    final = formed >= 95
    cur_px = float(df["close"].iloc[-1])

    # previous completed RTH session (context / prior-day levels)
    prth = df[(df.index >= prev.replace(hour=9, minute=30)) &
              (df.index < prev.replace(hour=16, minute=0))]
    pdh, pdl, pdc = prth["high"].max(), prth["low"].min(), prth["close"].iloc[-1]

    # phase
    if now.time() < RTH_OPEN and now.normalize() == cur:
        mins = (cur.replace(hour=9, minute=30) - now).total_seconds() / 60
        phase = f"PRE-OPEN ({mins:.0f} min to open)"
    elif now.time() < RTH_CLOSE and now.normalize() == cur:
        phase = "RTH IN PROGRESS"
    else:
        phase = "POST-CLOSE (overnight building)"

    print(f"=== {sym} failed-auction read  |  as of {now:%a %Y-%m-%d %H:%M} ET  [{phase}] ===")
    print(f"prev session {prev.date()}: H {pdh:.0f}  L {pdl:.0f}  C {pdc:.0f}")
    print(f"overnight VP ({cur.date()}, {len(on)} bars, {formed:.0f}% formed{' FINAL' if final else ' DEVELOPING'}):")
    print(f"  ON Hi {on_hi:.0f} | VAH {vah:.0f} | POC {poc:.0f} | VAL {val:.0f} | ON Lo {on_lo:.0f} | VA {vah-val:.0f}pts")
    loc = "ABOVE VAH" if cur_px > vah else "BELOW VAL" if cur_px < val else "INSIDE value"
    print(f"now {cur_px:.0f} [{loc}]  toVAH {vah-cur_px:+.0f} toPOC {poc-cur_px:+.0f} toVAL {val-cur_px:+.0f}")

    # failed-auction read at both edges (RTH only)
    rth = df[(df.index >= cur.replace(hour=9, minute=30)) & (df.index <= now) &
             (df.index.normalize() == cur)]
    reads = {}
    if len(rth):
        reads["short"] = reclaim(rth, vah, "high")
        reads["long"] = reclaim(rth, val, "low")

    # R:R geometry. If a setup has actually TRIGGERED, use the real reclaim
    # entry and real poke extreme (a reclaim close often sits well inside the
    # level, so POC can already be behind you); else show the idealized plan.
    va = vah - val

    def rr_block(side):
        r = reads.get(side)
        edge = vah if side == "short" else val
        sign = -1 if side == "short" else 1     # profit direction
        triggered = bool(r and r.get("status") == "reclaim")
        if triggered:
            entry = r["entry"]
            struct_stop = r["ext"] + (5 if side == "short" else -5)
            tight_stop = entry * (1 + sign * -TIGHT_BUFFER_FRAC)
            header = f"  {side.upper()} TRIGGERED - actual entry {entry:.0f} (reclaim), stop beyond poke {r['ext']:.0f}"
        else:
            entry = edge
            struct_stop = on_hi + 5 if side == "short" else on_lo - 5
            tight_stop = edge * (1 + sign * -TIGHT_BUFFER_FRAC)
            header = f"  {side.upper()} plan - entry at {'VAH' if side=='short' else 'VAL'} {edge:.0f}"
        cands = [("POC", poc), ("VAL" if side == "short" else "VAH", val if side == "short" else vah)]
        valid = [(n, p) for n, p in cands if sign * (p - entry) > 0]  # targets still ahead
        if not valid:
            return header + "\n     (no value-area target left in the trade's direction)"
        out = [header]
        for stop, lab in [(struct_stop, "structural"), (tight_stop, "tight ~1-min")]:
            risk = abs(entry - stop)
            rrs = " ".join(f"{n} {abs(entry-p)/risk:.1f}R" for n, p in valid) if risk else "n/a"
            out.append(f"     {lab} stop {stop:.0f} (risk {risk:.0f}pt): {rrs}")
        if not triggered:
            flags = []
            if abs(entry - (on_hi if side == "short" else on_lo)) < 0.03 * va:
                flags.append("structural stop degenerate (overnight extreme hugs the edge)")
            if abs(entry - valid[0][1]) < 0.15 * va:
                flags.append("nearest target trivial -> use the far one")
            out.append("     -> " + ("AWKWARD: " + "; ".join(flags) if flags else "clean geometry"))
        return "\n".join(out)
    if len(rth):
        print(f"RTH so far ({rth.index.min():%H:%M}->{rth.index.max():%H:%M}): "
              f"O {rth['open'].iloc[0]:.0f} H {rth['high'].max():.0f} L {rth['low'].min():.0f} last {cur_px:.0f}")
        for name, side, lvl in [("VAH short", "short", vah), ("VAL long", "long", val)]:
            r = reads.get(side)
            if not r:
                print(f"  {name}: no touch of {lvl:.0f} yet")
            elif r["status"] == "acceptance":
                print(f"  {name}: poked {r['ext']:.0f} at {r['poke_t']:%H:%M} but NO reclaim = acceptance (no fade)")
            else:
                print(f"  {name}: TRIGGERED - poke {r['ext']:.0f}, reclaim {r['conf_t']:%H:%M} entry {r['entry']:.0f}")
    print("R:R geometry:")
    print(rr_block("short"))
    print(rr_block("long"))

    _chart(sym, df, now, cur, prev, on_start, on, poc, vah, val, on_hi, on_lo,
           pdh, pdl, cur_px, formed, final, phase, reads)


def _chart(sym, df, now, cur, prev, on_start, on, poc, vah, val, on_hi, on_lo,
           pdh, pdl, cur_px, formed, final, phase, reads):
    plot = df[df.index >= prev.replace(hour=9, minute=30)]
    fig, (axp, axv) = plt.subplots(1, 2, figsize=(16, 8),
                                   gridspec_kw={"width_ratios": [4.5, 1]}, sharey=True)
    for i, (ts, r) in enumerate(plot.iterrows()):
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        axp.plot([i, i], [r["low"], r["high"]], color=c, lw=0.55, zorder=2)
        axp.add_patch(Rectangle((i-0.32, min(r["open"], r["close"])), 0.64,
                                abs(r["close"]-r["open"])+0.2, facecolor=c, edgecolor=c, zorder=3))
    axp.axhspan(val, vah, color="#90caf9", alpha=0.12, zorder=0)
    for lv, lab, col in [(vah, "VAH %.0f" % vah, "#c62828"), (poc, "POC %.0f" % poc, "#6a1b9a"),
                         (val, "VAL %.0f" % val, "#2e7d32")]:
        axp.axhline(lv, color=col, lw=1.5, zorder=4)
        axp.text(len(plot)+0.5, lv, lab, color=col, va="center", fontsize=10, fontweight="bold")
    for lv, lab, col in [(pdh, "PDH %.0f" % pdh, "#795548"), (pdl, "PDL %.0f" % pdl, "#795548"),
                         (on_hi, "ONHi %.0f" % on_hi, "#9e9e9e"), (on_lo, "ONLo %.0f" % on_lo, "#9e9e9e")]:
        axp.axhline(lv, color=col, lw=0.8, ls="--", zorder=1)
        axp.text(len(plot)+0.5, lv, lab, color=col, va="center", fontsize=7.5)
    # session dividers
    for d, lab in [(prev.replace(hour=16), "prev close"), (on_start, "18:00"),
                   (cur.replace(hour=9, minute=30), "%s open" % cur.strftime("%a"))]:
        idx = plot.index.searchsorted(d)
        if 0 < idx < len(plot):
            axp.axvline(idx-0.5, color="#455a64", lw=1, ls=":", zorder=1)
            axp.text(idx-0.5, plot["high"].max(), " "+lab, color="#455a64", fontsize=7.5, va="top")
    axp.scatter([len(plot)-1], [cur_px], marker="o", s=75, color="#1565c0", zorder=6)
    axp.text(len(plot)+0.5, cur_px, "NOW %.0f" % cur_px, color="#1565c0", va="center",
             fontsize=9, fontweight="bold")
    ftag = "FINAL" if final else "DEVELOPING %.0f%%" % formed
    axp.set_title(f"{sym} failed-auction read — prev session {prev.strftime('%a %m-%d')} + "
                  f"{cur.strftime('%a %m-%d')} overnight/premarket\n"
                  f"as of {now:%a %H:%M} ET [{phase}] — overnight VP {ftag}; PDH/PDL dashed",
                  fontsize=10.5)
    tk = list(range(0, len(plot), 18))
    axp.set_xticks(tk); axp.set_xticklabels([plot.index[i].strftime("%a %H:%M") for i in tk],
                                            rotation=45, fontsize=7.5)
    axp.set_ylabel(sym); axp.set_xlim(-2, len(plot)+16); axp.grid(alpha=0.15)
    # VP side panel
    lo, hi = on["low"].min(), on["high"].max()
    edges = np.linspace(lo, hi, 51); centers = (edges[:-1]+edges[1:])/2; vol = np.zeros(50)
    for low, high, v in zip(on["low"], on["high"], on["volume"]):
        a = max(0, int(np.searchsorted(edges, low, "right"))-1)
        b = min(49, int(np.searchsorted(edges, high, "right"))-1); vol[a:b+1] += v/(b-a+1)
    cols = ["#90caf9" if val <= c <= vah else "#cfd8dc" for c in centers]
    axv.barh(centers, vol, height=(hi-lo)/50, color=cols)
    axv.axhline(poc, color="#6a1b9a", lw=1.4); axv.axhline(cur_px, color="#1565c0", lw=1, ls=(0, (1, 1)))
    axv.set_title("overnight\nvol by price", fontsize=9); axv.set_xticks([])
    plt.tight_layout()
    out = ROOT / "reports" / "img" / f"{sym.lower()}_setup_latest.png"
    plt.savefig(out, dpi=108, bbox_inches="tight")
    print(f"chart -> {out}")


def watch(sym: str, near: float = 30.0) -> None:
    """Lightweight edge-watcher status for the scheduled loop.

    Prints ONE machine-readable STATUS line the agent acts on each wake:
      STATUS=ALERT   a reclaim confirmed on the latest bar AT/NEAR an edge -> tell the user
      STATUS=ARMED   price within `near` pts of VAH/VAL -> watch closely (check again in 5 min)
      STATUS=QUIET   mid-value, no edge in play (check again in 15 min)
      STATUS=PREOPEN / CLOSED  outside RTH
    'Fresh' = the reclaim's confirming bar is the latest (or 1 before) bar, so
    each real trigger is shouted once, not re-shouted every wake.
    """
    df = load(sym)
    now, cur, prev, on_start, on_end = windows(df)
    on = df[(df.index >= on_start) & (df.index < on_end)]
    if len(on) < 10:
        print("STATUS=CLOSED reason=thin-overnight"); return
    poc, vah, val = volume_profile(on, 50)
    cur_px, now_t = float(df["close"].iloc[-1]), df.index[-1]
    tnow = now_t.time()
    if tnow < RTH_OPEN and now_t.normalize() == cur:
        mins = (cur.replace(hour=9, minute=30) - now_t).total_seconds() / 60
        print(f"STATUS=PREOPEN VAH={vah:.0f} VAL={val:.0f} price={cur_px:.0f} mins_to_open={mins:.0f}"); return
    if tnow >= RTH_CLOSE or now_t.normalize() != cur:
        print(f"STATUS=CLOSED VAH={vah:.0f} VAL={val:.0f} price={cur_px:.0f}"); return
    rth = df[(df.index >= cur.replace(hour=9, minute=30)) & (df.index <= now_t) &
             (df.index.normalize() == cur)]
    d_vah, d_val = vah - cur_px, cur_px - val
    fresh = None
    for side, lvl in (("short", vah), ("long", val)):
        r = reclaim(rth, lvl, "high" if side == "short" else "low")
        if r and r.get("status") == "reclaim" and (now_t - r["conf_t"]).total_seconds() <= 10 * 60 + 30:
            fresh = (side, r)  # within ~2 bars, so an opening trigger survives the first check
    nearest = min(abs(d_vah), abs(d_val))
    if fresh:
        side, r = fresh
        edge = "VAH" if side == "short" else "VAL"
        print(f"STATUS=ALERT side={side} edge={edge} entry={r['entry']:.0f} poke={r['ext']:.0f} "
              f"conf={r['conf_t']:%H:%M} price={cur_px:.0f} VAH={vah:.0f} POC={poc:.0f} VAL={val:.0f}")
    elif nearest <= near:
        edge = "VAH" if abs(d_vah) < abs(d_val) else "VAL"
        print(f"STATUS=ARMED edge={edge} dist={nearest:.0f} price={cur_px:.0f} "
              f"VAH={vah:.0f} VAL={val:.0f} next=5min")
    else:
        print(f"STATUS=QUIET price={cur_px:.0f} toVAH={d_vah:+.0f} toVAL={d_val:+.0f} "
              f"VAH={vah:.0f} VAL={val:.0f} next=15min")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NQ")
    ap.add_argument("--watch", action="store_true", help="print edge-watcher STATUS only")
    ap.add_argument("--near", type=float, default=30.0, help="'near an edge' threshold (pts)")
    a = ap.parse_args()
    if a.watch:
        watch(a.symbol, a.near)
    else:
        run(a.symbol)
