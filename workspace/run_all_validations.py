"""
run_all_validations.py
=======================
Master runner: executes all validation scripts in sequence and produces
a summary Excel receipt with overall PASS/FAIL status.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-07

USAGE:
    cd C:\Projekt\Business_Analytics
    & ".\.venv\Scripts\Activate.ps1"
    python C:\Projekt\BCG\workspace\run_all_validations.py

WHAT IT DOES:
  1. Runs each validate_*.py script as a subprocess
  2. Captures exit code and console output
  3. Writes a combined Excel summary receipt with status of each
  4. Returns 0 if all pass, 1 if any FAIL/REVIEW

VALIDATION SCRIPTS RUN (in order):
  01. validate_extraction_coverage.py  (revenue coverage vs BCG facit)
  02. validate_cluster_seed.py         (0808 mapping integrity)
  03. validate_facit_selection.py      (0828 selection + pg4 integrity)
  04. validate_fte_coverage.py         (FTE NULL share + revenue impact)
  05. validate_dropped_rows.py         (filter funnel forensics)
  06. validate_cluster_distribution.py (revenue/quantity per cluster)
  07. validate_volume_quantity.py      (VAT, NoofUnits, outliers)
  08. validate_baseline_replication.py (per-ItemCode drift vs BCG facit)
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from _validation_helpers import (
    now_iso, now_file_stamp, get_receipt_dir,
    section, subsection, write_receipt,
)


# Scripts to run, in order
SCRIPTS = [
    "validate_extraction_coverage.py",
    "validate_cluster_seed.py",
    "validate_facit_selection.py",
    "validate_fte_coverage.py",
    "validate_dropped_rows.py",
    "validate_cluster_distribution.py",
    "validate_volume_quantity.py",
    "validate_baseline_replication.py",
]


def run_script(script_path):
    """Run a single validation script, return (exit_code, stdout, stderr, duration_sec)."""
    start = datetime.now()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 min per script
        )
        duration = (datetime.now() - start).total_seconds()
        return result.returncode, result.stdout, result.stderr, duration
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT after 300s", 300.0
    except Exception as e:
        return -2, "", f"ERROR launching: {e}", 0.0


def extract_status(stdout):
    """Extract final status from stdout."""
    if not stdout:
        return "NO_OUTPUT"
    for line in reversed(stdout.splitlines()):
        if ">> Result:" in line:
            return line.split(">> Result:", 1)[1].strip()
        if "Status:" in line and ("PASS" in line or "REVIEW" in line or "FAIL" in line):
            return line.split("Status:", 1)[1].strip()
    return "UNKNOWN"


def main():
    timestamp_iso = now_iso()
    timestamp_file = now_file_stamp()
    run_dir = Path(__file__).parent

    section("VALIDATION SUITE - MASTER RUNNER")
    print(f"Run timestamp: {timestamp_iso}")
    print(f"Scripts to run: {len(SCRIPTS)}")
    print(f"Receipts will be saved to: {get_receipt_dir()}")
    print()

    results = []
    for idx, script in enumerate(SCRIPTS, 1):
        script_path = run_dir / script
        subsection(f"[{idx}/{len(SCRIPTS)}] Running: {script}")

        if not script_path.exists():
            print(f"  SKIP: file not found at {script_path}")
            results.append({
                "script": script,
                "status": "SKIP",
                "exit_code": -3,
                "duration_sec": 0.0,
                "first_line": "File not found",
                "last_line": "",
            })
            continue

        exit_code, stdout, stderr, duration = run_script(script_path)
        status = extract_status(stdout)

        # Get first and last meaningful line for log
        out_lines = [ln for ln in stdout.splitlines() if ln.strip()]
        first_line = out_lines[0] if out_lines else "(no output)"
        last_line = out_lines[-1] if out_lines else "(no output)"

        # Show essential output
        if exit_code == 0:
            print(f"  Exit: 0  Status: {status}  Duration: {duration:.1f}s")
        else:
            print(f"  Exit: {exit_code}  Status: {status}  Duration: {duration:.1f}s")
            if stderr:
                print(f"  STDERR (first 3 lines):")
                for ln in stderr.splitlines()[:3]:
                    print(f"    {ln}")

        print(f"  Last line: {last_line}")

        results.append({
            "script": script,
            "status": status,
            "exit_code": exit_code,
            "duration_sec": round(duration, 2),
            "first_line": first_line[:200],
            "last_line": last_line[:200],
        })
        print()

    # ----- Overall summary -----
    section("OVERALL VALIDATION SUMMARY")
    n_pass = sum(1 for r in results if "PASS" in r["status"])
    n_review = sum(1 for r in results if "REVIEW" in r["status"])
    n_fail = sum(1 for r in results if "FAIL" in r["status"])
    n_skip = sum(1 for r in results if r["status"] == "SKIP")
    n_info = sum(1 for r in results if r["status"] == "INFO")
    n_other = len(results) - n_pass - n_review - n_fail - n_skip - n_info

    print(f"  PASS:   {n_pass}")
    print(f"  REVIEW: {n_review}")
    print(f"  FAIL:   {n_fail}")
    print(f"  INFO:   {n_info}")
    print(f"  SKIP:   {n_skip}")
    print(f"  OTHER:  {n_other}")
    print(f"  TOTAL:  {len(results)}")
    print()

    overall = "PASS" if (n_fail == 0 and n_skip == 0) else ("FAIL" if n_fail > 0 else "REVIEW")
    print(f"  >> OVERALL: {overall}")
    print()

    # ----- Write master receipt -----
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"00_master_summary_{timestamp_file}.xlsx"

    summary_rows = [
        [idx + 1, r["script"], r["status"], r["exit_code"],
         f"{r['duration_sec']}s", r["last_line"]]
        for idx, r in enumerate(results)
    ]

    sheets = [
        {
            "name": "Summary",
            "subtitle": f"Generated: {timestamp_iso}",
            "headers": ["#", "Script", "Status", "Exit", "Duration", "Last line"],
            "rows": summary_rows,
            "notes": [
                f"OVERALL: {overall}",
                f"PASS: {n_pass}, REVIEW: {n_review}, FAIL: {n_fail}, INFO: {n_info}, SKIP: {n_skip}",
                f"Receipts saved to: {receipt_dir}",
            ],
        },
        {
            "name": "Metadata",
            "subtitle": "",
            "headers": ["Key", "Value"],
            "rows": [
                ["Script", "run_all_validations.py"],
                ["Run timestamp", timestamp_iso],
                ["Total scripts", len(results)],
                ["Overall status", overall],
                ["Receipt directory", str(receipt_dir)],
                ["Developer", "Jens Palmö, Evidensia"],
            ],
        },
    ]
    write_receipt(receipt_path, "Validation Suite - Master Summary", sheets)
    print(f"  Master receipt: {receipt_path}")
    print()

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
