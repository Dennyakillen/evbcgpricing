"""
run_cluster_model.py -- Phase runner: Cluster model steps 1-4 on the Azure VM
========================================================================
Runs the Cluster family's BCG launcher (regular_price -> data_prepration ->
feature_selection -> model) on bcg-poc-vm, detached via setsid, with the
growing date window injected through BCG_START_DATE/BCG_END_DATE (G7 env
pattern -- constants.py on the VM is already patched to read them).
Writes phase status + heartbeat to the Blob status contract so the future
status view can render progress. BCG code is NEVER touched.

Pattern: same as run_step6.py / run_bundle_dataprep.py (Jens's proven runner
family): PREFLIGHT -> RUN verbatim -> VERIFY output file (R7) -> tolerate
known-benign errors. KARNPRINCIPER A.9: build on the existing pattern.

Known-benign errors this runner tolerates (encoded, not guessed):
- launcher's 5th script (data_prep_after_model_output.py) ALWAYS fails on
  Linux: it needs xlwings/Excel-COM (LB.44). Steps 1-4 done + fresh
  output_summary.xlsx = SUCCESS for this phase. Step 5 is its own LOCAL phase.
- feature_selection two-pass (LB.18-class): on a NEW key set with no
  control_file, pass 1 generates the template and crashes by design. This
  runner detects that signature and relaunches ONCE (pass 2).

Production test design (first run): re-run Cluster on the data already on the
VM from 2026-06-09 -> the orchestration is validated by reproducing a known
result (6624 unique KEY). Frozen-baseline discipline: the existing remote
output_summary.xlsx is archived (cp) before launch, never overwritten blind.

Inputs (on VM, from the 2026-06-09 session):
  ~/bcg/cluster/data/<MEASURE>.csv  (growing CSV -- exact name measured, not guessed)
  ~/bcg/cluster/code/control_files/  (control file from prior run)
Outputs:
  VM:    ~/bcg/cluster/output/model/output_summary.xlsx
  Local: <repo>\\Pipeline\\02. Elasticity\\2. Product Cluster Level Models\\output\\azure_run_model\\
  Blob:  output/<YYYY-MM-DD>/output_summary.xlsx  (dated folder, Jens's spec)

Related: run_status.py (contract), blob.py (status+output I/O, key mode =
documented debt until AAD data role exists), azure_vm.py (VM/SSH mechanics).
Adapted from the proven run_site_model.py (site validated 2026-06-09 + 2026-06-15).

Usage (global Python 3.11, from repo root):
    py -3.11 orchestration\\runners\\run_cluster_model.py --check     (preflight only)
    py -3.11 orchestration\\runners\\run_cluster_model.py --dry-run   (show plan)
    py -3.11 orchestration\\runners\\run_cluster_model.py          (real run, ~2h ref)

Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Author: Claude advisor, Phase Z session 2026-06-12.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Path bootstrap: runners are entry points; shared/ and infrastructure/ are
# sibling layers, not an installed package. This keeps zero packaging
# ceremony while letting the committed layered structure work.
ORCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))

# Documented debt: AAD data role is ABAC-blocked -> account-key mode until
# the role exists. Overridable; remove when PRICINGMODEL_AUTH=aad works.
os.environ.setdefault("PRICINGMODEL_AUTH", "key")

from run_status import RunStatus, RunState, PhaseState, default_pipeline, window_run_id, resolve_window_end  # noqa: E402
from blob import write_status, read_status, upload_outputs                # noqa: E402
from azure_vm import (                                                    # noqa: E402
    VmConfig, ensure_subscription, start_vm, deallocate_vm,
    vm_power_state, wait_for_ssh, ssh_run, ssh_launch_detached, ssh_launch_selftest,
    scp_from_vm, SshUnreachable,
)

log = logging.getLogger("run_cluster_model")

# ----------------------- Phase constants (Cluster) ------------------------
# Copy-adapt of run_site_model.py: ONLY these constants differ from Site.
# Everything below (detach, poll, two-pass, outcome-gated deallocate, attach)
# is family-agnostic and copied verbatim from the proven Site runner.
PHASE_KEY      = "cluster_model"
REMOTE_CODE    = "/home/azureuser/bcg/cluster/code"
# Cluster OWNS this venv (Site borrows it -- UBUNTU_AZURE_VM #18). Same string,
# different ownership; comment updated per the handover instruction.
REMOTE_PYTHON  = "/home/azureuser/bcg/cluster/.venv/bin/python"
# !!! MUST BE MEASURED, NOT GUESSED (handover + KARN matt-gissa-inte) !!!
# Site input was 0902_..._site_level.csv. Cluster exact filename on the VM is
# unknown until measured. Run measure_cluster_values.py (delivered alongside) or:
#   ssh azureuser@<ip> "ls -t ~/bcg/cluster/data/*.csv | head -1"
# then paste the exact path here.
REMOTE_INPUT   = "/home/azureuser/bcg/cluster/data/0828_Sweden_weekly_model_data_P_C.csv"   # measured 2026-06-15 (P_C = Product x Cluster)
REMOTE_OUTPUT  = "/home/azureuser/bcg/cluster/output/model/output_summary.xlsx"
REMOTE_LOGDIR  = "/home/azureuser/bcg/logs"
LOCAL_OUT_DIR  = Path(r"C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model")
# !!! MUST BE MEASURED, NOT GUESSED !!!
# Handover warns: ROADMAP "4180 KEY" is the STEP-5 BLEND count, NOT necessarily
# the model steps 1-4 KEY count (Site steps 1-4 = 6624). Read the cluster facit
# steps-1-4 output_summary.xlsx KEY count. measure_cluster_values.py reads it.
# None until measured -> verify reports the count without asserting a guessed target.
EXPECTED_KEYS  = 4180          # cluster GROWING steps-1-4 (F.7 ref; 3812 was the FROZEN facit -- wrong baseline)
BENIGN_STEP5   = "Error in data_prep_after_model_output.py"   # xlwings on Linux, always (LB.44)
TWO_PASS_SIG   = "Error in feature_selection.py"              # pass-1 template crash (LB.18-class)


def _now_utc() -> float:
    return datetime.now(timezone.utc).timestamp()


def get_or_create_status(run_id: str) -> RunStatus:
    """One status file per run_id covers ALL phases; each runner updates its
    own phase (read-modify-write; phases run sequentially by one person)."""
    try:
        return read_status(run_id)
    except Exception:
        log.info("No status file for run_id=%s -- creating.", run_id)
        return default_pipeline(run_id=run_id, triggered_by="jens (run_cluster_model)")


def preflight(cfg: VmConfig) -> None:
    """Verify everything this phase needs BEFORE costing VM time."""
    ensure_subscription(cfg)
    state = vm_power_state(cfg)
    log.info("VM power state: %s", state)
    log.info("Preflight (local) OK -- az reachable, subscription correct.")


def preflight_remote(cfg: VmConfig) -> float:
    """After VM is up: verify inputs + venv, archive existing output
    (frozen-baseline discipline), return launch epoch for freshness checks."""
    for path, label in [(REMOTE_INPUT, "input CSV"),
                        (REMOTE_PYTHON, "pipeline venv python"),
                        (f"{REMOTE_CODE}/launcher.py", "launcher.py")]:
        cp = ssh_run(cfg, f"test -e {path} && echo yes || echo no")
        if "yes" not in cp.stdout:
            raise RuntimeError(f"Missing on VM: {label} ({path})")
        log.info("OK on VM: %s", label)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ssh_run(cfg, f"test -f {REMOTE_OUTPUT} && cp {REMOTE_OUTPUT} {REMOTE_OUTPUT}.pre_{stamp} "
                 f"&& echo archived || echo none")
    log.info("Existing remote output archived (frozen-baseline, Way A).")
    return _now_utc()


def launch(cfg: VmConfig, run_id: str, start_date: str, end_date: str) -> str:
    """Detached setsid launch. No single quotes inside inner_cmd (quoting rule).
    Env vars = the G7 growing-window injection, same as Jens's manual runs."""
    remote_log = f"{REMOTE_LOGDIR}/{run_id}_cluster.log"
    inner = (f"export BCG_START_DATE={start_date} BCG_END_DATE={end_date} && "
             f"cd {REMOTE_CODE} && {REMOTE_PYTHON} launcher.py")
    ssh_launch_detached(cfg, inner, remote_log)
    return remote_log


