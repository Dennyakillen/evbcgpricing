#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_5_vm_reachability.py  --  SOND 5: VARFOER hanger SSH till VM:en? (lager for lager)
=========================================================================================
FRAGAN den svarar: nar SSH till bcg-poc-vm "fastnar", VILKET lager ar trasigt?
Internet, VPN-route, TCP/22, SSH-handskakning, session-stabilitet under tid,
eller VM-svarstid under last? Kvallens strul (2026-06-23) rubricerades "krasch"
men var ol4st pa tunnelniva -- denna sond isolerar lagret i ETT svep i stallet
for reaktiv gissa->testa->hanga.

P.5-anda: folj kedjan lager for lager, mat tillstandet efter varje, testa flera
rotorsaks-hypoteser PARALLELLT i samma korning, skriv till fil sa brus inte
begraver svaret. ROR INGET pa VM:en -- bara matning.

LAGREN (var med egen kort timeout sa ett hangt lager ej blockerar nasta):
  L1  Internet              -- nar publik host (utesluter "allt nere")
  L2  VPN/route till VM-IP  -- TCP-anslutning till VM:ens privata IP (ej SSH an)
  L3  TCP port 22 oppen     -- svarar SSH-porten pa socket-niva?
  L4a SSH snabbkommando     -- 'echo ALIVE' (millisekunder; lyckades 21:07 ikvall)
  L4b SSH medellangt kmd    -- 'ls ~/bcg' (filsystem; nagra hundra ms)
  L4c SSH langsamt kmd      -- 'ps aux | wc -l' (processlista; det som HANGDE)
  L5  VM-last (om L4 funkar) -- uptime/loadavg: hog load => jobbet lever & kvaver sshd
  L6  Jobb-livssignal        -- kor python/ray pa VM? (svaret vi jagat hela kvallen)

TOLKNING (sonden skriver den sjalv langst ned):
  - L1 OK, L2 FAIL  -> VPN-route till 172.18.x nere (privat IP ej nabar). VPN-problem.
  - L2 OK, L3 FAIL  -> ansluter till VM men port 22 filtrerad/stangd (NSG/sshd nere).
  - L3 OK, L4a FAIL -> handskakning failar (sshd-problem, nyckel, MaxStartups).
  - L4a OK, L4c FAIL -> SESSION-STABILITET: korta kmd lyckas, langre dor.
       Korsa med L5: hog load => VM kvaver SSH (jobbet LEVER); lag load => natflakighet.
  - L4c OK + L5 hog load + L6>0 -> jobbet lever, SSH bara trog under last. VANTA.
  - L4c OK + L6==0 -> jobbet dott. Las VARFOR (KeyError = fix holl ej, eller annat).

KOER (global py -3.11, lokalt -- kraver ssh+ping pa PATH, VPN igang):
    py -3.11 probe_5_vm_reachability.py
    py -3.11 probe_5_vm_reachability.py --vm azureuser@172.18.148.4 --ip 172.18.148.4

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
Beroende: std-lib (subprocess, socket, time, argparse, datetime). ssh+ping pa PATH.
"""
from __future__ import annotations
import argparse
import datetime
import socket
import subprocess
import sys
import time

VM_DEFAULT = "azureuser@172.18.148.4"
IP_DEFAULT = "172.18.148.4"
PUBLIC_HOST = "github.com"  # for L1 internet-check (i nat-allowlist)


def timed(fn):
    """Kor fn(), returnera (resultat, sekunder)."""
    t0 = time.monotonic()
    try:
        r = fn()
    except Exception as e:
        return (("EXC", str(e)[:120]), time.monotonic() - t0)
    return (r, time.monotonic() - t0)


def ssh_cmd(vm: str, cmd: str, timeout: int) -> tuple[str, str]:
    """Kor ETT ssh-kommando med hard timeout. Returnera (verdict, detalj)."""
    full = [
        "ssh",
        "-o", f"ConnectTimeout={min(timeout, 15)}",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        vm, cmd,
    ]
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", f"hangde >{timeout}s")
    if r.returncode == 0:
        return ("OK", r.stdout.strip()[:200] or "(tom stdout men rc=0)")
    return ("FAIL", (r.stderr.strip() or f"rc={r.returncode}")[:200])


def tcp_check(ip: str, port: int, timeout: int) -> tuple[str, str]:
    """Ren socket-anslutning (ingen SSH). Isolerar L2/L3 fran handskakning."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return ("OK", f"TCP {ip}:{port} ansluten")
    except socket.timeout:
        return ("TIMEOUT", f"TCP {ip}:{port} timeout >{timeout}s")
    except Exception as e:
        return ("FAIL", f"{type(e).__name__}: {e}")
    finally:
        s.close()


