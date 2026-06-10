"""
convert_masterdata_to_parquet.py — F.9 Bundle pre-VM step (v2, streaming)

Purpose
-------
replicate_dataprep.py writes output/Sweden_masterdata.csv (~7 GB, comma-separated).
Bundle- and Clustering-SQL-dataprep both read sweden_master_data.parquet via their
00_read.sql (read_parquet). This script converts the growing CSV to parquet and
places it where both pipelines expect it.

v2 change (2026-06-10, eleganstest KÄRNPRINCIPER §8.2)
------------------------------------------------------
v1 did a full-file type scan (sample_size=-1) into a VIEW, then DESCRIBE, then COPY —
two passes over 7 GB, slow and RAM-heavy. v2 streams CSV -> parquet in a single
DuckDB COPY (no full pre-scan), then verifies the FINISHED parquet (columnar, fast)
for schema + YearFlag population. One heavy pass instead of two; verification moved
to the cheap side.

Type-safety note (v3, 2026-06-10)
---------------------------------
v2 used read_csv_auto with a row sample to infer types. It crashed: ItemType was
typed BIGINT from a clean 20k-row sample, then a product description with embedded
quotes + comma (line 654262) spilled into the column and broke the CAST (LB.49).
v3 reads with all_varchar=true: no type inference at all, so no sample-gambling and
no crash. Faithful because Bundle/Clustering 00_read.sql CAST every column to its
target type themselves -- typing belongs to the consumer, not this transport layer.
Diagnosed: all_varchar reads all 27,435,679 rows strict, zero loss.
The --full-scan flag is retained for CLI parity but is now a no-op (all_varchar
needs no sampling).

Chain context
-------------
transaction_data.parquet (growing 2026-04-30)
  -> replicate_dataprep.py  BCG_END_DATE=2026-04-30  (G7 _inject_dates active)
  -> output/Sweden_masterdata.csv  (growing, YearFlag incl '12M ending Jun 26')
  -> THIS SCRIPT  (streaming CSV -> parquet)
  -> sweden_master_data.parquet  in Bundle + Clustering parquet/ dirs
  -> Bundle 00_read.sql read_parquet(...)  ->  Bundle chain

LB references
-------------
- LB.10  BCG CSVs are cp1252; this CSV is runner-produced, read_csv_auto handles it.
- LB.24  Never touches the frozen baseline parquet; caller backs it up first.
- LB.39  Logs row + ItemCode counts on the produced parquet so silent loss is visible.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 convert_masterdata_to_parquet.py

Options:
    --csv <path>     Path to Sweden_masterdata.csv (default: Elasticity SQL prep output/)
    --full-scan      Use sample_size=-1 (full type scan) -- only if a type error appears
    --bundle-only    Write only the Bundle parquet target (skip Clustering)

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-10 (v2 streaming rewrite).
"""
import argparse
import sys
import time
from pathlib import Path

import duckdb


# --- Paths -----------------------------------------------------------------
BCG_ROOT = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity")

DEFAULT_CSV = (
    BCG_ROOT
    / "Sweden_Elasticity_Data_Prep_SQL"
    / "output"
    / "Sweden_masterdata.csv"
)

BUNDLE_PARQUET = (
    BCG_ROOT / "4. Bundle Clinic Data Prep" / "Sweden_Bundling_Data_Prep"
    / "parquet" / "sweden_master_data.parquet"
)
CLUSTERING_PARQUET = (
    Path(r"C:\Projekt\BCG\Pipeline\01. Clustering")
    / "Sweden_clustering_SQL" / "parquet" / "sweden_master_data.parquet"
)

EXPECTED_COLS = {
    "ID_Customer", "ID_Department", "ID_User", "ID_Item", "ID_Patient",
    "InvoiceDate", "NoofUnits", "Unit", "SalesTotal", "SoldQuantity",
    "PercentageChange", "PatientSinceDate", "CustomerSinceDate",
    "ItemDescription", "ItemType", "Price", "ItemCode", "ProductGroupL4Name",
    "CostCenterCode", "BusinessArea", "InvoiceMonth", "InvoiceYear",
    "VisitID", "YearFlag",
}


