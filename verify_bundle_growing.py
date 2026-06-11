"""
verify_bundle_growing.py — F.9 Bundle, growing-window verification on outputs

Purpose
-------
Bundle SQL data-prep ran and produced Raw_Data_Clinic_Hospital.csv. But Bundle's
01_process.sql line 20 has `WHERE YearFlag IN ('...23','...24','...25')`. The source
parquet contains ALL years (Jun 17..Jun 26), so this filter could silently drop
everything after Jun 25 -- the same G7 trap we fixed at masterdata level but which
may still live in Bundle's own SQL.

This script trusts the file, not the log line (R7 / LB.39): it reports the YearFlag
population and max week in the produced output, so we KNOW whether Bundle is growing
or got capped at Jun 2025.

Verdict
-------
- '12M ending Jun 26' present, max_week in 2026  -> growing confirmed, proceed to Ray.
- Jun 26 absent, max_week ~2025-06               -> Bundle SQL capped it; patch
  01_process.sql line 20 (add Jun 26 or make date-based) and re-run dataprep.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 verify_bundle_growing.py

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-11.
"""
import sys
from pathlib import Path

import duckdb

OUT = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\4. Bundle Clinic Data Prep"
    r"\Sweden_Bundling_Data_Prep\output\Raw_Data_Clinic_Hospital.csv"
)


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    if not OUT.exists():
        log("ERROR", f"not found: {OUT}")
        return 1

    p = str(OUT).replace("\\", "/")
    con = duckdb.connect()

    df = con.execute(
        f"""
        SELECT YearFlag,
               COUNT(*) AS n,
               MIN(week_starting_monday) AS min_week,
               MAX(week_starting_monday) AS max_week
        FROM read_csv('{p}', all_varchar=true)
        GROUP BY YearFlag
        ORDER BY YearFlag
        """
    ).df()

    log("FILE", f"{OUT.name}")
    print(df.to_string(index=False))
    print()

    flags = set(df["YearFlag"].dropna().tolist())
    max_week_all = con.execute(
        f"SELECT MAX(week_starting_monday) FROM read_csv('{p}', all_varchar=true)"
    ).fetchone()[0]
    log("MAX-WEEK", f"latest week_starting_monday in output = {max_week_all}")

    if "12M ending Jun 26" in flags:
        log("VERDICT", "GROWING confirmed -> '12M ending Jun 26' present in Bundle output.")
        log("ACTION", "Proceed to Ray basket build "
                      "(2.Sweden_Bundle_Clinic_Model_Data_Creation.py).")
        return 0
    else:
        log("VERDICT", "CAPPED -> '12M ending Jun 26' ABSENT. Bundle 01_process.sql "
                       "line 20 filtered out the new months.")
        log("ACTION", "Patch Sweden_Bundling_Data_Prep/scripts/01_process.sql: add "
                      "'12M ending Jun 26' to the YearFlag IN (...) list (or make it "
                      "date-based), then re-run run_bundle_dataprep.py.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
