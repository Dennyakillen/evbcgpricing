"""
diagnose_masterdata_csv.py — F.9 Bundle, CSV read-strategy diagnosis

Purpose
-------
convert_masterdata_to_parquet.py v2 crashed: DuckDB auto-typed ItemType as BIGINT
from a 20k-row sample, then hit a malformed row (line 654262) where a product
description with embedded quotes + comma spilled into the ItemType column. This
script determines the correct read strategy without guessing:

  1. raw line count of the CSV (wc-equivalent)
  2. rows readable with all_varchar=true (no type inference -> no BIGINT crash)
  3. rows readable with all_varchar=true + ignore_errors=true
  4. whether (2) and (3) differ -> tells us if malformed rows are dropped

Decision logic
--------------
- If (2) == rawlines-1 (header): all_varchar alone reads every row faithfully.
  -> convert script should use all_varchar=true, NO ignore_errors. Zero loss.
- If (2) < rawlines-1 but (3) recovers more: there are genuinely malformed rows.
  -> we must understand how many and whether BCG's baseline also dropped them
     (LB.39: silent population loss). Do NOT proceed to parquet until understood.

Why all_varchar is the faithful path
-------------------------------------
Bundle/Clustering 00_read.sql CAST every column to its target type themselves.
The parquet is just a transport layer between the SQL prep and those readers, so
moving data as text (all_varchar) and letting 00_read.sql do the typing matches
how BCG's own read was structured (strict_mode=false, null_padding=true, ItemType
as VARCHAR in the commented read_csv block).

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 diagnose_masterdata_csv.py

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-10.
"""
import sys
from pathlib import Path

import duckdb

CSV = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity"
    r"\Sweden_Elasticity_Data_Prep_SQL\output\Sweden_masterdata.csv"
)


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    if not CSV.exists():
        log("ERROR", f"not found: {CSV}")
        return 1

    csv_sql = str(CSV).replace("\\", "/")
    con = duckdb.connect()

    # 1) raw physical line count (fast, streamed by DuckDB)
    rawlines = con.execute(
        f"SELECT COUNT(*) FROM read_csv('{csv_sql}', all_varchar=true, "
        f"header=false, ignore_errors=true)"
    ).fetchone()[0]
    log("RAW", f"lines readable (all_varchar, ignore_errors, header=false) = {rawlines:,}")

    # 2) all_varchar, header=true, strict (no ignore) -- does it read clean?
    try:
        n_strict = con.execute(
            f"SELECT COUNT(*) FROM read_csv('{csv_sql}', all_varchar=true, header=true)"
        ).fetchone()[0]
        log("VARCHAR", f"rows (all_varchar=true, strict) = {n_strict:,}")
        strict_ok = True
    except Exception as e:
        log("VARCHAR", f"strict read FAILED: {type(e).__name__}: {str(e)[:160]}")
        n_strict = None
        strict_ok = False

    # 3) all_varchar + ignore_errors (recovers past malformed rows)
    n_ignore = con.execute(
        f"SELECT COUNT(*) FROM read_csv('{csv_sql}', all_varchar=true, "
        f"header=true, ignore_errors=true)"
    ).fetchone()[0]
    log("IGNORE", f"rows (all_varchar=true, ignore_errors=true) = {n_ignore:,}")

    # --- verdict ------------------------------------------------------------
    print()
    if strict_ok and n_strict == n_ignore:
        log("VERDICT", "all_varchar=true reads EVERY row, no errors, no loss.")
        log("ACTION", "convert script: use all_varchar=true (no ignore_errors). Zero loss.")
    elif strict_ok and n_strict != n_ignore:
        log("VERDICT", f"strict read succeeded but counts differ "
                       f"(strict={n_strict:,} vs ignore={n_ignore:,}) -- unexpected, inspect.")
    else:
        dropped = (rawlines - 1) - n_ignore if rawlines else None
        log("VERDICT", "all_varchar strict FAILS -> malformed rows exist.")
        if dropped is not None:
            log("LOSS", f"ignore_errors drops ~{dropped:,} row(s) vs raw line count.")
        log("ACTION", "Do NOT write parquet yet. Decide: does BCG baseline also drop "
                      "these? (LB.39). If yes -> ignore_errors matches BCG. If no -> "
                      "fix the malformed rows upstream or quote-handling in the export.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
