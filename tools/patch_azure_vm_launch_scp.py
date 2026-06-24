#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_azure_vm_launch_scp.py  --  Harda DELAD SSH-infra mot tunnel-blink
========================================================================
ROTORSAK (mate 2026-06-24, hela kedjan foljd): cluster-maj-relaunch dog i
'OBSERVATION LOST' ~90s in. launch-test PASS (detach frisk), config oprovad.
Asymmetri-jakt i azure_vm.py avslojade: poll_until_done HAR full AZ.7-tolerans
(except SshUnreachable -> fortsatt, az out-of-band var 3:e miss). Men launch
arver INTE den toleransen:

  - ssh_launch_detached (L195 write_script, L204 setsid+echo): INGA retries.
    En tunnel-blink under launch -> ssh_run kastar SshUnreachable -> main
    fangar som "failed after launch" -> OBSERVATION LOST. Jobbet startar aldrig.
  - scp_from_vm (L231): RA subprocess.run, ENDAST ConnectTimeout=10, INGEN
    retry/ServerAlive. Nedstroms-fallpunkt: en blink i minut 50 av en lyckad
    korning tappar hela output-hamtningen (samma symptom som tidigare incident
    "tunnel drop prevented auto-upload").

MONSTER: tunneln tal enstaka korta anrop (sond 5 gron, launch-test gron) men
blinkar efter en SERIE anrop i tat foljd (4 SSH-anrop i preflight precis fore
launch -> launch landar i blink). Darfor PASS i vakuum men FAIL i full korning.

FIX (denna fil, DELAD infra -> harder cluster+site+bundle simultant):
  A1. ssh_launch_detached: retries=2 pa write_script (L195) + setsid+echo (L204).
  A2. ssh_launch_detached: efter "started", VERIFIERA med pgrep -f launcher.py
      att jobbet faktiskt lever (out-of-band-taligt). Lever det ej -> retry
      hela launch-sekvensen en gang. Stanger "halv launch"-risken (steg 1 kor,
      steg 2 blinkar -> .launch.sh finns men inget jobb). Gor launch lika
      robust som poll_until_done.
  B.  scp_from_vm: ServerAliveInterval=10 ServerAliveCountMax=3 (paritet med
      ssh_run) + retry-loop (2 omforsok). Stanger nedstroms-fallpunkten.

ADDITIV: ssh_run:s default (retries=0) ororda. Andrar inte beteende nar tunneln
ar frisk (0 blinkar -> 0 retries anvands). "Slapp igenom mer, aldrig mindre."

IDEMPOTENT. Backup. UTF-8 utan BOM. Verifierar sig sjalv.

KOER (global py -3.11, lokalt):
    py -3.11 patch_azure_vm_launch_scp.py --dry-run
    py -3.11 patch_azure_vm_launch_scp.py

