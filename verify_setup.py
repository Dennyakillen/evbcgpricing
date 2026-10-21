#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
verify_setup.py — kontroll att BCG Pricing (evbcgpricing) är korrekt uppsatt lokalt (rapporterande grind).

Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB).

Kontrakt: MASTER_INSTALL §3. Mall: Scraping_VetPris verify_setup.py (2026-10-19). Samma skript körs av
install.py (sist), av ägaren vid behov och i kallstarten — en kallstart ska inte ha en egen, svagare kontroll.

Kör från repo-roten i repots .venv:
    .\.venv\Scripts\python.exe verify_setup.py      (eller: python verify_setup.py med aktiverad .venv)

Prövar, i ordning:
  1. Python-version och att det är DETTA repos .venv som kör.
  2. Kallstart-vakten: att modulerna som importeras (run_status, blob, data_access) är DETTA repos kopior,
     inte en annan via PYTHONPATH eller hårdkodade sys.path-rader (IN.3).
  3. Mappar (kodmappar = [FEL] om de saknas; körtidsmappar = [OBS], install.py/sonderna skapar dem).
  4. Källfiler med en rad om vad var och en gör (kod = [FEL]; dokument = [OBS], beslutsfilen kan ha undantagit).
  5. Beroenden mot requirements-local.txt (installerad version, pinning, plattformsmarkörer).
  6. Importtest av kärnmoduler (egna och tredjepart) — inga nätverksanrop (blob-klienten är lazy).
  7. Körprofil: PRICINGMODEL_* / BCG_* i den här terminalen och vad blob.py:s defaults blir av dem.
  8. Git-status.
  9. Diagnostik offline: DO.1-kvittona syns, Blob-inventeringen läses, run_status självtest,
     all_chain_validator statiskt, ODBC-drivrutin och az CLI finns, .env för DW, kända IN.3-skulder.

Markörer: [OK] / [OBS] (information, påverkar inte avslutskoden) / [FEL].
Avslutskod: 0 = inga [FEL], 1 = minst ett [FEL]. install.py ärver koden.

AVSIKT (avviker från mallen):
  - Ingen src/-layout: repot bär platta moduler. install.py lägger fyra mappar i en .pth; kontroll 2 prövar
    varifrån de importeras.
  - Dokument saknas = [OBS], inte [FEL]: vilka md-filer som följer med DevOps-exporten styrs av beslutsfilen.
  - Inget nätverk: Blob, DW och VM prövas inte här (MASTER_INSTALL §5). all_chain_validator körs i statiskt
    läge (utan --vm); run_status självtest är offline.
  - Beroenden läses ur requirements-local.txt (lokal miljö), inte requirements.txt (App Service-lasten).
