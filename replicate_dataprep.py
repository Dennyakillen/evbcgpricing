#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replicate_dataprep.py  --  BCG Sweden Elasticity SQL data prep, ported to DuckDB-Python.

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Project:   evbcgpricing  --  Spar B, etapp B.1 (DuckDB golden reference)

WHAT THIS DOES
--------------
Runs BCG's three SQL files (00_read / 01_process / 02_export) VERBATIM through the
duckdb Python package instead of the blocked duckdb.exe (decision D4). It then validates
the two cluster-level outputs against BCG's frozen facit (the 0828_* CSVs) in layers
(population -> columns -> KPI -> row-level), per KARNPRINCIPER 8.3.

WHY IT EXISTS (read this before judging the design)
---------------------------------------------------
This is the ONLY place in the whole migration where a bit-for-bit check is possible:
BCG's own input files, BCG's own logic, only the engine swapped. Once the source moves
to live DW views, outputs can only be reconciled (not matched), because the data drifts.
So this script is a KEPT artifact -- the regression oracle the future T-SQL views are
checked against -- not a throwaway step.

CRITICAL interpretation of the result (do not skip):
  * Near-zero diff  -> logic ported correctly AND the 0828 facit came from this SQL version.
  * Small/moderate diff (a few %) -> most likely SQL drift between the Aug (0828) run and
    this Dec V2 SQL, OR accepted data drift. NOT necessarily a porting bug.
  * Large/structural diff -> porting/plumbing bug. Investigate before trusting anything.
The script SHOWS the diffs; it does not pretend a single threshold is truth (8.3).

USAGE (PowerShell, from inside the SQL folder so input/ parquet/ output/ resolve)
---------------------------------------------------------------------------------
  cd "C:\\Projekt\\BCG\\Pipeline\\02. Elasticity\\Sweden_Elasticity_Data_Prep_SQL"
  python -m replicate_dataprep --facit-dir "C:\\Projekt\\BCG\\Pipeline\\02. Elasticity\\2. Product Cluster Level Models\\data"

  # or fully explicit:
  python replicate_dataprep.py --base-dir "...\\Sweden_Elasticity_Data_Prep_SQL" --facit-dir "...\\data"

Output is intentionally STRUCTURAL only (counts, KPIs, PASS/FAIL) -- no raw data rows --
so it is safe to tee to a log and paste back. Tee + filter pattern (token-safe):
  python replicate_dataprep.py ... 2>&1 | Tee-Object run_dataprep.txt
  Select-String -Path run_dataprep.txt -Pattern "RUN|VERIFY|KPI|ROW|GATE|ERROR|Saved"
