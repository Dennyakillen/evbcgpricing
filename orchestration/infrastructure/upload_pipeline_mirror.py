"""
upload_pipeline_mirror.py -- Steg 2 av FD.28 (Jens Palmö)

Speglar den LOKALA pipeline-strukturen till Blob (test-konto, key-läge).
Allt facit, all växande output och alla valideringar finns redan klart lokalt
end-to-end -- detta skript kopierar dem rakt av. Ingen gissning om "vilken fil
som gäller": skriptet UPPTÄCKER vad som finns och rapporterar det. Du ser i
utskriften exakt vad som speglades.

Speglar per familj till prefix som matchar BCG-strukturen:
    02_cluster/  03_site/  04_bundle/  05_step6/
Hoppar BRUS (ren resurs): _archive*, _backup*, .pre*, _Ivce*, _run_logs, .venv.

KÖRS LOKALT (PowerShell), efter upload_frozen_facit.py (steg 1):
    cd C:/Projekt/BCG
    py -3.11 orchestration/infrastructure/upload_pipeline_mirror.py
    # Torrkörning (visar vad som SKULLE laddas upp, rör inte Blob):
    py -3.11 orchestration/infrastructure/upload_pipeline_mirror.py --dry-run

AUTH: key-läge mot test-konto (ingen Kent). IDEMPOTENT (overwrite=True).
"""
import os
import sys
from pathlib import Path

os.environ["PRICINGMODEL_STORAGE"] = "evbcgpricinginput"
os.environ["PRICINGMODEL_RG"]      = "ev-openai-swce-rg-test"
os.environ["PRICINGMODEL_AUTH"]    = "key"

_HERE = Path(__file__).parent
_ORCH = _HERE.parent
sys.path.insert(0, str(_HERE))
_rs = list(_ORCH.rglob("run_status.py"))
if _rs:
    sys.path.insert(0, str(_rs[0].parent))
import blob  # noqa: E402
from azure.storage.blob import BlobServiceClient  # noqa: E402

CONTAINER = "pipeline"
DRY = "--dry-run" in sys.argv

# Lokal pipeline-rot
_PIPE = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity")

# Familj -> (lokal mapp, blob-prefix). Speglar BCG-numreringen.
FAMILIES = {
    "cluster": (_PIPE / "2. Product Cluster Level Models", "02_cluster"),
    "site":    (_PIPE / "3. Product Site Level Models",    "03_site"),
    "bundle":  (_PIPE / "5. Bundle Clinic Models",         "04_bundle"),
    "step6":   (_PIPE / "6. Fall Back Logic",              "05_step6"),
}

# Mappar/mönster som är BRUS (sidoutveckling) -- speglas INTE (ren resurs).
SKIP_DIR_PREFIX = ("_archive", "_backup", "_run_logs", ".venv", "__pycache__", ".git")
SKIP_FILE_SUBSTR = (".pre_", "_Ivce", "~$")

# Filtyper värda att spegla (output + data, inte kod/skräp)
KEEP_EXT = (".xlsx", ".csv", ".parquet")


def _skip_dir(name: str) -> bool:
    return any(name.startswith(p) for p in SKIP_DIR_PREFIX)


def _skip_file(name: str) -> bool:
    return any(s in name for s in SKIP_FILE_SUBSTR) or not name.lower().endswith(KEEP_EXT)


def _client() -> BlobServiceClient:
    key = blob._read_account_key()
    return BlobServiceClient(account_url=blob._ACCOUNT_URL, credential=key)


def _walk_clean(root: Path):
    """Ge (lokal fil, relativ sökväg) för rena filer under root, hoppa brus-mappar."""
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # Beskär skräp-mappar in-place så os.walk inte går ner i dem
        dirnames[:] = [d for d in dirnames if not _skip_dir(d)]
        for fn in filenames:
            if _skip_file(fn):
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root)
            yield full, rel


def main() -> int:
    print("=" * 64)
    print(f"FD.28 STEG 2 -- Spegla lokal pipeline -> Blob {'(TORRKÖRNING)' if DRY else ''}")
    print("=" * 64)
    print(f"  Konto: {blob.STORAGE_ACCOUNT} · Container: {CONTAINER} · Auth: {blob._AUTH_MODE}")

    cc = None
    if not DRY:
        svc = _client()
        try:
            svc.create_container(CONTAINER)
        except Exception:
            pass
        cc = svc.get_container_client(CONTAINER)

    total_ok, total_skip_fam, total_mb = 0, 0, 0.0
    for family, (local_dir, prefix) in FAMILIES.items():
        print("-" * 64)
        if not local_dir.exists():
            print(f"  [SAKNAS] {family}: {local_dir} (familjen ej körd lokalt?)")
            total_skip_fam += 1
            continue
        files = list(_walk_clean(local_dir))
        if not files:
            print(f"  [TOM] {family}: inga rena filer (bara brus/kod?)")
            continue
        print(f"  {family} -> {prefix}/  ({len(files)} filer)")
        for full, rel in files:
            blob_name = f"{prefix}/{str(rel).replace(os.sep, '/')}"
            mb = full.stat().st_size / (1024 * 1024)
            total_mb += mb
            if DRY:
                print(f"    [skulle UPP] {mb:7.2f} MB  {blob_name}")
                total_ok += 1
                continue
            try:
                with open(full, "rb") as fh:
                    cc.upload_blob(name=blob_name, data=fh, overwrite=True)
                up = cc.get_blob_client(blob_name).get_blob_properties().size / (1024 * 1024)
                tag = "OK" if abs(up - mb) < 0.01 else "STORLEK SKILJER!"
                print(f"    [UPP] {mb:7.2f} MB  {blob_name}  ({tag})")
                total_ok += 1
            except Exception as e:
                print(f"    [FEL] {blob_name}: {e}")

    print("=" * 64)
    verb = "skulle laddas upp" if DRY else "uppladdade"
    print(f"  KLART: {total_ok} filer {verb}, {total_mb:.1f} MB totalt, "
          f"{total_skip_fam} familjer saknades")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
