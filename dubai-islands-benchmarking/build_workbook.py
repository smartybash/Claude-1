import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = openpyxl.Workbook()
NAVY = "1F3864"; STEEL = "8FA3C0"; TINT = "F4F6FA"; MUTE = "5A6472"
hdr_font = Font(bold=True, color="FFFFFF", size=10)
hdr_fill = PatternFill("solid", fgColor=NAVY)
bold = Font(bold=True, size=10)
thin = Side(style="thin", color="C7CDD6")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")
ctr = Alignment(horizontal="center", vertical="center")


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def write_table(ws, start, headers, rows, colw=None):
    for j, h in enumerate(headers, 1):
        ws.cell(row=start, column=j, value=h)
    style_header(ws, start, len(headers))
    for i, r in enumerate(rows, start + 1):
        for j, v in enumerate(r, 1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.border = border
            cell.alignment = ctr if j > 1 else Alignment(vertical="center")
    if colw:
        for j, w in enumerate(colw, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w


# ---------------- Sheet 1: DLD benchmarks - non-branded ----------------
ws = wb.active; ws.title = "DLD benchmarks - non-branded"
ws["A1"] = "Dubai Islands – non-branded: DLD-registered transaction benchmarks (trailing 12 months, as at Jul-2026)"
ws["A1"].font = Font(bold=True, size=12, color=NAVY)
headers = ["Project", "Developer", "Branded?", "DLD registered txns (12m)", "Avg registered price (AED)",
           "Avg unit size (sq.ft)", "Avg AED/sq.ft (sellable)", "Basis / note"]
rows = [
    ["Bay Grove Residences", "Nakheel", "No", 298, 3137836, 1276, 2460, "DLD via Bayut; +1% over 6m; 1BR avg AED 2,084,000. Size & psf estimated (e)."],
    ["Bay Grove Residences B", "Nakheel", "No", 200, 3318110, 1322, 2510, "DLD via Bayut; size & psf estimated (e)."],
    ["Dubai Islands – off-plan apt avg", "— (market)", "No", None, None, None, 2340, "DLD market avg, mid-2025 (2,162 in 2024)."],
    ["Dubai Islands – all property avg", "— (market)", "Mixed", None, 3494007, None, None, "DLD all-property avg, trailing 12m."],
    ["Bay Apartments (prior launch)", "Subject – 2024", "No", 296, 3100000, 1458, 2145, "Client 2024 benchmarking base (Oct-24)."],
]
write_table(ws, 3, headers, rows, colw=[26, 16, 10, 14, 16, 13, 14, 46])
ws.cell(row=3+len(rows)+2, column=1,
        value="Note: figures marked estimated (e) are per-sq.ft/size derived from DLD average tickets and published unit sizes; "
              "core DLD counts and average prices are as registered.").font = Font(italic=True, size=9, color=MUTE)

# ---------------- Sheet 2: DLD benchmarks - branded ----------------
ws = wb.create_sheet("DLD benchmarks - branded")
ws["A1"] = "Branded residences: DLD-registered transaction benchmarks (trailing 12 months, as at Jul-2026)"
ws["A1"].font = Font(bold=True, size=12, color=NAVY)
headers = ["Project", "Developer / Brand", "Location", "DLD registered txns (12m)", "Avg registered price (AED)",
           "Avg unit size (sq.ft)", "Avg AED/sq.ft (sellable)", "Basis / note"]
rows = [
    ["Rixos Dubai Islands Hotel & Residences", "Nakheel / Accor (Rixos)", "Dubai Islands (on-island)", 29, 6253545, 2156, 2900,
     "DLD via Bayut; mix incl. beach houses/duplexes, psf estimated (e)."],
    ["Swissotel Waterfront Residences", "Accor (Swissotel) / The Summary", "Dubai Islands (on-island)", None, None, None, None,
     "Launched (105 homes); registered resale volume still thin."],
    ["Emaar Beachfront (branded towers)", "Emaar", "Dubai Harbour (off-island)", None, 6032330, 2011, 3000,
     "DLD via Bayut; +14% over 6m; psf c.2,800–3,200, estimated (e)."],
    ["Palm Jumeirah (branded benchmark)", "— (market)", "Palm Jumeirah (off-island)", 1229, None, None, None,
     "1,229 resales / AED 12.1bn, 12m to Nov-2025."],
    ["Dubai branded-residence average", "— (market report)", "Dubai-wide", None, None, None, 3289,
     "Branded avg AED 3,289 vs non-branded AED 2,220 (~42% premium, H2-2024)."],
]
write_table(ws, 3, headers, rows, colw=[34, 26, 24, 14, 16, 13, 14, 44])

# ---------------- Sheet 3: Recent launches <=9m ----------------
ws = wb.create_sheet("Recent launches (<=9m)")
ws["A1"] = "Dubai Islands – recent off-plan launches within ~9 months (context; refresh registered psf from DLD/Property Monitor)"
ws["A1"].font = Font(bold=True, size=12, color=NAVY)
headers = ["Project", "Developer", "Launched", "Product", "Handover", "Registered DLD psf", "Note"]
rows = [
    ["Helvetia Marine", "DHG Properties", "Jan-2026", "1–3BR + duplex/garden, ~100 units", "Q1-2028", "TO REFRESH", "Reported sold out at launch."],
    ["Bay Estates Phase 1", "Nakheel (Island E)", "Mar-2026", "3–7BR townhouses / beachfront villas", "n/a", "TO REFRESH", "From ~AED 4.7m; not apartments."],
    ["Wynwood", "Imtiaz", "late-2025 / early-2026", "1–4BR + duplex/PH", "Q3-2027", "TO REFRESH", "G+2P+14 residential."],
    ["Seaside", "Prestige One", "~2025 (borderline)", "1–3BR apartments", "Q4-2026", "TO REFRESH", "Units 1,203–2,442 sq.ft."],
]
write_table(ws, 3, headers, rows, colw=[20, 18, 20, 34, 12, 18, 30])
for r in range(4, 4+len(rows)):
    ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor="FFF2CC")
ws.cell(row=3+len(rows)+2, column=1,
        value="Registered per-sq.ft for these <=9-month launches is still accumulating and could not be retrieved from within this session "
              "(Bayut/Property Finder/DLD portals blocked). Populate 'Registered DLD psf' from your DLD / Property Monitor export.").font = Font(italic=True, size=9, color=MUTE)

# ---------------- Sheets 4 & 5: Indicative pricing ----------------
def indicative_sheet(name, title, rows):
    ws = wb.create_sheet(name)
    ws["A1"] = title; ws["A1"].font = Font(bold=True, size=12, color=NAVY)
    headers = ["Typology", "Units", "Mix %", "Avg internal (sq.ft)", "Avg sellable (sq.ft)",
               "Sales value (AED m)", "Mix by value %", "Min (AED m)", "Avg (AED m)", "Max (AED m)",
               "AED/sq.ft internal", "AED/sq.ft sellable"]
    write_table(ws, 3, headers, rows, colw=[14, 8, 8, 12, 12, 13, 12, 10, 10, 10, 13, 14])
    tot = 3 + len(rows)
    for c in range(1, 13):
        ws.cell(row=tot, column=c).fill = PatternFill("solid", fgColor=TINT)
        ws.cell(row=tot, column=c).font = bold

indicative_sheet("Indicative - non-branded",
    "Indicative pricing – non-branded subject scheme (Dubai Islands)",
    [
        ["1 bedroom", 108, "36.5%", 790, 883, 262.4, "23.4%", 2.1, 2.43, 2.8, 3076, 2750],
        ["2 bedroom", 60, "20.3%", 1118, 1371, 217.8, "19.4%", 3.1, 3.63, 4.2, 3247, 2648],
        ["2 bed + maid", 88, "29.7%", 1348, 1772, 389.8, "34.7%", 3.8, 4.43, 5.2, 3286, 2500],
        ["3 bedroom", 36, "12.2%", 1893, 2318, 212.8, "19.0%", 5.0, 5.91, 7.0, 3122, 2550],
        ["4 bedroom", 4, "1.4%", 2756, 3604, 39.6, "3.5%", 8.5, 9.90, 11.2, 3592, 2747],
        ["Overall", 296, "100.0%", 1180, 1458, 1122.4, "100.0%", 2.1, 3.79, 11.2, 3205, 2602],
    ])

indicative_sheet("Indicative - branded",
    "Indicative pricing – branded subject scheme (Dubai Islands, Rixos-tier)",
    [
        ["1 bedroom", 40, "26.7%", 780, 950, 133.0, "15.4%", 2.9, 3.33, 3.8, 4263, 3500],
        ["2 bedroom", 45, "30.0%", 1190, 1450, 218.6, "25.3%", 4.2, 4.86, 5.6, 4082, 3350],
        ["2 bed + maid", 30, "20.0%", 1517, 1850, 177.6, "20.6%", 5.1, 5.92, 6.9, 3902, 3200],
        ["3 bedroom", 25, "16.7%", 2010, 2450, 199.1, "23.1%", 6.9, 7.96, 9.2, 3962, 3250],
        ["4 bed / PH", 10, "6.7%", 3200, 3900, 134.6, "15.6%", 11.5, 13.46, 15.5, 4205, 3450],
        ["Overall", 150, "100.0%", 1417, 1727, 862.9, "100.0%", 2.9, 5.75, 15.5, 4061, 3332],
    ])

# ---------------- Sheet 6: Sources ----------------
ws = wb.create_sheet("Sources & method")
ws["A1"] = "Sources & method"; ws["A1"].font = Font(bold=True, size=12, color=NAVY)
notes = [
    "Data basis: DLD-registered transactions surfaced via Bayut / Property Finder (trailing 12 months, as at Jul-2026), plus published DLD market averages and a Dubai branded-residence market report (H2-2024).",
    "Registered figures (transaction counts and average registered prices) are as recorded with the Dubai Land Department. No broker asking prices, launch 'starting-from' prices, or marketing quotes are used.",
    "Cells marked (e) are per-sq.ft / average-size figures estimated from DLD average tickets and published unit sizes where the portal did not expose an average psf directly.",
    "Subject 'Indicative' schemes (non-branded and branded) are analytical pricing scenarios constructed from the benchmarks — they are NOT live registered projects.",
    "Recency: benchmarks reflect transactions registered within the trailing 12 months; the 'Recent launches (<=9m)' tab lists sub-9-month launches whose registered psf must be refreshed from your DLD / Property Monitor export.",
    "Limitation: row-level (per-transaction) DLD data could not be extracted from within this session because Bayut, Property Finder, propsearch, dxbinteract and the DLD/Dubai Pulse portals block automated access. Project-level DLD aggregates are used as the transaction basis.",
    "To upgrade to full row-level backing: export DLD/Property Monitor transactions with columns [Project | Building | Developer | Branded | Registration date | Unit type | Internal sq.ft | Sellable sq.ft | Price AED | AED/sq.ft | Off-plan/Ready | DLD ref] and this workbook can be repopulated at transaction level.",
]
for i, n in enumerate(notes, 3):
    c = ws.cell(row=i, column=1, value="• " + n)
    c.alignment = wrap; c.font = Font(size=10)
ws.column_dimensions["A"].width = 140
for i in range(3, 3+len(notes)):
    ws.row_dimensions[i].height = 44

wb.save("/tmp/claude-0/-home-user-Claude-1/456a4dde-a616-5eda-bbc4-16747b5cae37/scratchpad/Dubai_Islands_DLD_transactions.xlsx")
print("WROTE workbook with sheets:", wb.sheetnames)