"""
from __future__ import annotations

import importlib
import os
import warnings
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# EN sanning för Python-versionen: install.py:s tabell (MASTER_INSTALL krav 12). Fallback om install.py saknas.
_dwb = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True   # AVSIKT: ingen __pycache__/ i repo-roten av denna import
    sys.path.insert(0, str(ROOT))
    from install import PYTHON_WANTED, PTH_DIRS, REQUIREMENTS_REL, RUNTIME_DIRS, ENV_FILE_REL  # noqa: E402
    _PY_SOURCE = "install.py"
except Exception:
    PYTHON_WANTED = (3, 11)
    PTH_DIRS = ["orchestration/shared", "orchestration/infrastructure", "orchestration/webapp", "tools/dw"]
    REQUIREMENTS_REL = "requirements-local.txt"
    RUNTIME_DIRS = ["workspace", "workspace/flow_map", "workspace/validation_receipts", "output_model_feed", "output_analyspaket"]
    ENV_FILE_REL = "tools/dw/.env"
    _PY_SOURCE = "fallback i verify_setup.py (install.py gick inte att läsa)"
finally:
    sys.dont_write_bytecode = _dwb
    if sys.path and sys.path[0] == str(ROOT):
        sys.path.pop(0)

CODE_DIRS = ["orchestration", "orchestration/shared", "orchestration/infrastructure", "orchestration/runners",
             "orchestration/webapp", "verify_tool", "verify_tool/probes", "verify_tool/proof_chain",
             "verify_tool/extraction_validation", "verify_tool/output_rationality", "verify_tool/provenance",
             "verify_tool/run", "tools", "tools/dw", "tools/spegel", "docs", "Pipeline", "Pipeline/02. Elasticity"]
# FACIT-TRÅD-2 2026-10-21: tools/spegel (återställaren) tillagd; tools/blob_inventory.py bort ur SOURCE_FILES
# (inventeringsverktyget är utvecklarens metodik och följer inte med DevOps-exporten, beslut 2026-10-21).

# Beskrivningarna bygger på lästa filer (run_data, blob, run_status, app, all_chain_validator, stage_webapp,
# webapp_deploy_probe, dry_run_full_pipeline, Dockerfile, startup.sh, DRIFT, REPLIKERING) och på DRIFT.md:s
# kommandon för övriga; kod = [FEL] om den saknas.
SOURCE_FILES = {
    "requirements.txt":                               "App Service-/containerlast (Dockerfile, stage_webapp) — INTE lokal miljö",
    "requirements-local.txt":                         "lokala beroenden, pinnade (läses av install.py och kontroll 5)",
    "install.py":                                     "förstagångsinstallation (mappar, .venv, beroenden, .pth, .env)",
    "Dockerfile":                                     "dashboard-container (python:3.11-slim, gunicorn) för App Service",
    "startup.sh":                                     "App Service-start: gunicorn app:app (gunicorn 20.1 pga cwd på sys.path)",
    "azure-pipelines.yml":                            "DevOps-pipeline (inert tills service connection finns)",
    ".gitignore":                                     "vad git inte bär (Excel-utdata, parquet, workspace, .venv, .env)",
    ".gitattributes":                                 "radslut: .sh/.yml/.yaml alltid LF (Linux-körning)",
    "orchestration/shared/run_status.py":             "statuskontraktet: RunStatus, default_pipeline, window_run_id (stdlib)",
    "orchestration/infrastructure/blob.py":           "Blob-lager: status/in-/utdata/kvitton; auth aad|key via PRICINGMODEL_AUTH",
    "orchestration/infrastructure/azure_vm.py":       "VM-mekanik (az vm start/deallocate, ssh) för MOTOR-steget",
    "orchestration/runners/run_data.py":              "FÖRE: REGEN (tools/dw) -> PREP (DuckDB) -> UPLOAD (Blob input)",
    "orchestration/runners/run_cluster_model.py":     "MOTOR: cluster-familjen på VM:en",
    "orchestration/runners/run_site_model.py":        "MOTOR: site-familjen på VM:en (steg 5 lokalt, xlwings)",
    "orchestration/runners/run_bundle_model.py":      "MOTOR: bundle-familjen på VM:en",
    "orchestration/runners/run_after.py":             "EFTER: hämta utdata, steg 6, R12, Model Feed",
    "orchestration/webapp/app.py":                    "Flask-dashboard (läser status/körningar/kvitton ur Blob; 127.0.0.1:5000)",
    "orchestration/webapp/story_config.py":           "dashboardens berättelse-/textkonfiguration",
    "orchestration/webapp/info_config.py":            "dashboardens info-/fältkonfiguration",
    "tools/replicate_dataprep.py":                    "PREP: parquet -> vecko-CSV:er via DuckDB (BCG_END_DATE)",
    "tools/stage_webapp.py":                          "manifestdriven staging av webappen (kräver deploy-probens manifest)",
    "tools/webapp_deploy_probe.py":                   "AST-importhölje + requirements-täckning för webappen (Excel-kvitto)",
    "tools/dw/regenerate_transaction_parquet_chunked_v2.py": "REGEN: DW -> transaction_data.parquet, chunkat per år (kopia av BA-originalet)",
    "tools/dw/data_access.py":                        "DW-anslutning via AAD-token + pyodbc; .env via BCG_DW_ENV (kopia av BA-originalet)",
    "tools/dw/.env.example":                          "mall för tools/dw/.env (platshållare; .env committas aldrig)",
    "tools/dw/README.md":                             "härkomst, förutsättningar och miljövariabler för DW-steget",
    "tools/spegel/spegel_fran_blob.py":              "steg 2 efter install.py: facit + indata ur Blob (sha256-verifierat)",
    "verify_tool/probes/all_chain_validator.py":      "struktur-/runner-/kontraktsvalidering av hela kedjan (statisk utan --vm)",
    "verify_tool/dry_run_full_pipeline.py":           "preflight: sökvägar, fönsterkonsistens, runner-dry-runs (+ --vm)",
    "verify_tool/dry_run_e2e.py":                     "strukturell e2e-dry-run (BA_ROOT-miljövariabel)",
    "verify_tool/window_coherence.py":                "fönster-koherens tvärs familjer",
    "verify_tool/pipeline_contracts.py":              "kontrakt mellan pipelinens steg",
    "verify_tool/proof_chain/run_all.py":             "replikeringsbeviset FR-1..7 mot facit",
    "verify_tool/extraction_validation/run_all_validations.py": "DW-extrakt vs facit (DRIFT §3.2)",
    "verify_tool/output_rationality/run_all_rationality.py":    "rimlighet i färsk output (DRIFT §3.2)",
    "verify_tool/provenance/run_all_provenance.py":             "färskt vs fruset + freshness (DRIFT §3.2)",
    "verify_tool/run/run_step6.py":                   "steg 6 (Fall Back Logic) lokalt",
    "verify_tool/run/build_r12_for_model.py":         "R12-aggregering för Model Feed",
}
DOC_FILES = {
    "README.md":                                      "rot-README: syfte, Ny dator, dagsrutin, var data bor",
    "DRIFT.md":                                       "runbok: FÖRE/MOTOR/EFTER, validera, felsök",
    "REPLIKERING_OCH_VALIDERING.md":                  "hur replikeringen bevisades och var evidensen finns",
    "STATE.md":                                       "resurs-ID:n, lägen, hårda värden",
    "orchestration/README.md":                        "importkedjan och hur runners/app startas",
    "docs/governance/ROADMAP.md":                     "faser och vad som återstår",
    "docs/ops/DATA_PLACERING.md":                    "var datan ligger (git/Blob), roll i kedjan, hur den återställs",
    "docs/ops/OFFBOARDING_KRITISKT.md":              "det som inte följer med utvecklarens dator, och vad som ersätter det",
    "docs/BCG_ORIGINAL_REFERENSER.md":               "vilka filer ur BCG-originalet validatorerna jämför mot",
}

# (modul, attribut som ska finnas, bara win32?) — egna platta moduler via .pth
IMPORT_TESTS_OWN = [
    ("run_status",  ["RunStatus", "default_pipeline", "window_run_id", "resolve_window_end"], False),
    ("blob",        ["write_status", "read_status", "upload_inputs", "list_runs", "STORAGE_ACCOUNT"], False),
    ("story_config", [], False),
    ("info_config",  [], False),
    ("data_access", ["get_connection", "query_to_df"], True),
]
ORIGIN_DIRS = {"run_status": "orchestration/shared", "blob": "orchestration/infrastructure",
               "story_config": "orchestration/webapp", "info_config": "orchestration/webapp", "data_access": "tools/dw"}
IMPORT_TESTS_3P = [("pandas", False), ("numpy", False), ("pyarrow", False), ("openpyxl", False), ("duckdb", False),
                   ("flask", False), ("azure.storage.blob", False), ("azure.identity", False),
                   ("xlwings", True), ("pyodbc", True)]
PROFILE_VARS = ["PRICINGMODEL_STORAGE", "PRICINGMODEL_AUTH", "PRICINGMODEL_KEY", "PRICINGMODEL_RG",
                "PRICINGMODEL_SUBSCRIPTION", "PRICINGMODEL_STATUS_CONTAINER", "PRICINGMODEL_OUTPUT_CONTAINER",
                "PRICINGMODEL_INPUT_CONTAINER", "PRICINGMODEL_PIPELINE_CONTAINER", "PRICINGMODEL_RECEIPTS_CONTAINER",
                "BCG_START_DATE", "BCG_END_DATE", "BCG_DW_ENV", "BCG_DW_PYTHON", "BCG_REGEN_SCRIPT", "BA_ROOT",
                "BCG_FACIT_DIR"]
FACIT_DIR_REL = "verify_tool/facit/BCG_orginal_V2_New/02. Elasticity"
FACIT_EXPECTED = 9   # filer i Blob pipeline/00_frozen_facit/bcg_original/ (uppladdade 2026-10-21)
DASHBOARD_RECEIPTS = [  # kvitton som orchestration/webapp/story_config.py pekar på (spårade, DO.1 2026-10-21)
    "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
    "verify_tool/receipts/2026-06-08/rationality/00_rationality_master_2026-06-08_130847.xlsx",
    "verify_tool/receipts/2026-06-11/provenance/00_provenance_master_2026-06-11_181714.xlsx",
]
SECRET_VARS = {"PRICINGMODEL_KEY"}
RECEIPTS_2026_06_08 = "verify_tool/receipts/2026-06-08"
RECEIPTS_EXPECTED = 9   # spårade kvitton (DO.1-fix 2026-10-20: 8 + 08_baseline_replication)

WIDTH = 66
_errors = 0


def _sep(char: str = "-") -> None:
    print(char * WIDTH)


def _header(title: str) -> None:
    print()
    _sep()
    print(f"  {title}")
    _sep()


def _ok(msg: str) -> None:
    print(f"  [OK]      {msg}")


def _obs(msg: str) -> None:
    print(f"  [OBS]     {msg}")


def _fail(msg: str) -> None:
    global _errors
    _errors += 1
    print(f"  [FEL]     {msg}")


def _under(path: Path, parent: Path) -> bool:
    try:
        Path(os.path.normcase(str(path.resolve()))).relative_to(Path(os.path.normcase(str(parent.resolve()))))
        return True
    except ValueError:
        return False


def _win() -> bool:
    return sys.platform == "win32"


# --- 1 -----------------------------------------------------------------------------------------
def check_python() -> None:
    _header("1. Python och virtuell miljö")
    v = sys.version_info
    if (v.major, v.minor) == tuple(PYTHON_WANTED):
        _ok(f"Python {v.major}.{v.minor}.{v.micro}  ({sys.executable})")
    else:
        _obs(f"Python {v.major}.{v.minor}.{v.micro} — beroendena är pinnade och testade mot "
             f"{PYTHON_WANTED[0]}.{PYTHON_WANTED[1]} (värde från {_PY_SOURCE})")
    venv_dir = ROOT / ".venv"
    if sys.prefix == sys.base_prefix:
        _fail("ingen venv kör detta skript — kör .\\.venv\\Scripts\\python.exe verify_setup.py "
              "(eller py -3.11 install.py)")
    elif _under(Path(sys.prefix), venv_dir) or _under(venv_dir, Path(sys.prefix)):
        _ok(f"repots egen .venv: {sys.prefix}")
    else:
        _fail(f"en ANNAN venv kör: {sys.prefix} — förväntat {venv_dir} (MASTER_INSTALL IN.2)")


# --- 2 -----------------------------------------------------------------------------------------
def check_code_origin() -> None:
    """Kallstart-vakten (IN.3): modulerna ska komma ur DETTA repo, via install.py:s .pth — inte via PYTHONPATH
    eller en annan kopia. Egna moduler importeras här en gång; kontroll 6 återanvänder dem."""
    _header("2. Kallstart-vakt — vilken kopia av koden körs?")
    pp = os.environ.get("PYTHONPATH", "")
    outside = [p for p in pp.split(os.pathsep) if p.strip() and not _under(Path(p), ROOT)]
    if not pp:
        _ok("PYTHONPATH ej satt (modulerna läggs på sökvägen av install.py:s .pth-fil)")
    elif outside:
        _fail(f"PYTHONPATH pekar UTANFÖR detta repo: {outside} — ta bort: Remove-Item Env:PYTHONPATH")
    else:
        _obs(f"PYTHONPATH satt men inom repot: {pp} — behövs inte efter install.py")
    for mod_name, _names, win_only in IMPORT_TESTS_OWN:
        if win_only and not _win():
            _obs(f"{mod_name}: bara Windows (pyodbc) — hoppas över på {sys.platform}")
            continue
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            if isinstance(e, ModuleNotFoundError) and e.name and e.name.split(".")[0] != mod_name:
                hint = f"beroendet '{e.name}' saknas — kör py -3.11 install.py (steg 4: pip install)"
            else:
                hint = "kör py -3.11 install.py (steg 5 skriver .pth) och ta bort PYTHONPATH"
            _fail(f"import {mod_name} misslyckades: {type(e).__name__}: {e} — {hint}")
            continue
        origin = Path(getattr(mod, "__file__", "")).resolve()
        want = ROOT / ORIGIN_DIRS[mod_name]
        if _under(origin, want):
            _ok(f"{mod_name:<13} importeras från detta repo: {ORIGIN_DIRS[mod_name]}/")
        else:
            _fail(f"{mod_name:<13} importeras från {origin.parent} — INTE från {want}. Kör install.py i denna mapp "
                  "(repot flyttat?) och ta bort PYTHONPATH")


# --- 3 -----------------------------------------------------------------------------------------
def check_dirs() -> None:
    _header("3. Mappar")
    for rel in CODE_DIRS:
        if (ROOT / rel).is_dir():
            _ok(f"{rel}/")
        else:
            _fail(f"{rel}/  — mapp saknas i repot")
    for rel in RUNTIME_DIRS:
        if (ROOT / rel).is_dir():
            _ok(f"{rel}/  (körtidsmapp)")
        else:
            # AVSIKT: inte [FEL] — install.py skapar dem; flera sonder skapar dem också själva
            _obs(f"{rel}/  saknas — skapas av install.py eller av sonden vid första körning")


# --- 4 -----------------------------------------------------------------------------------------
def check_files() -> None:
    _header("4. Källfiler (kod = [FEL] om saknad; dokument = [OBS])")
    for rel, desc in SOURCE_FILES.items():
        if (ROOT / rel).is_file():
            _ok(f"{rel:<56} {desc}")
        else:
            _fail(f"{rel:<56} SAKNAS — {desc}")
    for rel, desc in DOC_FILES.items():
        if (ROOT / rel).is_file():
            _ok(f"{rel:<56} {desc}")
        else:
            _obs(f"{rel:<56} saknas — {desc} (undantagen enligt beslutsfilen, eller ofullständig klon)")


# --- 5 -----------------------------------------------------------------------------------------
_REQ = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*(==|>=|<=|~=|>|<)?\s*([^\s;#]+)?\s*(?:;\s*(.+))?$")


def _marker_applies(marker: str | None) -> bool:
    """Minimal PEP 508: bara sys_platform == / != stöds (det är allt requirements-local.txt använder)."""
    if not marker:
        return True
    m = re.match(r"""^\s*sys_platform\s*(==|!=)\s*["']([^"']+)["']\s*$""", marker)
    if not m:
        return True   # okänd markör: pröva ändå, rapporteras om paketet saknas
    return (sys.platform == m.group(2)) if m.group(1) == "==" else (sys.platform != m.group(2))


def check_dependencies() -> None:
    _header(f"5. Beroenden mot {REQUIREMENTS_REL}")
    from importlib import metadata
    req = ROOT / REQUIREMENTS_REL
    if not req.is_file():
        _fail(f"{REQUIREMENTS_REL} saknas")
        return
    n = 0
    unpinned = []
    for raw in req.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = _REQ.match(line)
        if not m:
            _obs(f"rad tolkas inte: {raw!r}")
            continue
        name, op, want, marker = m.group(1), m.group(2), m.group(3), m.group(4)
        if not _marker_applies(marker):
            _obs(f"{name:<28} gäller inte denna plattform ({marker.strip()})")
            continue
        n += 1
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            _fail(f"{name:<28} inte installerat — kör py -3.11 install.py")
            continue
        if op == "==":
            if have == want:
                _ok(f"{name:<28} {have}")
            else:
                _fail(f"{name:<28} {have} installerat, {want} krävs — kör py -3.11 install.py")
        else:
            unpinned.append(name)
            _ok(f"{name:<28} {have}  (krav: {op or ''}{want or ''})")
    if unpinned:
        _obs(f"ej pinnade med == : {', '.join(unpinned)} (MASTER_INSTALL krav 6)")
    if n == 0:
        _fail(f"{REQUIREMENTS_REL} innehåller inga beroenden för denna plattform")


# --- 6 -----------------------------------------------------------------------------------------
def check_imports() -> None:
    _header("6. Importtest — egna moduler och tredjepart (inga nätverksanrop)")
    for mod_name, names, win_only in IMPORT_TESTS_OWN:
        if win_only and not _win():
            continue
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            _fail(f"{mod_name:<22} import-fel: {type(e).__name__}: {e}")
            continue
        missing = [x for x in names if not hasattr(mod, x)]
        if missing:
            _fail(f"{mod_name:<22} saknar {', '.join(missing)}")
        else:
            _ok(f"{mod_name:<22} {', '.join(names) if names else 'importerbar'}")
    for mod_name, win_only in IMPORT_TESTS_3P:
        if win_only and not _win():
            _obs(f"{mod_name:<22} bara Windows — hoppas över")
            continue
        try:
            mod = importlib.import_module(mod_name)
            with warnings.catch_warnings():   # Flask 3.1: __version__ ger DeprecationWarning -- brus i en grind
                warnings.simplefilter("ignore")
                ver = getattr(mod, "__version__", None) or getattr(getattr(mod, "version", None), "__str__", lambda: "")()
            _ok(f"{mod_name:<22} {ver or 'importerbar'}")
        except Exception as e:
            _fail(f"{mod_name:<22} import-fel: {type(e).__name__}: {e}")


# --- 7 -----------------------------------------------------------------------------------------
def check_profile() -> None:
    """Körprofilen i denna terminal — och vad blob.py:s defaults BLIR av den (utvärdera funktionen, inte flaggan)."""
    _header("7. Körprofil — miljövariabler i denna terminal")
    set_vars = {k: os.environ[k] for k in PROFILE_VARS if k in os.environ}
    if not set_vars:
        _ok("inga PRICINGMODEL_*/BCG_*/BA_ROOT satta — kodens standardvärden gäller")
    for k, val in set_vars.items():
        shown = "<satt, visas inte>" if k in SECRET_VARS else repr(val)
        _obs(f"{k}={shown}  (Remove-Item Env:{k} återställer)")
    try:
        blob = importlib.import_module("blob")
    except Exception:
        return
    mode = getattr(blob, "_AUTH_MODE", "?")
    acct = getattr(blob, "STORAGE_ACCOUNT", "?")
    note = ("run_data.py och app.py sätter 'key' själva om variabeln saknas (ABAC-vägg, FD.29)"
            if mode == "aad" else "kontonyckel läses vid körning via az (aldrig i fil)")
    _ok(f"blob.py i denna terminal: konto {acct}, auth-läge '{mode}' — {note}")
    _ok(f"containrar: status={getattr(blob, 'CONTAINER_STATUS', '?')} output={getattr(blob, 'CONTAINER_OUTPUT', '?')} "
        f"input={getattr(blob, 'CONTAINER_INPUT', '?')} pipeline={getattr(blob, 'CONTAINER_PIPELINE', '?')} "
        f"receipts={getattr(blob, 'CONTAINER_RECEIPTS', '?')}")


# --- 8 -----------------------------------------------------------------------------------------
def check_git() -> None:
    _header("8. Git-status")
    try:
        r = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True, timeout=15)
    except FileNotFoundError:
        _obs("git hittades inte i PATH")
        return
    except Exception as e:
        _obs(f"git-kontrollen misslyckades: {e}")
        return
    if r.returncode != 0:
        _obs("inte ett git-repo (väntat i en exportmapp före git init)")
        return
    if r.stdout.strip():
        _obs("ocommittade ändringar:\n" + r.stdout.rstrip())
    else:
        _ok("rent arbetsträd")
    b = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, timeout=15)
    if b.stdout.strip():
        _ok(f"aktiv branch: {b.stdout.strip()}")


# --- 9 -----------------------------------------------------------------------------------------
def diagnostics() -> None:
    _header("9. Diagnostik offline")
    # a) DO.1: spårade kvitton syns i klonen (gitignore-fixen 2026-10-20)
    rdir = ROOT / RECEIPTS_2026_06_08
    n = len(list(rdir.glob("*.xlsx"))) if rdir.is_dir() else 0
    if n == RECEIPTS_EXPECTED:
        _ok(f"{RECEIPTS_2026_06_08}/: {n} kvitton (DO.1 — spårade filer syns trots *.xlsx i .gitignore)")
    else:
        _fail(f"{RECEIPTS_2026_06_08}/: {n} kvitton, {RECEIPTS_EXPECTED} väntade — .gitignore döljer spårade filer? (DO.1)")
    # b) datans hemvist dokumenterad + kvitton som dashboarden pekar på (FACIT-TRÅD-2 2026-10-21)
    dp = ROOT / "docs" / "ops" / "DATA_PLACERING.md"
    if dp.is_file():
        _ok("docs/ops/DATA_PLACERING.md finns — var datan ligger och hur den återställs")
    else:
        _obs("docs/ops/DATA_PLACERING.md saknas — datans hemvist är inte dokumenterad i klonen")
    for rel in DASHBOARD_RECEIPTS:
        if (ROOT / rel).is_file():
            _ok(f"{rel} (dashboarden länkar hit)")
        else:
            _fail(f"{rel} saknas — dashboarden pekar dit (story_config.py); spåras via !-rad i .gitignore (DO.1)")
    # b2) facit för validatorerna (BCG_FACIT_DIR, default verify_tool/facit) -- data, inte kod: [OBS]
    froot = Path(os.environ["BCG_FACIT_DIR"]) / "BCG_orginal_V2_New" / "02. Elasticity" if os.environ.get("BCG_FACIT_DIR") else ROOT / FACIT_DIR_REL
    nf = sum(1 for p in froot.rglob("*") if p.is_file()) if froot.is_dir() else 0
    if nf >= FACIT_EXPECTED:
        _ok(f"facit för validatorerna: {nf} filer under {froot.relative_to(ROOT) if _under(froot, ROOT) else froot}")
    else:
        _obs(f"facit för validatorerna: {nf}/{FACIT_EXPECTED} filer — kör: .\\.venv\\Scripts\\python.exe tools\\spegel\\spegel_fran_blob.py --kor "
             f"(proof_chain, output_rationality, provenance och extraction_validation jämför mot dem)")
    # c) run_status självtest (stdlib, offline)
    rs = ROOT / "orchestration" / "shared" / "run_status.py"
    try:
        r = subprocess.run([sys.executable, str(rs)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and "OK: contract" in r.stdout:
            _ok("run_status.py självtest: " + r.stdout.strip().splitlines()[-1])
        else:
            _fail(f"run_status.py självtest misslyckades (kod {r.returncode}): {(r.stderr or r.stdout).strip()[-300:]}")
    except Exception as e:
        _fail(f"run_status.py självtest gick inte att köra: {e}")
    # d) all_chain_validator statiskt (inga nätverksanrop utan --vm; skriver inget med flaggorna)
    acv = ROOT / "verify_tool" / "probes" / "all_chain_validator.py"
    try:
        r = subprocess.run([sys.executable, str(acv), "--no-receipt", "--no-flow-md"], cwd=ROOT,
                           capture_output=True, text=True, timeout=180)
        summary = next((l.strip() for l in r.stdout.splitlines() if "PASS=" in l), "")
        if r.returncode == 0:
            _ok(f"all_chain_validator (statisk): {summary or 'kod 0'}")
        else:
            _fail(f"all_chain_validator (statisk): kod {r.returncode} {summary} — läs utskriften: "
                  f".\\.venv\\Scripts\\python.exe verify_tool\\probes\\all_chain_validator.py --no-receipt --no-flow-md")
    except Exception as e:
        _fail(f"all_chain_validator gick inte att köra: {e}")
    # e) DW-förutsättningar (behövs bara för REGEN) — information, inte fel
    env_file = ROOT / ENV_FILE_REL
    if env_file.is_file():
        keys = [l.split("=", 1)[0].strip() for l in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
                if "=" in l and not l.lstrip().startswith("#")]
        filled = [l.split("=", 1)[0].strip() for l in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
                  if "=" in l and not l.lstrip().startswith("#") and l.split("=", 1)[1].strip()]
        _ok(f"{ENV_FILE_REL}: nycklar {', '.join(keys) or '—'}; ifyllda: {len(filled)}/{len(keys)} (värden visas inte)")
        if len(filled) < len(keys):
            _obs("tomma värden i .env — REGEN (DW) kräver alla tre; värdena finns hos den som förvaltar DW (IT)")
    else:
        _obs(f"{ENV_FILE_REL} saknas — skapas av install.py; behövs bara för bränsleledets REGEN-steg")
    if _win():
        try:
            import pyodbc  # noqa: F401
            drivers = pyodbc.drivers()
            if any("ODBC Driver 17 for SQL Server" in d for d in drivers):
                _ok("ODBC Driver 17 for SQL Server finns (REGEN mot DW)")
            else:
                _obs(f"ODBC Driver 17 for SQL Server saknas (systeminstallation, IT) — REGEN kan inte nå DW. Finns: {drivers}")
        except Exception as e:
            _obs(f"pyodbc.drivers() gick inte att läsa: {e}")
    az = shutil.which("az") or shutil.which("az.cmd")
    if az:
        _ok(f"az CLI finns ({az}) — Blob-nyckelläge och VM-steg använder det; inloggning prövas inte här")
    else:
        _obs("az CLI saknas i PATH — Blob (key-läge), VM-steg och inventering kräver Azure CLI (IT-policy: systeminstallation)")
    # f) kända IN.3-skulder i källan (information)
    try:
        src = rs.read_text(encoding="utf-8", errors="replace")
        if "C:\\Projekt\\BCG" in src:
            _obs("run_status.resolve_window_end: default-parquet hårdkodad till C:\\Projekt\\BCG — i en klon på annan "
                 "sökväg faller den tyst till 2026-04-30; ange alltid --end explicit till run_data.py (backlog)")
    except Exception:
        pass
    tools_hard = []
    for p in sorted((ROOT / "tools").glob("*.py")):
        try:
            if "C:\\Projekt\\BCG\\orchestration" in p.read_text(encoding="utf-8", errors="replace"):
                tools_hard.append(p.name)
        except Exception:
            pass
    if tools_hard:
        _obs(f"{len(tools_hard)} verktyg i tools/ bär hårdkodad sys.path mot C:\\Projekt\\BCG (engångs-/diagnosverktyg; "
             f".pth-filen gör dem körbara ändå): {', '.join(tools_hard[:6])}{' …' if len(tools_hard) > 6 else ''}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    _sep("=")
    print("  VERIFY SETUP — BCG Pricing (evbcgpricing), lokal miljö")
    print(f"  Repo-rot: {ROOT}")
    _sep("=")
    check_python()
    check_code_origin()
    check_dirs()
    check_files()
    check_dependencies()
    check_imports()
    check_profile()
    check_git()
    diagnostics()
    print()
    _sep("=")
    if _errors:
        print(f"  {_errors} [FEL] — rätta dem innan kedjan körs. [OBS] är information.")
    else:
        print("  Inga [FEL]. [OBS] är information.")
    print("  Bevisar inte: DW (VPN/ODBC/AAD), Blob (az login), VM:ens Ray-venv, Excel-COM (steg 5) eller containerbygget.")
    print("  Rök-tester för det: DRIFT.md (FÖRE/MOTOR/EFTER) och verify_tool\\dry_run_full_pipeline.py --vm.")
    _sep("=")
    return 1 if _errors else 0


if __name__ == "__main__":
    sys.exit(main())
