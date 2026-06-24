#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_preflight_parity_site_bundle.py  --  Horisontell preflight-paritet
========================================================================
SKULD (horisontell granskning 2026-06-24): vi hardade cluster:s preflight_remote
med retries=2 (2026-06-23, LB.78) men BARA cluster. Site och bundle bar fortfarande
den skora preflight (ssh_run utan retries) som dodade cluster forsta gangen. Copy-
adapt-arkitekturen garanterar att en defekt i en familj finns i de andra -- och
denna mate bekraftade det: site L121/L126 + bundle L135/L140 saknar retries.

Detta ar Jens princip "horisontell validering": varje hittat fel valideras mot
kommande familjers motsvarande kod. Inte scope-glidning -- rattning av gammal skuld.

FIX (additiv, identisk med cluster-fixen): retries=2 pa bada ssh_run-anropen i
preflight_remote, i bade run_site_model.py och run_bundle_model.py. Efterat har
alla tre runners IDENTISK preflight-robusthet.

IDEMPOTENT. Backup per fil. UTF-8 utan BOM. Verifierar + py_compile.

KOER (global py -3.11, lokalt):
    py -3.11 patch_preflight_parity_site_bundle.py --dry-run
    py -3.11 patch_preflight_parity_site_bundle.py

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
"""
from __future__ import annotations
import argparse, datetime, shutil, sys, py_compile
from pathlib import Path

FILES = [
    r"C:\Projekt\BCG\orchestration\runners\run_site_model.py",
    r"C:\Projekt\BCG\orchestration\runners\run_bundle_model.py",
]

# Bada filerna har IDENTISKA preflight-rader (copy-adapt). Samma naal i bada.
NEEDLE_1 = 'cp = ssh_run(cfg, f"test -e {path} && echo yes || echo no")'
INSERT_1 = 'cp = ssh_run(cfg, f"test -e {path} && echo yes || echo no", retries=2)'

NEEDLE_2 = '                 f"&& echo archived || echo none")'
INSERT_2 = '                 f"&& echo archived || echo none", retries=2)'


def patch_one(fp: Path, dry: bool) -> int:
    print(f"\n--- {fp.name} ---")
    if not fp.exists():
        print(f"  [FEL] saknas: {fp}"); return 2
    text = fp.read_text(encoding="utf-8")
    changes, skipped = [], []

    for needle, insert, label in [(NEEDLE_1, INSERT_1, "test -e retries=2"),
                                  (NEEDLE_2, INSERT_2, "archive retries=2")]:
        if insert in text:
            skipped.append(f"{label}: redan patchad.")
        elif needle in text:
            if text.count(needle) != 1:
                print(f"  [STOPP] {label}: naal {text.count(needle)} ggr (vantade 1)."); return 2
            text = text.replace(needle, insert, 1)
            changes.append(label)
        else:
            print(f"  [STOPP] {label}: hittar ej naal:\n    {needle}"); return 2

    for c in changes: print(f"  + {c}")
    for s in skipped: print(f"  = {s}")
    if not changes:
        print("  [KLART] redan patchad."); return 0
    if dry:
        print("  [DRY-RUN] inget skrevs."); return 0

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    bak = fp.with_suffix(fp.suffix + f".before-parity-{stamp}.bak")
    shutil.copy2(fp, bak)
    print(f"  [Backup] {bak.name}")
    with open(fp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    v = fp.read_text(encoding="utf-8")
    ok1, ok2 = INSERT_1 in v, INSERT_2 in v
    bom = fp.read_bytes()[:3] == b"\xef\xbb\xbf"
    try:
        py_compile.compile(str(fp), doraise=True); syn = True
    except py_compile.PyCompileError as e:
        print(f"  [py_compile FEL] {e}"); syn = False
    print(f"  test-e retries={'JA' if ok1 else 'NEJ'} | archive retries={'JA' if ok2 else 'NEJ'} "
          f"| BOM={'JA-FEL' if bom else 'nej'} | syntax={'OK' if syn else 'FEL'}")
    return 0 if (ok1 and ok2 and not bom and syn) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    print("=" * 74)
    print("PATCH preflight-paritet -- site + bundle far cluster:s retries=2 (horisontell skuld)")
    print("=" * 74)
    rc = 0
    for f in FILES:
        rc |= patch_one(Path(f), args.dry_run)
    print("\n" + ("[DRY-RUN klar]" if args.dry_run else "[KLART]" if rc == 0 else "[VARNING ngt ej gron]"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
