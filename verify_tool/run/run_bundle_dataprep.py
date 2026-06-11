"""
run_bundle_dataprep.py — F.9 Bundle SQL data-prep runner (duckdb-Python)

Purpose
-------
Runs Bundle SQL data-prep (00_read -> 01_process -> 02_export) via the duckdb
Python API instead of the shipped run.ps1 + duckdb.exe, which AppLocker (LB.2) and
execution policy (LB.21) block in Jens's environment. Mirrors the proven pattern in
replicate_dataprep.py (the Elasticity SQL runner).

Why this is a thin runner, not a port
--------------------------------------
The three SQL files are run verbatim, in order. No date injection is needed here:
Bundle reads sweden_master_data.parquet which is ALREADY G7-windowed (regenerated
growing 2026-06-10, YearFlag through Jun 26). Bundle 01_process.sql's own
`YearFlag IN ('...23','...24','...25')` filter is therefore harmless — the parquet
data already sits inside the window; the filter just doesn't exclude anything new.
(If a future run needs Bundle restricted differently, that's a separate decision.)

Inputs the SQL expects (verified present 2026-06-11)
----------------------------------------------------
  parquet/sweden_master_data.parquet            (666 MB, growing — written 2026-06-10)
  input/sweden_bundle_analysis.csv              (18.67 MB)
  input/Sweden_Clinic_Cluster_Mapping.csv       (1382 B, 3 cols incl New_Cluster)
  input/Sweden_Interpolated_Productivity_time.csv (357 KB, FTE cap 2025-06 -> LB.14 NULLs expected)

Outputs (written to output/ by 02_export.sql)
---------------------------------------------
  Raw_Data_Clinic_Hospital.csv        (bundle-cluster weekly model input -> step 1 of model)
  Sweden_Clinic_Hospital_FTE_Data.csv (FTE per cluster/week)
  bundlegroup_bundle_mapping.csv      (bundle -> service group mapping)
  Bundle_Clinic_Data.csv              (exploded bundle membership)

Path discipline
---------------
The SQL uses relative macros (INPUT_DIR='input', OUTPUT_DIR='output',
PARQUET_DIR='parquet'), so the runner sets the DuckDB working directory to the
Sweden_Bundling_Data_Prep folder via os.chdir before executing (LB.20: relative
paths are location-dependent). Run from anywhere; --base-dir controls resolution.

LB references
-------------
- LB.2   AppLocker blocks duckdb.exe -> use duckdb Python API.
- LB.14  FTE cap 2025-06 -> NULL FTE for 2025-07..2026-04 weeks (expected, not a bug).
- LB.20  Relative SQL paths -> chdir to the data-prep folder before running.
- LB.31  On Windows PS, capture this script's output with redirection, not Tee 2>&1.
- R7     Trust the produced file, not the log line -> verify_outputs lists sizes.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 run_bundle_dataprep.py

Options:
    --base-dir <path>   Sweden_Bundling_Data_Prep folder (default: the known repo path)

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-11.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import duckdb


DEFAULT_BASE = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\4. Bundle Clinic Data Prep"
    r"\Sweden_Bundling_Data_Prep"
)

SQL_FILES = ["00_read.sql", "01_process.sql", "02_export.sql"]

# Files 02_export.sql writes (names per the verbatim COPY statements).
EXPECTED_OUTPUTS = [
    "Raw_Data_Clinic_Hospital.csv",
    "Sweden_Clinic_Hospital_FTE_Data.csv",
    "bundlegroup_bundle_mapping.csv",
    "Bundle_Clinic_Data.csv",
]

# Inputs that must exist before running (fail fast, don't crash mid-SQL).
REQUIRED_INPUTS = [
    ("parquet", "sweden_master_data.parquet"),
    ("input", "sweden_bundle_analysis.csv"),
    ("input", "Sweden_Clinic_Cluster_Mapping.csv"),
    ("input", "Sweden_Interpolated_Productivity_time.csv"),
]


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def preflight(base: Path) -> bool:
    ok = True
    for sub, name in REQUIRED_INPUTS:
        p = base / sub / name
        if not p.exists():
            log("MISSING", f"{sub}/{name}  -- required input not found")
            ok = False
        elif p.stat().st_size == 0:
            log("EMPTY", f"{sub}/{name}  -- 0 bytes (the cluster-mapping trap; investigate)")
            ok = False
        else:
            log("INPUT", f"{sub}/{name}  ({p.stat().st_size:,} bytes)")
    for fn in SQL_FILES:
        if not (base / "scripts" / fn).is_file():
            log("MISSING", f"scripts/{fn}  -- SQL file not found")
            ok = False
    return ok


def run_sql_files(con: duckdb.DuckDBPyConnection, scripts_dir: Path) -> None:
    for fname in SQL_FILES:
        path = scripts_dir / fname
        with open(path, "r", encoding="utf-8") as fh:
            script = fh.read()
        t0 = time.time()
        con.execute(script)  # duckdb runs all ;-separated statements
        log("RUN", f"{fname} executed in {time.time() - t0:6.1f}s")


def verify_outputs(base: Path) -> None:
    """R7: trust the file, not the log line."""
    out_dir = base / "output"
    found = {}
    if out_dir.is_dir():
        for fp in out_dir.iterdir():
            if fp.is_file():
                # 02_export may write 'output/\\name.csv' on some systems -> strip leading slashes/backslashes
                found[fp.name.lstrip("\\/")] = fp.stat().st_size
    for fn in EXPECTED_OUTPUTS:
        match = next((k for k in found if k.lower() == fn.lower()), None)
        if match is not None:
            log("VERIFY", f"output/{match}  {found[match]:>14,} bytes  -> OK")
        else:
            log("VERIFY", f"output/{fn}  MISSING (check export path / backslash issue)")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run Bundle SQL data-prep (00->01->02) via duckdb-Python."
    )
    ap.add_argument("--base-dir", default=str(DEFAULT_BASE),
                    help="Sweden_Bundling_Data_Prep folder containing input/ parquet/ output/ scripts/.")
    ap.add_argument("--threads", type=int, default=0, help="DuckDB threads (0 = default).")
    args = ap.parse_args()

    base = Path(args.base_dir)
    if not base.is_dir():
        log("ERROR", f"base-dir not found: {base}")
        return 1

    log("RUN", f"base-dir = {base}")
    if not preflight(base):
        log("ABORT", "preflight failed -- fix missing/empty inputs before running.")
        return 2

    (base / "output").mkdir(exist_ok=True)

    # LB.20: SQL macros are relative; run from the data-prep folder.
    prev_cwd = os.getcwd()
    os.chdir(base)
    try:
        con = duckdb.connect()
        if args.threads:
            con.execute(f"PRAGMA threads={args.threads}")
        con.execute("PRAGMA enable_object_cache")
        run_sql_files(con, base / "scripts")
    finally:
        os.chdir(prev_cwd)

    verify_outputs(base)
    log("DONE", "Bundle SQL data-prep complete. Outputs in Sweden_Bundling_Data_Prep/output/.")
    log("NEXT", "Ray basket build: 1.Data_Pre_Processing/code/2.Sweden_Bundle_Clinic_Model_Data_Creation.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
