# GEX backtest — does the real dealer-gamma regime predict the next day?

First test on REAL gamma (not a proxy): Alpha Vantage premium `HISTORICAL_OPTIONS`
chains for QQQ, 31 sampled sessions Oct-2025..Aug-2026 (19 negative-gamma, 12
positive-gamma). Per session we compute net GEX / gamma-flip (`av_gex.py`); the
chain's OI is as-of the close so it sets the NEXT day's open. We then measure
that next day's realized behavior (`backtest_gamma_filter.py`).

Gamma is about MAGNITUDE, so the metrics are next-day range, net open->close
travel, and efficiency (trend-iness).

| next-day metric | NEG-gamma | POS-gamma | diff | Welch t |
|---|---|---|---|---|
| **range %** | **1.68** | 1.32 | +0.36 | **1.77** |
| \|open->close\| % | 0.78 | 0.60 | +0.19 | 0.98 |
| efficiency | 0.49 | 0.43 | +0.06 | 0.58 |

Split-half (range): first half NEG 1.65 vs POS 1.25 (+0.40); second half NEG 1.69
vs POS 1.39 (+0.30) — **same sign both halves.**

## Verdict
- **SUPPORTED:** negative gamma -> **bigger-range / expansion** next day (~+0.36%/day
  on QQQ), and it's **stable across both halves** — the first gamma signal here that
  didn't sign-flip out of sample.
- **NOT supported:** that negative gamma gives a cleaner one-way **trend** or bigger
  net directional move (efficiency & open->close diffs are weak, t<1).

## How we use it (evidence-based, not Alex's stronger claim)
Gamma is a **volatility / expected-range switch, not a direction switch**:
- NEGATIVE gamma -> widen expectations: bigger EM, give trades room, fades can run
  further; don't assume a clean trend.
- POSITIVE gamma -> tighter/rangey: mean-reversion at the edges more reliable,
  breakouts stall.
Direction still comes from the rest of the stack (structure, VWAP, rotation, flow).

## Caveats
n=31 sampled (not consecutive) sessions, QQQ only, costs not modelled. Directional
read, not proof. `av_gex --log` appends every future rerun to `gex_history.jsonl`,
so this strengthens over time and can be re-run with more sessions / other symbols.

## Follow-up: mining other chain features (backtest_gex_features.py)

- **Dealer delta -> direction: NULL.** Computed dealer delta was net-negative on all
  30 sampled days (assumption artifact, no variation) and its magnitude had ~0
  correlation with next-day return (corr +0.06). Not a usable directional signal.
- **Net GEX magnitude -> next-day range: clean DOSE-RESPONSE.** Terciles:
  most-negative **1.85%** > middle 1.55% > most-positive **1.24%** (monotone).
  corr(distance-below-flip, range) = **+0.40**. So the range edge is graded, not
  binary: the more negative / deeper below flip, the wider the next day.
- **Actionable:** scale the day's expected range by net GEX — most-negative ~1.85%
  QQQ vs most-positive ~1.24%. Direction still comes from elsewhere.

## EM band = VIX 1-sigma scaled by the gamma tercile (shipped)
The dose-response above is now wired into the pipeline. `gamma_context.gamma_em_mult`
reads live terciles from `gex_history.jsonl` and scales the VIX expected-move band:
most-negative tercile **x1.20**, middle **x1.00**, most-positive **x0.80**. The
scaled band shows in the confluence read, the ToS study, and the on-chart label.
Gamma stays a range switch, not a direction switch.

## Follow-up: mega-cap earnings nights widen the next session (backtest_earnings_range.py)
Tested the well-known idea on our own data: the QQQ session that reacts to an
AAPL / MSFT / NVDA report (post-market -> next day, pre-market -> same day; report
dates from AV `EARNINGS`).

| next QQQ session | range % | median |
|---|---|---|
| **earnings-reaction day** (n=61) | **1.926** | 1.749 |
| normal day (n=1191) | 1.591 | 1.361 |

Ratio **1.21x**, Welch t **+2.70**, split-half **1.20x / 1.22x** (both halves > 1).

- **SUPPORTED & stable:** mega-cap earnings nights run ~1.2x wider — and it's a
  **forward-known** amplifier (the calendar is public weeks ahead), unlike gamma
  which is only known one day out.
- **Shipped:** `earnings_mult()` widens the band **x1.20** on a reaction day and
  **stacks** with the gamma multiplier (e.g. a positive-gamma earnings day nets
  0.80 x 1.20 = 0.96). Reaction days come from `data/earnings_calendar.json`,
  refreshed by `earnings_cal.py` from AV `EARNINGS_CALENDAR`. AV's forward coverage
  is partial (as of 2026-08-10 it had NVDA 8/26, TSLA 10/21, GOOGL 10/28); missing
  names are simply absent (no widener) until AV populates them.

## Direction: is there a DIRECTIONAL edge in the chain? (backtest_direction.py)
Everything above is a range switch. This hunted the harder thing — next-day SIGN.
**Verdict: NO genuine directional edge in the daily chain summary. Do not ship one.**

At first glance two rules looked strong (positive-gamma "revert to flip" and
"revert to wall-channel center", both ~73% hit, t up to +2.5). Skew controls
killed them:
- The sample is **down-skewed** (P(up)=37%), so "always predict down" already
  hits 63% for free — that alone explains dealer-delta (63%) and any down-leaning
  rule.
- In **every** positive-gamma session spot was **above** the flip (spot>flip is
  essentially definitional for positive gamma), so the reversion rule made **zero
  up-calls** (n=0) — it only ever said "down" and rode the skew.
- The continuous check `corr(spot-vs-flip distance, next-day return)` in positive
  gamma is just **-0.12** (right sign, negligible size).
