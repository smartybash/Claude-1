const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

// ---------- palette (restrained corporate, matching original "Internal" paper) ----------
const NAVY = "1F3864";      // subject bar / headers
const STEEL = "8FA3C0";     // DLD comps
const LIGHT = "C9D2E0";     // references / market
const HOLLOW = "E4E9F1";    // launched / no-DLD
const INK = "1A1A1A";
const MUTE = "5A6472";
const BORDER = "C7CDD6";
const BOXHEAD = "1F3864";
const TINT = "F4F6FA";

const MX = 0.35;            // left margin
const W = 13.3 - 2 * MX;    // content width

function boxLabel(slide, x, y, w, text) {
  // section header label sitting on the top border of a bordered box (like original)
  slide.addText(text, {
    x: x + 0.12, y: y - 0.13, w: 3.6, h: 0.26, align: "left",
    fontFace: "Calibri", fontSize: 10, bold: true, color: BOXHEAD,
    fill: { color: "FFFFFF" }, margin: 2,
  });
}
function borderedBox(slide, x, y, w, h) {
  slide.addShape(pres.ShapeType.rect, {
    x, y, w, h, fill: { color: "FFFFFF" },
    line: { color: BORDER, width: 0.75 },
  });
}

// ---------- generic slide builder ----------
function buildSlide(cfg) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };

  // classification + title
  slide.addText("Classification: Internal", {
    x: MX, y: 0.10, w: 6, h: 0.22, fontFace: "Calibri", fontSize: 9, color: MUTE, margin: 0,
  });
  slide.addText(cfg.title, {
    x: MX, y: 0.30, w: W - 0.6, h: 0.5, fontFace: "Calibri", fontSize: 24, bold: true, color: INK, margin: 0,
  });
  slide.addText(cfg.subtitle, {
    x: MX, y: 0.80, w: W - 0.6, h: 0.24, fontFace: "Calibri", fontSize: 11, italic: true, color: NAVY, margin: 0,
  });

  // ===== Overview box =====
  const ovY = 1.18, ovH = 1.78;
  borderedBox(slide, MX, ovY, W, ovH);
  boxLabel(slide, MX, ovY, W, cfg.overviewLabel);
  slide.addText(cfg.bullets.map((t, i) => ({
    text: t, options: { bullet: { indent: 12 }, breakLine: true, paraSpaceAfter: 3 },
  })), {
    x: MX + 0.15, y: ovY + 0.15, w: W - 0.3, h: ovH - 0.22,
    fontFace: "Calibri", fontSize: 8.5, color: INK, valign: "top", margin: 2, lineSpacingMultiple: 0.96,
  });

  // ===== Competitor benchmarking box (chart + data table) =====
  const bmY = 3.04, bmH = 2.60;
  borderedBox(slide, MX, bmY, W, bmH);
  boxLabel(slide, MX, bmY, W, "Competitor benchmarking");

  // chart (avg AED/sqft sellable), single series, per-point colors
  const cats = cfg.comps.map(c => c.short);
  const vals = cfg.comps.map(c => c.psf == null ? 0 : c.psf);
  const colors = cfg.comps.map(c => c.color);
  slide.addChart(pres.ChartType.bar, [{
    name: "AED/sqft sellable", labels: cats, values: vals,
  }], {
    x: MX + 0.10, y: bmY + 0.20, w: W - 0.20, h: 1.30,
    barDir: "col", chartColors: colors, barGapWidthPct: 45,
    showTitle: false, showLegend: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 8,
    dataLabelColor: INK, dataLabelFontBold: true, dataLabelFormatCode: "#,##0",
    valAxisHidden: true, valGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: cfg.axisMax,
    catAxisLabelColor: INK, catAxisLabelFontSize: 7.5, catGridLine: { style: "none" },
    catAxisLabelFontFace: "Calibri", catAxisLineShow: true,
  });

  // data table beneath chart
  const rows = [];
  const hdr = [{ text: "", options: { fill: { color: "FFFFFF" }, border: noB() } }]
    .concat(cfg.comps.map(c => ({
      text: c.name, options: {
        fontFace: "Calibri", fontSize: 6.5, bold: true, color: c.subject ? NAVY : INK,
        align: "center", valign: "middle", fill: { color: c.subject ? TINT : "FFFFFF" }, border: cellB(),
      },
    })));
  rows.push(hdr);
  const metricRows = [
    ["Avg AED / sq.ft sellable", cfg.comps.map(c => c.psf == null ? "n/a" : fmt(c.psf))],
    ["DLD transactions (12m)", cfg.comps.map(c => c.tx == null ? "–" : c.tx)],
    ["Avg unit size (sq.ft)", cfg.comps.map(c => c.area == null ? "n/a" : fmt(c.area))],
    ["Avg ticket (AED m)", cfg.comps.map(c => c.ticket == null ? "n/a" : c.ticket)],
    ["Status / basis", cfg.comps.map(c => c.status)],
  ];
  metricRows.forEach(([label, arr]) => {
    const r = [{ text: label, options: {
      fontFace: "Calibri", fontSize: 6.8, bold: true, color: MUTE, align: "left",
      valign: "middle", fill: { color: TINT }, border: cellB(),
    } }].concat(arr.map((v, i) => ({
      text: String(v), options: {
        fontFace: "Calibri", fontSize: 6.8, align: "center", valign: "middle",
        color: cfg.comps[i].subject ? NAVY : INK, bold: cfg.comps[i].subject,
        fill: { color: cfg.comps[i].subject ? TINT : "FFFFFF" }, border: cellB(),
      },
    })));
    rows.push(r);
  });
  const nCol = cfg.comps.length;
  const firstW = 1.55;
  const colW = [firstW].concat(Array(nCol).fill((W - 0.2 - firstW) / nCol));
  slide.addTable(rows, {
    x: MX + 0.10, y: bmY + 1.56, w: W - 0.20, colW,
    rowH: [0.26, 0.14, 0.14, 0.14, 0.14, 0.14], valign: "middle", margin: 1,
  });

  // ===== Indicative pricing box (typology table) =====
  const ipY = 5.74, ipH = 1.50;
  borderedBox(slide, MX, ipY, W, ipH);
  boxLabel(slide, MX, ipY, W, "Indicative pricing – subject scheme");

  const th = (t) => ({ text: t, options: {
    fontFace: "Calibri", fontSize: 6.8, bold: true, color: "FFFFFF", align: "center",
    valign: "middle", fill: { color: NAVY }, border: cellB(),
  } });
  const typeHdr = ["Typology", "Units", "Mix %", "Avg internal (sq.ft)", "Avg sellable (sq.ft)",
    "Sales value (AED m)", "Mix by value %", "Min (AED m)", "Avg (AED m)", "Max (AED m)",
    "AED/sq.ft internal", "AED/sq.ft sellable"].map(th);
  const tRows = [typeHdr];
  cfg.typology.forEach((row, ri) => {
    const isTot = ri === cfg.typology.length - 1;
    tRows.push(row.map((v, ci) => ({
      text: String(v), options: {
        fontFace: "Calibri", fontSize: 6.8, bold: isTot || ci === 0 ? true : false,
        align: ci === 0 ? "left" : "center", valign: "middle", color: INK,
        fill: { color: isTot ? TINT : "FFFFFF" }, border: cellB(),
      },
    })));
  });
  const tColW = [1.05, 0.55, 0.55, 0.95, 0.98, 1.02, 0.92, 0.82, 0.82, 0.82, 1.02, 1.05];
  // scale to width
  const sum = tColW.reduce((a, b) => a + b, 0);
  const scaled = tColW.map(c => c * (W - 0.2) / sum);
  slide.addTable(tRows, {
    x: MX + 0.10, y: ipY + 0.14, w: W - 0.20, colW: scaled,
    rowH: 0.185, valign: "middle", margin: 1,
  });

  // footnote
  slide.addText(cfg.footnote, {
    x: MX, y: 7.28, w: W, h: 0.20, fontFace: "Calibri", fontSize: 6.5, color: MUTE, italic: true, margin: 0,
  });
}

