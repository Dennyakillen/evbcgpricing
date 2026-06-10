"""
check_yearflag_population.py — F.9 Bundle pre-flight check

Purpose
-------
Counts YearFlag values in the current sweden_master_data.parquet. Used to decide
SQL-patch path (a) or (b) in F9_BUNDLE_INVENTORY.md Blockare 2:
  (a) '12M ending Jun 26' present in growing data -> extend WHERE clause in
      Sweden_Bundling_Data_Prep/scripts/01_process.sql to include it.
  (b) flag absent -> rewrite filter to date-based (InvoiceDate >= START_DATE
      AND < END_DATE2) via _inject_dates pattern (same as Cluster/Site SQL prep).

When to use
-----------
Backup for the PowerShell oneliner in F9_BUNDLE_INVENTORY.md section 5, block A.
Use this when nested-quote escaping breaks the oneliner (LB.21,
KÄRNPRINCIPER §5: avoid long python -c oneliners with nested quotes).

How to run
----------
    py -3.11 "C:\\Projekt\\BCG\\check_yearflag_population.py"

Expected output
---------------
A YearFlag x count table. Look for whether values beyond '12M ending Jun 25'
are present, particularly '12M ending Jun 26'.

Related files
-------------
- F9_BUNDLE_INVENTORY.md (this script's caller; section 5 block A)
- Pipeline/02. Elasticity/4. Bundle Clinic Data Prep/Sweden_Bundling_Data_Prep/scripts/01_process.sql
  (the SQL whose WHERE clause is being decided)
- Pipeline/01. Clustering/Sweden_clustering_SQL/parquet/sweden_master_data.parquet
  (the parquet file inspected here)

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-10.
"""
import sys
from pathlib import Path

import duckdb


PARQUET_PATH = Path(
    r"C:\Projekt\BCG\Pipeline\01. Clustering"
    r"\Sweden_clustering_SQL\parquet\sweden_master_data.parquet"
)


def main() -> int:
    if not PARQUET_PATH.exists():
        print(f"ERROR: parquet not found at:\n  {PARQUET_PATH}", file=sys.stderr)
        return 1

    size_mb = PARQUET_PATH.stat().st_size / 1024 / 1024
    print(f"Reading: {PARQUET_PATH}")
    print(f"Size:    {size_mb:.1f} MB")
    print()

    con = duckdb.connect()
    # Use forward slashes inside the SQL string to avoid escape issues on Windows.
    sql_path = str(PARQUET_PATH).replace("\\", "/")
    df = con.execute(
        f"""
        SELECT YearFlag, COUNT(*) AS n
        FROM read_parquet('{sql_path}')
        GROUP BY YearFlag
        ORDER BY YearFlag
        """
    ).df()

    print("YearFlag population:")
    print(df.to_string(index=False))
    print()

    flags = set(df["YearFlag"].dropna().tolist())
    has_jun26 = "12M ending Jun 26" in flags
    print(f"Has '12M ending Jun 26': {has_jun26}")
    if has_jun26:
        print("-> SQL-patch path (a): extend WHERE clause to include it.")
    else:
        print("-> SQL-patch path (b): rewrite filter to InvoiceDate-based "
              "via _inject_dates pattern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
