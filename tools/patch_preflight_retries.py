#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_preflight_retries.py  --  LB.78: harda preflight_remote mot tunnel-flakighet
====================================================================================
ROTORSAK (bevisad 2026-06-23, git-verifierad): cluster-maj-relaunch foll i
preflight_remote med 'Failed before launch' efter 'ssh hung ... timeout 60s'.
ssh_run HAR retry-stod (retries-param), men preflight_remote anropar den UTAN
retries -> ETT forsok per test -e. wait_for_ssh DAREMOT retryar 18 ggr (red ut
fyra hangningar samma kvall). preflight ar darfor skorare an resten av runnern
mot SAMMA tunnel-flakighet. Glaskaken ar latent -- biter bara nar tunneln ar
dalig nog att ett 60s-fonster hanger. Koden var OFORANDRAD sedan lyckad
Site-korning (git log -p bevisade) -- det var tunneln igar, inte koden.

FIX (additiv): lagg retries=2 pa preflight_remote:s TVA ssh_run-anrop
(rad ~135 test -e-loopen, rad ~140 archive). Ror INTE ssh_run:s default
(retries=0 forblir default for andra anropare). Bara preflight blir robust.

STRATEGI: "slapp igenom mer, aldrig mindre" -- preflight rider nu ut en
hangning i stallet for att kasta SshUnreachable pa forsta. Andrar inte
beteende nar tunneln ar frisk (0 hangningar -> 0 retries anvands).

IDEMPOTENT: kollar om retries= redan finns i raderna. Backup forst.
UTF-8 utan BOM. Verifierar sig sjalv.

KOER (global py -3.11, lokalt):
    py -3.11 patch_preflight_retries.py
    py -3.11 patch_preflight_retries.py --dry-run

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
Beroende: std-lib (pathlib, argparse, datetime, shutil).
"""
from __future__ import annotations
import argparse
import datetime
import shutil
import sys
from pathlib import Path

DEFAULT = r"C:\Projekt\BCG\orchestration\runners\run_cluster_model.py"

# Anrop 1: test -e-loopen (rad ~135). Exakt strang fran kallan 2026-06-24.
NEEDLE_1 = 'cp = ssh_run(cfg, f"test -e {path} && echo yes || echo no")'
INSERT_1 = 'cp = ssh_run(cfg, f"test -e {path} && echo yes || echo no", retries=2)'

# Anrop 2: archive (rad ~140). Tva-rads f-string -- matcha forsta raden + retries pa slutet.
# Kallan:
#   ssh_run(cfg, f"test -f {REMOTE_OUTPUT} && cp {REMOTE_OUTPUT} {REMOTE_OUTPUT}.pre_{stamp} "
#                f"&& echo archived || echo none")
NEEDLE_2 = '                 f"&& echo archived || echo none")'
INSERT_2 = '                 f"&& echo archived || echo none", retries=2)'

DONE_MARK = "retries=2"


def main() -> int:
    ap = argparse.ArgumentParser(description="LB.78: harda preflight_remote med retries=2.")
    ap.add_argument("--file", default=DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fp = Path(args.file)
    print("=" * 74)
    print("PATCH preflight_remote -- LB.78 retries=2 (harda mot tunnel-flakighet)")
    print(f"Fil: {fp}")
    print("=" * 74)

    if not fp.exists():
        print(f"[FEL] Hittar inte: {fp}")
        return 2

    text = fp.read_text(encoding="utf-8")
    original = text
    changes, skipped = [], []

    # Anrop 1
    if INSERT_1 in text:
        skipped.append("Anrop 1 (test -e-loop): retries=2 finns redan.")
    elif NEEDLE_1 in text:
        n = text.count(NEEDLE_1)
        if n != 1:
            print(f"[STOPP] Anrop-1-naal foorekommer {n} ggr (vantade 1). Inspektera manuellt.")
            return 2
        text = text.replace(NEEDLE_1, INSERT_1, 1)
        changes.append("Anrop 1 (test -e-loop, rad ~135): +retries=2")
    else:
        print(f"[STOPP] Hittar ej Anrop-1-naal:\n  {NEEDLE_1}")
        print("  -> Kallan kan ha andrats. Mat om raden innan patch.")
        return 2

    # Anrop 2
    if INSERT_2 in text:
        skipped.append("Anrop 2 (archive): retries=2 finns redan.")
    elif NEEDLE_2 in text:
        n = text.count(NEEDLE_2)
        if n != 1:
            print(f"[STOPP] Anrop-2-naal foorekommer {n} ggr (vantade 1). Inspektera manuellt.")
            return 2
        text = text.replace(NEEDLE_2, INSERT_2, 1)
        changes.append("Anrop 2 (archive, rad ~140): +retries=2")
    else:
        print(f"[STOPP] Hittar ej Anrop-2-naal:\n  {NEEDLE_2}")
        print("  -> Tva-rads f-string kan ha annan indragning. Mat om innan patch.")
        return 2

    print("\nPLANERADE AENDRINGAR:")
    for c in changes:
        print(f"  + {c}")
    for s in skipped:
        print(f"  = {s}")

    if not changes:
        print("\n[KLART] Redan patchad (idempotent).")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] Inget skrevs.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    bak = fp.with_suffix(fp.suffix + f".before-retries-{stamp}.bak")
    shutil.copy2(fp, bak)
    print(f"\n[Backup] {bak}")

    with open(fp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"[Skrev]  {fp} (UTF-8 utan BOM)")

    verify = fp.read_text(encoding="utf-8")
    ok1 = INSERT_1 in verify
    ok2 = INSERT_2 in verify
    bom = fp.read_bytes()[:3] == b"\xef\xbb\xbf"
    print("\nVERIFIERING:")
    print(f"  Anrop 1 har retries=2 : {'JA' if ok1 else 'NEJ'}")
    print(f"  Anrop 2 har retries=2 : {'JA' if ok2 else 'NEJ'}")
    print(f"  BOM (ska vara NEJ)    : {'JA -- FEL!' if bom else 'NEJ (bra)'}")

    if ok1 and ok2 and not bom:
        print("\n[KLART] Harden. preflight rider nu ut tunnel-hangning. Committa + relaunch.")
        return 0
    print("\n[VARNING] Verifiering ej gron -- inspektera fil + backup.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
