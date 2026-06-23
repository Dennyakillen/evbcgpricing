#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# cleanup_blob_status.py -- Leverans 1: gor Blob-statusfilerna fonster-konsekventa
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Forfattare: Claude-radgivare. Sessionsdatum 2026-06-23.
#
# SYFTE
#   Appens rullgardin ska visa RENA datafonster med sann status per familj.
#   Idag ligger fyra statusfiler pa Blob i blandade scheman (datum vs fonster),
#   en ar ett tickande heartbeat-spoke (maj, dog vid tunnel-tapp fore finalize),
#   en ar en syntetisk app-testfil (omojlig fas-kombo). Detta skript gor Blob
#   sann: tva rena fonster-filer (facit + maj), inget spoke, inget syntetiskt.
#
# VAD DET GOR (idempotent -- kan koras om utan skada)
#   1. BACKUP: laddar ner ALLA nuvarande statusfiler lokalt fore nagot ror.
#   2. MAJ sann: site_model -> succeeded (6604 KEY, validerad rationality 2026-06-23),
#      finalize() -> run-niva WAITING (site klar, resten pending). Spoket dor.
#   3. FACIT skapas: 2022-07-01_2025-06-29, alla familjer succeeded, arligt markt
#      som validerad replikering (verify_receipt_2026-05-28), EJ motor-korning.
#   4. RENSAR kvarlevor: 2026-06-17, 2026-06-20 (datum-schema, ersatts av fonster),
#      2022-07-01_2026-04-30 (syntetisk testfil).
#   5. R7: laser om Blob, bekraftar exakt {facit, maj}, bada sjalvkonsistenta.
#
# DATUM-NOT (inget hardkodat i pipelinen -- detta ar ett ENGANGS-administrativt skript)
#   Facit-fonstret 2022-07-01..2025-06-29 ar BCG:s frusna period (start = LF.2-ankaret,
#   slut = matt ur facit-CSV week_starting_monday 2025-06-23 = sista kompletta veckan,
#   uttryckt som sondag 06-29 enligt constants.py-konventionen). Facit kordes ALDRIG
#   genom orkestratorn (den replikerades + validerades via verify_tool), darfor maste
#   dess fonster anges har en gang. Framtida korningar far sitt run_id HARLETT via
#   window_run_id + resolve_window_end ur parqueten -- aldrig hardkodat.
#
# KOR (global Python 3.11, fran orchestration-mappen, ratt konto satt):
#   $env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
#   py -3.11 tools\cleanup_blob_status.py            # visar plan, fragar innan andring
#   py -3.11 tools\cleanup_blob_status.py --apply    # genomfor
# =====================================================================
import sys, os, json, argparse, datetime
from pathlib import Path

ORCH = Path(r"C:\Projekt\BCG\orchestration")
sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))

from run_status import default_pipeline, PhaseState, RunState  # noqa: E402
from blob import (write_status, read_status, _client,           # noqa: E402
                  CONTAINER_STATUS)

# --- konstanter for detta engangs-jobb ---
FACIT_RUN  = "2022-07-01_2025-06-29"
MAJ_RUN    = "2022-07-01_2026-05-31"
DELETE_IDS = ["2026-06-17", "2026-06-20", "2022-07-01_2026-04-30"]
SITE_NOTE_MAJ   = "6604 KEY (vaxande, validerad rationality 2026-06-23)"
FACIT_NOTE      = "validated bit-for-bit vs BCG -- see verify_receipt_2026-05-28"

STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = Path(__file__).resolve().parent / f"status_backup_{STAMP}"


def _cont():
    return _client().get_container_client(CONTAINER_STATUS)


def list_status_ids():
    return sorted(b.name[:-5] for b in _cont().list_blobs() if b.name.endswith(".json"))


def backup_all():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    c = _cont()
    n = 0
    for b in c.list_blobs():
        if not b.name.endswith(".json"):
            continue
        data = c.get_blob_client(b.name).download_blob().readall()
        (BACKUP_DIR / b.name).write_bytes(data)
        n += 1
    print(f"  [backup] {n} statusfil(er) -> {BACKUP_DIR}")


