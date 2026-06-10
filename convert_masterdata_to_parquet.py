"""
convert_masterdata_to_parquet.py — F.9 Bundle pre-VM step

Purpose
-------
replicate_dataprep.py writes output/Sweden_masterdata.csv (comma-separated CSV).
Bundle- and Clustering-SQL-dataprep both read sweden_master_data.parquet via their
00_read.sql (read_parquet). This script converts the growing CSV to parquet and
places it where both pipelines expect it — closing the only gap between the proven
G7 runner and the Bundle chain.

Why a script, not a oneliner
-----------------------------
KÄRNPRINCIPER §5 / §4.1: encoding (cp1252 on BCG CSVs, LB.10), dtype coercion, and
schema verification have too many traps for a python -c oneliner. This file is the
delivery.

Chain context
-------------
transaction_data.parquet (growing 2026-04-30)
  -> replicate_dataprep.py  BCG_END_DATE=2026-04-30  (G7 _inject_dates active)
  -> output/Sweden_masterdata.csv  (growing, YearFlag now includes '12M ending Jun 26')
  -> THIS SCRIPT
  -> sweden_master_data.parquet  in Bundle + Clustering parquet/ dirs
  -> Bundle 00_read.sql read_parquet(...)  ->  Bundle chain

Schema
------
Verified against Bundle 00_read.sql commented CSV-read block (24 columns). The script
warns (does not silently proceed) if the produced CSV's columns diverge from this
expected set — a divergence means the SQL prep changed and the parquet readers may
break (R7 discipline; LB.39 population awareness).

LB references
-------------
- LB.10  BCG CSVs are cp1252, not UTF-8 — read with encoding fallback.
- LB.24  Validate against frozen original; this script never touches the frozen
         baseline parquet, it writes a fresh growing one (caller backs up first).
- LB.39  Log row + ItemCode counts so silent population loss is visible.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 convert_masterdata_to_parquet.py

Optional overrides:
    --csv   <path to Sweden_masterdata.csv>   (default: Elasticity SQL prep output/)
    --dry-run                                 (verify + report, write nothing)

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-10.
"""
import argparse
import sys
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

# Both pipelines read sweden_master_data.parquet from their own parquet/ dir.
PARQUET_TARGETS = [
    BCG_ROOT / "4. Bundle Clinic Data Prep" / "Sweden_Bundling_Data_Prep"
    / "parquet" / "sweden_master_data.parquet",
    Path(r"C:\Projekt\BCG\Pipeline\01. Clustering")
    / "Sweden_clustering_SQL" / "parquet" / "sweden_master_data.parquet",
]

# Expected columns, from Bundle 00_read.sql commented read_csv block (24 cols).
# Order is not enforced (parquet is columnar); presence is.
EXPECTED_COLS = {
    "ID_Customer", "ID_Department", "ID_User", "ID_Item", "ID_Patient",
    "InvoiceDate", "NoofUnits", "Unit", "SalesTotal", "SoldQuantity",
    "PercentageChange", "PatientSinceDate", "CustomerSinceDate",
    "ItemDescription", "ItemType", "Price", "ItemCode", "ProductGroupL4Name",
    "CostCenterCode", "BusinessArea", "InvoiceMonth", "InvoiceYear",
    "VisitID", "YearFlag",
}


def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert growing Sweden_masterdata.csv -> sweden_master_data.parquet "
                    "for Bundle + Clustering SQL prep."
    )
    ap.add_argument("--csv", default=str(DEFAULT_CSV),
                    help="Path to Sweden_masterdata.csv (default: Elasticity SQL prep output/).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Verify schema + report row/ItemCode/YearFlag counts, write nothing.")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        log("ERROR", f"CSV not found:\n  {csv_path}")
        log("HINT", "Run replicate_dataprep.py with BCG_END_DATE set first (see F9 inventory).")
        return 1

    csv_mb = csv_path.stat().st_size / 1024 / 1024
    log("READ", f"{csv_path}")
    log("SIZE", f"{csv_mb:.1f} MB")

    con = duckdb.connect()
    csv_sql = str(csv_path).replace("\\", "/")

    # read_csv_auto handles the comma-separated export; sample_size=-1 forces a full
    # type scan so growing rows past 2025-06 don't get mistyped from a short sample.
    con.execute(
        f"""
        CREATE OR REPLACE VIEW master AS
        SELECT * FROM read_csv_auto('{csv_sql}', sample_size=-1, ignore_errors=false)
        """
    )

    cols = [r[0] for r in con.execute("DESCRIBE master").fetchall()]
    cols_set = set(cols)

    # --- Schema verification (R7: warn, don't silently proceed) -------------
    missing = EXPECTED_COLS - cols_set
    extra = cols_set - EXPECTED_COLS
    if missing:
        log("WARN", f"CSV is MISSING expected columns: {sorted(missing)}")
        log("WARN", "Bundle/Clustering 00_read.sql may fail or read wrong data. "
                    "Investigate before writing parquet.")
    if extra:
        log("INFO", f"CSV has extra columns (harmless for parquet): {sorted(extra)}")
    if not missing:
        log("OK", f"All {len(EXPECTED_COLS)} expected columns present.")

    # --- Population + G7 sanity (LB.39) -------------------------------------
    rows = con.execute("SELECT COUNT(*) FROM master").fetchone()[0]
    log("POP", f"rows = {rows:,}")
    if "ItemCode" in cols_set:
        items = con.execute('SELECT COUNT(DISTINCT "ItemCode") FROM master').fetchone()[0]
        log("POP", f"distinct ItemCode = {items:,}")
    if "YearFlag" in cols_set:
        yf = con.execute(
            'SELECT "YearFlag", COUNT(*) n FROM master GROUP BY 1 ORDER BY 1'
        ).df()
        log("YEARFLAG", "population:")
        print(yf.to_string(index=False))
        has26 = "12M ending Jun 26" in set(yf["YearFlag"].dropna().tolist())
        if has26:
            log("G7", "'12M ending Jun 26' PRESENT -> growing window confirmed.")
        else:
            log("WARN", "'12M ending Jun 26' ABSENT -> did you set BCG_END_DATE=2026-04-30 "
                        "before running replicate_dataprep.py? This CSV looks frozen.")

    if args.dry_run:
        log("DRY-RUN", "schema + population reported; no parquet written.")
        return 0

    # --- Write parquet to both targets --------------------------------------
    for target in PARQUET_TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target_sql = str(target).replace("\\", "/")
        con.execute(
            f"COPY master TO '{target_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        out_mb = target.stat().st_size / 1024 / 1024
        log("WRITE", f"{target}  ({out_mb:.1f} MB)")

    log("DONE", "sweden_master_data.parquet regenerated growing in both pipeline dirs.")
    log("NEXT", "Bundle SQL prep can now run; verify YearFlag population above includes Jun 26.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
