# =====================================================================
# azure_vm.py -- Z.1 orchestrator-karna for evbcgpricing (Phase Z)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Starta bcg-poc-vm -> git pull senaste koden -> trigga pipelinen som
#   BAKGRUNDSPROCESS (9h-saker, ingen blockerande timeout) -> skriv
#   heartbeat + fasovergangar till statuskontraktet (run_status) i Blob
#   -> deallokera VM nar korningen ar klar.
#
#   Frontytan ror ALDRIG VM:en. Den laser bara statusfilen ur Blob.
#   Detta ar hela poangen: kollega utan VM-access ser status och hamtar
#   output.
#
# ----------------------------------------------------------------------
# !!! OLOST DESIGNFRAGA -- LAS INNAN DU ANVANDER (markeras i koden) !!!
# ----------------------------------------------------------------------
#   Hur startas pipelinens steg 1-6 pa VM:en idag?
#     SCENARIO A: ett enda paraply-script (t.ex. run_pipeline.sh) som
#                 kor hela kedjan. Da racker EN nohup-bakgrundsprocess
#                 och pipelinen sjalv skriver sin fas till statusfilen.
#     SCENARIO B: stegen kors manuellt i sekvens, OCH steg 5 + Step 6 ar
#                 Excel/COM-bundna och kors LOKALT pa Windows (LB.44).
#                 Da kan orchestratorn INTE fyra-och-glomma hela 1-6 som
#                 en VM-process. Den kor steg 1-4 pa VM, satter status
#                 till WAITING (lokalt steg), och de lokala stegen kors
#                 separat pa din Windows-maskin med ett eget wrapper-
#                 script som ocksa uppdaterar statusfilen.
#
#   Funktionen _trigger_pipeline_on_vm() nedan ar STUBBAD tills Jens
#   bekraftat A eller B. Allt ANNAT i denna fil ar komplett och korbart.
#   "Mat, gissa inte" -- vi gjuter inte in VM/lokal-arkitekturen pa en
#   gissning som memory-noterna (LB.44) motsager.
# ----------------------------------------------------------------------
#
# BEROENDEN
#   - Python 3.11
#   - azure-identity, azure-mgmt-compute  (VM-livscykel via SDK)
#       ELLER az CLI via subprocess (fallback -- se KOMMENTAR i koden)
#   - run_status.py  (statuskontraktet -- MASTE ligga bredvid)
#   - blob.py        (Z.2 -- Blob-I/O; stubbad import tills den finns)
#   - paramiko ELLER az vm run-command for SSH-kommandon till VM
#
# DETTA BEROR PA DEN
#   - Flask-frontytan (Z.3) anropar start_run() och laser status via Blob
#
# SUBSCRIPTION-FALLA (LB.46 / MASTER_AZURE 1.2)
#   BCG-VM ligger i ev-lz3-ai (SE) = 42f726f8-91ee-44d4-832f-9d9ec412ef8f.
#   Denna modul satter ALLTID ratt subscription explicit innan VM-anrop.
#
# RISKFLAGGA (Jens infra-confidence)
#   deallocate stoppar compute-debitering (~9 kr/h). Denna modul kor
#   deallocate i en finally-blockerad vag sa att VM:en inte blir kvar
#   och kostar pengar aven om en korning kraschar. Det ar en kraftfull
#   operation -- den ar saker har for att den bara stanger NER, aldrig
#   raderar. Disk/data overlever deallocate.
# =====================================================================

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from run_status import (
    RunStatus, RunState, default_pipeline, utcnow_iso,
)

# blob.py byggs i Z.2. Tills dess: en tydlig stub sa filen importerar rent
# och self-testet kan koras lokalt utan Azure. Ersatts av riktig import.
try:
    from blob import write_status, read_status, upload_outputs  # type: ignore
    _BLOB_AVAILABLE = True