def make_maj_true(apply: bool):
    """Maj: site_model klar, finalize -> WAITING. Spoket dor."""
    try:
        rs = read_status(MAJ_RUN)
    except Exception as e:
        print(f"  [maj] KUNDE EJ LASA {MAJ_RUN}: {e} -- hoppar")
        return
    before = rs.state.value
    for p in rs.phases:
        if p.key == "site_model":
            p.state = PhaseState.SUCCEEDED
            p.note = SITE_NOTE_MAJ
            if not p.finished_at:
                p.finished_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    new_state = rs.finalize()
    print(f"  [maj] {MAJ_RUN}: site_model -> succeeded; run {before} -> {new_state.value}")
    if apply:
        write_status(rs)
        print("        skrivet.")


def make_facit(apply: bool):
    """Facit: konstruerad fonster-fil, alla familjer succeeded, arligt markt."""
    rs = default_pipeline(run_id=FACIT_RUN, triggered_by="cleanup_blob_status (validated replication)")
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in rs.phases:
        # Extraction + alla familjer + efter-steg: facit ar fullt validerad bakat.
        p.state = PhaseState.SUCCEEDED
        p.started_at = p.started_at or now
        p.finished_at = now
        p.note = FACIT_NOTE
    new_state = rs.finalize()
    print(f"  [facit] {FACIT_RUN}: alla 7 faser -> succeeded; run -> {new_state.value}")
    if apply:
        write_status(rs)
        print("         skrivet.")


def delete_leftovers(apply: bool):
    c = _cont()
    existing = set(list_status_ids())
    for rid in DELETE_IDS:
        if rid in existing:
            print(f"  [delete] {rid}.json")
            if apply:
                c.delete_blob(f"{rid}.json")
        else:
            print(f"  [delete] {rid}.json (finns ej -- redan rensad)")


def verify():
    print("\n--- R7-verifiering: vad ligger pa Blob nu ---")
    ids = list_status_ids()
    ok = True
    for rid in ids:
        try:
            rs = read_status(rid)
            ph = " | ".join(f"{p.key}:{p.state.value}" for p in rs.phases)
            running = [p.key for p in rs.phases if p.state == PhaseState.RUNNING]
            spook = (rs.state == RunState.RUNNING) or bool(running)
            mark = "SPOKE!" if spook else "ok"
            print(f"  {rid}: run={rs.state.value} [{mark}]")
            print(f"      {ph}")
            if spook:
                ok = False
        except Exception as e:
            print(f"  {rid}: LASFEL {e}")
            ok = False
    expected = {FACIT_RUN, MAJ_RUN}
    extra = set(ids) - expected
    missing = expected - set(ids)
    if extra:
        print(f"  [VARNING] ovantade filer kvar: {sorted(extra)}")
        ok = False
    if missing:
        print(f"  [VARNING] forvantad fil saknas: {sorted(missing)}")
        ok = False
    print("\n  VERDICT: " + ("REN -- exakt {facit, maj}, inga spoken." if ok
                             else "GRANSKA -- se varningar ovan."))


def main():
    ap = argparse.ArgumentParser(description="Gor Blob-statusfilerna fonster-konsekventa (Leverans 1).")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: bara visa plan).")
    args = ap.parse_args()

    print("=" * 70)
    print("CLEANUP BLOB STATUS -- Leverans 1 (fonster-konsekvent)")
    print("=" * 70)
    print(f"  Konto: {os.environ.get('PRICINGMODEL_STORAGE', '(ej satt!)')}")
    print(f"  Lage:  {'APPLY (skriver/raderar)' if args.apply else 'DRY-RUN (visar plan)'}")
    print(f"\n  Nuvarande statusfiler: {list_status_ids()}")

    print("\n1. BACKUP")
    if args.apply:
        backup_all()
    else:
        print(f"  [backup] skulle ladda ner alla -> status_backup_<stamp>/ (kor med --apply)")

    print("\n2. MAJ sann (spoke -> WAITING)")
    make_maj_true(args.apply)

    print("\n3. FACIT skapas (validerad replikering)")
    make_facit(args.apply)

    print("\n4. RENSA kvarlevor")
    delete_leftovers(args.apply)

    if args.apply:
        verify()
    else:
        print("\n  (R7-verifiering visas efter --apply)")
    print("=" * 70)


if __name__ == "__main__":
    main()
