#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_2_april_vs_maj_csv.py  --  SOND 2: april-CSV vs maj-CSV strukturdiff
===========================================================================
FRÅGAN den svarar: hur skiljer sig MAJ-cluster-CSV:n STRUKTURELLT från
APRIL-cluster-CSV:n (den som byggde 4180 modeller RENT 2026-06-17)? Vilka
kolumner är nya i maj, vilka tappades, vilka är namn-drift?

VARFÖR den är avgörande: 2026-06-23 fanns en OLÖST MOTSÄGELSE -- sond 1 sa
att ProductGroupL4Name saknas i config, men april byggde rent. Antingen
hade april-CSV en annan kolumnuppsättning, ELLER 17-juni-körningen var en
annan CSV än vi tror. Denna sond MÄTER skillnaden i stället för att gissa.

Den läser BÅDA CSV-headers (maj = nuvarande, april = arkiverad .pre_maj_*)
och korsar dem. RÖR INGET. Resultatet avgör om config-fixen är KOMPLETT
(bara de kända skillnaderna) eller om data_prep-vägen divergerat bredare
(då måste man förstå VARFÖR innan cluster byggs på maj-CSV:n).

KÄNT 2026-06-23 (att verifiera/utöka): maj saknar 'TotalNetXVat' + 'No of Sites',
har 'No_of_Sites'. april = 12 kol, maj = 11 kol.

KÖR (global py -3.11, kräver ssh):
    py -3.11 probe_2_april_vs_maj_csv.py
    py -3.11 probe_2_april_vs_maj_csv.py --april <VM-path>  # om arkivnamn känt

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Författare: Claude-rådgivare.
Beroende: ssh på PATH. std-lib.
"""
from __future__ import annotations
import argparse
import subprocess
import sys

VM = "azureuser@172.18.148.4"
MAJ_DEFAULT = "~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv"
# April-CSV arkiverades som .pre_maj_<stamp> innan maj-CSV scp:ades 2026-06-23.


def ssh(cmd: str, timeout: int = 30) -> str:
    r = subprocess.run(["ssh", VM, cmd], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 and not r.stdout:
        raise RuntimeError(f"ssh-fel: {r.stderr.strip()[:200]}")
    return r.stdout


def cols_of(path: str) -> list[str]:
    return [c.strip() for c in ssh(f"head -1 {path}").strip().split(",")]


def find_april_archive() -> str | None:
    out = ssh("ls -t ~/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv.pre_maj_* 2>/dev/null | head -1").strip()
    return out or None


def main() -> int:
    ap = argparse.ArgumentParser(description="SOND 2: april-CSV vs maj-CSV strukturdiff.")
    ap.add_argument("--maj", default=MAJ_DEFAULT)
    ap.add_argument("--april", default=None, help="VM-path till april-arkiv; annars auto (.pre_maj_*).")
    args = ap.parse_args()

    print("=" * 72)
    print("SOND 2 -- april-CSV vs maj-CSV strukturdiff")
    print("=" * 72)

    try:
        maj = cols_of(args.maj)
        april_path = args.april or find_april_archive()
        if not april_path:
            print("[VARNING] Hittade inget april-arkiv (.pre_maj_*).")
            print(f"  MAJ-CSV ({len(maj)} kol): {maj}")
            print("  -> Kan ej diffa. Ange --april med rätt VM-path om arkivet flyttats.")
            return 2
        april = cols_of(april_path)
    except Exception as e:
        print(f"[FEL] {e}\n  -> ssh/VM/token. Sonden gissar inte.")
        return 2

    print(f"\nAPRIL ({april_path.split('/')[-1]}): {len(april)} kolumner")
    print(f"MAJ:   {len(maj)} kolumner")

    aprset, majset = set(april), set(maj)

    print(f"\n=== NYA i MAJ (maj-data_prep lade till) ===")
    new_maj = [c for c in maj if c not in aprset]
    for c in new_maj or ["  (inga)"]:
        print(f"  + {c}" if c in majset else c)

    print(f"\n=== TAPPADE i MAJ (fanns i april, borta i maj) ===")
    lost = [c for c in april if c not in majset]
    for c in lost or ["  (inga)"]:
        print(f"  - {c}" if c in aprset else c)

    print(f"\n=== NAMN-DRIFTER (mellanslag <-> understreck) ===")
    drifts = []
    for c in new_maj:
        alt = c.replace("_", " ") if "_" in c else c.replace(" ", "_")
        if alt in aprset:
            print(f"  MAJ '{c}'  <->  APRIL '{alt}'")
            drifts.append((c, alt))
    if not drifts:
        print("  (inga rena namn-drifter)")

    # Genuina skillnader (ej bara namn-drift) = de som biter nedströms
    drift_maj = {d[0] for d in drifts}
    drift_apr = {d[1] for d in drifts}
    genuine_new = [c for c in new_maj if c not in drift_maj]
    genuine_lost = [c for c in lost if c not in drift_apr]

    print(f"\n=== TOLKNING ===")
    if drifts:
        print(f"  Namn-drift: {len(drifts)} kolumn(er) -- samma data, olika namn (config-fix: tål båda).")
    if genuine_new:
        print(f"  GENUINT NYA i maj: {genuine_new} -- config måste känna dessa (rätt typ).")
    if genuine_lost:
        print(f"  GENUINT TAPPADE i maj: {genuine_lost}")
        print(f"    -> VIKTIGT: om nedströms-kod (model.py/Step6) LÄSER dessa, biter det senare.")
        print(f"    -> Kör sond 4 (nedströms-konsekvens) för att se om de refereras.")
    if not (genuine_new or genuine_lost):
        print("  Skillnaden är ENBART namn-drift -> config-fix räcker, ingen strukturell divergens.")

    print(f"\n  MOTSÄGELSE-CHECK (ProductGroupL4Name): "
          + ("finns i BÅDA" if "ProductGroupL4Name" in aprset and "ProductGroupL4Name" in majset
             else "skiljer -- se ovan"))
    if "ProductGroupL4Name" in aprset and "ProductGroupL4Name" in majset:
        print("    -> Den fanns i april med. Om sond 1 sa att config saknar den OCH april byggde rent,")
        print("       byggde april troligen på en ANNAN config/CSV än vi tror. Verifiera mot 17-juni-loggen.")

    print("\n" + "=" * 72)
    has_genuine = bool(genuine_new or genuine_lost)
    print("DOM: " + ("REVIEW -- strukturell divergens (ej bara namn), förstå VARFÖR via sond 3"
                     if has_genuine else "PASS-ish -- endast namn-drift, config-fix räcker (verifiera sond 4)"))
    print("=" * 72)
    return 2 if has_genuine else 0


if __name__ == "__main__":
    sys.exit(main())
