"""Confluence engine — HTF-anchored, scored support/resistance zones.

Standalone overnight VAH/VAL is noise. A level matters where MANY independent
things agree. This gathers levels from every timeframe/type, clusters them into
zones, scores each zone by the weight of what stacks there, and prints the
strong support (long) zones below price and resistance (short) zones above.

Inputs (all cached): 1h ETH (-> resampled to 4h for major swings), 30-min
(composite value + weekly), 5-min (VWAP, overnight, prior-day, OR, round #s).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sweeplib.levels import round_numbers, round_step, volume_profile

ET = "America/New_York"


def load(name: str) -> pd.DataFrame:
    r = json.loads((ROOT / "data" / name).read_text())
    df = pd.DataFrame({k: r[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(r["time"], utc=True).tz_convert(ET))
    return df[~df.index.duplicated(keep="last")].sort_index()


def resample(df, rule):
    o = df.resample(rule, label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna()


def swings(df, k, recent):
    """Fractal swing highs/lows: extreme vs k bars each side. Return the most
    recent `recent` bars' pivots as (price, kind)."""
    h, l = df["high"].values, df["low"].values
    n = len(df)
    out = []
    for i in range(k, n - k):
        if h[i] == max(h[i - k:i + k + 1]):
            out.append((float(h[i]), i))
        if l[i] == min(l[i - k:i + k + 1]):
            out.append((float(l[i]), i))
    return [p for p, i in out if i >= n - recent]


def build_zones(m5, m30, h1, scale_pt=None):
    """Generic confluence-zone builder. Works for NQ (futures, ETH+30m+1h) and
    QQQ (equity, RTH-only 5m+1h, m30 may be None). Returns (px, now, zi) where
    zi = [(price,lo,hi,score,labs_str), ...]. scale_pt overrides the ~pt cluster
    tolerance basis (default 0.0018*price)."""
    h4 = resample(h1, "4h")
    px = float(m5["close"].iloc[-1])
    now = m5.index[-1]
    levels = []
    for p in swings(h4, 2, 60):
        levels.append((p, "4h swing", 3.0))
    for p in swings(h1, 3, 90):
        levels.append((p, "1h swing", 2.0))
    if m30 is not None and len(m30) > 40:
        poc, vah, val = volume_profile(m30, 80)
        levels += [(vah, "cVAH", 2.5), (poc, "cPOC", 2.5), (val, "cVAL", 2.5)]
        iso = m30.index.isocalendar()
        m30w = m30.assign(wk=iso["year"].astype(str) + iso["week"].astype(str))
        for wk in list(dict.fromkeys(m30w["wk"]))[-2:]:
            g = m30w[m30w["wk"] == wk]
            levels += [(float(g["high"].max()), "wkH", 2.5), (float(g["low"].min()), "wkL", 2.5)]
    cur = now.normalize()
    days = sorted({d for d in m5.index.normalize().unique() if d < cur})
    if days:
        pg = m5[(m5.index >= days[-1].replace(hour=9, minute=30)) & (m5.index < days[-1].replace(hour=16))]
        if len(pg) > 10:
            levels += [(float(pg["high"].max()), "PDH", 2.0), (float(pg["low"].min()), "PDL", 2.0),
                       (float(pg["close"].iloc[-1]), "PDC", 1.5)]
    rth = m5[(m5.index >= cur.replace(hour=9, minute=30)) & (m5.index.normalize() == cur)]
    if len(rth) >= 2:
        tp = (rth["high"] + rth["low"] + rth["close"]) / 3
        vwap = float((tp * rth["volume"]).cumsum().iloc[-1] / rth["volume"].cumsum().iloc[-1])
        levels.append((vwap, "VWAP", 1.5))
        orb = rth.iloc[:6]
        levels += [(float(orb["high"].max()), "ORH", 1.0), (float(orb["low"].min()), "ORL", 1.0)]
        levels += [(float(rth["high"].max()), "dayH", 1.5), (float(rth["low"].min()), "dayL", 1.5)]
    on = m5[(m5.index >= (cur - pd.Timedelta(days=1)).replace(hour=18)) & (m5.index < cur.replace(hour=9, minute=30))]
    if len(on) >= 10:
        opoc, ovah, oval = volume_profile(on, 50)
        levels += [(ovah, "onVAH", 1.0), (oval, "onVAL", 1.0)]
    for p in round_numbers(px, round_step(px), 3):
        levels.append((p, "round", 1.0))
    tol = scale_pt if scale_pt else 0.0018 * px
    levels.sort()
    zones, cluster = [], [levels[0]]
    for lv in levels[1:]:
        if lv[0] - cluster[-1][0] <= tol:
            cluster.append(lv)
        else:
            zones.append(cluster); cluster = [lv]
    zones.append(cluster)
    INTRADAY = {"VWAP", "ORH", "ORL", "dayH", "dayL"}  # not knowable pre-open
    zi = []
    for z in zones:
        w = sum(x[2] for x in z)
        pre = [x for x in z if x[1] not in INTRADAY]          # pre-open members only
        pw = sum(x[2] for x in pre)
        pnt = len({x[1] for x in pre})
        zi.append((sum(x[0] * x[2] for x in z) / w, min(x[0] for x in z),
                   max(x[0] for x in z), w, ", ".join(dict.fromkeys(x[1] for x in z)), pw, pnt))
    return px, now, zi