def output_fresh(cfg: VmConfig, since_epoch: float) -> bool:
    """R7: trust the file. mtime newer than launch + size > 0."""
    cp = ssh_run(cfg, f"stat -c %Y_%s {REMOTE_OUTPUT} 2>/dev/null || echo 0_0", check=False)
    try:
        mtime, size = (int(x) for x in cp.stdout.strip().split("_"))
    except Exception:
        return False
    return mtime > since_epoch and size > 0


def poll_until_done(cfg: VmConfig, rs: RunStatus, remote_log: str,
                    launch_epoch: float, max_hours: float,
                    poll_s: int) -> tuple[str, str]:
    """Poll the detached run. Returns (outcome, last_log_tail) where outcome is:
      'success'       -- fresh output produced (steps 1-4 done)
      'pipeline_dead' -- process gone, no fresh output, VM reachable/running
      'lost'          -- could not observe (tunnel) until deadline; job may
                         well still be running -- caller must NOT deallocate.

    Design rule (FAS 13 lesson): the job is setsid-detached and self-
    sufficient; observation is optional. A missed poll = wait, not fail.
    When SSH flakes repeatedly we consult az power state OUT-OF-BAND (the
    exact manual recovery used in FAS 13: az goes outside the tunnel)."""
    deadline = _now_utc() + max_hours * 3600
    last_tail = ""
    missed = 0
    while _now_utc() < deadline:
        time.sleep(poll_s)
        try:
            tail = ssh_run(cfg, f"tail -n 40 {remote_log} 2>/dev/null || true",
                           check=False, timeout=90, retries=1).stdout
            last_tail = tail or last_tail
            running = bool(ssh_run(cfg, "pgrep -f launcher.py || true",
                                   check=False, timeout=60, retries=1).stdout.strip())
            fresh = output_fresh(cfg, launch_epoch)
            missed = 0
        except SshUnreachable as e:
            missed += 1
            log.warning("Observation missed (%d in a row): %s -- detached job "
                        "is unaffected; waiting for the tunnel.", missed, e)
            if missed % 3 == 0:
                state = vm_power_state(cfg)          # az = out-of-band truth
                log.info("Out-of-band az check: VM power state = %s", state)
                if "running" not in state.lower():
                    return "pipeline_dead", last_tail + f"\n[runner] VM state={state} during observation loss"
            for p in rs.phases:
                if p.key == PHASE_KEY:
                    p.note = f"observation degraded (tunnel, {missed} missed polls) -- run unaffected"
            try:
                rs.beat(); write_status(rs)
            except Exception:
                pass
            continue

        finished_lines = [l.strip() for l in last_tail.splitlines()
                          if "Finished" in l and ".py" in l]
        note = finished_lines[-1] if finished_lines else "running (no step finished yet)"
        for p in rs.phases:
            if p.key == PHASE_KEY:
                p.note = note
        rs.beat()
        try:
            write_status(rs)
        except Exception as e:                      # status write must never kill the run
            log.warning("Status write failed (run continues): %s", e)
        log.info("poll: running=%s | %s", running, note)

        if fresh and (not running or BENIGN_STEP5 in last_tail):
            if BENIGN_STEP5 in last_tail:
                log.info("Known-benign: launcher's step 5 failed on Linux "
                         "(xlwings, LB.44) -- steps 1-4 succeeded.")
            return "success", last_tail
        if not running and not fresh:
            return "pipeline_dead", last_tail
    return ("lost" if missed > 0 else "pipeline_dead"), \
           last_tail + "\n[runner] deadline reached (max-hours)"


