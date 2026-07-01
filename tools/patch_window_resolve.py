#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_window_resolve.py -- kill the silent date-lock in the orchestrators
==========================================================================
Purpose
    Three surgical, measured changes (source-verified 2026-07-01):

    1. CREATE orchestration/shared/window.py with resolve_window_end():
       last day of the latest CLOSED month. Single owner of the growing-
       window default (derive, never declare twice).

    2. PATCH run_data.py + run_after.py:
       --end default "2026-04-30" (hardcoded, stale) -> None, and after
       parse_args() resolve None via resolve_window_end(). An orchestrator
       run without --end today would silently rebuild the APRIL window --
       the exact silent date-lock class (LB.50/G7) this project keeps
       paying for. Explicit --end always wins (re-runs of an existing
       window MUST pass their own --end).

    3. MEASURE-AND-FIX run_data.REGEN_SCRIPT: the constant points at
       regenerate_transaction_parquet_chunked.py, but only ..._v2.py is
       tracked in Business_Analytics (git ls-files 2026-07-01). If v1 is
       absent on disk AND v2 exists, repoint the constant (L.43/four-maps
       class). If v1 exists (untracked), leave it and report.

    Idempotent, timestamped .bak per touched file, preserves each file's
    own line endings, UTF-8 without BOM (LB.86). Verifies syntax of the
    patched files with ast.parse before declaring success.

Upstream   : orchestration/runners/run_data.py, run_after.py (anchors unique,
             verified: 1x default="2026-04-30", 1x args = ap.parse_args() each)
Downstream : every future fresh-window run of the FORE and EFTER chains
Lessons    : LB.50/G7 (silent date-lock), LB.85 (declare once), LB.86, L.43
Run        : py -3.11 tools\\patch_window_resolve.py
             py -3.11 tools\\patch_window_resolve.py --repo <root> --ba-root <root>   (test mode)
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

WINDOW_PY = '''"""
window.py -- growing-window resolution (single owner of the window default)
============================================================================
resolve_window_end() -> 'YYYY-MM-DD' for the last day of the latest CLOSED
month. The growing window keeps its fixed anchor (WINDOW_ANCHOR); only the
end moves. Orchestrators call this when --end is not given, so no runner
ever carries a stale hardcoded date again (silent date-lock class, LB.50/G7).

WARNING -- re-run vs new window: window_run_id derives from (start, end), so
auto-resolving on a later calendar date yields a NEW run_id and a NEW status
file. To RE-run an existing window (e.g. maj = 2022-07-01..2026-05-31), pass
that window's --end explicitly. Auto-resolve is for FRESH windows only,
after the parquet has been regenerated for the new period (LB.50).

Developer: Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
"""
from __future__ import annotations

from datetime import date, timedelta

WINDOW_ANCHOR = "2022-07-01"   # BCG frozen start; growing window keeps this fixed


def resolve_window_end(today: "date | None" = None) -> str:
    """Last day of the latest fully closed month, as 'YYYY-MM-DD'.

    Example: called on 2026-07-01 (or any day in July 2026) -> '2026-06-30'.
    If the DW load for the just-closed month lags, pass --end explicitly.
    """
    t = today or date.today()
    last_closed = t.replace(day=1) - timedelta(days=1)
    return last_closed.isoformat()
'''

RESOLVE_BLOCK = (
    "    if args.end is None:\n"
    "        from window import resolve_window_end\n"
    "        args.end = resolve_window_end()\n"
    "        print(f\"[window] --end not given -> auto: {args.end} (latest closed month). \"\n"
    "              f\"Re-running an existing window? Pass its --end explicitly.\")\n"
)

V1_NAME = "regenerate_transaction_parquet_chunked.py"
V2_NAME = "regenerate_transaction_parquet_chunked_v2.py"


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


