# Order-flow batch: classification, definitions and bar — fixed before any result

Written and committed **before a single test is run**. Nothing below was chosen
with knowledge of an outcome.

---

## Provenance, fixed for every run in this batch

**Sessions — the 16 explored-pile dates at true 0.25:**

```
20260701 20260702 20260706 20260707 20260708 20260709 20260710 20260713
20260714 20260715 20260716 20260717 20260720 20260721 20260812 20260820
```

**Resolution:** 0.25 price grid, verified per file by the smallest non-zero gap
between distinct traded prices.

**Recorder versions:** 2026-09-16.r through 2026-09-17.z for the July dates;
the two August dates predate that lineage and are the original 0.25 captures.
Every file carries its own `#fmt=` header or is plain CSV; the loader reports
which.

**Sealed and not touched by anything in this batch:**
`20260618 20260622 20260623 20260624 20260625 20260626 20260629 20260630`
and the four remaining coarse sealed dates. No sanity check, no calibration,
no peek.

Every result table in this batch reprints the date list, the resolution and the
recorder lineage. A result without them is not reported.

---

## Part 1 — classification of every previous kill

### Group 1 — CLOSED. Resolution cannot touch these.

**Thirteen strategies from the long-history backtests**: ICT prior-day sweep and
reclaim, NWOG weekend gap fade, 15-minute ORB with FVG, Initial Balance
breakout, VWAP retest, MAGS/SMH/IGV breadth veto, value-area fade, VA fade with
wide-IB filter, fixed-level fade in all variants, the 1,421-session level fade,
gap fill against gap size, the open drive, and the 2,680-session structure
timeframe test.

*Reason:* every one was computed from Alpha Vantage bar data — daily and
one-minute OHLCV — and never touched the ATAS tape. There is no ATAS price
grid in them to be coarse. This is checkable: the scripts read
`data/*.json` and `data/intraday*`, not `data/tape`.

**CVD level gate and CVD change gate.**
*Reason:* both are computed from signed volume — trade size multiplied by the
aggressor flag — summed over a window. Neither reads a price distance anywhere.
A 5-point grid changes which price a trade is stamped at; it does not change
its size or its side. The arithmetic is identical on either grid.

**Order-size gate (25+ and 50+ lot net delta).**
*Reason:* same. It counts contracts in orders above a size threshold and signs
them by aggressor. Size and side are exact on both grids.

**Footprint levels / heavy-level revisits.**
*Reason:* killed by a **placebo**, not by a measurement. The real level and a
price shifted 25 points away paid the same or better. Both arms sit on the same
grid and are quantised identically, so coarseness cannot create the null — it
would have to make a real level look like an arbitrary price, and the arbitrary
price won.

**The lookahead, the overlap inflation, the impossible fill, the overfit
threshold.**
*Reason:* these are not hypotheses, they are bugs found in my own method. The
findings they invalidated were withdrawn because the arithmetic was wrong, and
correct arithmetic on coarse data is still correct arithmetic.

### Group 2 — NOT SAFE. Killed on data since shown to be coarse or shadowed.

**BOOK ladder-imbalance family in `filter_survey.py`.**
*Reason:* it ran on the July/August depth files, all of which are on the
5-point grid. Every threshold in it is expressed in **levels**, so "imbalance
over the top N levels" spanned N × 5.00 points rather than N × 0.25. At ten
levels that is 50 points of book, not 2.5 — not a touch measure at all but a
whole-range one, under a name that says otherwise. The verdict was reached on a
quantity the label does not describe.

**Footprint bar-shape study — `absorb_lo`, `absorb_hi`, `poc_pos`, `unf_net`.**
*Reason:* each is defined at "the bar's extreme price". On a 5-point grid the
extreme is a five-point bucket holding up to twenty real prices, so absorption
at the low and continuation two points above it fell in the same cell and
cancelled. The null calibration and the points test were both run correctly —
on a feature that could not express what it was named for.

### Group 3 — VERDICT MAY STAND, REASONING DID NOT. Test specification was inadequate.

**Order-book imbalance over ten levels, and depth-beyond-the-touch.**
*Reason:* the resolution was right — ladder reach of 12 points over ~48 levels
is 0.25 arithmetic, and a 5-point grid would have given 240. So this is not
Group 2. It is Group 3 because the sample was **four sessions**, and the
nested-subset table that produced the "monotonic degradation" conclusion was
**one session**. A clean ordering across five nested measures on one day is a
description of that day. The conclusion may well be right; one session cannot
establish it.

**Absorption properly instrumented, and cancellation alone.**
*Reason:* same four sessions, same problem. Reported at t = +1.50 and t = −0.91,
neither of which distinguishes a small effect from none at that sample size.
The measurement was sound and the sample could not carry the claim.

**Sweep depth gating.**
*Reason:* already established in the resolution audit and the reason this batch
exists. 94–97% of multi-fill aggressive orders reported zero price span,
because their fills fell inside one 5-point bucket. The gate was mechanically
off almost always, so its failure carries no information about sweeps. Counted
here as never measured rather than killed.

