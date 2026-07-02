#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fd_minipass.py -- the FD mini-pass: close capture-debt in ONE governance commit
======================================================================================
Purpose
    Four surgical, measured edits across three governance files (2026-07-02):

    FUTURE_DEVELOPMENT.md (docs/governance/):
      1. FD.22 index row: status "Önskad" -> corrected. Live-ticking runtime was
         BUILT in FAS 18 (dashboard.html); the index row was stale (fourth-map class).
      2. Append FD.<max+1> "Robusthetspass" (promotion of BACKLOG BB.9 MOGEN per
         §5b + BB.10 + the P.9 io_safe-wiring rest) and FD.<max+2>
         "Sökvägs-centralisering" (captured from the deps measurement / BA cleanup
         checklist §4). Numbers are DERIVED from the file's own max FD (declare
         once), and a row is added to the file's "Senaste uppdateringar" table
         per its own protocol ("Hur posten levs"). Header date bumped.

    BACKLOG.md (repo root):
      3. BB.9 status: MOGEN -> FLYTTAD -> FD.<max+1> (§5b: MOGEN moves to owner).
         The build-SPÄRR text (not before cluster-maj green) is kept verbatim.

    MANIFEST.md (repo root):
      4. Weave path C:\\Projekt\\masters -> C:\\Projekt\\Master-Bibliotek (repo
         rename 2026-06-26; deps measurement 2026-07-02 proved old path MISSING).
         NOTE: this fixes ONLY the weave's root pointer -- the full doc sweep
         (NEXT_SESSION §5.6, all other files) remains a separate pass.

    Idempotent, timestamped .bak per touched file, preserves line endings
    (newline=''), UTF-8 without BOM (LB.86). Verifies all markers before exit.

Upstream   : docs/governance/FUTURE_DEVELOPMENT.md, BACKLOG.md, MANIFEST.md
Downstream : next sessions read these as governing truth; BB.9's new owner is FD
Lessons    : LB.85 (declare once -- FD number derived), §5b (MOGEN -> owner),
             fourth-map class (stale index rows), LB.86 (script-written docs)
Run        : py -3.11 tools\\patch_fd_minipass.py
             py -3.11 tools\\patch_fd_minipass.py --repo <root>     (test mode)
Developer  : Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

TODAY = "2026-07-02"

FD22_OLD = "| FD.22 | Live-tickande körtid + summering i frontend | Önskad |"
FD22_NEW = ("| FD.22 | Live-tickande körtid + summering i frontend | **Byggd** "
            "(FAS 18, dashboard.html) — indexrad rättad 2026-07-02 |")

BB9_OLD = "**Status:** MOGEN — flyttas till FD/robusthetspass vid nästa FD-redigering."
# {n1} injected at runtime (derived FD number)
BB9_NEW = "**Status:** FLYTTAD → FD.{n1} (2026-07-02, §5b MOGEN→ägare)."

MANIFEST_OLD = r"C:\Projekt\masters"
MANIFEST_NEW = r"C:\Projekt\Master-Bibliotek"

UPDATE_ROW = ("| 2026-07-02 | FD-minipass: FD.{n1} Robusthetspass delad infra tillagd "
              "(uppflyttning BB.9 tar-fetch MOGEN + BB.10 selftest + P.9 io_safe-wiring; "
              "SPÄRR till efter cluster-maj-grön). FD.{n2} Sökvägs-centralisering tillagd "
              "(deps-mätning 2026-07-02: 336+66 absoluta sökvägar, levande delmängd mäts om "
              "efter brus-städ). FD.22-indexraden rättad (live-tick BYGGD FAS 18 — raden var "
              "stale). BB.9 i BACKLOG → FLYTTAD. MANIFEST väv-sökväg → Master-Bibliotek. |")

