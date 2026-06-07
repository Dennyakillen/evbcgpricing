"""
run_all.py  --  verify_tool: run the full proof chain (FR-1..7) in milestone order
======================================================================================
Orchestrator. Runs the five standalone validators in the order of the
root README "Project Status - Milestone Tracker", streams each one's full
output, then prints a consolidated milestone table at the end - one row per
FR with PASS / REVIEW and the headline number.

This does NOT replace the standalone validators - it calls them. Run any one
of them alone when a decision-maker questions that specific part; run this
when you want the whole model proven in one pass (e.g. for a report).

Environment: each validator is invoked with Python 3.11 (the interpreter that
carries duckdb/pandas - the .venv and 3.13 do not). The orchestrator locates
3.11 via the launcher; override with --python if needed.

Developer: Jens Palmo, with AI advisor.
Run (PowerShell, from the verify_tool folder):
    py -3.11 run_all.py
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (label, FR, script, args) - order mirrors the README milestone tracker.
STEPS = [
    ("Data prep (rows / revenue / volume)", "FR-1", "verify_dataprep.py", []),
    ("Cluster model (product x cluster)",   "FR-4", "verify_model.py", ["--family", "cluster"]),
    ("Site model (product x site)",         "FR-5", "verify_model.py", ["--family", "site"]),
    ("Bundle model (baskets / clinic)",     "FR-6", "verify_model.py", ["--family", "bundle"]),
    ("Cluster blend / step 5 (43 reps)",    "FR-3", "verify_blend.py", []),
    ("Fallback weave / step 6 (F1-F7)",     "FR-7", "verify_fallback.py", []),
]


def find_python_311(override: str | None) -> list:
    """Return a command prefix that runs Python 3.11 (has duckdb/pandas)."""
    if override:
        return [override]
    # Prefer the Windows launcher: py -3.11
    if shutil.which("py"):
        return ["py", "-3.11"]
    # Fallback: the known global 3.11 path on this machine
    known = r"C:\Users\jepa02\AppData\Local\Programs\Python\Python311\python.exe"
    if Path(known).exists():
        return [known]
    # Last resort: whatever runs this orchestrator
    return [sys.executable]


def parse_verdict(text: str, fr: str) -> dict:
    """Pull a headline + PASS/REVIEW signal out of a validator's output."""
    res = {"headline": "", "status": "?"}

    # dataprep / blend: explicit overall / representative-set verdicts
    if "overall=PASS" in text or "representative-set match: PASS" in text:
        res["status"] = "PASS"
    if "overall=REVIEW" in text or "representative-set match: REVIEW" in text:
        res["status"] = "REVIEW"

    # verify_model: population + rank-corr + decision-relevant line
    m = re.search(r"Population match\s*:\s*(\d+)/(\d+)", text)
    if m:
        pop_o, pop_f = m.group(1), m.group(2)
        rc = re.search(r"Rank corr \(Spearman\)\s*:\s*([\d.]+)", text)
        dr = re.search(r"Decision-relevant\s*:\s*(\d+)/(\d+)\s+significant groups identical \(([\d.]+)%\)", text)
        parts = [f"pop {pop_o}/{pop_f}"]
        if rc:
            parts.append(f"rank-corr {rc.group(1)}")
        if dr:
            parts.append(f"decision-rel {dr.group(1)}/{dr.group(2)} ({dr.group(3)}%)")
        res["headline"] = ", ".join(parts)
        # model validators report deviations, not PASS/FAIL - mark structural OK
        # when population is identical and rank-corr is high.
        if pop_o == pop_f:
            res["status"] = "PASS" if (rc and float(rc.group(1)) >= 0.90) else "REVIEW"

    # dataprep headline: rows + corr (from the [ROW] log line)
    m = re.search(r"matched=([\d,]+)\s+only_ours=\d+\s+only_facit=\d+.*?corr=([\d.]+)", text)
    if m and not res["headline"]:
        res["headline"] = f"rows {m.group(1)}, corr {m.group(2)}"

    # blend headline: representatives
    m = re.search(r"Representative set\s*:\s*(\d+)/(\d+) match BCG", text)
    if m:
        res["headline"] = f"{m.group(1)}/{m.group(2)} representatives match"

    # fallback headline: correlation + level match
    m = re.search(r"correlation \(ours,facit\)\s*:\s*([\d.]+)", text)
    if m:
        lvl = re.search(r"matching level\s*:\s*[\d,]+\s*/\s*[\d,]+\s*\(([\d.]+)%\)", text)
        res["headline"] = f"corr {m.group(1)}"
        if lvl:
            res["headline"] += f", level match {lvl.group(1)}%"
        if float(m.group(1)) >= 0.99:
            res["status"] = "PASS"

    return res


