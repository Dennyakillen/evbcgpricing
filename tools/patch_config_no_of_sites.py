#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_config_no_of_sites.py  --  VAEG A (defensiv union): laer config.yml laesa
SQL-prep-schemat (No_of_Sites, understreck) UTAN att tappa BA-schemat (No of Sites).
================================================================================
ROTORSAK (bevisad sond 3 + lokal config-maetning 2026-06-23):
  Cluster-maj kraschar i feature_selection.py:532
    df[col].astype(config['col_type'][col])   -> KeyError
  Maj-CSV kommer fran SQL-prep-vaegen (kanonisk: No_of_Sites, understreck;
  se MEASURE_COLS + facit-alias i replicate_dataprep). config.yml baer den
  AELDRE BA/facit-konventionen (No of Sites, mellanslag). config slaepar efter
  kanon -- alltsa fixas config, INTE SQL-prep.

STRATEGI (Jens 2026-06-23): defensiv union -- "slaepp igenom MER, aldrig mindre".
  Laegg understrecks-varianten BREDVID mellanslags-varianten. Bada vaegarna
  fungerar efterat (SQL-prep-CSV och ev. gammal BA-CSV). Ingen befintlig
  funktion tas bort. BCG-logiken oroerd; bara config utvidgas.

TVA aendringar (additiva):
  1. cols_to_try (L48): laegg 'No_of_Sites' efter 'No of Sites'
     -> feature_selection far en feature-kandidat som FINNS i SQL-prep-CSV.
        (foersaekring mot tyst feature-bortfall, R7-klass: annars bygger
         cluster klart men UTAN No_of_Sites som variabel.)
  2. col_type (efter L72): laegg "No_of_Sites : 'float64'"
     -> typ-uppslaget pa rad 532 hittar den faktiska kolumnen (stoppar KeyError).
  TotalNetXVat (L109): OROERD. Ej en feature (varken cols_to_try/cols_needed);
  col_type-uppslag pa en franvarande kolumn aer en no-op. Roer ej mer aen noedvaendigt.

IDEMPOTENT: kollar om understrecks-varianten redan finns -> hoppar da den raden.
SAEKERHET: backup foerst; UTF-8 utan BOM (filen aer redan BOM-loes: 23 20 47);
matchar exakt indrag + trailing spaces; verifierar sin egen aendring efterat.

