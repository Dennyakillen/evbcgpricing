"""
azure_vm.py -- VM lifecycle + SSH execution mechanics (infrastructure layer)
=============================================================================
Pure mechanics for controlling bcg-poc-vm and executing commands on it.
Contains NO orchestration logic -- phase runners (orchestration/runners/)
own their phase's specifics and call these primitives.

Why this shape (course correction 2026-06-12, KARNPRINCIPER A.9 + 8.2):
The earlier version of this file contained a generic start_run() engine with
a stubbed pipeline trigger. That generic engine was replaced by per-phase
runners following Jens's proven run_step6.py pattern (preflight -> run
verbatim -> verify output -> tolerate known-benign errors). This file keeps
only what all runners share: VM start/deallocate, SSH exec, detached launch
(setsid), and scp fetch.

Platform lessons encoded here:
- 'az' is az.cmd on Windows -> subprocess MUST use shell=True string commands
  (list-args gives WinError 2). 'ssh'/'scp' are real .exe -> list-args work.
- LB.46: az caches active subscription -> ensure_subscription() before any
  VM command, never assume.
- CZ.6: sshd is not awake immediately after vm start -> wait_for_ssh() with
  retry, 'Connection refused/timed out' right after start is normal.
- setsid (not tmux, not nohup): process starts in its OWN session, can never
  receive SIGHUP when the ssh channel closes. tmux was a pre-Owner workaround
  Jens explicitly wants retired.

Used by: orchestration/runners/run_site_model.py (and future per-phase runners)
Depends on: az CLI logged in (management scope), working ssh keys to the VM.
The VM has NO public IP -- reachable only when started and from the VNet/VPN
Jens normally uses (SSH proven working repeatedly in prior sessions).

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Author: Claude advisor, Phase Z session 2026-06-12.
"""
from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass

log = logging.getLogger("azure_vm")


@dataclass(frozen=True)
class VmConfig:
    """Facts verified against Azure 2026-06-12 (preflight + az vm show)."""
    subscription_id: str = "42f726f8-91ee-44d4-832f-9d9ec412ef8f"   # ev-lz3-ai (SE)
    resource_group: str = "ev-openai-swce-rg-test"
    vm_name: str = "bcg-poc-vm"
    vm_user: str = "azureuser"
    vm_ip: str = "172.18.148.4"   # private IP; VNet/VPN access required

    @property
    def ssh_target(self) -> str:
        return f"{self.vm_user}@{self.vm_ip}"


# ---------------------------------------------------------------------------
# az CLI -- shell=True because az is a .cmd on Windows (WinError 2 otherwise).
# Arguments here are our own constants only, never untrusted input.
# ---------------------------------------------------------------------------
def _az(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    log.info("az %s", cmd)
    cp = subprocess.run(f"az {cmd}", shell=True, capture_output=True, text=True)
    if check and cp.returncode != 0:
        raise RuntimeError(f"az failed ({cp.returncode}): {cp.stderr.strip()[:400]}")
    return cp


def ensure_subscription(cfg: VmConfig) -> None:
    """LB.46: always set + verify, never trust the cached subscription."""
    _az(f'account set --subscription "{cfg.subscription_id}"')
    cur = _az("account show --query id -o tsv").stdout.strip()
    if cur != cfg.subscription_id:
        raise RuntimeError(f"Active subscription {cur} != expected {cfg.subscription_id} (LB.46)")


def start_vm(cfg: VmConfig) -> None:
    """Idempotent: az vm start on a running VM succeeds quickly."""
    ensure_subscription(cfg)
    log.info("Starting VM %s (idempotent) ...", cfg.vm_name)
    _az(f"vm start --resource-group {cfg.resource_group} --name {cfg.vm_name}")


def deallocate_vm(cfg: VmConfig) -> None:
    """Stops compute billing (~9 kr/h). Disk and data survive deallocate."""
    log.info("Deallocating VM %s ...", cfg.vm_name)
    _az(f"vm deallocate --resource-group {cfg.resource_group} --name {cfg.vm_name}", check=False)


def vm_power_state(cfg: VmConfig) -> str:
    cp = _az(
        f"vm get-instance-view --resource-group {cfg.resource_group} "
        f"--name {cfg.vm_name} "
        f'--query "instanceView.statuses[?starts_with(code, \'PowerState/\')].displayStatus" '
        f"-o tsv",
        check=False,
    )
    return cp.stdout.strip() or "unknown"


# ---------------------------------------------------------------------------
# SSH/SCP -- real .exe binaries on Windows, list-args are correct here.
# ---------------------------------------------------------------------------
class SshUnreachable(RuntimeError):
    """The VPN tunnel / SSH path is flaky (known recurring environment trait,
    FAS 13: hostname returned empty + cp hung while az confirmed VM running).
    Callers must treat this as OBSERVATION LOSS, never as pipeline failure --
    the detached job on the VM is unaffected by our ability to look at it."""


def ssh_run(cfg: VmConfig, remote_cmd: str, check: bool = True,
            timeout: int = 60, retries: int = 0) -> subprocess.CompletedProcess:
    """Run one remote command and wait for it. Keep remote_cmd free of single
    quotes (VM paths contain no spaces; this avoids the PS/bash quoting class
    of failures entirely since we never go through PowerShell).

    ServerAlive options make a stalled tunnel self-terminate in ~30s instead
    of hanging until our subprocess timeout. On timeout or ssh exit 255
    (ssh-level/network error, NOT the remote command's exit code) we retry,
    then raise SshUnreachable so callers can classify it as observation loss.
    """
    last_err = None
    for attempt in range(retries + 1):
        try:
            cp = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
                 "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=3",
                 cfg.ssh_target, remote_cmd],
                capture_output=True, text=True, timeout=timeout,
            )
            if cp.returncode == 255:          # ssh itself failed (tunnel), not the command
                last_err = f"ssh exit 255: {cp.stderr.strip()[:200]}"
                log.warning("ssh unreachable (attempt %d/%d): %s",
                            attempt + 1, retries + 1, last_err)
                continue
            if check and cp.returncode != 0:
                raise RuntimeError(f"ssh failed ({cp.returncode}): {cp.stderr.strip()[:400]}")
            return cp
        except subprocess.TimeoutExpired:
            last_err = f"timeout after {timeout}s"
            log.warning("ssh hung (attempt %d/%d, %s) -- known tunnel flakiness, "
                        "killing and retrying.", attempt + 1, retries + 1, last_err)
    raise SshUnreachable(f"SSH observation failed after {retries + 1} attempt(s): {last_err}")