def crossref_qqq(nq_px, nq_zi):
    """Return set of NQ zone indices confirmed by a QQQ strong zone (scaled)."""
    try:
        q5 = load("qqq_5min.json"); qh1 = load("qqq_1h.json")
    except FileNotFoundError:
        return None, None
    q_px, _, q_zi = build_zones(q5, None, qh1)
    scale = nq_px / q_px
    q_strong = [(p * scale, w, labs) for (p, lo, hi, w, labs, pw, pnt) in q_zi if pw >= 5]
    confirmed = {}
    for i, (price, lo, hi, w, labs, pw, pnt) in enumerate(nq_zi):
        for qp, qw, qlabs in q_strong:
            if lo - 20 <= qp <= hi + 20:
                confirmed[i] = qp
                break
    return confirmed, q_strong


def main():
    m5 = load("nq_5min_eth_live.json")
    m30 = load("nq_30min_eth.json")
    h1 = load("nq_1h_eth.json")
    px, now, zi_all = build_zones(m5, m30, h1)
    tol = 0.0018 * px
    confirmed, q_strong = crossref_qqq(px, zi_all)

    # REFINED FILTER (backtest_confluence.py): a real zone needs >=2 distinct
    # level-types (lone levels held 64% vs 94% for >=2). Drop lone levels and
    # anything far from price. Tradeable = score>=8 AND >=2 types.
    def ntypes(labs):
        return len({x.strip() for x in labs.split(",")})

    # GRADE ON PRE-OPEN SOURCES ONLY (pnt = z[6], pw = z[5]) so the plan is the
    # same one you'd have at 9:30. Intraday levels (VWAP/OR/dayH) are shown as
    # "+context" but never upgrade the grade. Backtest edge was measured on
    # pre-open zones only, so this is the honest, tradeable-at-open map.
    INTRADAY = {"VWAP", "ORH", "ORL", "dayH", "dayL"}
    WINDOW = 400
    zi = [z for z in zi_all if z[6] >= 2 and abs(z[0] - px) <= WINDOW]  # >=2 PRE-OPEN sources
    above = sorted([z for z in zi if z[0] > px], key=lambda x: x[0])
    below = sorted([z for z in zi if z[0] <= px], key=lambda x: -x[0])
    conf_prices = set(round(confirmed[i]) for i in confirmed) if confirmed else set()

    def qflag(lo, hi):
        if confirmed is None: return ""
        return " Qs" if any(lo - 20 <= cp <= hi + 20 for cp in conf_prices) else ""

    def grade(pw, pnt):   # backtest: DENSE (>=4 pre-open sources)=+6 vs null
        if pnt >= 4: return "DENSE"
        if pw >= 8: return "A+  "
        if pw >= 5: return "**  "
        return "    "

    def fmt(z):
        price, lo, hi, w, labs, pw, pnt = z
        pre = ", ".join(l for l in labs.split(", ") if l not in INTRADAY)
        intra = [l for l in labs.split(", ") if l in INTRADAY]
        ctx = f"  +{'/'.join(intra)}" if intra else ""
        return f"  {grade(pw,pnt)}{qflag(lo,hi):>3} {lo:.0f}-{hi:.0f}  pre-open {pw:.0f} ({pnt}x)  [{pre}]{ctx}"

    print(f"NQ CONFLUENCE — {now:%a %m-%d %H:%M} ET   price {px:.0f}")
    print("(graded on PRE-OPEN sources = fixed at 9:30; '+VWAP/dayH' = intraday context, "
          "does NOT upgrade grade. DENSE=>=4 pre-open sources)\n")

    # GAMMA CONTEXT (VIX-implied expected move + vol regime) — see gamma_context.py.
    emlo = emhi = None
    try:
        import scripts.gamma_context as gc
        c = gc.context(px, "NQ")
        emlo, emhi = c["dn"], c["up"]
        print(f"GAMMA/EM CONTEXT: VIX {c['vix']:.1f} (20d {c['vix_sma20']:.1f}) -> {c['regime']}")
        print(f"  expected move +/-{c['em']:.0f}  ->  1sigma band [{c['dn']:.0f} .. {c['up']:.0f}]  "
              f"| pin {c['pin']:.0f} | weekly +/-{c['weekly']:.0f}")
        print(f"  {c['note']}")
        gl = c.get("gamma_levels")
        if gl:
            def _fmt(k):
                if k == "net_gex":
                    return f"net GEX {gl[k]/1e9:+.2f}B"
                if k == "dealer_delta":
                    return f"dealer delta {gl[k]/1e6:+.1f}M"
                return f"{k.replace('_',' ')} {gl[k]:.0f}"
            parts = [_fmt(k) for k in
                     ("net_gex", "gamma_flip", "zero_gamma", "call_wall", "put_wall", "dealer_delta") if k in gl]
            print(f"  DEALER GAMMA ({gl.get('_source','')} {gl.get('_date','')}): " + " | ".join(parts))
            gr = gc.gamma_read(px, gl)
            if gr["state"] != "UNKNOWN":
                print(f"  -> {gr['state']} GAMMA at open ({gr['basis']}): {gr['note']} [CONTEXT]")
        else:
            print("  DEALER GAMMA: not loaded (fill net_gex/gamma_flip in data/gamma_levels.json from WealthCharts)")
        print()
    except Exception as e:  # never let the context block break the core read
        print(f"(gamma context unavailable: {e})\n")

    def em_tag(level):
        if emlo is None:
            return ""
        return "  [within EM]" if emlo <= level <= emhi else "  [beyond EM - needs above-avg range]"

    print("RESISTANCE above (short):")
    for z in above[:4][::-1]: print(fmt(z))
    print(f"  ------ price {px:.0f} ------")
    print("SUPPORT below (long):")
    for z in below[:4]: print(fmt(z))

    # A+ ZONES = pre-open score >=8 (the only zones with a validated edge). Surface
    # the nearest few on each side of price so there's always a concrete map, not
    # just the single best level.
    # A+ scan is NOT capped by the display WINDOW: A+ zones are rare and worth
    # showing wherever they sit, so pull from the full valid set (>=2 pre-open
    # sources, per the refined filter) to always reach the nearest few each side.
    aplus_all = [z for z in zi_all if z[6] >= 2 and z[5] >= 8]
    aplus_above = sorted([z for z in aplus_all if z[0] > px], key=lambda x: x[0])
    aplus_below = sorted([z for z in aplus_all if z[0] <= px], key=lambda x: -x[0])
    N = 3
    print(f"\nA+ ZONES (pre-open score>=8) — nearest {N} each side:")
    print("  above price (short-side resistance):")
    if aplus_above:
        for z in aplus_above[:N][::-1]: print(fmt(z))
    else:
        print("    none in range")
    print(f"    ------ price {px:.0f} ------")
    print("  below price (long-side support):")
    if aplus_below:
        for z in aplus_below[:N]: print(fmt(z))
    else:
        print("    none in range")

    sa = aplus_above[0] if aplus_above else None  # nearest A+ resistance
    sb = aplus_below[0] if aplus_below else None   # nearest A+ support
    print("\nTRADEABLE (nearest A+ pair, score>=8, >=2 sources):")
    if sb: print((f"  LONG off support {sb[1]:.0f}-{sb[2]:.0f} -> target {sa[1]:.0f}{em_tag(sa[1])}" if sa else f"  LONG off {sb[1]:.0f}-{sb[2]:.0f}"))
    if sa: print((f"  SHORT off resistance {sa[1]:.0f}-{sa[2]:.0f} -> target {sb[2]:.0f}{em_tag(sb[2])}" if sb else f"  SHORT off {sa[1]:.0f}-{sa[2]:.0f}"))
    if not sa and not sb: print("  none in range - stand aside")

    _chart(m5, above, below, px, now, zi, conf_prices, confirmed,
           em=(emlo, emhi, c["pin"]) if emlo is not None else None)