- Momentum control (yesterday persists) is null (47%, t~0), as expected.

So direction is NOT in this data. Direction should keep coming from: (1) the
trend/balance regime (`intraday_engine`), (2) the rotation/breadth leadership read
(`rotation.py`, already built), and (3) the gamma flip used **intraday** as a bias
pivot (above flip = favor longs at support; below = favor shorts at resistance) —
framed as context, not a mechanical daily trigger.
**Next real probe if we want to keep hunting direction:** 25-delta IV skew /
risk-reversal computed from the full AV `HISTORICAL_OPTIONS` chain we already
fetch — store per session and test ~50 sessions before trusting. Not shipped blind.

## "Fade the wall on range days, ride through on trend days" (backtest_wall_touch.py)
Tested the clean idea: at a wall, POSITIVE gamma (range) -> FADE, NEGATIVE gamma
(expansion) -> CONTINUE. Daily proxy on the 31 wall sessions (touch = next-day
High/Low reached the wall; fade/continue = where it closed vs the wall).

**Underpowered and, as far as it goes, leans AGAINST the "continue" half:**
- Only 13 touches in 31 sessions — because walls sit ~1-3% away and price rarely
  reaches them at daily resolution.
- POSITIVE-gamma touches: **n=1** (it faded). Positive-gamma/range days almost
  never reach the far wall — that's *why* they're range days. Distance check: on
  POS-gamma days the day-high sits a median 1.2% under the call wall and the
  day-low a median **4.3%** above the put wall (nowhere near it).
- NEGATIVE-gamma touches (n=12): faded **58%**, continued only **42%** — i.e. the
  wall mostly *held* even on expansion days, the opposite of "continue on trend."
  Consistent with the 90%/73% containment finding: walls are the range boundary
  and mostly reject.

**Structural nuance found:** which wall price approaches is regime-dependent (and
partly a directional confound) — POS gamma drifts up toward the CALL wall, NEG
gamma drives down into the PUT wall (NEG-gamma regimes coincide with selloffs).

**Verdict (daily):** daily data does NOT support the two-regime wall rule. See the
intraday follow-up below, which settles it.

## INTRADAY resolution + expanded sample (backtest_wall_touch_intraday.py — SETTLED)
Expanded to **123 consecutive Jan–Jun 2026 QQQ sessions** (walls+net_gex computed
from AV chains; 61 negative-gamma / 62 positive-gamma) and pulled QQQ **5-min RTH
bars** (AV `TIME_SERIES_INTRADAY`, monthly). For each session's next day we find
the first bar that TAGS each wall and classify reject vs continue over K=3/6/12
bars.

**The hypothesis is NOT supported — it's null-to-reversed:**

| K (mins) | POS-gamma reject% | NEG-gamma reject% | z (pos−neg) |
|---|---|---|---|
| 3 (15m) | 36% | 60% | −1.26 |
| 6 (30m) | 43% | 48% | −0.29 |
| 12 (60m) | 43% | 57% | −0.81 |
| 6, within 0.15% | 43% | 65% | −1.37 |

The idea predicts POS-gamma reject% **>** NEG-gamma (positive z). Every spec gives
a **negative** z (the opposite lean — negative-gamma tags reject slightly *more*),
and none is significant. At 30 min it's essentially a coin flip in both regimes
(43% vs 48%). So a wall tag behaves about the same regardless of gamma — **there
is no range-fades / trend-continues switch at the wall.**

**Also key, practically:** even across 123 sessions only **~37 tags** occurred —
the max-OI walls sit ~1–3% from spot, so price rarely reaches them intraday. The
tradeable event is rare, and when it happens gamma doesn't tell you fade vs break.
Net of everything: walls are best used as the **outer boundary of the confluence
map** (already shipped), not as a gamma-conditioned fade/continue trigger.
Data kept: 123-session walls in `gex_history.jsonl`, 5-min months in
`data/intraday/`, so this can be re-run/extended.

## Levels: dealer walls sharpen confluence (backtest_walls.py — SHIPPED)
Do the call/put walls act as next-day S/R? On QQQ (n=30):
- next-day **HIGH stayed <= call wall 90%** of the time (resistance cap),
- next-day **LOW stayed >= put wall 73%** (support floor), both contained 63%.
Price typically stops ~2% short of a wall, so walls are **outer range boundaries /
high-conviction caps**, not precise magnets (precise touch-and-reject needs
intraday data to confirm).