def verify_and_fetch(run_id: str) -> tuple[Path, str]:
    """scp output home (archive any local predecessor first), verify KEY
    count against the 2026-06-09 reference, upload to dated Blob folder."""
    LOCAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    local_file = LOCAL_OUT_DIR / "output_summary.xlsx"
    if local_file.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_file.rename(LOCAL_OUT_DIR / f"output_summary.pre_{stamp}.xlsx")
    scp_from_vm(VmConfig(), REMOTE_OUTPUT, str(local_file))

    note = f"{local_file.stat().st_size/1e6:.1f} MB"
    try:
        import pandas as pd
        df = pd.read_excel(local_file)
        keys = df["KEY"].nunique() if "KEY" in df.columns else len(df)
        if EXPECTED_KEYS is None:
            note = f"{keys} unique KEY (no target set -- measure + set EXPECTED_KEYS), {note}"
        else:
            match = "MATCHES" if keys == EXPECTED_KEYS else f"differs from {EXPECTED_KEYS}"
            note = f"{keys} unique KEY ({match} cluster facit reference), {note}"
        log.info("VERIFY: %s", note)
    except Exception as e:
        log.warning("Verification read skipped (%s) -- file fetched, size %s", e, note)

    date_folder = datetime.now().strftime("%Y-%m-%d")
    blob_paths = upload_outputs(date_folder, [str(local_file)])
    return local_file, note, blob_paths


