"""
idempotens_audit.py  --  kartlagger atomara vs sarbara skrivningar i kodbasen
=============================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.

SYFTE (mat, gissa inte -- tillampad pa din egen kod)
----------------------------------------------------
Svarar pa fragan "foljer mina skrivningar ett idempotent (atomart) monster?"
genom att SKANNA koden, inte gissa. Hittar varje stalle dar data skrivs till
disk, klassificerar det som ATOMART (temp->rename, krasch-sakert) eller SARBART
(direkt till slutmal, kan lamna halv fil vid krasch), och skriver en rapport.

VAD ATOMART BETYDER
-------------------
En skrivning ar atomar om en krasch mitt i den ALDRIG lamnar en halv slutfil.
Uppnas via write-rename: skriv till temp, byt namn atomiskt nar klart. En halv
temp-fil ar ofarlig (ignoreras/stadas); en halv slutfil laser nasta steg som
trunkerad data -> tyst fel (din dyraste felklass).

KOR (global py-3.11, repo-roten)
--------------------------------
    py -3.11 idempotens_audit.py                    # skanna + skriv rapport
    py -3.11 idempotens_audit.py --root <sokvag>    # annan rot
    py -3.11 idempotens_audit.py --no-report        # bara stdout
"""
from __future__ import annotations

import argparse
import ast
import datetime
import sys
from pathlib import Path

# Skrivnings-anrop att leta efter (metod-namn som producerar filer)
WRITE_CALLS = {
    "to_parquet", "to_excel", "to_csv", "to_feather", "to_pickle", "to_json",
    "save", "savefig", "write_text", "write_bytes", "to_hdf",
}
# Anrop som INDIKERAR atomart monster i narheten
ATOMIC_HINTS = {"replace", "rename", "move", "Move-Item"}
# Mappar att hoppa (genererat/tredjepart)
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", "_archive",
             "_arkiv", "archives", "workspace", "data", ".vscode"}


class WriteFinding:
    def __init__(self, file, line, call, target_hint, atomic, context):
        self.file = file; self.line = line; self.call = call
        self.target_hint = target_hint; self.atomic = atomic; self.context = context


def _has_atomic_nearby(lines, idx, window=6):
    """Kollar om ett rename/replace finns inom +/- window rader (heuristik:
    temp-skrivning foljt av rename)."""
    lo = max(0, idx - window); hi = min(len(lines), idx + window + 1)
    chunk = " ".join(lines[lo:hi])
    return any(h in chunk for h in ATOMIC_HINTS)


def _target_looks_temp(call_line):
    """Skriver anropet till en temp-fil? (.tmp, tempfile, _tmp, NamedTemporary)"""
    low = call_line.lower()
    return any(t in low for t in [".tmp", "tempfile", "_tmp", "namedtemporary", "mkstemp"])


def scan_file(path: Path):
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return findings  # hoppa filer som ej parsar

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in WRITE_CALLS:
                ln = node.lineno
                call_line = lines[ln - 1] if ln - 1 < len(lines) else ""
                writes_to_temp = _target_looks_temp(call_line)
                atomic_nearby = _has_atomic_nearby(lines, ln - 1)
                # Atomart om: skriver till temp OCH har rename i narheten
                is_atomic = writes_to_temp and atomic_nearby
                ctx = call_line.strip()[:90]
                findings.append(WriteFinding(
                    str(path), ln, node.func.attr,
                    "temp" if writes_to_temp else "slutmal(?)",
                    is_atomic, ctx))
    return findings


