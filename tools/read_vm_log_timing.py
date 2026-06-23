# read_vm_log_timing.py -- READ-ONLY: plocka korttider ur VM-loggarna (april + maj).
# Loggarna har en tidssammanfattning per steg + total. Vi filtrerar strukturlinjer.
import re
from pathlib import Path

LOGDIR = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\_vm_logs")
# Monster som fangar BCG-launcherns tidssammanfattning + per-steg-tider
PATTERNS = re.compile(
    r"(regular_price|data_prep|feature_selection|model\.py|"
    r"min\s+\d+\s+sec|Total|SUMMA|AKTIV|Time taken|Finished|completed|"
    r"\d+\s*min\s*\d+\s*sec|sec\b|elapsed|duration|Models built)",
    re.IGNORECASE)

for f in sorted(LOGDIR.glob("*.log")):
    print("=" * 70)
    print(f.name)
    print("=" * 70)
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        print("  LASFEL:", e); continue
    hits = [ln.strip() for ln in lines if PATTERNS.search(ln)]
    # Visa de SISTA 30 traffarna (tidssammanfattning ligger i slutet)
    for ln in hits[-30:]:
        print("  " + ln[:160])
    print("")
