#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
survival_test.py  --  DET DEFINITIVA BEVISET pa overlevnadstesen (FD.37)
========================================================================
Sond 7 bevisar att filerna FINNS pa Blob. Detta test bevisar att Efter-steget
faktiskt KORS fran Blob -- genom att simulera att datorn inte har filerna:

  1. Doper TILLFALLIGT om run_step6:s lokala kallor (+ tx-CSV) till *.SURVIVALTEST
     -> nu finns de inte dar koden letar lokalt.
  2. Kor run_after --date-folder <date> (PULL maste hamta allt fran Blob).
  3. Aterstaller namnen OAVSETT utfall (finally -- aven vid krasch/avbrott).
  4. Dom: lyckades run_after? -> overlevnadstesen ar BEVISAD, ej paastad.

SAKERHET: rename (inte radering) -- helt reversibelt. finally aterstaller alltid.
Om nagot avbryts mitt i: kor med --restore-only for att aterstalla manuellt.

ANVANDNING:
    cd "C:\\Projekt\\BCG"; $env:PRICINGMODEL_AUTH="key"
    py -3.11 workspace\\survival_test.py --date-folder 2026-06-17 --dry-run
    py -3.11 workspace\\survival_test.py --date-folder 2026-06-17
    py -3.11 workspace\\survival_test.py --restore-only   # nodfall om avbrott

Developer: Jens Palmo. Author: Claude advisor 2026-06-22 (overlevnadstes-bevis).
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
SUFFIX = ".SURVIVALTEST"

# run_step6:s lokala KALLOR + tx -- de filer som ska "forsvinna" sa PULL maste hamta.
# (Identiska med download_outputs v2:s destinationer = run_step6:s kallor.)
LOCAL_SOURCES = [
    REPO/"Pipeline/02. Elasticity/2. Product Cluster Level Models/_archive_growing_2026-04-27_v2_pg4fix/output_summary.xlsx",
    REPO/"Pipeline/02. Elasticity/3. Product Site Level Models/output/model/output_summary.xlsx",
    REPO/"Pipeline/02. Elasticity/6. Fall Back Logic/input_data/final_model_cluster_granularity_Ivce.xlsx",
    REPO/"Pipeline/02. Elasticity/6. Fall Back Logic/input_data/output_summary_bundle.xlsx",
    REPO/"Pipeline/02. Elasticity/6. Fall Back Logic/input_data/Complete_Product_Data.xlsx",
    REPO/"Pipeline/01. Data Prep/output/Sweden_weekly_model_data_site_level_growing.csv",
]


def log(tag, msg): print(f"[{tag}] {msg}", flush=True)


def hide(paths):
    hidden = []
    for p in paths:
        if p.exists():
            tgt = p.with_name(p.name + SUFFIX)
            if tgt.exists(): tgt.unlink()
            p.rename(tgt)
            hidden.append((p, tgt))
            log("HIDE", f"{p.name} -> {tgt.name}")
        else:
            log("skip", f"{p.name} (fanns ej lokalt -- redan 'borta')")
    return hidden


def restore(paths):
    n = 0
    for p in paths:
        tgt = p.with_name(p.name + SUFFIX)
        if tgt.exists():
            if p.exists(): p.unlink()  # ta bort PULL:ad kopia, aterstall original
            tgt.rename(p)
            log("RESTORE", f"{tgt.name} -> {p.name}")
            n += 1
    log("RESTORE", f"{n} original aterstallda.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Definitivt overlevnadsbevis: gom lokala kallor, kor fran Blob.")
    ap.add_argument("--date-folder", default="2026-06-17")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore-only", action="store_true", help="Nodfall: aterstall *.SURVIVALTEST och avsluta.")
    args = ap.parse_args()

    if args.restore_only:
        restore(LOCAL_SOURCES); return 0

    print("=" * 70)
    print("DEFINITIVT OVERLEVNADSBEVIS -- simulerar att datorn saknar filerna")
    print("=" * 70)

    if args.dry_run:
        print("DRY-RUN -- skulle doina om (rename) dessa lokala kallor:")
        for p in LOCAL_SOURCES:
            print(f"  {'finns' if p.exists() else 'saknas'}: {p}")
        print("\nSedan kora run_after (PULL fran Blob), sedan aterstalla. Inget gjort.")
        return 0

    hidden = []
    try:
        log("STEP", "1. Gommer lokala kallor (rename -> *.SURVIVALTEST)...")
        hidden = hide(LOCAL_SOURCES)

        log("STEP", "2. Kor run_after (maste nu hamta ALLT fran Blob)...")
        run_after = REPO/"orchestration"/"runners"/"run_after.py"
        rc = subprocess.run(
            [sys.executable, str(run_after), "--date-folder", args.date_folder, "--no-push"],
            cwd=str(REPO),
        ).returncode
    finally:
        log("STEP", "3. Aterstaller original (finally -- alltid)...")
        restore(LOCAL_SOURCES)

    print("=" * 70)
    if rc == 0:
        print("DOM: BEVISAD -- run_after lyckades UTAN lokala kallor.")
        print("Efter-steget kor bevisligen fran Blob. Datorn ar UMBARLIG for")
        print("Efter-kedjan: en eftertradare kan klona GitHub + lasa Blob och kora.")
    else:
        print(f"DOM: EJ BEVISAD -- run_after exit={rc} utan lokala kallor.")
        print("Nagot lases fortfarande lokalt. Se loggen ovan for vilket steg som foll.")
        print("(Original aterstallda -- inget forlorat.)")
    print("=" * 70)
    return rc


if __name__ == "__main__":
    sys.exit(main())
