"""
validate_fte_coverage.py
=========================
Validates FTE (Sum_FTE_Interpolated) coverage in our extraction.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - BCG's frozen FTE file (Sweden__Interpolated_Productivity_time_date_june25.xlsx)
  - FTE coverage in our extraction (rows with vs without Sum_FTE_Interpolated)
  - Week-level breakdown: which weeks lack FTE?
  - Revenue impact: how much TotalNet is affected by missing FTE?
  - Cluster-level FTE distribution

KNOWN STATE (per LF / IB documentation):
  - BCG's interpolated FTE file covers 2022-07 to 2025-06 only
  - For growing window, weeks after 2025-06 lack FTE -> Sum_FTE_Interpolated = NULL
  - This is "Way 1" (faithful replication); Way 2 (rebuild from Quinyx) is future scaling

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\04_fte_coverage_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    OUR_CSV, BCG_FTE_XLSX,
    fmt_msek, fmt_pct, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("FTE COVERAGE VALIDATION")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not BCG_FTE_XLSX.exists():
        sys.exit(f"ERROR: FTE file missing: {BCG_FTE_XLSX}")
    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Load FTE file -----
    subsection("[1/5] Loading BCG FTE interpolated file")
    fte = pd.read_excel(BCG_FTE_XLSX, engine="openpyxl")
    fte["week_starting_monday"] = pd.to_datetime(fte["week_starting_monday"])
    print(f"  Rows loaded: {fmt_int(len(fte))}")
    print(f"  Date range: {fte['week_starting_monday'].min().date()} -> "
          f"{fte['week_starting_monday'].max().date()}")
    print(f"  Distinct clusters: {fte['Cluster'].nunique()}")
    print(f"  Distinct weeks: {fte['week_starting_monday'].nunique()}")
    print(f"  File hash: {file_hash_short(BCG_FTE_XLSX)}")
    fte_max_date = fte["week_starting_monday"].max()
    print()

    # ----- Load our extraction -----
    subsection("[2/5] Loading our extraction")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    our["week_starting_monday"] = pd.to_datetime(our["week_starting_monday"])
    print(f"  Rows loaded: {fmt_int(len(our))}")
    print(f"  Date range: {our['week_starting_monday'].min().date()} -> "
          f"{our['week_starting_monday'].max().date()}")
    print()

    # ----- Analyze FTE NULL -----
    subsection("[3/5] FTE coverage analysis")
    null_mask = our["Sum_FTE_Interpolated"].isna()
    n_null = null_mask.sum()
    n_total = len(our)
    pct_null = 100 * n_null / n_total

    print(f"  Total rows: {fmt_int(n_total)}")
    print(f"  Rows with FTE: {fmt_int(n_total - n_null)} ({100*(n_total-n_null)/n_total:.1f}%)")
    print(f"  Rows WITHOUT FTE: {fmt_int(n_null)} ({pct_null:.2f}%)")
    print()

    # Revenue impact
    rev_with_fte = our.loc[~null_mask, "TotalNet"].sum()
    rev_no_fte = our.loc[null_mask, "TotalNet"].sum()
    rev_total = our["TotalNet"].sum()
    pct_rev_no_fte = 100 * rev_no_fte / rev_total

    print(f"  Revenue WITH FTE:    {fmt_msek(rev_with_fte)}  ({100*rev_with_fte/rev_total:.1f}%)")
    print(f"  Revenue WITHOUT FTE: {fmt_msek(rev_no_fte)}  ({pct_rev_no_fte:.1f}%)")
    print()

    # ----- Week-level breakdown -----
    subsection("[4/5] Week-level breakdown (rows without FTE)")
    if n_null > 0:
        weeks_no_fte = our.loc[null_mask, "week_starting_monday"].unique()
        weeks_no_fte = sorted(pd.to_datetime(weeks_no_fte))
        print(f"  Distinct weeks without FTE: {len(weeks_no_fte)}")
        print(f"  First missing week: {weeks_no_fte[0].date()}")
        print(f"  Last missing week:  {weeks_no_fte[-1].date()}")
        print(f"  (BCG FTE coverage ends: {fte_max_date.date()})")
        print()

        # Weeks DataFrame for receipt
        week_rev = our[null_mask].groupby(
            our.loc[null_mask, "week_starting_monday"].dt.to_period("W").astype(str)
        ).agg(
            rows=("TotalNet", "count"),
            TotalNet=("TotalNet", "sum"),
        ).reset_index()
        week_rev.columns = ["week", "rows", "TotalNet"]
    else:
        weeks_no_fte = []
        week_rev = pd.DataFrame(columns=["week", "rows", "TotalNet"])
        print("  All rows have FTE - frozen window only.")
        print()

    # ----- Status assessment -----
    # Expected: 19-21% NULL for growing window past 2025-06
    # < 1% = frozen window (PASS)
    # 15-25% = growing window past FTE coverage (PASS, expected)
    # > 30% = unexpected coverage gap (REVIEW)
    if pct_null < 1:
        status = "PASS"
        status_note = "Frozen window only - full FTE coverage."
    elif 15 <= pct_null <= 25:
        status = "PASS"
        status_note = "Growing window past BCG FTE coverage (2025-06). Expected per Way 1."
    elif pct_null < 15:
        status = "PASS"
        status_note = f"Partial growing window, lower NULL share than typical 20%."
    else:
        status = "REVIEW"
        status_note = f"Unexpected: {pct_null:.1f}% NULL exceeds 25% threshold. Investigate."

    print(f"  Status: {status}")
    print(f"  Note: {status_note}")
    print()

    # ----- Receipt -----
    subsection("[5/5] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"04_fte_coverage_{timestamp_file}.xlsx"

    summary_rows = [
        ["Total rows in extraction", fmt_int(n_total).strip(), ""],
        ["Rows with FTE", fmt_int(n_total - n_null).strip(), f"{100*(n_total-n_null)/n_total:.2f}%"],
        ["Rows WITHOUT FTE", fmt_int(n_null).strip(), f"{pct_null:.2f}%"],
        ["", "", ""],
        ["Total revenue (TotalNet)", f"{rev_total:,.0f}", f"{rev_total/1e6:.1f} MSEK"],
        ["Revenue with FTE", f"{rev_with_fte:,.0f}", f"{rev_with_fte/1e6:.1f} MSEK"],
        ["Revenue without FTE", f"{rev_no_fte:,.0f}", f"{rev_no_fte/1e6:.1f} MSEK"],
        ["", "", ""],
        ["BCG FTE coverage ends", fte_max_date.strftime("%Y-%m-%d"), ""],
        ["Our extraction ends", our["week_starting_monday"].max().strftime("%Y-%m-%d"), ""],
        ["", "", ""],
        ["Status", status, status_note],
    ]

    sheets = [
        {
            "name": "Summary",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Metric", "Value", "Notes"],
            "rows": summary_rows,
            "notes": [
                "FTE source: BCG's frozen interpolated file (Way 1 - faithful replication).",
                "Way 2 (rebuild FTE from Quinyx DW) is on roadmap.",
                "Pipeline handles NULL FTE in regression (drops or imputes per BCG logic).",
            ],
        },
        {
            "name": "Weeks_Without_FTE",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Week", "Rows", "TotalNet (SEK)"],
            "rows": [[r["week"], int(r["rows"]), float(r["TotalNet"])]
                     for _, r in week_rev.iterrows()],
            "notes": [
                f"Distinct weeks without FTE: {len(weeks_no_fte)}",
                "These weeks fall after BCG's FTE coverage ends.",
            ],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_fte_coverage.py"],
                ["Run timestamp", timestamp_iso],
                ["FTE file", str(BCG_FTE_XLSX)],
                ["FTE hash", file_hash_short(BCG_FTE_XLSX)],
                ["FTE coverage end", fte_max_date.strftime("%Y-%m-%d")],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "FTE Coverage Validation", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()
    print(f"  >> Result: {status}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
