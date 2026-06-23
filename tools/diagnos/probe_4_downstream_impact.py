#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_4_downstream_impact.py  --  SOND 4: biter CSV-skillnaden NEDSTRÖMS?
=========================================================================
FRÅGAN den svarar: om vi fixar config och bygger cluster på maj-CSV:n --
refereras de kolumner som SKILJER (No_of_Sites-drift, tappad TotalNetXVat,
ev. ProductGroupL4Name) någonstans NEDSTRÖMS (model.py, data_prep_after_
model_output.py, Step 6 / Fall_Back_Logic.py)? Om ja -> en config-fix räcker
INTE; samma divergens biter senare och vi får en NY krasch längre fram.

VARFÖR: 2026-06-23 fokuserade vi på feature_selection-kraschen (steg 3). Men
om model.py (steg 4) eller Step 6 (väven) läser t.ex. TotalNetXVat -- som maj-CSV
TAPPADE -- så bygger cluster klart men kraschar/ger fel i ett senare steg. Att
veta detta INNAN relaunch sparar en ~50-min-körning som dör i steg 4 i stället
för steg 3. Mät hela nedströms-konsekvensen på en gång.

LETAR (på VM -- modellstegen + Step 6 körs där / koden ligger där):
  - cluster/code/model.py                         (steg 4)
  - cluster/code/data_prep_after_model_output.py  (steg 5, Excel — körs lokalt men koden finns)
  - Fall Back Logic / Step 6                       (väven, om på VM)
  för referenser till de skiljande kolumnerna.

KÖR (global py -3.11, kräver ssh):
    py -3.11 probe_4_downstream_impact.py
    py -3.11 probe_4_downstream_impact.py --cols No_of_Sites TotalNetXVat ProductGroupL4Name

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Författare: Claude-rådgivare.
Beroende: ssh på PATH. std-lib.
"""
from __future__ import annotations
import argparse
import subprocess
import sys

VM = "azureuser@172.18.148.4"
# Kolumner som skiljer maj/april (default från 2026-06-23-mätningen)
DEFAULT_COLS = ["No_of_Sites", "No of Sites", "TotalNetXVat", "ProductGroupL4Name"]
# Nedströms-filer (efter feature_selection) på VM
DOWNSTREAM = [
    "~/bcg/cluster/code/model.py",
    "~/bcg/cluster/code/data_prep_after_model_output.py",
    "~/bcg/cluster/code/utils.py",
    # Step 6 / väven — sök brett under bcg om den ligger på VM
]


def ssh(cmd: str, timeout: int = 40) -> str:
    r = subprocess.run(["ssh", VM, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout  # returnerar tom om fel; vi rapporterar per fil


def grep_file(remote_path: str, col: str) -> list[str]:
    """grep efter EN kolumn i EN fil. Enkla citat, inga inre dubbla, ett mönster (LB.13)."""
    # Ersätt mellanslag i kolumnnamn med . (regex any-char) för att undvika citat-strul
    pattern = col.replace(" ", ".")
    out = ssh(f"grep -n '{pattern}' {remote_path} 2>/dev/null")
    return [l for l in out.splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="SOND 4: nedströms-konsekvens av CSV-skillnad.")
    ap.add_argument("--cols", nargs="*", default=DEFAULT_COLS)
    ap.add_argument("--files", nargs="*", default=DOWNSTREAM)
    args = ap.parse_args()

    print("=" * 72)
    print("SOND 4 -- biter CSV-skillnaden NEDSTRÖMS (model.py / steg 5 / Step 6)?")
    print(f"Kolumner: {args.cols}")
    print("=" * 72)

    impact = {}  # col -> [ (fil, rad) ]
    for f in args.files:
        fname = f.split("/")[-1]
        print(f"\n--- {fname} ({f}) ---")
        file_has_any = False
        for col in args.cols:
            hits = grep_file(f, col)
            if hits:
                file_has_any = True
                impact.setdefault(col, []).append(fname)
                for h in hits[:5]:
                    print(f"  [{col}] {h[:150]}")
        if not file_has_any:
            print("  (ingen av de skiljande kolumnerna refereras här)")

    # Sök även Step 6 brett (väven kan ligga var som helst under bcg)
    print(f"\n--- Step 6 / Fall_Back (bred sökning under ~/bcg) ---")
    for col in args.cols:
        pattern = col.replace(" ", ".")
        out = ssh(f"grep -rln '{pattern}' ~/bcg 2>/dev/null | grep -i 'fall\\|step6\\|blend' | head -5")
        files = [l for l in out.splitlines() if l.strip()]
        if files:
            impact.setdefault(col, []).extend(f.split("/")[-1] for f in files)
            print(f"  [{col}] refereras i: {', '.join(f.split('/')[-1] for f in files)}")
    if not any("fall" in str(v).lower() or "step6" in str(v).lower() for v in impact.values()):
        print("  (inga Step6/fallback-träffar -- eller väven ligger ej på VM)")

    print("\n" + "=" * 72)
    print("TOLKNING:")
    if impact:
        for col, files in impact.items():
            print(f"  '{col}' refereras nedströms i: {sorted(set(files))}")
        print("\n  -> Om en TAPPAD kolumn (t.ex. TotalNetXVat) refereras nedströms:")
        print("     config-fix räcker EJ. Den kolumnen måste tillbaka i maj-CSV (data_prep),")
        print("     annars kraschar/felar steg 4/5/6 EFTER att cluster byggt klart (~50 min spilld).")
        print("  -> Om bara namn-drift-kolumner (No_of_Sites) refereras och de FINNS (rätt namn):")
        print("     config-fix räcker, nedströms ser rätt kolumn.")
        verdict = "REVIEW -- skiljande kolumner refereras nedströms, se ovan"
    else:
        print("  Inga skiljande kolumner refereras nedströms -> config-fix på feature_selection")
        print("  räcker; cluster bör bygga HELA vägen efter fixen.")
        verdict = "PASS -- ingen nedströms-konsekvens, config-fix räcker"
    print(f"\nDOM: {verdict}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
