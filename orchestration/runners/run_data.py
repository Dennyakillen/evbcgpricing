"""
run_data.py -- Lokala bränsleledet: ett kommando kör regen -> prep -> upload (FD.26, lager 1)
=============================================================================================
Kedjar de tre lokala stegen som producerar och säkrar modellens bränsle, så att en körning
(terminal ELLER "Kör" i VS Code) ersätter att klippa-och-klistra tre separata kommandon:

  1. REGEN   regenerate_transaction_parquet_chunked.py  (DW -> transaction_data.parquet)
  2. PREP    replicate_dataprep.py                       (parquet -> vecko-CSV:er via DuckDB)
  3. UPLOAD  upload_inputs (blob.py)                      (parquet -> Blob 'input'-container)

VARFÖR LOKALT (arkitekturbeslut 2026-06-15, LB.58/65/66)
--------------------------------------------------------
Data prep KÖRS lokalt: datalagret (DW) nås bara via VPN, inte från Azure-VM:en (LB.58), och
DuckDB-prep behöver inte VM:ens RAM (LB.65 -- bara Ray-modellstegen gör det). Men artefakten
(parqueten) laddas upp till Blob FÖR ATT ÖVERLEVA den icke-säkerhetskopierade lokala datorn
(LB.66): kod ligger i Git, stora data-artefakter i Blob. "Kör där du måste, lagra där det överlever."

DATUMKOPPLINGEN (verifierad mot källan 2026-06-15 -- icke-trivial)
-------------------------------------------------------------------
Ett gemensamt --end måste nå de två stegen på OLIKA sätt:
  - REGEN tar --end som FLAGGA (+ --out + --overwrite, se nedan).
  - PREP tar INTE --end. Datumfönstret styrs av miljövariabeln BCG_END_DATE, som
    replicate_dataprep._inject_dates() läser ur os.environ och injicerar i SQL:en in-memory
    (LB.22). Runnern sätter alltså env-varen INNAN den anropar prep.
Att skicka --end till prep vore tyst fel (okänd flagga ignoreras/kraschar). Källa, inte gissning.

PARQUET-NAMNSKARVEN (LB.62-klassen)
-----------------------------------
regen skriver default till transaction_data_GROWING.parquet och vägrar skriva över utan
--overwrite (skyddar den frusna facit-parqueten). Men 00_read.sql läser transaction_data.parquet
(utan _growing). Runnern styr därför regen med explicit --out = <prep-parquet> + --overwrite,
så filen landar direkt där prep läser den. Ingen efterföljande rename behövs.

LAGER (NEXT_SESSION): LAGER 1 = ren orkestrering. LAGER 2 (detta) = statusrapportering för
extraction-fasen till statuskontraktet (run_status.py) + Blob (blob.py), så webappen visar att
bränsleledet kördes. ENDAST extraction-fasen rörs; de andra fem faserna (cluster/site/step5/
step6/build_r12) är egna sessioner och lämnas i sina befintliga tillstånd i statusfilen.

Statusskrivning är BEST-EFFORT (run_site_model.py-mönstret): ett misslyckat write_status får
ALDRIG döda kedjan -- statusen är observation, inte sanningen om jobbet. Allt write_status
wrappas i try/except.

KÖR (global Python 3.11, från repo-roten C:\Projekt\BCG)
--------------------------------------------------------
    py -3.11 orchestration\runners\run_data.py --dry-run          # visa planen, gör inget
    py -3.11 orchestration\runners\run_data.py --skip-regen --skip-prep   # bara upload (snabb, idempotent)
    py -3.11 orchestration\runners\run_data.py --end 2026-04-30   # hela kedjan, växande fönster
    py -3.11 orchestration\runners\run_data.py --skip-regen --skip-prep --run-id 2026-06-15  # bara upload, skriv status

Token: kör `az login --scope https://management.core.windows.net//.default` först (E.3, var 4:e h).

Developer: Jens Palmö (Senior Business Analyst)
Author: Claude advisor, Phase Z session 2026-06-15 (FD.26 lager 1 + lager 2 statusrapportering).
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# --- Path-bootstrap: upload_inputs bor i infrastructure/, run_status i shared/ ---
ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))
os.environ.setdefault("PRICINGMODEL_AUTH", "key")   # ABAC-vägg -> nyckel-läge (dokumenterad skuld, FD.29)

log = logging.getLogger("run_data")

# --- Lager 2: statuskontrakt. Importeras högt men användning är best-effort. ---
from run_status import RunStatus, default_pipeline, window_run_id   # noqa: E402
try:
    from blob import write_status, read_status        # noqa: E402
    _STATUS_AVAILABLE = True
except Exception as _e:                                # azure-libs saknas / import-fel
    _STATUS_AVAILABLE = False
    logging.getLogger("run_data").warning(
        "Statusskrivning otillgänglig (%s) -- kör utan status (lager 1-beteende).", _e)

PHASE_KEY = "extraction"   # den fas run_data ansvarar för (run_status.default_pipeline)

# --- Verifierade sökvägar (ur sessionens källäsning 2026-06-15) ---
BA_VENV_PYTHON = Path(r"C:\Projekt\Business_Analytics\.venv\Scripts\python.exe")  # regen kräver pyodbc
REGEN_SCRIPT   = Path(r"C:\Projekt\Business_Analytics\regenerate_transaction_parquet_chunked.py")
PREP_SCRIPT    = Path(r"C:\Projekt\BCG\tools\replicate_dataprep.py")
PREP_BASE_DIR  = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL")
PARQUET_OUT    = PREP_BASE_DIR / "parquet" / "transaction_data.parquet"   # dit 00_read.sql läser

# Global Python 3.11 för prep (DuckDB) -- 'py -3.11'. För regen används BA-venvens egen python.exe.
PY311 = ["py", "-3.11"]


def _run(cmd: list[str], env: dict | None = None, cwd: str | None = None) -> int:
    """Kör ett delsteg synkront, strömmar output. Returnerar exit-koden.
    Stegen är multi-minuters men SYNKRONA (regen ~chunkar, prep ~11 min, upload ~2 min) --
    ingen detach behövs (mätt: upload 1 GB = 2 min). Ett misslyckat steg stoppar kedjan."""
    log.info("KÖR: %s", " ".join(str(c) for c in cmd))
    t0 = time.time()
    cp = subprocess.run(cmd, env=env, cwd=cwd)
    dt = time.time() - t0
    log.info("KLAR (%.0fs, exit=%d): %s", dt, cp.returncode, cmd[0] if cmd else "?")
    return cp.returncode


# ---------------------------------------------------------------------------
# Lager 2: statusrapportering för extraction-fasen. ALLT best-effort -- en
# misslyckad status-skrivning får aldrig döda kedjan (run_site_model-mönstret).
# ---------------------------------------------------------------------------
def _get_or_create_status(run_id: str) -> "RunStatus | None":
    """Läs befintlig statusfil (gemensam för alla sex faser) eller skapa ny.
    Returnerar None om status är otillgängligt -- då kör vi rent lager 1-beteende."""
    if not _STATUS_AVAILABLE:
        return None
    try:
        return read_status(run_id)
    except Exception:
        log.info("Ingen statusfil för run_id=%s -- skapar ny.", run_id)
        try:
            return default_pipeline(run_id=run_id, triggered_by="jens (run_data)")
        except Exception as e:
            log.warning("Kunde inte skapa status (%s) -- fortsätter utan.", e)
            return None


def _write(rs: "RunStatus | None") -> None:
    """Best-effort write_status. Sväljer alla fel -- status får aldrig döda kedjan."""
    if rs is None or not _STATUS_AVAILABLE:
        return
    try:
        write_status(rs)
    except Exception as e:
        log.warning("Status-skrivning misslyckades (kedjan fortsätter): %s", e)


def _status_start(run_id: str) -> "RunStatus | None":
    """Markera extraction-fasen som startad. ENDAST extraction rörs."""
    rs = _get_or_create_status(run_id)
    if rs is None:
        return None
    try:
        rs.start_phase(PHASE_KEY)
    except Exception as e:
        log.warning("start_phase('%s') misslyckades (%s) -- fortsätter utan status.", PHASE_KEY, e)
        return None
    _write(rs)
    return rs


def _status_finish(rs: "RunStatus | None", ok: bool, note: str,
                   blob_path: str | None = None) -> None:
    """Markera extraction klar/misslyckad. Lägg ev. parquet-blobväg i output_blob_paths."""
    if rs is None:
        return
    try:
        rs.finish_phase(PHASE_KEY, ok=ok, note=note)
        rs.finalize()   # harled run-nivan ur faserna (etappmodellen)
        if blob_path:
            rs.output_blob_paths = sorted(set(rs.output_blob_paths) | {blob_path})
    except Exception as e:
        log.warning("finish_phase misslyckades (%s).", e)
    _write(rs)


def step_regen(end: str) -> int:
    """Steg 1: regenerera parqueten ur DW. BA-venvens python (pyodbc). --out + --overwrite
    styr filen direkt till transaction_data.parquet (LB.62-skarven). VPN måste vara uppe."""
    if not BA_VENV_PYTHON.exists():
        log.error("Saknar BA-venv python: %s", BA_VENV_PYTHON)
        return 2
    if not REGEN_SCRIPT.exists():
        log.error("Saknar regen-skript: %s", REGEN_SCRIPT)
        return 2
    PARQUET_OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(BA_VENV_PYTHON), str(REGEN_SCRIPT),
           "--end", end, "--out", str(PARQUET_OUT), "--overwrite"]
    log.info("REGEN: DW -> %s (kräver VPN till DW; ~chunkad per år)", PARQUET_OUT.name)
    return _run(cmd)


def step_prep(end: str) -> int:
    """Steg 2: DuckDB-data-prep. Datum via env BCG_END_DATE (INTE flagga -- _inject_dates läser
    os.environ). Utelämnar --facit-dir = replicate-only (växande, ingen frozen-validering)."""
    if not PREP_SCRIPT.exists():
        log.error("Saknar prep-skript: %s", PREP_SCRIPT)
        return 2
    if not PARQUET_OUT.exists():
        log.error("Saknar parquet (kör REGEN först eller släpp --skip-regen): %s", PARQUET_OUT)
        return 2
    env = dict(os.environ)
    env["BCG_END_DATE"] = end          # G7-injektion (LB.22) -- prep läser detta, inte en flagga
    cmd = PY311 + [str(PREP_SCRIPT), "--base-dir", str(PREP_BASE_DIR)]
    log.info("PREP: parquet -> vecko-CSV:er (BCG_END_DATE=%s, replicate-only)", end)
    return _run(cmd, env=env)


def step_upload() -> "tuple[int, str | None]":
    """Steg 3: ladda upp parqueten till Blob 'input'-containern (upload_inputs, bevisad).
    Returnerar (exit-kod, blob-väg) -- vägen läggs i statusens output_blob_paths (lager 2)."""
    if not PARQUET_OUT.exists():
        log.error("Saknar parquet att ladda upp: %s", PARQUET_OUT)
        return 2, None
    try:
        from blob import upload_inputs
    except Exception as e:
        log.error("Kunde inte importera upload_inputs (%s: %s). Azure-libs i global 3.11?",
                  type(e).__name__, e)
        return 2, None
    log.info("UPLOAD: %s -> Blob 'input' (~2 min för 1 GB)", PARQUET_OUT.name)
    try:
        paths = upload_inputs([str(PARQUET_OUT)])
    except Exception as e:
        log.error("Uppladdning misslyckades (%s: %s)", type(e).__name__, str(e)[:200])
        if "token" in str(e).lower() or "expired" in str(e).lower():
            log.error("Token död (E.3): az login --scope https://management.core.windows.net//.default")
        return 2, None
    log.info("UPLOAD klar: %s", paths)
    return 0, (paths[0] if paths else None)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lokala bränsleledet: regen -> prep -> upload (FD.26 lager 1).")
    ap.add_argument("--end", default="2026-04-30",
                    help="Växande fönster slutdatum (default 2026-04-30). Når regen som --out-fönster "
                         "och prep som env BCG_END_DATE.")
    ap.add_argument("--skip-regen", action="store_true",
                    help="Hoppa parquet-regenerering (om parqueten redan är aktuell).")
    ap.add_argument("--skip-prep", action="store_true", help="Hoppa DuckDB-data-prep.")
    ap.add_argument("--skip-upload", action="store_true", help="Hoppa Blob-uppladdning.")
    ap.add_argument("--dry-run", action="store_true", help="Visa planen, kör ingenting.")
    ap.add_argument("--run-id", default=None,
                    help="Status-run-id (delas med modell-runnersna). Default: datafonstret "
                         "(window_run_id ur 2022-07-01..--end) sa extraction hamnar i SAMMA "
                         "statusfil som modellfamiljerna for samma period. Ange explicit for overstyrning.")
    ap.add_argument("--no-status", action="store_true",
                    help="Kör utan statusrapportering (rent lager 1-beteende).")
    args = ap.parse_args()
    # Harled fonster-id om --run-id ej angavs. Start = "2022-07-01" (BCG:s frysta
    # startpunkt, = modell-runnrarnas default) sa extraction delar statusfil med
    # modellfamiljerna for samma period. run_data har bara --end. Markt (KARN).
    if args.run_id is None:
        args.run_id = window_run_id("2022-07-01", args.end)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    plan = []
    if not args.skip_regen:  plan.append(f"1. REGEN  (--end {args.end} --out {PARQUET_OUT.name} --overwrite)")
    if not args.skip_prep:   plan.append(f"2. PREP   (BCG_END_DATE={args.end}, replicate-only)")
    if not args.skip_upload: plan.append("3. UPLOAD (parquet -> Blob 'input')")
    if not plan:
        log.warning("Alla steg överhoppade -- inget att göra.")
        return 0

    log.info("PLAN för bränsleledet:")
    for p in plan:
        log.info("   %s", p)

    if args.dry_run:
        log.info("--dry-run: inget kördes.")
        return 0

    # Lager 2: markera extraction-fasen startad (best-effort). --no-status = rent lager 1.
    rs = None if args.no_status else _status_start(args.run_id)

    ran = []          # vilka steg som faktiskt kördes (för status-noten)
    blob_path = None  # parquet-blobväg (länkas i statusens output_blob_paths)

    # Sekventiellt: ett fel stoppar kedjan (nedströms steg beror på uppströms artefakt).
    if not args.skip_regen:
        rc = step_regen(args.end)
        if rc != 0:
            _status_finish(rs, ok=False, note=f"REGEN misslyckades (exit={rc})")
            log.error("REGEN misslyckades (exit=%d) -- stoppar kedjan.", rc); return rc
        ran.append("regen")
    if not args.skip_prep:
        rc = step_prep(args.end)
        if rc != 0:
            _status_finish(rs, ok=False, note=f"PREP misslyckades (exit={rc})")
            log.error("PREP misslyckades (exit=%d) -- stoppar kedjan.", rc); return rc
        ran.append("prep")
    if not args.skip_upload:
        rc, blob_path = step_upload()
        if rc != 0:
            _status_finish(rs, ok=False, note=f"UPLOAD misslyckades (exit={rc})")
            log.error("UPLOAD misslyckades (exit=%d).", rc); return rc
        ran.append("upload")

    size_mb = PARQUET_OUT.stat().st_size / 1_000_000 if PARQUET_OUT.exists() else 0
    note = (f"Bränsleledet kört ({', '.join(ran) or 'inga steg'}); "
            f"parquet {size_mb:.0f} MB, fönster t.o.m. {args.end}")
    _status_finish(rs, ok=True, note=note, blob_path=blob_path)
    log.info("Bränsleledet klart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