def find_remote_log(cfg: VmConfig) -> tuple[str, float]:
    """For --attach: locate the newest cluster run log on the VM and recover the
    launch time from its .launch.sh (written at launch -- its mtime IS the
    launch epoch). Lets us re-attach after local interruptions (token death,
    accidental Ctrl+C, tunnel collapse) without touching the running job."""
    cp = ssh_run(cfg, f"ls -t {REMOTE_LOGDIR}/*_cluster.log 2>/dev/null | head -1", check=False)
    remote_log = cp.stdout.strip()
    if not remote_log:
        raise RuntimeError("No cluster run log found on the VM -- nothing to attach to.")
    cp = ssh_run(cfg, f"stat -c %Y {remote_log}.launch.sh 2>/dev/null || echo 0", check=False)
    launch_epoch = float(cp.stdout.strip() or 0)
    if launch_epoch == 0:
        raise RuntimeError(f"Found {remote_log} but no .launch.sh next to it -- "
                           "cannot recover launch time safely.")
    log.info("Attaching to %s (launched %s)", remote_log,
             datetime.fromtimestamp(launch_epoch).strftime("%Y-%m-%d %H:%M:%S"))
    return remote_log, launch_epoch


def finish_success(rs: RunStatus, run_id: str, cfg: VmConfig) -> int:
    local_file, note, blob_paths = verify_and_fetch(run_id)

    # Bygg 2: hämta ALLA växande output-filer från VM + ladda upp till Blob
    # (alla storlekar, inga dubbletter -- VM-mappen är ren). Din syfte-B-vision.
    try:
        _, all_note = fetch_all_outputs(cfg, run_id)
        note = f"{note}; {all_note}"
    except Exception as e:
        log.warning("Bygg 2 (alla filer till Blob) misslyckades -- summary uppladdad ändå: %s", e)

    # Bygg 1: auto-validera mot fryst BCG-facit, sist (din vision: validera när
    # familjen körts). Mot SENASTE körning är medvetet utanför scope.
    try:
        val_note = run_local_validation("cluster", local_file)
        note = f"{note}; {val_note}"
        log.info("Auto-validering klar: %s", val_note)
    except Exception as e:
        log.warning("Auto-validering misslyckades (output ändå hämtad): %s", e)

    rs.finish_phase(PHASE_KEY, ok=True, note=note)
    rs.output_blob_paths = sorted(set(rs.output_blob_paths) | set(blob_paths))
    rs.finalize()   # harled run-nivan ur faserna (stang/vilande, ej tickande spoke)
    rs.beat(); write_status(rs)
    print("\n" + rs.timing_summary())
    print(f"\nSUCCESS: {local_file}\n{note}")
    return 0


# ============================================================================
# TILLÄGG till run_cluster_model.py (Phase Z): auto-validering + alla filer
# till Blob. Bygg 1+2, 2026-06-16. Hakar in i finish_success före deallocate.
# ============================================================================

# --- Validerings-orkestratorer per familj (mätt: tar --output-summary / --family) ---
import subprocess
VERIFY_ROOT = ORCH.parent / "verify_tool"
VERIFY_PY = sys.executable  # global 3.11 (verify_tool-miljön; samma som kör runnern)

