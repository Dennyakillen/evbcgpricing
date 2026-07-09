# read_app_logs.py -- read App Service docker logs from the Kudu log zip
# =============================================================================
# Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Why:       'az webapp log download' produces a NON-standard zip (documented
#            Azure CLI issue since 2017) whose trace entries carry characters
#            illegal on Windows (':'). PS 5.1 Expand-Archive (.NET ZipArchive)
#            throws "path's format is not supported" on them. Extraction is
#            the wrong tool: this script reads ONLY the *docker*.log entries
#            IN MEMORY, never touching the broken sibling entries. Reusable
#            for any App Service (local rounds and DevOps troubleshooting).
# Usage:     az webapp log download -g <rg> -n <app> --log-file %TEMP%\logs.zip
#            py -3.11 tools\read_app_logs.py --zip %TEMP%\logs.zip --since 2026-07-07T1
# Output:    per-file header + matched structural lines only (token discipline)
# =============================================================================
from __future__ import annotations

import argparse
import io
import re
import zipfile
from pathlib import Path

KEYS = re.compile(
    r"App command line|shell script|is a file|running from|Starting gunicorn|"
    r"Booting worker|Traceback|not found|Exited|Listening at|"
    r"Build Operation ID|Updated PYTHONPATH|ModuleNotFound|Error"
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="path to downloaded log zip")
    ap.add_argument("--since", default="",
                    help="timestamp prefix filter, e.g. 2026-07-07T1 "
                         "(matches 15:00-19:59 UTC that day)")
    ap.add_argument("--all-lines", action="store_true",
                    help="print every line in range, not only keyword hits")
    opts = ap.parse_args()

    zpath = Path(opts.zip)
    if not zpath.exists():
        raise SystemExit(f"zip not found: {zpath}")

    with zipfile.ZipFile(zpath) as zf:
        docker = sorted(
            (i for i in zf.infolist()
             if "docker" in i.filename.lower()
             and i.filename.lower().endswith(".log")),
            key=lambda i: i.date_time,
        )
        if not docker:
            names = [i.filename for i in zf.infolist()][:20]
            raise SystemExit(f"no *docker*.log entries found; first entries: {names}")
        print(f"[logs] {len(docker)} docker log file(s) in zip; "
              f"reading in-memory (no extraction)")
        for info in docker[-4:]:  # newest few files
            print(f"\n### {info.filename}  ({info.file_size} B)")
            with zf.open(info) as fh:
                text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
                hits = 0
                for line in text:
                    if opts.since and opts.since not in line:
                        continue
                    if opts.all_lines or KEYS.search(line):
                        print("  " + line.rstrip())
                        hits += 1
                if hits == 0:
                    print("  (no matching lines in this file for the given "
                          "--since window)")


if __name__ == "__main__":
    main()
