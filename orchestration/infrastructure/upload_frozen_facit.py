"""
upload_frozen_facit.py -- Steg 1 av FD.28 blob-struktur (Jens Palmö)

Skapar containern 'pipeline' i TEST-kontot (evbcgpricinginput) och laddar upp
det frysta BCG-facit per familj till 00_frozen_facit/. Detta är nollpunkten som
allt växande jämförs mot -- och som idag bara lever på Jens lokala maskin (LB.66).

KÖRS LOKALT (PowerShell):
    cd C:/Projekt/BCG
    py -3.11 orchestration/infrastructure/upload_frozen_facit.py

KRÄVER: az login giltig (storage-scope), Owner på test-RG (key-läge läser nyckeln).
AUTH: key-läge (kringgår ABAC-väggen). Ingen Kent behövs. Rör INTE blob.py:s kod
-- pekar om via env-vars som blob.py redan respekterar.

IDEMPOTENT: kan köras om; överskriver befintliga blobbar, skapar inte dubbletter.
"""
import os
import sys
from pathlib import Path

# --- Peka blob.py mot TEST-kontot i key-läge (env-vars, ingen kodändring) ---
os.environ["PRICINGMODEL_STORAGE"] = "evbcgpricinginput"
os.environ["PRICINGMODEL_RG"]      = "ev-openai-swce-rg-test"
os.environ["PRICINGMODEL_AUTH"]    = "key"

# Importera blob.py:s byggstenar (nyckel-läsning, konto-URL).
# blob.py importerar run_status, så den modulens mapp måste på sökvägen.
# Vi GISSAR inte var den ligger -- vi SÖKER upp den under orchestration/ och
# lägger dess mapp på path. Robust oavsett katalogstruktur (mät, gissa inte).
_HERE = Path(__file__).parent                 # orchestration/infrastructure
_ORCH = _HERE.parent                           # orchestration
sys.path.insert(0, str(_HERE))                 # för blob.py självt

_run_status_hits = list(_ORCH.rglob("run_status.py"))
if _run_status_hits:
    for hit in _run_status_hits:
        sys.path.insert(0, str(hit.parent))
    print(f"  [path] run_status hittad: {_run_status_hits[0].parent}")
else:
    print("  [VARNING] run_status.py hittades inte under orchestration/ -- "
          "blob-import kan misslyckas.")

import blob  # noqa: E402
from azure.storage.blob import BlobServiceClient  # noqa: E402

CONTAINER = "pipeline"

# --- Fryst BCG-facit per familj (entydigt: output\model\output_summary.xlsx) ---
# Källa: OneDrive BCG-original. Detta är nollpunkten, validerad bit-för-bit.
_BCG = Path(r"C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB"
            r"\Datastrategi\BCG\BCG_orginal_V2_New\02. Elasticity")

FROZEN_FACIT = {
    "cluster": _BCG / "2. Product Cluster Level Models" / "output" / "model" / "output_summary.xlsx",
    "site":    _BCG / "3. Product Site Level Models"    / "output" / "model" / "output_summary.xlsx",
    "bundle":  _BCG / "5. Bundle Clinic Models"         / "output" / "model" / "output_summary.xlsx",
}


def _client() -> BlobServiceClient:
    """Bygg klient i key-läge (samma nyckel-läsning som blob.py)."""
    key = blob._read_account_key()
    return BlobServiceClient(account_url=blob._ACCOUNT_URL, credential=key)


def main() -> int:
    print("=" * 64)
    print("FD.28 STEG 1 -- Fryst BCG-facit -> Blob (test-konto, key-läge)")
    print("=" * 64)
    print(f"  Konto:     {blob.STORAGE_ACCOUNT}")
    print(f"  Container: {CONTAINER}")
    print(f"  Auth:      {blob._AUTH_MODE}")
    print("-" * 64)

    svc = _client()

    # Skapa container (idempotent -- hoppar om den finns)
    try:
        svc.create_container(CONTAINER)
        print(f"  [SKAPAD] container '{CONTAINER}'")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e) or "exists" in str(e).lower():
            print(f"  [FINNS]  container '{CONTAINER}' (ok, idempotent)")
        else:
            print(f"  [FEL] kunde inte skapa container: {e}")
            return 1

    cc = svc.get_container_client(CONTAINER)

    # Ladda upp facit per familj med storlekskvitto (LB.39)
    print("-" * 64)
    ok, fail = 0, 0
    for family, local_path in FROZEN_FACIT.items():
        blob_name = f"00_frozen_facit/{family}/output_summary.xlsx"
        if not local_path.exists():
            print(f"  [SAKNAS] {family}: {local_path}")
            fail += 1
            continue
        size_mb = local_path.stat().st_size / (1024 * 1024)
        try:
            with open(local_path, "rb") as fh:
                cc.upload_blob(name=blob_name, data=fh, overwrite=True)
            # Verifiera uppladdad storlek (tyst förlust ska synas)
            props = cc.get_blob_client(blob_name).get_blob_properties()
            up_mb = props.size / (1024 * 1024)
            match = "OK" if abs(up_mb - size_mb) < 0.01 else "STORLEK SKILJER!"
            print(f"  [UPP] {family:8s} {size_mb:6.2f} MB -> {blob_name}  ({match})")
            ok += 1
        except Exception as e:
            print(f"  [FEL] {family}: {e}")
            fail += 1

    print("-" * 64)
    print(f"  KLART: {ok} uppladdade, {fail} fel/saknade")
    print("=" * 64)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
