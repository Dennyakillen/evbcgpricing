#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_survival_regen.py -- close the BA survival bug: run_data REGEN -> _v2 (contract-checked)
==============================================================================================
Purpose
    run_data.py:87 points REGEN_SCRIPT at regenerate_transaction_parquet_chunked.py
    (NO _v2). Business_Analytics tracks ONLY _v2 in git (deps measurement +
    BA cleanup, 2026-07-02) -- so a fresh clone crashes in the FÖRE chain. This
    repoints to _v2, but ONLY AFTER measuring that _v2 satisfies the exact CLI
    contract run_data calls it with (--end, --out, --overwrite). Repointing to a
    file whose contract differs would trade a clone-crash for a silent runtime
    break -- the BA checklist's own rule ("kontraktstest, inte diff-räkning").

    Two files, one commit (the fourth-map/grind class -- else a gate lies):
      1. run_data.py:87           REGEN_SCRIPT -> ..._v2.py
      2. dry_run_full_pipeline.py the "regen (BA-venv)" path entry that checks
                                  the v1 path in CODE -> ..._v2.py

    Commit 6cda4da's message claimed "REGEN repointed to _v2 (measured)" but the
    repoint never happened (measured false 2026-07-02). This patch makes the
    message finally true; note that in the commit body.

Guard: if _v2 does NOT satisfy the contract (missing --end/--out/--overwrite),
    the patch REFUSES to repoint and tells you -- measure, don't guess.

Idempotent, timestamped .bak, preserves line endings, UTF-8 no BOM (LB.86).

Upstream   : orchestration/runners/run_data.py, verify_tool/dry_run_full_pipeline.py
             (+ measures C:/Projekt/Business_Analytics/regenerate_*_v2.py)
Downstream : a fresh clone can run the FÖRE chain (survival test); dry_run_full green
Lessons    : L.43 (right file wrong dir), survival/clone axis, contract-over-diff,
             fourth-map class (code grid must move with the anchor), LB.86
Run        : py -3.11 tools\\patch_survival_regen.py
             py -3.11 tools\\patch_survival_regen.py --repo <r> --ba-root <r>   (test)
Developer  : Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

V1 = "regenerate_transaction_parquet_chunked.py"
V2 = "regenerate_transaction_parquet_chunked_v2.py"
REQUIRED_FLAGS = ["--end", "--out", "--overwrite"]   # the contract run_data calls with


def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}", flush=True)


def _read(p: Path) -> str:
    with open(p, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _write(p: Path, text: str) -> None:
    bak = p.with_name(p.name + f".bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(p, bak)
    log("BACKUP", bak.name)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    log("SAVED", str(p))


def measure_contract(ba_root: Path) -> bool:
    """True only if _v2 exists AND declares all flags run_data calls with."""
    v2 = ba_root / V2
    if not v2.exists():
        log("FAIL", f"contract: {V2} not found in {ba_root} -- cannot repoint")
        return False
    src = _read(v2)
    missing = [f for f in REQUIRED_FLAGS
               if not re.search(r'add_argument\(\s*["\']' + re.escape(f), src)]
    if missing:
        log("FAIL", f"contract: {V2} is MISSING flags {missing} -- NOT a drop-in for "
                    f"run_data (which calls --end/--out/--overwrite). Repoint REFUSED.")
        return False
    log("OK", f"contract: {V2} declares all of {REQUIRED_FLAGS} -- safe drop-in")
    return True


def repoint(path: Path, label: str) -> bool:
    """Replace V1 -> V2 in a file (only the exact chunked.py, not v2 already)."""
    if not path.exists():
        log("FAIL", f"{label}: not found: {path}")
        return False
    text = _read(path)
    # already pointing at v2 and no bare v1 left?
    bare_v1 = re.search(re.escape(V1) + r'(?!["\']?_?v2)', text)  # V1 not followed by v2
    if V2 in text and V1 not in text:
        log("OK", f"{label}: already points at _v2 (idempotent)")
        return True
    # Replace only occurrences of V1 that are NOT already the v2 filename.
    # Since V2 contains V1 as a prefix, guard by replacing 'chunked.py' -> 'chunked_v2.py'
    # only where not already '_v2'.
    new_text = re.sub(re.escape(V1) + r'(?!_v2)', V2, text)
    if new_text == text:
        log("WARN", f"{label}: no bare {V1} occurrence found -- nothing changed")
        return True
    if path.suffix == ".py":
        try:
            ast.parse(new_text.replace("\r\n", "\n"))
        except SyntaxError as e:
            log("FAIL", f"{label}: repoint broke syntax ({e}) -- NOT written")
            return False
    _write(path, new_text)
    n = len(re.findall(re.escape(V1) + r'(?!_v2)', text))
    log("PATCH", f"{label}: {V1} -> {V2} ({n} occurrence(s))")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Close BA survival bug: repoint REGEN to _v2 (contract-checked).")
    ap.add_argument("--repo", default=r"C:\Projekt\BCG")
    ap.add_argument("--ba-root", default=r"C:\Projekt\Business_Analytics")
    ap.add_argument("--skip-contract", action="store_true",
                    help="(NOT recommended) repoint without measuring v2's flags.")
    args = ap.parse_args()

    repo = Path(args.repo)
    ba = Path(args.ba_root)
    run_data = repo / "orchestration" / "runners" / "run_data.py"
    dry_full = repo / "verify_tool" / "dry_run_full_pipeline.py"

    # 1. contract gate
    if not args.skip_contract:
        if not ba.exists():
            log("WARN", f"BA root not found ({ba}) -- cannot measure contract. "
                        f"Run on the machine with Business_Analytics, or --skip-contract "
                        f"only if you have verified _v2's flags yourself.")
            return 2
        if not measure_contract(ba):
            log("ABORT", "contract not satisfied -- repoint refused (measure, don't guess).")
            return 3
    else:
        log("WARN", "contract check SKIPPED by flag -- you asserted _v2 is a drop-in.")

    # 2. repoint both maps, same run
    ok1 = repoint(run_data, "run_data.py")
    ok2 = repoint(dry_full, "dry_run_full_pipeline.py")

    # 3. verify
    log("VERIFY", "final state:")
    for path, label in [(run_data, "run_data.py"), (dry_full, "dry_run_full_pipeline.py")]:
        if not path.exists():
            log("VERIFY", f"  {label}: MISSING FILE")
            continue
        t = _read(path)
        pts_v2 = V2 in t
        bare_v1 = bool(re.search(re.escape(V1) + r'(?!_v2)', t))
        log("VERIFY", f"  {label}: points_v2={pts_v2}, bare_v1_left={bare_v1}")

    ok = ok1 and ok2
    if ok:
        log("DONE", "survival bug closed. Verify a fresh-clone can run FÖRE:\n"
                    "  py -3.11 orchestration\\tools\\survival_test.py\n"
                    "then: git add orchestration/runners/run_data.py "
                    "verify_tool/dry_run_full_pipeline.py tools/patch_survival_regen.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