**Shipped:** `confluence.build_zones` now injects the dealer levels as heavy,
distinct sources — call wall `cWall` (3.0), put wall `pWall` (3.0), gamma flip
`gFlip` (2.5) — for both NQ and QQQ (QQQ's feed into the cross-ref too). A
structural swing that also sits at the call wall now clusters into a DENSE zone
(e.g. NQ 30074-30112 = 1h+4h swing + wkH + cWall), so the map upgrades exactly
where dealers are defending. This is the model-free half of Alex's wall read.

## Direction probe #2: 25-delta IV skew / risk-reversal (backtest_skew.py — PARKED)
Followed up the "next real probe" from the direction section. Built the skew
history properly: `av_skew.py` computes RR25 = IV(25d put) - IV(25d call) at the
~30-DTE expiry from the full AV `HISTORICAL_OPTIONS` chain; fetched **56 real QQQ
chains** (2026-04-10..06-30, one clean sample) into `skew_history.jsonl`.

RR25 -> next-day open->close return:

| RR25 tercile | mean next-day ret | P(up) |
|---|---|---|
| low  | +0.118% | 57% |
| mid  | +0.004% | 61% |
| high | +0.357% | 59% |

- corr(RR25, next-ret) = **+0.15** (weak contrarian: extreme hedging -> slight
  bounce), and the sign is **stable both halves** (+0.15 / +0.16) — but it's below
  the pre-registered bar (|corr|>0.25, monotone terciles), the terciles are
  U-shaped not monotone, and P(up) is flat across them.
- The **change** signal (d_RR25) is worse: corr +0.10 and it **sign-flips across
  halves** (-0.22 / +0.24) — unstable.
- Skew -> next-day **range** is also weak (corr +0.16).

**Verdict: no tradeable directional edge.** There's a faint, sign-stable
contrarian tilt from the skew *level* (extreme fear -> mild mean-reversion), but
too weak to mechanize on 56 sessions in one regime (post-April-vol, declining
skew). Kept the infrastructure: `av_skew.py` reads the SAME chain we already fetch
for GEX (zero extra fetches), so `skew_history.jsonl` keeps growing each rerun and
can be re-tested at n~150. Not wired into any trade rule. (One row, 2026-06-24,
interpolated to RR25=0 — a degenerate both-wings-equal artifact; harmless at n=56.)

## Other AV data assessed
- **News Sentiment — NOT usable as a daily signal.** QQQ returned ~3 articles over
  3 days and the items are descriptive/backward-looking ("QQQ ETF Gains 1.2%"),
  i.e. reverse-causal. Too sparse and lagging on an ETF ticker to mechanize.
- **Put/Call Ratio — parked** (user said forget PCR): contrarian PCR is a weak/noisy
  daily signal; live QQQ PCR ~0.95 is fine as passive chart context only.

## "Trade the transition": compression near strikes / expansion on escape (backtest_gamma_transition.py)
Tested the classic pin-then-expand mechanic on 123 Jan-Jun 2026 QQQ sessions
(5-min bars + flip/walls). Three parts:

- **Magnitude by regime — TRUE & already shipped.** Positive/high-gamma days are
  tighter, negative/low-gamma wider (net-GEX terciles 1.24% vs 1.85%). This is the
  reliable core and is already the gamma-scaled EM band.
- **Compression EXACTLY at a strike — NOT supported intraday.** dist-to-nearest
  heavy level vs forward 30-min range: corr only +0.11, terciles ~flat
  (0.37/0.36/0.41%). Compression is a regime property, not a strike-proximity one.
- **Expansion on flip ESCAPE — right sign, underpowered.** Range in the 30 min
  after price crosses the flip vs before: DOWN cross (into negative gamma)
  **1.30x** expand (n=10); UP cross (into positive gamma) **0.78x** contract
  (n=10). Mechanistically exactly the hypothesis, but only 20 flip-crosses in 123
  sessions (price usually stays one side of the flip), so suggestive, not
  significant.

**Usable form:** treat the gamma FLIP as the compression<->expansion line — below
it (negative gamma) favor trend-follow / wider targets; above it favor
fade-the-edges. Already reflected in the regime read + the plotted gFlip level and
the EM scaling. Not built into a mechanical flip-cross trigger (n=10 too thin);
keep logging flip-crosses to re-test as the sample grows.

## Does the clean VWAP + FVG strategy have a real edge? (backtest_vwap_fvg.py)
Mechanical spec on 123 sessions of real 5-min QQQ: bias off session VWAP, enter
aligned 3-bar FVGs, stop at the far gap edge, target M*risk. n=737 trades.

**No mechanical edge.** Break-even to negative at every target:
- 1.0R: 42% win, **-0.15R** avg (-111R)
- 1.5R: 37% win, **-0.07R**
- 2.0R: 34% win, **~0.00R**  (before costs; costs make it negative)

**Avoiding positive-gamma days does NOT help** (the specific ask): POS vs NEG
gamma are ~identical (e.g. 1.5R: POS -0.06R vs NEG -0.03R). No clean gamma no-go.
Longs≈shorts, AM≈PM.

**Confirmation candle = look-ahead trap.** Filtering on "entry bar closed in the
trade direction" while filling at the gap edge shows a fake 66% win / +0.67R —
but that uses the bar's close to bless an intrabar fill. Done right (enter at the
confirmation bar's CLOSE), it collapses to **50% win / +0.01R** (1R), breakeven.
Higher win% is buyable (confirm, or 1R targets) but it does NOT create positive
expectancy — the payoff shrinks to match.

**Only genuine (non-look-ahead) tilts, both weak:** bigger gaps beat smaller
(largest third +0.10R vs smallest -0.28R) and entries NEAR vwap beat far
(+0.08R vs -0.22R). Real and sensible, but ~+0.1R — likely eaten by costs; not a
standalone edge.

**Takeaway:** a simple-LOOKING discretionary chart is not a simple mechanical
edge. The profit on such setups lives in discretion (which gap, context/absorption,
skipping bad ones, exiting at VWAP/structure) that the mechanical rule doesn't
capture. Caveats: QQQ only, one gap/stop/target spec, idealized fills, no costs.

## Structure stops + realistic exits — a CONDITIONAL edge appears (backtest_vwap_fvg_v2.py)
v1's tight gap-edge stop was killing it. Re-ran with STRUCTURE stops (swing low/high
of prior 5 bars) and how the setup is really managed, on 123 QQQ sessions:

- CONTINUATION (with VWAP bias), fixed 2R: +0.05R — still ~flat.
- CONTINUATION, **ride to a VWAP-loss** (let winners run): the split by gamma is the
  find — NEGATIVE-gamma **+0.19R** (n=270, t +1.92, both split-halves + : 0.11 / 0.27)
  vs POSITIVE-gamma **-0.03R**. Trend-follow profile: 38% win, negative median,
  positive mean from rare big runners.
- REVERSION (fade back to VWAP): -0.02R, no edge.

