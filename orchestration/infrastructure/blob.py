# =====================================================================
# blob.py -- Blob-lager for Phase Z (evbcgpricing pricingmodel)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Limmar ihop statuskontraktet (run_status.py) med Azure Blob Storage.
#   Implementerar exakt de tre funktioner azure_vm.py importerar:
#     write_status(rs)            -> skriver statusfil till 'runstatus'
#     read_status(run_id)         -> laser tillbaka (sanning ur Blob)
#     upload_outputs(run_id, ...) -> laddar upp resultatfiler till 'output'
#
#   Statusfilen i Blob ar SANNINGEN om "lever korningen?". Den overlever
#   att VM:en deallokeras och kan lasas av en kollega UTAN VM-access.
#   SSE i frontytan (senare) ar bara kosmetik ovanpa denna fil.
#
# AUTENTISERING -- den viktiga designen
#   Vi anvander DefaultAzureCredential. Den provar i tur och ordning:
#     1. Miljovariabler / Managed Identity (nar koden kor i Azure)
#     2. Azure CLI-inloggning (din 'az login' nar du kor lokalt)
#   Resultat: EXAKT SAMMA KOD kor som DIG pa din laptop under utveckling,
#   och som MI:n nar den flyttar till en Azure-resurs. Ingen kodandring
#   vid skiftet. Det ar sa "overlever att du slutar" byggs i praktiken.
#
#   Lokalt kraver det att DITT konto har Storage Blob Data-roll pa
#   kontot (du visade dig ha data-plane-access som Owner i Z.0). I
#   molnet kraver det att MI:n har Storage Blob Data Contributor (Z.2).
#
# BEROENDEN
#   pip install azure-storage-blob azure-identity
#   run_status.py (maste ligga bredvid)
#
# DETTA BEROR PA DEN
#   azure_vm.py (importerar write_status/read_status/upload_outputs)
#   ev. framtida Flask-frontyta (laser status for visning)
#
# KONFIG
#   Storage-konto och containernamn ar Z.0-fakta. ENDA stallet de
#   definieras pa Python-sidan -- andra har om de byter.
# =====================================================================

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

from run_status import RunStatus

log = logging.getLogger("blob")

# --- Z.0-fakta. Overridebara via miljovariabler for test/flexibilitet. ---
STORAGE_ACCOUNT   = os.environ.get("PRICINGMODEL_STORAGE", "evbcgpricinginput")
CONTAINER_STATUS  = os.environ.get("PRICINGMODEL_STATUS_CONTAINER", "runstatus")
CONTAINER_OUTPUT  = os.environ.get("PRICINGMODEL_OUTPUT_CONTAINER", "output")
CONTAINER_INPUT   = os.environ.get("PRICINGMODEL_INPUT_CONTAINER", "input")

_ACCOUNT_URL = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"

# Autentiseringslage. Tva vagar, vald via miljovariabel PRICINGMODEL_AUTH:
#   "aad"  (default) -> DefaultAzureCredential. MI i molnet, din az-login
#          lokalt. FRAMTIDSVAGEN. Kraver Storage Blob Data-roll (ABAC-vagg
#          nekar dig den lokalt idag -- darfor finns vag tva).
#   "key"  -> kontonyckel, last vid korning via 'az storage account keys
#          list' (du far lasa den som control-plane-Owner). Lever bara i
#          processminnet, hardkodas aldrig. LOKAL FALLBACK inom din
#          behorighet, kringgar ABAC utan IT.
# Byt tillbaka till "aad" (eller ta bort variabeln) den dag du har AAD-
# datarollen -- ingen kodandring kravs, kontonyckel-vagen slocknar da.
_AUTH_MODE = os.environ.get("PRICINGMODEL_AUTH", "aad").lower()

RESOURCE_GROUP = os.environ.get("PRICINGMODEL_RG", "ev-openai-swce-rg-test")
SUBSCRIPTION   = os.environ.get("PRICINGMODEL_SUBSCRIPTION", "ev-lz3-ai (SE)")


# ---------------------------------------------------------------------
# Klient-fabrik. Lazy: skapas vid forsta anrop, inte vid import, sa att
# import inte kraver Azure-uppkoppling. Auth-vag styrs av _AUTH_MODE.
# ---------------------------------------------------------------------
_service_client: Optional[BlobServiceClient] = None


