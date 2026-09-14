"""GEX / gamma-regime proxy — the backtestable core of Alex's tape read.

WHY A PROXY: a real dealer-GEX needs option OPEN INTEREST + gamma per strike,
and a HISTORY of it to backtest. Neither IBKR MCP nor FMP exposes option OI /
greeks (let alone history), so a literal GEX backtest is impossible here. But
the *tradeable content* of the gamma read is a regime call:
  * POSITIVE gamma  -> dealers sell rallies / buy dips -> vol suppressed ->
                       intraday MEAN-REVERSION works (fade extremes to VWAP).
  * NEGATIVE gamma  -> dealers buy rallies / sell dips -> vol amplified ->
                       intraday TREND / breakout works, fading gets run over.
VIX relative to its own trend is a clean, non-circular proxy for that regime
(implied vol is options-derived; the trade outcome is price-derived).

CLASSIFIER (no lookahead — uses PRIOR day's VIX close, known at the open):
  SUPPRESSED (pos-gamma-like) : VIX[t-1] < SMA20(VIX)[t-1]  AND  VIX[t-1] < 20
  AMPLIFIED  (neg-gamma-like) : VIX[t-1] > SMA20(VIX)[t-1]                    (or VIX>=22)
  NEUTRAL                     : otherwise (not traded by the filter)

TEST: on pooled QQQ+SPY hourly RTH sessions (the window IBKR intraday reaches),
run the SAME 11:00 trade two ways, split by regime:
  MOMENTUM = trade WITH the first-90-min move (d = sign(p_dec-open))
  FADE     = trade AGAINST it (d = -sign)
  entry = market @ 11:00, stop = 0.30*ATR20, exit = stop or MOC, costs 0.02*ATR.
MERIT if MOMENTUM is positive in AMPLIFIED and FADE is positive in SUPPRESSED
(the crossover) — that is the gamma regime earning its keep as a mode switch.
Scope: QQQ+SPY 1h, ~Nov-2025..Jul-2026; costs modelled; PnL in ATR units.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backtest_trend import build_sessions, simulate

pd.set_option("display.width", 200)


def vix_regime() -> pd.Series:
    """Date -> regime string, lagged one day (known at the open)."""
    r = json.loads((ROOT / "data" / "vix_daily_5y.json").read_text())
    v = pd.Series(r["close"], index=pd.to_datetime([t[:10] for t in r["time"]]))
    v = v[~v.index.duplicated(keep="last")].sort_index()
    sma = v.rolling(20).mean()
    lo, hi = v.shift(1), sma.shift(1)          # prior-day values
    reg = pd.Series("NEUTRAL", index=v.index)
    reg[(lo < hi) & (lo < 20)] = "SUPPRESSED"  # pos-gamma-like
    reg[(lo > hi) | (lo >= 22)] = "AMPLIFIED"  # neg-gamma-like
    reg.index = pd.to_datetime(reg.index.date)
    return reg


def summarise(pnls: list[float]) -> dict:
    a = np.array(pnls, dtype=float)
    if len(a) == 0:
        return {"n": 0, "win%": np.nan, "avg_ATR": np.nan, "total": np.nan}
    return {"n": len(a), "win%": round((a > 0).mean(), 3),
            "avg_ATR": round(a.mean(), 4), "total": round(a.sum(), 2)}


def main():
    reg = vix_regime()
    sessions = build_sessions("qqq") + build_sessions("spy")

    buckets = {r: {"MOM": [], "FADE": []} for r in ("SUPPRESSED", "NEUTRAL", "AMPLIFIED")}
    for s in sessions:
        rr = reg.get(s["date"])
        if rr is None or rr not in buckets:
            continue
        d = 1 if s["p_dec"] >= s["open"] else -1     # first-90-min direction
        pm = simulate(s, d, "mkt", "atr")
        pf = simulate(s, -d, "mkt", "atr")
        if pm is not None:
            buckets[rr]["MOM"].append(pm)
        if pf is not None:
            buckets[rr]["FADE"].append(pf)

    print("GEX / GAMMA-REGIME PROXY  (VIX vs its 20d trend, lagged) — QQQ+SPY 1h")
    print("same 11:00 trade, MOMENTUM (with first-90m move) vs FADE (against), by regime.")
    print("hypothesis: MOM wins in AMPLIFIED (neg-gamma), FADE wins in SUPPRESSED (pos-gamma).\n")
    hdr = f"{'regime':12s} {'style':5s} | {'n':>4} {'win%':>6} {'avg_ATR':>8} {'total':>7}"
    print(hdr); print("-" * len(hdr))
    for rr in ("SUPPRESSED", "NEUTRAL", "AMPLIFIED"):
        for style in ("MOM", "FADE"):
            st = summarise(buckets[rr][style])
            print(f"{rr:12s} {style:5s} | {st['n']:>4} {st['win%']!s:>6} "
                  f"{st['avg_ATR']!s:>8} {st['total']!s:>7}")
        print("-" * len(hdr))

    sup_fade = summarise(buckets["SUPPRESSED"]["FADE"])["avg_ATR"]
    amp_mom = summarise(buckets["AMPLIFIED"]["MOM"])["avg_ATR"]
    sup_mom = summarise(buckets["SUPPRESSED"]["MOM"])["avg_ATR"]
    amp_fade = summarise(buckets["AMPLIFIED"]["FADE"])["avg_ATR"]
    print("\ncrossover check (which style wins in each regime):")
    print(f"  SUPPRESSED (low VIX): MOM {sup_mom:+.4f} vs FADE {sup_fade:+.4f}  -> "
          f"{'MOM (trend-continuation)' if sup_mom > sup_fade else 'FADE'}")
    print(f"  AMPLIFIED (high VIX): MOM {amp_mom:+.4f} vs FADE {amp_fade:+.4f}  -> "
          f"{'FADE (afternoon reversal)' if amp_fade > amp_mom else 'MOM'}")

    # the observed edge = best style per regime; is it a genuine, opposite-direction switch?
    switch = (sup_mom > sup_fade) != (amp_mom > amp_fade)  # different style wins in each
    best_sup = max(sup_mom, sup_fade); best_amp = max(amp_mom, amp_fade)
    print("\nVERDICT:", "REGIME HAS MERIT as a mode-switch (best style differs by regime, both edges > 0)"
          if (switch and best_sup > 0 and best_amp > 0)
          else "no usable mode-switch on this sample")

    # ---- robustness: split-half (time) and per-instrument on the two 'winning' cells ----
    def cell(sess, regime, style):
        out = []
        for s in sess:
            if reg.get(s["date"]) != regime:
                continue
            d = 1 if s["p_dec"] >= s["open"] else -1
            p = simulate(s, d if style == "MOM" else -d, "mkt", "atr")
            if p is not None:
                out.append(p)
        return summarise(out)

    ss = sorted(sessions, key=lambda s: s["date"])
    midd = ss[len(ss) // 2]["date"]
    print("\nstability of the two edge cells (SUPPRESSED/MOM, AMPLIFIED/FADE):")
    for lab, sub in [("first half ", [s for s in ss if s["date"] < midd]),
                     ("second half", [s for s in ss if s["date"] >= midd]),
                     ("QQQ only   ", [s for s in ss if s["sym"] == "qqq"]),
                     ("SPY only   ", [s for s in ss if s["sym"] == "spy"])]:
        a = cell(sub, "SUPPRESSED", "MOM"); b = cell(sub, "AMPLIFIED", "FADE")
        print(f"  {lab}: SUP/MOM avg {a['avg_ATR']!s:>8} (n={a['n']:>3})   "
              f"AMP/FADE avg {b['avg_ATR']!s:>8} (n={b['n']:>3})")


if __name__ == "__main__":
    main()