**Synthesis (the actionable rule):** pool both confirmed expansion signals —
negative gamma OR a mega-cap earnings-reaction day — as "EXPANSION days":
  EXPANSION continuation-ride: **+0.20R, t +2.08** (n=290, 38% win)
  COMPRESSION (pos-gamma, no earnings): **-0.06R, t -0.68** (n=224)
Adding the independent earnings trigger nudged t 1.92 -> 2.08 in the same
direction — evidence it's a real regime effect, not a gamma-definition artifact.

**Honest caveats:** t barely > 2; profit is concentrated (top-3 neg-gamma trades =
~54% of that bucket's R) — inherent to trend-following but fragile at n~123. So:
promising and mechanistically coherent (it unifies everything that survived — the
gamma range/expansion switch + the earnings widener), but SUGGESTIVE, not proven.

**What it means:** the tradeable idea isn't "VWAP+FVG" flat — it's *trade FVG
continuation, let winners run, ONLY on expansion days; skip positive-gamma
compression days for this style.* This validates the "avoid positive-gamma days"
instinct for the ride-it style specifically, and is already reflected in the gamma
regime read (neg = give room/trend; pos = tighter/fade).
**Next review:** expand the sample (more expansion days: Jul-Aug 2026, 2025 H2) to
see if t holds and the concentration diversifies before trusting it live.

## Exit optimization for the FVG continuation trade (backtest_fvg_exits.py)
Same entries (structure stop), only the exit varies. On EXPANSION days (neg-gamma
or earnings reaction) vs COMPRESSION days, 123 QQQ sessions, n=601:

| exit | EXPANSION mean | win% | COMPRESSION mean |
|---|---|---|---|
| fixed 3R | **+0.182R** | 43% | -0.077R |
| vwapCross (ride) | +0.173R | 38% | -0.126R |
| half@1R + ride | +0.142R | 55% | -0.002R |
| fixed 2R | +0.100R | 44% | +0.001R |
| trailPrevLow | +0.119R | 39% | +0.136R |
| fixed 1R | +0.105R | 55% | +0.088R |

- The **let-it-run exits (3R / vwapCross) give the biggest expansion-vs-compression
  spread (~0.26-0.30R)** — confirms the mechanism: only expansion days follow
  through to far targets; compression days bleed. Regime filter matters MOST for
  runners.
- **half@1R+ride** is the practical pick: +0.14R on expansion at 55% win.
- fixed1R and trailPrevLow are mildly positive in BOTH regimes — tighter,
  regime-agnostic scalps (small, more cost-sensitive), a different animal from the
  expansion thesis.
- Carried forward to the out-of-sample test: fixed3R (max separation) + half@1
  (practical). All modest (~0.1-0.18R) so costs matter; the +0.17-0.18R runners
  have the most margin.

## Expanded / OOS test + NQ — data-availability status (partial)
Attempted the out-of-sample expansion and the NQ test. Data blockers hit:

- **OOS expansion (QQQ 2025 H2) — BLOCKED.** Needs new options chains to extend the
  net_gex regime, and the Alpha Vantage MCP server is disconnected. Resume when AV
  is back: fetch 2025 H2 + Jul-Aug 2026 chains (av_gex --log) + intraday months,
  then re-run backtest_vwap_fvg_v2 / backtest_fvg_exits on the combined ~250
  sessions to see if the expansion edge holds t>2 and de-concentrates.
- **NQ full test — BLOCKED for scale.** IBKR get_price_history caps at 1000 bars
  per call with no historical paging (~11-13 sessions/pull); AV has no futures. So
  no bulk NQ intraday history is available here.

**NQ transfer check (backtest_nq_check.py, 11 sessions Jul27-Aug10 2026, anecdotal):**
the strategy mechanics transfer cleanly and the character matches QQQ — half@1R+ride
**56% win / +0.07R** on NQ (vs QQQ 55%), VWAP-ride ~breakeven. BUT all 11 sessions
were positive-gamma (compression), so there were **zero expansion days** to test the
actual edge on NQ. Confirms the code/behaviour ports to the future; the expansion
edge on NQ still needs expansion days + more history (accumulate NQ pulls forward,
or use a futures-history provider).

## Where this leaves the strategy (interim)
- In-sample (123 QQQ sessions): a CONDITIONAL edge — FVG continuation, structure
  stop, let-winners-run, ONLY on expansion days (neg-gamma or earnings); +0.14 to
  +0.18R expansion vs ~0/negative compression. Suggestive (t~2), concentrated in a
  few trend days — NOT yet proven.
- Blocked on the two tests that would confirm/refute it (OOS + NQ) by the AV outage
  and IBKR's history cap. No live trading rule shipped on this until it clears OOS.

## Data hygiene + time-of-day (backtest_fvg_timeofday.py)
**Data is RTH-only, no after-hours noise** — every QQQ/NQ session is 09:30-15:55 ET
(~78 5-min bars), VWAP anchored to the 9:30 open (AV fetched with
extended_hours=false; NQ filtered to 09:30-15:59). Confirmed.

Time-of-day on the EXPANSION-day continuation trade refines the "first 2 hours"
idea: the **opening hour (9:30-10:30) is the WORST window** — negative across all
exits (half@1 -0.04R, vwapCross -0.14R/24% win, fixed2R -0.10R): opening noise,
unstable VWAP, whipsawed FVGs. The **10:30-11:30 hour is the single best**
(half@1 +0.31R/67% win). The afternoon is NOT weak (pm vwapCross +0.25R).

So the better filter is **skip the first hour**, not "trade only the first two."
Applying it lifts the expansion-day edge:
- half@1R+ride: +0.142R -> **+0.167R**
- vwapCross:    +0.173R -> **+0.219R**
Filter chosen in-sample (first-hour weakness is consistent across all 3 exits, so
plausibly real) — the pending out-of-sample run will judge whether it holds.

---

# OUT-OF-SAMPLE EXPANSION (2025-H2 backfill) — verdict

**Data added:** Alpha Vantage came back online; backfilled the gap.
- `gex_history.jsonl`: **134 → 279 sessions** (2025-07-01 … 2026-08-11), zero dups.
- `skew_history.jsonl`: 105 → 258 sessions.
- Intraday 5-min: added 2025-07…2025-12 (now a continuous 2025-07 → 2026-07, 13 months).
- All GEX logged with `av_gex --log` only; live `gamma_levels.json` untouched.

The 2025-H2 window is genuine out-of-sample: none of it informed the original
(2025-10-13→2026-08-07) in-sample tuning.

## What SURVIVED out-of-sample

**1. Negative-gamma → bigger / trendier next day — CONFIRMED and STRENGTHENED.**
`backtest_gamma_filter.py`, n 133 → **251** (109 neg, 142 pos):

| metric | NEG-γ | POS-γ | diff | Welch t (was) |
|---|---|---|---|---|
| next-day range % | 1.618 | 1.111 | +0.507 | **5.72** (3.80) |
| \|open→close\| %  | 0.847 | 0.558 | +0.289 | **3.68** (2.60) |

Holds in **both halves** (H1 diff +0.51, H2 +0.42). t=5.72 on n=251 is no longer
"suggestive" — this is the real, de-concentrated edge. The tell is the daily
*range/directionality*, not a specific entry.

**2. Skip the opening hour (9:30–10:30) — HOLDS.**
`backtest_fvg_timeofday.py`, expansion n 301 → **546**. The opening hour is the
worst bucket across all three exits OOS (half@1 **−0.023R**, vwapCross **−0.084R**,
fixed2R **−0.045R**); 10:30–11:30 is the best (half@1 +0.236R / 64% win). The
first-hour weakness reproduced cleanly out-of-sample.

## What BROKE out-of-sample

**3. The "only trade EXPANSION days" split — DID NOT HOLD.** This was the headline
in-sample edge and the one flagged as concentration-risky. In-sample, expansion
days dominated compression (e.g. fixed3R +0.182R exp vs −0.077R comp; vwapCross
+0.173R vs −0.126R). OOS on n=1020 entries the gap **collapsed**:

| exit | EXPANSION | COMPRESSION |
|---|---|---|
| fixed1R | +0.094R | +0.099R |
| fixed2R | +0.076R | +0.122R |
| trailPrevLow | +0.155R | +0.130R |
| half@1 | +0.107R | +0.065R |

Compression days are **just as tradeable** as expansion days out-of-sample. The
in-sample expansion premium was small-sample noise — the concentration worry was
correct. FVG continuation is a *mild all-days* edge (fixed3R +0.101R, trailPrevLow
+0.143R over n=1020), not a regime-gated one.

**4. "Trade only the first 2 hours (pm weak)" — DID NOT HOLD.** OOS the afternoon
is fine (half@1 pm +0.135R, vwapCross pm +0.156R). The correct rule is *skip the
first hour*, full stop — not "front-load the session."

## Secondary (`backtest_gamma_transition.py`, expanded)
- Flip-escape **DOWN into negative gamma** still expands: post/pre **1.20×** (n=26,
  was 1.30× n=10); up-crosses compress (0.69×). Directionally intact, de-concentrated.
- Compression-near-heavy-strikes: corr(dist, fwd 30-min range) +0.11 → **+0.21**,
  but bins only weakly monotonic (near 0.30% / mid 0.30% / far 0.39%). Weak support.

## Bottom line
- **Keep:** (a) negative-gamma regime as a *next-day range/trend expectation* filter
  (now strongly validated), (b) skip-the-first-hour on intraday FVG entries.
- **Drop:** gating FVG continuation on expansion-vs-compression days, and the
  "first-2-hours-only" timing — neither survived OOS.
- FVG continuation is a small positive edge every day; the gamma regime tells you
  *how far price is likely to travel*, not whether the FVG setup itself works.

---

## Chop-zone (range-compression) breakout — `backtest_range_breakout.py`

Prompted by the 2026-08-13 failure: fading the call wall lost because price had
compressed for several daily bars and then broke out and ran. Tests the break of
a multi-day range, mechanically, both sides. QQQ daily, 5y.

**Compression** = an N-day box (prior N daily highs/lows, excluding today).
Two definitions, same result:
- adaptive: box width in the bottom tercile of its trailing 60-day distribution
- ATR-native: box height ≤ k·ATR(14) — the only one thinkScript can compute, so
  it is the rule the chart ships.

**Breakout** = today trades beyond the box. Entry at the box edge, stop the far
side (risk = box height).

### The edge is real, and it wants a RUN-IT exit
| rule (5-day box, adaptive) | n | mean R | win% | t |
|---|---|---|---|---|
| measured move (1× box) | 246 | +0.129 | 56 | 2.05 |
| fixed 2R | 246 | +0.312 | 43 | 3.29 |
| **fixed 3R** | 246 | **+0.428** | 36 | **3.51** |
| trail prior bar | 246 | +0.186 | 54 | 4.64 |

ATR-native rule (what the ToS chart computes), 3R exit:
| N, k | n | 3R mean R | t |
|---|---|---|---|
| **N=5, box≤2.0·ATR** | 252 | **+0.362** | 3.04 |
| N=5, box≤2.5·ATR | 424 | +0.254 | 2.83 |
| N=10, box≤2.0·ATR | 15 | +0.067 | — (too few) |

The chart ships **N=5, box≤2.0·ATR, 3R / measured-move exit**. Higher payoff
targets beat tight ones — the opposite of the fade. **False-breakout rate ≈55%**
(price closes back inside the box within 3 days): you are wrong more than half the
time and the winners carry it. Wrong psychology for a fader; that is the point.

### Two things the data killed
- **Compression does NOT predict expansion.** Next-day range after a compressed
  box: 1.64% vs 1.93% normal (Welch t=−4.99). The tight range is *not* a coiled
  spring; it is only a clean place for a stop. **The break is the only trigger.**
  Reframe: fade the range *until* the box breaks, then flip to breakout-continuation.
- **Gamma squeeze — CANNOT CONFIRM.** Theory: a break in negative gamma / through
  a wall forces dealers to chase. On the 53 breakouts with a prior option read,
  negative-gamma breakouts made **−0.09R** vs positive-gamma **+0.16R** — the
  *wrong* direction, on a sample far too small to trust. The ToS chart therefore
  draws the squeeze *condition* as a labelled, unvalidated context flag for
  sizing only, **never as a buy/sell signal.** Shipping it as a signal would be
  inventing an edge the data does not support.

### Chart = backtest
`generate_tos_breakout.py` emits a DAILY study whose ThinkScript reproduces the
Python rule 1:1 (boxHi=`Highest(high[1],N)`, box≤`atrK·ATR(14)` Wilders, entry at
edge, stop far side, measured + 3R targets). One acknowledged difference: on an
outside bar that breaks both sides the same day, the backtest records both trades
while the chart's held-state picks the long. Rare; does not affect the edge.

### Follow-up: failed-break filter + direction (`backtest_failed_break_filter.py`)

**Q: does a FAILED poke on one side make the OTHER side's break run harder**
(trapped-trader / spring-upthrust)? **A: no.** Breakouts whose opposite side had
a failed poke within W days ("primed") did not beat the rest:

| within W days | primed n | primed 3R | un-primed 3R |
|---|---|---|---|
| W=3 | 42 | +0.333R (t 1.13) | +0.330R |
| W=5 | 55 | +0.236R (t 0.94) | +0.355R |

Primed ≈ un-primed at W=3 and *worse* at W=5, small n throughout. Filter dropped.

**But the test surfaced a real, bigger split — DIRECTION × EXIT:**
| dir | n | measured | 2R | 3R | trail |
|---|---|---|---|---|---|
| **long** | 140 | +0.150 | +0.485 | **+0.807 (t 4.79)** | +0.224 |
| **short** | 127 | **+0.172 (t 1.97)** | −0.001 | −0.195 (t −1.37) | +0.089 |

Long breakouts RUN — hold for 3R. Short breakouts only reach the measured move
(1× box) then get bought back — take the pop, do NOT hold a short for 3R.
Caveat: 5y of a QQQ bull tape, so the long bias is partly drift; treat NQ shorts
as lower-conviction too, but the exit asymmetry (shorts scalp, longs run) is the
usable rule. Now baked into `generate_tos_breakout.py`'s bubbles and labels.

### Breadth expansion — does the breakout edge GENERALISE? (QQQ + SPY + IWM)

Longer *calendar* history was not obtainable this session: Alpha Vantage is not
connected, FMP historical chart/index endpoints are plan-locked, and IBKR caps
daily bars at 5 years / 1000 per call. So instead of more QQQ years, the data
was expanded in BREADTH — SPY (large blend) and IWM (small cap) added at 5y
daily depth alongside QQQ (Nasdaq), all 2021-08-16 → 2026-08-13, ~1254 bars each.
This tests whether the edge is market-wide or a QQQ artifact.

**Shippable rule (N=5, box≤2.0×ATR, 3R exit) across instruments:**
| sym | n | meas R | 3R | t(3R) | falseBrk | LONG 3R | SHORT 3R |
|---|---|---|---|---|---|---|---|
| QQQ | 255 | +0.189 | +0.325 | 2.76 | 55% | +0.788 | −0.195 |
| SPY | 244 | +0.145 | +0.411 | 3.37 | 56% | +0.833 | −0.176 |
| IWM | 278 | +0.043 | +0.245 | 2.22 | 60% | +0.458 | +0.015 |
| **POOL** | **777** | +0.123 | **+0.323** | **4.81** | 57% | **+0.690** | **−0.111** |

The edge holds on all three tapes it was never tuned on (pooled t=4.81, far
stronger than any single instrument — the payoff of breadth). The **long > short
asymmetry is robust everywhere**: longs run to 3R on all three; shorts lose on
QQQ/SPY and are flat on IWM (small caps a touch more two-sided). Confirms a
market-wide breakout effect, not a QQQ artifact, and confirms the direction-aware
exit already on the chart (longs run, shorts scalp).

**Failed-break filter, pooled (n=812):** still dead. Primed (opposite side failed
within W days) +0.219R vs un-primed +0.361R at W=3; +0.237R vs +0.367R at W=5.
The null holds across markets — filter stays dropped.

### DEEP history — the edge over 27 years (Alpha Vantage full daily)

Alpha Vantage reconnected, so the daily history was extended from 5y to the full
series: QQQ & SPY 1999-11 → 2026-08 (6,736 bars each), IWM 2000-05 → 2026-08
(6,592). Stored as `data/<sym>_daily_full.json`; `load_daily` prefers it over the
5y file. This spans the dot-com bust, 2008 GFC, 2018, COVID-2020 and the 2022
bear — a real regime stress test, not just the recent bull tape.

**Shippable rule (N=5, box≤2.0×ATR, 3R) over ~27y:**
| sym | n | meas R | 3R | t(3R) | falseBrk | LONG 3R | SHORT 3R |
|---|---|---|---|---|---|---|---|
| QQQ | 1533 | +0.089 | +0.251 | 5.30 | 59% | +0.530 | −0.094 |
| SPY | 1542 | +0.044 | +0.136 | 2.97 | 61% | +0.345 | −0.165 |
| IWM | 1481 | +0.041 | +0.082 | 1.77 | 62% | +0.245 | −0.114 |
| **POOL** | **4556** | +0.058 | **+0.157** | **5.85** | 60% | **+0.375** | **−0.123** |

Verdict: the breakout edge **survives 27 years and three bear markets** — pooled
3R +0.157R/trade at t=5.85. It is *smaller* than the 5y bull-slice (+0.32R
pooled), which is the honest correction: the recent number was flattered by a
one-directional tape. The **long > short asymmetry persists WITH bears in the
sample** (long +0.375 vs short −0.123 pooled), so it is a structural property of
breakouts, not just drift — longs follow through, downside breaks get bought
back. Confirms the chart's direction-aware exit (longs run to 3R, shorts take the
measured move). N=5 stays the best box; the chart cites the 27y numbers now.

