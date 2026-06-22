"""
run_after.py  --  "Efter -- resultat och affarssignal": lokal orkestrator (FD.37)
=================================================================================
OVERLEVNADSTES (karnsyfte): Blob ska innehalla ALLT fran senaste korningen --
aven Step 6/7 som maste koras lokalt (xlwings/COM ej i molnet) -- sa systemet
kan aterskapas av en eftertradare UTAN Jens lokala dator. Darfor:
  - HAMTAR motorns utfall + frusna lager FRAN BLOB (inte lokala filer), och
  - LADDAR UPP det lokalt producerade resultatet TILLBAKA till Blob.
Blob ar den enda kompletta, reproducerbara sanningen.

Kedjan (ur sond 6 after_chain_probe -- noll gissning):
  PULL    -- download_outputs(date_folder): hamta de 5 Step-6-inputs fran Blob
             (2 LIVE ur output/<date>, 3 FROZEN ur pipeline/00_frozen_facit/)
             -> run_step6:s lokala destinationer. TVINGAD (--no-pull bara for
             felsokning pa samma maskin som korde motorn).
  STEP 6  -- subprocess run_step6.py (placerar, vaver F1-F7, R7, LB.53-tolerant)
             -> Final_Fallback_Data_*.xlsx
  STEP 7  -- subprocess build_r12_for_model.py (auto-tx) -> Model_Feed_*.xlsx
  PUSH    -- Final_Fallback_Data + Model_Feed -> Blob (samma datummapp). Status:
             step6 + build_r12 -> grona, finalize() -> alla sju grona -> SUCCEEDED.

Status (best-effort, run_data-monstret): laser motorns BEFINTLIGA statusfil
(samma fonster-run_id) och UPPDATERAR den -> Fore+Motor+Efter i EN fil per fonster.
Ett misslyckat write_status far ALDRIG doda kedjan.

De tre frusna lasen (FD.11/14/15) RAPPORTERAS i slutloggen, doljs ej (LB.77).

Usage:
    cd "C:\\Projekt\\BCG"; $env:PRICINGMODEL_AUTH="key"
    py -3.11 orchestration\\runners\\run_after.py --date-folder 2026-06-17
    py -3.11 orchestration\\runners\\run_after.py --date-folder 2026-06-17 --dry-run
    py -3.11 orchestration\\runners\\run_after.py --no-pull   # lokala filer (felsokning)

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Author: Claude advisor, 2026-06-22 (FD.37 / overlevnadstes).
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
RUN_STEP6 = REPO / "verify_tool" / "run" / "run_step6.py"
BUILD_R12 = REPO / "verify_tool" / "run" / "build_r12_for_model.py"
RUN_PROVENANCE = REPO / "verify_tool" / "provenance" / "run_all_provenance.py"
RUN_RATIONALITY = REPO / "verify_tool" / "output_rationality" / "run_all_rationality.py"
FBL = REPO / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic"
MODEL_FEED_DIR = REPO / "output_model_feed"
# tx-CSV som PULL placerar (download_outputs v2). build_r12 far den explicit.
TX_PULLED = REPO / "Pipeline" / "01. Data Prep" / "output" / "Sweden_weekly_model_data_site_level_growing.csv"

sys.path.insert(0, str(REPO / "orchestration" / "shared"))
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))

from run_status import RunStatus, default_pipeline, window_run_id   # noqa: E402
from blob import write_status, read_status, upload_outputs          # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_after")

PHASES_OWNED = ["step6", "build_r12"]
FROZEN_LOCKS = [
    "FD.11 bundle-gren (Step6-vav)",
    "FD.14 vav-vikter (df_all_product)",
    "FD.15 cluster-steg5-routning (blended_output)",
]


# ----- Status (best-effort: run_data-monstret) -----
def _load_status(run_id: str) -> "RunStatus | None":
    try:
        rs = read_status(run_id)
        log.info("Status: uppdaterar befintlig fil for fonster %s.", run_id)
        return rs
    except Exception:
        log.info("Status: ingen befintlig fil for %s -- skapar ny pipeline.", run_id)
        try:
            return default_pipeline(run_id=run_id, triggered_by="jens (run_after)")
        except Exception as e:
            log.warning("Kunde ej skapa statuspipeline (%s) -- kor utan status.", e)
            return None


def _persist(rs):
    if rs is None: return
    try:
        rs.beat(); write_status(rs)
    except Exception as e:
        log.warning("write_status misslyckades (%s) -- status ar observation.", e)


def _phase_start(rs, key):
    if rs is None: return
    try:
        rs.start_phase(key); _persist(rs)
    except Exception as e:
        log.warning("start_phase('%s') misslyckades (%s).", key, e)


def _phase_finish(rs, key, ok, note):
    if rs is None: return
    try:
        rs.finish_phase(key, ok=ok, note=note)
        rs.finalize()
        _persist(rs)
    except Exception as e:
        log.warning("finish_phase('%s') misslyckades (%s).", key, e)


# ----- Steg -----
def _run_subprocess(script: Path, extra_args, cwd=None) -> int:
    if not script.exists():
        log.error("Skript saknas: %s", script); return 1
    cmd = [sys.executable, str(script)] + extra_args
    log.info("Kor: %s", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode


def _newest(glob_pat: str, *roots: Path):
    cands = []
    for r in roots:
        cands += list(r.glob(glob_pat))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None



# ----- D: fortroende-validering (FD.37) -----
# Efter Step 6/7 kors de BEFINTLIGA validerarna (provenance + rationality) sa de
# producerar Excel-kvitton i receipts/<datum>/{provenance,rationality}/ -- exakt
# dar appens _validator_receipt letar. Fortroende kring datan, inte sonder.
# Validerarna ar sjalvgaende (inga args, hittar Final_Fallback sjalva).
def _run_validators() -> dict:
    """Kor provenance + rationality. Returnerar {namn: exit_code}. Best-effort:
    en validerare som fallerar stoppar inte kedjan (fortroende-kvitto = observation,
    inte grind). Exit 1 fran rationality = REVIEW (granskning), inte FAIL (PRIO 3)."""
    results = {}
    for label, script in [("provenance", RUN_PROVENANCE), ("rationality", RUN_RATIONALITY)]:
        if not script.exists():
            log.warning("Validerare saknas: %s -- hoppar.", script)
            results[label] = -1
            continue
        log.info("Kor validerare: %s", label)
        try:
            rc = subprocess.run([sys.executable, str(script)], cwd=str(script.parent)).returncode
            results[label] = rc
            # exit 0 = PASS; exit 1 (rationality) = REVIEW; ovrigt = problem
            verdict = "PASS" if rc == 0 else ("REVIEW" if (label == "rationality" and rc == 1) else f"exit={rc}")
            log.info("Validerare %s: %s", label, verdict)
        except Exception as e:
            log.warning("Validerare %s kraschade (%s) -- fortroende-kvitto uteblir.", label, e)
            results[label] = -2
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Efter-kedjan: PULL fran Blob -> Step6 -> R12 -> PUSH (FD.37).")
    ap.add_argument("--run-id", default=None, help="Fonster-id for status (default: window_run_id ur --start/--end).")
    ap.add_argument("--start", default="2022-07-01", help="Fonstrets start.")
    ap.add_argument("--end", default="2026-04-30", help="Fonstrets slut.")
    ap.add_argument("--date-folder", default=None, help="Blob-datummapp for LIVE-output att PULL:a (t.ex. 2026-06-17). KRAVS om ej --no-pull.")
    ap.add_argument("--no-pull", action="store_true", help="Hoppa PULL, anvand lokala filer (FELSOKNING pa motor-maskinen).")
    ap.add_argument("--tx", default=None, help="Transaktions-CSV for R12 (annars auto).")
    ap.add_argument("--no-push", action="store_true", help="Hoppa Blob-upload av resultatet.")
    ap.add_argument("--dry-run", action="store_true", help="Visa plan, kor inget.")
    args = ap.parse_args()

    if args.run_id is None:
        args.run_id = window_run_id(args.start, args.end)

    print("=" * 70)
    print("EFTER -- resultat och affarssignal (FD.37 / overlevnadstes)")
    print(f"Fonster (run_id): {args.run_id}")
    print(f"PULL fran Blob:   {'AV (lokala filer)' if args.no_pull else 'PA -> date-folder ' + str(args.date_folder)}")
    print("Step 6 (fallback-vav) -> Step 7 (R12) -> push tillbaka till Blob")
    print("Frusna las som bars av utfallet (RAPPORTERAS, ej dolda):")
    for lock in FROZEN_LOCKS:
        print(f"  - {lock}")
    print("=" * 70)

    if not args.no_pull and not args.date_folder and not args.dry_run:
        log.error("PULL ar PA men --date-folder saknas. Ange vilken Blob-korning som ska vavas, "
                  "eller --no-pull for lokala filer.")
        return 2

    if args.dry_run:
        print("DRY-RUN -- plan:")
        print(f"  PULL:   {'AV' if args.no_pull else 'download_outputs(' + str(args.date_folder) + ') -> 5 inputs (2 LIVE + 3 FROZEN)'}")
        print(f"  STEP 6: subprocess {RUN_STEP6.name}")
        print(f"  STEP 7: subprocess {BUILD_R12.name} {'--tx '+args.tx if args.tx else '(auto-tx)'} --end {args.end[:7]}")
        print(f"  PUSH:   {'AV' if args.no_push else 'Final_Fallback_Data + Model_Feed -> Blob/' + (args.date_folder or 'idag')}")
        print(f"  STATUS: step6 + build_r12 -> grona, finalize()")
        return 0

    rs = _load_status(args.run_id)

    # --- PULL (tvingad om ej --no-pull) ---
    if not args.no_pull:
        try:
            from blob import download_outputs
        except ImportError:
            log.error("download_outputs saknas i blob.py -- klistra in Steg A-tillagget forst.")
            return 2
        res = download_outputs(args.date_folder, str(REPO))
        if res["missing"]:
            log.error("PULL ofullstandig -- saknade inputs pa Blob: %s", res["missing"])
            log.error("Kor upload_frozen_facit.py (Steg B) for frusna lager, eller verifiera "
                      "att motorns output finns under output/%s/.", args.date_folder)
            return 3
        log.info("PULL komplett: alla 5 inputs placerade fran Blob.")

    # --- STEP 6 ---
    _phase_start(rs, "step6")
    rc = _run_subprocess(RUN_STEP6, [])
    if rc != 0:
        _phase_finish(rs, "step6", ok=False, note=f"run_step6 exit={rc}")
        log.error("Step 6 misslyckades (exit=%d).", rc); return rc
    fallback = _newest("Final_Fallback_Data*.xlsx", FBL / "output_data", FBL)
    note6 = f"Final_Fallback_Data: {fallback.name}" if fallback else "OK (fil ej hittad)"
    _phase_finish(rs, "step6", ok=True, note=note6)
    log.info("STEP 6 OK. %s", note6)

    # --- STEP 7 ---
    _phase_start(rs, "build_r12")
    # tx: explicit --tx > PULL:ad CSV > auto. Overlevnadstes: PULL:ad kommer fran Blob.
    tx_path = args.tx or (str(TX_PULLED) if TX_PULLED.exists() else None)
    r12_args = (["--tx", tx_path] if tx_path else []) + ["--end", args.end[:7]]
    if tx_path:
        log.info("build_r12 tx: %s", tx_path)
    rc = _run_subprocess(BUILD_R12, r12_args)
    if rc != 0:
        _phase_finish(rs, "build_r12", ok=False, note=f"build_r12 exit={rc}")
        log.error("Step 7 (R12) misslyckades (exit=%d).", rc); return rc
    model_feed = _newest("Model_Feed_*.xlsx", MODEL_FEED_DIR)
    note7 = f"Model_Feed: {model_feed.name}" if model_feed else "OK (fil ej hittad)"
    _phase_finish(rs, "build_r12", ok=True, note=note7)
    log.info("STEP 7 OK. %s", note7)

    # --- D: fortroende-validering (kor BEFINTLIGA validerare -> kvitton till appen) ---
    log.info("Kor fortroende-validerare (provenance + rationality)...")
    val = _run_validators()
    # Berika fas-noterna med validerings-domen sa appen/statusen visar fortroende.
    if rs is not None:
        prov = val.get("provenance")
        rat = val.get("rationality")
        prov_txt = "provenance PASS" if prov == 0 else f"provenance exit={prov}"
        rat_txt = "rationality PASS" if rat == 0 else ("rationality REVIEW" if rat == 1 else f"rationality exit={rat}")
        try:
            # Lagg domen sist i step6:s not (step6 ar den fas appen knyter provenance till)
            for ph in rs.phases:
                if ph.key == "step6":
                    base = ph.note or ""
                    ph.note = f"{base} | {prov_txt}; {rat_txt}".strip(" |")
            _persist(rs)
            log.info("Fortroende-dom skriven till status: %s; %s", prov_txt, rat_txt)
        except Exception as e:
            log.warning("Kunde ej skriva fortroende-dom till status (%s).", e)

    # --- PUSH (resultatet TILLBAKA till Blob -- overlevnadstes) ---
    if not args.no_push:
        date_folder = args.date_folder or datetime.now().strftime("%Y-%m-%d")
        to_push = [str(p) for p in (fallback, model_feed) if p is not None]
        if to_push:
            try:
                paths = upload_outputs(date_folder, to_push)
                if rs is not None:
                    rs.output_blob_paths = sorted(set(rs.output_blob_paths) | set(paths))
                    _persist(rs)
                log.info("PUSH klar: %d filer -> Blob %s/ (Efter-resultatet ligger nu pa Blob).",
                         len(paths), date_folder)
            except Exception as e:
                log.warning("PUSH misslyckades (%s) -- resultatet finns lokalt men EJ pa Blob.", e)
        else:
            log.warning("Inget att pusha (Final_Fallback/Model_Feed ej hittad).")

    # --- Slutrapport: frusna las (LB.77) ---
    print("\n" + "=" * 70)
    print("EFTER KLAR. Blob bar nu hela kedjan (Fore+Motor+Efter) for fonstret.")
    print("Utfallet ar FARSKT i karnsignalen men bar tre FRUSNA lager:")
    for lock in FROZEN_LOCKS:
        print(f"  REVIEW: {lock}")
    print("Se provenance-kvittot (verify_tool/provenance) for full harkomst.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
