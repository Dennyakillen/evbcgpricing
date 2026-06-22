#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_to_blob_complete.py  --  Steg B (komplett): allt affarsdata till Blob
============================================================================
Overlevnadstesen: Blob ska bara ALLT affarsdata sa datorn blir umbarlig.
Detta skript laddar upp de bitar som annars ar DATOR-UNIKA (sond 7 flaggar dem):
  1. Frusna facit-lager (FD.14 vav-vikter, FD.15 cluster-steg5) -> pipeline/
  2. Bundle facit (FD.11) -> redan pa Blob, verifieras
  3. tx-CSV for build_r12 (Sweden_weekly_model_data_site_level.csv, ~171 MB)
  4. (valfritt) gamla valideringar/receipts -> pipeline/00_validations/

DRY-RUN som DEFAULT -- visar planen utan att ladda upp. --commit for att kora.

ANVANDNING:
    cd "C:\\Projekt\\BCG"; $env:PRICINGMODEL_AUTH="key"
    py -3.11 workspace\\upload_to_blob_complete.py              # dry-run (default)
    py -3.11 workspace\\upload_to_blob_complete.py --commit     # ladda upp pa riktigt
    py -3.11 workspace\\upload_to_blob_complete.py --commit --with-validations  # + receipts

Developer: Jens Palmo. Author: Claude advisor 2026-06-22 (overlevnadstes).
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))
from blob import _client  # noqa: E402
CONTAINER_PIPELINE = "pipeline"

FBL_INPUT = REPO / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic" / "input_data"
TX_CSV = REPO / "Pipeline" / "02. Elasticity" / "Sweden_Elasticity_Data_Prep_SQL" / "output" / "Sweden_weekly_model_data_site_level.csv"
# Gamla valideringar (justera om annan plats): verify_tool-receipts
RECEIPTS_DIRS = [
    REPO / "verify_tool" / "receipts",
    REPO / "workspace" / "validation_receipts",
]

# Frusna facit + tx (de filer sond 7 annars flaggar DATOR-UNIK)
CORE_UPLOADS = [
    {"label": "FD.15 cluster-steg5", "src": FBL_INPUT / "final_model_cluster_granularity_Ivce.xlsx",
     "blob": "00_frozen_facit/cluster_step5/final_model_cluster_granularity_Ivce.xlsx", "fd": "FD.15"},
    {"label": "FD.14 vav-vikter", "src": FBL_INPUT / "Complete_Product_Data.xlsx",
     "blob": "00_frozen_facit/weave_weights/Complete_Product_Data.xlsx", "fd": "FD.14"},
    {"label": "tx-CSV (build_r12)", "src": TX_CSV,
     "blob": "00_frozen_facit/tx/Sweden_weekly_model_data_site_level.csv", "fd": "FD.37"},
]


def log(tag, msg): print(f"[{tag}] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Steg B komplett: allt affarsdata till Blob (overlevnadstes).")
    ap.add_argument("--commit", action="store_true", help="Ladda upp pa riktigt (annars dry-run).")
    ap.add_argument("--with-validations", action="store_true", help="Ladda aven upp gamla valideringar/receipts.")
    ap.add_argument("--overwrite", action="store_true", help="Skriv over befintliga blobbar.")
    args = ap.parse_args()
    dry = not args.commit

    print("=" * 70)
    print(f"STEG B KOMPLETT -- affarsdata till Blob  [{'DRY-RUN' if dry else 'COMMIT'}]")
    print("=" * 70)

    svc = _client()
    container = svc.get_container_client(CONTAINER_PIPELINE)

    # Verifiera bundle redan pa Blob (FD.11)
    try:
        b = [x.name for x in container.list_blobs(name_starts_with="00_frozen_facit/bundle/")]
        log("VERIFY", f"FD.11 bundle-facit pa Blob: {b if b else 'SAKNAS (kontrollera!)'}")
    except Exception as e:
        log("WARN", f"kunde ej lista bundle ({e})")

    uploads = list(CORE_UPLOADS)

    # Bygg validerings-listan om begart
    if args.with_validations:
        for rdir in RECEIPTS_DIRS:
            if rdir.is_dir():
                for fp in rdir.rglob("*"):
                    if fp.is_file():
                        rel = fp.relative_to(rdir)
                        uploads.append({
                            "label": f"validation: {rel}",
                            "src": fp,
                            "blob": f"00_validations/{rdir.name}/{rel.as_posix()}",
                            "fd": "-",
                        })

    total_mb = 0.0
    n = 0
    for item in uploads:
        src = item["src"]
        if not src.exists():
            log("MISSING-SRC", f"{item['label']}: {src}")
            continue
        mb = src.stat().st_size / 1e6
        bc = container.get_blob_client(item["blob"])
        exists = bc.exists()
        if exists and not args.overwrite:
            log("SKIP", f"{item['label']}: finns pa Blob ({item['blob']}) -- --overwrite for ersatta.")
            continue
        action = "would upload" if dry else "uploading"
        log("UPLOAD", f"{item['label']} [{item['fd']}] {action} ({mb:.2f} MB) -> {CONTAINER_PIPELINE}/{item['blob']}")
        total_mb += mb
        if not dry:
            with open(src, "rb") as fh:
                bc.upload_blob(fh, overwrite=True)
            up = bc.get_blob_properties().size / 1e6
            log("DONE", f"{item['label']}: {up:.2f} MB pa Blob ({'OK' if abs(up-mb)<0.05 else 'STORLEK SKILJER'})")
            n += 1

    print("=" * 70)
    if dry:
        print(f"DRY-RUN: {sum(1 for i in uploads if i['src'].exists())} filer skulle laddas upp (~{total_mb:.0f} MB).")
        print("Kor med --commit for att utfora. --with-validations for receipts.")
    else:
        print(f"KLART: {n} filer uppladdade (~{total_mb:.0f} MB).")
        print("Kor survival_probe.py for att verifiera att inget langre ar dator-unikt.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
