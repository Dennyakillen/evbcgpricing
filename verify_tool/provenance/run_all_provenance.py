"""
run_all_provenance.py
=====================
Master runner for the DATA PROVENANCE validation suite.

Runs each validate_*.py as a subprocess, captures output and status, and writes a
single combined Excel receipt (the "Logg" format the other suites use) to
verify_tool/receipts/YYYY-MM-DD/provenance/. Use this when you want a single
management-facing artefact showing which Step 6 inputs are fresh growing data and
which rest on frozen locked assumptions.

VALIDATION SCRIPTS RUN (in order):
  01. validate_step6_provenance.py   (Step 6 inputs: live growing vs frozen)

Run (PowerShell):
    cd "C:\\Projekt\\BCG\\verify_tool\\provenance"
    py -3.11 run_all_provenance.py

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Created:   2026-06-11
"""
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _provenance_helpers import (  # noqa: E402
    now_iso, now_file_stamp, get_receipt_dir,
    section, subsection, capture_stdout, write_log_receipt,
)

SCRIPTS = [
    "validate_step6_provenance.py",
    "validate_fallback_freshness.py",
]


def run_script(script_path, extra_args=None):
    """Run one validation script; return (exit_code, stdout, stderr, duration_sec)."""
    start = datetime.now()
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300,
        )
        duration = (datetime.now() - start).total_seconds()
        return result.returncode, result.stdout, result.stderr, duration
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT after 300s", 300.0
    except Exception as e:
        return -2, "", f"ERROR launching: {e}", 0.0


def extract_status(stdout):
    """Extract final status from stdout (>> Result: line)."""
    if not stdout:
        return "NO_OUTPUT"
    for line in reversed(stdout.splitlines()):
        if ">> Result:" in line:
            return line.split(">> Result:", 1)[1].strip()
    return "UNKNOWN"


def _run_master():
    section("DATA PROVENANCE SUITE - MASTER RUNNER")
    print(f"Run timestamp: {now_iso()}")
    print(f"Scripts to run: {len(SCRIPTS)}")
    print(f"Receipts will be saved to: {get_receipt_dir()}")
    print()

    run_dir = Path(__file__).resolve().parent
    results = []
    for idx, script in enumerate(SCRIPTS, 1):
        script_path = run_dir / script
        subsection(f"[{idx}/{len(SCRIPTS)}] Running: {script}")
        if not script_path.exists():
            print(f"  SKIP: file not found at {script_path}")
            results.append({"script": script, "status": "SKIP", "last_line": "File not found"})
            continue

        exit_code, stdout, stderr, duration = run_script(script_path)
        status = extract_status(stdout)
        out_lines = [ln for ln in stdout.splitlines() if ln.strip()]
        last_line = out_lines[-1] if out_lines else "(no output)"

        # Stream the child's full output so the receipt captures it verbatim.
        if stdout:
            print(stdout.rstrip())
        if exit_code not in (0, 1) and stderr:
            print("  STDERR (first 5 lines):")
            for ln in stderr.splitlines()[:5]:
                print(f"    {ln}")

        print(f"  Exit: {exit_code}  Status: {status}  Duration: {duration:.1f}s")
        results.append({"script": script, "status": status, "last_line": last_line[:200]})
        print()

    section("OVERALL PROVENANCE SUMMARY")
    n_pass = sum(1 for r in results if "PASS" in r["status"])
    n_review = sum(1 for r in results if "REVIEW" in r["status"])
    n_skip = sum(1 for r in results if r["status"] == "SKIP")
    print(f"  PASS:   {n_pass}")
    print(f"  REVIEW: {n_review}")
    print(f"  SKIP:   {n_skip}")
    print(f"  TOTAL:  {len(results)}")
    print()

    if n_skip:
        overall = "REVIEW"
    elif n_review:
        overall = "REVIEW"
    else:
        overall = "PASS"

    print(f"  >> OVERALL: {overall}")
    print()
    if overall == "PASS":
        print("  All Step 6 inputs are live growing data -- the blend is fully fresh.")
    else:
        print("  The blend mixes fresh and frozen inputs. See the provenance headline")
        print("  table and FD tickets above. This is the documented momentum shortcut;")
        print("  decision-makers must know which numbers rest on frozen locks.")
    print()
    return 0 if overall == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Run all data provenance validations.")
    ap.parse_args()

    with capture_stdout() as buf:
        exit_code = _run_master()
    log_text = buf.getvalue()
    receipt_dir = get_receipt_dir()
    receipt_path = receipt_dir / f"00_provenance_master_{now_file_stamp()}.xlsx"
    write_log_receipt(receipt_path, "run_all_provenance.py", log_text)
    print()
    print(f"  Master receipt (Logg): {receipt_path}")
    return exit_code if exit_code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