except Exception:  # pragma: no cover
    _BLOB_AVAILABLE = False

    def write_status(rs: "RunStatus") -> None:  # type: ignore
        logging.getLogger("azure_vm").warning(
            "blob.py saknas (Z.2 ej byggd) -- status skrivs EJ till Blob: %s/%s",
            rs.run_id, rs.state.value,
        )

    def read_status(run_id: str):  # type: ignore
        raise RuntimeError("blob.py saknas -- read_status ej tillganglig forran Z.2 byggts.")

    def upload_outputs(run_id: str, local_paths: list[str]) -> list[str]:  # type: ignore
        raise RuntimeError("blob.py saknas -- upload_outputs ej tillganglig forran Z.2 byggts.")


log = logging.getLogger("azure_vm")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# =====================================================================
# Konfiguration -- BCG-specifika fakta (verifierade mot MASTER_AZURE 1.2
# + memory). VM-RG och venv-sokvag ar memory-antaganden; preflight_check
# verifierar VM/RG/SKU mot Azure innan dessa anvands skarpt.
# =====================================================================
@dataclass(frozen=True)
class VmConfig:
    subscription_id: str = "42f726f8-91ee-44d4-832f-9d9ec412ef8f"   # ev-lz3-ai (SE)
    resource_group: str  = "ev-openai-swce-rg-test"
    vm_name: str         = "bcg-poc-vm"
    vm_user: str         = "azureuser"
    vm_private_ip: str   = "172.18.148.4"
    venv_python: str     = "~/bcg/cluster/.venv/bin/python"          # delad venv (Python 3.11.9, Ray 2.41.0)
    repo_dir: str        = "~/bcg"                                   # justera till faktisk repo-rot pa VM
    git_branch: str      = "fas-f-fresh-data"
    heartbeat_seconds: int = 60                                     # hur ofta liv-signal skrivs
    poll_seconds: int      = 120                                    # hur ofta status pollas