Utvecklare: Jens Palmoe (Senior Business Analyst, Evidensia). Forfattare: Claude-radgivare.
Beroende: std-lib.
"""
from __future__ import annotations
import argparse, datetime, shutil, sys
from pathlib import Path

DEFAULT = r"C:\Projekt\BCG\orchestration\infrastructure\azure_vm.py"

# --- A1: retries pa de tva launch-anropen ---------------------------------
NEEDLE_A1a = '    ssh_run(cfg, write_script, timeout=30)'
INSERT_A1a = '    ssh_run(cfg, write_script, timeout=30, retries=2)'

NEEDLE_A1b = '    cp = ssh_run(cfg, launch_cmd, timeout=20)'
INSERT_A1b = '    cp = ssh_run(cfg, launch_cmd, timeout=20, retries=2)'

# --- A2: pgrep-verifiering + retry hela launchen --------------------------
# Vi ersatter hela det gamla launch-blocket (write+launch+confirm) med en
# robust variant: en for-loop med 2 forsok, pgrep-verifiering efter "started".
# Marker for idempotens.
OLD_LAUNCH_BLOCK = '''    ssh_run(cfg, write_script, timeout=30, retries=2)

    # Step 2: launch fully detached. setsid + redirect ALL of the script's
    # std streams to /dev/null means the child holds no descriptor on this
    # ssh channel; 'echo started' completes the channel immediately.
    launch_cmd = (
        f"setsid {launcher_sh} </dev/null >/dev/null 2>&1 & "
        f"echo started"
    )
    cp = ssh_run(cfg, launch_cmd, timeout=20, retries=2)
    if "started" not in cp.stdout:
        raise RuntimeError(f"Detached launch did not confirm start: {cp.stdout!r} {cp.stderr!r}")
    log.info("Detached launch confirmed. Remote log: %s", remote_log)'''

NEW_LAUNCH_BLOCK = '''    # Step 2: launch fully detached. setsid + redirect ALL of the script's
    # std streams to /dev/null means the child holds no descriptor on this
    # ssh channel; 'echo started' completes the channel immediately.
    launch_cmd = (
        f"setsid {launcher_sh} </dev/null >/dev/null 2>&1 & "
        f"echo started"
    )
    # A2 (2026-06-24): launch must inherit poll_until_done's AZ.7 tolerance.
    # ssh_run already retries each call on a tunnel blink; on top of that we
    # VERIFY the job actually started (pgrep, out-of-band-tolerant) and retry
    # the whole launch sequence once if not. This closes the "half launch"
    # gap: step 1 wrote .launch.sh but step 2's blink meant nothing started
    # (the exact failure of the cluster-maj run, ps=0 + no logfile + .launch.sh
    # absent). A launch that "confirmed" but left no live process is a lie we
    # now catch instead of handing to poll as a phantom run.
    proc_sig = inner_cmd.split("&&")[-1].split()[-1] if "&&" in inner_cmd else "launcher.py"
    last_err = ""
    for launch_attempt in (1, 2):
        # (re)write the launcher script -- idempotent, owns its own redirection
        ssh_run(cfg, write_script, timeout=30, retries=2)
        cp = ssh_run(cfg, launch_cmd, timeout=20, retries=2)
        if "started" not in cp.stdout:
            last_err = f"no 'started' confirmation: {cp.stdout!r} {cp.stderr!r}"
            log.warning("Launch attempt %d: %s", launch_attempt, last_err)
            continue
        # Verify the job is actually alive on the VM (not just that echo printed).
        # check=False + retries=2 so a blink on THIS probe doesn't false-negative.
        try:
            alive = bool(ssh_run(cfg, f"pgrep -f {proc_sig} || true",
                                 check=False, timeout=30, retries=2).stdout.strip())
        except SshUnreachable as e:
            # Could not verify due to tunnel -- per AZ.7, observation loss is not
            # failure. Trust the 'started' echo; poll_until_done will confirm via
            # az out-of-band. Do NOT relaunch (would risk a duplicate job).
            log.warning("Post-launch verify unreachable (%s) -- trusting 'started' "
                        "(AZ.7: observation optional, poll will confirm out-of-band).", e)
            log.info("Detached launch confirmed (unverified). Remote log: %s", remote_log)
            return
        if alive:
            log.info("Detached launch confirmed + verified alive. Remote log: %s", remote_log)
            return
        last_err = "launch echoed 'started' but pgrep found no live process"
        log.warning("Launch attempt %d: %s -- relaunching.", launch_attempt, last_err)
    raise RuntimeError(f"Detached launch failed after 2 attempts: {last_err}")'''


def apply_simple(text, needle, insert, label, changes, skipped):
    if insert in text:
        skipped.append(f"{label}: redan patchad.")
        return text, True
    if needle in text:
        if text.count(needle) != 1:
            print(f"[STOPP] {label}: naal {text.count(needle)} ggr (vantade 1).")
            return text, False
        changes.append(label)
        return text.replace(needle, insert, 1), True
    print(f"[STOPP] {label}: hittar ej naal:\n  {needle}")
    return text, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    fp = Path(args.file)

    print("=" * 74)
    print("PATCH azure_vm.py -- launch retry+verify (A) + scp harden (B), DELAD infra")
    print(f"Fil: {fp}")
    print("=" * 74)
    if not fp.exists():
        print(f"[FEL] saknas: {fp}"); return 2

    text = fp.read_text(encoding="utf-8")
    original = text
    changes, skipped = [], []

    # A1a: write_script retries
    text, ok = apply_simple(text, NEEDLE_A1a, INSERT_A1a, "A1a write_script retries=2", changes, skipped)
    if not ok: return 2
    # A1b: launch_cmd retries
    text, ok = apply_simple(text, NEEDLE_A1b, INSERT_A1b, "A1b launch_cmd retries=2", changes, skipped)
    if not ok: return 2
    # A2: swap launch block for robust version (depends on A1 having run)
    if NEW_LAUNCH_BLOCK in text:
        skipped.append("A2 pgrep-verify+relaunch: redan patchad.")
    elif OLD_LAUNCH_BLOCK in text:
        if text.count(OLD_LAUNCH_BLOCK) != 1:
            print(f"[STOPP] A2: block {text.count(OLD_LAUNCH_BLOCK)} ggr (vantade 1)."); return 2
        text = text.replace(OLD_LAUNCH_BLOCK, NEW_LAUNCH_BLOCK, 1)
        changes.append("A2 pgrep-verify + relaunch-once")
    else:
        print("[STOPP] A2: hittar ej det forvantade launch-blocket (efter A1).")
        print("  -> Kallan kan avvika. Inspektera ssh_launch_detached manuellt.")
        return 2

    # B: scp_from_vm harden
    OLD_SCP = '''    cp = subprocess.run(
        ["scp", "-o", "ConnectTimeout=10",
         f"{cfg.ssh_target}:{remote_path}", local_path],
        capture_output=True, text=True, timeout=600,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"scp failed ({cp.returncode}): {cp.stderr.strip()[:400]}")
    log.info("Fetched %s -> %s", remote_path, local_path)'''
    NEW_SCP = '''    # B (2026-06-24): scp goes through the SAME flaky tunnel as ssh_run but was
    # a raw subprocess with no ServerAlive + no retry -- a blink in minute 50 of
    # a successful run would lose the whole output fetch. Mirror ssh_run's
    # keepalive + add a retry loop. "self-terminate a stalled tunnel in ~30s
    # instead of hanging to the 600s timeout, then retry."
    last_err = ""
    for attempt in range(3):                         # 1 try + 2 retries
        cp = subprocess.run(
            ["scp", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
             "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=3",
             f"{cfg.ssh_target}:{remote_path}", local_path],
            capture_output=True, text=True, timeout=600,
        )
        if cp.returncode == 0:
            log.info("Fetched %s -> %s", remote_path, local_path)
            return
        last_err = cp.stderr.strip()[:400]
        log.warning("scp failed (attempt %d/3, rc=%d): %s -- retrying.",
                    attempt + 1, cp.returncode, last_err)
    raise RuntimeError(f"scp failed after 3 attempts ({cp.returncode}): {last_err}")'''

    if NEW_SCP in text:
        skipped.append("B scp harden: redan patchad.")
    elif OLD_SCP in text:
        if text.count(OLD_SCP) != 1:
            print(f"[STOPP] B: scp-block {text.count(OLD_SCP)} ggr (vantade 1)."); return 2
        text = text.replace(OLD_SCP, NEW_SCP, 1)
        changes.append("B scp_from_vm: keepalive + retry-loop")
    else:
        print("[STOPP] B: hittar ej det forvantade scp-blocket.")
        print("  -> Inspektera scp_from_vm manuellt.")
        return 2

    print("\nPLANERADE AENDRINGAR:")
    for c in changes: print(f"  + {c}")
    for s in skipped: print(f"  = {s}")
    if not changes:
        print("\n[KLART] Redan patchad (idempotent)."); return 0
    if args.dry_run:
        print("\n[DRY-RUN] Inget skrevs."); return 0

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    bak = fp.with_suffix(fp.suffix + f".before-launchscp-{stamp}.bak")
    shutil.copy2(fp, bak)
    print(f"\n[Backup] {bak}")
    with open(fp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"[Skrev]  {fp} (UTF-8 utan BOM)")

    v = fp.read_text(encoding="utf-8")
    checks = {
        "A1a write_script retries=2": INSERT_A1a in v,
        "A1b launch_cmd retries=2":  INSERT_A1b in v,
        "A2 pgrep-verify block":     NEW_LAUNCH_BLOCK in v,
        "B scp keepalive+retry":     NEW_SCP in v,
        "ingen BOM":                 fp.read_bytes()[:3] != b"\xef\xbb\xbf",
    }
    print("\nVERIFIERING:")
    for k, ok in checks.items():
        print(f"  {'JA ' if ok else 'NEJ'} {k}")
    # Syntaxkoll: kompilera filen
    import py_compile
    try:
        py_compile.compile(str(fp), doraise=True)
        print("  JA  py_compile (syntax OK)")
        syntax_ok = True
    except py_compile.PyCompileError as e:
        print(f"  NEJ py_compile MISSLYCKADES: {e}")
        syntax_ok = False

    if all(checks.values()) and syntax_ok:
        print("\n[KLART] launch+scp harden, syntax gron. Committa + relaunch.")
        return 0
    print("\n[VARNING] Ej gron -- aterstall fran backup, inspektera.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
