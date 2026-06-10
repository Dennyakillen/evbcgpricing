"""
run_all_rationality.py
=======================
Master runner for output rationality validation suite.

Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Created:   2026-06-08

USAGE:
    cd C:/Projekt/Business_Analytics
    & ".\\.venv\\Scripts\\Activate.ps1"
    python C:/Projekt/BCG/verify_tool/output_rationality/run_all_rationality.py

    # With override:
    python .../run_all_rationality.py --output-summary "<path to xlsx>"

WHAT IT DOES:
  1. Runs each validate_*.py script as a subprocess
  2. Captures exit code and console output
  3. Writes a combined Excel summary receipt with status of each
  4. Returns 0 if all pass, 1 if any FAIL/REVIEW

VALIDATION SCRIPTS RUN (in order):
  01. validate_distribution.py              (aggregate elasticity profile)
  02. validate_outliers.py                  (extreme values)
  03. validate_drift_vs_bcg.py              (per-KEY delta vs BCG)
  04. validate_sign_flips.py                (sign changes vs BCG)
  05. validate_per_cluster.py               (cluster consistency)
  06. validate_per_itemcode_family.py       (family-level patterns)
  07. validate_top_leverage.py              (revenue x |elast| ranking)
  08. validate_significance_consistency.py  (sig rate vs BCG)
  09. validate_review_required.py           (aggregator - manual review list)
"""
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from _rationality_helpers import (
    now_iso, now_file_stamp, get_receipt_dir,
    section, subsection, capture_stdout, write_log_receipt,
)


# Scripts to run, in order
SCRIPTS = [
    "validate_distribution.py",
    "validate_outliers.py",
    "validate_drift_vs_bcg.py",
    "validate_sign_flips.py",
    "validate_per_cluster.py",
    "validate_per_itemcode_family.py",
    "validate_top_leverage.py",
    "validate_significance_consistency.py",
    "validate_review_required.py",
]


def run_script(script_path, extra_args=None):
    """Run a single validation script, return (exit_code, stdout, stderr, duration_sec)."""
    start = datetime.now()
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
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


def _run_master(output_summary_path=None):
    timestamp_iso = now_iso()
    run_dir = Path(__file__).parent

    section("OUTPUT RATIONALITY SUITE - MASTER RUNNER")
    print(f"Run timestamp: {timestamp_iso}")
    print(f"Scripts to run: {len(SCRIPTS)}")
    print(f"Receipts will be saved to: {get_receipt_dir()}")
    if output_summary_path:
        print(f"Output override: {output_summary_path}")
    print()

    # Build extra args once
    extra_args = []
    if output_summary_path:
        extra_args = ["--output-summary", str(output_summary_path)]

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

        exit_code, stdout, stderr, duration = run_script(script_path, extra_args)
        status = extract_status(stdout)

        out_lines = [ln for ln in stdout.splitlines() if ln.strip()]
        first_line = out_lines[0] if out_lines else "(no output)"
        last_line = out_lines[-1] if out_lines else "(no output)"

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
    section("OVERALL RATIONALITY SUMMARY")
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

    if n_fail > 0:
        overall = "FAIL"
    elif n_skip > 0 or n_review > 0:
        overall = "REVIEW"
    else:
        overall = "PASS"

    print(f"  >> OVERALL: {overall}")
    print()

    if overall == "PASS":
        print("  Model output is decision-ready.")
        print("  All rationality checks within acceptable bands.")
    elif overall == "REVIEW":
        print("  Model output needs human eyes on the REVIEW items above.")
        print("  See validate_review_required.py receipt for the consolidated list.")
    else:
        print("  Model output has FAIL items - do not use for price decisions.")
        print("  Investigate the FAILing checks before proceeding.")
    print()

    return 0 if overall == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Run all output rationality validations.")
    ap.add_argument("--output-summary", default=None,
                    help="Override path to output_summary.xlsx (passed to all scripts)")
    args = ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_master(output_summary_path=args.output_summary)
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"00_rationality_master_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "run_all_rationality.py", log_text)
    print()
    print(f"  Master receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