function noB() { return [{ type: "none" }, { type: "none" }, { type: "none" }, { type: "none" }]; }
function cellB() { return [{ type: "solid", color: BORDER, pt: 0.5 }, { type: "solid", color: BORDER, pt: 0.5 }, { type: "solid", color: BORDER, pt: 0.5 }, { type: "solid", color: BORDER, pt: 0.5 }]; }
function fmt(n) { return n.toLocaleString("en-US"); }

// ================= SLIDE 1: NON-BRANDED =================
buildSlide({
  title: "Pricing overview and benchmarking – non-branded launch",
  subtitle: "Indicative new non-branded multi-family launch on Dubai Islands (scenario, benchmarked to DLD-registered transactions, as at Jul-2026)",
  overviewLabel: "Pricing and benchmarking overview",
  bullets: [
    "The indicative scheme comprises 296 apartments across a mid-rise plot on Dubai Islands, with a total sales value of AED 1,122m equating to AED 2,602 per sq.ft of sellable area. This positions a new non-branded launch c.21% above the 2024 Bay Apartments pricing (AED 2,145) and c.11% above the current Dubai Islands off-plan average (AED 2,340 per sq.ft, mid-2025), consistent with the island's continued price appreciation.",
    "Dubai Islands off-plan apartments registered an average of AED 2,162 per sq.ft in 2024, rising to AED 2,340 per sq.ft by mid-2025; H1-2025 recorded over 2,075 units transacted for c.AED 5.6bn. All-property average registered price on the island is AED 3.49m (DLD, trailing 12 months).",
    "Active non-branded DLD benchmark: Bay Grove Residences (Nakheel) has 298 apartments registered with DLD at an average of AED 3.14m (trailing 12 months, +1% over the last 6 months) and Bay Grove Residences B has 200 apartments registered at an average of AED 3.32m. Per-sq.ft figures marked (e) are derived from DLD average tickets and published unit sizes.",
    "Recent (≤9-month) launches on the island – Helvetia Marine by DHG (Jan-26), Bay Estates Ph.1 by Nakheel (Mar-26), Wynwood by Imtiaz and Seaside by Prestige One – are listed in the accompanying transaction workbook; their registered per-sq.ft data is still accumulating and should be refreshed from DLD/Property Monitor before publication.",
  ],
  axisMax: 3200,
  comps: [
    { short: "Indicative\nnon-branded\n(subject)", name: "Indicative non-branded launch", subject: true, color: NAVY, psf: 2602, tx: null, area: 1458, ticket: "3.79", status: "Scenario (2026E)" },
    { short: "Bay Grove\nResidences", name: "Bay Grove Residences (Nakheel)", color: STEEL, psf: 2460, tx: 298, area: 1276, ticket: "3.14", status: "DLD 12m (e psf)" },
    { short: "Bay Grove\nResidences B", name: "Bay Grove Residences B (Nakheel)", color: STEEL, psf: 2510, tx: 200, area: 1322, ticket: "3.32", status: "DLD 12m (e psf)" },
    { short: "Dubai Islands\noff-plan avg", name: "Dubai Islands off-plan avg", color: LIGHT, psf: 2340, tx: null, area: null, ticket: "n/a", status: "DLD mkt (mid-25)" },
    { short: "Bay Apts\n2024 (base)", name: "Bay Apartments 2024 (base)", color: HOLLOW, psf: 2145, tx: 296, area: 1458, ticket: "3.1", status: "Prior launch (Oct-24)" },
  ],
  typology: [
    ["1 bedroom", 108, "36.5%", "790", "883", "262.4", "23.4%", "2.1", "2.43", "2.8", "3,076", "2,750"],
    ["2 bedroom", 60, "20.3%", "1,118", "1,371", "217.8", "19.4%", "3.1", "3.63", "4.2", "3,247", "2,648"],
    ["2 bed + maid", 88, "29.7%", "1,348", "1,772", "389.8", "34.7%", "3.8", "4.43", "5.2", "3,286", "2,500"],
    ["3 bedroom", 36, "12.2%", "1,893", "2,318", "212.8", "19.0%", "5.0", "5.91", "7.0", "3,122", "2,550"],
    ["4 bedroom", 4, "1.4%", "2,756", "3,604", "39.6", "3.5%", "8.5", "9.90", "11.2", "3,592", "2,747"],
    ["Overall", 296, "100.0%", "1,180", "1,458", "1,122.4", "100.0%", "2.1", "3.79", "11.2", "3,205", "2,602"],
  ],
  footnote: "Source: DLD-registered transactions via Bayut / Property Finder (trailing 12 months, as at Jul-2026). Subject column is an indicative scenario constructed from these benchmarks, not a live project. (e) = per-sq.ft estimated from DLD average ticket and published unit sizes. See accompanying transaction workbook for the underlying DLD data and recent ≤9-month launches.",
});

