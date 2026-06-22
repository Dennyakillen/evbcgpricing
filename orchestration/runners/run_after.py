"""
run_after.py  --  "Efter -- resultat och affarssignal": lokal orkestrator
=========================================================================
Paketerar de steg som maste koras UTANFOR Azure (xlwings/COM finns ej pa
Linux, LB.44) och laddar upp utfallet till Blob sa allt sparas pa samma
stalle som motorns output. Speglar run_data.py (Fore-fasen) i anda: tunn
runner som orkestrerar BEFINTLIGA, beprovade steg + rapporterar status.

Kedjan (harledd ur sond 6 after_chain_probe -- noll gissning)
-------------------------------------------------------------
  (valfri) PULL  -- hamta motorns LIVE-output (cluster+site output_summary)
                    fran Blob -> run_step6:s lokala destinationer. AV som
                    default: pa samma maskin som korde motorn finns kallorna
                    redan lokalt (matt 2026-06-22). --pull for cross-maskin.
  STEP 6         -- subprocess verify_tool/run/run_step6.py (placerar lokala
                    kallor + frysta lager, vaver F1-F7, verifierar R7,
                    tolererar LB.53-mallfelet). -> Final_Fallback_Data_*.xlsx
  STEP 7         -- subprocess verify_tool/run/build_r12_for_model.py
                    (auto-hittar senaste Final_Fallback_Data + tx via
                    TX_CANDIDATES). -> Model_Feed_*.xlsx
  PUSH           -- ladda upp Final_Fallback_Data + Model_Feed till Blob
                    (samma datummapp). Status: step6 + build_r12 -> grona,
                    finalize() -> fonstret blir "alla sju grona" -> SUCCEEDED.

VIKTIGT -- de tre frusna lasen (FD.11 bundle, FD.14 vav-vikter, FD.15
cluster-steg5) bars av utfallet. Provenance-kvittot marker det REVIEW med
flit. Denna runner RAPPORTERAR det (sista loggraderna), doljer det ej -- en
elasticitet ur denna vav ar farsk i karnsignalen men frusen i tre uppstroms-
lager. (Spegel av LB.77: avsiktlig avvikelse marks pa platsen.)

Status (best-effort, run_data-monstret): ett misslyckat write_status far
ALDRIG doda kedjan. run_after AGER tva faser: step6 + build_r12. Den laser
in motorns BEFINTLIGA statusfil (samma fonster-run_id) och uppdaterar den --
sa Fore+Motor+Efter hamnar i EN statusfil per datafonster.

Usage
-----
    cd "C:\\Projekt\\BCG"
    py -3.11 orchestration\\runners\\run_after.py
    py -3.11 orchestration\\runners\\run_after.py --dry-run
    py -3.11 orchestration\\runners\\run_after.py --pull --date-folder 2026-06-17
    py -3.11 orchestration\\runners\\run_after.py --tx "<sokvag till growing-csv>"

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Author: Claude advisor, 2026-06-22 (FD.37).
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
FBL = REPO / "Pipeline" / "02. Elasticity" / "6. Fall Back Logic"
MODEL_FEED_DIR = REPO / "output_model_feed"

# Bootstrap orchestration-moduler (samma monster som run_data).
sys.path.insert(0, str(REPO / "orchestration" / "shared"))
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))

from run_status import RunStatus, default_pipeline, window_run_id   # noqa: E402
from blob import write_status, read_status, upload_outputs          # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_after")

# run_after AGER dessa tva faser i default_pipeline (matt mot run_status.py).
PHASES_OWNED = ["step6", "build_r12"]

# Frusna las att RAPPORTERA (ej dolja) -- LB.77 / FD.11/14/15.
FROZEN_LOCKS = [
    "FD.11 bundle-gren (Step6-vav)",
    "FD.14 vav-vikter (df_all_product)",
    "FD.15 cluster-steg5-routning (blended_output)",
]


# --------------------------------------------------------------------------
# Status -- best-effort (run_data-monstret: status far aldrig doda kedjan)
# --------------------------------------------------------------------------
def _load_status(run_id: str) -> "RunStatus | None":
    """Las motorns BEFINTLIGA statusfil for fonstret om den finns, annars ny.
    run_after UPPDATERAR den -- skriver inte over Fore+Motor-faserna."""
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


def _persist(rs: "RunStatus | None") -> None:
    if rs is None:
        return
    try:
        rs.beat()
        write_status(rs)
    except Exception as e:
        log.warning("write_status misslyckades (%s) -- status ar observation, fortsatter.", e)


def _phase_start(rs: "RunStatus | None", key: str) -> None:
    if rs is None:
        return
    try:
        rs.start_phase(key)
        _persist(rs)
    except Exception as e:
        log.warning("start_phase('%s') misslyckades (%s) -- fortsatter utan status.", key, e)


def _phase_finish(rs: "RunStatus | None", key: str, ok: bool, note: str) -> None:
    if rs is None:
        return
    try:
        rs.finish_phase(key, ok=ok, note=note)
        rs.finalize()   # harled run-nivan ur faserna (etappmodellen)
        _persist(rs)
    except Exception as e:
        log.warning("finish_phase('%s') misslyckades (%s).", key, e)


# --------------------------------------------------------------------------
# Steg
# --------------------------------------------------------------------------
def _run_subprocess(script: Path, extra_args: "list[str]", cwd: "Path | None" = None) -> int:
    if not script.exists():
        log.error("Skript saknas: %s", script)
        return 1
    cmd = [sys.executable, str(script)] + extra_args
    log.info("Kor: %s", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return proc.returncode


def _newest(glob_pat: str, *roots: Path) -> "Path | None":
    cands = []
    for r in roots:
        cands += list(r.glob(glob_pat))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Efter-kedjan: Step 6 + R12 + push till Blob (FD.37).")
    ap.add_argument("--run-id", default=None,
                    help="Fonster-id for status. Default: datafonstret (window_run_id ur --start/--end).")
    ap.add_argument("--start", default="2022-07-01", help="Fonstrets start (BCG:s frysta startpunkt).")
    ap.add_argument("--end", default="2026-04-30", help="Fonstrets slut (vaxande).")
    ap.add_argument("--pull", action="store_true",
                    help="Hamta motorns output fran Blob fore Step 6 (cross-maskin). "
                         "AV som default -- kallorna finns lokalt pa korningsmaskinen.")
    ap.add_argument("--date-folder", default=None,
                    help="Blob-datummapp att PULL:a fran (t.ex. 2026-06-17). Kravs med --pull.")
    ap.add_argument("--tx", default=None, help="Transaktions-CSV for R12 (annars auto via TX_CANDIDATES).")
    ap.add_argument("--no-push", action="store_true", help="Hoppa over Blob-upload av resultatet.")
    ap.add_argument("--dry-run", action="store_true", help="Visa plan, kor inget.")
    args = ap.parse_args()

    if args.run_id is None:
        args.run_id = window_run_id(args.start, args.end)

    print("=" * 70)
    print("EFTER -- resultat och affarssignal (FD.37)")
    print(f"Fonster (run_id): {args.run_id}")
    print("Step 6 (fallback-vav) -> Step 7 (R12 model feed) -> push + status")
    print("Frusna las som bars av utfallet (RAPPORTERAS, ej dolda):")
    for lock in FROZEN_LOCKS:
        print(f"  - {lock}")
    print("=" * 70)

    if args.dry_run:
        print("DRY-RUN -- plan:")
        if args.pull:
            print(f"  PULL fran Blob-mapp '{args.date_folder or '(senaste)'}' -> lokala destinationer")
        else:
            print("  PULL: AV (lokala kallor anvands)")
        print(f"  STEP 6: subprocess {RUN_STEP6.name} (cwd-styrt internt)")
        print(f"  STEP 7: subprocess {BUILD_R12.name} {'--tx '+args.tx if args.tx else '(auto-tx)'}")
        print(f"  PUSH:   {'AV' if args.no_push else 'Final_Fallback_Data + Model_Feed -> Blob'}")
        print("  STATUS: step6 + build_r12 -> grona, finalize()")
        return 0

    rs = _load_status(args.run_id)

    # --- (valfri) PULL ---
    if args.pull:
        if not args.date_folder:
            log.error("--pull kraver --date-folder (vilken Blob-korning som ska vavas).")
            return 2
        try:
            from blob import download_outputs
            placed = download_outputs(args.date_folder, str(REPO))
            log.info("PULL klar: %d filer placerade.", len(placed))
        except ImportError:
            log.error("download_outputs saknas i blob.py -- bygg den (FD.37) eller kor utan --pull.")
            return 2

    # --- STEP 6 ---
    _phase_start(rs, "step6")
    rc = _run_subprocess(RUN_STEP6, [])   # run_step6 chdir:ar sjalv till FBL
    if rc != 0:
        _phase_finish(rs, "step6", ok=False, note=f"run_step6 exit={rc}")
        log.error("Step 6 misslyckades (exit=%d). Avbryter fore R12.", rc)
        return rc
    fallback = _newest("Final_Fallback_Data*.xlsx", FBL / "output_data", FBL)
    note6 = f"Final_Fallback_Data producerad: {fallback.name}" if fallback else "OK (fil ej hittad for verifiering)"
    _phase_finish(rs, "step6", ok=True, note=note6)
    log.info("STEP 6 OK. %s", note6)

    # --- STEP 7 (build_r12) ---
    _phase_start(rs, "build_r12")
    r12_args = ["--tx", args.tx] if args.tx else []
    r12_args += ["--end", args.end[:7]]   # build_r12 --end vill YYYY-MM
    rc = _run_subprocess(BUILD_R12, r12_args)
    if rc != 0:
        _phase_finish(rs, "build_r12", ok=False, note=f"build_r12 exit={rc}")
        log.error("Step 7 (R12) misslyckades (exit=%d).", rc)
        return rc
    model_feed = _newest("Model_Feed_*.xlsx", MODEL_FEED_DIR)
    note7 = f"Model_Feed producerad: {model_feed.name}" if model_feed else "OK (fil ej hittad for verifiering)"
    _phase_finish(rs, "build_r12", ok=True, note=note7)
    log.info("STEP 7 OK. %s", note7)

    # --- PUSH (resultatet till Blob) ---
    if not args.no_push:
        date_folder = args.date_folder or datetime.now().strftime("%Y-%m-%d")
        to_push = [str(p) for p in (fallback, model_feed) if p is not None]
        if to_push:
            try:
                paths = upload_outputs(date_folder, to_push)
                if rs is not None:
                    rs.output_blob_paths = sorted(set(rs.output_blob_paths) | set(paths))
                    _persist(rs)
                log.info("PUSH klar: %d filer -> Blob %s/", len(paths), date_folder)
            except Exception as e:
                log.warning("PUSH misslyckades (%s) -- resultatet finns lokalt.", e)
        else:
            log.warning("Inget att pusha (varken Final_Fallback eller Model_Feed hittad).")

    # --- Slutrapport: frusna las (LB.77 -- dolj ej) ---
    print("\n" + "=" * 70)
    print("EFTER KLAR. Utfallet ar FARSKT i karnsignalen men bar tre FRUSNA lager:")
    for lock in FROZEN_LOCKS:
        print(f"  REVIEW: {lock}")
    print("Se provenance-kvittot (verify_tool/provenance) for full harkomst.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