---

## Part 2 — what is in this batch

The four never-measured families, plus Groups 2 and 3. Group 2's BOOK family
and Group 3's book-imbalance work are the same quantity measured properly, so
they are tested once, not twice.

| # | family | source |
|---|---|---|
| A | footprint diagonal imbalance | never measured |
| B | stacked imbalance | never measured |
| C | sweep depth from per-fill detail | never measured |
| D | book imbalance at real tick distance | never measured + Group 2 BOOK + Group 3 |
| E | footprint absorption at the true extreme | Group 2 |
| F | absorption and cancellation, pull vs fill | Group 3 |

---

## Part 3 — exact feature definitions, fixed now

Bars are **5 minutes**, RTH only, 13:30–20:00 UTC. All features are computed
from prints and book states inside the bar and are known at its close.

**A. Diagonal imbalance.** For each traded price `p` in the bar, buy volume at
`p` against sell volume at `p − 1 tick` (0.25). Imbalanced when the ratio is
≥ 3.0 and the larger side is ≥ 10 contracts. Sell imbalance is the mirror:
sell at `p` against buy at `p + 1 tick`.
- `A1 imb_net` = (buy-imbalanced prices − sell-imbalanced prices) / traded prices in the bar
- `A2 imb_extreme` = imbalance count in the top quarter of the bar's range minus the bottom quarter, normalised the same way

**B. Stacked imbalance.** Longest run of consecutive imbalanced prices, same
side, using A's definition.
- `B1 stack_net` = (longest buy run ≥ 3) − (longest sell run ≥ 3), as −1/0/+1
- `B2 stack_len` = signed longest run length, buy positive

**C. Sweep depth, from the per-fill rows.** An aggressive order's sweep depth is
`|last fill price − first fill price| / 0.25`, in ticks, now that fills are
individually recorded.
- `C1 sweep_net` = signed contracts in orders with sweep depth ≥ 2 ticks, divided by bar volume
- `C2 sweep_deep` = signed contracts in orders with sweep depth ≥ 8 ticks, divided by bar volume

**D. Book imbalance at real tick distance.** From the reconstructed book at the
bar's close, `(bid size − ask size) / (bid + ask)` within a price distance, not
a level count.
- `D1 imb_touch` = within 1.00 point of the touch
- `D2 imb_5pt` = within 5.00 points of the touch

**E. Footprint absorption at the true extreme.**
- `E1 absorb_net` = (buy volume at the bar's lowest traded price − sell volume at the highest) / bar volume
- `E2 unf_net` = (low printed both sides) − (high printed both sides), as −1/0/+1

**F. Absorption and cancellation.** Size that left the touch price, split into
what trades consumed and what was cancelled, over the bar.
- `F1 pulled_net` = (bid size cancelled − ask size cancelled) / bar volume
- `F2 filled_net` = (bid size filled − ask size filled) / bar volume

**Twelve features. Two per family. No sweeps, no threshold searches.** Where a
threshold appears (3.0 ratio, 10 contracts, 3 in a row, 2 and 8 ticks, 1.00 and
5.00 points) it is the conventional value a footprint or DOM trader would use,
not one chosen from this data.

---

## Part 4 — the bar, fixed now

**Primary horizon: the next 15 minutes.** One horizon, counted once per
feature. 30 minutes is printed alongside as description only and is **not** a
test and **not** counted.

**Twelve tests.** That is the multiple-testing burden, stated before any result
exists. Bonferroni gives each test p < 0.0042, which on 16 sessions is about
**|t| ≥ 3.0**.

To be called a live candidate a feature must clear all three:

1. **|t| ≥ 3.0** on the information coefficient, computed once per session and
   the t taken across the 16 sessions — never across bars.
2. **Beat its own null.** The same feature scored against returns circularly
   shifted within each session. If the null throws up something as strong, the
   count of survivors is what chance produces here.
3. **Pay in points.** Top and bottom quintile, 15-minute hold, after 2 points
   of cost, per-session mean positive. Every correlation in this project that
   reached this step has died at it.

A feature clearing 1 and 2 but failing 3 is **not** a finding; it is reported as
a correlation that does not trade.

**Power, stated in advance.** Sixteen sessions is not many. If the true effect
is the size of anything seen so far in this project, this batch will most
likely return nothing, and that null will be weak evidence rather than strong.
A null result here means "not visible at this sample size", not "absent". I
will say which of those two a null is when it arrives, and will not present a
failure to detect as a refutation.

---

## Part 5 — the recommendation this batch must produce

One of:

- **something clears the bar** → finish the re-record, the order-flow branch is
  alive; or
- **nothing clears it and the sample is the binding constraint** → finishing the
  re-record is the only way to settle it, and the cost is known; or
- **nothing clears it and the effects are far too small for more sessions to
  rescue** → the order-flow branch is done, move to the pullback work.

The third is a real possible answer and will be given if the numbers support it.