**Failed-break filter over 27y (n=4,582 pooled):** conclusively dead — primed
(opposite side failed within W days) +0.016R (t=0.30) vs un-primed +0.196R
(t=6.39). A recent opposite-side failure REMOVES the edge. Stays dropped.

### Daily FVG continuation over 27y (`backtest_daily_fvg.py`) — NEW, and the strongest daily edge

The daily FVG chart's edge previously had no committed backtest (numbers were
ad-hoc, 5y). Built `backtest_daily_fvg.py` reproducing the chart's exact rule
(3 open-gap slots per side, first touch of the near edge, WITH the 20SMA trend,
swing-K stop, maxStopATR=2.5) and ran it on the full ~27y history:

| bucket | n | 2R | 3R | t(3R) | trail |
|---|---|---|---|---|---|
| QQQ continuation | 433 | +0.322 | +0.476 | 5.14 | +2.55 |
| SPY continuation | 420 | +0.303 | +0.430 | 4.60 | +3.77 |
| IWM continuation | 418 | +0.288 | +0.372 | 4.01 | +2.72 |
| **POOL continuation** | **1271** | **+0.305** | **+0.427** | **7.95** | +3.01 |
| POOL long only | 799 | +0.415 | +0.563 | 8.16 | +3.26 |
| POOL short only | 472 | +0.119 | +0.196 | 2.33 | +2.59 |
| POOL FADE (vs trend) | 573 | −0.047 | +0.013 | 0.18 | +1.49 |