"""

from __future__ import annotations
import argparse
import os
import sys
import time

import duckdb

# ----------------------------------------------------------------------------------
# Configuration (tweak via CLI; defaults are sensible for the PoC)
# ----------------------------------------------------------------------------------
SQL_FILES = ["00_read.sql", "01_process.sql", "02_export.sql"]

# (live duckdb table, facit CSV filename, ours' cluster key column, facit->ours column aliases)
VALIDATIONS = [
    ("weekly_cluster", "0828_Sweden_weekly_model_data_P_C.csv", "Cluster",
     {"No of Sites": "No_of_Sites"}),
    ("weekly_ch",      "0828_Sweden_weekly_model_data_P_CH.csv", "New_Cluster",
     {"No of Sites": "No_of_Sites", "Cluster": "New_Cluster"}),
]

# For --validate-only: which produced output CSV corresponds to each "ours" table,
# so we can re-validate without re-running the (multi-minute) SQL pipeline.
OURS_OUTPUT = {
    "weekly_cluster": "Sweden_weekly_model_data_P_C.csv",
    "weekly_ch":      "Sweden_weekly_model_data_P_CH.csv",
}

# KPI measure columns to sum (those that should exist in both sides for P_C and P_CH).
MEASURE_COLS = [
    "SoldQuantity",
    "NoofUnits",
    "TotalNet",
    "QuantitySold(SalesTotal>0)",
    "No_of_Sites",
]
# The single measure used for row-level max-diff + correlation (the headline number).
HEADLINE_MEASURE = "TotalNet"


def log(tag: str, msg: str) -> None:
    """Structural log line. Keep these grep-able (RUN|VERIFY|KPI|ROW|GATE|ERROR|Saved)."""
    print(f"[{tag}] {msg}", flush=True)


def sniff_encoding(path: str) -> str:
    """Detect facit encoding by bytes, not by hope (mirrors MASTER_PYTHON xxd discipline).

    BCG's 0828 facit is single-byte (latin-1/cp1252) -- Swedish chars are invalid UTF-8,
    which is why a naive read_csv_auto crashes (R12b). We never compute on the text columns
    (we sum numbers and join on ASCII ItemCode), so latin-1 is always a safe fallback.
    Returns one of duckdb's accepted values: 'utf-16', 'utf-8', 'latin-1'.
    """
    with open(path, "rb") as fh:
        head = fh.read(4)
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"                      # BOM -> UTF-16
    if head[:3] == b"\xef\xbb\xbf":
        return "utf-8"                       # UTF-8 BOM
    with open(path, "rb") as fh:
        chunk = fh.read(2_000_000)
    try:
        chunk.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as e:
        # A multibyte char split at the chunk boundary is not a real failure.
        if e.start >= len(chunk) - 4:
            return "utf-8"
        return "latin-1"                     # cp1252/latin-1 single-byte (the 0828 case)


def _inject_dates(script: str, fname: str) -> str:
    """G7 (FAS F, Jens Palmo): if BCG_START_DATE/BCG_END_DATE are set, rewrite the
    hardcoded SQL date window in-memory. The SQL FILE ON DISK STAYS VERBATIM, so
    FR-1 reproduces exactly when no env vars are set. Only 01_process.sql has a
    date window. Logs any override so it never happens silently."""
    start = os.environ.get("BCG_START_DATE")
    end = os.environ.get("BCG_END_DATE")
    if not (start or end):
        return script
    new = script
    if start:
        new = new.replace("DATE '2022-07-01'", f"DATE '{start}'")
    if end:
        new = new.replace("DATE '2025-06-28'", f"DATE '{end}'")
    if new != script:
        log("G7", f"{fname}: SQL date window overridden -> start={start or 'orig'} end={end or 'orig'}")
    return new


def run_sql_files(con: duckdb.DuckDBPyConnection, scripts_dir: str) -> None:
    """Execute the three BCG SQL files whole, in order, verbatim (no edits)."""
    for fname in SQL_FILES:
        path = os.path.join(scripts_dir, fname)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"SQL file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            script = fh.read()
            script = _inject_dates(script, fname)
        t0 = time.time()
        con.execute(script)  # duckdb runs all ;-separated statements, comments included
        log("RUN", f"{fname} executed in {time.time() - t0:6.1f}s")


def verify_outputs(con: duckdb.DuckDBPyConnection, base_dir: str) -> None:
    """R7: trust the file, not the log line. List produced CSVs with size + row count."""
    out_dir = os.path.join(base_dir, "output")
    expected = [
        "Sweden_masterdata.csv",
        "item_description.csv",
        "Sweden_weekly_model_data_P_C.csv",
        "Sweden_weekly_model_data_P_CH.csv",
        "Sweden_weekly_model_data_site_level.csv",
        "Comple_Product_Data.csv",
    ]
    found = {}
    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            fp = os.path.join(out_dir, fn)
            if os.path.isfile(fp):
                found[fn] = os.path.getsize(fp)
    for fn in expected:
        # The verbatim 02_export.sql writes 'output/\\name.csv'; on Windows that lands as
        # 'output\\name.csv', on Linux it can land literally backslashed (logged: see G11/TD6).
        match = next((k for k in found if k.lstrip("\\/").lower() == fn.lower()), None)
        if match is not None:
            log("VERIFY", f"output/{match}  {found[match]:>12,} bytes  -> OK")
        else:
            log("VERIFY", f"output/{fn}  MISSING (check export path / backslash issue G11)")


def existing_cols(con: duckdb.DuckDBPyConnection, relation: str) -> list[str]:
    return [r[0] for r in con.execute(f"DESCRIBE {relation}").fetchall()]


def q1(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()[0]


def kpi_block(con: duckdb.DuckDBPyConnection, relation: str, key_col: str,
              cols_present: list[str]) -> dict:
    """Compute population + KPI numbers for one relation (live table or facit view)."""
    kpis: dict[str, float] = {}
    kpis["rows"] = q1(con, f'SELECT COUNT(*) FROM {relation}')
    if "ItemCode" in cols_present:
        kpis["items"] = q1(con, f'SELECT COUNT(DISTINCT "ItemCode") FROM {relation}')
    if "ProductGroupL4Name" in cols_present and key_col in cols_present:
        kpis["groups"] = q1(
            con,
            f'SELECT COUNT(*) FROM (SELECT DISTINCT "ProductGroupL4Name", "{key_col}" FROM {relation})'
        )
    for m in MEASURE_COLS:
        if m in cols_present:
            kpis[f"sum::{m}"] = q1(con, f'SELECT COALESCE(SUM(CAST("{m}" AS DOUBLE)),0) FROM {relation}')
    return kpis


def fmt(v: float) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1e6 or (v != 0 and abs(v) < 1e-3):
        return f"{v:.4e}"
    return f"{v:,.2f}" if isinstance(v, float) else f"{v}"


def pct_diff(ours: float, facit: float) -> float | None:
    if facit in (0, None) or ours is None:
        return None
    return (ours - facit) / facit * 100.0


def validate_one(con: duckdb.DuckDBPyConnection, table: str, facit_path: str,
                 key_col: str, tol_pct: float, eps: float, encoding: str = "auto",
                 aliases: dict | None = None) -> bool:
    tag = table
    aliases = aliases or {}
    log("KPI", f"==== validating {table}  vs  {os.path.basename(facit_path)} ====")
    if not os.path.isfile(facit_path):
        log("ERROR", f"{tag}: facit not found: {facit_path}")
        return False

    enc = sniff_encoding(facit_path) if encoding == "auto" else encoding
    log("KPI", f"{tag}: facit encoding = {enc}")
    # Register facit raw. read_csv_auto with full-file sampling for stable types.
    # encoding is detected because the 0828 facit is single-byte (latin-1), not UTF-8 (R12b).
    con.execute(
        f"CREATE OR REPLACE VIEW facit_raw AS "
        f"SELECT * FROM read_csv_auto('{facit_path.replace(chr(92), '/')}', "
        f"header=true, sample_size=-1, encoding='{enc}')"
    )
    # Rename known column-name drift to our canonical names (G12): the Aug facit uses
    # 'No of Sites' (spaces) and, for P_CH, 'Cluster' for what V2 calls 'New_Cluster'.
    # Data is identical; only the label drifted. Aliasing lets all layers align cleanly.
    raw_cols = existing_cols(con, "facit_raw")
    parts = [f'"{c}" AS "{aliases[c]}"' if c in aliases else f'"{c}"' for c in raw_cols]
    con.execute(f'CREATE OR REPLACE VIEW facit AS SELECT {", ".join(parts)} FROM facit_raw')
    if aliases:
        applied = {k: v for k, v in aliases.items() if k in raw_cols}
        log("KPI", f"{tag}: applied facit aliases {applied or '(none matched)'}")

    ours_cols = existing_cols(con, table)
    facit_cols = existing_cols(con, "facit")

    # Layer 1 + 2: population + column sets
    only_ours = [c for c in ours_cols if c not in facit_cols]
    only_facit = [c for c in facit_cols if c not in ours_cols]
    log("KPI", f"{tag}: columns ours={len(ours_cols)} facit={len(facit_cols)} "
               f"| only_ours={only_ours or '-'} | only_facit={only_facit or '-'}")
    if key_col not in facit_cols:
        # Be resilient: pick the other known key if the expected one is absent.
        alt = "New_Cluster" if key_col == "Cluster" else "Cluster"
        if alt in facit_cols and alt in ours_cols:
            log("KPI", f"{tag}: expected key '{key_col}' missing in facit, falling back to '{alt}'")
            key_col = alt
        else:
            log("ERROR", f"{tag}: key column '{key_col}' missing in facit; cannot align rows")

    common = [c for c in ours_cols if c in facit_cols]
    ours_kpi = kpi_block(con, table, key_col, common)
    facit_kpi = kpi_block(con, "facit", key_col, common)

    # Layer 3: KPI comparison with tolerance
    gate_ok = True
    keys = ["rows", "items", "groups"] + [f"sum::{m}" for m in MEASURE_COLS if f"sum::{m}" in ours_kpi]
    for k in keys:
        o = ours_kpi.get(k)
        f = facit_kpi.get(k)
        d = pct_diff(o, f) if (o is not None and f is not None) else None
        within = (d is None) or (abs(d) <= tol_pct)
        if not within:
            gate_ok = False
        flag = "ok" if within else "OUT"
        dtxt = "n/a" if d is None else f"{d:+.3f}%"
        log("KPI", f"{tag}: {k:<28} ours={fmt(o):>16}  facit={fmt(f):>16}  diff={dtxt:>10}  [{flag}]")

    # Layer 4 (best-effort): row-level alignment on (ItemCode, key, week)
    if {"ItemCode", "week_starting_monday"}.issubset(set(common)) and key_col in common:
        try:
            con.execute(f"""
                CREATE OR REPLACE TEMP VIEW _o AS
                SELECT CAST("ItemCode" AS VARCHAR) k_item,
                       CAST("{key_col}" AS VARCHAR) k_key,
                       CAST("week_starting_monday" AS DATE) k_week,
                       CAST("{HEADLINE_MEASURE}" AS DOUBLE) m
                FROM {table};
                CREATE OR REPLACE TEMP VIEW _f AS
                SELECT CAST("ItemCode" AS VARCHAR) k_item,
                       CAST("{key_col}" AS VARCHAR) k_key,
                       CAST("week_starting_monday" AS DATE) k_week,
                       CAST("{HEADLINE_MEASURE}" AS DOUBLE) m
                FROM facit;
            """)
            matched = q1(con, "SELECT COUNT(*) FROM _o JOIN _f USING (k_item,k_key,k_week)")
            only_o = q1(con, "SELECT COUNT(*) FROM _o ANTI JOIN _f USING (k_item,k_key,k_week)")
            only_f = q1(con, "SELECT COUNT(*) FROM _f ANTI JOIN _o USING (k_item,k_key,k_week)")
            mism = q1(con, f"""
                SELECT COUNT(*) FROM _o o JOIN _f f USING (k_item,k_key,k_week)
                WHERE ABS(o.m - f.m) > {eps} * GREATEST(1.0, ABS(f.m))
            """)
            corr = q1(con, "SELECT COALESCE(corr(o.m, f.m),0) FROM _o o JOIN _f f USING (k_item,k_key,k_week)")
            maxd = q1(con, "SELECT COALESCE(MAX(ABS(o.m - f.m)),0) FROM _o o JOIN _f f USING (k_item,k_key,k_week)")
            log("ROW", f"{tag}: matched={matched:,} only_ours={only_o:,} only_facit={only_f:,} "
                       f"{HEADLINE_MEASURE}_mismatch(>eps)={mism:,} max_abs_diff={maxd:.6g} corr={corr:.6f}")
        except Exception as e:
            log("ROW", f"{tag}: row-level compare skipped ({type(e).__name__}: {str(e)[:120]})")
    else:
        log("ROW", f"{tag}: row-level compare skipped (key columns not all present)")

    log("GATE", f"{tag}: {'PASS' if gate_ok else 'REVIEW'} "
               f"(aggregates within +/-{tol_pct}% : {gate_ok})")
    return gate_ok


def emit_code_baseline(con: duckdb.DuckDBPyConnection, base_dir: str) -> None:
    """B.3.5: write the grouping-invariant code-level baseline that the DW-native build
    (B.4) is validated against. Source = filtered_master_2 = the filtered, PG4-canonicalised
    population BEFORE the group-relative Top80 cut. Per ItemCode: Sum SalesExVAT (BCG
    'SalesTotal') and Sum SoldQuantity. Top80 is group-dependent, so it is deliberately
    excluded here -- only pre-Top80 per-code totals are comparable once grouping changes (D-B3)."""
    out = os.path.join(base_dir, "output", "code_level_baseline.csv").replace(chr(92), "/")
    try:
        con.execute(f"""
            COPY (
              SELECT ItemCode,
                     COUNT(*)            AS n_rows,
                     SUM(SalesTotal)     AS sum_SalesExVAT,
                     SUM(SoldQuantity)   AS sum_SoldQuantity
              FROM filtered_master_2
              GROUP BY ItemCode
              ORDER BY ItemCode
            ) TO '{out}' WITH (HEADER, DELIMITER ',')
        """)
        n, ssales, sqty = con.execute(
            "SELECT COUNT(DISTINCT ItemCode), SUM(SalesTotal), SUM(SoldQuantity) FROM filtered_master_2"
        ).fetchone()
        log("VERIFY", f"code_level_baseline.csv: {n:,} distinct ItemCode (pre-Top80) | "
                      f"Sum SalesExVAT={float(ssales):.4e} | Sum SoldQuantity={float(sqty):.4e}")
        log("Saved", f"code-level baseline -> output/code_level_baseline.csv")
    except Exception as e:
        log("ERROR", f"code baseline failed: {type(e).__name__}: {e}")


def register_ours_from_output(con: duckdb.DuckDBPyConnection, base_dir: str, table: str) -> None:
    """validate-only: load an already-produced output CSV as the 'ours' table, so we can
    re-validate without re-running the multi-minute SQL pipeline."""
    out_dir = os.path.join(base_dir, "output")
    want = OURS_OUTPUT[table]
    cand = None
    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            if fn.lstrip("\\/").lower() == want.lower():
                cand = os.path.join(out_dir, fn)
                break
    if cand is None:
        raise FileNotFoundError(f"{table}: expected output '{want}' not found in {out_dir}")
    enc = sniff_encoding(cand)
    con.execute(
        f"CREATE OR REPLACE VIEW {table} AS "
        f"SELECT * FROM read_csv_auto('{cand.replace(chr(92), '/')}', "
        f"header=true, sample_size=-1, encoding='{enc}')"
    )
    log("RUN", f"{table}: loaded from output/{os.path.basename(cand)} (encoding={enc})")


def main() -> int:
    ap = argparse.ArgumentParser(description="BCG Sweden elasticity SQL prep -> DuckDB-Python replicate + validate")
    ap.add_argument("--base-dir", default=os.getcwd(),
                    help="Folder containing input/ parquet/ output/ scripts/ (default: cwd)")
    ap.add_argument("--scripts-dir", default=None,
                    help="Folder with 00_read/01_process/02_export.sql (default: <base-dir>/scripts)")
    ap.add_argument("--facit-dir", default=None,
                    help="Folder with the 0828_* facit CSVs. If omitted, only replicates (no validation).")
    ap.add_argument("--tolerance-pct", type=float, default=2.0,
                    help="Aggregate KPI tolerance band in percent (default 2.0)")
    ap.add_argument("--strict-eps", type=float, default=1e-6,
                    help="Relative epsilon for row-level measure mismatch (default 1e-6)")
    ap.add_argument("--threads", type=int, default=0, help="DuckDB threads (0 = duckdb default)")
    ap.add_argument("--facit-encoding", default="auto",
                    choices=["auto", "utf-8", "latin-1", "utf-16"],
                    help="Facit CSV encoding. 'auto' sniffs (0828 is latin-1, not UTF-8 -- R12b).")
    ap.add_argument("--validate-only", action="store_true",
                    help="Skip the SQL run; validate the already-produced output CSVs against facit.")
    ap.add_argument("--no-code-baseline", action="store_true",
                    help="Skip emitting the pre-Top80 code-level baseline (B.3.5) on a full run.")
    args = ap.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    scripts_dir = args.scripts_dir or os.path.join(base_dir, "scripts")
    out_dir = os.path.join(base_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    # The SQL uses relative INPUT_DIR()='input' etc. -> resolve by running with cwd=base_dir.
    # This is why we replicate the original Readme's "cd into this folder" behaviour and
    # change nothing in the SQL itself (verbatim replication).
    os.chdir(base_dir)
    log("RUN", f"base-dir   = {base_dir}")
    log("RUN", f"scripts    = {scripts_dir}")
    log("RUN", f"facit-dir  = {args.facit_dir or '(none -> replicate only)'}")

    con = duckdb.connect()  # in-memory; 1 GB parquet fits comfortably, spill if needed
    # Keep spill inside the project so a low-RAM laptop never fills the system temp.
    tmp = os.path.join(out_dir, "duckdb_tmp")
    os.makedirs(tmp, exist_ok=True)
    con.execute(f"PRAGMA temp_directory='{tmp.replace(chr(92), '/')}'")
    if args.threads > 0:
        con.execute(f"PRAGMA threads={args.threads}")

    try:
        if args.validate_only:
            if not args.facit_dir:
                log("ERROR", "validate-only requires --facit-dir")
                return 2
            log("RUN", "validate-only: skipping SQL run, loading existing output CSVs")
            for table, _, _, _ in VALIDATIONS:
                register_ours_from_output(con, base_dir, table)
        else:
            run_sql_files(con, scripts_dir)
            verify_outputs(con, base_dir)
            if not args.no_code_baseline:
                emit_code_baseline(con, base_dir)
    except Exception as e:
        log("ERROR", f"{'load' if args.validate_only else 'SQL execution'} failed: {type(e).__name__}: {e}")
        return 2

    if not args.facit_dir:
        log("Saved", "replication complete (no facit-dir given -> validation skipped)")
        return 0

    all_ok = True
    for table, facit_name, key_col, aliases in VALIDATIONS:
        facit_path = os.path.join(args.facit_dir, facit_name)
        ok = validate_one(con, table, facit_path, key_col, args.tolerance_pct,
                          args.strict_eps, args.facit_encoding, aliases)
        all_ok = all_ok and ok

    log("Saved", f"validation complete. overall={'PASS' if all_ok else 'REVIEW'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
