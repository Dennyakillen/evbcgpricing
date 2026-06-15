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

LAGER (NEXT_SESSION): detta är LAGER 1 -- ren orkestrering, INGEN statusrapportering.
Statuskontrakt-skrivning (extraction-fasen i run_status.py) är lager 2, byggs separat när
lager 1 är bevisat. Håll lagren isär (en ny rörlig del i taget).

KÖR (global Python 3.11, från repo-roten C:\Projekt\BCG)
--------------------------------------------------------
    py -3.11 orchestration\runners\run_data.py --dry-run          # visa planen, gör inget
    py -3.11 orchestration\runners\run_data.py --skip-regen --skip-prep   # bara upload (snabb, idempotent)
    py -3.11 orchestration\runners\run_data.py --end 2026-04-30   # hela kedjan, växande fönster

Token: kör `az login --scope https://management.core.windows.net//.default` först (E.3, var 4:e h).

Developer: Jens Palmö (Senior Business Analyst)
Author: Claude advisor, Phase Z session 2026-06-15 (FD.26 lager 1).
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


def step_upload() -> int:
    """Steg 3: ladda upp parqueten till Blob 'input'-containern (upload_inputs, bevisad).
    Importeras sent så att --dry-run / --skip-upload inte kräver azure-libs."""
    if not PARQUET_OUT.exists():
        log.error("Saknar parquet att ladda upp: %s", PARQUET_OUT)
        return 2
    try:
        from blob import upload_inputs
    except Exception as e:
        log.error("Kunde inte importera upload_inputs (%s: %s). Azure-libs i global 3.11?",
                  type(e).__name__, e)
        return 2
    log.info("UPLOAD: %s -> Blob 'input' (~2 min för 1 GB)", PARQUET_OUT.name)
    try:
        paths = upload_inputs([str(PARQUET_OUT)])
    except Exception as e:
        log.error("Uppladdning misslyckades (%s: %s)", type(e).__name__, str(e)[:200])
        if "token" in str(e).lower() or "expired" in str(e).lower():
            log.error("Token död (E.3): az login --scope https://management.core.windows.net//.default")
        return 2
    log.info("UPLOAD klar: %s", paths)
    return 0


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
    args = ap.parse_args()

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

    # Sekventiellt: ett fel stoppar kedjan (nedströms steg beror på uppströms artefakt).
    if not args.skip_regen:
        rc = step_regen(args.end)
        if rc != 0:
            log.error("REGEN misslyckades (exit=%d) -- stoppar kedjan.", rc); return rc
    if not args.skip_prep:
        rc = step_prep(args.end)
        if rc != 0:
            log.error("PREP misslyckades (exit=%d) -- stoppar kedjan.", rc); return rc
    if not args.skip_upload:
        rc = step_upload()
        if rc != 0:
            log.error("UPLOAD misslyckades (exit=%d).", rc); return rc

    log.info("Bränsleledet klart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