Verdict: daily FVG continuation is the **strongest daily mechanical setup we
have** — pooled 3R +0.427R at t=7.95, holding on all three instruments over 27y
incl. bears. **Fading is dead** (+0.013R, t=0.18), vindicating the chart's
continuation-only arrows. Same long-bias as the breakout (long +0.563 vs short
+0.196). The trail exit shows a much larger mean (~+3R) but that is inflated by
multi-month trend-rides with big variance; 2R/3R are the tradeable numbers.
Daily chart now cites these committed figures.

### Scope note — what the 27y pull can and cannot refine
The Alpha Vantage expansion is DAILY only. Daily strategies were re-validated on
it: chop-zone breakout and daily FVG (above), plus the direction/regime context.
The INTRADAY setups — the 5-min FVG continuation study and the confluence "A+"
zones — are anchored to session (5-min) data that is only ~weeks deep here, so
they cannot be pushed to 27y without a deep intraday pull. AV TIME_SERIES_INTRADAY
can extend 5-min history (bounded, ~2y via month slices) if we want to re-test
those next; noted as the follow-up, not done in this pass.

### Extended gamma history — refining the regime split (`backfill_gamma_history.py`)

The gamma history was ~1 year (279 daily QQQ reads, 2025-07+), so the regime
splits were underpowered (breakout gamma-split was n=53). Backfilled MONTHLY QQQ
option chains for 2023-01 → 2025-06 via AV HISTORICAL_OPTIONS (near-expiry,
near-money walls, same rule as av_gex). History is now **310 QQQ reads,
2023-01 → 2026-08**. `backtest_range_breakout.gamma_lookup` carries the most
recent read forward (≤40 days) so a monthly read tags every subsequent session
(the gamma regime changes slowly).

