# find_timing_excels.py -- READ-ONLY: vilka Excel-filer finns i output-mapparna, och bar nagon korttid?
import os
from pathlib import Path
from datetime import datetime

DIRS = [
    r"C:\Projekt\BCG\verify_tool",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\3. Product Site Level Models\output\azure_run_model",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\3. Product Site Level Models\output",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\5. Bundle Clinic Models\output",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\6. Fall Back Logic\output_data",
    r"C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output",
]

print("=== Excel-filer per mapp (namn, KB, andrad) ===")
for d in DIRS:
    p = Path(d)
    if not p.exists():
        print("\n[SAKNAS] " + d)
        continue
    xls = sorted(p.glob("*.xlsx")) + sorted(p.glob("*.xlsm"))
    print("\n--- " + d + " ---")
    if not xls:
        print("  (inga Excel-filer direkt i mappen)")
    for f in xls:
        kb = round(f.stat().st_size / 1024, 1)
        mod = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {f.name:<60} {kb:>8} KB  {mod}")
