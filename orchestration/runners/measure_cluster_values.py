"""
measure_cluster_values.py -- mat de tva varden run_cluster_model.py kraver
==========================================================================
Handover + KARNPRINCIPER (matt, gissa inte): cluster-runnern har tva
familjespecifika varden som INTE far gissas analogt fran Site -- de mats:

  1. REMOTE_INPUT  -- cluster-CSV:ns EXAKTA filnamn pa VM:en.
  2. EXPECTED_KEYS -- cluster-modellens steg-1-4 KEY-antal (facit-referens).
                      OBS: ROADMAP:s "4180 KEY" ar STEG-5-BLENDEN, inte
                      nodvandigtvis steg 1-4. Las det riktiga talet ur
                      cluster-facitets output_summary.xlsx.

Detta script MATER bada och skriver ut tva rader att klistra in i
run_cluster_model.py:s konstantblock. Det ROR INGENTING (las-only) och
startar ingen korning.

Kor (global Python 3.11, fran repo-roten, VM behover INTE vara igang for
del 2 -- den laser den lokala frusna baslinjen):

    py -3.11 orchestration\\runners\\measure_cluster_values.py

Del 1 (REMOTE_INPUT) kraver att VM:en ar igang OCH att du ar pa kontorsnat/VPN
(LB.58). Om VM:en ar nere hoppar scriptet over del 1 och sager det -- kor om
nar VM:en startats, eller mat manuellt med ssh-raden som skrivs ut.

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Forfattare: Claude-radgivare, Phase Z FAS A.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

VM_IP = "172.18.148.4"
SSH_TARGET = f"azureuser@{VM_IP}"
REMOTE_DATA_DIR = "/home/azureuser/bcg/cluster/data"
# Cluster facit -- den skrivskyddade baslinjen (LF.3). Las-only.
LOCAL_FACIT = Path(
    r"C:\Projekt\BCG\Pipeline\02. Elasticity"
    r"\2. Product Cluster Level Models\output\azure_run_model\output_summary.xlsx"
)


def measure_remote_input() -> str | None:
    """Lista cluster-CSV:erna pa VM:en, nyaste forst. Returnerar exakt sokvag
    eller None om VM:en inte nas (nere eller utanfor kontorsnat/VPN)."""
    print("\n[1/2] REMOTE_INPUT -- cluster-CSV pa VM:en")
    print(f"      ssh {SSH_TARGET} \"ls -t {REMOTE_DATA_DIR}/*.csv\"")
    try:
        cp = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
             SSH_TARGET, f"ls -t {REMOTE_DATA_DIR}/*.csv 2>/dev/null | head -5"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        print(f"      VM ej nabar ({type(e).__name__}). Starta VM + var pa "
              f"kontorsnat/VPN, kor om. Eller mat manuellt med raden ovan.")
        return None
    if cp.returncode != 0 or not cp.stdout.strip():
        print(f"      Inga CSV-filer hittade (eller VM nere). stderr: {cp.stderr.strip()[:200]}")
        return None
    files = cp.stdout.strip().splitlines()
    print(f"      Hittade {len(files)} CSV (nyaste forst):")
    for i, f in enumerate(files):
        marker = "  <-- nyaste" if i == 0 else ""
        print(f"        {f}{marker}")
    newest = files[0]
    print(f"      => REMOTE_INPUT = \"{newest}\"")
    return newest


def measure_expected_keys() -> int | None:
    """Las cluster-facitets steg-1-4 KEY-antal ur den lokala frusna
    baslinjen. Las-only -- ror aldrig filen (LF.3)."""
    print("\n[2/2] EXPECTED_KEYS -- cluster steg-1-4 KEY ur facit")
    print(f"      Laser: {LOCAL_FACIT}")
    if not LOCAL_FACIT.exists():
        print("      Facit-filen finns inte lokalt. Antingen:")
        print("        - hamta den fran VM forst, eller")
        print("        - peka LOCAL_FACIT i detta script ratt, eller")
        print("        - lamna EXPECTED_KEYS = None (runnern raknar och rapporterar utan facit-jamforelse).")
        return None
    try:
        import pandas as pd
        df = pd.read_excel(LOCAL_FACIT)
        keys = df["KEY"].nunique() if "KEY" in df.columns else len(df)
        print(f"      => EXPECTED_KEYS = {keys}")
        if keys == 4180:
            print("      OBS: 4180 == ROADMAP:s step-5-blend-tal. Verifiera att DETTA "
                  "facit verkligen ar steg-1-4-output (output_summary.xlsx), inte blenden.")
        return int(keys)
    except Exception as e:
        print(f"      Kunde inte lasa ({e}). Lamna EXPECTED_KEYS = None tills matt.")
        return None


def main() -> int:
    print("=" * 68)
    print("Mater de tva varden run_cluster_model.py kraver (matt, gissa inte)")
    print("=" * 68)
    remote_input = measure_remote_input()
    expected_keys = measure_expected_keys()

    print("\n" + "=" * 68)
    print("KLISTRA IN i run_cluster_model.py:s konstantblock:")
    print("=" * 68)
    if remote_input:
        print(f'REMOTE_INPUT   = "{remote_input}"')
    else:
        print('REMOTE_INPUT   = "..."   # EJ MATT -- VM nere/ej nabar, mat manuellt')
    if expected_keys is not None:
        print(f"EXPECTED_KEYS  = {expected_keys}")
    else:
        print("EXPECTED_KEYS  = None    # EJ MATT -- runnern raknar utan facit-jamforelse")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
