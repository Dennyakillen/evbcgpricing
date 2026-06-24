#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fix_cluster_maj_status.py -- engangsrattning: stang cluster_model-fasen arligt
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.
#
# VARFOR: cluster-maj kordes klart pa VM 2026-06-24 (steg 1-4, modeller byggda,
#   output hamtad), MEN runnern avbrots med Ctrl+C mitt i per-fil-scp (encoding-
#   bugg pa svenska filnamn + 4181 individuella overforinngar = orimligt langt;
#   vi hamtade i stallet allt via tar). Eftersom runnern aldrig nadde finalize
#   star statusfilen kvar med cluster_model=running. Dessutom bar filen STALE
#   falt fran tidigare: topp-state=running med finished_at=2026-06-23 (igar
#   kvalls preflight-fel), hint="Technical failure before VM run started",
#   triggered_by="jens (run_site_model)". Appen visar darfor cluster som evigt
#   running med fel hint -- inte betryggande for det korda fonstret.
#
#   Detta ar finalize-spoket (FD.30) forvarrat av vart medvetna avbrott. Den
#   RIKTIGA finalize-arkitekturen ar Leverans 2 -- denna fil ar pragmatisk
#   rattning sa appen visar SANT for cluster-fonstret nu, inte en omskrivning
#   av finalize.
#
# RATIONALITY (matt 2026-06-24, run_all_rationality + receipts):
#   PASS 2 (per_cluster, top_leverage), REVIEW 7, FAIL 0.
#   Distribution PASS: 78.3% negativa (IB.9 ref 76.5%), median -0.2221,
#   significance 33.7%, NaN 0%. Population KONSEKVENT 3791 (finalized_x=3791,
#   output_summary=3791 -- inget tyst bortfall, matt). REVIEW = vantad facit-
#   vs-vaxande-drift (Spearman 0.69, driven av kanda extrema KEY t.ex.
#   Clinics-SBBS1681 -733 som aven facit hade). Step 6 fallback stadar bruset.
#
# GOR:
#   1. backup av statusfilen till Blob (som fix_maj_timing)
#   2. cluster_model: state=succeeded, finished_at = started_at + 696s
#      (note "Finished model.py in 11 min 36.8 sec" = 696.8s, VM-rapporterad),
#      arlig note med rationality-utfall.
#   3. rensa STALE topp-falt: hint=None, error=None, finished_at=None
#      (lat finalize() haärleda topp-state av faserna).
#   4. finalize() -> topp-state blir det faserna implicerar (bundle m.fl.
#      pending -> run forblir waiting/running, INTE succeeded -- pipelinen
#      har mer kvar).
#   5. R7: las tillbaka, verifiera cluster_model=succeeded.
#
# KOR (global py -3.11, ratt konto, token fornyad):
#   $env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
#   py -3.11 tools\fix_cluster_maj_status.py            # dry-run
#   py -3.11 tools\fix_cluster_maj_status.py --apply
# ---------------------------------------------------------------------
import sys, os, argparse, datetime
from pathlib import Path

sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")

from run_status import PhaseState  # noqa: E402
from blob import read_status, write_status, _client, CONTAINER_STATUS  # noqa: E402

RUN_ID = "2022-07-01_2026-05-31"
# VM-rapporterad modeltid fran cluster_model-fasens note: "Finished model.py in
# 11 min 36.8 sec". Men det ar BARA model.py-steget. Vi har ingen full 1-4-summa
# (loggen lag pa VM, ej hamtad). Konservativt: satt finished_at = started_at +
# observerad korytid fran tee-loggen: launch 08:52:23 -> benign step5 09:39:08
# = 2805 s wall (steg 1-4 + step5-forsok). Vi anvander den faktiska wall-tiden.
WALL_SECONDS = 2805   # 08:52:23 -> 09:39:08 (launch -> benign-step5), tee-logg
FMT = "%Y-%m-%dT%H:%M:%SZ"
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

