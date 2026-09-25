# Study (e) — simple intraday rules: pre-registration

Registered **before any of these rules is run on any data**. Data roles and harness
as studies (c) and (d) (`reports/db_cd_preregistration.md`): the 2010–2020 decisive
block labelled *"never used for this hypothesis; read by other studies, incl. study
(b)"*; 2021 → registration seen and not decisive; forward data the only true
out-of-sample. NQ `ohlcv-1m`. Costs per side NQ $2.25 + 1 tick, MNQ $0.62 + 1 tick.
Entry at the next bar's open, honest stop fills, stop first, entry bar searched.
Random-direction null with mirrored geometry, 5,000 simulations. **Holm across the
four rules.** Kill criteria: Sharpe ≥ 0.8, profit factor ≥ 1.3, beats the null at
Holm p ≤ 0.05.

## Which rules reuse a frozen repository spec (run in step 4, not here)

| rule | repository spec reused |
|---|---|
| ADR / VWAP pullbacks | `pullback_preregistration.md`, `pullback_preregistration_v2.md`, QQQ-screen pullback grid |
| multi-day box (Donchian-style) breakout | archived daily range breakout (`2fed2b4`) |

## Four new frozen rules (no repository spec exists)

**ATR14** = mean of the prior 14 RTH daily true ranges. **Gap** = RTH open − prior
RTH close, same contract (sessions after a roll night are skipped). One trade per
rule per day. Flat at 15:59.

1. **Gap-and-go.** |gap| ≥ 0.5 × ATR14. If the first 5-minute bar (09:30–09:34)
   closes beyond the RTH open **in the gap direction**, enter in the gap direction
   at 09:35. Stop = that bar's opposite extreme. Target 2R.
2. **Gap-fade.** |gap| ≥ 0.5 × ATR14. If the first 5-minute bar closes back
   **against** the gap, enter against the gap at 09:35. Stop = that bar's extreme on
   the gap side. Target = the prior RTH close (the gap fill). Skipped if the target
   is less than 1R away.
3. **PDH/PDL breakout.** The first 1-minute close above PDH (below PDL) between
   09:45 and 14:59. Enter in the breakout direction at the next open. Stop = level
   ∓ 0.25 × ATR14. Target 2R.
4. **Intraday Donchian.** 5-minute RTH bars. Channel = high and low of the prior 20
   bars of the session, so the first signal is possible at 11:10. Signal = the
   first 5-minute close outside the channel. Enter at the next bar's open. Stop =
   channel midpoint at the signal. Target 2R.

These overlap closed families (opening range, reference levels, gap fill). The
prior is negative; the rules are run because you asked for them.
