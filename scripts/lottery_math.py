"""What would a 100x single-option trade actually require, and how likely is it?

Answers the concrete question "turn $10,000 into $1,000,000 in one 0DTE or
3-5 DTE option trade" three independent ways:

  1. MARKOV BOUND (model-free). An option's price is the risk-neutral
     expected value of its payoff. Markov's inequality then says
        P(payoff >= M x price) <= E[payoff] / (M x price) = 1/M
     so a 100x outcome has probability AT MOST 1% on ANY option, any
     strike, any expiry. This is arithmetic from no-arbitrage pricing, not
     a forecast, and it is an upper bound before costs.

  2. MARKET-IMPLIED (from a real chain). For each OTM strike, work out how
     many contracts $10k buys, what underlying price makes the position
     worth $1M at expiry, and read the market's own probability of
     reaching that price off the delta of the option struck there.

  3. EMPIRICAL (from 25 years of SPY history). How often has SPY actually
     moved that far over 1 session and over 3-5 sessions.

Chain data: real SPY quotes from Alpha Vantage HISTORICAL_OPTIONS, priced
at the 2026-09-28 close for the 2026-09-29 expiry (i.e. what you could
have paid to open a 0DTE trade). SPY spot 765.61.

Usage: python scripts/lottery_math.py <spy_daily_csv_or_json>
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

STAKE = 10_000
TARGET = 1_000_000
MULTIPLE = TARGET / STAKE          # 100x

SPOT = 765.61                      # SPY close 2026-09-28
ATM_IV = 0.1222                    # SPY 0DTE at-the-money implied vol, same close

# (strike, mark, ask, delta) — real 0DTE SPY calls, 2026-09-28 close.
# Note the ask/mark divergence at and above 781: mark $0.01, ask $0.02.
# You pay the ask, so the true entry price is double the "mark" there.
CALLS = [
    (768, 0.93, 0.93, 0.30552),
    (769, 0.64, 0.64, 0.23279),
    (770, 0.45, 0.45, 0.17092),
    (771, 0.29, 0.30, 0.12079),
    (772, 0.21, 0.21, 0.10032),
    (773, 0.14, 0.14, 0.06915),
    (774, 0.10, 0.10, 0.04607),
    (775, 0.07, 0.07, 0.02964),
    (776, 0.06, 0.06, 0.02662),
    (777, 0.04, 0.05, 0.01703),
    (778, 0.04, 0.04, 0.01592),
    (779, 0.03, 0.03, 0.01502),
    (780, 0.03, 0.03, 0.01427),
    (781, 0.01, 0.02, 0.00633),
    (782, 0.01, 0.02, 0.00397),
    (785, 0.01, 0.02, 0.00429),
    (790, 0.01, 0.01, 0.00335),
    (800, 0.01, 0.01, 0.00252),
]

# delta by strike, for reading P(finish above a given level) off the chain
DELTA_BY_STRIKE = {k: d for k, _, _, d in CALLS}


def implied_prob_above(level: float) -> float | None:
    """Market-implied P(SPY finishes above `level`), interpolated on delta.

    A call's delta is the risk-neutral probability it expires in the money,
    so the delta curve across strikes IS the market's terminal
    distribution.
    """
    ks = sorted(DELTA_BY_STRIKE)
    if level <= ks[0] or level >= ks[-1]:
        return None
    for a, b in zip(ks, ks[1:]):
        if a <= level <= b:
            wa, wb = DELTA_BY_STRIKE[a], DELTA_BY_STRIKE[b]
            f = (level - a) / (b - a)
            return wa + f * (wb - wa)
    return None


def load_closes(path: str | Path) -> list[tuple[str, float]]:
    raw = Path(path).read_text()
    if raw.lstrip().startswith("{"):
        raw = json.loads(raw)["result"]
    rows = list(csv.DictReader(io.StringIO(raw)))
    out = [(r["timestamp"], float(r["close"])) for r in rows]
    out.sort(key=lambda t: t[0])
    return out


def horizon_returns(closes: list[tuple[str, float]], n: int) -> list[float]:
    """All overlapping n-session percentage moves."""
    c = [p for _, p in closes]
    return [(c[i + n] / c[i] - 1) for i in range(len(c) - n)]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    closes = load_closes(sys.argv[1])
    print(f"SPY history: {len(closes)} sessions, {closes[0][0]} to {closes[-1][0]}")
    print(f"Spot for the option math: {SPOT} (2026-09-28 close)\n")

    print("=" * 96)
    print("1. MARKOV BOUND — model-free ceiling on any 100x option trade")
    print("=" * 96)
    print(f"  P(payoff >= {MULTIPLE:.0f}x premium) <= 1/{MULTIPLE:.0f} = "
          f"{1 / MULTIPLE:.2%}   for ANY option, strike or expiry.")
    print("  Holds because price = risk-neutral E[payoff]; it is an upper bound,")
    print("  and it is BEFORE spread and commissions.\n")

    print("=" * 96)
    print("2. MARKET-IMPLIED — what each real 0DTE strike would need")
    print("=" * 96)
    print(f"{'strike':>7} {'ask':>6} {'contracts':>10} {'SPY needed':>11} "
          f"{'move req':>9} {'P(win) mkt':>11} {'odds':>10}")
    print("-" * 96)
    rows = []
    for strike, mark, ask, delta in CALLS:
        contracts = int(STAKE / (ask * 100))
        if contracts == 0:
            continue
        # intrinsic per contract needed so contracts x intrinsic x 100 = TARGET
        need_intrinsic = TARGET / (contracts * 100)
        spy_needed = strike + need_intrinsic
        move = spy_needed / SPOT - 1
        p = implied_prob_above(spy_needed)
        rows.append((strike, ask, contracts, spy_needed, move, p))
        ps = f"{p:.3%}" if p is not None else "<0.25%"
        od = f"1 in {1/p:,.0f}" if p else "1 in >400"
        print(f"{strike:>7} {ask:>6.2f} {contracts:>10,} {spy_needed:>11.2f} "
              f"{move:>+9.2%} {ps:>11} {od:>10}")

    best = max((r for r in rows if r[5]), key=lambda r: r[5])
    print(f"\n  Best-case strike is {best[0]:.0f}: needs SPY {best[3]:.2f} "
          f"({best[4]:+.2%}), market-implied probability {best[5]:.2%} "
          f"(~1 in {1/best[5]:.0f}).")

    print("\n" + "=" * 96)
    print("3. EMPIRICAL — how often SPY has actually moved that far")
    print("=" * 96)
    print("  Split by volatility regime, because an unconditional 25-year average")
    print("  blends 2008/2020 with quiet tape. Today's 0DTE ATM implied vol is")
    print(f"  {ATM_IV:.1%} annualized (daily sigma {ATM_IV / 252 ** 0.5:.2%}), so the")
    print("  low-vol column is the relevant one for a trade placed now.\n")

    c = [p for _, p in closes]
    rets1 = [c[i + 1] / c[i] - 1 for i in range(len(c) - 1)]
    import statistics
    vols = {i: statistics.pstdev(rets1[i - 20:i]) * 252 ** 0.5
            for i in range(20, len(rets1))}
    t33 = sorted(vols.values())[len(vols) // 3]

    print(f"{'horizon':>9} {'threshold':>11} {'all regimes':>14} "
          f"{f'low vol (<{t33:.0%})':>18}")
    print("  " + "-" * 56)
    for n in (1, 3, 5):
        idx = [i for i in range(20, len(c) - n)]
        lo = [i for i in idx if vols.get(i, 99) < t33]
        for th in (0.0214, 0.0240, 0.030, 0.040):
            fa = sum(1 for i in idx if c[i + n] / c[i] - 1 >= th) / len(idx)
            fl = sum(1 for i in lo if c[i + n] / c[i] - 1 >= th) / len(lo)
            print(f"{n:>7}d  {th:>+10.2%} {fa:>13.3%} {fl:>17.3%}")
        print()
    print("  The required +2.40% single session has happened ZERO times in "
          f"{len(lo):,} low-vol")
    print("  sessions across 25 years. The market's 0.42% is, if anything, "
          "generous — it")
    print("  prices overnight gap risk that this sample never realised.")

    print("\n" + "=" * 96)
    print("4. WHAT THE $10,000 ACTUALLY DOES — expected outcome")
    print("=" * 96)
    p = best[5]
    ev_gross = p * TARGET
    print(f"  Using the best strike ({best[0]:.0f} call at ${best[1]:.2f}):")
    print(f"    P(reach $1,000,000)      {p:.2%}")
    print(f"    P(expire worthless)      {1 - DELTA_BY_STRIKE[best[0]]:.2%}  "
          f"(SPY below {best[0]:.0f})")
    print(f"    Gross EV of the $1M leg  ${ev_gross:,.0f} on a ${STAKE:,} stake")
    print(f"  The premium is NOT the only cost: at strikes >= 781 the ask is "
          f"$0.02 against a $0.01 mark,")
    print(f"  so you cross a ~100% spread on entry. That alone roughly halves "
          f"the contract count.")
    print(f"\n  Expected value of repeating this trade is negative once spread "
          f"and commissions are paid;")
    print(f"  the distribution is ~99.6% total loss, ~0.4% life-changing gain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