# =====================================================================
# Lagsta nivan: kor ett az-CLI-kommando och returnera utdata.
# Vi anvander az CLI via subprocess i stallet for SDK av tva skal:
#   1) Det speglar exakt monstret i MASTER_AZURE (az ...), sa Jens kan
#      kora samma kommandon for hand vid felsokning.
#   2) Inget extra paket-/auth-lager -- az-login ar redan etablerat.
# Vill man senare byta till azure-mgmt-compute ar det en isolerad andring
# har, resten av filen ror inte CLI:t direkt.
# =====================================================================
def _az(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["az"] + args
    log.info("az %s", " ".join(args))
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if check and cp.returncode != 0:
        raise RuntimeError(f"az misslyckades ({cp.returncode}): {cp.stderr.strip()}")
    return cp


def _ensure_subscription(cfg: VmConfig) -> None:
    """Satt ALLTID ratt subscription forst (LB.46). Gissa aldrig pa cachen."""
    _az(["account", "set", "--subscription", cfg.subscription_id])
    cur = _az(["account", "show", "--query", "id", "-o", "tsv"]).stdout.strip()
    if cur != cfg.subscription_id:
        raise RuntimeError(
            f"Aktiv subscription {cur} != forvantad {cfg.subscription_id} (LB.46)."
        )
    log.info("Subscription bekraftad: %s", cfg.subscription_id)


# =====================================================================
# VM-livscykel
# =====================================================================
def start_vm(cfg: VmConfig) -> None:
    _ensure_subscription(cfg)
    log.info("Startar VM %s ...", cfg.vm_name)
    _az(["vm", "start", "--resource-group", cfg.resource_group, "--name", cfg.vm_name])
    log.info("VM startad.")


def deallocate_vm(cfg: VmConfig) -> None:
    """Stoppar compute-debitering. Kors i finally sa VM aldrig blir kvar."""
    log.info("Deallokerar VM %s (stoppar ~9 kr/h) ...", cfg.vm_name)
    _az(["vm", "deallocate", "--resource-group", cfg.resource_group, "--name", cfg.vm_name],
        check=False)  # check=False: misslyckas deallocate vill vi anda inte maskera originalfelet
    log.info("Deallocate-kommando skickat.")


def vm_power_state(cfg: VmConfig) -> str:
    cp = _az(["vm", "get-instance-view", "--resource-group", cfg.resource_group,
              "--name", cfg.vm_name,
              "--query", "instanceView.statuses[?starts_with(code,'PowerState/')].displayStatus",
              "-o", "tsv"], check=False)
    return cp.stdout.strip() or "unknown"


def _ssh(cfg: VmConfig, remote_cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Kor ett kommando pa VM via ssh. OBS: enkla citattecken runt remote_cmd,
    inga inre dubbla -- speglar SSH-quoting-regeln i memory (PS tolkar annars)."""
    ssh_target = f"{cfg.vm_user}@{cfg.vm_private_ip}"
    cmd = ["ssh", ssh_target, remote_cmd]
    log.info("ssh %s: %s", ssh_target, remote_cmd)
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if check and cp.returncode != 0:
        raise RuntimeError(f"ssh misslyckades ({cp.returncode}): {cp.stderr.strip()}")
    return cp


def git_pull_on_vm(cfg: VmConfig) -> str:
    """Hamta senaste koden (vag B: Git = source of truth). Returnerar SHA."""
    _ssh(cfg, f"cd {cfg.repo_dir} && git fetch --all --quiet && "
              f"git checkout {cfg.git_branch} --quiet && git pull --quiet")
    sha = _ssh(cfg, f"cd {cfg.repo_dir} && git rev-parse --short HEAD").stdout.strip()
    log.info("VM star pa commit %s", sha)
    return sha


# =====================================================================
# !!! STUBB -- pipeline-triggning. Fylls i nar Jens bekraftat A eller B.
# =====================================================================
def _trigger_pipeline_on_vm(cfg: VmConfig, run_id: str) -> None:
    """Starta pipelinens VM-steg som BAKGRUNDSPROCESS och slapp direkt.

    --- SCENARIO A (paraply-script finns) -----------------------------
    Da blir kroppen ungefar:
        _ssh(cfg,
            f"cd {cfg.repo_dir} && nohup {cfg.venv_python} run_pipeline.py "
            f"--run-id {run_id} > ~/bcg/logs/{run_id}.log 2>&1 & echo $!")
    Pipelinen sjalv ansvarar for att uppdatera statusfilen per fas
    (importerar run_status, skriver via blob.py pa VM:en).

    --- SCENARIO B (manuell kedja + lokalt Excel-glapp, LB.44) --------
    Da triggar denna funktion ENDAST steg 1-4 pa VM som bakgrundsprocess.
    Nar de ar klara satter orchestratorn status=WAITING (lokalt steg).
    Steg 5 + Step 6 kors av ett separat LOKALT wrapper-script pa Windows
    som ocksa uppdaterar statusfilen via blob.py. Orchestratorn
    deallokerar INTE forran de lokala stegen rapporterat klart -- eller
    sa deallokerar den efter steg 4 (VM behovs ej for Excel-stegen) och
    de lokala stegen kor mot redan nedladdad output. Det valet beror pa
    om VM-output racker lokalt -- en Z.1-detalj att spika med Jens.

    Tills A/B ar bekraftat: hard stopp, sa ingen kor pa en gissning.
    """
    raise NotImplementedError(
        "Pipeline-triggning ej faststalld. Bekrafta SCENARIO A (paraply-script) "
        "eller B (manuell kedja + lokalt Excel-steg, LB.44) innan denna fylls i. "
        "Kor Fraga A/B i sessionen forst -- mat, gissa inte."
    )


def _pipeline_running_on_vm(cfg: VmConfig, run_id: str) -> bool:
    """Stub-kompanjon: avgor om bakgrundsprocessen lever (pgrep mot run_id
    eller statusfilens last_heartbeat). Konkretiseras tillsammans med
    _trigger_pipeline_on_vm nar A/B ar bekraftat."""
    raise NotImplementedError("Konkretiseras med _trigger_pipeline_on_vm (A/B).")


# =====================================================================
# Orchestrering -- KOMPLETT runt stubben. start_run() ar det frontytan
# anropar. Den ar non-blocking i meningen att den startar bakgrunds-
# processen och sedan pollar; men den ar tankt att koras i en egen trad/
# bakgrundsjobb i Flask sa att HTTP-svaret slapper direkt (9h-saker).
# =====================================================================
def start_run(cfg: VmConfig, run_id: str, triggered_by: Optional[str] = None) -> RunStatus:
    """Hela livscykeln. Skriver status till Blob i varje overgang sa
    frontytan (och kollegan) alltid kan polla sanningen ur Blob."""
    rs = default_pipeline(run_id=run_id, triggered_by=triggered_by)
    rs.state = RunState.STARTING
    write_status(rs)

    try:
        start_vm(cfg)
        rs.vm_power_state = vm_power_state(cfg)
        rs.beat(); write_status(rs)

        sha = git_pull_on_vm(cfg)
        rs.git_sha = sha
        rs.beat(); write_status(rs)

        # --- STUBB: startar pipeline-bakgrundsprocess (A/B ej bekraftat) ---
        _trigger_pipeline_on_vm(cfg, run_id)

        # Pollnings-loop. Pipelinen (eller lokala wrappern) skriver fas-
        # overgangar till statusfilen; har laser vi tillbaka och uppdaterar
        # heartbeat sa frontytan ser liv aven mellan fasbyten.
        while True:
            time.sleep(cfg.poll_seconds)
            current = read_status(run_id)         # sanning ur Blob
            if current.state in (RunState.SUCCEEDED, RunState.FAILED):
                rs = current
                break
            current.beat()
            write_status(current)

        if rs.state == RunState.SUCCEEDED:
            log.info("Korning %s klar. Output: %s", run_id, rs.output_blob_paths)

    except NotImplementedError:
        # Stubben slog till -- forvanta detta tills A/B bekraftats.
        log.error("Pipeline-triggning ej implementerad (A/B ej bekraftat).")
        rs.fail("Pipeline-triggning ej faststalld -- bekrafta SCENARIO A/B.")
        write_status(rs)
    except Exception as e:
        log.exception("Korning %s misslyckades.", run_id)
        rs.fail(str(e))
        write_status(rs)
    finally:
        # Stoppa compute-debitering oavsett utfall. Detta ar den kraftfulla
        # men sakra operationen -- stanger ner, raderar inte.
        try:
            deallocate_vm(cfg)
            rs.vm_power_state = "deallocated"
            write_status(rs)
        except Exception:
            log.exception("Deallocate misslyckades -- KONTROLLERA VM MANUELLT (kostar ~9 kr/h).")

    return rs


if __name__ == "__main__":
    # Self-test utan Azure: bygg status, visa att stubben failar tydligt,
    # och att finally-vagen kors. Ingen VM ror, inget az-anrop -- vi
    # monkeypatchar de externa anropen sa logiken kan verifieras lokalt.
    import types

    cfg = VmConfig()

    # Patcha bort allt som kraver Azure/VM for sjalvtestet.
    g = globals()
    g["start_vm"]        = lambda c: log.info("[test] start_vm hoppad")
    g["deallocate_vm"]   = lambda c: log.info("[test] deallocate_vm hoppad")
    g["vm_power_state"]  = lambda c: "running"
    g["git_pull_on_vm"]  = lambda c: "testsha"

    rs = start_run(cfg, run_id="2026-06-12T-selftest", triggered_by="selftest")
    assert rs.state == RunState.FAILED, "Stubben ska ge FAILED tills A/B bekraftats"
    assert "SCENARIO" in (rs.error or ""), "Felmeddelandet ska peka pa A/B-beslutet"
    print("OK: orchestrering kor runt stubben; deallocate-vag (finally) trafffad; "
          "stubben failar tydligt i avvaktan pa A/B.")
