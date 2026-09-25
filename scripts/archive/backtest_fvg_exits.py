"""Exit/partial optimization for the FVG continuation trade (structure stop),
focused on EXPANSION days (negative gamma OR mega-cap earnings reaction) where the
edge lives. Same entries as backtest_vwap_fvg_v2 'cont'; only the exit varies.

Exits compared (long; short is the mirror):
  fixed1R / fixed2R / fixed3R : target M*risk, hard structure stop
  vwapCross                   : ride until a close back through VWAP
  trailPrevLow                : ratchet stop up to the prior bar's low
  half@1R+ride                : bank 1/2 at +1R, stop->breakeven, ride rest to VWAP loss
  half@2R+ride                : bank 1/2 at +2R, stop->breakeven, ride rest to VWAP loss
All on 123 QQQ sessions, structure stop = swing low/high of prior 5 bars. No costs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_vwap_fvg import load_intraday, regime_map, session_vwap, MIN_GAP
from backtest_vwap_fvg_v2 import earnings_reaction_days, K


def entries():
    """Yield continuation entries: (day, dirn, i, entry, stop, risk, net, bars, vwap)."""
    intr = load_intraday()
    days = sorted(intr["day"].unique())
    reg = regime_map(days)
    out = []
    for day in days:
        b = intr[intr["day"] == day].reset_index()
        if len(b) < K + 3:
            continue
        vwap = session_vwap(b).values
        h, l, c = b["high"].values, b["low"].values, b["close"].values
        n = len(b); net = reg.get(day)
        fvgs = []
        for i in range(n):
            if i >= 2:
                if l[i] > h[i - 2] and (l[i] - h[i - 2]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bull", "top": l[i], "bot": h[i - 2], "formed": i, "used": False})
                if h[i] < l[i - 2] and (l[i - 2] - h[i]) / c[i] >= MIN_GAP:
                    fvgs.append({"side": "bear", "top": l[i - 2], "bot": h[i], "formed": i, "used": False})
            for f in fvgs:
                if f["used"] or i <= f["formed"] or i < K:
                    continue
                if f["side"] == "bull" and l[i] <= f["top"] and c[i] > vwap[i]:
                    entry = f["top"]; stop = min(l[i - K:i + 1]); risk = entry - stop
                    if risk > 0 and l[i] > stop:
                        f["used"] = True
                        out.append((day, 1, i, entry, stop, risk, net, h, l, c, vwap, n))
                elif f["side"] == "bear" and h[i] >= f["bot"] and c[i] < vwap[i]:
                    entry = f["bot"]; stop = max(h[i - K:i + 1]); risk = stop - entry
                    if risk > 0 and h[i] < stop:
                        f["used"] = True
                        out.append((day, -1, i, entry, stop, risk, net, h, l, c, vwap, n))
            fvgs = [f for f in fvgs if f["used"] or not (
                (f["side"] == "bull" and l[i] <= f["bot"]) or
                (f["side"] == "bear" and h[i] >= f["top"]))]
    return out


def exit_R(rule, s, i, entry, stop, risk, h, l, c, vwap, n):
    """R for one trade under `rule`. s=+1 long, -1 short."""
    def adverse(j):  return l[j] if s > 0 else h[j]      # worst-case extreme
    def favor(j):    return h[j] if s > 0 else l[j]      # best-case extreme
    def stopped(j):  return (l[j] <= stop) if s > 0 else (h[j] >= stop)
    def rr(p):       return s * (p - entry) / risk
    def vwap_lost(j):return (c[j] < vwap[j]) if s > 0 else (c[j] > vwap[j])

    if rule.startswith("fixed"):
        M = float(rule[5])
        tgt = entry + s * M * risk
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if (favor(j) >= tgt) if s > 0 else (favor(j) <= tgt): return M
        return rr(c[n - 1])
    if rule == "vwapCross":
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if vwap_lost(j): return rr(c[j])
        return rr(c[n - 1])
    if rule == "trailPrevLow":
        ts = stop
        for j in range(i + 1, n):
            ts = max(ts, l[j - 1]) if s > 0 else min(ts, h[j - 1])
            if (l[j] <= ts) if s > 0 else (h[j] >= ts):
                return s * (ts - entry) / risk
        return rr(c[n - 1])
    if rule.startswith("half@"):
        P = float(rule[5])
        tgt = entry + s * P * risk
        for j in range(i + 1, n):
            if stopped(j): return -1.0
            if ((favor(j) >= tgt) if s > 0 else (favor(j) <= tgt)):
                # banked 0.5*P; ride remaining 0.5 with breakeven stop
                for k in range(j + 1, n):
                    if (l[k] <= entry) if s > 0 else (h[k] >= entry): rem = 0.0; break
                    if vwap_lost(k): rem = rr(c[k]); break
                else:
                    rem = rr(c[n - 1])
                return 0.5 * P + 0.5 * rem
        return rr(c[n - 1])
    raise ValueError(rule)


def main():
    ents = entries()
    er = earnings_reaction_days(sorted({e[0] for e in ents}))
    rules = ["fixed1R", "fixed2R", "fixed3R", "vwapCross", "trailPrevLow", "half@1", "half@2"]
    print(f"FVG continuation exit optimization  (n={len(ents)} entries, 123 QQQ sessions)\n")
    print(f"{'exit rule':14s} | {'ALL':>18s} | {'EXPANSION days':>20s} | {'COMPRESSION days':>20s}")
    print("-" * 80)
    for rule in rules:
        rows = []
        for (day, s, i, entry, stop, risk, net, h, l, c, vwap, n) in ents:
            R = exit_R(rule, s, i, entry, stop, risk, h, l, c, vwap, n)
            exp = (net is not None and net < 0) or (day in er)
            rows.append((R, exp))
        df = pd.DataFrame(rows, columns=["R", "exp"])
        def fmt(sub):
            if len(sub) == 0: return "n=0"
            return f"{sub['R'].mean():+.3f}R w{ (sub['R']>0).mean()*100:.0f}% n{len(sub)}"
        print(f"{rule:14s} | {fmt(df):>18s} | {fmt(df[df['exp']]):>20s} | {fmt(df[~df['exp']]):>20s}")
    print("\nread: pick the exit with the best EXPANSION-day mean R (that's the tradeable "
          "subset); compression stays a skip. Partials trade mean-R for higher win%.")


if __name__ == "__main__":
    main()
