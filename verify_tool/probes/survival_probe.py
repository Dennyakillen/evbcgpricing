#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
survival_probe.py  --  Sond 7: bevisar OVERLEVNADSTESEN (FD.37)
================================================================
Tesen (Jens): om den lokala datorn forsvinner ska ALLT ga att aterskapa.
Inget far vara unikt pa datorn -- metod pa GitHub, data pa Blob. Denna sond
MATER det i stallet for att paasta det: for varje fil Efter-kedjan behover,
svarar den "finns den pa Blob?" och "ar den lokala kopian den enda kallan?".

Den kor INGEN kedja, ror INGET -- laser bara: lokala sokvagar (finns?) + Blob
(finns?) och korsar dem. Binar dom per fil: SAKER (pa Blob) / DATOR-UNIK (bara
lokalt -> forloras om datorn dor) / SAKNAS (varken eller).

Tre kategorier filer kontrolleras (ur run_step6 + build_r12 + run_after):
  A. Step6:s 5 inputs       (2 LIVE output/, 3 FROZEN pipeline/)
  B. build_r12:s tx-CSV     (transaktionsdata for R12)
  C. Efter-resultatet       (Final_Fallback + Model_Feed -> output/)

ANVANDNING (global Python 3.11, kraver token for Blob-koll):
    cd "C:\\Projekt\\BCG"; $env:PRICINGMODEL_AUTH="key"
    py -3.11 workspace\\survival_probe.py --date-folder 2026-06-17

Developer: Jens Palmo. Author: Claude advisor 2026-06-22 (overlevnadstes).
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Sond 7: bevisa overlevnadstesen (Blob vs lokalt).")
    ap.add_argument("--date-folder", default="2026-06-17", help="Blob-datummapp for LIVE-output.")
    args = ap.parse_args()

    from blob import _client, CONTAINER_OUTPUT  # noqa
    CONTAINER_PIPELINE = "pipeline"
    svc = _client()

    def on_blob(container, blob_name) -> bool:
        try:
            return svc.get_container_client(container).get_blob_client(blob_name).exists()
        except Exception:
            return False

    df = args.date_folder
    # (kategori, etikett, lokal sokvag, blob-container, blob-namn)
    CHECKS = [
        ("A inputs", "cluster output_summary (LIVE)",
         REPO/"Pipeline/02. Elasticity/2. Product Cluster Level Models/_archive_growing_2026-04-27_v2_pg4fix/output_summary.xlsx",
         CONTAINER_OUTPUT, f"{df}/cluster/model/output_summary.xlsx"),
        ("A inputs", "site output_summary (LIVE)",
         REPO/"Pipeline/02. Elasticity/3. Product Site Level Models/output/model/output_summary.xlsx",
         CONTAINER_OUTPUT, f"{df}/output_summary.xlsx"),
        ("A inputs", "cluster-steg5 (FROZEN FD.15)",
         REPO/"Pipeline/02. Elasticity/6. Fall Back Logic/input_data/final_model_cluster_granularity_Ivce.xlsx",
         CONTAINER_PIPELINE, "00_frozen_facit/cluster_step5/final_model_cluster_granularity_Ivce.xlsx"),
        ("A inputs", "bundle (FROZEN FD.11)",
         Path(r"C:/Users/jepa02/OneDrive - Evidensia Djursjukvård AB/Datastrategi/BCG/BCG_orginal_V2_New/02. Elasticity/6. Fall Back Logic/input_data/output_summary_bundle.xlsx"),
         CONTAINER_PIPELINE, "00_frozen_facit/bundle/output_summary.xlsx"),
        ("A inputs", "vav-vikter (FROZEN FD.14)",
         REPO/"Pipeline/02. Elasticity/6. Fall Back Logic/input_data/Complete_Product_Data.xlsx",
         CONTAINER_PIPELINE, "00_frozen_facit/weave_weights/Complete_Product_Data.xlsx"),
        ("B tx-CSV", "build_r12 transaktions-CSV",
         REPO/"Pipeline/02. Elasticity/Sweden_Elasticity_Data_Prep_SQL/output/Sweden_weekly_model_data_site_level.csv",
         CONTAINER_PIPELINE, "00_frozen_facit/tx/Sweden_weekly_model_data_site_level.csv"),
    ]

    print("=" * 72)
    print("SOND 7 -- OVERLEVNADSTES (om datorn forsvinner: gar allt att aterskapa?)")
    print(f"Blob-datummapp for LIVE: {df}")
    print("=" * 72)

    safe, unique, missing = [], [], []
    cat = None
    for category, label, local, container, blob_name in CHECKS:
        if category != cat:
            print(f"\n{category}:")
            cat = category
        loc_exists = local.exists()
        blob_exists = on_blob(container, blob_name)
        if blob_exists:
            tag, color = "SAKER (pa Blob)", safe
        elif loc_exists:
            tag, color = "DATOR-UNIK (bara lokalt!)", unique
        else:
            tag, color = "SAKNAS (varken Blob eller lokalt)", missing
        color.append(label)
        loc = "lokal:JA" if loc_exists else "lokal:nej"
        blb = "blob:JA" if blob_exists else "blob:NEJ"
        print(f"  [{tag:<32}] {label:<34} ({loc}, {blb})")

    print("\n" + "=" * 72)
    print(f"SAMMANFATTNING:  {len(safe)} sakra,  {len(unique)} dator-unika,  {len(missing)} saknade")
    if unique:
        print("\n  DATOR-UNIKA (forloras om datorn dor -- maste till Blob):")
        for u in unique:
            print(f"    - {u}")
    if missing:
        print("\n  SAKNADE (finns ingenstans -- maste produceras):")
        for m in missing:
            print(f"    - {m}")
    print("\n" + "=" * 72)
    if not unique and not missing:
        print("DOM: PASS -- alla Efter-inputs finns pa Blob. Overlevnadstesen HALLER")
        print("for inputs. (Koden separat pa GitHub; resultat-PUSH verifieras av run_after.)")
        rc = 0
    else:
        print("DOM: REVIEW -- se dator-unika/saknade ovan. Kor upload-skripten sa de")
        print("hamnar pa Blob, kor sedan denna sond igen -> ska bli PASS.")
        rc = 2
    print("=" * 72)
    return rc


if __name__ == "__main__":
    sys.exit(main())