def patch_runner(path: Path) -> bool:
    """Returns True on success (patched or already patched)."""
    if not path.exists():
        log("FAIL", f"runner not found: {path}")
        return False
    text = _read(path)
    if "from window import resolve_window_end" in text:
        log("OK", f"{path.name}: already patched (resolve block present)")
        return True

    eol = "\r\n" if "\r\n" in text else "\n"

    # 1. default="2026-04-30" -> default=None (anchor verified unique per file)
    if text.count('default="2026-04-30"') != 1:
        log("FAIL", f"{path.name}: expected exactly 1 occurrence of "
                    f'default="2026-04-30", found {text.count(chr(34).join(["default=", "2026-04-30"]))} -- aborting this file')
        return False
    text = text.replace('default="2026-04-30"', "default=None")
    log("PATCH", f"{path.name}: --end default -> None")

    # 2. insert resolve block right after args = ap.parse_args()
    m = re.search(r"^([ \t]*)args = ap\.parse_args\(\)\r?\n", text, re.M)
    if not m:
        log("FAIL", f"{path.name}: parse_args() anchor not found")
        return False
    block = RESOLVE_BLOCK.replace("\n", eol)
    text = text[: m.end()] + block + text[m.end():]
    log("PATCH", f"{path.name}: resolve_window_end block inserted after parse_args()")

    # syntax gate before writing (a patcher that breaks the runner is worse than none)
    try:
        ast.parse(text.replace("\r\n", "\n"))
    except SyntaxError as e:
        log("FAIL", f"{path.name}: patched text does not parse ({e}) -- NOT written")
        return False
    _write(path, text)
    return True


def fix_regen_path(run_data: Path, ba_root: Path) -> bool:
    """Measure, don't guess: repoint REGEN_SCRIPT only if v1 absent AND v2 present."""
    v1, v2 = ba_root / V1_NAME, ba_root / V2_NAME
    if not ba_root.exists():
        log("SKIP", f"regen path: BA root not found ({ba_root}) -- could not measure, leaving as is")
        return True
    if v1.exists():
        log("OK", f"regen path: {V1_NAME} exists on disk (untracked?) -- constant left as is. "
                  f"Consider committing it (E.8) or migrating to _v2 deliberately.")
        return True
    if not v2.exists():
        log("WARN", f"regen path: NEITHER {V1_NAME} nor {V2_NAME} found in {ba_root} -- "
                    f"REGEN step is a dead path either way; investigate before running run_data without --skip-regen")
        return True
    text = _read(run_data)
    if V2_NAME in text:
        log("OK", "regen path: already points at _v2")
        return True
    if V1_NAME not in text:
        log("WARN", "regen path: constant line not found -- leaving as is")
        return True
    text = text.replace(V1_NAME + '"', V2_NAME + '"')
    try:
        ast.parse(text.replace("\r\n", "\n"))
    except SyntaxError as e:
        log("FAIL", f"run_data.py: regen repoint broke syntax ({e}) -- NOT written")
        return False
    _write(run_data, text)
    log("PATCH", f"run_data.py: REGEN_SCRIPT -> {V2_NAME} (measured: v1 absent, v2 present)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Kill the silent date-lock: window.py + runner patches.")
    ap.add_argument("--repo", default=r"C:\Projekt\BCG")
    ap.add_argument("--ba-root", default=r"C:\Projekt\Business_Analytics")
    args = ap.parse_args()

    repo = Path(args.repo)
    shared = repo / "orchestration" / "shared"
    runners = repo / "orchestration" / "runners"
    ok = True

    # --- 1. window.py ---
    wp = shared / "window.py"
    if wp.exists():
        log("OK", "window.py already exists -- not overwritten")
    else:
        shared.mkdir(parents=True, exist_ok=True)
        with open(wp, "w", encoding="utf-8", newline="") as fh:
            fh.write(WINDOW_PY)
        log("CREATED", str(wp))

    # --- 2. runners ---
    for name in ("run_data.py", "run_after.py"):
        if not patch_runner(runners / name):
            ok = False

    # --- 3. regen path (run_data only, measured) ---
    if not fix_regen_path(runners / "run_data.py", Path(args.ba_root)):
        ok = False

    # --- verify final state ---
    log("VERIFY", "final state:")
    for name in ("run_data.py", "run_after.py"):
        t = _read(runners / name) if (runners / name).exists() else ""
        has_block = "from window import resolve_window_end" in t
        has_none = "default=None" in t
        log("VERIFY", f"  {name}: resolve-block={has_block}, end-default-None={has_none}")
        if not (has_block and has_none):
            ok = False
    log("VERIFY", f"  window.py exists: {wp.exists()}")

    if ok:
        log("DONE", "next: py -3.11 -c \"import sys; sys.path.insert(0, r'<repo>/orchestration/shared'); "
                    "from window import resolve_window_end; print(resolve_window_end())\" then commit.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
