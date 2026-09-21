# Trendline reversal — CLOSED. Rejected as evidence.

Source: a Reddit post. Not owned or run by us. No Pine source, no live alerts,
no complete trade CSV are obtainable. **Assessment closed on the evidence
already held.** No further work is possible or planned.

---

## What was established

1. The bounded reconstruction tested **nine plausible causal specifications**
   (pivot left/right 2/2, 3/3, 5/5 × stop 0.5, 1.0, 1.2 × ATR14), with
   TP fixed at 1.2 × ATR14 as disclosed.
2. It **matched the published trade frequency of 28.6 trades per session**
   (pivot 3/3, stop 1.2 — 28.6 exactly).
3. It **matched the reported ATR-based target size of ~31–33 points**,
   consistent with 1.2 × ATR14 and with the published 31.5-point average win.
4. It **approximately matched the reversal-affected share of 20–21%**
   (pivot 5/5, stop 1.2 — 21.1% against the published 20.4%).
5. **Despite matching those structural characteristics, all nine optimistic
   (Model A) reconstructions were negative** — −$4,919 to −$63,710, expectancy
   −0.18 to −2.35 points per trade against a published +7.99.
6. **Under tick-accurate execution with commission and one tick each side,
   zero of nine were positive.** Best profit factor anywhere was 1.03 against
   a 1.15 bar.
7. **Reverse-on versus reverse-off moves the published result from strongly
   positive to negative** (+$63,414 to −$14,158 at 2 MNQ; +$317,070 to
   −$70,790 at 1 NQ). The $77,572 swing is **122.3% of net profit**, carried by
   438 of 2,147 trades — **44.28 points per affected trade**, which is 1.77× the
   median five-minute intrabar directional run and sits at its 80th percentile.
8. **The published notes state explicitly that intrabar entry inflated dollars
   by a median 4.3× versus the no-lookahead run**, with bar-close entry matching
   the honest run.
9. **The strategy permits same-bar exit and re-entry at a trendline price
   crossed before the prior trade exited.** In the one supplied trade sample
   this occurred 4 times with a non-zero gap and was **favourable on all four**,
   worth 22.4% of that day's P&L. An unbiased artefact would be adverse about
   half the time.
10. **Therefore the published performance is not independently reproducible and
    is highly dependent on optimistic intrabar execution assumptions.**

---

## Final classification

# REJECT AS EVIDENCE

This does **not** prove that every possible causal version of the underlying
trendline concept loses money. The true pivot settings, the stop multiplier and
the slope convention remain unknown, and the reconstruction was bounded by
design.

It means **the Reddit backtest cannot support a trading decision**, and no
further work is possible without the actual strategy source or a trade-level
export.

---

## Ledger entry

| field | |
|---|---|
| **Claim** | Trendline reversal strategy: 57% win rate, profit factor 1.72, 7.99 gross points per trade |
| **Finding** | Bounded reconstruction matched frequency, target scale and reversal share, but failed under every causal execution model — 0 of 9 positive optimistically, 0 of 9 positive tick-accurate after commission |
| **Primary failure mode** | Same-bar intrabar fills and reversal ordering |
| **Verdict** | **Published result rejected as execution-model dependent and not independently replicable** |
| **Reopen only if** | Pine source or a complete TradingView trade CSV becomes publicly available |

---

Standing constraints honoured throughout: sealed NQ days unread, **2016–2020
unread and unspent**. Nothing in this family was ever a candidate, and nothing
here justifies opening the holdout.

Evidence: `reports/trendline_reversal_mechanics.md`,
`reports/trendline_reversal_verdict.md`, `reports/trendline_recon_verdict.md`,
`reports/trendline_recon.csv`, `reports/trendline_recon_output.txt`.
