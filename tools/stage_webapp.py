# stage_webapp.py (v1.1.1) -- stage the BCG dashboard for deployment (any vehicle)
# =============================================================================
# Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Purpose:   ONE staging module, MANY transport vehicles (platform-compatible).
# v1.1:      MANIFEST-DRIVEN. The file list is no longer hardcoded here --
#            it is MEASURED by tools/webapp_deploy_probe.py (AST transitive
#            closure) and consumed from workspace/deploy_staging_manifest.json.
#            One owner of the closure logic (probe), one consumer (this file).
#            The regex import gate of v1.0 is retired: it produced 3 false
#            positives (stdlib + docstring) and, before the probe existed,
#            could not see transitive deps (run_status -> caught 2026-07-07).
# Pipeline:  probe (measure) -> stage (package) -> deploy (transport).
#            Local: deploy_dashboard_final.ps1 runs all three.
#            Azure DevOps: azure-pipelines.yml runs probe + stage the same way.
# Output:    <repo>/deploy.zip (gitignored) + workspace/deploy_staging/
# Run:       py -3.11 tools/stage_webapp.py
#            (fails with instructions if the manifest is missing/critical)
# Lessons:   D.15, D.16, D.20, D.22, D.23 (MASTER_AZURE_DEPLOY.md)
# =============================================================================
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEBAPP = REPO / "orchestration" / "webapp"
REQS_SRC = REPO / "requirements.txt"
MANIFEST = REPO / "workspace" / "deploy_staging_manifest.json"
STAGING = REPO / "workspace" / "deploy_staging"
ZIP_OUT = REPO / "deploy.zip"

STARTUP_SH = (
    "#!/bin/sh\n"
    "# D.22: gunicorn>=22 removed cwd from sys.path -> explicit chdir+PYTHONPATH.\n"
    "# 'python -m gunicorn' forces the antenv's PINNED gunicorn (20.1.0): Oryx\n"
    "# activates antenv before running this user startup script (verified vs\n"
    "# Microsoft sources 2026-07-07), so 'python' here is antenv's python.\n"
    "# D.23: written by stage_webapp.py with LF only. Never edit by hand on\n"
    "# Windows -- regenerate via stage_webapp.py.\n"
    "if [ -n \"$APP_PATH\" ] && [ -d \"$APP_PATH\" ]; then cd \"$APP_PATH\"; else cd /home/site/wwwroot; fi\n"
    "export PYTHONPATH=\"$(pwd)\"\n"
    "echo \"[startup.sh] running from $(pwd)\"\n"
    "exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app\n"
)


def fail(msg: str) -> None:
    print(f"[stage] FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print(f"[stage] repo root: {REPO}")

    # --- Gate 0: manifest exists and is clean ---------------------------------
    if not MANIFEST.exists():
        fail("staging manifest missing. Run the probe first:\n"
             "        py -3.11 tools\\webapp_deploy_probe.py\n"
             "        (review its receipt, then rerun staging)")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if m.get("critical"):
        fail(f"manifest carries {len(m['critical'])} CRITICAL probe finding(s) "
             f"-- fix and re-run the probe first: {m['critical']}")
    print(f"[stage] manifest: {len(m['files'])} module(s), "
          f"dirs {m.get('dirs', [])}, generated {m.get('generated')}")

    # --- Gate 1: requirements pin (D.22) ---------------------------------------
    if not REQS_SRC.exists():
        fail(f"missing {REQS_SRC}")
    if "gunicorn==20.1.0" not in REQS_SRC.read_text(encoding="utf-8",
                                                    errors="replace"):
        fail("requirements.txt lacks pinned 'gunicorn==20.1.0' (D.22)")

    # --- Stage per manifest ------------------------------------------------------
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    for entry in m["files"]:
        src = REPO / entry["src"]
        if not src.exists():
            fail(f"manifest file missing on disk: {entry['src']} "
                 "(stale manifest? re-run the probe)")
        shutil.copy2(src, STAGING / entry["dst"])
    for d in m.get("dirs", []):
        src_dir = WEBAPP / d
        if src_dir.exists():
            shutil.copytree(src_dir, STAGING / d,
                            ignore=shutil.ignore_patterns(
                                "__pycache__", "*.pyc", "*.bak", "*.log"))
    shutil.copy2(REQS_SRC, STAGING / "requirements.txt")

    # --- startup.sh: LF written, then MEASURED (D.23) -----------------------------
    sh_path = STAGING / "startup.sh"
    with open(sh_path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(STARTUP_SH)
    raw = sh_path.read_bytes()
    cr_count = raw.count(b"\r")
    if cr_count != 0:
        fail(f"startup.sh contains {cr_count} CR bytes (D.23)")
    print(f"[stage] startup.sh: {len(raw)} bytes, CR bytes = 0 (verified)")

    # --- Cache-bust: unique payload every build (D.16) ------------------------------
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (STAGING / "_cachebust.txt").write_text(
        f"build {stamp}\npurpose: force unique payload (D.16: identical Build "
        "Operation ID = wwwroot's oryx-manifest.toml was never replaced)\n",
        encoding="ascii")
    print(f"[stage] _cachebust.txt: {stamp}")

    # --- Gate 2: required files present ---------------------------------------------
    required = ["app.py", "requirements.txt", "startup.sh"] + \
               [e["dst"] for e in m["files"]]
    missing = [f for f in sorted(set(required)) if not (STAGING / f).exists()]
    if missing:
        fail(f"required files missing in staging: {missing}")
    print(f"[stage] required files: {len(set(required))} present")

    # --- Zip via Python zipfile (D.15) ------------------------------------------------
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(STAGING.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(STAGING).as_posix())

    # --- Gate 3: measure the zip (D.15 + D.20) -------------------------------------------
    with zipfile.ZipFile(ZIP_OUT) as zf:
        names = zf.namelist()
    bad = [n for n in names if "\\" in n]
    if bad:
        fail(f"{len(bad)} zip entries contain backslash (D.15): {bad[:5]}")
    for root_file in ("app.py", "startup.sh", "requirements.txt"):
        if root_file not in names:
            fail(f"'{root_file}' not at zip root (D.20 flatten broken)")
    size_mb = ZIP_OUT.stat().st_size / 1_048_576
    print(f"[stage] deploy.zip: {len(names)} entries, 0 backslash, "
          f"entry files at root, {size_mb:.2f} MB")
    print(f"[stage] OK -> {ZIP_OUT}")


if __name__ == "__main__":
    main()
