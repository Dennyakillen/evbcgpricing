#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ssh_keepalive.py  --  Permanent SSH-keepalive for bcg-poc-vm (lar tunneln overleva)
==========================================================================================
ROTORSAK (sond 5 + L4-isolering 2026-06-23): SSH-sessioner till VM:ens privata IP
DOG sa fort de var tysta >~1s (vantade pa kommando-output). 'echo' lyckades (ms),
'ls'/'ps'/runnerns poll/--attach hangde -- VPN/NAT slapper en idle SSH-session.
Bevisat fix: ServerAliveInterval=5 holl sessionen vid liv ('ls ~/bcg' returnerade).

Detta script gor fixen PERMANENT i ~/.ssh/config sa ATT VARJE ssh/scp till VM:en
(inkl. orchestration-runnerns egna observationer) arver keepalive -- inte bara
manuella kommandon med explicit flagga. Utan detta dor runnern likadant nasta korning.

ADDITIVT: laser befintlig ~/.ssh/config, laggar till ETT Host-block for VM-IP:n om
det inte redan finns. Ror inga andra Host-block. Idempotent (kollar markor).
Backup forst. Verifierar sig sjalv.

KOER (global py -3.11, lokalt):
    py -3.11 patch_ssh_keepalive.py
    py -3.11 patch_ssh_keepalive.py --dry-run
    py -3.11 patch_ssh_keepalive.py --host 172.18.148.4

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
Beroende: std-lib (pathlib, argparse, datetime, shutil).
"""
from __future__ import annotations
import argparse
import datetime
import shutil
import sys
from pathlib import Path

MARKER = "# bcg-poc-vm keepalive (sond5 2026-06-23 -- VPN slapper idle SSH)"

def block(host: str) -> str:
    return (
        f"\n{MARKER}\n"
        f"Host {host}\n"
        f"    ServerAliveInterval 5\n"
        f"    ServerAliveCountMax 3\n"
        f"    TCPKeepAlive yes\n"
    )

def main() -> int:
    ap = argparse.ArgumentParser(description="Permanent SSH-keepalive for VM-IP.")
    ap.add_argument("--host", default="172.18.148.4", help="VM privat IP (Host-match).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = Path.home() / ".ssh" / "config"
    print("=" * 72)
    print("PATCH ~/.ssh/config -- permanent keepalive for bcg-poc-vm")
    print(f"Fil: {cfg}")
    print(f"Host: {args.host}")
    print("=" * 72)

    cfg.parent.mkdir(mode=0o700, exist_ok=True)
    existing = cfg.read_text(encoding="utf-8") if cfg.exists() else ""

    if MARKER in existing:
        print("\n[KLART] Keepalive-blocket finns redan (idempotent) -- inget gjordes.")
        # Visa det sa Jens ser att det stammer
        for ln in existing.splitlines():
            if MARKER in existing and ("Host " + args.host in ln or "ServerAlive" in ln or MARKER == ln):
                print(f"    {ln}")
        return 0

    new_text = existing + block(args.host)
    print("\nLAGGER TILL (additivt, ror inga befintliga Host-block):")
    print(block(args.host).rstrip())

    if args.dry_run:
        print("\n[DRY-RUN] Inget skrevs.")
        return 0

    if cfg.exists():
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        bak = cfg.with_name(f"config.before-keepalive-{stamp}.bak")
        shutil.copy2(cfg, bak)
        print(f"\n[Backup] {bak}")

    with open(cfg, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_text)
    try:
        cfg.chmod(0o600)
    except Exception:
        pass
    print(f"[Skrev]  {cfg}")

    verify = cfg.read_text(encoding="utf-8")
    ok = MARKER in verify and "ServerAliveInterval 5" in verify
    print(f"\nVERIFIERING: keepalive-block narvarande: {'JA' if ok else 'NEJ'}")
    if ok:
        print("\n[KLART] Permanent. Testa: ssh azureuser@" + args.host + " 'ls ~/bcg | head -3'")
        print("        (utan -o-flaggor nu -- config.en bar dem). Sedan kor sond 5 igen for bevis.")
        return 0
    print("\n[VARNING] Verifiering ej gron -- inspektera filen + backup.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
