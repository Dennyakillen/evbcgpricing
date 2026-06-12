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
def ssh_run(cfg: VmConfig, remote_cmd: str, check: bool = True,
            timeout: int = 60) -> subprocess.CompletedProcess:
    """Run one remote command and wait for it. Keep remote_cmd free of single
    quotes (VM paths contain no spaces; this avoids the PS/bash quoting class
    of failures entirely since we never go through PowerShell)."""
    cp = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
         cfg.ssh_target, remote_cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    if check and cp.returncode != 0:
        raise RuntimeError(f"ssh failed ({cp.returncode}): {cp.stderr.strip()[:400]}")
    return cp


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
    immediately. setsid puts it in its own session (immune to SIGHUP when
    this ssh channel closes); stdin/stdout/stderr are detached from the
    channel so ssh does not block. inner_cmd must not contain single quotes."""
    remote = (
        f"mkdir -p $(dirname {remote_log}) && "
        f"setsid bash -c '{inner_cmd} > {remote_log} 2>&1' </dev/null >/dev/null 2>&1 &"
    )
    ssh_run(cfg, remote, timeout=30)
    log.info("Detached launch sent. Remote log: %s", remote_log)


def scp_from_vm(cfg: VmConfig, remote_path: str, local_path: str) -> None:
    cp = subprocess.run(
        ["scp", "-o", "ConnectTimeout=10",
         f"{cfg.ssh_target}:{remote_path}", local_path],
        capture_output=True, text=True, timeout=600,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"scp failed ({cp.returncode}): {cp.stderr.strip()[:400]}")
    log.info("Fetched %s -> %s", remote_path, local_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("azure_vm.py: mechanics module. Importable primitives:")
    print("  start_vm / deallocate_vm / vm_power_state / ensure_subscription")
    print("  wait_for_ssh / ssh_run / ssh_launch_detached / scp_from_vm")
    print("No self-test against Azure here -- runners exercise these for real.")
