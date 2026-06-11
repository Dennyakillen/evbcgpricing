"""
patch_bundle_yearflag.py — F.9 Bundle, replace hardcoded YearFlag filter with a
constant-anchor / no-upper-bound window filter. (v2 — fixes VARCHAR/DATE cast.)

Why
---
Bundle 01_process.sql had:
    YearFlag IN ('12M ending Jun 23','12M ending Jun 24','12M ending Jun 25')
which silently caps data at Jun 2025 (verify_bundle_growing.py -> CAPPED). The window
is already controlled upstream by replicate_dataprep.py; Bundle re-filtering is a
redundant silent-failure trap that re-caps every future fresh-data run.

v2 fix (2026-06-11)
-------------------
v1 replaced it with `week_starting_monday >= DATE '2022-07-01'` and crashed:
`Binder Error: Cannot compare VARCHAR and DATE`. The masterdata parquet was written
all_varchar=true (LB.49), so week_starting_monday is TEXT. v2 casts explicitly:
    CAST(week_starting_monday AS DATE) >= DATE '2022-07-01'
Type-agnostic: harmless if the column is already DATE.

Constant anchor (LF.2: 2022-07-01), NO upper bound -> Bundle inherits whatever window
the masterdata parquet carries; cannot silently cap; needs no yearly edit. YearFlag
COLUMN is untouched (downstream GROUP BY at lines 105/116 still work); only the FILTER
on it is removed.

Idempotent / recoverable
------------------------
The script first restores from .bak-yearflag-pre-g7 if that backup exists, so a prior
(broken) patch attempt is reverted before the correct patch is applied. The .bak is
the true pre-patch original (written on first run, never overwritten).

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 patch_bundle_yearflag.py --dry-run
    py -3.11 patch_bundle_yearflag.py

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Author: Claude advisor, 2026-06-11 (v2 cast fix).
"""
import argparse
import sys
from pathlib import Path

SQL = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\4. Bundle Clinic Data Prep"
    r"\Sweden_Bundling_Data_Prep\scripts\01_process.sql"
)
BAK = SQL.with_suffix(".sql.bak-yearflag-pre-g7")

OLD = "    YearFlag IN ('12M ending Jun 23','12M ending Jun 24','12M ending Jun 25')"

NEW = (
    "    -- G7 (Jens 2026-06-11): constant anchor LF.2, NO upper bound -> inherits the\n"
    "    -- window the masterdata parquet already carries (built by replicate_dataprep.py).\n"
    "    -- Cannot silently cap future fresh-data runs; YearFlag column kept for GROUP BY.\n"
    "    -- CAST: masterdata parquet written all_varchar=true (LB.49) -> week col is TEXT.\n"
    "    CAST(week_starting_monday AS DATE) >= DATE '2022-07-01'"
)


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SQL.exists():
        log("ERROR", f"not found: {SQL}")
        return 1

    # If a backup of the true original exists, restore from it first so we patch a
    # clean original (a prior broken patch attempt is reverted).
    if BAK.exists():
        original = BAK.read_text(encoding="utf-8")
        log("RESTORE", f"restoring from {BAK.name} before applying correct patch")
        text = original
    else:
        text = SQL.read_text(encoding="utf-8")

    count = text.count(OLD)
    if count == 0:
        log("ERROR", "target YearFlag IN (...) line not found verbatim in the original. "
                     "No change made. Existing YearFlag IN lines:")
        for i, line in enumerate(text.splitlines(), 1):
            if "YearFlag IN" in line:
                log("FOUND", f"line {i}: {line.strip()}")
        return 2

    new_text = text.replace(OLD, NEW)

    log("OLD", OLD.strip())
    log("NEW", "CAST(week_starting_monday AS DATE) >= DATE '2022-07-01'  (+ comments, no upper bound)")

    if args.dry_run:
        log("DRY-RUN", f"{count} occurrence(s) would be replaced; nothing written.")
        return 0

    # Write the true-original backup only if it doesn't already exist.
    if not BAK.exists():
        BAK.write_text(text, encoding="utf-8")
        log("BACKUP", f"{BAK.name} (true pre-patch original)")
    else:
        log("BACKUP", f"{BAK.name} preserved (original from first run)")

    SQL.write_text(new_text, encoding="utf-8")
    log("PATCHED", f"{count} occurrence(s) replaced in {SQL.name} with cast-safe filter")
    log("NEXT", "Re-run: py -3.11 run_bundle_dataprep.py  then  py -3.11 verify_bundle_growing.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
