#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_input_to_vm.py  --  ladda upp lokal CSV till VM:ens site-data (FD.17-steg)
=================================================================================
Site-runnern LASER VM:ens lokala ~/bcg/site/data/0902_..._site_level.csv men har
ingen scp_to_vm -- den antar att datan redan ligger dar (placerad manuellt i en
tidigare session). Detta skript fyller det glappet: laddar upp en fardig lokal CSV
till VM:ens forvantade sokvag+namn, sa familje-runnern kor pa FARSK data.

Speglar scp_from_vm i azure_vm.py (samma subprocess.run, list-args for riktig scp.exe,
omvand riktning). Verifierar byte-storlek pa VM:en efter upload (R7 -- lita pa matt).

ANVANDNING (BCG-repo, global Python; VM MASTE vara startad):
    cd "C:\\Projekt\\BCG"
    py -3.11 orchestration\\tools\\upload_input_to_vm.py `
        --local "Pipeline\\02. Elasticity\\Sweden_Elasticity_Data_Prep_SQL\\output\\Sweden_weekly_model_data_site_level.csv"

Default --remote = site-runnerns REMOTE_INPUT. Override for cluster/bundle.

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia), assisterad av Claude.
"""
from __future__ import annotations
import argparse, subprocess, sys, os
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
sys.path.insert(0, str(REPO / "orchestration" / "infrastructure"))

# VM-detaljer (matchar azure_vm.py VmConfig / STATE: privat IP 172.18.148.4)
VM_USER = "azureuser"
VM_HOST = os.environ.get("BCG_VM_HOST", "172.18.148.4")
# Site-runnerns REMOTE_INPUT (rad 84). Default-mal.
DEFAULT_REMOTE = "/home/azureuser/bcg/site/data/0902_Sweden_weekly_model_data_site_level.csv"


def log(tag, msg): print(f"[{tag}] {msg}", flush=True)


def remote_size(remote_path: str) -> "int | None":
    """ssh: stat byte-storlek pa VM (R7-verifiering efter upload)."""
    # Enkla yttre citattecken, inga nastlade dubbla (SSH-quoting-regel, stuck 6+ ggr)
    cmd = ["ssh", f"{VM_USER}@{VM_HOST}", f"stat -c %s {remote_path} 2>/dev/null || echo MISSING"]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    out = cp.stdout.strip()
    if out == "MISSING" or not out.isdigit():
        return None
    return int(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ladda upp lokal CSV till VM site-data (FD.17).")
    ap.add_argument("--local", required=True, help="Lokal CSV att ladda upp.")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help="Mal-sokvag pa VM (default = site REMOTE_INPUT).")
    ap.add_argument("--dry-run", action="store_true", help="Visa plan, ladda inte upp.")
    args = ap.parse_args()

    local = Path(args.local)
    if not local.is_absolute():
        local = REPO / args.local
    if not local.exists():
        log("ERROR", f"lokal fil saknas: {local}"); return 2
    local_bytes = local.stat().st_size

    print("=" * 66)
    print("UPLOAD INPUT TILL VM (FD.17)")
    print(f"  lokal:  {local}  ({local_bytes:,} bytes)")
    print(f"  -> VM:  {VM_USER}@{VM_HOST}:{args.remote}")
    print("=" * 66)

    # Visa vad som ligger dar NU (sa vi ser att vi ersatter ratt fil)
    before = remote_size(args.remote)
    log("BEFORE", f"VM-fil nu: {before:,} bytes" if before else "VM-fil saknas (ny upload)")

    if args.dry_run:
        log("DRY-RUN", "skulle scp:a upp filen. Inget gjort.")
        return 0

    # Arkivera VM:ens befintliga fil (frozen-baseline-disciplin, som runnern gor for output)
    if before:
        import datetime
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = f"{args.remote}.pre_{stamp}"
        log("ARCHIVE", f"sparar VM:ens gamla fil -> {os.path.basename(bak)}")
        subprocess.run(["ssh", f"{VM_USER}@{VM_HOST}", f"cp {args.remote} {bak}"],
                       capture_output=True, text=True, timeout=120)

    # scp upp (spegel av scp_from_vm: list-args, riktig scp.exe)
    log("UPLOAD", f"scp {local_bytes:,} bytes -> VM (kan ta nagra minuter)...")
    cp = subprocess.run(
        ["scp", "-q", str(local), f"{VM_USER}@{VM_HOST}:{args.remote}"],
        capture_output=True, text=True,
    )
    if cp.returncode != 0:
        log("ERROR", f"scp misslyckades ({cp.returncode}): {cp.stderr.strip()[:400]}")
        return 2

    # R7: verifiera byte-storlek pa VM matchar lokal
    after = remote_size(args.remote)
    if after is None:
        log("ERROR", "kunde ej verifiera VM-filens storlek efter upload."); return 2
    if after == local_bytes:
        log("DONE", f"VM-fil: {after:,} bytes -- MATCHAR lokal ({local_bytes:,}). Upload verifierad.")
    else:
        log("WARN", f"VM-fil: {after:,} bytes men lokal {local_bytes:,} -- STORLEK SKILJER. Kontrollera!")
        return 2

    print("=" * 66)
    print("KLART. VM har nu farsk CSV. Nasta: kor familje-runnern.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