FD_SECTIONS = """

---

## FD.{n1} — Robusthetspass: delad infrastruktur (tar-fetch, selftest, io_safe-wiring)

**Status:** Specificerad 2026-07-02 — uppflyttning av BACKLOG BB.9 (MOGEN, §5b) + BB.10 +
P.9-resten. **SPÄRR:** byggs EFTER att cluster-maj-relaunchen är grön — en variabel i taget;
relaunchen ska bevisa config-fixen, inte config + ny hämtningsväg samtidigt.

**Vad (tre delar, ETT pass — horisontella metoden BB.13 i praktiken, delad väg träffar alla tre):**
1. **tar-fetch (BB.9, BEVISAD FAS 21):** runnernas `fetch_all_outputs` scp:ar per fil
   (4181 överföringar); tar-varianten hämtade 190 MB på 10 s där per-fil malde 11+ min och
   föll på svenska filnamn (dubbel-UTF-8). Mätt 2026-07-02: bristen identisk i alla tre
   runners (`run_cluster_model.py:385`-mönstret, 3 anropsplatser per runner). Fix: `tar czf`
   på VM + EN `scp_from_vm` — i delad väg + tre runners samtidigt.
2. **selftest realistisk sekvens (BB.10):** `ssh_launch_selftest` kör `sleep 90` i vakuum
   (`azure_vm.py:241–257`) och gav PASS trots att skarp launch dog efter en serie täta
   SSH-anrop. Skärp till preflight-liknande serie + launch så tunnel-blink-klassen fångas
   FÖRE en 50-min-körning. (A2-fixen täcker redan skarpa vägen; TESTEN släpar.)
3. **io_safe-wiring (P.9-resten):** `io_safe.py` + idempotens-audit är byggda och committade
   (`cdd02d3`, triage 164 → ~3–4 relevanta skrivningar) — koppla `io_safe` i de utpekade
   skrivpunkterna så de långa stegen får atomära skrivningar på riktigt.

**Gäller om:** nästa gång en runner rörs, eller som eget dedikerat pass direkt efter maj-grönt.

## FD.{n2} — Sökvägs-centralisering (env/config-lager för C:\\Projekt-beroenden)

**Status:** Fångad 2026-07-02 ur deps-mätningen (`map_cross_project_deps.ps1`, BA-städningen).

**Uppmätt:** 336 absoluta sökvägar i 162 BCG-filer + 66 i 32 BA-filer. Mycket sitter i
`_ATT_RADERA/`, `archives/`, `workspace/` och genererade loggar — den LEVANDE skulden är
mindre och mäts om EFTER brus-städningen (BA-checklistan §4/§5).

**Vad:** centralisera levande `C:\\Projekt\\...`-beroenden till env-vars/en gemensam
config-modul, i survival-/klon-målets tjänst: en frisk klon på annan maskin ska köra utan
sök-ersätt av sökvägar. Prioritera kod-beroenden (runners, verify_tool, orchestration) —
docs/loggar är dokumentation, inte kontrakt.

**Gate:** eget pass, kandidat efter FAS A grön. Togs INTE på köpet i filflytt-städningen
(VAKTEN trigger 1 — frestelsen fanns, avvärjdes i BA-checklistan §4).
"""


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


def patch_fd(fd_path: Path) -> "tuple[bool, int]":
    """Returns (ok, n1). Derives n1/n2 from the file's own max FD number."""
    if not fd_path.exists():
        log("FAIL", f"not found: {fd_path}")
        return False, 0
    text = _read(fd_path)

    nums = sorted({int(m) for m in re.findall(r"FD\.(\d+)", text)})
    n1, n2 = nums[-1] + 1, nums[-1] + 2
    log("DERIVE", f"max FD in file = FD.{nums[-1]} -> new posts FD.{n1} + FD.{n2}")

    existing = re.search(r"## FD\.(\d+) — Robusthetspass", text)
    if existing:
        n1 = int(existing.group(1))
        log("OK", f"FUTURE_DEVELOPMENT already patched (FD.{n1}) -- idempotent no-op")
        return True, n1

    changed = False

    # 1. header date bump
    text, n = re.subn(r"(\*\*Senast uppdaterad:\*\* )\d{4}-\d{2}-\d{2}",
                      r"\g<1>" + TODAY, text, count=1)
    if n:
        log("PATCH", f"header: Senast uppdaterad -> {TODAY}")
        changed = True

    # 2. FD.22 index row correction
    if FD22_OLD in text:
        text = text.replace(FD22_OLD, FD22_NEW, 1)
        log("PATCH", "FD.22 index row: Önskad -> Byggd (FAS 18) [stale row corrected]")
        changed = True
    elif FD22_NEW.split("—")[0] in text:
        log("OK", "FD.22 row already corrected")
    else:
        log("WARN", "FD.22 anchor row not found verbatim -- row NOT touched (verify manually)")

    # 3. row in 'Senaste uppdateringar' (insert just before the FD.37 section)
    row = UPDATE_ROW.format(n1=n1, n2=n2)
    anchor = "\n\n## FD.37 —"
    if anchor in text:
        text = text.replace(anchor, "\n" + row + anchor, 1)
        log("PATCH", "row added to 'Senaste uppdateringar' (per the file's own protocol)")
        changed = True
    else:
        log("WARN", "FD.37 anchor not found -- update-table row NOT inserted")

    # 4. append the two new sections at EOF
    text = text.rstrip("\n") + FD_SECTIONS.format(n1=n1, n2=n2).rstrip() + "\n"
    log("PATCH", f"appended sections FD.{n1} + FD.{n2} at EOF")
    changed = True

    if changed:
        _write(fd_path, text)
    return True, n1