def main():
    ap = argparse.ArgumentParser(description="Kartlagg atomara vs sarbara skrivningar.")
    ap.add_argument("--root", default=".", help="Rot att skanna (default: aktuell mapp).")
    ap.add_argument("--no-report", action="store_true", help="Skriv ingen md-rapport.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    print("=" * 70)
    print("IDEMPOTENS-AUDIT  --  atomara vs sarbara skrivningar")
    print(f"  rot: {root}")
    print("=" * 70)

    all_findings = []
    for py in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in py.parts):
            continue
        all_findings.extend(scan_file(py))

    atomic = [f for f in all_findings if f.atomic]
    vulnerable = [f for f in all_findings if not f.atomic]

    print(f"\nTotalt skrivnings-anrop: {len(all_findings)}")
    print(f"  ATOMARA (temp->rename): {len(atomic)}")
    print(f"  SARBARA (direkt slutmal): {len(vulnerable)}")

    if vulnerable:
        print("\n-- SARBARA skrivningar (kan lamna halv fil vid krasch) --")
        for f in vulnerable:
            rel = Path(f.file).name
            print(f"  [{f.call:12}] {rel}:{f.line}  {f.context}")

    if atomic:
        print("\n-- ATOMARA skrivningar (krasch-sakra) --")
        for f in atomic:
            rel = Path(f.file).name
            print(f"  [{f.call:12}] {rel}:{f.line}")

    # Rapport
    if not args.no_report:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = root / f"IDEMPOTENS_AUDIT_{stamp}.md"
        L = []
        L.append("# Idempotens-audit -- atomara vs sarbara skrivningar")
        L.append("")
        L.append(f"_Genererad {datetime.datetime.now():%Y-%m-%d %H:%M} av idempotens_audit.py. "
                 f"Utvecklare: Jens Palmo._")
        L.append("")
        L.append(f"Skannade `{root}`. Hittade **{len(all_findings)}** skrivnings-anrop: "
                 f"**{len(atomic)}** atomara, **{len(vulnerable)}** sarbara.")
        L.append("")
        L.append("## Vad detta betyder")
        L.append("En SARBAR skrivning gar direkt till slutmalet. Kraschar processen mitt i "
                 "(natfel, token-dod E.3, VM-glapp) lamnas en HALV slutfil som nasta steg laser "
                 "som trunkerad data -> tyst fel (dyraste felklassen). En ATOMAR skrivning gar till "
                 "temp och byter namn nar klart -> en krasch lamnar bara ofarlig temp-skrap.")
        L.append("")
        if vulnerable:
            L.append("## SARBARA skrivningar (atgarda -- prioritera de som skriver pipeline-artefakter)")
            L.append("")
            L.append("| Anrop | Fil | Rad | Kontext |")
            L.append("|-------|-----|-----|---------|")
            for f in vulnerable:
                L.append(f"| `{f.call}` | {Path(f.file).name} | {f.line} | `{f.context}` |")
            L.append("")
            L.append("**Atgard:** ersatt `df.to_X(slutmal)` med write-rename-monster "
                     "(skriv till `.tmp.<pid>`, sedan `os.replace(tmp, slutmal)`). Se KARN-principen "
                     "om atomara skrivningar.")
            L.append("")
        if atomic:
            L.append("## ATOMARA skrivningar (redan krasch-sakra)")
            L.append("")
            for f in atomic:
                L.append(f"- `{Path(f.file).name}:{f.line}` -- {f.call}")
            L.append("")
        L.append("## Begransningar (arlig mätning)")
        L.append("- Heuristisk: 'atomar' = skriver till temp + rename inom 6 rader. Ett anrop som "
                 "delar upp temp/rename langre isar kan felklassas som sarbart -- verifiera manuellt.")
        L.append("- Tackningen ar statisk (AST): fangar direkta `.to_X()`-anrop, ej skrivningar via "
                 "wrappers/bibliotek som doljer anropet. Komplettera med blick pa egna I/O-helpers.")
        L.append("- En sarbar skrivning till en ENGANGS-fil (ej pipeline-artefakt) ar lagprioriterad.")
        out.write_text("\n".join(L), encoding="utf-8")
        print(f"\n[rapport] {out}")

    print("\n" + "-" * 70)
    if vulnerable:
        print(f"-> {len(vulnerable)} sarbara skrivningar. Prioritera de som skriver parquet/CSV/")
        print("   output_summary (pipeline-artefakter nasta steg laser). Engangsfiler ar OK.")
    else:
        print("-> Inga sarbara skrivningar funna (eller alla via wrappers -- verifiera I/O-helpers).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