def run_local_validation(family: str, local_file: Path) -> str:
    """Bygg 1: auto-validera den hämtade outputen mot FRYST BCG-facit, sist i
    körningen (din vision: validera när familjen körts). Kör rationality
    (--output-summary pekar på just denna fil) + proof_chain (--family).
    Headless subprocess, exit 0=PASS. Returnerar en kort status-note.
    Validering mot SENASTE körning är medvetet UTANFÖR scope (BCG-facit räcker)."""
    results = []

    # 1. Rationality (rimlighet) -- tar explicit sökväg till den hämtade filen
    rat = VERIFY_ROOT / "output_rationality" / "run_all_rationality.py"
    if rat.exists():
        try:
            cp = subprocess.run(
                [VERIFY_PY, str(rat), "--output-summary", str(local_file)],
                capture_output=True, text=True, timeout=600)
            verdict = "PASS" if cp.returncode == 0 else "REVIEW/FAIL"
            results.append(f"rationality={verdict}")
            log.info("Auto-validering rationality: %s (exit %d)", verdict, cp.returncode)
        except Exception as e:
            results.append("rationality=ERROR")
            log.warning("Rationality-validering misslyckades: %s", e)

    # 2. Proof-chain (bit-för-bit) -- hittar ours via default (azure_run_model/)
    pc = VERIFY_ROOT / "proof_chain" / "run_all.py"
    if pc.exists():
        try:
            cp = subprocess.run(
                [VERIFY_PY, str(pc), "--family", family],
                capture_output=True, text=True, timeout=1800)
            verdict = "PASS" if cp.returncode == 0 else "REVIEW/FAIL"
            results.append(f"proof_chain={verdict}")
            log.info("Auto-validering proof_chain: %s (exit %d)", verdict, cp.returncode)
        except Exception as e:
            results.append("proof_chain=ERROR")
            log.warning("Proof_chain-validering misslyckades: %s", e)

    return "validering: " + ", ".join(results) if results else "validering: inga skript hittades"


# --- Bygg 2: hämta ALLA växande output-filer från VM, ladda upp till Blob ---
# VM:ens output-mapp är ren (bara färsk körning -- inga lokala _archive/dubbletter).
# Filtrera bort .pre_-arkiv som runnern själv skapar. Alla storlekar (ditt val).
SKIP_UPLOAD_SUBSTR = (".pre_", "~$")

