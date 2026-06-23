#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_1_csv_vs_config.py  --  SOND 1: CSV-kolumner vs config col_type
======================================================================
FRÅGAN den svarar: vilka av (maj-)cluster-CSV:ns kolumner SAKNAS i
config.yml:s col_type-sektion -- och är det en NAMN-DRIFT (mellanslag
<-> understreck, FAS 3 / G12) eller en GENUINT saknad kolumn?

VARFÖR: feature_selection.py:532 loopar df:s kolumner och slår upp varje i
config['col_type'][col]. Saknas en -> KeyError, pipeline dör efter ~4 min.
Detta är felet som blockerade cluster-maj 2026-06-23 (KeyError 'No_of_Sites').

Sonden RÖR INGET -- läser bara CSV-header (på VM via ssh) + config.yml (VM)
och korsar dem. Den DÖMER inte, FIXAR inte -- den MÄTER vad som saknas så
fixen kan göras EN gång (alla kolumner) i stället för att snubbla kolumn
för kolumn med 4-minuters-kraschar emellan (vilket hände idag).

KÖR (global py -3.11, kräver ssh till VM):
    py -3.11 probe_1_csv_vs_config.py
    py -3.11 probe_1_csv_vs_config.py --csv <VM-path> --config <VM-path>

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Författare: Claude-rådgivare.
Beroende: ssh på PATH (kör mot VM). std-lib (subprocess, argparse).
"""
from __future__ import annotations
import argparse
import subprocess
import sys

VM = "azureuser@172.18.148.4"
CSV_DEFAULT = "~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv"
CONFIG_DEFAULT = "~/bcg/cluster/code/src/config.yml"


def ssh(cmd: str, timeout: int = 30) -> str:
    """Kör ETT kommando på VM. Enkla citat runt cmd (LB.13 — inga inre dubbla)."""
    r = subprocess.run(["ssh", VM, cmd], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 and not r.stdout:
        raise RuntimeError(f"ssh-fel: {r.stderr.strip()[:200]}")
    return r.stdout


def csv_columns(path: str) -> list[str]:
    """Headerns kolumnnamn (första raden), trimmade."""
    hdr = ssh(f"head -1 {path}").strip()
    return [c.strip() for c in hdr.split(",")]


def config_coltype_keys(path: str) -> set[str]:
    """Nycklar i col_type-sektionen. Läser från 'col_type:' tills nästa toppnyckel."""
    # Hämta col_type-sektionen: från raden med 'col_type:' och ~70 rader framåt.
    raw = ssh(f"grep -n -A70 'col_type' {path}")
    keys = set()
    started = False
    for line in raw.splitlines():
        # rad-format från grep: "57:col_type:" eller "70-    No of Sites : 'float64'"
        body = line.split(":", 1)[1] if line[:1].isdigit() and ":" in line else line
        if "col_type" in line:
            started = True
            continue
        if not started:
            continue
        # En col_type-rad ser ut: "    Kolumnnamn : 'typ'"  -> nyckel före första ':'
        if "'" in line and ":" in body:
            key = body.split(":")[0].strip().lstrip("-").strip()
            # filtrera bort radnummer-artefakter
            if key and not key.isdigit():
                keys.add(key)
        # stoppa om vi når en uppenbar nästa toppnyckel (ingen indrag, slutar med :)
        stripped = body.strip()
        if started and stripped and not line[:1].isspace() and stripped.endswith(":") and "col_type" not in line:
            break
    return keys


def main() -> int:
    ap = argparse.ArgumentParser(description="SOND 1: CSV-kolumner vs config col_type.")
    ap.add_argument("--csv", default=CSV_DEFAULT, help="VM-path till cluster-CSV.")
    ap.add_argument("--config", default=CONFIG_DEFAULT, help="VM-path till config.yml.")
    args = ap.parse_args()

    print("=" * 72)
    print("SOND 1 -- CSV-kolumner vs config col_type")
    print(f"CSV:    {args.csv}")
    print(f"config: {args.config}")
    print("=" * 72)

    try:
        cols = csv_columns(args.csv)
        keys = config_coltype_keys(args.config)
    except Exception as e:
        print(f"[FEL] {e}")
        print("  -> Kontrollera ssh/VM igång/token. Sonden gissar inte.")
        return 2

    print(f"\nCSV har {len(cols)} kolumner. config col_type har {len(keys)} nycklar.")

    missing = [c for c in cols if c not in keys]
    print(f"\n=== KOLUMNER I CSV SOM SAKNAS I config col_type ({len(missing)}) ===")
    if not missing:
        print("  (inga -- alla CSV-kolumner finns i config. KeyError kommer EJ härifrån.)")
    drift, genuine = [], []
    for c in missing:
        alt_us = c.replace(" ", "_")
        alt_sp = c.replace("_", " ")
        if alt_us in keys:
            print(f"  NAMN-DRIFT  CSV '{c}'  <- config har '{alt_us}' (understreck-drift, G12)")
            drift.append((c, alt_us))
        elif alt_sp in keys:
            print(f"  NAMN-DRIFT  CSV '{c}'  <- config har '{alt_sp}' (mellanslag-drift, G12)")
            drift.append((c, alt_sp))
        else:
            print(f"  GENUINT SAKNAD  CSV '{c}'  (ingen namnvariant i config -- ny kolumn)")
            genuine.append(c)

    print(f"\n=== FÖRSLAG TILL config-FIX (additivt, behåll befintliga rader) ===")
    if drift:
        print("  Namn-drifter -- lägg till understreck-varianten BREDVID befintlig (tål båda):")
        for csv_name, cfg_name in drift:
            print(f"    {csv_name} : (samma typ som '{cfg_name}')")
    if genuine:
        print("  Genuint saknade -- lägg till med RÄTT typ (bekräfta mot kolumnens innehåll först):")
        for c in genuine:
            print(f"    {c} : '???'   # läs kolumnens värden, gissa inte typ")
    if not missing:
        print("  (ingen fix behövs på config-nivå -- felet ligger annorstädes)")

    print("\n" + "=" * 72)
    verdict = "REVIEW -- kolumner saknas, se fix-förslag" if missing else "PASS -- config täcker alla CSV-kolumner"
    print(f"DOM: {verdict}")
    print("=" * 72)
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
