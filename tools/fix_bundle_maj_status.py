#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fix_bundle_maj_status.py -- engangsrattning: stang bundle_model-fasen arligt
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.
# Speglar fix_cluster_maj_status.py (samma blob-kontrakt, backup, R7).
#
# VARFOR: bundle-maj kordes klart pa VM 2026-06-24 (125 KEY, output_summary
#   hamtad 16:09). Men runnern avbrots/token-fel i flera iterationer, sa
#   statusfilens bundle_model-fas star ej succeeded. Detta satter den ratt.
#
# BEVIS (matt 2026-06-24, akta maj-korning):
#   - data_for_model nadde maj (2026-05-25) efter G7-patch (LB.78)
#   - feature_selection korde full automl (~1h) efter automl-mapp-fix (LB.79)
#   - output_summary: 125 KEY, SUM_visits=41291 (maj) vs 32854 (april) = OLIKA
#     -> akta maj-data, ej aterbruk (oberoende bevis mot input-summa)
#   - rationality: PASS 3, REVIEW 4, FAIL 0 (REVIEW = vantad facit-drift, IB.6/IB.11)
#   - elasticitet 85% neg, median -0.213 (FAS 18-ref: 86%, -0.21)
#
# KOR (global py -3.11, ratt konto, token fornyad):
#   $env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
#   py -3.11 tools\fix_bundle_maj_status.py            # dry-run
#   py -3.11 tools\fix_bundle_maj_status.py --apply
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
PHASE_KEY = "bundle_model"
FMT = "%Y-%m-%dT%H:%M:%SZ"
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

NOTE = ("125 KEY (vaxande maj-data). Rationality REVIEW=vantad facit-drift "
        "(85% neg, median -0.213), distribution PASS, inga FAIL. Maj bevisad: "
        "SUM_visits 41291 vs april 32854 (oberoende). G7-patch + automl-mapp-fix "
        "kravdes (LB.78/79). Step6 fallback stadar brus. Validerad 2026-06-24.")


def main():
    ap = argparse.ArgumentParser(description="Stang bundle_model-fasen arligt (succeeded + maj-note).")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: dry-run).")
    ap.add_argument("--finished", default=None,
                    help="finished_at ISO (default: nu, eftersom korytid spann over flera iterationer).")
    args = ap.parse_args()

    print("=" * 70)
    print("FIX BUNDLE MAJ STATUS -- bundle_model -> succeeded (arlig maj-note)")
    print("=" * 70)

    rs = read_status(RUN_ID)
    ph = next((p for p in rs.phases if p.key == PHASE_KEY), None)
    if ph is None:
        print(f"  [STOPP] {PHASE_KEY}-fas saknas i statusfilen.")
        print("  Faser som finns:", [p.key for p in rs.phases])
        return

    print(f"  FORE:")
    print(f"    {PHASE_KEY}.state    = {ph.state.value}")
    print(f"    {PHASE_KEY}.started  = {ph.started_at}")
    print(f"    {PHASE_KEY}.finished = {ph.finished_at}")
    print(f"    {PHASE_KEY}.note     = {ph.note}")
    print(f"    topp.state           = {rs.state.value}")

    # finished_at: bundle kordes i flera iterationer (G7, automl-fix), sa wall-tid
    # ar inte meningsfull. Satt nu (eller --finished) -- noten bar sanningen.
    new_finished = args.finished or datetime.datetime.utcnow().strftime(FMT)

    print(f"\n  EFTER (planerat):")
    print(f"    {PHASE_KEY}.state    = succeeded")
    print(f"    {PHASE_KEY}.finished = {new_finished}")
    print(f"    {PHASE_KEY}.note     = {NOTE[:60]}...")

    if not args.apply:
        print("\n  (dry-run -- kor med --apply)")
        print("=" * 70)
        return

    # backup
    bdir = Path(__file__).resolve().parent / f"status_backup_bundle_{STAMP}"
    bdir.mkdir(parents=True, exist_ok=True)
    c = _client().get_container_client(CONTAINER_STATUS)
    raw = c.get_blob_client(f"{RUN_ID}.json").download_blob().readall()
    (bdir / f"{RUN_ID}.json").write_bytes(raw)
    print(f"\n  [backup] {bdir}")

    # rattning
    if not ph.started_at:
        # om started saknas, satt en rimlig start (idag) sa duration ej blir absurd
        ph.started_at = new_finished
    ph.state = PhaseState.SUCCEEDED
    ph.finished_at = new_finished
    ph.note = NOTE
    # rensa ev. stale topp-falt
    for attr in ("hint", "error"):
        if hasattr(rs, attr):
            setattr(rs, attr, None)
    rs.finalize()
    write_status(rs)
    print("  skrivet.")

    # R7
    rs2 = read_status(RUN_ID)
    p2 = next(p for p in rs2.phases if p.key == PHASE_KEY)
    print(f"\n  R7:")
    print(f"    {PHASE_KEY}.state = {p2.state.value}  (ska vara succeeded)")
    print(f"    topp.state        = {rs2.state.value}")
    ok = (p2.state.value == "succeeded")
    print("\n  VERDICT: " + ("RATT -- bundle_model succeeded, appen visar sant."
                             if ok else "GRANSKA -- se backup."))
    print("=" * 70)


if __name__ == "__main__":
    main()
