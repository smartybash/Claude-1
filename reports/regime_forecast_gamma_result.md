# Dealer gamma: 0 of 4 on the regime, best-in-project on volatility

Pre-registered at `dd6e7ea`
(`reports/regime_forecast_gamma_preregistration.md`) before this ran.
Descriptive. **No rule was traded. The 6-variant stage-2 budget is unspent.**

Sealed NQ days were not read.

---

## 1. The hypothesis: 0 of 4

323 sessions carrying both a gamma row from the immediately preceding session and
a measurable outcome. Per year: 2021 (12), **2022 (0)**, 2023 (13), 2024 (12),
2025 (133), 2026 (153).

| criterion | bar | cleared |
|---|---|---|
| Spearman \|ρ\| | ≥ 0.10 | **0 of 4** |
| p-value | < 0.002778 | **0 of 4** |
| decile spread | ≥ 0.020 | **0 of 4** |

### Efficiency after D — the thing the hypothesis needs

| predictor | window | n | Spearman | p | Pearson | spread |
|---|---|---|---|---|---|---|
| net_gex | OR15 | 323 | −0.001 | 0.982 | −0.013 | −0.0066 |
| dist_flip | OR15 | 323 | +0.027 | 0.632 | +0.011 | −0.0034 |
| net_gex | OR30 | 323 | +0.026 | 0.640 | +0.025 | −0.0006 |
| **dist_flip** | **OR30** | 323 | **+0.076** | 0.173 | +0.075 | **+0.0076** |

Largest effect in the grid: **ρ = 0.076**, against a significance gate that needs
**0.167** at this sample size, and a decile spread of **0.0076** against a bar of
0.020. Nothing is close, and nothing reaches nominal significance uncorrected.

The declared 2025–2026 robustness read — named in the pre-registration as a
diagnostic so it could not be introduced afterwards — shows the same: ρ of
−0.008, −0.002, +0.021, +0.045 across the four combinations.

The best decile ladder in the grid, `dist_flip` at OR30, is a flat line:

| decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean eff_later | .0568 | .0613 | .0689 | .0671 | .0663 | .0786 | .0654 | .0729 | .0748 | .0644 |

**Combined with the original run: 0 of 18 combinations, across two genuinely
independent predictor families — price structure and dealer positioning.**

---

## 2. The positive control, which is the interesting half

Same code, same timestamp, same 323 sessions, outcome swapped to later realised
volatility:

| predictor | window | Spearman | p | later vol, d1 → d10 |
|---|---|---|---|---|
| **net_gex** | OR15 | **−0.520** | 1.1e-27 | **95.3 → 50.6 bps** |
| dist_flip | OR15 | −0.474 | 5.0e-22 | 94.0 → 62.5 bps |
| net_gex | OR30 | −0.501 | 3.6e-25 | 88.0 → 47.2 bps |
| dist_flip | OR30 | −0.454 | 6.7e-20 | 87.1 → 58.8 bps |

**Most-negative-gamma sessions run 1.9× the later volatility of
most-positive-gamma sessions** — 95 bps against 51. The sign is right: negative
gamma means dealers amplify, and it shows up as expansion.

This is a **stronger** separation than the daily finding already on record
(1.85% vs 1.24% next-day range, a ratio of 1.49). Measuring it post-decision
intraday rather than close-to-close sharpens it.

### It beats the free price-based predictor, and it is not the same information

I told the user before running this that gamma "would have to beat a free
predictor we already have." **On the same 322 sessions it does, clearly:**

| predictor | ρ vs later volatility |
|---|---|
| `rv_open` — opening-window realised vol, free from price | +0.445 |
| `or_ratio` — opening range vs trailing mean, free from price | +0.335 |
| **`net_gex` — dealer gamma** | **−0.521** |
| `dist_flip` — distance to the gamma flip | −0.474 |

And it survives controlling for the price predictor almost intact:

| | |
|---|---|
| partial rank corr(net_gex, rv_later **given rv_open**) | **−0.439** |
| partial rank corr(rv_open, rv_later **given net_gex**) | +0.335 |

Gamma keeps 0.44 of its 0.52 after the price predictor is removed. **The two are
complementary, not redundant** — gamma is carrying volatility information that
opening-window price action does not contain.

A caveat that keeps this honest: net gamma is partly a *state* variable that
tracks the volatility regime directly (negative-gamma periods coincide with
selloffs). It is legitimately forecasting — it is known before the open — but it
is reading the regime more directly than opening-window RV manages, rather than
seeing something price cannot in principle reflect.

---

## 3. Correction to what I told the user

Before running, I said gamma "would have to beat a free predictor you already
have, at forecasting the quantity that doesn't move R-multiples, while not
touching the quantity that does."

**The first clause was wrong.** Gamma does beat the free predictor, decisively
and with largely independent information. The rest held: it forecasts volatility,
not trend-vs-chop.

---

## 4. What this settles, and what it does not

**Settled — gamma cannot serve as a regime filter for these rules.** The regime
these continuation rules need is trend-vs-chop, measured as post-decision
efficiency. Gamma predicts it at ρ = 0.08 and a decile spread of 0.008. Nothing
in 18 combinations across two predictor families predicts it at all, and the
earlier work showed the dispersion in session efficiency is ~91% reproducible by
random walks in the first place.

**Reinforced — gamma is the best volatility forecaster this project has.** ρ =
−0.52, beating everything derived from price, and largely orthogonal to it. That
strengthens the case for what is *already* shipped: the expected-move band scaled
by gamma tercile (×1.20 / ×1.00 / ×0.80) in `gamma_context.gamma_em_mult`.

**But the structural limit is unchanged, and it is why this does not become a
strategy.** The rules are R-normalised: stop = 1.0 ATR, target = 3R. If a session
is twice as volatile, the ATR is wider, the stop is wider and the target is wider
— the R-multiple distribution is untouched. **An excellent volatility forecast is
still close to a no-op for a strategy denominated in R.** Its value is in position
sizing, expected-move bands and the cost hurdle, not in expectancy.

The one genuine expectancy channel is cost: cost is fixed in points while risk
scales, so a 1.9× wider session cuts cost/risk by nearly half. At the observed
~5% cost/risk that moves a 3R breakeven win rate by roughly half a percentage
point. Real, measurable, and far too small to rescue a rule that is already at or
below its random-walk rate.

### Not ruled out

- Gamma at a **different resolution** — intraday gamma updates rather than one
  daily figure from the prior close.
- Gamma against a **different regime definition** than efficiency. Any such test
  has to explain why it is not just re-measuring volatility, which is already
  known to be forecastable and already known not to move R-multiples.
- **The 2022 gap.** Any stage 2 would need the missing chains fetched first; the
  year-stability rule cannot be applied to a sample with a year absent, and that
  is a thing to fix rather than waive.

---

## 5. Where the ledger stands

| screen | sample | outcome |
|---|---|---|
| pullback, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| ORB + VWAP, QQQ screen | 1,418 sessions, 16 variants | closed, 0 of 16 |
| OR height, promoted | 1,418 + 1,256 held out, 4 variants | closed, 0 of 4 |
| European session, descriptive | 21 NQ sessions | same market, worse terms |
| regime forecastability, price | 1,418 sessions, 14 combinations | closed, 0 of 14 |
| discretionary strategy, mechanised | 1,417 sessions, 8 variants | closed, 0 of 8 |
| **regime forecastability, gamma** | **323 sessions, 4 combinations** | **closed, 0 of 4** |

Reproduce: `python3 scripts/orderflow/regime_forecast_gamma.py`.
Summary in `reports/regime_forecast_gamma_summary.csv`.