def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Stream growing Sweden_masterdata.csv -> sweden_master_data.parquet."
    )
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--full-scan", action="store_true",
                    help="Use sample_size=-1 (full type scan); only if a type error appears.")
    ap.add_argument("--bundle-only", action="store_true",
                    help="Write only the Bundle parquet target.")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        log("ERROR", f"CSV not found:\n  {csv_path}")
        log("HINT", "Run replicate_dataprep.py with BCG_END_DATE=2026-04-30 first.")
        return 1

    csv_gb = csv_path.stat().st_size / 1024 / 1024 / 1024
    log("READ", f"{csv_path}")
    log("SIZE", f"{csv_gb:.2f} GB")

    targets = [BUNDLE_PARQUET]
    if not args.bundle_only:
        targets.append(CLUSTERING_PARQUET)

    # all_varchar=true: no type inference -> no sample-based mistyping, no crash on
    # malformed-but-quoted description fields (LB.49). Bundle/Clustering 00_read.sql
    # CAST every column to its target type themselves, so the parquet is a faithful
    # text transport layer. Diagnosed 2026-06-10: reads all 27,435,679 rows, zero loss.
    # --full-scan kept for parity but unused now (all_varchar needs no sampling).
    csv_sql = str(csv_path).replace("\\", "/")
    read_expr = f"read_csv('{csv_sql}', all_varchar=true, header=true)"

    con = duckdb.connect()

    # --- Stream CSV -> parquet (single pass, low RAM) -----------------------
    # Parse the 7 GB CSV exactly once into the first target, then write any
    # remaining targets from the just-written parquet (cheap columnar copy).
    first = targets[0]
    first.parent.mkdir(parents=True, exist_ok=True)
    first_sql = str(first).replace("\\", "/")

    log("WRITE", f"streaming -> {first.name} (heavy pass) ...")
    t0 = time.time()
    con.execute(
        f"COPY (SELECT * FROM {read_expr}) "
        f"TO '{first_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    log("WRITE", f"{first}  ({first.stat().st_size/1024/1024:.1f} MB) in {time.time()-t0:.1f}s")

    for extra in targets[1:]:
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra_sql = str(extra).replace("\\", "/")
        con.execute(
            f"COPY (SELECT * FROM read_parquet('{first_sql}')) "
            f"TO '{extra_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        log("WRITE", f"{extra}  ({extra.stat().st_size/1024/1024:.1f} MB)")

    # --- Verify the FINISHED parquet (columnar, fast) -----------------------
    cols = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{first_sql}')"
    ).fetchall()]
    cols_set = set(cols)

    missing = EXPECTED_COLS - cols_set
    extra_cols = cols_set - EXPECTED_COLS
    if missing:
        log("WARN", f"parquet MISSING expected columns: {sorted(missing)}")
        log("WARN", "Bundle/Clustering 00_read.sql may break. Investigate before running prep.")
    else:
        log("OK", f"All {len(EXPECTED_COLS)} expected columns present.")
    if extra_cols:
        log("INFO", f"extra columns (harmless): {sorted(extra_cols)}")

    rows = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{first_sql}')"
    ).fetchone()[0]
    log("POP", f"rows = {rows:,}")
    if "ItemCode" in cols_set:
        items = con.execute(
            f'SELECT COUNT(DISTINCT "ItemCode") FROM read_parquet(\'{first_sql}\')'
        ).fetchone()[0]
        log("POP", f"distinct ItemCode = {items:,}")
    if "YearFlag" in cols_set:
        yf = con.execute(
            f'SELECT "YearFlag", COUNT(*) n FROM read_parquet(\'{first_sql}\') '
            f'GROUP BY 1 ORDER BY 1'
        ).df()
        log("YEARFLAG", "population:")
        print(yf.to_string(index=False))
        has26 = "12M ending Jun 26" in set(yf["YearFlag"].dropna().tolist())
        if has26:
            log("G7", "'12M ending Jun 26' PRESENT -> growing window confirmed.")
        else:
            log("WARN", "'12M ending Jun 26' ABSENT -> CSV looks frozen; "
                        "was BCG_END_DATE=2026-04-30 set during replicate_dataprep.py?")

    log("DONE", "sweden_master_data.parquet regenerated growing.")
    log("NEXT", "Bundle SQL prep can run; confirm YearFlag includes Jun 26 above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
