#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# add_april_status.py -- skapa sann statusfil for april-fonstret (2022-07-01_2026-04-30)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia). Forfattare: Claude.
#
# VARFOR: April-korningen (forsta lyckade +10-man, ~9h VM, dyrt kopt) ska vara
#   valbar i appens rullgardin som ett tredje fonster bredvid facit + maj.
#   Den gamla april-statusfilen var syntetisk (omojlig fas-kombo) och raderades
#   i cleanup_blob_status. Denna ersatter den med SANNING ur VM-loggarna.
#
# KALLOR (matt ur VM-loggar, hamtade 2026-06-23):
#   cluster: 2026-06-17_p1_cluster.log -> 4180 KEY, total 49 min 17.1 sec = 2957 s
#   site:    2026-06-17_p1_site.log    -> 6624 KEY, total 68 min  4.5 sec = 4085 s
#   bundle:  2026-06-20 (bundle/code)  ->  125 KEY, total  1 min 12.9 sec =   73 s
#   Alla tre: motorn (steg 1-4) klar; Steg 5 kraschade pa Linux (xlwings, LB.44) -- vantat.
#
# EFTER-FLODE: site_step5/step6/build_r12 = PENDING. Efter-flodet kordes lokalt
#   men aterrapporterades aldrig till statusfilen for april -> vi pastar inte att
#   det ar klart (arligt: motorn klar, efter ej verifierat pa detta fonster).
#   extraction = SUCCEEDED (data_prep producerade april-CSV:erna som motorn at).
#
# TIDER: started_at konstrueras ur loggdatum (17/6 cluster+site, 20/6 bundle) +
#   rimlig tid; finished_at = started_at + duration. ABSOLUT klocka approximativ,
#   DURATION exakt (det appen visar). Keep it simple.
#
# KOR (global py -3.11, ratt konto, token fornyad):
#   $env:PRICINGMODEL_AUTH="key"; $env:PRICINGMODEL_STORAGE="evbcgpricinginput"
#   py -3.11 tools\add_april_status.py            # dry-run
#   py -3.11 tools\add_april_status.py --apply
# ---------------------------------------------------------------------
import sys, os, argparse, datetime
from pathlib import Path

sys.path.insert(0, r"C:\Projekt\BCG\orchestration\shared")
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")

from run_status import default_pipeline, PhaseState  # noqa: E402
from blob import write_status, read_status, _client, CONTAINER_STATUS  # noqa: E402

RUN_ID = "2022-07-01_2026-04-30"
FMT = "%Y-%m-%dT%H:%M:%SZ"
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Matta korttider (sekunder) + KEY ur VM-loggarna
FAMILY = {
    "cluster_model": {"dur": 2957, "key": 4180, "start": "2026-06-17T06:00:00Z",
                      "note": "4180 KEY (april-fonster); total 49 min 17 s (VM-logg 2026-06-17)"},
    "site_model":    {"dur": 4085, "key": 6624, "start": "2026-06-17T07:30:00Z",
                      "note": "6624 KEY (april-fonster); total 68 min 4 s (VM-logg 2026-06-17)"},
    "bundle_model":  {"dur": 73,   "key": 125,  "start": "2026-06-20T15:40:00Z",
                      "note": "125 KEY (april-fonster); total 1 min 13 s (VM-logg 2026-06-20)"},
}
# extraction succeeded (data_prep matade motorn); efter-flode PENDING (ej aterrapporterat)
EXTRACTION_NOTE = "April-CSV:er producerade av data_prep (matade motorn)"
PENDING_KEYS = {"site_step5", "step6", "build_r12"}


def _plus(start_iso, secs):
    t0 = datetime.datetime.strptime(start_iso, FMT)
    return (t0 + datetime.timedelta(seconds=secs)).strftime(FMT)


def main():
    ap = argparse.ArgumentParser(description="Skapa sann april-statusfil (motorn klar, efter pending).")
    ap.add_argument("--apply", action="store_true", help="Genomfor (utan: dry-run).")
    args = ap.parse_args()

    print("=" * 66)
    print(f"ADD APRIL STATUS -- {RUN_ID}")
    print("=" * 66)

    # Kolla om den redan finns (idempotens / sakerhet)
    existing = [b.name[:-5] for b in _client().get_container_client(CONTAINER_STATUS).list_blobs()
                if b.name.endswith(".json")]
    if RUN_ID in existing:
        print(f"  [OBS] {RUN_ID} finns redan pa Blob. Detta skriver OVER den.")

    rs = default_pipeline(run_id=RUN_ID, triggered_by="add_april_status (motor ur VM-loggar)")
    now = datetime.datetime.utcnow().strftime(FMT)

    for p in rs.phases:
        if p.key == "extraction":
            p.state = PhaseState.SUCCEEDED
            p.started_at = "2026-06-17T05:30:00Z"
            p.finished_at = "2026-06-17T05:55:00Z"
            p.note = EXTRACTION_NOTE
        elif p.key in FAMILY:
            f = FAMILY[p.key]
            p.state = PhaseState.SUCCEEDED
            p.started_at = f["start"]
            p.finished_at = _plus(f["start"], f["dur"])
            p.note = f["note"]
        elif p.key in PENDING_KEYS:
            p.state = PhaseState.PENDING
            p.note = "Efter-flode kordes lokalt men ej aterrapporterat for april (ej verifierat)"

    new_state = rs.finalize()
    print(f"\n  Faser:")
    for p in rs.phases:
        dur = p.duration_human or "-"
        print(f"    {p.key:<16} {p.state.value:<10} dur={dur}")
    print(f"\n  Run-niva -> {new_state.value} (vantat: waiting -- motor klar, efter pending)")

    if not args.apply:
        print("\n  (dry-run -- kor med --apply)")
        print("=" * 66)
        return

    # backup om filen redan fanns
    if RUN_ID in existing:
        bdir = Path(__file__).resolve().parent / f"april_backup_{STAMP}"
        bdir.mkdir(parents=True, exist_ok=True)
        c = _client().get_container_client(CONTAINER_STATUS)
        raw = c.get_blob_client(f"{RUN_ID}.json").download_blob().readall()
        (bdir / f"{RUN_ID}.json").write_bytes(raw)
        print(f"\n  [backup] {bdir}")

    write_status(rs)
    print("  skrivet.")

    # R7
    rs2 = read_status(RUN_ID)
    print("\n  R7-verifiering:")
    ph = " | ".join(f"{p.key}:{p.state.value}" for p in rs2.phases)
    print(f"    run={rs2.state.value}")
    print(f"    {ph}")
    cl = next(p for p in rs2.phases if p.key == "cluster_model")
    si = next(p for p in rs2.phases if p.key == "site_model")
    bu = next(p for p in rs2.phases if p.key == "bundle_model")
    ok = (rs2.state.value == "waiting"
          and cl.duration_seconds == 2957
          and si.duration_seconds == 4085
          and bu.duration_seconds == 73)
    print(f"    cluster={cl.duration_human}  site={si.duration_human}  bundle={bu.duration_human}")
    print("\n  VERDICT: " + ("RATT -- april valbart, motor gron med ratt tider, efter pending."
                             if ok else "GRANSKA -- ovantat utfall."))
    print("=" * 66)


if __name__ == "__main__":
    main()