KOER (global py -3.11, lokalt -- ingen VM):
    py -3.11 patch_config_no_of_sites.py
    py -3.11 patch_config_no_of_sites.py --dry-run    # visa diff, skriv inget
    py -3.11 patch_config_no_of_sites.py --config "<annan path>"

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Foerfattare: Claude-radgivare.
Beroende: std-lib (pathlib, argparse, datetime, shutil). Inga tredjepartspaket.
"""
from __future__ import annotations
import argparse
import datetime
import shutil
import sys
from pathlib import Path

DEFAULT_CONFIG = (
    r"C:\Projekt\BCG\Pipeline\02. Elasticity"
    r"\2. Product Cluster Level Models\code\src\config.yml"
)

# Exakta straengar att matcha (maetta lokalt 2026-06-23, inkl. trailing spaces).
# cols_to_try-raden: 'No of Sites', foeljs av radslut (nasta rad ar fortsaettningen).
COLS_TO_TRY_NEEDLE = "'No of Sites',"
COLS_TO_TRY_INSERT = "'No of Sites','No_of_Sites',"

# col_type-raden: fyra blanksteg indrag + tva trailing spaces (maett).
COLTYPE_NEEDLE = "    No of Sites : 'float64'  "
COLTYPE_INSERT = "    No of Sites : 'float64'  \n    No_of_Sites : 'float64'  "

# Markoer foer idempotens (om understreck redan finns nagonstans i col_type/cols_to_try)
COLTYPE_DONE_MARK = "No_of_Sites : 'float64'"
COLS_TO_TRY_DONE_MARK = "'No_of_Sites'"


def read_text_no_bom(p: Path) -> str:
    # Filen aer BOM-loes UTF-8 (verifierat 23 20 47). Las som ren UTF-8.
    return p.read_text(encoding="utf-8")


def write_text_no_bom(p: Path, text: str) -> None:
    # WriteAllText med UTF-8 utan BOM (motsvarar [System.IO.File]::WriteAllText
    # med UTF8Encoding(False) -- aldrig Set-Content -Encoding UTF8 som ger BOM).
    import codecs
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Vaeg A defensiv union: config.yml taal No_of_Sites (understreck)."
    )
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="Path till config.yml")
    ap.add_argument("--dry-run", action="store_true", help="Visa vad som skulle aendras; skriv inget.")
    args = ap.parse_args()

    cfg = Path(args.config)
    print("=" * 74)
    print("PATCH config.yml -- Vaeg A defensiv union (No_of_Sites bredvid No of Sites)")
    print(f"Fil: {cfg}")
    print("=" * 74)

    if not cfg.exists():
        print(f"[FEL] Hittar inte config.yml: {cfg}")
        print("  -> Kontrollera --config-pathen. Skriptet gissar inte.")
        return 2

    original = read_text_no_bom(cfg)
    text = original
    changes = []
    skipped = []

    # --- Aendring 1: cols_to_try ---
    if COLS_TO_TRY_DONE_MARK in text:
        skipped.append("cols_to_try: 'No_of_Sites' finns redan -- hoppar (idempotent).")
    elif COLS_TO_TRY_NEEDLE in text:
        # Saekerhet: matcha bara EN gang (cols_to_try-raden). Raekna foerekomster.
        n = text.count(COLS_TO_TRY_NEEDLE)
        if n != 1:
            print(f"[STOPP] '{COLS_TO_TRY_NEEDLE}' foerekommer {n} ggr (vaentade 1).")
            print("  -> Tvetydig matchning. Inspektera manuellt; skriptet roer inget.")
            return 2
        text = text.replace(COLS_TO_TRY_NEEDLE, COLS_TO_TRY_INSERT, 1)
        changes.append("cols_to_try (L48): la till 'No_of_Sites' efter 'No of Sites'.")
    else:
        print(f"[STOPP] Hittar inte cols_to_try-naalen: {COLS_TO_TRY_NEEDLE!r}")
        print("  -> config-formatet har aendrats. Maet om innan patch.")
        return 2

    # --- Aendring 2: col_type ---
    if COLTYPE_DONE_MARK in text:
        skipped.append("col_type: \"No_of_Sites : 'float64'\" finns redan -- hoppar (idempotent).")
    elif COLTYPE_NEEDLE in text:
        n = text.count(COLTYPE_NEEDLE)
        if n != 1:
            print(f"[STOPP] col_type-naalen foerekommer {n} ggr (vaentade 1).")
            print("  -> Tvetydig matchning. Inspektera manuellt; skriptet roer inget.")
            return 2
        text = text.replace(COLTYPE_NEEDLE, COLTYPE_INSERT, 1)
        changes.append("col_type (efter L72): la till \"No_of_Sites : 'float64'\".")
    else:
        print(f"[STOPP] Hittar inte col_type-naalen (exakt, inkl. trailing spaces).")
        print("  -> Trailing whitespace kan ha aendrats. Maet om L70-75 innan patch.")
        return 2

    # --- Rapport ---
    print("\nPLANERADE AENDRINGAR:")
    for c in changes:
        print(f"  + {c}")
    for s in skipped:
        print(f"  = {s}")
    print("  = TotalNetXVat (L109): OROERD (ej feature; no-op vid franvaro).")

    if not changes:
        print("\n[KLART] Inget att goera -- config redan patchad (idempotent).")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] Inget skrevs. Koer utan --dry-run foer att tillaempa.")
        return 0

    # --- Backup + skriv ---
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    bak = cfg.with_suffix(cfg.suffix + f".before-patch-{stamp}.bak")
    shutil.copy2(cfg, bak)
    print(f"\n[Backup] {bak}")

    write_text_no_bom(cfg, text)
    print(f"[Skrev]  {cfg} (UTF-8 utan BOM)")

    # --- Verifiera egen aendring (laes om fran disk) ---
    verify = read_text_no_bom(cfg)
    ok_try = COLS_TO_TRY_DONE_MARK in verify
    ok_type = COLTYPE_DONE_MARK in verify
    bom = cfg.read_bytes()[:3] == b"\xef\xbb\xbf"
    print("\nVERIFIERING (laest om fran disk):")
    print(f"  cols_to_try har 'No_of_Sites' : {'JA' if ok_try else 'NEJ'}")
    print(f"  col_type har No_of_Sites      : {'JA' if ok_type else 'NEJ'}")
    print(f"  BOM infoerd (ska vara NEJ)     : {'JA -- FEL!' if bom else 'NEJ (bra)'}")

    if ok_try and ok_type and not bom:
        print("\n[KLART] Patch tillaempad och verifierad. Naesta: scp config -> VM, relaunch cluster.")
        return 0
    print("\n[VARNING] Verifiering ej helt groen -- inspektera filen + backup ovan.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