def wait_for_ssh(cfg: VmConfig, max_tries: int = 18, sleep_s: int = 10) -> None:
    """CZ.6: sshd needs ~1 min after vm start. Retry up to ~3 min."""
    for i in range(1, max_tries + 1):
        try:
            cp = ssh_run(cfg, "echo ok", check=False, timeout=20)
            if cp.returncode == 0 and "ok" in cp.stdout:
                log.info("SSH reachable (attempt %d).", i)
                return
        except Exception:
            pass
        log.info("SSH not ready (attempt %d/%d), waiting %ds ...", i, max_tries, sleep_s)
        time.sleep(sleep_s)
    raise RuntimeError(
        "VM not reachable over SSH. If the VM just started this can be slow "
        "boot; otherwise verify you are on the network/VPN that sees "
        f"{cfg.vm_ip} (the VM has no public IP)."
    )


def ssh_launch_detached(cfg: VmConfig, inner_cmd: str, remote_log: str) -> None:
    """Start a long-running command on the VM, fully detached, and return
    immediately.

    Why the indirection (root cause of the 2026-06-12 timeout): a trailing
    '&' backgrounds the job in bash, but ssh waits for its CHANNEL to close,
    not for the job to finish. setsid's children (Python, Ray's many worker
    procs) keep file descriptors tied to the ssh channel open, so ssh hangs
    until our timeout fires -- even with </dev/null >/dev/null 2>&1 on the
    outer command. The job may actually start, but ssh never returns cleanly.

    Robust fix (standard pattern): write a tiny launcher .sh ON THE VM, then
    start it with setsid + full fd detachment AND make the ssh command itself
    return immediately via a separate, instantly-completing invocation. We
    split into two ssh calls:
      1. write the launcher script + chmod (completes instantly)
      2. setsid the script with all fds to /dev/null, then 'echo started'
         -- ssh call 2 returns as soon as echo prints, because the launched
         process holds NO fd on this channel (the script redirects its own).
    inner_cmd must not contain single quotes (quoting discipline)."""
    launcher_sh = f"{remote_log}.launch.sh"
    # Step 1: write the launcher script on the VM. The script owns its own
    # redirection, so when setsid runs it, nothing touches the ssh channel.
    write_script = (
        f"mkdir -p $(dirname {remote_log}) && "
        f"printf '%s\\n' '#!/bin/bash' '{inner_cmd} > {remote_log} 2>&1' > {launcher_sh} && "
        f"chmod +x {launcher_sh}"
    )
    # Step 2: launch fully detached. setsid + redirect ALL of the script's
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
    raise RuntimeError(f"Detached launch failed after 2 attempts: {last_err}")


def ssh_launch_selftest(cfg: VmConfig) -> bool:
    """Isolated test of the detach mechanic WITHOUT running the pipeline.
    Launches 'sleep 90', confirms ssh returns immediately and the process
    is alive on the VM. Use this to validate launch before a 70-min run.
    Returns True on success."""
    import time as _t
    test_log = "/home/azureuser/bcg/logs/_launchtest.log"
    t0 = _t.time()
    ssh_launch_detached(cfg, "sleep 90 && echo done", test_log)
    elapsed = _t.time() - t0
    if elapsed > 15:
        log.error("Launch took %.1fs -- ssh did NOT release promptly (detach still broken).", elapsed)
        return False
    log.info("ssh released in %.1fs (good).", elapsed)
    alive = bool(ssh_run(cfg, "pgrep -f 'sleep 90' || true", check=False).stdout.strip())
    log.info("Test process alive on VM: %s", alive)
    ssh_run(cfg, "pkill -f 'sleep 90' || true", check=False)  # cleanup
    return alive


def scp_from_vm(cfg: VmConfig, remote_path: str, local_path: str) -> None:
    # B (2026-06-24): scp goes through the SAME flaky tunnel as ssh_run but was
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
    raise RuntimeError(f"scp failed after 3 attempts ({cp.returncode}): {last_err}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("azure_vm.py: mechanics module. Importable primitives:")
    print("  start_vm / deallocate_vm / vm_power_state / ensure_subscription")
    print("  wait_for_ssh / ssh_run / ssh_launch_detached / scp_from_vm")
    print("No self-test against Azure here -- runners exercise these for real.")
