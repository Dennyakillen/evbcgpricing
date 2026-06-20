"""
model_chain_validator.py -- skanna en modellmapps skript for vaxande-data-risker
================================================================================
SYFTE: INNAN en BCG-modell kors pa vaxande data -- kartlagg varje stalle dar
vaxande rader kan tappas tyst, eller dar ursprungsmiljons antaganden (UK/Alteryx)
biter. Statisk kallkods-skanning, kor ingen modell, ror ingen fil. (P.3 "anta tyst
filtrering tills motsatsen bevisats"; LESSONS LB.50/LB.73-76.)

Skannar alla *.py i en mapp for fem riskklasser:
  [1] env-styrda datumfonster (BCG_START_DATE/BCG_END_DATE) -- ett styrstalle?
  [2] datum-filter (week >= / < ) -- kapar de 2026-data om fonstret ar fruset?
  [3] hardkodade ar (2024/2025) -- frusna antaganden utan override
  [4] tyst datatapp: how='inner', .isin(), .dropna() -- inner-merge tommer
  [5] encoding-las (cp1252) -- UK-arv pa filer du matar

ANVANDNING:
    py -3.11 model_chain_validator.py "<sokvag till code-mapp>"
    (default: bundle clinic models code-mapp)
    -> skriver model_chain_validation_result.txt

TOLKNING:
    - Alla merges left/outer + env-styrt fonster = tal vaxande (gron).
    - inner-merge eller hardkodat ar = mat populationen fore/efter med
      chain_population_probe innan du litar pa korningen.

Utvecklare: Jens Palmo. Author: Claude (teknisk radgivare).
"""
import warnings; warnings.filterwarnings("ignore")
import re, os, sys, glob
from datetime import datetime

PATTERNS = {
    "env-fonster (BCG_*/environ)": r"environ|BCG_\w+",
    "datum-filter (week/DATE jamf)": r"week.*[<>]=?|START_DATE|END_DATE|>=.*DATE|DATE.*<",
    "hardkodat ar 2020-2026": r"20(2[0-6])-\d\d-\d\d|'20(2[0-6])'",
    "tyst datatapp (inner/isin/dropna)": r"how\s*=\s*['\"]inner|\.isin\(|\.dropna\(",
    "encoding-las (cp1252)": r"cp1252|encoding\s*=",
}

def scan(code_dir: str):
    out_path = "model_chain_validation_result.txt"
    f = open(out_path, "w", encoding="utf-8")
    def L(m):
        print(m); f.write(str(m) + "\n"); f.flush()

    L("=" * 64)
    L(f"MODEL CHAIN VALIDATOR: {code_dir}")
    L(f"Kord: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L("=" * 64)

    scripts = sorted(glob.glob(os.path.join(code_dir, "*.py")))
    if not scripts:
        L(f"  INGA .py-filer i {code_dir} -- kontrollera sokvagen.")
        f.close(); return

    L(f"\nSkannar {len(scripts)} skript: {[os.path.basename(s) for s in scripts]}")
    for label, pat in PATTERNS.items():
        L(f"\n[{label}]")
        hits = 0
        rx = re.compile(pat)
        for sc in scripts:
            try:
                lines = open(sc, encoding="utf-8", errors="replace").read().splitlines()
            except Exception as e:
                L(f"  LASFEL {os.path.basename(sc)}: {e}"); continue
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if not s or s.startswith("#"):
                    continue
                if rx.search(ln):
                    L(f"  {os.path.basename(sc)} L{i}: {s[:95]}")
                    hits += 1
        if hits == 0:
            L("  (inga traffar)")

    L("\nTOLKNING: env-styrt fonster + enbart left/outer-merges = tal vaxande.")
    L("inner-merge / hardkodat ar -> verifiera population med chain_population_probe.")
    L(f"\nKLAR -> {out_path}")
    f.close()

if __name__ == "__main__":
    default = (r"C:\Projekt\BCG\Pipeline\02. Elasticity"
               r"\5. Bundle Clinic Models\code")
    scan(sys.argv[1] if len(sys.argv) > 1 else default)