def _read_account_key() -> str:
    """Las kontonyckeln vid korning via az CLI. Du far lasa den som
    control-plane-Owner. Nyckeln returneras till processminnet -- den
    skrivs aldrig till disk eller logg. Kraver giltig az-login mot ratt
    subscription (LB.46).

    Windows-not: 'az' ar 'az.cmd' pa Windows och hittas INTE av subprocess
    med en argumentlista (WinError 2). Vi anvander shell=True sa att az
    hittas via PATH precis som i en terminal. shell=True ar harmlost har
    eftersom inga argument kommer fran ostrukturerad anvandarinput -- bara
    vara egna konstanter (storage-konto, RG, subscription)."""
    import subprocess

    def _run(cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Satt ratt subscription forst (LB.46-fallan). Citera subscription-namnet
    # eftersom det innehaller mellanslag och parenteser.
    _run(f'az account set --subscription "{SUBSCRIPTION}"')
    cp = _run(
        f'az storage account keys list '
        f'--account-name {STORAGE_ACCOUNT} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--query "[0].value" -o tsv'
    )
    if cp.returncode != 0 or not cp.stdout.strip():
        raise RuntimeError(
            "Kunde inte lasa kontonyckeln via az. Ar du inloggad och pa ratt "
            f"subscription ({SUBSCRIPTION})? Fel: {cp.stderr.strip()}"
        )
    return cp.stdout.strip()


def _client() -> BlobServiceClient:
    global _service_client
    if _service_client is None:
        if _AUTH_MODE == "key":
            log.info("Skapar BlobServiceClient mot %s (kontonyckel-lage)", _ACCOUNT_URL)
            key = _read_account_key()
            _service_client = BlobServiceClient(account_url=_ACCOUNT_URL, credential=key)
        else:
            log.info("Skapar BlobServiceClient mot %s (DefaultAzureCredential)", _ACCOUNT_URL)
            cred = DefaultAzureCredential()
            _service_client = BlobServiceClient(account_url=_ACCOUNT_URL, credential=cred)
    return _service_client


def _status_blob_name(run_id: str) -> str:
    """En statusfil per run_id. Plant namnschema -- latt att lista/hitta."""
    return f"{run_id}.json"


# ---------------------------------------------------------------------
# De tre funktioner azure_vm.py importerar.
# ---------------------------------------------------------------------
def write_status(rs: RunStatus) -> None:
    """Skriv statusfilen till 'runstatus'-containern. Overwrite: senaste
    skrivningen vinner (statusfilen ar en levande ogonblicksbild, inte
    en logg -- historik ligger i phases[] inuti filen)."""
    blob = _client().get_blob_client(
        container=CONTAINER_STATUS, blob=_status_blob_name(rs.run_id)
    )
    data = rs.to_json().encode("utf-8")
    blob.upload_blob(data, overwrite=True)
    log.info("Status skriven: %s/%s (state=%s)",
             CONTAINER_STATUS, _status_blob_name(rs.run_id), rs.state.value)


def read_status(run_id: str) -> RunStatus:
    """Las tillbaka statusfilen. Kastar ResourceNotFoundError om run_id
    inte finns -- anroparen far avgora om det betyder 'ej startad an'."""
    blob = _client().get_blob_client(
        container=CONTAINER_STATUS, blob=_status_blob_name(run_id)
    )
    try:
        data = blob.download_blob().readall().decode("utf-8")
    except ResourceNotFoundError:
        log.warning("Ingen statusfil for run_id=%s", run_id)
        raise
    return RunStatus.from_json(data)


def upload_outputs(run_id: str, local_paths: list[str]) -> list[str]:
    """Ladda upp resultatfiler till 'output'-containern under run_id/.
    Returnerar blob-sokvagarna (laggs i statusfilens output_blob_paths
    sa kollegan vet var resultatet finns)."""
    uploaded: list[str] = []
    for p in local_paths:
        path = Path(p)
        if not path.exists():
            log.warning("Hoppar over saknad fil: %s", p)
            continue
        blob_name = f"{run_id}/{path.name}"
        blob = _client().get_blob_client(container=CONTAINER_OUTPUT, blob=blob_name)
        with path.open("rb") as fh:
            blob.upload_blob(fh, overwrite=True)
        uploaded.append(f"{CONTAINER_OUTPUT}/{blob_name}")
        log.info("Output uppladdad: %s", blob_name)
    return uploaded


def upload_inputs(local_paths: list[str]) -> list[str]:
    """Ladda upp INPUT-filer (t.ex. transaction_data.parquet) till 'input'-
    containern. Platt namn (ingen datummapp): input ar den AKTUELLA bransle-
    filen, inte en daterad korningsartefakt -- overwrite=True, senaste vinner.
    Speglar hur transaction_data.parquet fungerar lokalt: en fil som skrivs
    over nar en ny vaxande version produceras, inte versionerad.

    LB.39: loggar uppladdad storlek per fil sa tyst forlust/avbrott syns.
    Stor fil (~1 GB parquet) -> SDK:n chunkar sjalv (max_concurrency); over-
    write kravs for att ersatta foregaende bransle. Returnerar blob-sokvagar."""
    uploaded: list[str] = []
    for p in local_paths:
        path = Path(p)
        if not path.exists():
            log.warning("Hoppar over saknad input-fil: %s", p)
            continue
        blob_name = path.name
        blob = _client().get_blob_client(container=CONTAINER_INPUT, blob=blob_name)
        size_mb = path.stat().st_size / 1_000_000
        log.info("Laddar upp input %s (%.1f MB) -> %s/%s ...",
                 path.name, size_mb, CONTAINER_INPUT, blob_name)
        with path.open("rb") as fh:
            blob.upload_blob(fh, overwrite=True, max_concurrency=4)
        props = blob.get_blob_properties()
        up_mb = props.size / 1_000_000
        ok = (props.size == path.stat().st_size)
        log.info("Input uppladdad: %s (%.1f MB i Blob, %s)",
                 blob_name, up_mb, "storlek matchar" if ok else "STORLEK SKILJER")
        uploaded.append(f"{CONTAINER_INPUT}/{blob_name}")
    return uploaded

# ==========================================================================
# TILLAGG till orchestration/infrastructure/blob.py
# Klistras in EFTER upload_inputs() (ca rad 218), FORE list_runs().
# Steg A (FD.37 / overlevnadstes): lokalt program hamtar Azures utfall +
# frusna facit-lager FRAN BLOB sa Efter-steget kor pa Blob, inte lokala filer.
# ==========================================================================

CONTAINER_PIPELINE = os.environ.get("PRICINGMODEL_PIPELINE_CONTAINER", "pipeline")

# download_outputs v2 (FD.37 / overlevnadstes): destinationerna = run_step6:s
# KALLOR (PLACEMENTS src + ALREADY path), inte dess placerings-mal -- sa Step 6
# laser Blob-hamtad data, inte lokala arkiv. Inkl. tx-CSV for build_r12.
# Verifierat 2026-06-22: Blob-cluster-filen har ra KEY (osplittad) = run_step6:s
# input, sa skrivning till kallplatsen ger ingen dubbel KEY-split.
_AFTER_INPUTS = [
    {"label": "cluster output_summary (LIVE)", "container": "output",
     "blob": "{date}/cluster/model/output_summary.xlsx",
     "dest": r"Pipeline\\02. Elasticity\\2. Product Cluster Level Models\\_archive_growing_2026-04-27_v2_pg4fix\\output_summary.xlsx"},
    {"label": "site output_summary (LIVE)", "container": "output",
     "blob": "{date}/output_summary.xlsx",
     "dest": r"Pipeline\\02. Elasticity\\3. Product Site Level Models\\output\\model\\output_summary.xlsx"},
    {"label": "cluster-steg5 (FROZEN FD.15)", "container": "pipeline",
     "blob": "00_frozen_facit/cluster_step5/final_model_cluster_granularity_Ivce.xlsx",
     "dest": r"Pipeline\\02. Elasticity\\6. Fall Back Logic\\input_data\\final_model_cluster_granularity_Ivce.xlsx"},
    {"label": "bundle (FROZEN FD.11)", "container": "pipeline",
     "blob": "00_frozen_facit/bundle/output_summary.xlsx",
     "dest": r"Pipeline\\02. Elasticity\\6. Fall Back Logic\\input_data\\output_summary_bundle.xlsx"},
    {"label": "vav-vikter (FROZEN FD.14)", "container": "pipeline",
     "blob": "00_frozen_facit/weave_weights/Complete_Product_Data.xlsx",
     "dest": r"Pipeline\\02. Elasticity\\6. Fall Back Logic\\input_data\\Complete_Product_Data.xlsx"},
    {"label": "tx-CSV (build_r12)", "container": "pipeline",
     "blob": "00_frozen_facit/tx/Sweden_weekly_model_data_site_level.csv",
     "dest": r"Pipeline\\01. Data Prep\\output\\Sweden_weekly_model_data_site_level_growing.csv"},
]


def download_outputs(date_folder: str, repo_root: str) -> dict:
    """Steg A v2 (overlevnadstes): hamta Efter-kedjans inputs FRAN BLOB till
    run_step6:s KALLOR + build_r12:s tx-plats, sa hela Efter-steget laser Blob
    -- inte lokala arkiv/OneDrive. Datorn blir umbarlig.

    LIVE (cluster+site) ur output/<date_folder>/, FROZEN (FD.11/14/15) + tx ur
    pipeline/. Returnerar {placed, missing}. Saknad blob loggas + 'missing'."""
    from pathlib import Path as _Path
    root = _Path(repo_root)
    placed, missing = [], []
    svc = _client()
    for item in _AFTER_INPUTS:
        blob_name = item["blob"].format(date=date_folder)
        dest = root / item["dest"]
        bc = svc.get_container_client(item["container"]).get_blob_client(blob_name)
        try:
            if not bc.exists():
                log.warning("PULL %s: blob saknas (%s/%s).", item["label"], item["container"], blob_name)
                missing.append(item["label"]); continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(bc.download_blob().readall())
            log.info("PULL %s: %s/%s -> %s (%.2f MB)", item["label"], item["container"],
                     blob_name, dest.name, dest.stat().st_size/1e6)
            placed.append(str(dest))
        except Exception as e:
            log.warning("PULL %s: fel (%s).", item["label"], e); missing.append(item["label"])
    log.info("PULL klar: %d placerade, %d saknade.", len(placed), len(missing))
    return {"placed": placed, "missing": missing}


def list_runs(prefix: str = "") -> list[str]:
    """Lista run_id:n som har en statusfil. For en framtida frontyta som
    vill visa korhistorik. Bekvamlighetsfunktion, ej kritisk."""
    container = _client().get_container_client(CONTAINER_STATUS)
    names = [b.name for b in container.list_blobs(name_starts_with=prefix)]
    return [n[:-5] for n in names if n.endswith(".json")]


# ---------------------------------------------------------------------
# Self-test: kor 'python blob.py' for ett round-trip mot RIKTIG Blob.
# Detta KRAVER att du ar inloggad (az login) och har Storage Blob Data-
# roll pa kontot. Det skriver en testfil med run_id 'selftest-<host>',
# laser tillbaka, och raderar den. Sakert: ror bara sin egen testblob.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import socket
    from run_status import default_pipeline

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    run_id = f"selftest-{socket.gethostname()}"
    print(f"Self-test mot {_ACCOUNT_URL} (container '{CONTAINER_STATUS}'), run_id={run_id}")
    print(f"Auth-lage: {_AUTH_MODE}  (satt PRICINGMODEL_AUTH=key for kontonyckel-fallback)")

    rs = default_pipeline(run_id=run_id, triggered_by="blob-selftest")
    rs.start_phase("step1_dataprep")
    rs.finish_phase("step1_dataprep", ok=True, note="self-test")

    try:
        write_status(rs)
        print("  write_status OK")
        back = read_status(run_id)
        assert back.run_id == run_id
        assert back.phases[1].note == "self-test"
        print("  read_status OK -- round-trip konsekvent")

        # Stada upp testbloben.
        _client().get_blob_client(
            container=CONTAINER_STATUS, blob=_status_blob_name(run_id)
        ).delete_blob()
        print("  testblob raderad")
        print("\nOK: blob.py fungerar mot riktig Blob. Datastig verifierad.")
    except Exception as e:
        msg = str(e)
        print(f"\nFAIL: {type(e).__name__}: {msg[:200]}")
        if "AuthorizationPermissionMismatch" in msg or "403" in msg:
            print("  Diagnos: 403 -- du autentiserade men saknar Storage Blob Data-roll (AAD).")
            print("  Detta ar ABAC-vaggen. Losning: kor med kontonyckel-lage i stallet:")
            print("    $env:PRICINGMODEL_AUTH = 'key'; py -3.11 blob.py")
        elif "token" in msg.lower() or "401" in msg:
            print("  Diagnos: auth/token. Logga in: az login --scope https://storage.azure.com/.default")
        else:
            print("  Diagnos: ovrigt fel -- las meddelandet ovan.")
        raise
