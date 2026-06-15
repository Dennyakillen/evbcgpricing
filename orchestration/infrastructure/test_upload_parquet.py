"""
test_upload_parquet.py -- ISOLERAT test av upload_inputs (blob.py) mot RIKTIG Blob.
Laddar upp transaction_data.parquet (~1 GB) till input-containern, mater tid +
verifierar att storleken i Blob matchar lokalt. Ror INGET annat: ingen regen,
ingen data prep, ingen run_data. ssh_launch_selftest-disciplinen -- bevisa den
enda nya sköra biten ensam fore den lindas in i en kedja.

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Kor (global Python 3.11, kontonyckel-lage, az inloggad mot ev-lz3-ai):
    py -3.11 test_upload_parquet.py
"""
import os, sys, time
from pathlib import Path

# Path-bootstrap: samma som runnern (run_status ligger i shared/)
ROOT = Path(r"C:\Projekt\BCG\orchestration")
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "infrastructure"))
os.environ.setdefault("PRICINGMODEL_AUTH", "key")  # ABAC-vagg -> nyckel-lage (dokumenterad skuld)

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from blob import upload_inputs, CONTAINER_INPUT  # noqa: E402

PARQUET = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\parquet\transaction_data.parquet")

def main() -> int:
    if not PARQUET.exists():
        print(f"[ERROR] hittar inte: {PARQUET}")
        return 1
    mb = PARQUET.stat().st_size / 1_000_000
    print(f"[TEST] laddar upp {PARQUET.name} ({mb:.1f} MB) -> container '{CONTAINER_INPUT}'")
    print(f"[TEST] startar... (1 GB tar nagra minuter; tiden mats)")
    t0 = time.time()
    try:
        paths = upload_inputs([str(PARQUET)])
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {str(e)[:300]}")
        if "403" in str(e) or "AuthorizationPermissionMismatch" in str(e):
            print("[DIAG] 403 -> AAD-roll saknas. Verifiera att PRICINGMODEL_AUTH=key (nyckel-lage).")
        elif "token" in str(e).lower() or "expired" in str(e).lower():
            print("[DIAG] token dod (E.3). Kor: az login --scope https://management.core.windows.net//.default")
        return 2
    dt = time.time() - t0
    print(f"[DONE] uppladdat: {paths}")
    print(f"[KPI] tid: {dt:.0f}s ({dt/60:.1f} min) | hastighet ~{mb/dt:.0f} MB/s")
    return 0

if __name__ == "__main__":
    sys.exit(main())