"""
check_env.py - Environment check for BCG Pricing project (v3)
==============================================================
Author: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
Purpose: Full miljö-validering med ~50 kontroller fördelade på 9 grupper.
         Bygger förtroende inför beslutsfattare och eliminerar manuell
         pre-flight vid sessionsstart.

Kontrollgrupper:
  LOCAL          - Git, venvs, token, lokala filer, disk
  CODE_INTEGRITY - Hash kritiska Python-filer, sök misstänkta strängar
  CONFIG         - config.yml-konsistens, control_file/data/constants cross-check
  AZURE          - VM status, IP
  PIPELINE_DATA  - Datakvalitet i data_for_model.csv (NULL, kolumner, distribution)
  PIPELINE_CTX   - Baselines, smoke PoC, growing output
  HISTORY        - Arkiv-mappar, loggar, commit-historik
  STORAGE        - Caches, stora filer, hygien
  VM_INNER       - SSH-baserade VM-kontroller (kraver VM running)
  SUMMARY        - Räknad sammanställning
  EXECUTIVE      - Verbal sammanfattning

Auto-fix capability:
  - /tmp/ray_spill auto-skapas på VM om saknad

Usage:
    python check_env.py                # gratis, ~5 sek
    python check_env.py --vm-inner     # + SSH-baserade kontroller
    python check_env.py --json         # JSON för parsing
    python check_env.py --no-autofix   # skippa auto-fix
    python check_env.py --skip-data    # skippa CSV-läsning (snabbare)
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(r"C:\Projekt")
BCG_ROOT = PROJECT_ROOT / "BCG"
BA_ROOT = PROJECT_ROOT / "Business_Analytics"
CLUSTER_ROOT = BCG_ROOT / "Pipeline" / "02. Elasticity" / "2. Product Cluster Level Models"
PIPELINE_VENV = BCG_ROOT / "Pipeline" / "02. Elasticity" / ".venv" / "Scripts" / "python.exe"
BA_VENV = BA_ROOT / ".venv" / "Scripts" / "python.exe"
CLUSTER_CODE = CLUSTER_ROOT / "code"

VM_IP = "172.18.148.4"
VM_NAME = "bcg-poc-vm"
VM_RG = "ev-openai-swce-rg-test"
VM_SUBSCRIPTION = "ev-lz3-ai (SE)"

ARCHIVE_GROWING = CLUSTER_ROOT / "_archive_growing_2026-04-27"
ARCHIVE_FROZEN_LOCAL = CLUSTER_ROOT / "_backup_pre_growing_run_2026-06-01-1708"
SHARE_TO_CLAUDE = BCG_ROOT / "_share_to_claude"
SESSION_PREP = BCG_ROOT / "_session_prep"

# Expected data window for growing dataset
EXPECTED_WINDOW_START = "2022-07-01"
EXPECTED_WINDOW_END = "2026-04-27"
EXPECTED_PYTHON_VERSION = "3.11"

# Kritiska Python-filer (samma lista lokalt och pa VM)
CRITICAL_PYTHON_FILES = [
    "code/constants.py",
    "code/feature_selection.py",
    "code/model.py",
    "code/data_prepration.py",
    "code/regular_price.py",
]

# Misstänkta strängar som inte ska finnas i Linux-körda filer
SUSPICIOUS_PATTERNS = [
    ("C:\\\\",              "hardkodad Windows-stig", ["feature_selection.py", "model.py", "data_prepration.py"]),
    ("xlwings",             "xlwings (Windows-only)", ["feature_selection.py", "model.py", "data_prepration.py"]),
    ("import win32",        "win32-modul (Windows-only)", ["feature_selection.py", "model.py", "data_prepration.py"]),
]

# Förväntade kolumner i data_for_model.csv (kritiska för pipeline)
EXPECTED_DATA_COLS = [
    "KEY", "week_starting_monday", "QuantitySold(SalesTotal>0)",
    "PRICE", "ItemCode", "Cluster", "SoldQuantity", "TotalNet",
    "YOY_SEASONALITY", "Regular_Price_fwbw_max_6",
]

# Filer som ska upp till VM
LOCAL_FILES_REQUIRED = [
    {"path": ARCHIVE_GROWING / "data_for_model.csv",             "min_mb": 60,   "label": "data_for_model.csv (growing)"},
    {"path": ARCHIVE_GROWING / "data_original.csv",              "min_mb": 50,   "label": "data_original.csv (growing)"},
    {"path": CLUSTER_CODE / "control_files" / "control_file.xlsx",        "min_mb": 0.05, "label": "control_file.xlsx"},
    {"path": CLUSTER_CODE / "control_files" / "transform_control_TT.csv", "min_mb": 0,    "label": "transform_control_TT.csv"},
]

VM_FILES_REQUIRED = [
    ("~/bcg/cluster/output/data_for_model.csv",                   "data_for_model.csv on VM",      50 * 1024 * 1024),
    ("~/bcg/cluster/output/data_original.csv",                    "data_original.csv on VM",       40 * 1024 * 1024),
    ("~/bcg/cluster/code/control_files/control_file.xlsx",        "control_file.xlsx on VM",       50_000),
    ("~/bcg/cluster/code/control_files/transform_control_TT.csv", "transform_control_TT.csv VM",   100),
]

# =============================================================================
# Result infrastructure
# =============================================================================

@dataclass
class CheckResult:
    group: str
    name: str
    status: str   # PASS, WARN, FAIL, INFO, SKIP, FIXED
    detail: str = ""
    
    def to_dict(self):
        return asdict(self)


class CheckCollector:
    def __init__(self, json_output=False):
        self.results: List[CheckResult] = []
        self.json_output = json_output
        self._current_group = None
        self.context: Dict = {}
    
    def add(self, group: str, name: str, status: str, detail: str = ""):
        result = CheckResult(group=group, name=name, status=status, detail=detail)
        self.results.append(result)
        if not self.json_output:
            self._print(result)
    
    def set_context(self, key: str, value):
        self.context[key] = value
    
    def _print(self, r: CheckResult):
        if r.group != self._current_group:
            print()
            print(r.group)
            self._current_group = r.group
        icon = {
            "PASS":  "[PASS]", "WARN":  "[WARN]", "FAIL":  "[FAIL]",
            "INFO":  "[INFO]", "SKIP":  "[SKIP]", "FIXED": "[FIX] ",
        }.get(r.status, "[?]")
        print(f"  {icon:<8} {r.name:<34} {r.detail}")
    
    def summary(self):
        if self.json_output:
            print(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "checks": [r.to_dict() for r in self.results],
                "context": {k: (str(v) if not isinstance(v, (int, float, bool, str, list, dict)) else v)
                            for k, v in self.context.items()},
            }, indent=2, default=str))
            return
        
        n_pass  = sum(1 for r in self.results if r.status == "PASS")
        n_warn  = sum(1 for r in self.results if r.status == "WARN")
        n_fail  = sum(1 for r in self.results if r.status == "FAIL")
        n_info  = sum(1 for r in self.results if r.status == "INFO")
        n_skip  = sum(1 for r in self.results if r.status == "SKIP")
        n_fixed = sum(1 for r in self.results if r.status == "FIXED")
        total   = len(self.results)
        
        print()
        print("=" * 80)
        print(f"SUMMARY: {n_pass} PASS / {n_warn} WARN / {n_fail} FAIL / "
              f"{n_fixed} FIXED / {n_info} INFO / {n_skip} SKIP   (total {total})")
        print("=" * 80)
        
        problems = [r for r in self.results if r.status in ("WARN", "FAIL")]
        if problems:
            print()
            print("Saker att titta pa:")
            for p in problems:
                print(f"  [{p.status}]  {p.group} > {p.name}")
                if p.detail:
                    print(f"            {p.detail}")
        
        print()
        if n_fail > 0:
            print("STATUS: FAIL - atgarda problem innan pipeline-korning.")
        elif n_warn > 0:
            print("STATUS: WARN - redo men kolla varningar.")
        else:
            print("STATUS: ALLT GRONT - redo for pipeline-korning.")
    
    def executive_summary(self):
        if self.json_output:
            return
        
        c = self.context
        results = self.results
        n_fail = sum(1 for r in results if r.status == "FAIL")
        n_warn = sum(1 for r in results if r.status == "WARN")
        
        print()
        print("=" * 80)
        print("  EXECUTIVE SUMMARY")
        print("=" * 80)
        print()
        
        if n_fail == 0 and n_warn == 0:
            print("Status:  ALLA SYSTEM REDO for pipeline-korning pa Azure VM.")
        elif n_fail == 0:
            print(f"Status:  KLAR for korning, {n_warn} varning(ar) ej blockerande.")
        else:
            print(f"Status:  EJ KLAR - {n_fail} blockerande problem ({n_warn} varning(ar)).")
        print()
        
        # Fas F context
        print("Fas F (vaxande fonster, 2026-04-27):")
        if c.get("local_files_total_mb"):
            print(f"  v  Lokala filer redo for VM-upload: {c['local_files_total_mb']:.0f} MB i 4 filer")
        if c.get("control_file_keys"):
            print(f"  v  Control file: {c['control_file_keys']} KEY, RUN=YES={c.get('control_file_run_yes', '?')}")
        if c.get("data_window_min") and c.get("data_window_max"):
            print(f"  v  Datafonster: {c['data_window_min']} -> {c['data_window_max']} "
                  f"({c.get('data_window_weeks', '?')} veckor, {c.get('data_total_rows', '?')} rader)")
        if c.get("data_unique_keys") and c.get("control_file_keys") and c["data_unique_keys"] == c["control_file_keys"]:
            print(f"  v  KEY-konsistens: data ({c['data_unique_keys']}) = control_file ({c['control_file_keys']})")
        if c.get("code_files_clean"):
            print(f"  v  Code integrity: {c['code_files_clean']} kritiska Python-filer utan misstankta stragnar")
        if c.get("smoke_50_exists"):
            print("  v  Smoke 50 KEY: tidigare validerad pa vaxande fonster")
        if c.get("frozen_baseline_kb"):
            print(f"  v  Frusen baseline: output_summary.xlsx ({c['frozen_baseline_kb']:.1f} KB) arkiverad")
        print()
        
        # VM
        print("Azure VM:")
        vm_status = c.get("vm_power_state", "okand")
        if vm_status == "VM deallocated":
            print("  v  bcg-poc-vm deallocated (ingen kostnad)")
        elif vm_status == "VM running":
            print("  !  bcg-poc-vm running - kostnad tickar (~9 kr/h)")
        else:
            print(f"  ?  bcg-poc-vm status: {vm_status}")
        
        vm_inner_ran = any(r.group == "VM_INNER" for r in results)
        if vm_inner_ran:
            n_vm_fail = sum(1 for r in results if r.group == "VM_INNER" and r.status == "FAIL")
            if n_vm_fail == 0:
                print(f"  v  VM-inre: pipeline venv, G7-patch, code integrity, alla filer")
                if c.get("vm_ram_avail"):
                    print(f"  v  VM resurser: {c['vm_ram_avail']} RAM ledigt, {c.get('vm_disk_avail', '?')} disk")
            else:
                print(f"  !  VM-inre: {n_vm_fail} fel - se FAIL-lista")
            if c.get("autofix_ray_spill"):
                print("  i  /tmp/ray_spill skapades automatiskt (forsvinner vid VM-omstart)")
        else:
            print("  i  VM-inre ej kontrollerad (kor med -StartVm for fullkedja)")
        print()
        
        # Next step
        print("Nasta beslut:")
        if n_fail > 0:
            print("  Atgarda blockerande problem ovan, kor sedan check_env igen.")
        elif not vm_inner_ran:
            print("  Kor `.\\check_env.ps1 -StartVm` for fullkedja innan pipeline-korning.")
        elif vm_status == "VM running":
            print("  VM tickar kostnad. Deallocate snarast om inte pipeline kor nu.")
            print("    az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm")
        else:
            print("  Pipeline-korning pa VM. Forvantad tid: 60-75 min, kostnad: ~15 kr.")
            print("  Resultat: output_summary.xlsx for 1521 KEY pa vaxande fonster.")
        print()
        
        # Risks
        print("Kanda risker (fran tidigare sessioner):")
        print("  - Lokal 31 GB-maskin OOM:ade pa 50% av vaxande fonster (kan ej koras lokalt)")
        print("  - /tmp/ray_spill forsvinner vid VM-omstart (auto-fixas)")
        print("  - Azure-token gar ut efter 4h (E.3) - re-login vid behov")
        print()
        
        print("=" * 80)
    
    def has_fail(self) -> bool:
        return any(r.status == "FAIL" for r in self.results)


# =============================================================================
# Subprocess helpers
# =============================================================================

def run_cmd(cmd, timeout=30) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
        return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout after {timeout}s"
    except Exception as e:
        return -2, "", f"Exception: {e}"


def ssh_cmd(remote_cmd: str, timeout=30) -> Tuple[int, str, str]:
    return run_cmd(["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new",
                    f"azureuser@{VM_IP}", remote_cmd], timeout=timeout)


def az_cmd(args, timeout=30) -> Tuple[int, str, str]:
    az_exe = None
    for candidate in ["az.cmd", "az.bat", "az.exe", "az"]:
        found = shutil.which(candidate)
        if found:
            az_exe = found
            break
    if not az_exe:
        az_exe = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    try:
        result = subprocess.run([az_exe] + [str(a) for a in args],
                                capture_output=True, text=True, timeout=timeout, shell=False)
        return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout after {timeout}s"
    except Exception as e:
        return -2, "", f"Exception: {e}"


def file_md5(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# =============================================================================
# LOCAL checks
# =============================================================================

def check_local(cc: CheckCollector):
    group = "LOCAL"
    
    for repo_name, repo_path in [("evbcgpricing", BCG_ROOT), ("Business_Analytics", BA_ROOT)]:
        if not repo_path.exists():
            cc.add(group, f"Repo {repo_name}", "FAIL", f"saknas: {repo_path}")
            continue
        rc, branch, _ = run_cmd(["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"])
        rc_sha, sha, _ = run_cmd(["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"])
        rc_st, status_out, _ = run_cmd(["git", "-C", str(repo_path), "status", "--porcelain"])
        
        if rc != 0 or rc_st != 0:
            cc.add(group, f"Repo {repo_name}", "FAIL", "git failade")
            continue
        
        modified_count = len([l for l in status_out.split("\n") if l.strip()])
        sha_disp = sha if rc_sha == 0 else "?"
        cc.set_context(f"git_{repo_name}_sha", sha_disp)
        cc.set_context(f"git_{repo_name}_branch", branch)
        
        if modified_count == 0:
            cc.add(group, f"Repo {repo_name}", "PASS", f"branch {branch} @ {sha_disp}, clean")
        else:
            cc.add(group, f"Repo {repo_name}", "WARN", f"branch {branch} @ {sha_disp}, {modified_count} andrade")
    
    # Pipeline venv
    if not PIPELINE_VENV.exists():
        cc.add(group, "Pipeline venv", "FAIL", f"saknas: {PIPELINE_VENV}")
    else:
        rc, ver, _ = run_cmd([str(PIPELINE_VENV), "--version"], timeout=10)
        rc2, _, err2 = run_cmd([str(PIPELINE_VENV), "-c", "import ray, statsmodels, pandas"], timeout=15)
        if rc == 0 and rc2 == 0:
            cc.add(group, "Pipeline venv", "PASS", f"{ver}, ray+statsmodels OK")
            cc.set_context("local_python_version", ver)
        else:
            cc.add(group, "Pipeline venv", "FAIL", f"problem: {err2[:80]}")
    
    # Business_Analytics venv
    if not BA_VENV.exists():
        cc.add(group, "Business venv", "WARN", "saknas (behovs ej for pipeline)")
    else:
        rc, ver, _ = run_cmd([str(BA_VENV), "--version"], timeout=10)
        rc2, _, err2 = run_cmd([str(BA_VENV), "-c", "import pyodbc, pandas"], timeout=15)
        if rc == 0 and rc2 == 0:
            cc.add(group, "Business venv", "PASS", f"{ver}, pyodbc OK")
        else:
            cc.add(group, "Business venv", "WARN", f"problem: {err2[:80]}")
    
    # Azure token
    rc, sub, _ = az_cmd(["account", "show", "--query", "name", "-o", "tsv"], timeout=15)
    if rc == 0 and sub:
        if VM_SUBSCRIPTION in sub:
            cc.add(group, "Azure token (mgmt)", "PASS", f"aktiv: {sub}")
        else:
            cc.add(group, "Azure token (mgmt)", "WARN", f"fel sub: {sub}")
    else:
        cc.add(group, "Azure token (mgmt)", "FAIL", "kor: az login --scope https://management.core.windows.net//.default")
    
    # Lokala filer
    total_mb = 0
    for f in LOCAL_FILES_REQUIRED:
        if not f["path"].exists():
            cc.add(group, f["label"], "FAIL", f"saknas")
        else:
            mb = f["path"].stat().st_size / (1024 * 1024)
            total_mb += mb
            if mb < f["min_mb"]:
                cc.add(group, f["label"], "WARN", f"{mb:.1f} MB (under {f['min_mb']})")
            else:
                cc.add(group, f["label"], "PASS", f"{mb:.1f} MB")
    cc.set_context("local_files_total_mb", total_mb)
    
    # control_file innehåll
    cf = CLUSTER_CODE / "control_files" / "control_file.xlsx"
    if cf.exists() and PIPELINE_VENV.exists():
        code = "import pandas as pd; df = pd.read_excel(r'" + str(cf) + "'); print(len(df), (df['RUN']=='YES').sum())"
        rc, out, _ = run_cmd([str(PIPELINE_VENV), "-c", code], timeout=30)
        if rc == 0 and out:
            parts = out.split()
            if len(parts) >= 2:
                total, run_yes = int(parts[0]), int(parts[1])
                cc.set_context("control_file_keys", total)
                cc.set_context("control_file_run_yes", run_yes)
                if total == run_yes and total > 100:
                    cc.add(group, "control_file content", "PASS", f"KEY={total}, RUN=YES={run_yes}")
                elif total > 100 and run_yes < 100:
                    cc.add(group, "control_file content", "WARN", f"KEY={total}, RUN=YES={run_yes} (smoke?)")
                else:
                    cc.add(group, "control_file content", "WARN", f"KEY={total}, RUN=YES={run_yes}")
    
    # Disk C:
    try:
        free_gb = shutil.disk_usage("C:\\").free / (1024**3)
        if free_gb < 10:
            cc.add(group, "Disk C: ledigt", "FAIL", f"{free_gb:.1f} GB (kritiskt lagt)")
        elif free_gb < 20:
            cc.add(group, "Disk C: ledigt", "WARN", f"{free_gb:.1f} GB (lagt for Ray-spill)")
        else:
            cc.add(group, "Disk C: ledigt", "PASS", f"{free_gb:.1f} GB")
    except Exception as e:
        cc.add(group, "Disk C: ledigt", "WARN", f"kunde inte mata: {e}")
    
    # _archive_growing
    if ARCHIVE_GROWING.exists():
        file_count = sum(1 for f in ARCHIVE_GROWING.rglob("*") if f.is_file())
        cc.add(group, "_archive_growing", "PASS", f"finns, {file_count} filer")
    else:
        cc.add(group, "_archive_growing", "FAIL", "saknas")
    
    # _share_to_claude
    if SHARE_TO_CLAUDE.exists():
        size_mb = sum(f.stat().st_size for f in SHARE_TO_CLAUDE.rglob("*") if f.is_file()) / (1024 * 1024)
        if size_mb > 100:
            cc.add(group, "_share_to_claude", "WARN", f"{size_mb:.0f} MB - kan stadas")
        else:
            cc.add(group, "_share_to_claude", "INFO", f"finns ({size_mb:.1f} MB)")
    
    if SESSION_PREP.exists():
        cc.add(group, "_session_prep", "PASS", "finns (verktygets hem)")


# =============================================================================
# CODE_INTEGRITY checks (A)
# =============================================================================

def check_code_integrity(cc: CheckCollector) -> Dict[str, str]:
    """Returnerar dict med {filename: md5} for kritiska filer (anvands for VM-jamforelse)."""
    group = "CODE_INTEGRITY"
    local_hashes: Dict[str, str] = {}
    
    # Hasha kritiska Python-filer lokalt
    for rel_path in CRITICAL_PYTHON_FILES:
        local_file = CLUSTER_ROOT / rel_path
        if local_file.exists():
            md5 = file_md5(local_file)
            local_hashes[rel_path] = md5
            cc.add(group, f"Hash {Path(rel_path).name}", "PASS", f"md5 {md5[:12]}...")
        else:
            cc.add(group, f"Hash {Path(rel_path).name}", "WARN", "fil saknas lokalt")
    
    # Misstankta strangar i Linux-korda filer
    clean_files = 0
    for pattern, desc, files in SUSPICIOUS_PATTERNS:
        for filename in files:
            local_file = CLUSTER_CODE / filename
            if not local_file.exists():
                continue
            try:
                content = local_file.read_text(encoding="utf-8", errors="ignore")
                if pattern.replace("\\\\", "\\") in content:
                    cc.add(group, f"{filename}: {desc}", "WARN", f"hittade '{pattern}' i koden")
                else:
                    clean_files += 1
            except Exception as e:
                cc.add(group, f"{filename}: {desc}", "WARN", f"kunde inte lasa: {e}")
    
    cc.set_context("code_files_clean", clean_files)
    if clean_files > 0:
        cc.add(group, "Misstankta strangar", "PASS",
               f"{clean_files} fil/monster-kombinationer rena")
    
    cc.set_context("local_file_hashes", local_hashes)
    return local_hashes


# =============================================================================
# CONFIG checks (B)
# =============================================================================

def check_config(cc: CheckCollector):
    group = "CONFIG"
    
    # config.yml existens + KEY-tomma sektioner (L.39 - dead config)
    config_yml = CLUSTER_CODE / "src" / "config.yml"
    if not config_yml.exists():
        config_yml = CLUSTER_CODE / "config.yml"
    
    if config_yml.exists():
        try:
            content = config_yml.read_text(encoding="utf-8", errors="ignore")
            # Räkna nycklar
            top_keys = [l.split(":")[0].strip() for l in content.split("\n")
                        if l and not l.startswith(" ") and not l.startswith("#") and ":" in l]
            cc.add(group, "config.yml", "PASS", f"finns, {len(top_keys)} top-level nycklar")
            
            # Flagga dead config (kanda L.39-fall)
            dead_keys = ["competitor_data", "InScope_Mapping", "inscope_mapping"]
            for dk in dead_keys:
                if dk.lower() in content.lower():
                    cc.add(group, f"Dead config: {dk}", "INFO",
                           "deklarerad i config men oanvand av koden (L.39)")
        except Exception as e:
            cc.add(group, "config.yml", "WARN", f"lasfel: {e}")
    else:
        cc.add(group, "config.yml", "WARN", "saknas")
    
    # Cross-check: data_for_model.csv KEY == control_file KEY
    cf_keys = cc.context.get("control_file_keys")
    data_keys = cc.context.get("data_unique_keys")
    if cf_keys and data_keys:
        if cf_keys == data_keys:
            cc.add(group, "KEY-konsistens (cf vs data)", "PASS",
                   f"control_file={cf_keys}, data={data_keys}")
        else:
            cc.add(group, "KEY-konsistens (cf vs data)", "FAIL",
                   f"control_file={cf_keys}, data={data_keys}")
    
    # Konfig-fil transform_control_TT.csv struktur
    tt = CLUSTER_CODE / "control_files" / "transform_control_TT.csv"
    if tt.exists():
        try:
            content = tt.read_text(encoding="utf-8", errors="ignore")
            lines = content.strip().split("\n")
            if len(lines) >= 2:
                cc.add(group, "transform_control_TT", "PASS", f"{len(lines)} rader")
            else:
                cc.add(group, "transform_control_TT", "WARN", "tom eller minimal")
        except Exception:
            cc.add(group, "transform_control_TT", "WARN", "lasfel")


# =============================================================================
# AZURE checks
# =============================================================================

def check_azure(cc: CheckCollector) -> Optional[str]:
    group = "AZURE"
    
    rc, status, err = az_cmd([
        "vm", "get-instance-view",
        "--resource-group", VM_RG, "--name", VM_NAME,
        "--query", "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus",
        "--output", "tsv"
    ], timeout=30)
    
    if rc != 0:
        cc.add(group, f"VM {VM_NAME}", "FAIL", f"status okand: {err[:80]}")
        return None
    
    cc.set_context("vm_power_state", status)
    
    if status == "VM deallocated":
        cc.add(group, f"VM {VM_NAME}", "PASS", "deallocated (ingen kostnad)")
    elif status == "VM running":
        cc.add(group, f"VM {VM_NAME}", "WARN", "running - kostnad tickar (~9 kr/h)")
    elif status == "VM stopped":
        cc.add(group, f"VM {VM_NAME}", "WARN", "stopped (allokerad, tickar kostnad)")
    else:
        cc.add(group, f"VM {VM_NAME}", "WARN", f"status: {status}")
    
    rc, ip, _ = az_cmd([
        "vm", "list-ip-addresses",
        "--resource-group", VM_RG, "--name", VM_NAME,
        "--query", "[0].virtualMachine.network.privateIpAddresses[0]",
        "--output", "tsv"
    ], timeout=30)
    
    if rc == 0 and ip:
        if ip == VM_IP:
            cc.add(group, "VM IP", "PASS", ip)
        else:
            cc.add(group, "VM IP", "WARN", f"{ip} (vantat: {VM_IP})")
    
    return status


# =============================================================================
# PIPELINE_DATA checks (C)
# =============================================================================

def check_pipeline_data(cc: CheckCollector, skip_data: bool = False):
    group = "PIPELINE_DATA"
    
    dfm = ARCHIVE_GROWING / "data_for_model.csv"
    if not dfm.exists():
        cc.add(group, "data_for_model.csv", "SKIP", "filen saknas - ej koppling till PIPELINE_DATA")
        return
    
    if skip_data:
        cc.add(group, "data_for_model.csv", "SKIP", "skippas (--skip-data)")
        return
    
    if not PIPELINE_VENV.exists():
        cc.add(group, "data_for_model.csv", "SKIP", "pipeline venv saknas")
        return
    
    # En tung lasning: hamta alla relevanta metrics i ett anrop
    code = f"""