def _chart(m5, above, below, px, now, zi, conf_prices=None, confirmed=None, em=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    conf_prices = conf_prices or set()

    def is_conf(lo, hi):
        return any(lo - 20 <= cp <= hi + 20 for cp in conf_prices)

    plot = m5[m5.index >= now - pd.Timedelta(hours=20)]
    fig, ax = plt.subplots(figsize=(15, 8))
    for i, (ts, r) in enumerate(plot.iterrows()):
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.5, zorder=3)
        ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6,
                               abs(r["close"] - r["open"]) + 0.2, facecolor=c, edgecolor=c, zorder=4))
    n = len(plot)
    for price, lo, hi, w, labs, pw, pnt in zi:
        if hi < plot["low"].min() - 100 or lo > plot["high"].max() + 100:
            continue
        red = price > px
        col = "#d32f2f" if red else "#2e7d32"
        conf = pw >= 8 and is_conf(lo, hi)
        strong = pw >= 8  # A+ tradeable on PRE-OPEN score
        dense = pnt >= 4
        qmark = " QQQ✓" if conf else ""
        band = max(hi - lo, 8)
        if strong:
            lab = "DENSE" if dense else "A+"
            ax.add_patch(Rectangle((0, lo - 1), n, band + 2, facecolor=col, alpha=0.36,
                                   edgecolor=col, lw=2.0 if dense else 1.4, zorder=2))
            ax.text(n + 0.5, price, f"{lab} {lo:.0f}-{hi:.0f}  pre{pw:.0f}({pnt}x){qmark}  [{labs[:26]}]",
                    color=col, va="center", fontsize=8, fontweight="bold")
        else:
            ax.add_patch(Rectangle((0, lo), n, band, facecolor=col, alpha=0.13, edgecolor="none", zorder=1))
            ax.text(n + 0.5, price, f"{lo:.0f}-{hi:.0f}  pre{pw:.0f}({pnt}x){qmark}", color=col, va="center", fontsize=7, alpha=0.55)
    if em is not None:
        emlo, emhi, pin = em
        for lvl in (emlo, emhi):
            ax.axhline(lvl, color="#f9a825", lw=1.1, ls=(0, (7, 4)), zorder=4)
        ax.text(n + 0.5, emhi, f"EM+ {emhi:.0f}", color="#f9a825", va="center", fontsize=7.5)
        ax.text(n + 0.5, emlo, f"EM- {emlo:.0f}", color="#f9a825", va="center", fontsize=7.5)
        ax.axhline(pin, color="#ef6c00", lw=0.9, ls=":", zorder=4)
        ax.text(n + 0.5, pin, f"pin {pin:.0f}", color="#ef6c00", va="center", fontsize=7)
    ax.axhline(px, color="#1565c0", lw=1.3, zorder=5)
    ax.text(n + 0.5, px, f"PRICE {px:.0f}", color="#1565c0", va="center", fontsize=9, fontweight="bold")
    ax.set_title(f"NQ confluence — {now:%a %m-%d %H:%M} ET   "
                 f"(graded on PRE-OPEN sources = fixed at 9:30; DENSE=>=4; QQQ✓ cross-check; weak faded)", fontsize=10.5)
    tk = list(range(0, n, max(1, n // 12)))
    ax.set_xticks(tk); ax.set_xticklabels([plot.index[i].strftime("%m-%d %H:%M") for i in tk], rotation=45, fontsize=7.5)
    ax.set_xlim(0, n + 26); ax.set_ylabel("NQ"); ax.grid(alpha=0.12, zorder=0)
    plt.tight_layout()
    out = ROOT / "reports" / "img" / "nq_confluence.png"
    plt.savefig(out, dpi=110, bbox_inches="tight")
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
