# NQ Confluence — chart studies

Ports of the three-filter system (`scripts/three_filter_read.py`) onto broker charts.

| File | Platform | Language |
|------|----------|----------|
| `nq_confluence.ts`   | **ThinkOrSwim** | thinkScript |
| `nq_confluence.pine` | **TradingView** | Pine v5 |

> ThinkOrSwim runs **thinkScript**, not Pine — use the `.ts` file there. The `.pine`
> file is only for TradingView.

## What it draws
- **Zones** (FILTER 1) — red = resistance, green = support. *Manual inputs, updated daily.*
- **Macro bias** (FILTER 2) — daily 10/20 SMA → label UP/DOWN/MIXED; gates every signal.
- **VWAP ± σ bands** (FILTER 3) — the stretch (`(close−VWAP)/σ`) shown in the status label.
- **Regression channel** — trailing linreg ± σ (breakout / tap-retrace context).
- **Signals + alerts**, trend-aligned only:
  - **FADE** ▽/△ — tag a trend-aligned zone **and** ≥0.5σ stretched (mean-reversion).
  - **BREAK** ✕ — a close **through** a trend-aligned level, with trend (continuation).

## Load
- **ToS:** Studies → Edit Studies → Create → paste `nq_confluence.ts` → apply to a **30-min /NQ (or /MNQ)** chart. Right-click the study → *Create alert* on the plots if you want push alerts.
- **TV:** Pine Editor → paste `nq_confluence.pine` → Add to chart (30-min **NQ1!/MNQ1!**) → set alerts from the four `alertcondition`s.

## Update the zones each morning
Run `python3 scripts/three_filter_read.py` and copy the zone rows into the Z1/Z2/Z3 inputs
(hi, lo, is-resistance). Example — **2026-07-31**:

| input | hi | lo | resistance? |
|-------|----|----|-------------|
| Z1 (A+ breakdown shelf) | 28763 | 28701 | yes |
| Z2 (DENSE support)      | 28254 | 28178 | no |
| Z3 (DENSE support)      | 28111 | 27990 | no |

## Caveats (read once)
- Zones, and the `shelf` source behind them, are computed in Python — the study can't
  rebuild them, so you paste them in daily. Everything else (bias, VWAP σ, channel, signals)
  is native and live.
- The channel here is a **trailing** linear regression; the Python version anchors at the
  current leg's origin. Close enough on-chart, not identical.
- Signals are decision prompts, not auto-orders. The edge that backtested is **fade only when
  stretched** and **break only with trend** — the script encodes exactly those.