def ping_check(host: str, timeout: int) -> tuple[str, str]:
    """ICMP ping (Windows: -n count, -w ms)."""
    try:
        r = subprocess.run(
            ["ping", "-n", "2", "-w", str(timeout * 1000), host],
            capture_output=True, text=True, timeout=timeout * 3,
        )
        ok = "TTL=" in r.stdout or "ttl=" in r.stdout
        return ("OK" if ok else "FAIL", r.stdout.strip().splitlines()[-1][:120] if r.stdout else "ingen output")
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", f"ping hangde >{timeout*3}s")
    except Exception as e:
        return ("FAIL", str(e)[:120])


def main() -> int:
    ap = argparse.ArgumentParser(description="SOND 5: VM-nabarhet lager for lager.")
    ap.add_argument("--vm", default=VM_DEFAULT)
    ap.add_argument("--ip", default=IP_DEFAULT)
    ap.add_argument("--public", default=PUBLIC_HOST)
    args = ap.parse_args()

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log("=" * 74)
    log(f"SOND 5 -- VM-nabarhet lager for lager   {stamp}")
    log(f"VM: {args.vm}   IP: {args.ip}")
    log("=" * 74)

    results = {}

    # L1 -- internet (publik host)
    log("\n[L1] Internet (publik host, utesluter 'allt nere')")
    (v, d), t = timed(lambda: ping_check(args.public, 5))
    results["L1"] = v
    log(f"     {v:<8} ({t:4.1f}s)  {d}")

    # L2 -- VPN/route: kan vi ens pinga VM:ens privata IP?
    log("\n[L2] VPN/route till VM privat IP (ICMP -- kan filtreras aven nar SSH funkar)")
    (v, d), t = timed(lambda: ping_check(args.ip, 5))
    results["L2_ping"] = v
    log(f"     {v:<8} ({t:4.1f}s)  {d}")
    log("     (OBS: ping kan vara blockerad i NSG aven nar TCP/22 ar oppen -- las L3 ocksa)")

    # L3 -- TCP port 22 (ren socket, ingen SSH-handskakning)
    log("\n[L3] TCP port 22 oppen (socket-niva, isolerar fran SSH-handskakning)")
    (v, d), t = timed(lambda: tcp_check(args.ip, 22, 10))
    results["L3"] = v
    log(f"     {v:<8} ({t:4.1f}s)  {d}")

    # L4a/b/c -- SSH-kommandon av OKANDE langd (samma session-typ, olika varaktighet)
    log("\n[L4] SSH-kommandon -- snabbt/medel/langsamt (isolerar SESSION-STABILITET)")
    for tag, cmd, to in [
        ("L4a snabb (echo)", "echo ALIVE", 12),
        ("L4b medel (ls)", "ls ~/bcg | head -3", 15),
        ("L4c langsam (ps)", "ps aux | grep -c [p]ython", 25),
    ]:
        (res, det), t = timed(lambda c=cmd, x=to: ssh_cmd(args.vm, c, x))
        v = res
        results[tag.split()[0]] = v
        log(f"     {tag:<20} {v:<8} ({t:5.1f}s)  {det}")

    # L5 -- VM-last (bara om nagon L4 lyckades)
    log("\n[L5] VM-last (hog load => jobbet lever & kvaver sshd; lag => natflakighet)")
    if any(results.get(k) == "OK" for k in ("L4a", "L4b", "L4c")):
        (res, det), t = timed(lambda: ssh_cmd(args.vm, "uptime; echo '---'; nproc", 20))
        results["L5"] = res[0]
        log(f"     {res[0]:<8} ({t:5.1f}s)  {det}")
    else:
        log("     SKIP -- ingen L4 lyckades, kan ej mata last")
        results["L5"] = "SKIP"

    # L6 -- jobb-livssignal (bara om L4 funkar)
    log("\n[L6] Jobb-livssignal: kor python/ray pa VM? (svaret vi jagat hela kvallen)")
    if any(results.get(k) == "OK" for k in ("L4a", "L4b", "L4c")):
        (res, det), t = timed(
            lambda: ssh_cmd(args.vm, "ps aux | grep -E '[p]ython|[r]ay' | wc -l", 25))
        results["L6"] = res[0]
        log(f"     {res[0]:<8} ({t:5.1f}s)  processer: {det}")
        if res[0] == "OK":
            (res2, det2), _ = timed(
                lambda: ssh_cmd(args.vm,
                    "ls -t ~/bcg/cluster/output/model/automl/results/ 2>/dev/null | head -3", 20))
            log(f"     feature_selection-output: {det2}")
    else:
        log("     SKIP -- ingen L4 lyckades")
        results["L6"] = "SKIP"

    # --- Dom ---
    log("\n" + "=" * 74)
    log("DOM (lager-isolering):")
    def g(k): return results.get(k, "?")
    if g("L1") != "OK":
        log("  -> L1 FAIL: internet/grundnat nere. Inte ett VM-problem -- fixa natet forst.")
    elif g("L2_ping") != "OK" and g("L3") != "OK":
        log("  -> L2+L3 FAIL: VM-IP onabar (VPN-route till 172.18.x nere). VPN-problem,")
        log("     INTE pipeline/fix. Ateranslut VPN, kor om sonden.")
    elif g("L3") != "OK":
        log("  -> L3 FAIL men L2 ev OK: TCP/22 stangd/filtrerad (NSG-regel eller sshd nere).")
    elif g("L4a") == "OK" and g("L4c") != "OK":
        if g("L5") == "OK":
            log("  -> SESSION-STABILITET-MONSTER + VM svarar pa last-fragan:")
            log("     korta kmd lyckas, langre dor. Las L5-load + L6:")
            log("     hog load + L6>0 => JOBBET LEVER och kvaver sshd (vanta ut det, ej fel).")
            log("     lag load + L6==0 => jobbet dott + natflakighet pa langre sessioner.")
        else:
            log("  -> L4a OK men L4c+L5 dog: langre SSH-sessioner overlever inte.")
            log("     Natflakighet pa varaktighet (keepalive/MTU/VPN-drop). Se rekommendation.")
    elif g("L4c") == "OK" and g("L6") == "OK":
        log("  -> Allt OK + jobb lever. SSH ar friskt NU. Kor run_cluster_model.py --attach,")
        log("     eller polla feature_selection-output direkt.")
    elif g("L4c") == "OK" and g("L6") not in ("OK", "SKIP"):
        log("  -> SSH OK men jobb-koll oklar -- las L6-raden manuellt.")
    elif g("L6") == "OK":
        log("  -> SSH funkar, jobbet lever. Vanta ut / attach.")
    else:
        log("  -> Blandat utfall -- las lagren ovan i ordning, forsta FAIL ar rotorsaken.")
    log("=" * 74)

    # Skriv kvitto till fil (brus begraver ej svaret -- P.5 punkt 4)
    out = f"sond5_vm_reachability_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.txt"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log(f"\n[Kvitto] {out}")
    except Exception as e:
        log(f"\n[Varning] kunde ej skriva kvitto: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
