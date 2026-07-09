# webapp_deploy_probe.py -- multi-hypothesis probe for dashboard deployment
# =============================================================================
# Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Purpose:   Measure, don't guess (KARNPRINCIP P.5 sond). Answers, in ONE run:
#   A. What is the TRUE import closure of the webapp?  AST-based, transitive,
#      starting at app.py. The regex gate in stage v1.0 could not see that
#      run_status (or anything run_status imports) belongs in the payload.
#   B. Is every EXTERNAL package in the closure covered by requirements.txt?
#      Locally the global Python has everything; in the cloud only
#      requirements.txt exists -> uncovered import = guaranteed ModuleNotFound.
#   C. Local tooling: Python version, az CLI version, does 'az webapp deploy'
#      support --clean (D.21: az subcommands drift between versions)?
#   D. (--azure) What Azure state do we have access to: app exists, runtime,
#      startup file, which app-setting NAMES exist (never values).
# Output:    workspace/deploy_staging_manifest.json  (consumed by
#            tools/stage_webapp.py -- ONE owner of the closure, no divergence)
#            + Excel receipt in workspace/validation_receipts/ (openpyxl,
#            timestamp in filename and first rows -- standing instruction).
# Read-only: probes and reports; changes nothing in repo or Azure.
# Run:       py -3.11 tools/webapp_deploy_probe.py [--azure]
# Exit:      0 = closure clean (warnings allowed), 1 = CRITICAL finding.
# Lessons:   D.16 (Build Operation ID lives in wwwroot's oryx-manifest.toml),
#            D.21, D.22, LB.67-class silent-empty, A.9b source-before-hypothesis.
# =============================================================================
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEBAPP = REPO / "orchestration" / "webapp"
ENTRY = WEBAPP / "app.py"
# Where local modules may legitimately live (searched in this order):
SEARCH_ROOTS = [
    WEBAPP,
    REPO / "orchestration" / "infrastructure",
    REPO / "orchestration" / "shared",
    REPO / "orchestration",
    REPO,
]
MANIFEST_OUT = REPO / "workspace" / "deploy_staging_manifest.json"
RECEIPT_DIR = REPO / "workspace" / "validation_receipts"

STDLIB = set(sys.stdlib_module_names)  # Python 3.10+, authoritative

LOG: list[str] = []
CRITICAL: list[str] = []
WARN: list[str] = []


def say(line: str) -> None:
    LOG.append(line)
    print(line)


def crit(line: str) -> None:
    CRITICAL.append(line)
    say(f"[CRITICAL] {line}")


def warn(line: str) -> None:
    WARN.append(line)
    say(f"[WARN] {line}")


# ---------------------------------------------------------------- A: closure
def top_level_imports(py_file: Path) -> set[str]:
    """All imported top-level module names in a file, via AST (all scopes)."""
    tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative import: resolves inside the staged flat dir anyway;
                # record the immediate name so collision/presence is checked
                for a in node.names:
                    mods.add(a.name.split(".")[0])
            elif node.module:
                mods.add(node.module.split(".")[0])
    return mods


def find_local(mod: str) -> Path | None:
    for root in SEARCH_ROOTS:
        cand = root / f"{mod}.py"
        if cand.exists():
            return cand
        pkg = root / mod / "__init__.py"
        if pkg.exists():
            return pkg  # package -- flagged separately (flat layout risk)
    return None


def requirements_names() -> set[str]:
    reqs = REPO / "requirements.txt"
    if not reqs.exists():
        crit("requirements.txt missing at repo root")
        return set()
    names = set()
    for line in reqs.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.add(line.split("==")[0].split(">=")[0].split("[")[0].lower())
    return names


def dists_for(mod: str) -> set[str]:
    try:
        from importlib.metadata import packages_distributions
        return {d.lower() for d in packages_distributions().get(mod, [])}
    except Exception:
        return set()