**Breakout by regime — the finding REVERSED with more data (n 53 → 184):**
| regime | n | trail mean | win% | false-breakout |
|---|---|---|---|---|
| NEG gamma (dealers amplify) | 63 | +0.237R | 65% | 46% |
| POS gamma (dealers dampen) | 121 | +0.145R | 45% | 64% |

At n=53 the split pointed the wrong way (neg −0.09 vs pos +0.16); at n=184 it
points the *right* way — **negative-gamma breakouts win more (65% vs 45%) and
fail far less (46% vs 64% false-breakout).** This tentatively rehabilitates the
"squeeze" intuition, but as a REGIME-SIGN filter, not a "through-a-wall" one
(punching through a wall was still weak: +0.11R vs +0.19R no-wall).

**Daily FVG continuation by regime (QQQ, n=59 tagged):** POS gamma +1.077R 3R
(t=3.14, n=34) vs NEG gamma +0.625R (t=1.57, n=25) — opposite lean to the
breakout, consistent with "continuation-with-trend works best on calm dampened
days," but n is small.

**Honest caveats:** (1) carry-forward means one monthly read tags ~20 sessions,
so these n's are inflated by clustering — the effective independent sample is
much smaller; treat as *suggestive*, not established. (2) The 2023-25 backfill is
monthly, not daily. Verdict: promising enough to **watch negative gamma as a
breakout quality filter** and keep continuation on positive-gamma days, but not
yet to hard-gate either. Denser backfill (weekly/daily) would settle it.

