"""
validate_extraction_coverage.py
================================
Validates revenue coverage of the pipeline extraction vs BCG facit
and quantifies incremental months.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-05
Updated:   2026-06-07 (English, uses shared helpers, saves to archives)

WHAT IT VALIDATES:
  - Total revenue captured
  - Frozen subset drift vs BCG facit (gate: +/- 0.5%)
  - Incremental months revenue per year and per pg4
  - Static documentation of all extraction filters

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\01_extraction_coverage_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    OUR_CSV, BCG_FACIT_CSV, BCG_START, BCG_END,
    fmt_msek, fmt_pct, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)

DRIFT_TOLERANCE_PCT = 0.5


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("EXTRACTION COVERAGE VALIDATION")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}\nRun export_b4b_for_model.py first.")
    if not BCG_FACIT_CSV.exists():
        sys.exit(f"ERROR: BCG facit missing: {BCG_FACIT_CSV}")

    # ----- 1. Load our extraction -----
    subsection("[1/4] Loading our extraction")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    our["week_starting_monday"] = pd.to_datetime(our["week_starting_monday"])
    our_min = our["week_starting_monday"].min().strftime("%Y-%m-%d")
    our_max = our["week_starting_monday"].max().strftime("%Y-%m-%d")
    print(f"  Rows: {fmt_int(len(our))}")
    print(f"  Date window: {our_min} -> {our_max}")
    print(f"  ItemCodes: {our['ItemCode'].nunique()}")
    print()

    # ----- 2. Load BCG facit -----
    subsection("[2/4] Loading BCG frozen facit")
    bcg = pd.read_csv(BCG_FACIT_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    bcg["week_starting_monday"] = pd.to_datetime(bcg["week_starting_monday"])
    print(f"  Rows: {fmt_int(len(bcg))}")
    print()

    # ----- 3. Segment and compute -----
    subsection("[3/4] Segmenting and computing drift")
    bcg_end_ts = pd.Timestamp(BCG_END)
    frozen = our[our["week_starting_monday"] <= bcg_end_ts]
    growth = our[our["week_starting_monday"] > bcg_end_ts]

    our_total = our["TotalNet"].sum()
    frozen_total = frozen["TotalNet"].sum()
    growth_total = growth["TotalNet"].sum()
    bcg_total = bcg["TotalNet"].sum()

    drift_abs = frozen_total - bcg_total
    drift_pct = 100 * drift_abs / bcg_total
    gate = abs(drift_pct) <= DRIFT_TOLERANCE_PCT
    status = "PASS" if gate else "REVIEW"

    print(f"  Our full extraction:  {fmt_msek(our_total)}")
    print(f"  Our frozen subset:    {fmt_msek(frozen_total)}")
    print(f"  Our incremental:      {fmt_msek(growth_total)}")
    print(f"  BCG facit:            {fmt_msek(bcg_total)}")
    print()
    print(f"  Drift frozen vs BCG: {drift_abs:+,.0f} SEK ({drift_pct:+.4f}%)")
    print(f"  Status: {status}")
    print()

    # Per year
    our["year"] = our["week_starting_monday"].dt.year
    yearly = our.groupby("year").agg(
        rows=("TotalNet", "count"),
        TotalNet=("TotalNet", "sum"),
        SoldQuantity=("SoldQuantity", "sum"),
        n_ItemCodes=("ItemCode", "nunique"),
    )

    # Per pg4 (incremental only)
    pg4_growth = pd.DataFrame()
    if len(growth) > 0:
        pg4_growth = growth.groupby("ProductGroupL4Name").agg(
            TotalNet=("TotalNet", "sum"),
            n_ItemCodes=("ItemCode", "nunique"),
        ).sort_values("TotalNet", ascending=False)

    # ----- 4. Receipt -----
    subsection("[4/4] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"01_extraction_coverage_{timestamp_file}.xlsx"

    summary_rows = [
        ["Our full extraction (SEK)", f"{our_total:,.0f}", f"{our_total/1e6:.1f} MSEK"],
        ["Our frozen subset (SEK)", f"{frozen_total:,.0f}", f"{frozen_total/1e6:.1f} MSEK"],
        ["Our incremental (SEK)", f"{growth_total:,.0f}", f"{growth_total/1e6:.1f} MSEK"],
        ["BCG facit (SEK)", f"{bcg_total:,.0f}", f"{bcg_total/1e6:.1f} MSEK"],
        ["", "", ""],
        ["Drift frozen vs BCG (SEK)", f"{drift_abs:+,.0f}", ""],
        ["Drift frozen vs BCG (%)", f"{drift_pct:+.4f}%", f"tolerance +/-{DRIFT_TOLERANCE_PCT}%"],
        ["Status", status, "Within tolerance" if gate else "EXCEEDS tolerance"],
        ["", "", ""],
        ["Incremental as % of BCG", f"{100*growth_total/bcg_total:+.1f}%", ""],
        ["", "", ""],
        ["Our window start", our_min, ""],
        ["Our window end", our_max, ""],
        ["BCG facit window", f"{BCG_START} -> {BCG_END}", ""],
        ["Our ItemCodes", str(our["ItemCode"].nunique()), ""],
        ["BCG facit ItemCodes", str(bcg["ItemCode"].nunique()), ""],
    ]

    yearly_rows = [
        [int(y), int(r["rows"]), float(r["TotalNet"]),
         round(r["TotalNet"]/1e6, 1), int(r["SoldQuantity"]), int(r["n_ItemCodes"])]
        for y, r in yearly.iterrows()
    ]

    pg4_rows = []
    if len(pg4_growth) > 0:
        pg4_rows = [[str(c), float(r["TotalNet"]),
                     round(r["TotalNet"]/1e6, 1), int(r["n_ItemCodes"])]
                    for c, r in pg4_growth.iterrows()]

    filters_doc = [
        [1, "InvoiceDate window", "SQL", f"{BCG_START} to END_DATE (LF.2 growing)"],
        [2, "SalesTotal > 0", "SQL", "Excludes zeros and credit notes"],
        [3, "SoldQuantity > 0", "SQL", "Requires sold quantity match"],
        [4, "ItemCode IS NOT NULL", "SQL", "Excludes items without code"],
        [5, "ItemCode != 'ta bort'", "SQL", "Excludes items marked for removal"],
        [6, "INNER JOIN Manual.Dim_Item_Extended", "SQL", "Requires valid item master"],
        [7, "INNER JOIN cluster seed (0808)", "Python", "Restricts to 58 ID_Department"],
        [8, "INNER JOIN facit_pairs (0828)", "Python", "Restricts to 1151 ItemCodes"],
    ]

    sheets = [
        {
            "name": "Summary",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Metric", "Value", "Notes"],
            "rows": summary_rows,
            "notes": [
                f"Run timestamp: {timestamp_iso}",
                f"Tolerance gate: +/- {DRIFT_TOLERANCE_PCT}% on frozen subset vs BCG facit",
            ],
        },
        {
            "name": "Yearly",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Year", "Rows", "TotalNet (SEK)", "TotalNet (MSEK)",
                        "SoldQuantity", "ItemCodes"],
            "rows": yearly_rows,
            "notes": [],
        },
        {
            "name": "pg4_Incremental",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["pg4 Category", "TotalNet (SEK)", "TotalNet (MSEK)", "ItemCodes"],
            "rows": pg4_rows if pg4_rows else [["(no incremental data)", "", "", ""]],
            "notes": ["Breakdown of revenue contributed by months beyond BCG's frozen window."],
        },
        {
            "name": "Filters",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["#", "Filter", "Layer", "Purpose"],
            "rows": filters_doc,
            "notes": [
                "All filters applied during extraction.",
                "Filters 7+8 restrict to BCG's 1151 ItemCode x Cluster selection by design.",
            ],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_extraction_coverage.py"],
                ["Run timestamp", timestamp_iso],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["BCG facit file", str(BCG_FACIT_CSV)],
                ["BCG facit hash", file_hash_short(BCG_FACIT_CSV)],
                ["BCG window", f"{BCG_START} to {BCG_END}"],
                ["Tolerance", f"+/- {DRIFT_TOLERANCE_PCT}%"],
                ["Result", status],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Extraction Coverage Validation", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()
    print(f"  >> Result: {status}")

    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
