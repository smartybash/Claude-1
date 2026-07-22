# Dubai Islands – pricing overview & benchmarking (refreshed)

Updated benchmarking slides for a **new launch on Dubai Islands**, in the same format as the
2024 Bay Apartments benchmarking pack. Two scenarios:

- **Slide 1 – non-branded launch** (product similar to Bay Apartments)
- **Slide 2 – branded launch** (Rixos-tier product)

## Files
| File | What it is |
|---|---|
| `Dubai_Islands_benchmarking.pptx` | The two benchmarking slides |
| `Dubai_Islands_DLD_transactions.xlsx` | Underlying DLD benchmark data + recent-launch tracker + indicative pricing |
| `build_benchmark.js` | Regenerates the .pptx (`node build_benchmark.js`, needs `pptxgenjs`) |
| `build_workbook.py` | Regenerates the .xlsx (`python build_workbook.py`, needs `openpyxl`) |

## Data basis
- **DLD-registered transactions only** (via Bayut / Property Finder), trailing 12 months, as at **Jul-2026**.
  No broker asking prices, no "starting-from" launch quotes, no hearsay.
- Core DLD figures (registered counts, average registered prices) are as recorded with the
  Dubai Land Department. Cells marked **(e)** are per-sq.ft / size figures estimated from DLD
  average tickets and published unit sizes where the portal did not expose an average psf directly.
- The **"Indicative"** subject columns are analytical pricing scenarios built from the benchmarks —
  they are **not** live registered projects.

## Known limitation (read before publishing)
Row-level (per-transaction) DLD data could **not** be pulled from within the build environment —
Bayut, Property Finder, propsearch, dxbinteract and the DLD / Dubai Pulse portals all block
automated access. The benchmarking therefore uses **project-level DLD aggregates** as the
transaction basis. The `Recent launches (<=9m)` tab lists sub-9-month Dubai Islands launches
(Helvetia Marine, Bay Estates Ph.1, Wynwood, Seaside) whose **registered per-sq.ft must be
refreshed from your DLD / Property Monitor export** before the pack is circulated.

To upgrade to full row-level backing, export transactions with:
`Project | Building | Developer | Branded | Registration date | Unit type | Internal sq.ft | Sellable sq.ft | Price AED | AED/sq.ft | Off-plan/Ready | DLD ref`