### Deep-intraday re-validation (~2 years) — 5-min FVG CONFIRMED, confluence "A+" NOT

Pulled QQQ 5-min from Alpha Vantage for 2024-07 → 2025-06 (extended_hours off) and
combined with the existing months: intraday now spans **2024-07 → 2026-07, ~2
years / 523 RTH sessions** (was ~weeks). `ingest_av_intraday.py` converts the AV
monthly payloads to data/intraday/qqq_5m_YYYY-MM.csv.

**5-min FVG (backtest_tos_fvg) — holds up strongly on 2y (n=1081):**
| exit (chart logic, most-recent gap) | mean R | t |
|---|---|---|
| trailPrevLow | +0.189R | 6.44 |
| fixed2R | +0.173R | 4.54 |
| fixed3R | +0.150R | 3.50 |
Chart logic (single most-recent gap, skip-first-hour) still beats multi-gap
(+0.189 vs +0.129 trail), and a tighter maxStopATR raises mean R (2.0→+0.226,
1.5→+0.291) at the cost of trades. Regime split ~even (NEG +0.423 / POS +0.409,
small n). Verdict: the 5-min FVG continuation edge is real and stable across ~2y.

**Confluence "A+" zones (backtest_confluence) — NOT validated on 2y:**
| bucket | hold-rate |
|---|---|
| A+ (score ≥8) & ≥2 sources | 82% |
| score <5 | 81% |
| lone (1 source) | 80% / ≥2 → 82% / ≥4 → 79% |
| **NULL (random levels)** | **87%** |

On 2 years the A+ score adds **no edge** — A+ zones hold 82% vs 87% for RANDOM
levels (i.e. slightly WORSE than luck), and score/source count barely move the
hold-rate. The earlier eye-catching "lone 64% vs ≥2 94%" gap was small-sample
noise; it collapses on the full sample. **The confluence scoring does not predict
which levels hold.** This matches the decision to keep the confluence zones
DEFAULT-OFF on the ToS studies — they should stay context-only, not a signal.
The validated levels remain the dealer-gamma walls/flip and the FVG/breakout
structure, not the confluence "A+" score. Confluence needs a rethink or retire.
(NQ/SPY HTF not extended — AV has no futures; SPY would need its own pulls.)

### Gamma backfill to 2020 — the neg-gamma breakout filter FIRMS UP (n=311)

Backfilled monthly QQQ gamma back through 2020-2021 (COVID + recovery) via AV
HISTORICAL_OPTIONS; history is now **334 QQQ reads, 2020-01 → 2026-08**
(2022 and part of 2021 still pending — AV dropped mid-batch). Re-running the
breakout regime split (carry-forward lookup):

| regime | n | trail mean | win% | false-breakout |
|---|---|---|---|---|
| NEG gamma | 119 | +0.177R | 63% | 46% |
| POS gamma | 192 | +0.112R | 43% | 67% |
| through a wall | 31 | +0.156R | 65% | vs +0.135R no-wall |

The split has now gone 53 → 184 → **311** as the history grew, and the finding
has only strengthened and stabilised: **negative-gamma breakouts win ~63% vs
43% and fail far less (46% vs 67% false-break)**, now across 2020-2026 incl. the
COVID shock. "Through a wall" even edged positive on the bigger sample. This is
strong enough to treat **negative gamma (price below the flip) as a breakout
QUALITY / SIZING filter — size up below the flip, smaller/cleaner-box only
above** — folded into generate_tos_breakout.py's regime labels. Caveat stands:
carry-forward (monthly reads tag ~20 sessions) inflates n via clustering, so it's
a sizing filter, not a hard gate. 2022 (the bear) still to be added when AV is
back — expected to reinforce the neg-gamma side further.

### Value-Area FADE (Flow-Zone setup) — `backtest_va_fade.py`

The user's setup: on a positive-gamma day, price makes ≥2 attempts at the prior
VAH (= call wall), fails, and rotates down POC → VAL (→ breakout). Short the VAH
rejection. Tested on QQQ 5-min RTH, 139 days (one trade/day = first VAH rejection
after 10:00 ET; prior-session VA from the 70% volume profile; stop above VAH).

| bucket | reach POC | reach VAL | target POC | target VAL |
|---|---|---|---|---|
| ALL | 63% | 35% | +0.33R (71% win) | +0.43R (53%) |
| POSITIVE gamma | 64% | 35% | +0.27R (71%) | +0.14R (46%) |
| NEGATIVE gamma | 61% | 34% | +0.42R (72%) | **+0.79R (61%)** |
| **≥2nd attempt ("2 pokes then fail")** | 67% | 33% | **+0.68R (73%)** | **+0.81R (52%)** |

Verdict — the setup is real, with two refinements to the thesis:
1. **The "2 attempts then fail" is the edge amplifier** (user's instinct, confirmed):
   the ≥2nd-poke rejection makes +0.68R to POC vs +0.23R for a 1st poke — roughly
   3× better. Wait for the second rejection.
2. **Target should follow the regime, not the label:** the fade-to-POC works in
   BOTH regimes (~71% win). But in POSITIVE gamma price PINS at POC — the run to
   VAL is weak (+0.14R). The full POC→VAL→breakout leg (the user's example) is
   actually NEGATIVE-gamma/expansion behaviour (VAL +0.79R). So: **pos gamma →
   target POC and expect the pin; neg gamma (or once VAL breaks) → let it run to
   VAL/breakout.** The example day was a pos-open that expanded — a transition.

Primary tradeable rule: short the 2nd VAH(call-wall) rejection after 10:00,
target POC; extend to VAL only if momentum/negative gamma. Stop above VAH.
(VAH≈call-wall confluence subset too small here, n≈2, to confirm separately.)