NOTE = ("3791 KEY (vaxande maj-data). Rationality REVIEW=vantad facit-drift "
        "(Spearman 0.69, kanda extrema KEY), distribution PASS (78% neg, "
        "median -0.22, sig 34%), inga FAIL. Pop konsekvent 3791 (ingen tyst "
        "forlust). Step6 fallback stadar brus. Validerad 2026-06-24.")


def main():
    ap = argparse.ArgumentParser(description="Stang cluster_model-fasen arligt (succeeded + rationality-note).")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: dry-run).")
    args = ap.parse_args()

    print("=" * 70)
    print("FIX CLUSTER MAJ STATUS -- cluster_model -> succeeded (arlig REVIEW-note)")
    print("=" * 70)

    rs = read_status(RUN_ID)
    cl = next((p for p in rs.phases if p.key == "cluster_model"), None)
    if cl is None:
        print("  [STOPP] cluster_model-fas saknas"); return

    print(f"  FORE:")
    print(f"    cluster_model.state    = {cl.state.value}")
    print(f"    cluster_model.started  = {cl.started_at}")
    print(f"    cluster_model.finished = {cl.finished_at}")
    print(f"    cluster_model.note     = {cl.note}")
    print(f"    topp.state             = {rs.state.value}")
    print(f"    topp.hint              = {getattr(rs, 'hint', None)}")
    print(f"    topp.error             = {getattr(rs, 'error', None)}")
    print(f"    topp.finished_at       = {getattr(rs, 'finished_at', None)}")

    if not cl.started_at:
        print("  [STOPP] cluster_model.started_at saknas -- kan ej rakna finished_at."); return

    t0 = datetime.datetime.strptime(cl.started_at, FMT)
    new_finished = (t0 + datetime.timedelta(seconds=WALL_SECONDS)).strftime(FMT)

    print(f"\n  EFTER (planerat):")
    print(f"    cluster_model.state    = succeeded")
    print(f"    cluster_model.finished = {new_finished}  (+{WALL_SECONDS}s wall)")
    print(f"    cluster_model.note     = {NOTE[:60]}...")
    print(f"    topp.hint              = None (rensas)")
    print(f"    topp.error             = None (rensas)")
    print(f"    topp.finished_at       = None (rensas, finalize haärleder topp-state)")

    if not args.apply:
        print("\n  (dry-run -- kor med --apply)")
        print("=" * 70); return

    # --- backup (som fix_maj_timing) ---
    bdir = Path(__file__).resolve().parent / f"status_backup_{STAMP}"
    bdir.mkdir(parents=True, exist_ok=True)
    c = _client().get_container_client(CONTAINER_STATUS)
    raw = c.get_blob_client(f"{RUN_ID}.json").download_blob().readall()
    (bdir / f"{RUN_ID}.json").write_bytes(raw)
    print(f"\n  [backup] {bdir}")

    # --- rattning ---
    cl.state = PhaseState.SUCCEEDED
    cl.finished_at = new_finished
    cl.note = NOTE
    # rensa stale topp-falt sa de inte forvillar appen / finalize
    if hasattr(rs, "hint"):
        rs.hint = None
    if hasattr(rs, "error"):
        rs.error = None
    if hasattr(rs, "finished_at"):
        rs.finished_at = None
    rs.finalize()
    write_status(rs)
    print("  skrivet.")

    # --- R7 ---
    rs2 = read_status(RUN_ID)
    c2 = next(p for p in rs2.phases if p.key == "cluster_model")
    print(f"\n  R7:")
    print(f"    cluster_model.state = {c2.state.value}  (ska vara succeeded)")
    print(f"    cluster_model.dur   = {c2.duration_human} ({c2.duration_seconds} s)")
    print(f"    topp.state          = {rs2.state.value}  (bundle m.fl. pending -> ej succeeded)")
    print(f"    topp.hint           = {getattr(rs2, 'hint', None)}  (ska vara None)")
    ok = (c2.state.value == "succeeded")
    print("\n  VERDICT: " + ("RATT -- cluster_model succeeded, appen visar sant."
                             if ok else "GRANSKA -- ovantat utfall, se backup."))
    print("=" * 70)


if __name__ == "__main__":
    main()
