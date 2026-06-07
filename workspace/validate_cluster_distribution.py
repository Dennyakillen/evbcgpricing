"""
validate_cluster_distribution.py
=================================
Validates revenue and volume distribution across the 7 BCG clusters.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - Revenue per cluster (SEK and % share)
  - SoldQuantity per cluster
  - Distinct ItemCodes per cluster
  - Distinct departments per cluster
  - Balance check: no cluster dominates beyond reasonable share

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\06_cluster_distribution_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    OUR_CSV, BCG_FACIT_CSV,
    fmt_msek, fmt_pct, fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("CLUSTER DISTRIBUTION VALIDATION")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Load -----
    subsection("[1/3] Loading our extraction")
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      low_memory=False)
    print(f"  Rows: {fmt_int(len(our))}")
    print(f"  Clusters: {our['Cluster'].nunique()}")
    print()

    # ----- Per cluster -----
    subsection("[2/3] Per-cluster distribution")
    per_cluster = our.groupby("Cluster").agg(
        rows=("TotalNet", "count"),
        TotalNet=("TotalNet", "sum"),
        SoldQuantity=("SoldQuantity", "sum"),
        n_ItemCodes=("ItemCode", "nunique"),
        n_weeks=("week_starting_monday", "nunique"),
    ).reset_index()

    total_rev = per_cluster["TotalNet"].sum()
    total_qty = per_cluster["SoldQuantity"].sum()
    per_cluster["pct_revenue"] = 100 * per_cluster["TotalNet"] / total_rev
    per_cluster["pct_quantity"] = 100 * per_cluster["SoldQuantity"] / total_qty
    per_cluster = per_cluster.sort_values("TotalNet", ascending=False)

    print(f"  {'Cluster':<18}  {'Rev (MSEK)':>10}  {'%Rev':>6}  "
          f"{'Quantity':>11}  {'%Qty':>6}  {'#Codes':>6}  {'#Weeks':>6}")
    for _, r in per_cluster.iterrows():
        print(f"  {r['Cluster']:<18}  {r['TotalNet']/1e6:>10.1f}  "
              f"{r['pct_revenue']:>5.1f}%  {r['SoldQuantity']:>11,.0f}  "
              f"{r['pct_quantity']:>5.1f}%  {r['n_ItemCodes']:>6}  {r['n_weeks']:>6}")
    print(f"  {'TOTAL':<18}  {total_rev/1e6:>10.1f}  100.0%  "
          f"{total_qty:>11,.0f}  100.0%")
    print()

    # ----- Balance check -----
    max_share = per_cluster["pct_revenue"].max()
    min_share = per_cluster["pct_revenue"].min()
    print(f"  Max cluster share: {max_share:.1f}%")
    print(f"  Min cluster share: {min_share:.1f}%")

    if max_share > 50:
        status = "REVIEW"
        note = f"One cluster has > 50% of revenue ({max_share:.1f}%) - imbalanced."
    elif min_share < 1:
        status = "REVIEW"
        note = f"One cluster has < 1% of revenue ({min_share:.1f}%) - very small."
    else:
        status = "PASS"
        note = "Distribution within reasonable balance (1% < share < 50%)."
    print(f"  Status: {status} - {note}")
    print()

    # ----- Receipt -----
    subsection("[3/3] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"06_cluster_distribution_{timestamp_file}.xlsx"

    distribution_rows = [
        [r["Cluster"], int(r["rows"]),
         float(r["TotalNet"]),
         round(r["TotalNet"]/1e6, 1),
         round(r["pct_revenue"], 2),
         int(r["SoldQuantity"]),
         round(r["pct_quantity"], 2),
         int(r["n_ItemCodes"]),
         int(r["n_weeks"])]
        for _, r in per_cluster.iterrows()
    ]

    sheets = [
        {
            "name": "Distribution",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Cluster", "Rows", "TotalNet (SEK)", "TotalNet (MSEK)",
                        "% Revenue", "SoldQuantity", "% Quantity",
                        "# ItemCodes", "# Weeks"],
            "rows": distribution_rows,
            "notes": [
                f"Total revenue: {total_rev/1e6:.1f} MSEK",
                f"Total quantity: {total_qty:,.0f}",
                f"Balance status: {status} - {note}",
            ],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_cluster_distribution.py"],
                ["Run timestamp", timestamp_iso],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["Balance status", status],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Cluster Distribution Validation", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()
    print(f"  >> Result: {status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