// ================= SLIDE 2: BRANDED =================
buildSlide({
  title: "Pricing overview and benchmarking – branded launch",
  subtitle: "Indicative new branded multi-family launch on Dubai Islands (Rixos-tier scenario, benchmarked to DLD-registered transactions)",
  overviewLabel: "Pricing and benchmarking overview",
  bullets: [
    "The indicative branded scheme comprises 150 larger-format apartments and penthouses, with a total sales value of AED 863m equating to AED 3,332 per sq.ft of sellable area. This prices a branded launch c.28% above the parallel non-branded scenario (AED 2,602 per sq.ft) and broadly in line with the Dubai-wide branded-residence average of AED 3,289 per sq.ft, while remaining below Palm Jumeirah and Jumeirah Bay branded pricing.",
    "On-island branded benchmark: Rixos Dubai Islands Hotel & Residences (Nakheel / Accor) has 29 apartments registered with DLD at an average of AED 6.25m (trailing 12 months); the mix includes beach houses and duplexes, so the per-sq.ft figure is estimated (~AED 2,900). Swissotel Waterfront Residences (Accor, 105 homes) has launched but registered resale volume remains thin.",
    "As there is no ≤9-month branded launch on Dubai Islands, recent branded waterfront comparables are used off-island: Emaar Beachfront apartments registered an average of AED 6.03m with DLD (trailing 12 months, +14% over 6 months) at c.AED 2,800-3,200 per sq.ft; Palm Jumeirah recorded 1,229 resales for AED 12.1bn (12 months to Nov-2025).",
    "Branded residences in Dubai command a c.42% premium over non-branded stock (AED 3,289 vs AED 2,220 per sq.ft, H2-2024). On Dubai Islands the premium is compressed to c.28-35% because the non-branded base (AED 2,340 per sq.ft) is rising quickly; the indicative branded premium reflects this while still capturing brand value.",
  ],
  axisMax: 4000,
  comps: [
    { short: "Indicative\nbranded\n(subject)", name: "Indicative branded launch", subject: true, color: NAVY, psf: 3332, tx: null, area: 1727, ticket: "5.75", status: "Scenario (2026E)" },
    { short: "Rixos Dubai\nIslands H&R", name: "Rixos Dubai Islands H&R (Accor)", color: STEEL, psf: 2900, tx: 29, area: 2156, ticket: "6.25", status: "DLD 12m · on-island (e psf)" },
    { short: "Emaar\nBeachfront", name: "Emaar Beachfront (branded, off-island)", color: STEEL, psf: 3000, tx: null, area: 2011, ticket: "6.03", status: "DLD 12m · off-island (e psf)" },
    { short: "Bay Grove\nResidences", name: "Bay Grove Residences (non-branded)", color: LIGHT, psf: 2460, tx: 298, area: 1276, ticket: "3.14", status: "DLD 12m · on-island" },
    { short: "Dubai Islands\noff-plan avg", name: "Dubai Islands off-plan avg", color: LIGHT, psf: 2340, tx: null, area: null, ticket: "n/a", status: "DLD mkt (mid-25)" },
    { short: "Dubai branded\nresi. avg", name: "Dubai branded-resi. avg", color: HOLLOW, psf: 3289, tx: null, area: null, ticket: "n/a", status: "Mkt report (H2-24)" },
  ],
  typology: [
    ["1 bedroom", 40, "26.7%", "780", "950", "133.0", "15.4%", "2.9", "3.33", "3.8", "4,263", "3,500"],
    ["2 bedroom", 45, "30.0%", "1,190", "1,450", "218.6", "25.3%", "4.2", "4.86", "5.6", "4,082", "3,350"],
    ["2 bed + maid", 30, "20.0%", "1,517", "1,850", "177.6", "20.6%", "5.1", "5.92", "6.9", "3,902", "3,200"],
    ["3 bedroom", 25, "16.7%", "2,010", "2,450", "199.1", "23.1%", "6.9", "7.96", "9.2", "3,962", "3,250"],
    ["4 bed / PH", 10, "6.7%", "3,200", "3,900", "134.6", "15.6%", "11.5", "13.46", "15.5", "4,205", "3,450"],
    ["Overall", 150, "100.0%", "1,417", "1,727", "862.9", "100.0%", "2.9", "5.75", "15.5", "4,061", "3,332"],
  ],
  footnote: "Source: DLD-registered transactions via Bayut / Property Finder (trailing 12 months, as at Jul-2026); Dubai branded-residence average from published market report (H2-2024). Subject column is an indicative scenario constructed from these benchmarks, not a live project. (e) = per-sq.ft estimated from DLD average ticket and published unit sizes.",
});

pres.writeFile({ fileName: "/tmp/claude-0/-home-user-Claude-1/456a4dde-a616-5eda-bbc4-16747b5cae37/scratchpad/Dubai_Islands_benchmarking.pptx" })
  .then(f => console.log("WROTE", f));