def patch_backlog(bl_path: Path, n1: int) -> bool:
    if not bl_path.exists():
        log("FAIL", f"not found: {bl_path}")
        return False
    text = _read(bl_path)
    new_status = BB9_NEW.format(n1=n1)
    if new_status in text:
        log("OK", "BACKLOG BB.9 already FLYTTAD (idempotent no-op)")
        return True
    if BB9_OLD not in text:
        log("WARN", "BB.9 MOGEN-anchor not found -- BACKLOG NOT touched (verify manually)")
        return True
    text = text.replace(BB9_OLD, new_status, 1)
    log("PATCH", f"BACKLOG BB.9: MOGEN -> FLYTTAD → FD.{n1} (SPÄRR-texten kvar orörd)")
    _write(bl_path, text)
    return True


def patch_manifest(mf_path: Path) -> bool:
    if not mf_path.exists():
        log("FAIL", f"not found: {mf_path}")
        return False
    text = _read(mf_path)
    if MANIFEST_NEW in text and MANIFEST_OLD not in text:
        log("OK", "MANIFEST weave path already Master-Bibliotek (idempotent no-op)")
        return True
    if MANIFEST_OLD not in text:
        log("WARN", "MANIFEST old path not found -- NOT touched")
        return True
    text = text.replace(MANIFEST_OLD, MANIFEST_NEW)
    log("PATCH", f"MANIFEST: {MANIFEST_OLD} -> {MANIFEST_NEW} (weave root pointer; "
                 f"full doc sweep remains a separate pass)")
    _write(mf_path, text)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="FD mini-pass: close governance capture-debt in one commit.")
    ap.add_argument("--repo", default=r"C:\Projekt\BCG")
    args = ap.parse_args()
    repo = Path(args.repo)

    fd = repo / "docs" / "governance" / "FUTURE_DEVELOPMENT.md"
    bl = repo / "BACKLOG.md"
    mf = repo / "MANIFEST.md"

    ok_fd, n1 = patch_fd(fd)
    ok_bl = patch_backlog(bl, n1) if ok_fd else False
    ok_mf = patch_manifest(mf)

    # ---- verify final state ----
    log("VERIFY", "final markers:")
    checks = [
        (fd, f"## FD.{n1} — Robusthetspass", "FD-post 1"),
        (fd, "Sökvägs-centralisering", "FD-post 2"),
        (fd, "indexrad rättad 2026-07-02", "FD.22 corrected"),
        (bl, f"FLYTTAD → FD.{n1}", "BB.9 promoted"),
        (mf, MANIFEST_NEW, "MANIFEST path"),
    ]
    ok = ok_fd and ok_bl and ok_mf
    for path, marker, label in checks:
        hit = path.exists() and marker in _read(path)
        log("VERIFY", f"  {label:<18} {'OK' if hit else 'MISSING'}  ({path.name})")
        ok = ok and hit
    if ok:
        log("DONE", "git add docs/governance/FUTURE_DEVELOPMENT.md BACKLOG.md MANIFEST.md "
                    "tools/patch_fd_minipass.py  ->  one commit")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
