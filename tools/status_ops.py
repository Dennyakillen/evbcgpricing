#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
status_ops.py -- safe operations on window status files (inspect / backup / mark-extraction)
=============================================================================================
Purpose
    Status files live in Blob ('runstatus/<run_id>.json'), are LAST-WRITE-WINS
    and have NO history -- they are the one truth in this project that git does
    NOT protect. This tool makes the three needed operations safe and honest:

      inspect          Print every phase with started_at / finished_at /
                       duration / note, plus total_active vs wall_clock.
                       This is the measurement that SETTLES the "durations
                       look doubled" question: the timestamps show whether a
                       phase span covers fetch/upload legs (BB.9 class), a
                       poll-lag tail, or a genuine re-run.
      backup           Download the Blob JSON to workspace/status_backups/
                       with a UTC timestamp in the name. mark-extraction
                       ALWAYS does this first -- refusing to write without it.
      mark-extraction  BB.6a: set the 'extraction' phase to SUCCEEDED with an
                       HONEST retro note (the maj data prep ran OUTSIDE the
                       orchestrator, so no runner ever marked it). Timestamps
                       are set to the date you supply (--when), never invented
                       silently. Runs finalize() afterwards so the run-level
                       state follows the etapp model.

    Offline mode: every command accepts --file <local.json> instead of
    --window, so operations can be rehearsed on a backup before touching Blob
    (and so this tool is testable without Azure).

Usage
    py -3.11 tools\\status_ops.py inspect --window 2022-07-01_2026-05-31
    py -3.11 tools\\status_ops.py backup  --window 2022-07-01_2026-05-31
    py -3.11 tools\\status_ops.py mark-extraction --window 2022-07-01_2026-05-31 ^
        --when 2026-06-18 --note "SQL-prep ran outside orchestrator; marked retroactively"
    py -3.11 tools\\status_ops.py inspect --file workspace\\status_backups\\<file>.json

Auth: uses blob.py's own env handling (key mode works while the AAD data-plane
role is pending). Lessons: R7 (receipts over pluppar), LB.60-class (verify by
reading back), one-truth-one-place.

Developer : Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
Created   : 2026-07-02
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG") if Path(r"C:\Projekt\BCG").exists() else Path.cwd()
BACKUP_DIR = REPO / "workspace" / "status_backups"

sys.path.insert(0, str(REPO / "orchestration" / "shared"))
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))


def _load(window: "str | None", file: "str | None"):
    """Return (RunStatus, source_label). Blob via --window, local via --file."""
    from run_status import RunStatus  # noqa: F401  (import check)
    if file:
        from run_status import RunStatus as RS
        return RS.from_json(Path(file).read_text(encoding="utf-8")), f"file:{file}"
    from blob import read_status
    return read_status(window), f"blob:{window}"


def _save(rs, window: "str | None", file: "str | None") -> None:
    if file:
        Path(file).write_text(rs.to_json(), encoding="utf-8")
        print(f"[SAVED] {file}")
    else:
        from blob import write_status
        write_status(rs)
        print(f"[SAVED] blob runstatus for {window}")


def cmd_backup(window: str) -> Path:
    from blob import read_status
    rs = read_status(window)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = BACKUP_DIR / f"{window}__{ts}.json"
    p.write_text(rs.to_json(), encoding="utf-8")
    print(f"[BACKUP] {p}")
    return p


def cmd_inspect(window, file) -> int:
    rs, src = _load(window, file)
    print(f"=== STATUS {src} ===")
    print(f"run_id={rs.run_id}  state={getattr(rs.state,'value',rs.state)}  "
          f"started={rs.started_at}  finished={rs.finished_at}  heartbeat={rs.last_heartbeat}")
    print(f"{'phase':<16} {'state':<10} {'started_at':<21} {'finished_at':<21} {'duration':<10} note")
    for p in rs.phases:
        print(f"{p.key:<16} {getattr(p.state,'value',p.state):<10} "
              f"{p.started_at or '-':<21} {p.finished_at or '-':<21} "
              f"{p.duration_human or '-':<10} {p.note or ''}")
    try:
        print(f"\ntotal_active={rs.total_active_human}  (sum of phase durations)")
        print(f"wall_clock ={rs.wall_clock_human}  (first start -> last finish)")
        print("Tolkning: duration >> faktisk berakningstid => fasen spanner "
              "fetch/upload-ben (BB.9-klass) eller poll-slap; jamfor timestamps "
              "mot dina tee-loggar.")
    except Exception:
        pass
    return 0


def cmd_mark_extraction(window, file, when, note):
    return cmd_mark(window, file, "extraction", when, note)


def cmd_mark(window, file, phase: str, when: str, note: str) -> int:
    if not file:
        cmd_backup(window)  # KRITISKT: aldrig skriva utan backup
    rs, src = _load(window, file)
    from run_status import PhaseState
    hit = None
    hit = next((p for p in rs.phases if p.key == phase), None)
    if hit is None:
        print(f"[FAIL] no phase {phase!r}. Valid: {[p.key for p in rs.phases]}")
        return 1
    if getattr(hit.state, "value", hit.state) == "succeeded":
        print(f"[OK] {phase} already SUCCEEDED -- idempotent no-op")
        return 0
    stamp = f"{when}T12:00:00Z"
    hit.state = PhaseState.SUCCEEDED
    hit.started_at = hit.started_at or stamp
    hit.finished_at = hit.finished_at or stamp
    hit.note = note
    new_state = rs.finalize()
    print(f"[MARK] {phase} -> SUCCEEDED ({when}) | run-level after finalize: "
          f"{getattr(new_state,'value',new_state)}")
    _save(rs, window, file)
    # read-back verification (LB.60-class: don't trust the write line)
    rs2, _ = _load(window, file)
    ok = any(p.key == phase and getattr(p.state, "value", p.state) == "succeeded"
             for p in rs2.phases)
    print(f"[VERIFY] read-back {phase} succeeded: {ok}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Safe status-file operations (inspect/backup/mark-extraction).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("inspect", "backup", "mark", "mark-extraction"):
        s = sub.add_parser(name)
        s.add_argument("--window", default=None, help="run_id, e.g. 2022-07-01_2026-05-31")
        s.add_argument("--file", default=None, help="local status JSON (offline mode)")
        if name == "mark":
            s.add_argument("--phase", required=True)
            s.add_argument("--when", required=True)
            s.add_argument("--note", default="ran outside orchestrator; marked retroactively")
        if name == "mark-extraction":
            s.add_argument("--when", required=True, help="date the prep actually ran, YYYY-MM-DD")
            s.add_argument("--note", default="SQL-prep ran outside orchestrator; marked retroactively (BB.6a)")
    a = ap.parse_args()
    if not a.window and not a.file:
        ap.error("--window or --file required")
    if a.cmd == "inspect":
        return cmd_inspect(a.window, a.file)
    if a.cmd == "backup":
        cmd_backup(a.window)
        return 0
    if a.cmd == "mark":
        return cmd_mark(a.window, a.file, a.phase, a.when, a.note)
    return cmd_mark_extraction(a.window, a.file, a.when, a.note)


if __name__ == "__main__":
    sys.exit(main())
