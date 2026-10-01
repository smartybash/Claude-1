"""The evening workflow as one command: gamma screen CSV in, trade sheet out.

    python scripts/evening_scan.py data/gamma_screen_example.csv \
        --spy 0.8 --qqq 0.3 --bulls 420 --bears 120 --vix-delta -0.4

Loads the screen, runs the five entry filters over every name, reads the
three regime gates, and writes the evening report: the CONFIRMED list
(greenlit for tomorrow's open trigger), the PENDING watchlist, B
Continuation candidates, and a blocked summary. Percentages on the CLI are
in percent (0.8 = +0.8%); the HYG divergence flag halves new-entry sizing.

Omit the regime flags and the scan still runs — the report then marks the
gates unchecked and withholds approvals.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol_desk import (  # noqa: E402
    BLOCKED, CONFIRMED, PENDING, B_CONTINUATION, P2P,
    approve, continuation_eligible, read_gates, screen, size_factor,
)
from vol_desk.loader import load_gamma_screen  # noqa: E402


def fmt_row(row, res) -> str:
    rr = f"{res.rr:.2f}" if res.rr is not None else "—"
    tags = []
    if row.grade >= 11 and row.deep:
        tags.append("DEEP")
    if row.sustained:
        tags.append("SUSTAINED")
    return (f"| {row.symbol} | {row.spot:g} | {row.p_trans:g} | {row.plus_gex:g} "
            f"| {rr} | {res.cushion:.1%} | {row.grade} | {row.db_change:+.2f} "
            f"| {' '.join(tags)} |")


TABLE_HEAD = ("| Symbol | Spot | pTrans | +GEX | R/R | Cushion | Grade | dbChg | Tags |\n"
              "|---|---|---|---|---|---|---|---|---|")


def main() -> int:
    ap = argparse.ArgumentParser(description="Vol Desk evening scan")
    ap.add_argument("screen_csv", help="gamma screen CSV export")
    ap.add_argument("--spy", type=float, help="SPY session change, in percent")
    ap.add_argument("--qqq", type=float, help="QQQ session change, in percent")
    ap.add_argument("--bulls", type=int, help="bull names in the universe")
    ap.add_argument("--bears", type=int, help="bear names in the universe")
    ap.add_argument("--vix-delta", type=float, help="VIX dealer delta positioning")
    ap.add_argument("--hyg-bear", action="store_true",
                    help="HYG dealer positioning has gone bear (credit divergence)")
    ap.add_argument("-o", "--out", default=None,
                    help="report path (default reports/evening_scan_<date>.md)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="list every blocked name with its failed filters")
    args = ap.parse_args()

    rows = load_gamma_screen(args.screen_csv)
    results = [(r, screen(r)) for r in rows]
    confirmed = [(r, s) for r, s in results if s.status == CONFIRMED]
    pending = [(r, s) for r, s in results if s.status == PENDING]
    blocked = [(r, s) for r, s in results if s.status == BLOCKED]
    confirmed.sort(key=lambda rs: rs[1].rr or 0, reverse=True)

    regime_inputs = (args.spy, args.qqq, args.bulls, args.bears, args.vix_delta)
    gates = None
    if all(v is not None for v in regime_inputs):
        gates = read_gates(args.spy / 100, args.qqq / 100,
                           args.bulls, args.bears, args.vix_delta)

    lines = [f"# Vol Desk evening scan — {date.today().isoformat()}", ""]
    lines.append(f"{len(rows)} names screened: {len(confirmed)} CONFIRMED, "
                 f"{len(pending)} PENDING, {len(blocked)} BLOCKED.")
    lines.append("")

    # --- regime gates ---
    lines.append("## Regime gates")
    lines.append("")
    if gates is None:
        lines.append("Regime inputs not provided — gates unchecked, **no new-entry "
                     "approvals from this report**. Re-run with --spy/--qqq/--bulls/"
                     "--bears/--vix-delta.")
    else:
        mark = lambda ok: "PASS" if ok else "fail"
        ratio = args.bulls / args.bears if args.bears else float("inf")
        lines += [
            f"- Basket gate: {mark(gates.basket)} (SPY {args.spy:+.1f}%, QQQ {args.qqq:+.1f}%)",
            f"- Bull:Bear gate: {mark(gates.bull_bear)} ({ratio:.1f}:1)",
            f"- VIX delta gate: {mark(gates.vix)} (dealer delta {args.vix_delta:+.2f})",
            "",
            f"**{gates.count}/3** — P2P Track 1: "
            f"{'approved' if approve(P2P, gates) else ('strong setups only' if approve(P2P, gates, strong_setup=True) else 'NO new entries')}; "
            f"B Continuation: {'approved' if approve(B_CONTINUATION, gates) else 'NO new entries'}.",
        ]
        sf = size_factor(args.hyg_bear, equities_bullish=gates.count >= 2)
        if sf < 1.0:
            lines.append(f"HYG divergence: credit bear while equities bullish — "
                         f"size new entries at {sf:.0%}.")
    lines.append("")

    # --- confirmed ---
    lines.append("## CONFIRMED — greenlit for the open trigger")
    lines.append("")
    if confirmed:
        lines.append("Entry is the first 5-min candle close above pTrans, not the level.")
        lines.append("")
        lines.append(TABLE_HEAD)
        lines += [fmt_row(r, s) for r, s in confirmed]
    else:
        lines.append("None tonight.")
    lines.append("")

    # --- pending ---
    lines.append("## PENDING — within 0.5% below pTrans, watch the first candle")
    lines.append("")
    if pending:
        lines.append(TABLE_HEAD)
        lines += [fmt_row(r, s) for r, s in pending]
        lines.append("")
        lines.append("R/R re-checks at the confirming close.")
    else:
        lines.append("None tonight.")
    lines.append("")

    # --- B continuation ---
    cont = [(r, s) for r, s in results
            if continuation_eligible(r) and s.status in (CONFIRMED, PENDING)]
    lines.append("## B Continuation candidates (Minervini ≥ 100, needs 3/3 gates)")
    lines.append("")
    if cont:
        if gates is not None and not approve(B_CONTINUATION, gates):
            lines.append("**Gate is not 3/3 — no B entries today.** Structural candidates:")
            lines.append("")
        lines.append(TABLE_HEAD)
        lines += [fmt_row(r, s) for r, s in cont]
        lines.append("")
        lines.append("Confirm clean staircase structure on the chart before entry.")
    else:
        lines.append("None tonight.")
    lines.append("")

    # --- blocked ---
    lines.append("## Blocked")
    lines.append("")
    by_filter: dict[str, int] = {}
    for _, s in blocked:
        for f in s.failed_filters():
            by_filter[f] = by_filter.get(f, 0) + 1
    lines.append(", ".join(f"{k}: {v}" for k, v in sorted(by_filter.items()))
                 or "Nothing blocked.")
    if args.verbose and blocked:
        lines.append("")
        for r, s in blocked:
            lines.append(f"- {r.symbol}: failed {', '.join(s.failed_filters())}")
    lines.append("")

    report = "\n".join(lines)
    out = Path(args.out) if args.out else Path("reports") / f"evening_scan_{date.today():%Y%m%d}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report)
    print(f"\n[written to {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
