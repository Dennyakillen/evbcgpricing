"""
validate_dropped_rows.py
=========================
Quantifies what the extraction pipeline filters OUT vs the final CSV.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES (post-mortem analysis):
  - Compares DW rows extracted vs final CSV rows
  - Quantifies effect of each filter stage:
       * SalesTotal > 0
       * SoldQuantity > 0
       * INNER JOIN cluster seed (drops departments outside BCG mapping)
       * INNER JOIN facit_pairs (drops ItemCodes outside BCG selection)
       * Aggregation (compresses to ItemCode x Cluster x week grain)
  - Reads the last DW extraction log if available to get filter funnel

LIMITATIONS:
  - Cannot re-query DW from this script (validation only, no infrastructure changes)
  - Relies on the most recent dwexport_log_*.txt OR runs static analysis on output
  - For full forensics, run with --re-extract flag in future (not built yet)

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\05_dropped_rows_<timestamp>.xlsx
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    OUR_CSV, BUSINESS_ROOT,
    fmt_msek, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)


def find_latest_export_log():
    """Find the most recent DW export log file."""
    # Common locations
    candidates = []
    for parent in [Path.home() / "Downloads",
                   BUSINESS_ROOT,
                   Path.home()]:
        if parent.exists():
            candidates.extend(parent.glob("dwexport_log_*.txt"))
            candidates.extend(parent.glob("dw_export_*.txt"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def parse_export_log(log_path):
    """Extract filter funnel numbers from export log."""
    if not log_path or not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="ignore")

    parsed = {}
    # Match patterns like "DW rows: 11491982  departments: 87"
    m = re.search(r"DW rows:\s*(\d+)\s+departments:\s*(\d+)", text)
    if m:
        parsed["dw_rows"] = int(m.group(1))
        parsed["dw_departments"] = int(m.group(2))

    m = re.search(r"After cluster join: rows=(\d+)\s+clusters=(\d+)", text)
    if m:
        parsed["after_cluster_rows"] = int(m.group(1))
        parsed["after_cluster_clusters"] = int(m.group(2))

    m = re.search(r"After facit selection: codes=(\d+)", text)
    if m:
        parsed["after_facit_codes"] = int(m.group(1))

    m = re.search(r"pg4 coverage\s+after\s+BCG fill:\s*(\d+)/(\d+)", text)
    if m:
        parsed["after_pg4_fill_nonnull"] = int(m.group(1))
        parsed["after_pg4_fill_total"] = int(m.group(2))

    m = re.search(r"Distinct ItemCode:\s*(\d+)\s+KEY:\s*(\d+)", text)
    if m:
        parsed["final_itemcodes"] = int(m.group(1))
        parsed["final_keys"] = int(m.group(2))

    m = re.search(r"Sum TotalNet:\s*([\d,]+)\s+Sum SoldQuantity:\s*([\d,]+)", text)
    if m:
        parsed["sum_totalnet"] = int(m.group(1).replace(",", ""))
        parsed["sum_soldquantity"] = int(m.group(2).replace(",", ""))

    m = re.search(r"Sum_FTE_Interpolated NULL:\s*(\d+)", text)
    if m:
        parsed["fte_null_rows"] = int(m.group(1))

    return parsed


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("DROPPED ROWS / FILTER FUNNEL VALIDATION")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Find and parse export log -----
    subsection("[1/4] Searching for latest DW export log")
    log = find_latest_export_log()
    parsed = None
    if log:
        print(f"  Found: {log}")
        print(f"  Last modified: {pd.Timestamp(log.stat().st_mtime, unit='s')}")
        parsed = parse_export_log(log)
        if parsed:
            print(f"  Parsed {len(parsed)} funnel metrics")
        else:
            print(f"  Could not parse - file format unexpected")
    else:
        print(f"  No log file found in Downloads / Business_Analytics / home.")
        print(f"  Funnel analysis will be limited to final CSV only.")
    print()

    # ----- Read final CSV stats -----
    subsection("[2/4] Reading final CSV (post-pipeline)")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    final_rows = len(our)
    final_itemcodes = our["ItemCode"].nunique()
    final_keys = our.assign(KEY=our["Cluster"].astype(str) + "-" + our["ItemCode"].astype(str))["KEY"].nunique()
    final_revenue = our["TotalNet"].sum()
    final_quantity = our["SoldQuantity"].sum()
    print(f"  Final rows: {fmt_int(final_rows)}")
    print(f"  Final ItemCodes: {final_itemcodes}")
    print(f"  Final KEY (Cluster x ItemCode): {final_keys}")
    print(f"  Final TotalNet: {fmt_msek(final_revenue)}")
    print(f"  Final SoldQuantity: {fmt_int(int(final_quantity))}")
    print()

    # ----- Build funnel -----
    subsection("[3/4] Filter funnel (where rows were dropped)")
    funnel = []
    if parsed:
        if "dw_rows" in parsed:
            funnel.append(("DW raw query (SalesTotal > 0, SoldQuantity > 0, ItemCode IS NOT NULL, != 'ta bort')",
                          parsed["dw_rows"], "", "SQL"))
        if "after_cluster_rows" in parsed:
            dropped = parsed["dw_rows"] - parsed["after_cluster_rows"]
            pct = 100 * dropped / parsed["dw_rows"] if parsed["dw_rows"] else 0
            funnel.append((f"After INNER JOIN cluster seed (0808, 58 ID_Department)",
                          parsed["after_cluster_rows"],
                          f"-{dropped:,} ({pct:.1f}%)",
                          "Python"))
        if "after_facit_codes" in parsed:
            funnel.append((f"After INNER JOIN facit_pairs (0828, 1151 ItemCodes)",
                          f"codes={parsed['after_facit_codes']}", "", "Python"))
        if "after_pg4_fill_nonnull" in parsed:
            funnel.append((f"After aggregation (ItemCode x Cluster x week) + pg4 fill",
                          parsed["after_pg4_fill_total"],
                          f"pg4 coverage 100%",
                          "Python"))
    funnel.append(("Final CSV (post-aggregation)", final_rows,
                   f"ItemCodes={final_itemcodes}, KEY={final_keys}", "Output"))

    print(f"  {'Stage':<60}  {'Rows':>12}  {'Delta':>20}")
    for stage, rows, delta, layer in funnel:
        rows_str = f"{rows:,}" if isinstance(rows, int) else str(rows)
        print(f"  {stage[:60]:<60}  {rows_str:>12}  {delta:>20}")
    print()

    if parsed and "dw_rows" in parsed:
        total_dropped_to_final = parsed["dw_rows"] - final_rows
        pct_dropped = 100 * total_dropped_to_final / parsed["dw_rows"]
        print(f"  Total compression: DW {parsed['dw_rows']:,} -> CSV {final_rows:,}")
        print(f"  ({total_dropped_to_final:,} rows compressed/dropped, {pct_dropped:.1f}%)")
        print(f"  Note: 'compression' includes aggregation from row-level to week-level,")
        print(f"        not only dropped rows.")
        print()

    # ----- Receipt -----
    subsection("[4/4] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"05_dropped_rows_{timestamp_file}.xlsx"

    funnel_rows = [[stage, str(rows), delta, layer] for stage, rows, delta, layer in funnel]

    parsed_rows = [[k, str(v)] for k, v in (parsed or {}).items()]
    if not parsed_rows:
        parsed_rows = [["(no log found)", "Run after a fresh export to capture full funnel"]]

    sheets = [
        {
            "name": "Filter_Funnel",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Stage", "Rows", "Delta", "Layer"],
            "rows": funnel_rows,
            "notes": [
                "Layer = where the filter is applied (SQL = in DW query, Python = post-query in export script).",
                "INTENTIONAL drops (LF-locked): facit_pairs restricts to BCG's 1151 ItemCode x Cluster selection.",
                "INTENTIONAL drops: cluster seed restricts to 58 ID_Department in 7 BCG clusters.",
            ],
        },
        {
            "name": "Parsed_Log_Metrics",
            "subtitle": f"From log: {log.name if log else 'none'}",
            "headers": ["Metric", "Value"],
            "rows": parsed_rows,
            "notes": [
                "Metrics parsed from the latest dwexport_log_*.txt file.",
                "To regenerate: tee export_b4b_for_model.py output to Downloads next time.",
            ],
        },
        {
            "name": "Final_CSV_Stats",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Metric", "Value"],
            "rows": [
                ["Total rows", fmt_int(final_rows).strip()],
                ["Distinct ItemCodes", final_itemcodes],
                ["Distinct KEY (Cluster x ItemCode)", final_keys],
                ["Sum TotalNet (SEK)", f"{final_revenue:,.0f}"],
                ["Sum TotalNet (MSEK)", f"{final_revenue/1e6:.1f}"],
                ["Sum SoldQuantity", fmt_int(int(final_quantity)).strip()],
            ],
            "notes": [],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_dropped_rows.py"],
                ["Run timestamp", timestamp_iso],
                ["Export log used", str(log) if log else "none"],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Dropped Rows / Filter Funnel Analysis", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()
    print(f"  >> Result: INFO (forensic analysis, no pass/fail gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
