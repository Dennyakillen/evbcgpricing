"""
support_files_check.py -- verifiera att en modells config-refererade stodfiler finns
====================================================================================
SYFTE: INNAN korning -- bekrafta att varje fil modellens config.yml pekar pa
faktiskt existerar, sa korningen inte dor flera steg in pa en saknad fil. Fangar
ocksa "dott config-arv" (nycklar som pekar pa filer skriptet aldrig laser -- som
InScope Mapping.xlsx i bundle, FD.36).

ANVANDNING:
    py -3.11 support_files_check.py "<modell-rot>" "<code/src/config.yml>"
    (default: bundle clinic models)
    -> skriver support_files_result.txt

VARNING: en SAKNAD fil betyder inte alltid blockerare -- om skriptet aldrig laser
nyckeln ar det dott arv. Verifiera med grep i kallkoden (model_chain_validator)
innan du bygger en saknad fil i onodan.

Utvecklare: Jens Palmo. Author: Claude (teknisk radgivare).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, re
from datetime import datetime

def check(model_root: str, config_path: str):
    out_path = "support_files_result.txt"
    f = open(out_path, "w", encoding="utf-8")
    def L(m):
        print(m); f.write(str(m) + "\n"); f.flush()

    L("=" * 64)
    L("SUPPORT FILES CHECK")
    L(f"Modell-rot: {model_root}")
    L(f"Kord: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L("=" * 64)

    if not os.path.exists(config_path):
        L(f"  config saknas: {config_path}"); f.close(); return

    # Plocka ut alla filsokvagar ur config (varden som ser ut som .xlsx/.csv-sokvagar)
    txt = open(config_path, encoding="utf-8", errors="replace").read()
    paths = re.findall(r':\s*["\']?([^\s"\'#]+\.(?:xlsx|csv))["\']?', txt)
    seen = set()
    L(f"\nHittade {len(paths)} fil-referenser i config:")
    for rel in paths:
        if rel in seen:
            continue
        seen.add(rel)
        full = os.path.join(model_root, rel.lstrip("/\\"))
        ex = os.path.exists(full)
        sz = f"{os.path.getsize(full)/1024:.1f} KB" if ex else "-"
        mark = "OK    " if ex else "SAKNAS"
        L(f"  [{mark}] {rel}  ({sz})")

    L("\nNOTERA: SAKNAS == blockerare ENDAST om kallkoden faktiskt laser filen.")
    L("Kor model_chain_validator / grep for att skilja levande beroende fran dott arv.")
    L(f"\nKLAR -> {out_path}")
    f.close()

if __name__ == "__main__":
    root = (r"C:\Projekt\BCG\Pipeline\02. Elasticity\5. Bundle Clinic Models")
    cfg = os.path.join(root, r"code\src\config.yml")
    check(sys.argv[1] if len(sys.argv) > 1 else root,
          sys.argv[2] if len(sys.argv) > 2 else cfg)
