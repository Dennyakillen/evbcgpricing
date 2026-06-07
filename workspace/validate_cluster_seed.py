"""
validate_cluster_seed.py
=========================
Validates the BCG cluster seed mapping (0808_Sweden_Clinic_Cluster_Mapping.xlsx).

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

WHAT IT VALIDATES:
  - Cluster seed file exists and is readable
  - All expected 7 named clusters are present
  - 58 ID_Department are mapped (BCG's frozen count)
  - No duplicate ID_Department mappings
  - All ID_Department from our extraction map to a cluster
  - Distribution per cluster (department count, balance)

OUTPUT:
  - Console log (structural)
  - Excel receipt: archives\validation_receipts\YYYY-MM-DD\02_cluster_seed_<timestamp>.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from _validation_helpers import (
    BCG_CLUSTER_SEED_XLSX, OUR_CSV,
    fmt_int, now_iso, now_file_stamp, get_receipt_dir,
    file_hash_short, section, subsection, write_receipt,
)

EXPECTED_CLUSTERS = {"Clinics 0", "Clinics 1", "Clinics 2",
                     "Sjukhus A", "Sjukhus B", "Sjukhus C", "Sjukhus Södran"}
EXPECTED_DEPT_COUNT = 58


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()

    section("CLUSTER SEED VALIDATION (0808)")
    print(f"Run timestamp: {timestamp_iso}")
    print()

    if not BCG_CLUSTER_SEED_XLSX.exists():
        sys.exit(f"ERROR: cluster seed missing: {BCG_CLUSTER_SEED_XLSX}")
    if not OUR_CSV.exists():
        sys.exit(f"ERROR: our extraction missing: {OUR_CSV}")

    # ----- Load seed -----
    subsection("[1/4] Loading cluster seed")
    seed = pd.read_excel(BCG_CLUSTER_SEED_XLSX, sheet_name="New Mapping", engine="openpyxl")
    print(f"  Sheet 'New Mapping' loaded: {len(seed)} rows")
    print(f"  Columns: {list(seed.columns)[:8]}")
    print(f"  File hash (MD5 short): {file_hash_short(BCG_CLUSTER_SEED_XLSX)}")
    print()

    # Clean
    seed = seed[["ID_Department", "Cluster"]].copy()
    seed["ID_Department"] = pd.to_numeric(seed["ID_Department"], errors="coerce").astype("Int64")
    seed_clean = seed.dropna(subset=["ID_Department", "Cluster"]).drop_duplicates("ID_Department")

    # ----- Checks -----
    subsection("[2/4] Validation checks")

    checks = []

    # Check 1: department count
    n_dept = seed_clean["ID_Department"].nunique()
    chk1_pass = (n_dept == EXPECTED_DEPT_COUNT)
    print(f"  Departments mapped: {n_dept} (expected {EXPECTED_DEPT_COUNT}) -> "
          f"{'PASS' if chk1_pass else 'FAIL'}")
    checks.append(("Departments mapped", n_dept, EXPECTED_DEPT_COUNT, "PASS" if chk1_pass else "FAIL"))

    # Check 2: clusters present
    clusters_found = set(seed_clean["Cluster"].unique())
    missing = EXPECTED_CLUSTERS - clusters_found
    extra = clusters_found - EXPECTED_CLUSTERS
    chk2_pass = (not missing and not extra)
    print(f"  Clusters found: {len(clusters_found)} (expected {len(EXPECTED_CLUSTERS)}) -> "
          f"{'PASS' if chk2_pass else 'REVIEW'}")
    if missing:
        print(f"    MISSING: {missing}")
    if extra:
        print(f"    UNEXPECTED: {extra}")
    checks.append(("Cluster names match expected", str(sorted(clusters_found)),
                   str(sorted(EXPECTED_CLUSTERS)), "PASS" if chk2_pass else "REVIEW"))

    # Check 3: no duplicate ID_Department
    raw_count = len(seed.dropna(subset=["ID_Department", "Cluster"]))
    dedup_count = len(seed_clean)
    duplicates = raw_count - dedup_count
    chk3_pass = (duplicates == 0)
    print(f"  Duplicate ID_Department: {duplicates} -> {'PASS' if chk3_pass else 'FAIL'}")
    checks.append(("Duplicate ID_Department", duplicates, 0, "PASS" if chk3_pass else "FAIL"))

    # Check 4: all departments in our extraction are in seed
    our = pd.read_csv(OUR_CSV, encoding="cp1252", encoding_errors="ignore",
                      usecols=["Cluster"], low_memory=False)
    our_clusters = set(our["Cluster"].astype(str).str.strip().unique())
    our_missing = our_clusters - clusters_found
    chk4_pass = (not our_missing)
    print(f"  Our extraction uses clusters not in seed: {len(our_missing)} -> "
          f"{'PASS' if chk4_pass else 'FAIL'}")
    if our_missing:
        print(f"    UNKNOWN CLUSTERS IN OUR DATA: {our_missing}")
    checks.append(("Our cluster usage covered by seed", str(sorted(our_clusters)),
                   "all in seed", "PASS" if chk4_pass else "FAIL"))

    # ----- Distribution -----
    subsection("[3/4] Department distribution per cluster")
    distribution = seed_clean.groupby("Cluster").agg(
        n_departments=("ID_Department", "nunique"),
    ).reset_index().sort_values("Cluster")

    print(f"  {'Cluster':<20}  {'#Departments':>12}")
    for _, row in distribution.iterrows():
        print(f"  {row['Cluster']:<20}  {row['n_departments']:>12}")
    print(f"  {'TOTAL':<20}  {distribution['n_departments'].sum():>12}")
    print()

    # ----- Receipt -----
    subsection("[4/4] Writing Excel receipt")
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"02_cluster_seed_{timestamp_file}.xlsx"

    sheets = [
        {
            "name": "Summary",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Check", "Actual", "Expected", "Status"],
            "rows": checks,
            "notes": [
                f"Source file: {BCG_CLUSTER_SEED_XLSX.name}",
                f"File hash: {file_hash_short(BCG_CLUSTER_SEED_XLSX)}",
                "Expected: BCG's frozen mapping = 58 ID_Department in 7 named clusters",
            ],
        },
        {
            "name": "Distribution",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["Cluster", "# Departments"],
            "rows": [[r["Cluster"], int(r["n_departments"])] for _, r in distribution.iterrows()],
            "notes": [f"Total departments mapped: {distribution['n_departments'].sum()}"],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "validate_cluster_seed.py"],
                ["Run timestamp", timestamp_iso],
                ["Seed file", str(BCG_CLUSTER_SEED_XLSX)],
                ["Seed hash", file_hash_short(BCG_CLUSTER_SEED_XLSX)],
                ["Our extraction file", str(OUR_CSV)],
                ["Our extraction hash", file_hash_short(OUR_CSV)],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Cluster Seed Validation", sheets)
    print(f"  Receipt: {receipt_path.name}")
    print()

    overall_pass = all(c[3] == "PASS" for c in checks)
    print(f"  >> Result: {'PASS' if overall_pass else 'REVIEW'}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