def fetch_all_outputs(cfg: VmConfig, run_id: str) -> tuple[list[Path], str]:
    """Bygg 2: scp:a HELA VM:ens cluster-output-mapp (inte bara summary),
    ladda upp alla relevanta filer till Blob under output/<date>/cluster/.
    Inga dubbletter (VM-mappen är ren; .pre_ filtreras)."""
    remote_dir = "/home/azureuser/bcg/cluster/output"
    local_root = LOCAL_OUT_DIR.parent / "azure_run_full"
    local_root.mkdir(parents=True, exist_ok=True)

    # Lista VM:ens output-filer (rekursivt), scp:a var och en
    cp = ssh_run(cfg, f"find {remote_dir} -type f 2>/dev/null", check=False)
    remote_files = [l.strip() for l in cp.stdout.splitlines() if l.strip()]
    fetched = []
    for rf in remote_files:
        name = rf.rsplit("/", 1)[-1]
        if any(s in name for s in SKIP_UPLOAD_SUBSTR):
            continue
        rel = rf.replace(remote_dir + "/", "")
        dest = local_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            scp_from_vm(cfg, rf, str(dest))
            fetched.append(dest)
        except Exception as e:
            log.warning("scp misslyckades för %s: %s", rf, e)

    if not fetched:
        return [], "0 filer hämtade från VM"

    date_folder = datetime.now().strftime("%Y-%m-%d")
    # upload_outputs bygger blob_name = f"{run_id}/{path.name}" -- så vi lägger
    # hela den relativa MAPPEN i run_id-argumentet. Då bevaras strukturen och
    # filnamns-kollisioner (två output_summary.xlsx i olika undermappar) undviks.
    # Resultat: output/<date>/cluster/<rel-mapp>/<filnamn> -- förutsägbart för
    # nästa familjs återanvändning (din vision).
    blob_paths = []
    total_mb = 0.0
    for f in fetched:
        rel = f.relative_to(local_root)
        subdir = rel.parent.as_posix()           # "" om filen ligger i roten
        prefix = f"{date_folder}/cluster" + (f"/{subdir}" if subdir not in ("", ".") else "")
        mb = f.stat().st_size / 1e6
        total_mb += mb
        bp = upload_outputs(prefix, [str(f)])
        blob_paths.extend(bp)
    note = f"{len(fetched)} filer -> Blob ({total_mb:.0f} MB)"
    log.info("Bygg 2: %s", note)
    return fetched, note


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Cluster model steps 1-4 on the VM (Phase Z runner).")
    ap.add_argument("--run-id", default=None,
                    help="Run id. Default: datafonstret (window_run_id ur start/end) sa alla familjer for samma period delar EN statusfil.")
    ap.add_argument("--start-date", default="2022-07-01")
    ap.add_argument("--end-date", default=None,
                    help="Growing window end. TODO Phase Z vision: empty -> auto last closed month.")
    ap.add_argument("--max-hours", type=float, default=3.0, help="Cluster ref: ~2h (heavier than Site).")
    ap.add_argument("--poll-seconds", type=int, default=90)
    ap.add_argument("--keep-vm", action="store_true", help="Skip deallocate (e.g. cluster runs next).")
    ap.add_argument("--check", action="store_true", help="Local preflight only; touches nothing.")
    ap.add_argument("--dry-run", action="store_true", help="Show the exact plan; no actions.")
    ap.add_argument("--launch-test", action="store_true",
                    help="Start VM, validate the detach mechanic with a sleep job, deallocate. No pipeline.")
    ap.add_argument("--attach", action="store_true",
                    help="Re-attach to a run already in progress on the VM (after local interruption). "
                         "No launch -- just observe, fetch, deallocate.")
    args = ap.parse_args()
    # Phase Z: harled vaxande fonstrets slut dynamiskt ur parquetens data om
    # --end-date ej angavs (ingen hardkodning -> foljer datan, sista kompletta manad).
    if args.end_date is None:
        args.end_date = resolve_window_end()
        logging.getLogger(__name__).info(
            "WINDOW: end-date harlett dynamiskt -> %s (sista kompletta manad i parquet)",
            args.end_date)
    # Harled fonster-id ur datumfonstret om --run-id ej angavs, sa alla familjer
    # for samma parquet-period hamnar i SAMMA statusfil (grona samtidigt, i synk).
    if args.run_id is None:
        args.run_id = window_run_id(args.start_date, args.end_date)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = VmConfig()

    if args.dry_run:
        print(f"PLAN run_id={args.run_id}: start VM -> archive remote output -> setsid launch:")
        print(f"  export BCG_START_DATE={args.start_date} BCG_END_DATE={args.end_date} && "
              f"cd {REMOTE_CODE} && {REMOTE_PYTHON} launcher.py")
        print(f"  poll {args.poll_seconds}s, max {args.max_hours}h; benign: step-5 xlwings; "
              f"two-pass on feature_selection; fetch -> {LOCAL_OUT_DIR}; blob output/<date>/; "
              f"deallocate only on confirmed success/dead (observation loss leaves VM running)")
        return 0

    preflight(cfg)
    if args.check:
        print("CHECK OK: az + subscription fine. Run without --check to execute.")
        return 0

    if args.launch_test:
        try:
            start_vm(cfg)
            wait_for_ssh(cfg)
            ok = ssh_launch_selftest(cfg)
            print("LAUNCH-TEST:", "PASS -- detach mechanic works." if ok
                  else "FAIL -- ssh did not release or process not alive (see log).")
            return 0 if ok else 1
        finally:
            deallocate_vm(cfg)
            log.info("VM deallocated after launch-test.")

    rs = get_or_create_status(args.run_id)

    # --------------- ATTACH: observe an existing run ----------------------
    if args.attach:
        state = vm_power_state(cfg)
        if "running" not in state.lower():
            print(f"VM is '{state}' -- nothing running to attach to.")
            return 1
        wait_for_ssh(cfg)
        remote_log, launch_epoch = find_remote_log(cfg)
        rs.start_phase(PHASE_KEY)   # idempotent enough: marks observing again
        write_status(rs)
        outcome, tail = poll_until_done(cfg, rs, remote_log, launch_epoch,
                                        args.max_hours, args.poll_seconds)
        return _handle_outcome(outcome, tail, rs, args, cfg, attempt_left=False)

    # --------------- NORMAL: launch + observe -----------------------------
    rs.start_phase(PHASE_KEY)
    write_status(rs)

    try:
        start_vm(cfg)
        wait_for_ssh(cfg)
        launch_epoch = preflight_remote(cfg)
    except KeyboardInterrupt:
        log.warning("Interrupted before launch -- deallocating (nothing running).")
        deallocate_vm(cfg)
        return 1
    except Exception as e:
        log.exception("Failed before launch.")
        rs.fail(error=str(e), hint="Technical failure before the VM run started. Contact Jens.")
        write_status(rs)
        deallocate_vm(cfg)          # nothing launched -> safe to stop billing
        return 1

    try:
        for attempt in (1, 2):                     # two-pass tolerance, max one relaunch
            remote_log = launch(cfg, f"{args.run_id}_p{attempt}", args.start_date, args.end_date)
            outcome, tail = poll_until_done(cfg, rs, remote_log, launch_epoch,
                                            args.max_hours, args.poll_seconds)
            if outcome == "pipeline_dead" and attempt == 1 \
                    and TWO_PASS_SIG in tail and BENIGN_STEP5 not in tail:
                log.info("feature_selection pass-1 template crash detected "
                         "(LB.18-class) -- relaunching once for pass 2.")
                rs.beat(); write_status(rs)
                continue
            return _handle_outcome(outcome, tail, rs, args, cfg, attempt_left=False)
        return 1
    except KeyboardInterrupt:
        return _leave_running(rs, cfg, "Interrupted locally (Ctrl+C).")
    except SshUnreachable as e:
        return _leave_running(rs, cfg, f"Tunnel lost during orchestration: {e}")
    except Exception as e:
        log.exception("Runner failed after launch.")
        return _leave_running(rs, cfg, f"Local runner error after launch: {e}")


