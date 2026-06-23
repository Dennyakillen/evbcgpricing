#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fix_maj_timing.py -- engangsrattning: ge maj site_model sin SANNA korttid (69:49)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.
#
# VARFOR: cleanup_blob_status satte finished_at = "nu" (saknades efter tunnel-tapp)
#   -> duration blev 19h 28m (start igar -> stad i morse), inte den faktiska korytiden.
#   started_at (2026-06-22T13:40:28Z) ar KORREKT (maj-korningens start, VM-logg).
#   VM-loggens tidssammanfattning: total 69 min 49 s = 4189 s (NEXT_SESSION).
#   Korsvaliderat: 13:40:28 + 4189s = 14:50:17, minuten-nara output_summary 14:46.
#
# GOR: behall started_at, satt finished_at = started_at + 4189s. finalize() (run
#   forblir WAITING). Backup + R7 (duration_human ska bli '1h 9m 49s').
#
# KOR (global py -3.11, ratt konto, token fornyad):
#   $env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
#   py -3.11 tools\fix_maj_timing.py            # dry-run
#   py -3.11 tools\fix_maj_timing.py --apply
# ---------------------------------------------------------------------
import sys, os, argparse, json, datetime
from pathlib import Path

sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")

from run_status import PhaseState  # noqa: E402
from blob import read_status, write_status, _client, CONTAINER_STATUS  # noqa: E402

RUN_ID = "2022-07-01_2026-05-31"
ACTIVE_SECONDS = 4189   # 69 min 49 s, VM-logg (regular 4:57 + prep 4:51 + featsel 36:49 + model 23:12)
FMT = "%Y-%m-%dT%H:%M:%SZ"
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    ap = argparse.ArgumentParser(description="Ratta maj site_model:s korttid till 69:49.")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: dry-run).")
    args = ap.parse_args()

    print("=" * 64)
    print("FIX MAJ TIMING -- site_model -> 69 min 49 s")
    print("=" * 64)

    rs = read_status(RUN_ID)
    site = next((p for p in rs.phases if p.key == "site_model"), None)
    if site is None:
        print("  [STOPP] site_model-fas saknas")
        return

    print(f"  FORE:  started={site.started_at}  finished={site.finished_at}  dur={site.duration_human}")

    if not site.started_at:
        print("  [STOPP] started_at saknas -- kan ej rakna finished_at relativt. Sag till.")
        return

    t0 = datetime.datetime.strptime(site.started_at, FMT)
    new_finished = (t0 + datetime.timedelta(seconds=ACTIVE_SECONDS)).strftime(FMT)
    print(f"  EFTER: started={site.started_at}  finished={new_finished}  (dur ska bli 1h 9m 49s)")

    if not args.apply:
        print("\n  (dry-run -- kor med --apply)")
        print("=" * 64)
        return

    # backup
    bdir = Path(__file__).resolve().parent / f"timing_backup_{STAMP}"
    bdir.mkdir(parents=True, exist_ok=True)
    c = _client().get_container_client(CONTAINER_STATUS)
    raw = c.get_blob_client(f"{RUN_ID}.json").download_blob().readall()
    (bdir / f"{RUN_ID}.json").write_bytes(raw)
    print(f"  [backup] {bdir}")

    # rattning
    site.finished_at = new_finished
    rs.finalize()
    write_status(rs)
    print("  skrivet.")

    # R7
    rs2 = read_status(RUN_ID)
    s2 = next(p for p in rs2.phases if p.key == "site_model")
    print(f"\n  R7: site_model dur = {s2.duration_human} ({s2.duration_seconds} s), run={rs2.state.value}")
    ok = (s2.duration_seconds == ACTIVE_SECONDS) and (rs2.state.value == "waiting")
    print("  VERDICT: " + ("RATT -- 1h 9m 49s, run waiting." if ok else "GRANSKA -- ovantat utfall."))
    print("=" * 64)


if __name__ == "__main__":
    main()
