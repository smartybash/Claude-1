"""Can a single earnings-event option trade turn $10,000 into $100,000 with odds on our side?

For one upcoming earnings event, every OTM option and every liquid vertical
spread on the real chain is priced as a $10,000 all-in position, then
judged three ways:

  MARKET    The probability of finishing beyond the level that makes the
            position worth $100,000, read model-free from the chain: a
            spread between adjacent strikes is a digital option, and its
            price is the market's probability.

  HISTORY   Every past earnings event for the same stock, replayed over the
            identical window (same sessions before the reaction, same
            after) and applied to today's spot. Gives the stock's own
            probability of the 10x and the position's historical expected
            value.

  ROBUST?   An apparent edge must survive: the modern era alone (2013+),
            removal of the single best event, and a bootstrap over events.

What "odds on our side" can mean. For any fairly priced long-only position,
Markov's inequality caps P(payoff >= 10x cost) at 1/10. So a 10x trade can
never be likely to win; the only achievable version of "odds on our side"
is positive expected value — history paying more than the $10,000 costs.

Why verticals. A naked OTM option wastes probability on outcomes far past
the 10x level. A vertical spread caps the payoff, so one that costs ~10% of
its width pays 10x on a much smaller move — its probability approaches the
10% ceiling. The spread section ranks these, at executable prices (long leg
at the ask, short leg at the bid).

Prices are raw closes; stock splits (2:1, 3:1, 3:2, 4:1 single-day ratios)
are detected, back-adjusted and printed for audit. Commissions follow the
IBKR Pro fixed schedule for options (verify against your own account).

    python scripts/event_10x.py --chain data/mu_chain_20260929.json \
        --daily mu_daily.json --earnings data/mu_earnings_dates.json \
        --chain-date 2026-09-29 --expiry 2026-10-02
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import statistics
from bisect import bisect_left
from datetime import date, timedelta
from pathlib import Path

STAKE = 10_000.0
TARGET = 100_000.0
MODERN = "2013-01-01"      # start of the "modern era" robustness subset
EXIT_FEE = 0.65            # per contract to close a leg worth >= $0.10


def commission(price: float) -> float:
    """Per-contract commission, IBKR Pro fixed schedule for US equity options.

    Premium < $0.05 -> $0.25; $0.05-$0.10 -> $0.50; >= $0.10 -> $0.65.
    """
    if price < 0.05:
        return 0.25
    if price < 0.10:
        return 0.50
    return 0.65


# ---------------------------------------------------------------- loaders

def load_chain(path: str) -> list[dict]:
    d = json.loads(Path(path).read_text())
    if "fields" in d:  # compact transcribed format (no bid / OI)
        f = d["fields"]
        return [dict(zip(f, row)) for row in d["data"]]
    return [{"strike": float(r["strike"]), "type": r["type"],
             "ask": float(r["ask"]), "bid": float(r["bid"]), "mark": float(r["mark"]),
             "implied_volatility": float(r["implied_volatility"]),
             "delta": float(r["delta"]), "oi": int(r["open_interest"])}
            for r in d["data"]]


def load_daily(path: str) -> tuple[list[str], list[float], list[str]]:
    """Dates and split-adjusted closes, plus a log of detected splits."""
    raw = Path(path).read_text()
    if raw.lstrip().startswith("{"):
        raw = json.loads(raw)["result"]
    rows = sorted(csv.DictReader(io.StringIO(raw)), key=lambda r: r["timestamp"])
    dates = [r["timestamp"] for r in rows]
    close = [float(r["close"]) for r in rows]
    splits = []
    for i in range(len(close) - 1, 0, -1):
        ratio = close[i - 1] / close[i]
        for s in (2.0, 3.0, 1.5, 4.0):
            if abs(ratio / s - 1) < 0.06:
                for j in range(i):
                    close[j] /= s
                splits.append(f"{dates[i]} {s:g}:1")
                break
    return dates, close, splits


def load_events(path: str) -> tuple[dict, list[tuple[str, str]]]:
    d = json.loads(Path(path).read_text())
    return d["upcoming"], [tuple(x) for x in d["past"]]


# ------------------------------------------------------------ the market

def _isotonic(ys: list[float], weights: list[float], increasing: bool) -> list[float]:
    """Pool-adjacent-violators: the closest monotone sequence (weighted L2)."""
    sign = 1 if increasing else -1
    blocks = []  # [weighted mean, weight, count]
    for y, w in zip(ys, weights):
        blocks.append([sign * y, w, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            m2, w2, c2 = blocks.pop()
            m1, w1, c1 = blocks.pop()
            blocks.append([(m1 * w1 + m2 * w2) / (w1 + w2), w1 + w2, c1 + c2])
    out = []
    for m, _, c in blocks:
        out += [sign * m] * c
    return out


def digital_prob(chain: list[dict], level: float, side: str) -> float | None:
    """Model-free P(S_T beyond `level`) from adjacent-strike spreads (marks).

    Raw pairwise digitals are noisy where options trade in pennies, so they
    are forced to be monotone — P(S_T > K) cannot rise with K — by isotonic
    regression weighted by strike spacing, before interpolating.
    """
    legs = sorted((c for c in chain if c["type"] == side), key=lambda c: c["strike"])
    mids, raw, wts = [], [], []
    for a, b in zip(legs, legs[1:]):
        dk = b["strike"] - a["strike"]
        if dk <= 0:
            continue
        p = (a["mark"] - b["mark"]) / dk if side == "call" else (b["mark"] - a["mark"]) / dk
        mids.append((a["strike"] + b["strike"]) / 2)
        raw.append(min(max(p, 0.0), 1.0))
        wts.append(dk)
    fitted = _isotonic(raw, wts, increasing=(side == "put"))
    pts = list(zip(mids, fitted))
    if not pts or level < pts[0][0] or level > pts[-1][0]:
        return None
    for (k1, p1), (k2, p2) in zip(pts, pts[1:]):
        if k1 <= level <= k2:
            return p1 + (p2 - p1) * (level - k1) / (k2 - k1)
    return pts[-1][1]


# ---------------------------------------------------------------- history

def sessions_between(a: str, b: str) -> int:
    """Weekday sessions after `a` up to and including `b` (holidays ignored)."""
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    n, d = 0, da
    while d < db:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def reaction_index(dates: list[str], report: str, when: str) -> int | None:
    """Index of the first session that trades on the news."""
    i = bisect_left(dates, report)
    if i >= len(dates) or dates[i] != report:
        return None
    return i + 1 if when == "post" else i


def window_returns(dates, close, events, pre: int, post: int) -> list[tuple[str, float]]:
    out = []
    for d, when in events:
        r = reaction_index(dates, d, when)
        if r is None or r - pre < 0 or r + post >= len(close):
            continue
        out.append((d, close[r + post] / close[r - pre] - 1))
    return out


# ------------------------------------------------------------- positions

class Position:
    """A $10k all-in long option or vertical spread, held to expiry."""

    def __init__(self, label, side, long_k, short_k, debit, fees_in, fee_out):
        self.label, self.side = label, side
        self.long_k, self.short_k = long_k, short_k
        per = debit * 100 + fees_in
        self.n = int(STAKE // per) if per > 0 else 0
        self.debit = debit
        self.fee_out = fee_out  # per unit, to close at expiry
        width = abs(short_k - long_k) if short_k is not None else float("inf")
        self.max_pay = self.n * (width * 100 - fee_out) if short_k is not None else float("inf")

    def value(self, s_t: float) -> float:
        x = (s_t - self.long_k) if self.side == "call" else (self.long_k - s_t)
        if x <= 0 or self.n == 0:
            return 0.0
        if self.short_k is not None:
            x = min(x, abs(self.short_k - self.long_k))
        return max(0.0, self.n * (100 * x - self.fee_out))

    def level(self) -> float | None:
        """Underlying price at which the position is worth TARGET."""
        if self.n == 0 or self.max_pay < TARGET:
            return None
        need = (TARGET + self.n * self.fee_out) / (100 * self.n)
        return self.long_k + need if self.side == "call" else self.long_k - need


def naked_positions(chain, spot):
    out = []
    for leg in chain:
        otm = (leg["type"] == "call" and leg["strike"] > spot) or \
              (leg["type"] == "put" and leg["strike"] < spot)
        if not otm or leg["ask"] <= 0:
            continue
        p = Position(f"{leg['strike']:g}{leg['type'][0].upper()}", leg["type"],
                     leg["strike"], None, leg["ask"], commission(leg["ask"]), EXIT_FEE)
        if p.level() is not None:
            out.append(p)
    return out


def vertical_positions(chain, spot, max_width=60, min_oi=100):
    """OTM verticals with >= 10x max payoff, long at ask, short at bid."""
    if not chain or "bid" not in chain[0]:
        return []
    by = {(c["strike"], c["type"]): c for c in chain}
    out = []
    for side in ("call", "put"):
        ks = sorted(k for (k, t) in by if t == side)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if b - a > max_width:
                    break
                lk, sk = (a, b) if side == "call" else (b, a)
                if (side == "call" and lk <= spot) or (side == "put" and lk >= spot):
                    continue
                lo, sh = by[(lk, side)], by[(sk, side)]
                if lo["ask"] <= 0 or sh["bid"] <= 0 or lo.get("oi", 0) < min_oi or sh.get("oi", 0) < min_oi:
                    continue
                debit = lo["ask"] - sh["bid"]
                if debit <= 0:
                    continue
                p = Position(f"+{lk:g}/-{sk:g}{side[0].upper()}", side, lk, sk, debit,
                             commission(lo["ask"]) + commission(sh["bid"]), 2 * EXIT_FEE)
                if p.level() is not None:
                    out.append(p)
    return out


def evaluate(p: Position, spot, chain, hist, rng) -> dict:
    lvl = p.level()
    moves = [r for _, r in hist]
    modern = [r for d, r in hist if d >= MODERN]
    vals = [p.value(spot * (1 + r)) for r in moves]
    won = [v >= TARGET for v in vals]
    ev_all, ev_drop1 = statistics.mean(vals), statistics.mean(sorted(vals)[:-1])
    mvals = sorted(p.value(spot * (1 + r)) for r in modern)
    ev_mod, ev_mod_drop1 = statistics.mean(mvals), statistics.mean(mvals[:-1])
    boot = None  # only bootstrapped when the cheaper checks already pass
    if ev_all > STAKE and ev_mod > STAKE and ev_drop1 > STAKE and ev_mod_drop1 > STAKE:
        boots = [statistics.mean(rng.choices(vals, k=len(vals))) for _ in range(4000)]
        boot = sum(b > STAKE for b in boots) / len(boots)
    return {
        "pos": p, "level": lvl, "move": lvl / spot - 1,
        "mkt": digital_prob(chain, lvl, p.side),
        "p_all": sum(won) / len(won),
        "p_mod": sum(p.value(spot * (1 + r)) >= TARGET for r in modern) / len(modern),
        "ev_all": ev_all, "ev_mod": ev_mod, "ev_drop1": ev_drop1,
        "ev_mod_drop1": ev_mod_drop1, "boot": boot,
    }


def robust_edge(e: dict) -> bool:
    """An edge must not hinge on any single event, in either sample."""
    return (e["ev_all"] > STAKE and e["ev_mod"] > STAKE and e["ev_drop1"] > STAKE
            and e["ev_mod_drop1"] > STAKE and (e["boot"] or 0) >= 0.90)


def table(rows, title):
    print(f"\n{title}")
    hdr = (f"{'position':>16} {'debit':>6} {'n':>5} {'10x at':>9} {'move':>7} {'mkt P':>6} "
           f"{'hist P':>6} {'2013+ P':>7} {'EV all':>8} {'EV 2013+':>8} {'-best':>7} {'2013+-best':>10} {'boot':>5}")
    print(hdr)
    print("-" * len(hdr))
    for e in rows:
        p = e["pos"]
        mk = f"{e['mkt']:.1%}" if e["mkt"] is not None else "n/a"
        print(f"{p.label:>16} {p.debit:>6.2f} {p.n:>5} {e['level']:>9.2f} {e['move']:>+7.1%} {mk:>6} "
              f"{e['p_all']:>6.1%} {e['p_mod']:>7.1%} {e['ev_all']:>8,.0f} {e['ev_mod']:>8,.0f} "
              f"{e['ev_drop1']:>7,.0f} {e['ev_mod_drop1']:>10,.0f} {boot_s(e['boot']):>5}")


def boot_s(b: float | None) -> str:
    return "—" if b is None else f"{b:.0%}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--daily", required=True)
    ap.add_argument("--earnings", required=True)
    ap.add_argument("--chain-date", required=True)
    ap.add_argument("--expiry", required=True)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    chain = load_chain(args.chain)
    dates, close, splits = load_daily(args.daily)
    upcoming, past = load_events(args.earnings)
    sym = Path(args.earnings).name.split("_")[0].upper()
    spot = close[dates.index(args.chain_date)]

    to_report = sessions_between(args.chain_date, upcoming["date"])
    pre = to_report + (0 if upcoming["time"].startswith("pre") else 1)
    post = sessions_between(args.chain_date, args.expiry) - pre
    hist = window_returns(dates, close, past, pre, post)
    moves = [r for _, r in hist]
    modern = [r for d, r in hist if d >= MODERN]

    ks = sorted({c["strike"] for c in chain})
    atm = min(ks, key=lambda k: abs(k - spot))
    straddle = sum(c["mark"] for c in chain if c["strike"] == atm)
    implied = straddle / spot

    print("=" * 108)
    print(f"{sym}: earnings {upcoming['date']} {upcoming['time']}, expiry {args.expiry}. "
          f"Spot {spot:.2f} ({args.chain_date} close).")
    print(f"History replayed over the same window: {pre} session(s) into the reaction, {post} after. "
          f"{len(hist)} events, {len(modern)} since 2013.")
    if splits:
        print(f"Splits back-adjusted: {', '.join(splits)}")
    print("=" * 108)
    print(f"Implied move (ATM {atm:g} straddle {straddle:.2f}): +/-{implied:.2%}")
    for lab, mv in (("all events", moves), ("since 2013", modern)):
        am = [abs(m) for m in mv]
        print(f"Realised |move| {lab:>11}: mean {statistics.mean(am):.2%} "
              f"(realised/implied {statistics.mean(am) / implied:.2f}), "
              f"largest up {max(mv):+.1%}, largest down {min(mv):+.1%}")

    rng = random.Random(7)
    naked = [evaluate(p, spot, chain, hist, rng) for p in naked_positions(chain, spot)]
    spreads = [evaluate(p, spot, chain, hist, rng) for p in vertical_positions(chain, spot)]

    table(sorted(naked, key=lambda e: -e["ev_mod"])[: args.top],
          "NAKED OPTIONS — best by modern-era expected value (EV per $10,000 staked)")
    if spreads:
        table(sorted(spreads, key=lambda e: -(e["mkt"] or 0))[: args.top],
              "VERTICAL SPREADS — highest market-implied P(10x)")
        table(sorted(spreads, key=lambda e: -e["ev_mod"])[: args.top],
              "VERTICAL SPREADS — best by modern-era expected value")

    best_p = max((e["mkt"] or 0 for e in naked + spreads), default=0)
    edge = [e for e in naked + spreads if robust_edge(e)]
    print(f"\nBest market-implied P(10x) available: {best_p:.1%} (ceiling for any fair long position: 10.0%)")
    print(f"Positions whose edge survives ALL checks (EV > stake on all events, on 2013+, "
          f"without the best event in each, bootstrap >= 90%): {len(edge)}")
    for e in sorted(edge, key=lambda e: -e["ev_mod"])[:5]:
        print(f"   {e['pos'].label}: EV 2013+ ${e['ev_mod']:,.0f}, P(10x) {e['p_mod']:.1%}")
    print("\nEvent windows, newest first: " +
          "  ".join(f"{d[2:7]}:{r:+.1%}" for d, r in hist[:14]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