def _handle_outcome(outcome: str, tail: str, rs: RunStatus, args, cfg,
                    attempt_left: bool) -> int:
    """Deallocate ONLY on confirmed outcomes. Observation loss leaves the VM
    (and the possibly-healthy job) alone -- the FAS 13 rule, now in code."""
    if outcome == "success":
        rc = finish_success(rs, args.run_id, cfg)
        if args.keep_vm:
            log.warning("VM left RUNNING (--keep-vm). ~9 kr/h -- deallocate when done.")
        else:
            deallocate_vm(cfg)
            log.info("VM deallocated -- compute billing stopped.")
        return rc
    if outcome == "pipeline_dead":
        rs.fail(error=f"Run did not produce fresh output. Log tail:\n{tail[-1500:]}",
                hint="Cluster model stalled on the VM. Restart the run, or contact Jens.")
        write_status(rs)
        deallocate_vm(cfg)
        log.info("VM deallocated -- compute billing stopped.")
        return 1
    # outcome == "lost"
    return _leave_running(rs, cfg, "Could not observe the run (tunnel) before the deadline.")


def _leave_running(rs: RunStatus, cfg: VmConfig, why: str) -> int:
    """We lost the ability to watch -- the detached job has NOT failed.
    Leave the VM running, tell the status file and Jens how to recover."""
    log.warning("%s The detached job on the VM is likely STILL RUNNING.", why)
    rs.mark_waiting(f"{why} Job continues detached on the VM. "
                    f"Re-attach with: py -3.11 orchestration\\runners\\run_cluster_model.py --attach")
    try:
        write_status(rs)
    except Exception:
        pass
    print("\n" + "=" * 70)
    print("OBSERVATION LOST -- THE RUN ITSELF IS LIKELY FINE (setsid-detached).")
    print("VM left RUNNING on purpose (~9 kr/h) so the job can finish.")
    print("When the tunnel is back, re-attach with:")
    print("    py -3.11 orchestration\\runners\\run_cluster_model.py --attach")
    print("Or, to stop everything and the billing:")
    print("    az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm")
    print("=" * 70)
    return 2


if __name__ == "__main__":
    sys.exit(main())
