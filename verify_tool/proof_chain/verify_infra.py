# -*- coding: utf-8 -*-
"""
verify_infra.py  --  verify_tool: infrastructure / environment readiness check
======================================================================
Answers ONE question before you trust any proof: "is the environment
ready to run the verify_tool suite?" Inspired by the verify_setup.py
pattern (file-exists + content-check), applied to the BCG pipeline.

Checks, in order:
  1. Python      - is a 3.11 interpreter with duckdb + pandas + openpyxl reachable?
  2. Suite       - are the five validators + README present in verify_tool?
  3. Facit       - do the frozen BCG facit files exist (the UNTOUCHED original,
                   not the drift-prone Pipeline/.../data copy)?
  4. Pipeline    - are the produced output CSVs + model output_summary.xlsx
                   on disk (what the validators read as "ours")?

Reports each as OK / MISSING / WRONG, like verify_setup.py. Does NOT run
the proofs - it confirms they CAN run. Run this first when returning to the
project, on a new machine, or before a live demo.

Developer: Jens Palmo, with AI advisor.
Run (PowerShell):
    py -3.11 verify_infra.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

_ORIG = Path(
    r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG"
    r"\BCG_orginal_V2_New\02. Elasticity"
)
_PIPE = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity")
_DP = _PIPE / "Sweden_Elasticity_Data_Prep_SQL" / "output"

# --- 1. Python interpreter requirement -----------------------------------
REQUIRED_MODULES = ["duckdb", "pandas", "openpyxl", "numpy"]

# --- 2. Suite files (must exist in verify_tool\) -------------------------
SUITE_FILES = {
    HERE / "verify_dataprep.py": ["replicate_dataprep.py", "--validate-only"],
    HERE / "verify_model.py": ["--family", "Rank corr", "rank()"],
    HERE / "verify_blend.py": ["fallback_blend.py", "--facit"],
    HERE / "verify_fallback.py": ["ProductKey", "elasticity_level"],
    HERE / "run_all.py": ["CONSOLIDATED MILESTONE", "write_receipt"],
    HERE / "README.md": ["Environment", "py -3.11"],
}

# --- 3. Frozen facit files (the UNTOUCHED original) ----------------------
FACIT_FILES = [
    _ORIG / "2. Product Cluster Level Models" / "data" / "0828_Sweden_weekly_model_data_P_C.csv",
    _ORIG / "2. Product Cluster Level Models" / "data" / "0828_Sweden_weekly_model_data_P_CH.csv",
    _ORIG / "2. Product Cluster Level Models" / "output" / "model" / "output_summary.xlsx",
    _ORIG / "3. Product Site Level Models" / "output" / "model" / "output_summary.xlsx",
    _ORIG / "5. Bundle Clinic Models" / "output" / "model" / "output_summary.xlsx",
    _ORIG / "2. Product Cluster Level Models" / "output" / "final_model_cluster_granularity.xlsx",
    _ORIG / "6. Fall Back Logic" / "input_data" / "Complete_Product_Data.xlsx",
    _ORIG / "6. Fall Back Logic" / "output_data" / "Final_Fallback_Data_20250930_091648.xlsx",
]

# --- 4. Our produced artefacts (what validators read as "ours") ----------
OURS_FILES = [
    _DP / "Sweden_weekly_model_data_P_C.csv",
    _DP / "Sweden_weekly_model_data_P_CH.csv",
    _PIPE / "2. Product Cluster Level Models" / "output" / "azure_run_model" / "output_summary.xlsx",
    _PIPE / "3. Product Site Level Models" / "output" / "azure_run_model" / "output_summary.xlsx",
    _PIPE / "5. Bundle Clinic Models" / "output" / "azure_run_model" / "output_summary.xlsx",
    Path(r"C:\Projekt\BCG\replicate_dataprep.py"),
    Path(r"C:\Projekt\BCG\fallback_blend.py"),
]

# --- 5. Full repo structure audit ----------------------------------------
REPO = Path(r"C:\Projekt\BCG")

# Files that SHOULD be in the repo root (core: docs, pipeline scripts, tools).
EXPECTED_ROOT = {
    # Documentation
    "README.md", "BCG_PRICING_PLAYBOOK.md", "INSIGHTS_BCG.md", "LESSONS_BCG.md",
    "ROADMAP.md", "NEXT_SESSION.md", "TECHNICAL_PREREQUISITES.md",
    "UBUNTU_AZURE_VM.md",
    # KÄRNPRINCIPER.md deliberately left out of EXPECTED: the Ä in the filename
    # mismatches under Windows filename encoding and false-flags MISSING. It is a
    # core doc but audited separately (see TOLERATED_ROOT).
    # Pipeline scripts the validators call
    "replicate_dataprep.py", "fallback_blend.py",
    # Tools / helpers (kept in root)
    "compare_to_facit.py", "compare_features_to_facit.py",
    "fix_config_encoding.py", "make_smoke_control.py",
    "inventory_for_gitignore.py", "patch_step6_xlwings.py",
    "Build-Structure.ps1", "Copy-Sources.ps1", "Scan-BCGFolder.ps1",
    "setup_step6_run.ps1",
    # Config
    ".gitignore",
}

# Files in root that look like run residue / backups - flagged STRAY (not deleted).
STRAY_ROOT = {
    "blended_output.csv", "blended_output_final_model.csv",
    "bcg_replication_blend.csv", "bcg_replication_blend_final_model.csv",
    "blend_facit_log.txt", "blend_log.txt",
    "run_dw_codelevel.txt", "gitignore_inventory.txt",
    ".gitignore.bak-20260526",
    "SESSION_2026-05-25_STEG5_STEG6.md",
}

# Tolerated extras: known, not core, not stray (leave alone, don't flag).
TOLERATED_ROOT = {
    "BCG_STRUCTURE_REPORT.md",
    "KÄRNPRINCIPER.md",  # core doc; audited as tolerated to avoid Ä-encoding false MISSING
}

# Files that SHOULD be in verify_tool\.
EXPECTED_VERIFY_TOOL = {
    "verify_dataprep.py", "verify_model.py", "verify_blend.py",
    "verify_fallback.py", "verify_infra.py", "run_all.py",
    "compare_features_to_facit.py", "README.md",
}

# Top-level dirs that should exist.
EXPECTED_DIRS = {"Elasticity", "Pipeline", "verify_tool"}
# Tolerated dirs (working copies / generated - leave alone).
TOLERATED_DIRS = {"_step6_run", "receipts", ".git", "__pycache__"}

# --- 6. DEEP per-folder audit (folders we own + can define a truth for) --
# All three model families share the SAME BCG code set. Site/Bundle are clean;
# Cluster has accumulated logs + .bak. The expected set lets the audit name the
# stray files one by one (logs, backups) and flag any missing core file.
MODEL_CODE_EXPECTED = {
    "constants.py", "data_prep_after_model_output.py", "data_prepration.py",
    "feature_selection.py", "launcher.py", "model.py", "regular_price.py",
    "utils.py",
}
# Some families also legitimately carry these (Cluster has the full pipeline run set).
MODEL_CODE_TOLERATED = {
    "excel_creation.py",  # cluster has it; not in site/bundle - tolerated, not stray
    "holiday_check0820.xlsx",
}
MODEL_SRC_EXPECTED = {"config.yml"}
MODEL_SRC_TOLERATED = set()  # config.yml.bak is a backup -> STRAY, not tolerated

# Stray patterns inside model code dirs: run logs + backups.
def _is_model_stray(name: str) -> bool:
    return (name.endswith(".bak")
            or name.endswith("_log.txt") or name.endswith("_log2.txt")
            or name.endswith("_fte.txt")
            or name.endswith(".py.bak"))

DATAPREP_SCRIPTS_EXPECTED = {"00_read.sql", "01_process.sql", "02_export.sql"}
DATAPREP_SCRIPTS_TOLERATED = {"PLACE_DuckDB_here.txt", "Readme.md"}

MODEL_DIRS = [
    "2. Product Cluster Level Models",
    "3. Product Site Level Models",
    "5. Bundle Clinic Models",
]


def _audit_folder(folder: Path, expected: set, stray: set, tolerated: set):
    """Return (ok, missing, stray_present, unexpected) by comparing disk to expected."""
    if not folder.exists():
        return [], sorted(expected), [], []
    on_disk = {p.name for p in folder.iterdir() if p.is_file()}
    ok = sorted(expected & on_disk)
    missing = sorted(expected - on_disk)
    stray_present = sorted(stray & on_disk)
    unexpected = sorted(on_disk - expected - stray - tolerated)
    return ok, missing, stray_present, unexpected



def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def find_python_311() -> list:
    if shutil.which("py"):
        return ["py", "-3.11"]
    known = r"C:\Users\jepa02\AppData\Local\Programs\Python\Python311\python.exe"
    if Path(known).exists():
        return [known]
    return [sys.executable]


def main() -> int:
    ok = 0
    fail = 0

    print("\n=== verify_tool — infrastructure readiness check ===")

    # 1. Python + modules
    _section("1. PYTHON INTERPRETER (3.11 with duckdb/pandas/openpyxl/numpy)")
    py = find_python_311()
    probe = "import " + ", ".join(REQUIRED_MODULES) + "; print('|'.join([" + \
            ", ".join(f"{m}.__version__" for m in REQUIRED_MODULES) + "]))"
    try:
        r = subprocess.run(py + ["-c", probe], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            vers = dict(zip(REQUIRED_MODULES, r.stdout.strip().split("|")))
            print(f"  OK       {' '.join(py)}")
            for m, v in vers.items():
                print(f"             {m} {v}")
            ok += 1
        else:
            print(f"  FEL      {' '.join(py)} missing modules:")
            print("           " + (r.stderr.strip().splitlines()[-1] if r.stderr else "unknown"))
            print("           -> the suite needs Python 3.11 with these installed.")
            fail += 1
    except Exception as e:
        print(f"  FEL      could not probe interpreter: {type(e).__name__}: {e}")
        fail += 1

    # 2. Suite files + content
    _section("2. SUITE FILES (verify_tool\\)")
    for path, required in SUITE_FILES.items():
        if not path.exists():
            print(f"  SAKNAS   {path.name}")
            fail += 1
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        missing = [s for s in required if s not in content]
        if missing:
            print(f"  FEL      {path.name}  -> saknar: {missing}")
            fail += 1
        else:
            print(f"  OK       {path.name}")
            ok += 1

    # 3. Frozen facit
    _section("3. FROZEN FACIT (untouched BCG original)")
    for path in FACIT_FILES:
        if path.exists():
            size = path.stat().st_size
            # P_CH facit known to drift to header-only; flag tiny files
            warn = "  [WARN tiny - possibly header-only/overwritten]" if size < 1000 else ""
            print(f"  OK       {path.name}  ({size:,} bytes){warn}")
            ok += 1
        else:
            print(f"  SAKNAS   {path.name}\n             {path.parent}")
            fail += 1

    # 4. Our produced artefacts
    _section("4. OUR ARTEFACTS (what validators read as 'ours')")
    for path in OURS_FILES:
        if path.exists():
            print(f"  OK       {path.name}  ({path.stat().st_size:,} bytes)")
            ok += 1
        else:
            print(f"  SAKNAS   {path.name}\n             {path.parent}")
            fail += 1

    # 5. Full structure audit: root + verify_tool + dirs
    _section("5. STRUCTURE AUDIT (root + verify_tool: missing / stray / unexpected)")

    # 5a. Root
    print("  [repo root]")
    r_ok, r_missing, r_stray, r_unexpected = _audit_folder(
        REPO, EXPECTED_ROOT, STRAY_ROOT, TOLERATED_ROOT)
    print(f"    EXPECTED present : {len(r_ok)}/{len(EXPECTED_ROOT)}")
    for m in r_missing:
        print(f"      MISSING  {m}   (expected core file not found)")
        fail += 1
    for s in r_stray:
        print(f"      STRAY    {s}   (run residue / backup - consider removing)")
    for u in r_unexpected:
        print(f"      UNKNOWN  {u}   (not in expected/stray/tolerated - review)")
    if not r_missing:
        ok += 1

    # 5b. verify_tool
    print("\n  [verify_tool]")
    vt = HERE
    v_ok, v_missing, v_stray, v_unexpected = _audit_folder(
        vt, EXPECTED_VERIFY_TOOL, set(), {"receipts", "__pycache__"})
    print(f"    EXPECTED present : {len(v_ok)}/{len(EXPECTED_VERIFY_TOOL)}")
    for m in v_missing:
        print(f"      MISSING  {m}")
        fail += 1
    for u in v_unexpected:
        print(f"      UNKNOWN  {u}   (review)")
    if not v_missing:
        ok += 1

    # 5c. top-level dirs
    print("\n  [top-level dirs]")
    on_disk_dirs = {p.name for p in REPO.iterdir() if p.is_dir()}
    d_missing = sorted(EXPECTED_DIRS - on_disk_dirs)
    d_unexpected = sorted(on_disk_dirs - EXPECTED_DIRS - TOLERATED_DIRS)
    for d in sorted(EXPECTED_DIRS & on_disk_dirs):
        print(f"      OK       {d}/")
    for d in d_missing:
        print(f"      MISSING  {d}/")
        fail += 1
    for d in d_unexpected:
        print(f"      UNKNOWN  {d}/   (review)")
    if not d_missing:
        ok += 1

    # 6. DEEP per-folder audit (model code dirs + dataprep scripts)
    _section("6. DEEP FOLDER AUDIT (file-by-file: expected / missing / stray)")
    pipe = _PIPE

    def deep_audit(folder: Path, expected: set, tolerated: set, stray_fn=None):
        """Print every file in folder classified; return missing count."""
        nonlocal ok, fail
        if not folder.exists():
            print(f"    [folder MISSING] {folder}")
            fail += 1
            return
        on_disk = sorted(p.name for p in folder.iterdir() if p.is_file())
        present_expected = [f for f in on_disk if f in expected]
        missing = sorted(expected - set(on_disk))
        for f in on_disk:
            if f in expected:
                print(f"      OK       {f}")
            elif f in tolerated:
                print(f"      ok(tol)  {f}   (allowed extra)")
            elif stray_fn and stray_fn(f):
                print(f"      STRAY    {f}   (log/backup - consider removing)")
            else:
                print(f"      UNKNOWN  {f}   (review)")
        for f in missing:
            print(f"      MISSING  {f}   (expected core file)")
            fail += 1
        if not missing:
            ok += 1

    for m in MODEL_DIRS:
        print(f"\n  [{m}\\code]")
        deep_audit(pipe / m / "code", MODEL_CODE_EXPECTED, MODEL_CODE_TOLERATED, _is_model_stray)
        print(f"  [{m}\\code\\src]")
        deep_audit(pipe / m / "code" / "src", MODEL_SRC_EXPECTED, MODEL_SRC_TOLERATED, _is_model_stray)

    print("\n  [Sweden_Elasticity_Data_Prep_SQL\\scripts]")
    deep_audit(pipe / "Sweden_Elasticity_Data_Prep_SQL" / "scripts",
               DATAPREP_SCRIPTS_EXPECTED, DATAPREP_SCRIPTS_TOLERATED)

    # Verdict
    _section("VERDICT")
    print(f"  OK: {ok}   FEL/SAKNAS: {fail}")
    if fail == 0:
        print("\n  Environment is ready. Run:  py -3.11 run_all.py --excel")
    else:
        print("\n  Resolve the FEL/SAKNAS items above before running the suite.")
        print("  Common fixes:")
        print("   - Python: run with 'py -3.11' (the .venv lacks duckdb).")
        print("   - Facit SAKNAS: ensure OneDrive 'Always keep on this device' (no stubs).")
        print("   - Ours SAKNAS: the VM run output / dataprep CSVs must be on disk.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
