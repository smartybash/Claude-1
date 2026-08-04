# Deviations from spec — sweep/run intraday build

Same discipline as the earlier momentum spec: every place the implementation
had to guess or diverge from the prompt, listed plainly.

1. **Data depth is 10–12 sessions, not the 2–3 years specified.** This is the
   dominant deviation and it drives the NOT-VALIDATED verdict. Cause, verified,
   not assumed: (a) no local TWS/Gateway in this container — API ports
   7496/7497/4001/4002 all closed, so the `ib_async` deep fetch cannot connect;
   (b) the IBKR MCP connector hard-caps historical requests at 1000 bars with
   no backward-paging parameter. 1000 five-minute RTH bars ≈ 12 sessions. Per
   the program's rule, reported and stopped rather than fabricated.
   `scripts/fetch_intraday.py` is the spec-faithful path to real depth once run
   where TWS lives.

2. **Data source is the IBKR MCP `get_price_history`, not `ib_async` directly.**
   The spec names `ib_async`. `ib_async` needs a socket to TWS that does not
   exist here. The MCP tool hits the same IBKR back end and is the only working
   historical source in this environment, so it was used for the caching layer;
   `ib_async` is used in `fetch_intraday.py` exactly as specified for the
   depth-fetch that must run elsewhere.

3. **Futures intraday series is a single front-month contract, not continuous.**
   For the 10-session diagnostic the front Sep-2026 NQ/ES contract was pulled
   directly. Its span contains no roll, so no roll-jump exclusion was needed
   here. The spec's continuous-vs-stitched requirement is honored in
   `fetch_intraday.py` (uses `ContFuture` = continuous; writes roll-date files
   for exclusion). Stated in the report as required.

4. **Equal-H/L pools built on daily pivots, not intraday pivots.** The spec's
   pivot definition is instrument-agnostic; with only ~10 intraday sessions,
   intraday swing pools would be trivially small and unstable, so pools are
   built from confirmed daily swing pivots (k=2) over the last ~20 sessions —
   which is also what the live screener needs pre-open. The same
   `sweeplib.levels.swing_pivots` function serves both parts, as the spec asks.
   NQ/ES have only 61 daily bars, so their pools are shallower than QQQ/SPY's;
   noted here as a known limitation, not tuned around.

5. **Round-number grid is auto-scaled to live price, not hardcoded.**
   `levels.round_step` picks 250 / 50 / 10 point spacing by price magnitude, so
   it adapts to NQ vs ES vs ETF scale and to future price drift, per the spec's
   "don't hardcode last session's levels."

6. **Confirmation on the touch bar itself is permitted for all K (j=0..K).**
   The spec defines K=0 as "the touch bar's own close decides it." I extended
   the same rule to K≥0: a sweep can confirm on the touch bar if that bar closes
   back inside. This is *not* the same-bar-definition bug — the touch is defined
   by the bar's high/low, the return is measured from that bar's close forward,
   so definition and outcome never share data. Documented and audited (99/99
   NQ trades causal). If a reviewer prefers strictly-next-bar entry, set the
   confirmation to require j≥1; it was left inclusive because that is the
   literal reading of the K=0 case.

7. **Re-entry is off.** The spec flags this as an explicit decision, not a
   silent default. Chosen: one entry per level per session, no re-entry, and
   re-entry is deliberately excluded from the walk-forward grid. This keeps the
   multiplicity count honest (6 tests/instrument).

8. **Targets: only flat-EOD is implemented and tested.** The spec says test the
   flat-EOD control first ("since it's the simplest") and lists opposite-level /
   trailing-stop variants as the fuller menu. Only the control is built, because
   adding target variants would multiply the test count on a sample already too
   small to support the base case — that would worsen, not fix, the multiplicity
   problem. Target variants are left for after real depth exists.

9. **Costs use a stated conservative default, not API-reached commissions.** The
   MCP surface does not expose per-contract MNQ/MES commission. Defaults: 1.0 bp
   round-trip for NQ/ES, 0.5 bp for QQQ/SPY, reported at 0.5×/1×/2×. Stated as a
   default per the spec's fallback instruction.

10. **`--live` screener path is written but unrun here** (no TWS). Only the
    `--replay` and `--selftest` paths were executed in this environment; both
    pass and exercise the full engine + alert path. The live path mirrors the
    replay path bar-for-bar.

11. **POC computed from 5-min bars, not tick data.** The volume profile spreads
    each 5-min bar's volume uniformly across the price bins its range spans
    (50 bins/session). True tick-level profile would place the POC more
    precisely; at 5-min the POC is approximate. Documented; unavoidable without
    tick data.

12. **POC/VAH/VAL side assigned by prior close.** POC is an in-range magnet with
    no fixed pre-session approach direction, so `poc_session_levels` assigns
    side (and thus touch direction) by position vs the prior close — the same
    convention already used for round numbers and prior-week levels. An
    alternative is to track both-direction touches per level; not done, to keep
    one entry per level and the multiplicity count honest.

13. **POC levels are NOT merged into coincident structural levels.** So the
    category breakdown can compare POC vs PDH/PDL cleanly, a POC that sits on
    top of (say) PDH is kept as a separate level. Rare in the sample; noted
    because it can double-count a touch when two categories overlap.