def write_receipt(full_log: str, interpreter: str) -> Path:
    """Write a dated Excel receipt: a single 'Logg' sheet holding the run's raw
    stdout exactly as the terminal produced it (Consolas monospace, one line per
    cell). Mirrors the analyspaket.py reference: no colour, no interpretation -
    the unprocessed log, with stdout's own column alignment preserved visually by
    the monospace font. data_type='s' forces every line to be text so lines that
    start with '=' (e.g. ===-rules) are not parsed as formulas (#VALUE!)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
    except ImportError:
        print("[warn] openpyxl not available - skipping Excel receipt.")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    receipts = HERE / "receipts"
    receipts.mkdir(exist_ok=True)
    out = receipts / f"verify_receipt_{today}.xlsx"

    MONO = "Consolas"
    wb = Workbook()
    ws = wb.active
    ws.title = "Logg"
    ws.sheet_view.showGridLines = False

    # A small header band, then the raw log verbatim.
    preamble = [
        f"verify_tool full proof chain — receipt {stamp}",
        f"interpreter: {interpreter}",
        "Developer: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)",
        "Raw stdout below, verbatim. Monospace preserves the column alignment.",
        "=" * 76,
        "",
    ]
    all_lines = preamble + full_log.splitlines()
    for i, line in enumerate(all_lines, start=1):
        c = ws.cell(row=i, column=1)
        c.value = line
        c.data_type = "s"  # force text: '='-prefixed lines must not become formulas
        c.font = Font(name=MONO, size=9, color="1A1A1A")
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
    ws.column_dimensions["A"].width = 120
    ws.freeze_panes = "A7"  # keep the preamble band visible

    wb.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the full verify_tool proof chain (FR-1..7).")
    ap.add_argument("--python", default=None,
                    help="Python interpreter to run validators with (default: py -3.11)")
    ap.add_argument("--stop-on-error", action="store_true",
                    help="Stop if a validator crashes (default: continue and report).")
    ap.add_argument("--excel", action="store_true",
                    help="Also write a dated Excel receipt to verify_tool\\receipts\\.")
    args = ap.parse_args()

    py = find_python_311(args.python)

    # Tee: everything we 'emit' is both printed and captured for the Excel receipt.
    _buf = []
    def emit(s=""):
        print(s)
        _buf.append(s)

    emit("=" * 72)
    emit("verify_tool - FULL PROOF CHAIN (FR-1..7), milestone order")
    emit("=" * 72)
    emit(f"interpreter: {' '.join(py)}")
    emit("Each validator runs standalone below; consolidated table at the end.")

    results = []
    for label, fr, script, extra in STEPS:
        script_path = HERE / script
        if not script_path.exists():
            results.append((fr, label, "MISSING", f"{script} not found in {HERE}"))
            continue
        emit("\n" + "#" * 72)
        emit(f"# {fr}  -  {label}")
        emit("#" * 72)
        cmd = py + [str(script_path)] + extra
        emit(f"$ {' '.join(cmd)}\n")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            results.append((fr, label, "TIMEOUT", "exceeded 30 min"))
            if args.stop_on_error:
                break
            continue
        out = (proc.stdout or "") + (proc.stderr or "")
        emit(out.rstrip())
        verdict = parse_verdict(out, fr)
        status = verdict["status"]
        if proc.returncode != 0 and status == "?":
            status = "ERROR"
        results.append((fr, label, status, verdict["headline"]))
        if status in ("ERROR", "TIMEOUT") and args.stop_on_error:
            break

    # --- consolidated milestone table ---------------------------------
    emit("\n" + "#" * 72)
    emit("# CONSOLIDATED MILESTONE TABLE  (mirrors README Project Status)")
    emit("#" * 72)
    emit(f"{'FR':<6} {'Milestone':<38} {'Status':<8} Headline")
    emit("-" * 72)
    icon = {"PASS": "[PASS]", "REVIEW": "[~]", "ERROR": "[ERR]",
            "TIMEOUT": "[TIME]", "MISSING": "[MISS]", "?": "[?]"}
    for fr, label, status, headline in results:
        emit(f"{fr:<6} {label[:37]:<38} {icon.get(status, status):<8} {headline}")
    emit("-" * 72)

    passed = sum(1 for _, _, s, _ in results if s == "PASS")
    total = len(results)
    emit(f"\n{passed}/{total} milestones PASS.")
    emit("Note: model families (FR-4/5/6) report deviations, not binary pass -")
    emit("'PASS' here means identical population + rank-corr >= 0.90. Read each")
    emit("family's SUMMARY above for the decision-relevant detail; finer levels")
    emit("(Site/Bundle) carry weak-signal tail groups the fallback discards (IB.9).")

    # optional Excel receipt - the full captured log as a 'Logg' sheet
    if args.excel:
        path = write_receipt("\n".join(_buf), " ".join(py))
        if path:
            print(f"\n[receipt] Excel saved: {path}")

    # overall exit code: non-zero if anything errored/timed out (not for REVIEW)
    hard_fail = any(s in ("ERROR", "TIMEOUT", "MISSING") for _, _, s, _ in results)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
