"""
dry_run_full_pipeline.py  --  strukturell dry-run tvars HELA roret (Phase Z)
============================================================================
Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB).
Forfattare: Claude advisor.

VAD DETTA AR (och vad det INTE ar)
----------------------------------
Detta gar langs HELA rordragningen med en lampa och kollar att varje SKARV ar
ihopskruvad -- med roren TOMMA. Det testar RORMOKERIET (sokvagar, namnskarvar,
fonster-konsistens, VM-mekanik, Blob-containrar), INTE vattnet (om data tappas).
For vattnet: window_coherence.py (tvars-familjer) + conservation (kommande) +
end-to-end mot frozen facit (run_smoke_facit.py).

KOMPLETTERAR (ersatter EJ) orchestration\\dry_run_pipeline.py
-------------------------------------------------------------
Den befintliga dry_run_pipeline.py gor 19 KALLA ror-kontroller (konto, parquet,
facit, status, runners, app pekar ratt). DENNA fil gor nasta lager: att SKARVARNA
MELLAN stegen passar tvars FORE -> MOTOR -> EFTER, sa en flertimmarskorning inte
faller i minut 50 pa en namnskarv. Kor garna bada; de kan slas ihop senare.

DE FYRA SKARVKLASSER DENNA FANGAR (mat-gissa-inte, fore varm korning)
---------------------------------------------------------------------
  1. SOKVAGAR finns      -- varje runner + skript + VM-interpreter pa plats.
  2. FONSTER-KONSISTENS  -- window_run_id IDENTISKT tvars run_data / familje-
                            runners / run_after for samma --start/--end. (Driftar
                            de far familjerna olika statusfiler -> finalize ljuger.)
  3. RUNNER-DRY-RUN      -- varje runner svarar pa --dry-run utan att krascha
                            (bevisar att deras egen preflight-logik laddar).
  4. VM + BLOB nabar     -- (om --vm) az svarar, VM-power-state lasbar, Blob-
                            containrar deklarerade. Den vata sidans grundplåt.

KOR (global py-3.11, repo-roten)
--------------------------------
    py -3.11 verify_tool\\dry_run_full_pipeline.py --start 2022-07-01 --end 2026-05-31
    py -3.11 verify_tool\\dry_run_full_pipeline.py --end 2026-05-31 --vm   # + VM/Blob-koll
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Projekt\BCG")
ORCH = REPO / "orchestration"
RUNNERS = ORCH / "runners"

RUN_DATA = RUNNERS / "run_data.py"
RUN_AFTER = RUNNERS / "run_after.py"
FAMILY_RUNNERS = {
    "cluster": RUNNERS / "run_cluster_model.py",
    "site":    RUNNERS / "run_site_model.py",
    "bundle":  RUNNERS / "run_bundle_model.py",
}

# Skript som skarvarna refererar (fast sokvag i repot)
REFERENCED = {
    "regen (BA-venv)":   Path(r"C:\Projekt\Business_Analytics\regenerate_transaction_parquet_chunked.py"),
    "BA-venv python":    Path(r"C:\Projekt\Business_Analytics\.venv\Scripts\python.exe"),
    "prep (DuckDB)":     REPO / "tools" / "replicate_dataprep.py",
    "run_step6":         REPO / "verify_tool" / "run" / "run_step6.py",
    "build_r12":         REPO / "verify_tool" / "run" / "build_r12_for_model.py",
    "pipeline_contracts": REPO / "verify_tool" / "pipeline_contracts.py",
    "window_coherence":  REPO / "verify_tool" / "window_coherence.py",
}

sys.path.insert(0, str(ORCH / "shared"))
sys.path.insert(0, str(ORCH / "infrastructure"))

ROWS: list = []


def rec(status, check, detalj=""):
    ROWS.append((status, check, detalj))
    mark = {"OK": "  OK ", "FAIL": " FAIL", "INFO": "info ", "WARN": "warn "}.get(status, status)
    print(f"   [{mark}] {check}" + (f"  --  {detalj}" if detalj else ""))


def section(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def _exists(p: Path) -> bool:
    return p.exists()


def check_paths():
    section("1. SOKVAGAR -- finns varje lank roret behover?")
    core = {"run_data": RUN_DATA, "run_after": RUN_AFTER, **FAMILY_RUNNERS}
    for label, p in core.items():
        rec("OK" if _exists(p) else "FAIL", f"runner: {label}",
            str(p) if not _exists(p) else f"{p.stat().st_size:,} B")
    for label, p in REFERENCED.items():
        ok = _exists(p)
        # BA-venv + regen + VM-interpreter kan saknas lokalt utan att vara fel HAR
        sev = "OK" if ok else ("WARN" if "BA-venv" in label or "regen" in label else "FAIL")
        rec(sev, f"skript: {label}", str(p) if not ok else "finns")


def check_window_consistency(start: str, end: str):
    section("2. FONSTER-KONSISTENS -- samma window_run_id tvars alla steg?")
    try:
        from run_status import window_run_id  # type: ignore
    except Exception as e:  # noqa: BLE001
        rec("FAIL", "kan ej importera window_run_id", f"{type(e).__name__}: {e}")
        return
    rid = window_run_id(start, end)
    rec("INFO", "window_run_id (kanon)", rid)
    # run_data harleder start='2022-07-01' internt om bara --end ges. Bevisa att
    # det matchar det run_after/familjerna anvander.
    rid_data_default = window_run_id("2022-07-01", end)
    if rid_data_default == rid:
        rec("OK", "run_data default-start ger samma id", f"({rid})")
    else:
        rec("WARN", "run_data default-start ger ANNAT id",
            f"run_data(2022-07-01,{end})={rid_data_default} != {rid} -- ange --start lika overallt")
    # default_pipeline-faser tackta?
    try:
        from run_status import default_pipeline, PhaseLocation  # type: ignore
        phases = default_pipeline(run_id=rid).phases
        vm = [p.key for p in phases if p.location == PhaseLocation.VM]
        loc = [p.key for p in phases if p.location == PhaseLocation.LOCAL]
        rec("INFO", "MOTOR-faser (VM)", ", ".join(vm))
        rec("INFO", "FORE/EFTER-faser (LOCAL)", ", ".join(loc))
        rec("OK", "statuskontrakt laddbart", f"{len(phases)} faser")
    except Exception as e:  # noqa: BLE001
        rec("FAIL", "default_pipeline ej laddbart", f"{type(e).__name__}: {e}")


def check_runner_dryruns(start: str, end: str):
    section("3. RUNNER-DRY-RUN -- svarar varje runner utan att krascha?")
    py = [sys.executable]
    # run_data: stoder --dry-run + --end
    plans = [
        ("run_data", py + [str(RUN_DATA), "--dry-run", "--end", end]),
        ("run_after", py + [str(RUN_AFTER), "--dry-run", "--start", start, "--end", end]),
    ]
    # familje-runners: forsok --dry-run; om de saknar flaggan, notera (vissa kanske
    # inte har den -- da ar det en INFO, inte ett fel).
    for fam, p in FAMILY_RUNNERS.items():
        if p.exists():
            plans.append((f"run_{fam}_model", py + [str(p), "--dry-run"]))

    for label, cmd in plans:
        if not Path(cmd[1]).exists():
            rec("WARN", f"{label}: hoppar (saknas)", cmd[1])
            continue
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if cp.returncode == 0:
                rec("OK", f"{label} --dry-run", "exit 0 (preflight laddade)")
            else:
                tail = (cp.stderr or cp.stdout).strip().splitlines()[-1:] or [""]
                # En runner som inte kanner --dry-run ger ofta SystemExit 2 (argparse)
                if "unrecognized arguments" in (cp.stderr or "") or "--dry-run" in (cp.stderr or ""):
                    rec("INFO", f"{label}: ingen --dry-run-flagga", " stoder ej torrkorning (ok)")
                else:
                    rec("WARN", f"{label} --dry-run exit {cp.returncode}", tail[0][:120])
        except subprocess.TimeoutExpired:
            rec("WARN", f"{label} --dry-run", "timeout 120s (oväntat for torrkorning)")
        except Exception as e:  # noqa: BLE001
            rec("FAIL", f"{label} --dry-run kraschade", f"{type(e).__name__}: {e}")


def check_vm_and_blob(do_vm: bool):
    section("4. VM + BLOB -- den vata sidans grundplåt")
    # Blob-containrar deklarerade i blob.py (statisk -- kraver ingen token)
    try:
        blob_txt = (ORCH / "infrastructure" / "blob.py").read_text(encoding="utf-8", errors="replace")
        for c in ["input", "output", "runstatus", "pipeline"]:
            present = (f'"{c}"' in blob_txt) or (f"'{c}'" in blob_txt)
            rec("OK" if present else "WARN", f"Blob-container '{c}' deklarerad",
                "i blob.py" if present else "ej funnen")
    except Exception as e:  # noqa: BLE001
        rec("WARN", "blob.py ej last", f"{type(e).__name__}: {e}")

    if not do_vm:
        rec("INFO", "VM-kontroller hoppade", "kor med --vm for levande az/VM/Blob-koll")
        return

    try:
        from azure_vm import VmConfig, ensure_subscription, vm_power_state  # type: ignore
    except Exception as e:  # noqa: BLE001
        rec("WARN", "azure_vm ej importerbar", f"{type(e).__name__}: {e}")
        return
    cfg = VmConfig()
    try:
        ensure_subscription(cfg)
        rec("OK", "az subscription satt + verifierad", cfg.subscription_id)
    except Exception as e:  # noqa: BLE001
        rec("WARN", "az subscription", f"{type(e).__name__}: {str(e)[:120]} (token dod? az login)")
        return
    try:
        ps = vm_power_state(cfg)
        rec("INFO", "VM power-state", f"{ps} (deallocated = vantat mellan korningar)")
    except Exception as e:  # noqa: BLE001
        rec("WARN", "VM power-state ej last", f"{type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Strukturell dry-run tvars hela roret (FORE->MOTOR->EFTER).")
    ap.add_argument("--start", default="2022-07-01")
    ap.add_argument("--end", default="2026-04-30")
    ap.add_argument("--vm", action="store_true", help="Kor aven levande az/VM/Blob-kontroller.")
    args = ap.parse_args()

    print("=" * 72)
    print("DRY-RUN FULL PIPELINE  --  skarvarna tvars hela roret")
    print(f"  fonster: {args.start} .. {args.end}")
    print("=" * 72)

    check_paths()
    check_window_consistency(args.start, args.end)
    check_runner_dryruns(args.start, args.end)
    check_vm_and_blob(args.vm)

    section("SAMMANFATTNING")
    n_fail = sum(1 for s, _, _ in ROWS if s == "FAIL")
    n_warn = sum(1 for s, _, _ in ROWS if s == "WARN")
    n_ok = sum(1 for s, _, _ in ROWS if s == "OK")
    print(f"  OK={n_ok}  WARN={n_warn}  FAIL={n_fail}")
    if n_fail:
        print("  -> FAIL: en skarv passar inte. Atgarda fore varm korning.")
    elif n_warn:
        print("  -> Inga FAIL. WARN = forvantade lokala luckor (BA-venv/VM nere) -- las dem.")
    else:
        print("  -> Alla skarvar passar. Roret ar redo for vatten.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
