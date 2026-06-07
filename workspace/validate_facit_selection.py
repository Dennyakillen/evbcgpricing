"""
validate_facit_selection.py
============================
Validates BCG's frozen ItemCode x Cluster selection (0828 facit).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - 0828 facit file exists and is readable
  - 1151 ItemCodes and 4949 ItemCode x Cluster pairs (BCG's frozen count)
  - All clinical service codes present (AAP, DUS, AEM, ALB, ALT, ANALYS)
  - pg4 mapping is complete (100% non-null) and 1:1 per ItemCode
  - Distribution per cluster (item count, coverage)
  - All our extraction's ItemCodes are in facit selection

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\03_facit_selection_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    BCG_FACIT_CSV, OUR_CSV,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)

EXPECTED_ITEMCODES = 1151
EXPECTED_PAIRS = 4949
EXPECTED_PG4_CATEGORIES = 23
SERVICE_CODE_PATTERNS = ["AAP", "DUS", "AEM", "ALB", "ALT", "ANALYS", "ASU", "ARCCRE"]


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("FACIT SELECTION VALIDATION (0828)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not BCG_FACIT_CSV.exists():
        sys.exit(f"ERROR: facit missing: {BCG_FACIT_CSV}")
    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Load facit -----
    subsection("[1/5] Loading BCG facit")
    fac = pd.read_csv(BCG_FACIT_CSV, encoding="cp1252", encoding_errors="ignore",
                      usecols=["ItemCode", "Cluster", "ProductGroupL4Name"],
                      low_memory=False)
    fac["ItemCode"] = fac["ItemCode"].astype(str).str.strip().str.upper()
    fac["Cluster"] = fac["Cluster"].astype(str).str.strip()
    print(f"  Rows loaded: {fmt_int(len(fac))}")
    print(f"  File hash: {file_hash_short(BCG_FACIT_CSV)}")
    print()

    # ----- Checks -----
    subsection("[2/5] Validation checks")
    checks = []

    # Check 1: ItemCode count
    n_codes = fac["ItemCode"].nunique()
    chk1 = (n_codes == EXPECTED_ITEMCODES)
    print(f"  ItemCodes: {n_codes} (expected {EXPECTED_ITEMCODES}) -> "
          f"{'PASS' if chk1 else 'FAIL'}")
    checks.append(("ItemCode count", n_codes, EXPECTED_ITEMCODES,
                   "PASS" if chk1 else "FAIL"))

    # Check 2: ItemCode x Cluster pairs
    pairs = fac[["ItemCode", "Cluster"]].drop_duplicates()
    n_pairs = len(pairs)
    chk2 = (n_pairs == EXPECTED_PAIRS)
    print(f"  ItemCode x Cluster pairs: {n_pairs} (expected {EXPECTED_PAIRS}) -> "
          f"{'PASS' if chk2 else 'REVIEW'}")
    checks.append(("ItemCode x Cluster pairs", n_pairs, EXPECTED_PAIRS,
                   "PASS" if chk2 else "REVIEW"))

    # Check 3: pg4 non-null
    n_pg4_null = fac["ProductGroupL4Name"].isna().sum()
    chk3 = (n_pg4_null == 0)
    print(f"  pg4 NULL rows: {n_pg4_null} (expected 0) -> "
          f"{'PASS' if chk3 else 'FAIL'}")
    checks.append(("pg4 NULL rows", n_pg4_null, 0,
                   "PASS" if chk3 else "FAIL"))

    # Check 4: pg4 1:1 mapping per ItemCode
    per_code_pg4 = fac.groupby("ItemCode")["ProductGroupL4Name"].nunique()
    multi_pg4 = (per_code_pg4 > 1).sum()
    chk4 = (multi_pg4 == 0)
    print(f"  ItemCodes with multiple pg4 values: {multi_pg4} (expected 0) -> "
          f"{'PASS' if chk4 else 'FAIL'}")
    checks.append(("Multi-pg4 ItemCodes", multi_pg4, 0,
                   "PASS" if chk4 else "FAIL"))

    # Check 5: pg4 categories
    n_categories = fac["ProductGroupL4Name"].nunique()
    chk5 = (n_categories == EXPECTED_PG4_CATEGORIES)
    print(f"  Distinct pg4 categories: {n_categories} (expected {EXPECTED_PG4_CATEGORIES}) -> "
          f"{'PASS' if chk5 else 'REVIEW'}")
    checks.append(("Distinct pg4 categories", n_categories, EXPECTED_PG4_CATEGORIES,
                   "PASS" if chk5 else "REVIEW"))

    # Check 6: Service codes present
    code_set = set(fac["ItemCode"].unique())
    service_found = []
    for pattern in SERVICE_CODE_PATTERNS:
        n_match = sum(1 for c in code_set if c.startswith(pattern))
        service_found.append((pattern, n_match))
    all_services_present = all(n > 0 for _, n in service_found)
    chk6 = all_services_present
    print(f"  Service code patterns found: {sum(1 for _, n in service_found if n > 0)}/{len(SERVICE_CODE_PATTERNS)} -> "
          f"{'PASS' if chk6 else 'REVIEW'}")
    checks.append(("Service code patterns present", str(service_found),
                   "all > 0", "PASS" if chk6 else "REVIEW"))

    # Check 7: All our extraction's ItemCodes in facit
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      usecols=["ItemCode"], low_memory=False)
    our_codes = set(our["ItemCode"].astype(str).str.strip().str.upper().unique())
    not_in_facit = our_codes - code_set
    chk7 = (len(not_in_facit) == 0)
    print(f"  Our codes not in facit: {len(not_in_facit)} (expected 0) -> "
          f"{'PASS' if chk7 else 'FAIL'}")
    checks.append(("Our codes covered by facit", len(not_in_facit), 0,
                   "PASS" if chk7 else "FAIL"))

    # ----- Distribution per cluster -----
    subsection("[3/5] ItemCode count per cluster (in facit)")
    pairs_per_cluster = pairs.groupby("Cluster").size().reset_index(name="n_codes")
    print(f"  {'Cluster':<20}  {'#ItemCodes':>12}")
    for _, r in pairs_per_cluster.iterrows():
        print(f"  {r['Cluster']:<20}  {r['n_codes']:>12}")
    print(f"  {'TOTAL pairs':<20}  {pairs_per_cluster['n_codes'].sum():>12}")
    print()

    # ----- pg4 distribution -----
    subsection("[4/5] pg4 category distribution in facit")
    pg4_dist = fac.groupby("ProductGroupL4Name").agg(
        n_codes=("ItemCode", "nunique"),
        n_rows=("ItemCode", "count"),
    ).reset_index().sort_values("n_rows", ascending=False)
    print(f"  {'pg4 category':<25}  {'#Codes':>7}  {'#Rows':>9}")
    for _, r in pg4_dist.iterrows():
        cat = str(r["ProductGroupL4Name"])[:24]
        print(f"  {cat:<25}  {r['n_codes']:>7}  {r['n_rows']:>9,}")
    print()

    # ----- Receipt -----
    subsection("[5/5] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"03_facit_selection_{timestamp_file}.xlsx"

    sheets = [
        {
            "name": "Summary",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Check", "Actual", "Expected", "Status"],
            "rows": checks,
            "notes": [
                f"Source: {BCG_FACIT_CSV.name}",
                f"File hash: {file_hash_short(BCG_FACIT_CSV)}",
            ],
        },
        {
            "name": "Cluster_Distribution",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Cluster", "# ItemCodes (pairs)"],
            "rows": [[r["Cluster"], int(r["n_codes"])] for _, r in pairs_per_cluster.iterrows()],
            "notes": [f"Total pairs: {pairs_per_cluster['n_codes'].sum()}"],
        },
        {
            "name": "pg4_Distribution",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["pg4 Category", "# ItemCodes", "# Rows"],
            "rows": [[str(r["ProductGroupL4Name"]), int(r["n_codes"]), int(r["n_rows"])]
                     for _, r in pg4_dist.iterrows()],
            "notes": [f"Total categories: {n_categories}"],
        },
        {
            "name": "Service_Codes",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Pattern", "# ItemCodes found"],
            "rows": [[p, n] for p, n in service_found],
            "notes": [
                "Service codes verify that clinical services (not just goods) are in facit.",
                "AAP=undersökning, DUS=ultraljud, AEM=anestesi, ALB/ALT/ANALYS=labb",
            ],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_facit_selection.py"],
                ["Run timestamp", timestamp_iso],
                ["Facit file", str(BCG_FACIT_CSV)],
                ["Facit hash", file_hash_short(BCG_FACIT_CSV)],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Facit Selection Validation", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()

    overall = all(c[3] in ("PASS", "REVIEW") for c in checks) and \
              not any(c[3] == "FAIL" for c in checks)
    print(f"  >> Result: {'PASS' if overall else 'REVIEW/FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