def build_closure() -> tuple[dict[str, Path], set[str]]:
    """Returns ({module_name: local_path}, {external_module_names}).
    Raises nothing; records CRITICAL for unresolved names."""
    local: dict[str, Path] = {}
    external: set[str] = set()
    queue = [("app", ENTRY)]
    seen = {"app"}
    while queue:
        name, path = queue.pop()
        local[name] = path
        for mod in sorted(top_level_imports(path)):
            if mod in seen or mod in STDLIB:
                continue
            lp = find_local(mod)
            if lp is not None:
                seen.add(mod)
                if lp.name == "__init__.py":
                    warn(f"{name} imports PACKAGE '{mod}' ({lp.parent}) -- "
                         "flat staging cannot hold packages as-is; needs "
                         "directory copy or refactor. Review.")
                queue.append((mod, lp))
            elif dists_for(mod):
                external.add(mod)
                seen.add(mod)
            else:
                crit(f"unresolved import '{mod}' (from {name}.py): not stdlib, "
                     "not found in search roots, not an installed package")
    return local, external


# ---------------------------------------------------------------- C: tooling
def az(*args: str) -> tuple[int, str]:
    exe = "az.cmd" if sys.platform == "win32" else "az"
    try:
        p = subprocess.run([exe, *args], capture_output=True, text=True,
                           timeout=60)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "az CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "az call timed out"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--azure", action="store_true",
                    help="also probe Azure state (requires az login)")
    opts = ap.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    say(f"webapp_deploy_probe -- {ts}")
    say(f"repo: {REPO}")
    say("")

    # --- A: import closure ----------------------------------------------------
    say("=== A. IMPORT CLOSURE (AST, transitive from app.py) ===")
    if not ENTRY.exists():
        crit(f"entry point missing: {ENTRY}")
        return finish(1, opts)
    local, external = build_closure()
    say(f"local modules in closure: {len(local)}")
    for name, path in sorted(local.items()):
        say(f"  STAGE  {name:<20} <- {path.relative_to(REPO)}")
    say(f"external modules in closure: {sorted(external)}")

    # flat-layout collision check
    stems: dict[str, list[Path]] = {}
    for name, path in local.items():
        stems.setdefault(path.stem, []).append(path)
    for stem, paths in stems.items():
        if len(paths) > 1:
            crit(f"flat-layout NAME COLLISION on '{stem}.py': "
                 f"{[str(p.relative_to(REPO)) for p in paths]}")

    # --- B: requirements coverage ----------------------------------------------
    say("")
    say("=== B. REQUIREMENTS COVERAGE (cloud has ONLY requirements.txt) ===")
    reqs = requirements_names()
    say(f"requirements.txt entries: {sorted(reqs)}")
    for mod in sorted(external):
        dists = dists_for(mod)
        hit = dists & reqs
        if hit:
            say(f"  OK     {mod:<20} covered by {sorted(hit)}")
        elif dists:
            crit(f"external '{mod}' resolves locally to {sorted(dists)} but "
                 "NONE of these are in requirements.txt -> ModuleNotFound in "
                 "cloud. Add the right distribution to requirements.txt.")
        else:
            warn(f"external '{mod}': cannot map to a pip distribution "
                 "locally -- verify manually")
    if "gunicorn" not in reqs or "gunicorn==20.1.0" not in (
            (REPO / "requirements.txt").read_text(encoding="utf-8",
                                                  errors="replace")):
        crit("gunicorn==20.1.0 pin missing in requirements.txt (D.22)")

    # --- runtime assets ----------------------------------------------------------
    say("")
    say("=== RUNTIME ASSETS (webapp dir) ===")
    for sub in ("templates", "static"):
        d = WEBAPP / sub
        if d.exists():
            n = sum(1 for f in d.rglob("*") if f.is_file())
            say(f"  {sub}/: {n} file(s) -- staged by directory copy")
        else:
            say(f"  {sub}/: absent (fine if app does not use it)")

    # --- C: local tooling ---------------------------------------------------------
    say("")
    say("=== C. LOCAL TOOLING ===")
    say(f"  Python: {sys.version.split()[0]} "
        f"({'OK, matches App Service 3.11' if sys.version_info[:2] == (3, 11) else 'NOTE: App Service runtime is 3.11'})")
    rc, out = az("version", "-o", "json")
    if rc == 0:
        try:
            say(f"  az CLI: {json.loads(out).get('azure-cli', '?')}")
        except Exception:
            say("  az CLI: present (version unparsed)")
        rc2, helptext = az("webapp", "deploy", "--help")
        if rc2 == 0 and "--clean" in helptext:
            say("  az webapp deploy --clean: SUPPORTED (verified, D.21)")
        else:
            warn("az webapp deploy --clean NOT found in --help -- CLI drift "
                 "(D.21). Do not run the final round until resolved; "
                 "alternative bust: az webapp config appsettings + Kudu wipe.")
    else:
        warn(f"az CLI unavailable ({out.strip()}) -- local deploy blocked; "
             "DevOps path unaffected")

    # --- D: Azure state (optional, names only, never values) -----------------------
    if opts.azure:
        say("")
        say("=== D. AZURE STATE (read-only, setting NAMES only) ===")
        rc, out = az("account", "show", "--query", "name", "-o", "tsv")
        say(f"  subscription: {out.strip() if rc == 0 else 'NOT LOGGED IN'}")
        if rc == 0:
            rc, out = az("webapp", "show", "-g", "ev-openai-swce-rg-test",
                         "-n", "evbcg-dashboard", "-o", "json")
            if rc == 0:
                app = json.loads(out)
                say(f"  app state: {app.get('state')}")
                say(f"  runtime:   {app.get('siteConfig', {}).get('linuxFxVersion') or '(query via config)'}")
            else:
                warn("cannot read app (PIM expired or deleted)")
            rc, out = az("webapp", "config", "show", "-g",
                         "ev-openai-swce-rg-test", "-n", "evbcg-dashboard",
                         "--query", "appCommandLine", "-o", "tsv")
            if rc == 0:
                say(f"  startup-file: '{out.strip()}'")
            rc, out = az("webapp", "config", "appsettings", "list", "-g",
                         "ev-openai-swce-rg-test", "-n", "evbcg-dashboard",
                         "--query", "[].name", "-o", "json")
            if rc == 0:
                names = json.loads(out)
                say(f"  app settings present (names): {sorted(names)}")
                for req_name in ("SCM_DO_BUILD_DURING_DEPLOYMENT",
                                 "PRICINGMODEL_AUTH", "PRICINGMODEL_KEY",
                                 "PRICINGMODEL_STORAGE"):
                    tag = "OK" if req_name in names else "MISSING"
                    say(f"    {tag:<8} {req_name}")

    # --- manifest -----------------------------------------------------------------
    say("")
    say("=== STAGING MANIFEST ===")
    files = []
    for name, path in sorted(local.items()):
        src = str(path.relative_to(REPO)).replace("\\", "/")
        files.append({"src": src, "dst": f"{path.stem}.py"})
        say(f"  {src}  ->  {path.stem}.py")
    manifest = {
        "generated": ts,
        "entry": "app.py",
        "files": files,
        "dirs": [s for s in ("templates", "static") if (WEBAPP / s).exists()],
        "external": sorted(external),
        "critical": CRITICAL,
        "warnings": WARN,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    say(f"manifest written: {MANIFEST_OUT.relative_to(REPO)}")

    return finish(1 if CRITICAL else 0, opts)


def finish(code: int, opts) -> int:
    say("")
    say(f"=== PROBE VERDICT: {'CRITICAL FINDINGS -- fix before deploy' if code else 'CLEAN (warnings above, if any)'} ===")
    say(f"critical: {len(CRITICAL)}, warnings: {len(WARN)}")
    # Excel receipt (standing instruction: openpyxl, timestamp in name + rows)
    try:
        from openpyxl import Workbook
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        wb = Workbook()
        ws = wb.active
        ws.title = "probe_log"
        ws.append(["webapp_deploy_probe receipt"])
        ws.append([f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        ws.append([f"verdict: {'CRITICAL' if code else 'CLEAN'}"])
        ws.append([])
        for line in LOG:
            ws.append([line])
        out = RECEIPT_DIR / f"webapp_deploy_probe_{stamp}.xlsx"
        wb.save(out)
        print(f"[receipt] {out}")
    except Exception as e:  # receipt failure must not mask the verdict
        print(f"[receipt] FAILED to write Excel receipt: {e}")
    return code


if __name__ == "__main__":
    sys.exit(main())