import pandas as pd
df = pd.read_csv(r'{dfm}', usecols=[
    'KEY', 'week_starting_monday',
    'QuantitySold(SalesTotal>0)', 'PRICE',
    'SoldQuantity', 'TotalNet', 'YOY_SEASONALITY'
], parse_dates=['week_starting_monday'], low_memory=False, on_bad_lines='skip')
print('TOTAL_ROWS|' + str(len(df)))
print('UNIQUE_KEYS|' + str(df['KEY'].nunique()))
print('WEEK_MIN|' + str(df['week_starting_monday'].min().date()))
print('WEEK_MAX|' + str(df['week_starting_monday'].max().date()))
print('UNIQUE_WEEKS|' + str(df['week_starting_monday'].nunique()))
print('NULL_KEY|' + str(df['KEY'].isnull().sum()))
print('NULL_WEEK|' + str(df['week_starting_monday'].isnull().sum()))
print('NULL_QTY|' + str(df['QuantitySold(SalesTotal>0)'].isnull().sum()))
print('NULL_PRICE|' + str(df['PRICE'].isnull().sum()))
print('NULL_TOTALNET|' + str(df['TotalNet'].isnull().sum()))
print('NULL_SOLDQTY|' + str(df['SoldQuantity'].isnull().sum()))
print('NULL_YOY_SEASON|' + str(df['YOY_SEASONALITY'].isnull().sum()))
"""
    rc, out, err = run_cmd([str(PIPELINE_VENV), "-c", code], timeout=120)
    if rc != 0 or not out:
        cc.add(group, "data_for_model.csv", "WARN", f"kunde inte parsas: {err[:80]}")
        return
    
    facts = {}
    for line in out.split("\n"):
        if "|" in line:
            k, v = line.split("|", 1)
            facts[k.strip()] = v.strip()
    
    # Total rader
    try:
        total = int(facts.get("TOTAL_ROWS", "0"))
        cc.set_context("data_total_rows", total)
        if total > 100_000:
            cc.add(group, "Totalt rader", "PASS", f"{total:,}")
        else:
            cc.add(group, "Totalt rader", "WARN", f"{total:,} (forvantat 200k+)")
    except ValueError:
        pass
    
    # Unika KEY
    try:
        n_keys = int(facts.get("UNIQUE_KEYS", "0"))
        cc.set_context("data_unique_keys", n_keys)
        cf_keys = cc.context.get("control_file_keys")
        if cf_keys and n_keys == cf_keys:
            cc.add(group, "Unika KEY", "PASS", f"{n_keys} (matchar control_file)")
        elif cf_keys:
            cc.add(group, "Unika KEY", "WARN", f"{n_keys} (control_file: {cf_keys})")
        else:
            cc.add(group, "Unika KEY", "INFO", str(n_keys))
    except ValueError:
        pass
    
    # Datafonster
    wmin, wmax = facts.get("WEEK_MIN"), facts.get("WEEK_MAX")
    n_weeks = facts.get("UNIQUE_WEEKS")
    if wmin and wmax:
        cc.set_context("data_window_min", wmin)
        cc.set_context("data_window_max", wmax)
        cc.set_context("data_window_weeks", int(n_weeks) if n_weeks else 0)
        if wmax >= EXPECTED_WINDOW_END[:7]:
            cc.add(group, "Datafonster", "PASS", f"{wmin} -> {wmax} ({n_weeks} veckor)")
        else:
            cc.add(group, "Datafonster", "WARN",
                   f"{wmin} -> {wmax} (forvantat slut {EXPECTED_WINDOW_END})")
    
    # NULL-rakning i kritiska kolumner
    for label, key in [
        ("NULL KEY", "NULL_KEY"),
        ("NULL week_starting", "NULL_WEEK"),
        ("NULL QuantitySold(SalesTotal>0)", "NULL_QTY"),
        ("NULL PRICE", "NULL_PRICE"),
        ("NULL SoldQuantity", "NULL_SOLDQTY"),
        ("NULL TotalNet", "NULL_TOTALNET"),
        ("NULL YOY_SEASONALITY", "NULL_YOY_SEASON"),
    ]:
        try:
            n_null = int(facts.get(key, "0"))
            if n_null == 0:
                cc.add(group, label, "PASS", "0 NULL")
            elif n_null < 1000:
                cc.add(group, label, "INFO", f"{n_null} NULL (lagt antal)")
            else:
                cc.add(group, label, "WARN", f"{n_null} NULL")
        except ValueError:
            pass
    
    # Kolumnlista — verifiera att alla forvantade finns
    code2 = f"import pandas as pd; df = pd.read_csv(r'{dfm}', nrows=1); print(','.join(df.columns))"
    rc2, out2, _ = run_cmd([str(PIPELINE_VENV), "-c", code2], timeout=30)
    if rc2 == 0 and out2:
        cols = set(c.strip() for c in out2.split(","))
        missing = [c for c in EXPECTED_DATA_COLS if c not in cols]
        if not missing:
            cc.add(group, "Forvantade kolumner", "PASS", f"alla {len(EXPECTED_DATA_COLS)} finns")
        else:
            cc.add(group, "Forvantade kolumner", "WARN", f"saknas: {', '.join(missing)}")
        cc.add(group, "Antal kolumner totalt", "INFO", f"{len(cols)}")


# =============================================================================
# PIPELINE_CTX checks
# =============================================================================

def check_pipeline_context(cc: CheckCollector):
    group = "PIPELINE_CTX"
    
    if ARCHIVE_FROZEN_LOCAL.exists():
        os_file = ARCHIVE_FROZEN_LOCAL / "output_summary.xlsx"
        if os_file.exists():
            info = os_file.stat()
            kb = info.st_size / 1024
            cc.add(group, "Frozen baseline", "PASS",
                   f"output_summary.xlsx {kb:.1f} KB, {datetime.fromtimestamp(info.st_mtime):%Y-%m-%d}")
            cc.set_context("frozen_baseline_kb", kb)
        else:
            cc.add(group, "Frozen baseline", "WARN", "output_summary.xlsx saknas i arkivet")
    else:
        cc.add(group, "Frozen baseline", "WARN", "frusen-arkiv saknas lokalt")
    
    smoke = ARCHIVE_GROWING / "smoke_50KEY_finalized.csv"
    if smoke.exists():
        info = smoke.stat()
        kb = info.st_size / 1024
        cc.add(group, "Smoke 50 KEY (PoC)", "PASS", f"{kb:.1f} KB - vaxande fonster bevisat")
        cc.set_context("smoke_50_exists", True)
    
    growing_os = ARCHIVE_GROWING / "output_summary.xlsx"
    if growing_os.exists():
        info = growing_os.stat()
        kb = info.st_size / 1024
        cc.add(group, "Growing output", "PASS", f"{kb:.1f} KB - VM-korning klar")
    else:
        cc.add(group, "Growing output", "INFO", "ej producerad annu")


# =============================================================================
# HISTORY checks (D)
# =============================================================================

def check_history(cc: CheckCollector):
    group = "HISTORY"
    
    # Alla _archive_-mappar
    archive_dirs = list(CLUSTER_ROOT.glob("_archive_*"))
    for d in archive_dirs:
        if d.is_dir():
            n_files = sum(1 for f in d.rglob("*") if f.is_file())
            size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024 * 1024)
            cc.add(group, f"Archive: {d.name}", "INFO", f"{n_files} filer, {size_mb:.0f} MB")
    
    # Alla _backup_-mappar
    backup_dirs = list(CLUSTER_ROOT.glob("_backup_*"))
    for d in backup_dirs:
        if d.is_dir():
            n_files = sum(1 for f in d.rglob("*") if f.is_file())
            size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024 * 1024)
            cc.add(group, f"Backup: {d.name}", "INFO", f"{n_files} filer, {size_mb:.0f} MB")
    
    # Loggar i _run_logs/
    log_dir = CLUSTER_ROOT / "_run_logs"
    if log_dir.exists():
        logs = list(log_dir.glob("*.log"))
        if logs:
            cc.add(group, "Run logs", "PASS", f"{len(logs)} loggar")
        else:
            cc.add(group, "Run logs", "INFO", "mapp finns men tom")
    
    # Senaste commit-meddelanden (BCG)
    rc, out, _ = run_cmd(["git", "-C", str(BCG_ROOT), "log", "--oneline", "-3"], timeout=10)
    if rc == 0 and out:
        for i, line in enumerate(out.split("\n")[:3], 1):
            cc.add(group, f"BCG commit -{i}", "INFO", line[:70])


# =============================================================================
# STORAGE checks (E)
# =============================================================================

def check_storage(cc: CheckCollector):
    group = "STORAGE"
    
    # __pycache__ totalt
    cache_size_mb = 0
    cache_count = 0
    for cache_dir in BCG_ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            cache_count += 1
            for f in cache_dir.rglob("*"):
                if f.is_file():
                    cache_size_mb += f.stat().st_size / (1024 * 1024)
    if cache_count > 0:
        if cache_size_mb > 50:
            cc.add(group, "__pycache__ totalt", "INFO",
                   f"{cache_count} mappar, {cache_size_mb:.0f} MB (kan stadas)")
        else:
            cc.add(group, "__pycache__ totalt", "INFO",
                   f"{cache_count} mappar, {cache_size_mb:.1f} MB")
    
    # Stora filer (>100 MB) som inte ar i _archive_/_backup_
    big_files = []
    for f in CLUSTER_ROOT.rglob("*"):
        if not f.is_file():
            continue
        # Skippa filer i arkiv/backup-mappar
        rel_parts = f.relative_to(CLUSTER_ROOT).parts
        if any(p.startswith("_archive_") or p.startswith("_backup_") for p in rel_parts):
            continue
        try:
            size_mb = f.stat().st_size / (1024 * 1024)
            if size_mb > 100:
                big_files.append((f.name, size_mb))
        except (OSError, PermissionError):
            continue
    
    if big_files:
        cc.add(group, "Stora filer (>100MB) utanfor arkiv", "WARN",
               f"{len(big_files)} st: " + ", ".join(f"{n} ({s:.0f}MB)" for n, s in big_files[:3]))
    else:
        cc.add(group, "Stora filer (>100MB) utanfor arkiv", "PASS", "inga")
    
    # Backup-filer (.bak) löst i koden
    bak_files = list(CLUSTER_CODE.rglob("*.bak*"))
    if bak_files:
        cc.add(group, "Backup-filer i kod", "WARN",
               f"{len(bak_files)} st - ev rensa")
    else:
        cc.add(group, "Backup-filer i kod", "PASS", "inga")


# =============================================================================
# VM_INNER checks
# =============================================================================

def check_vm_inner(cc: CheckCollector, autofix: bool = True,
                   local_hashes: Optional[Dict[str, str]] = None):
    group = "VM_INNER"
    
    rc, out, err = ssh_cmd("echo SSH_OK", timeout=15)
    if rc != 0 or "SSH_OK" not in out:
        cc.add(group, "SSH connectivity", "FAIL", f"misslyckades: {err[:80]}")
        return
    cc.add(group, "SSH connectivity", "PASS", "OK")
    
    # Pipeline venv
    rc, ver, _ = ssh_cmd("~/bcg/cluster/.venv/bin/python --version", timeout=15)
    rc2, _, err2 = ssh_cmd("~/bcg/cluster/.venv/bin/python -c 'import ray, statsmodels, pandas'", timeout=20)
    if rc == 0 and rc2 == 0:
        cc.add(group, "VM pipeline venv", "PASS", f"{ver}, ray+statsmodels OK")
        cc.set_context("vm_python_version", ver)
        # Cross-check Python version vs lokal
        local_ver = cc.context.get("local_python_version", "")
        if local_ver and ver and local_ver.split()[1].split(".")[:2] == ver.split()[1].split(".")[:2]:
            cc.add(group, "Python-version match", "PASS",
                   f"lokal={local_ver} == VM={ver} (major.minor)")
        elif local_ver:
            cc.add(group, "Python-version match", "WARN",
                   f"lokal={local_ver} vs VM={ver}")
    else:
        cc.add(group, "VM pipeline venv", "FAIL", f"import-fel: {err2[:80]}")
    
    # constants.py G7 - test override
    rc, out, _ = ssh_cmd("grep -c 'os.environ.get' ~/bcg/cluster/code/constants.py", timeout=10)
    if rc == 0 and out.strip().isdigit() and int(out.strip()) >= 2:
        rc2, out2, _ = ssh_cmd(
            "cd ~/bcg/cluster/code && BCG_END_DATE=2026-04-27 ~/bcg/cluster/.venv/bin/python "
            "-c 'import constants; print(constants.END_DATE, constants.END_DATE2)'", timeout=15)
        if rc2 == 0 and "2026-04-27" in out2 and "2026-04-28" in out2:
            cc.add(group, "constants.py G7", "PASS", "env-override fungerar")
        else:
            cc.add(group, "constants.py G7", "FAIL", f"override-test misslyckades: {out2[:80]}")
    else:
        cc.add(group, "constants.py G7", "FAIL", "ej patchad")
    
    # Code integrity: hash kritiska filer pa VM, jamfor med lokala
    if local_hashes:
        for rel_path, local_md5 in local_hashes.items():
            if local_md5 is None:
                continue
            vm_path = f"~/bcg/cluster/{rel_path}"
            rc, out, _ = ssh_cmd(f"md5sum {vm_path} 2>/dev/null | awk '{{print $1}}'", timeout=15)
            if rc == 0 and out and out.strip():
                vm_md5 = out.strip()
                if vm_md5 == local_md5:
                    cc.add(group, f"VM hash {Path(rel_path).name}", "PASS",
                           f"matchar lokalt ({vm_md5[:12]}...)")
                else:
                    # Specialfall: constants.py forvantas skilja sig (G7-patch pa VM)
                    if "constants.py" in rel_path:
                        cc.add(group, f"VM hash {Path(rel_path).name}", "INFO",
                               f"skiljer (forvantat: G7-patch pa VM)")
                    else:
                        cc.add(group, f"VM hash {Path(rel_path).name}", "WARN",
                               f"divergerar: lokal={local_md5[:12]}, VM={vm_md5[:12]}")
            else:
                cc.add(group, f"VM hash {Path(rel_path).name}", "WARN", "kunde inte hash:a")
    
    # /tmp/ray_spill med auto-fix
    rc, out, _ = ssh_cmd("test -d /tmp/ray_spill && echo OK || echo MISSING", timeout=10)
    if "OK" in out:
        cc.add(group, "/tmp/ray_spill", "PASS", "finns")
    else:
        if autofix:
            rc_fix, _, err_fix = ssh_cmd("mkdir -p /tmp/ray_spill && echo CREATED", timeout=10)
            if rc_fix == 0:
                cc.add(group, "/tmp/ray_spill", "FIXED",
                       "saknades, skapad (forsvinner vid VM-omstart)")
                cc.set_context("autofix_ray_spill", True)
            else:
                cc.add(group, "/tmp/ray_spill", "FAIL",
                       f"saknas, auto-fix failade: {err_fix[:80]}")
        else:
            cc.add(group, "/tmp/ray_spill", "FAIL",
                   "saknas (kor utan --no-autofix)")
    
    # ray_spill-stig i feature_selection.py
    rc, out, _ = ssh_cmd("grep -c '/tmp/ray_spill' ~/bcg/cluster/code/feature_selection.py", timeout=10)
    if rc == 0 and out.strip().isdigit() and int(out.strip()) >= 1:
        rc2, out2, _ = ssh_cmd("grep -c 'C:..ray_spill' ~/bcg/cluster/code/feature_selection.py", timeout=10)
        if rc2 == 0 and out2.strip() == "0":
            cc.add(group, "ray_spill in code", "PASS", "Linux-stig (CZ.5 fixed)")
        else:
            cc.add(group, "ray_spill in code", "WARN", "bade Linux och Windows-stig")
    else:
        cc.add(group, "ray_spill in code", "FAIL", "ingen /tmp/ray_spill-referens")
    
    # Misstankta strangar i Linux-korda filer pa VM
    for pattern, desc, files in SUSPICIOUS_PATTERNS:
        # bygg ett enda grep-kommando over alla filerna
        files_paths = " ".join(f"~/bcg/cluster/code/{f}" for f in files)
        rc, out, _ = ssh_cmd(f"grep -l '{pattern}' {files_paths} 2>/dev/null | wc -l", timeout=15)
        if rc == 0 and out.strip().isdigit():
            n_hits = int(out.strip())
            if n_hits == 0:
                cc.add(group, f"VM: ingen {desc}", "PASS", f"i {len(files)} filer")
            else:
                cc.add(group, f"VM: hitta {desc}", "WARN", f"i {n_hits} fil(er)")
    
    # Filer pa VM
    for vm_path, label, min_bytes in VM_FILES_REQUIRED:
        rc, out, _ = ssh_cmd(f"test -f {vm_path} && stat -c %s {vm_path} || echo MISSING", timeout=10)
        if "MISSING" in out:
            cc.add(group, label, "FAIL", "saknas")
        else:
            try:
                size = int(out.strip())
                if size < min_bytes:
                    cc.add(group, label, "WARN", f"{size/1024/1024:.1f} MB (under {min_bytes/1024/1024:.0f})")
                else:
                    cc.add(group, label, "PASS", f"{size/1024/1024:.1f} MB")
            except ValueError:
                cc.add(group, label, "WARN", out[:50])
    
    # Cross-check VM control_file KEY-count
    rc, out, _ = ssh_cmd(
        "~/bcg/cluster/.venv/bin/python -c \""
        "import pandas as pd; "
        "df = pd.read_excel('/home/azureuser/bcg/cluster/code/control_files/control_file.xlsx'); "
        "print(len(df), (df['RUN']=='YES').sum())\"", timeout=30)
    if rc == 0 and out:
        parts = out.split()
        if len(parts) >= 2:
            vm_keys, vm_yes = int(parts[0]), int(parts[1])
            cf_keys_local = cc.context.get("control_file_keys")
            if cf_keys_local and vm_keys == cf_keys_local:
                cc.add(group, "VM control_file", "PASS",
                       f"KEY={vm_keys}, RUN=YES={vm_yes} (matchar lokalt)")
            elif cf_keys_local:
                cc.add(group, "VM control_file", "WARN",
                       f"VM KEY={vm_keys} vs lokal={cf_keys_local}")
            else:
                cc.add(group, "VM control_file", "INFO",
                       f"KEY={vm_keys}, RUN=YES={vm_yes}")
    
    # Frozen archive pa VM
    rc, out, _ = ssh_cmd(
        "test -d ~/bcg/cluster/_archive_frozen_2026-05-26 && "
        "ls ~/bcg/cluster/_archive_frozen_2026-05-26 | wc -l || echo MISSING", timeout=10)
    if "MISSING" in out:
        cc.add(group, "Frozen archive on VM", "WARN",
               "saknas (tidigare resultat ej arkiverade)")
    else:
        try:
            count = int(out.strip())
            cc.add(group, "Frozen archive on VM", "PASS", f"{count} filer")
        except ValueError:
            pass
    
    # Senaste filändring i output/
    rc, out, _ = ssh_cmd(
        "find ~/bcg/cluster/output -maxdepth 2 -type f -printf '%T@ %p\\n' "
        "2>/dev/null | sort -rn | head -1 | awk '{print $2}'", timeout=10)
    if rc == 0 and out:
        rc2, mtime, _ = ssh_cmd(f"stat -c '%y' {out}", timeout=10)
        if rc2 == 0 and mtime:
            cc.add(group, "Senaste output-fil", "INFO",
                   f"{mtime[:19]} ({Path(out).name})")
    
    # System resources
    rc, out, _ = ssh_cmd("free -h | awk 'NR==2 {print $7}'", timeout=10)
    if rc == 0 and out:
        cc.add(group, "VM RAM ledigt", "INFO", out.strip())
        cc.set_context("vm_ram_avail", out.strip())
    
    rc, out, _ = ssh_cmd("df -h / | awk 'NR==2 {print $4}'", timeout=10)
    if rc == 0 and out:
        cc.add(group, "VM disk ledigt (/)", "INFO", out.strip())
        cc.set_context("vm_disk_avail", out.strip())
    
    rc, out, _ = ssh_cmd("df -h /tmp | awk 'NR==2 {print $4}'", timeout=10)
    if rc == 0 and out:
        cc.add(group, "VM /tmp ledigt", "INFO", out.strip())


# =============================================================================
# Main
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="Environment check for BCG Pricing project (v3)")
    ap.add_argument("--vm-inner", action="store_true", help="Inkludera VM-inre kontroller")
    ap.add_argument("--json", action="store_true", help="JSON-output")
    ap.add_argument("--no-autofix", action="store_true", help="Skippa auto-fix")
    ap.add_argument("--skip-data", action="store_true", help="Skippa CSV-läsning (snabbare)")
    args = ap.parse_args()
    
    cc = CheckCollector(json_output=args.json)
    
    if not args.json:
        print("=" * 80)
        print(f"  BCG Pipeline Environment Check v3  -  {datetime.now():%Y-%m-%d %H:%M:%S}")
        print("=" * 80)
    
    check_local(cc)
    local_hashes = check_code_integrity(cc)
    check_config(cc)
    vm_state = check_azure(cc)
    check_pipeline_data(cc, skip_data=args.skip_data)
    check_pipeline_context(cc)
    check_history(cc)
    check_storage(cc)
    
    if args.vm_inner:
        if vm_state == "VM running":
            check_vm_inner(cc, autofix=not args.no_autofix, local_hashes=local_hashes)
        else:
            cc.add("VM_INNER", "VM check", "SKIP",
                   f"VM ar {vm_state}, ej running")
    
    cc.summary()
    cc.executive_summary()
    
    return 1 if cc.has_fail() else 0


if __name__ == "__main__":
    sys.exit(main())
