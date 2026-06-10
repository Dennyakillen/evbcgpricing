"""
verify_bundle_schema.py — F.9 Bundle, parquet-vs-SQL column reconciliation

Purpose
-------
convert_masterdata_to_parquet.py warned that the produced parquet schema differs
from EXPECTED_COLS. But EXPECTED_COLS was built from the *commented-out* (dead)
CSV-read block in Bundle 00_read.sql, which may be stale. The real question is not
"does the parquet match my guessed list" but "does the parquet contain every column
Bundle's SQL actually references". This script answers exactly that.

Method
------
1. Read the actual column list from the freshly written Bundle parquet.
2. Hold the set of columns Bundle 01_process.sql references (extracted by reading
   the SQL; listed below as BUNDLE_SQL_COLS).
3. Report: which referenced columns are present, which are missing.
   - missing == empty  -> parquet is sufficient, the convert WARN was a false alarm
     from a stale EXPECTED_COLS. Green light for Bundle SQL prep.
   - missing != empty   -> Bundle SQL will break; STOP and investigate why the
     masterdata export omits them.

BUNDLE_SQL_COLS source
----------------------
From Bundle Sweden_Bundling_Data_Prep/scripts/01_process.sql (verified in session
2026-06-10): the FROM sweden_master_data SELECT/WHERE/GROUP BY reference these.
Update this list if the SQL is re-read and found to reference more.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-10.
"""
import sys
from pathlib import Path

import duckdb

BUNDLE_PARQUET = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\4. Bundle Clinic Data Prep"
    r"\Sweden_Bundling_Data_Prep\parquet\sweden_master_data.parquet"
)

# Columns Bundle 01_process.sql references against sweden_master_data.
# (raw_data SELECT + WHERE + bundle_cluster_data GROUP BY)
BUNDLE_SQL_COLS = {
    "InvoiceDate",
    "ID_Patient",
    "ID_Department",
    "ItemCode",
    "ProductGroupL4Name",
    "SalesTotal",
    "SoldQuantity",
    "YearFlag",
    "ItemDescription",
}


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    if not BUNDLE_PARQUET.exists():
        log("ERROR", f"parquet not found: {BUNDLE_PARQUET}")
        return 1

    p = str(BUNDLE_PARQUET).replace("\\", "/")
    con = duckdb.connect()
    cols = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{p}')"
    ).fetchall()]
    cols_set = set(cols)

    log("PARQUET", f"{len(cols)} columns present:")
    print("  " + ", ".join(sorted(cols)))
    print()

    present = sorted(BUNDLE_SQL_COLS & cols_set)
    missing = sorted(BUNDLE_SQL_COLS - cols_set)

    log("USED-PRESENT", f"{len(present)}/{len(BUNDLE_SQL_COLS)}: {present}")
    if missing:
        log("USED-MISSING", f"{missing}")
        print()
        log("VERDICT", "STOP. Bundle 01_process.sql references columns NOT in parquet.")
        log("ACTION", "Investigate why replicate_dataprep.py masterdata export omits "
                      "them, OR confirm the SQL was re-read and the column names differ "
                      "(e.g. casing).")
        return 2
    else:
        print()
        log("VERDICT", "OK. Every column Bundle SQL references is present in the parquet.")
        log("ACTION", "The convert WARN was a false alarm from a stale EXPECTED_COLS "
                      "(built from dead commented CSV block). Green light for Bundle SQL prep.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
