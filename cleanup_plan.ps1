# cleanup_plan.ps1  —  safe, reviewable cleanup of the BCG repo root
# ====================================================================
# Owner: Jens Palmö. Goal: an operationally usable, logical folder structure.
#
# SAFETY FIRST — read before running:
#   * This script uses `git mv` so history is preserved and the moves are tracked.
#   * It moves SCRIPTS and DOCS only. It does NOT touch Pipeline\, archives\,
#     output_*\, or any data file — nothing that a run depends on at a relative path.
#   * The run scripts (run_step6, build_r12, fallback_blend, run_bundle_dataprep) use
#     ABSOLUTE BCG_ROOT paths, so moving them does not break their access to Pipeline\.
#     VERIFY THIS with the cross-reference check first (section 0).
#   * Run section 0, read the output, THEN run section 1+ if clean.
#   * Everything is `git mv`, so `git reset --hard` undoes it before commit.
#
# RUN FROM:  C:\Projekt\BCG

# ============================================================
# SECTION 0 — VERIFY before moving (run this, read output, do not skip)
# ============================================================
Write-Output "=== Cross-references between root scripts (flag before moving) ==="
$pys = Get-ChildItem -File -Filter "*.py"
$flagged = $false
foreach ($f in $pys) {
  $c = Get-Content $f.FullName -Raw
  foreach ($o in $pys) {
    if ($f.Name -ne $o.Name -and $c -match ("import\s+" + [regex]::Escape($o.BaseName) + "\b")) {
      Write-Output "  ⚠ $($f.Name) imports $($o.Name) — keep these in the SAME folder"
      $flagged = $true
    }
  }
}
if (-not $flagged) { Write-Output "  ✓ No inter-script imports found — safe to group freely." }
Write-Output ""
Write-Output "If anything is flagged above, keep those scripts together. Otherwise proceed."
Write-Output "Press Ctrl+C to stop here and review, or continue to run the moves."
Pause

# ============================================================
# SECTION 1 — create the target folders
# ============================================================
$dirs = @(
  "verify_tool\run",
  "analysis",
  "presentations",
  "tools",
  "docs\governance",
  "docs\knowledge",
  "docs\ops"
)
foreach ($d in $dirs) {
  if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null; Write-Output "created $d" }
}

# ============================================================
# SECTION 2 — move RUN scripts → verify_tool\run\
# (operational entry points that execute the model)
# ============================================================
$run = @("run_step6.py","build_r12_for_model.py","fallback_blend.py","run_bundle_dataprep.py")
foreach ($f in $run) { if (Test-Path $f) { git mv $f "verify_tool\run\$f" } }

# ============================================================
# SECTION 3 — move ANALYSIS scripts → analysis\
# ============================================================
$ana = @("analys_bcg_freshness.py","xlsx_export_bcg_freshness.py","compare_elasticity_runs.py",
         "assess_bundle_materiality.py")
foreach ($f in $ana) { if (Test-Path $f) { git mv $f "analysis\$f" } }

# ============================================================
# SECTION 4 — move PRESENTATIONS / teaching artifacts → presentations\
# ============================================================
$pres = @("elasticity_since_bcg.html","Model_Update_Guide.html","Model_Update_Guide.pdf",
          "Elasticitet_Beslutssnurra_BCG.xlsx")
foreach ($f in $pres) { if (Test-Path $f) { git mv $f "presentations\$f" } }
# (Elasticitet_Sandbox_BCG.xlsx if present)
if (Test-Path "Elasticitet_Sandbox_BCG.xlsx") { git mv "Elasticitet_Sandbox_BCG.xlsx" "presentations\Elasticitet_Sandbox_BCG.xlsx" }

# ============================================================
# SECTION 5 — move ONE-OFF TOOLS → tools\
# (diagnostics / converters / patches not part of the run path)
# ============================================================
$tools = @("convert_masterdata_to_parquet.py","diagnose_masterdata_csv.py","inspect_parquet.py",
           "check_yearflag_population.py","patch_bundle_yearflag.py","verify_bundle_growing.py",
           "verify_bundle_schema.py","replicate_dataprep.py")
foreach ($f in $tools) { if (Test-Path $f) { git mv $f "tools\$f" } }

# ============================================================
# SECTION 6 — move DOCS into docs\ subfolders
# ============================================================
$gov = @("BCG_PRICING_PLAYBOOK.md","ROADMAP.md","LOCKED_ASSUMPTIONS.md","FUTURE_DEVELOPMENT.md")
foreach ($f in $gov) { if (Test-Path $f) { git mv $f "docs\governance\$f" } }

$know = @("LESSONS_BCG.md","INSIGHTS_BCG.md","F9_BUNDLE_INVENTORY.md")
foreach ($f in $know) { if (Test-Path $f) { git mv $f "docs\knowledge\$f" } }

$ops = @("TECHNICAL_PREREQUISITES.md","KRAVSPEC_IT.md","MASTER_AZURE.md","UBUNTU_AZURE_VM.md")
foreach ($f in $ops) { if (Test-Path $f) { git mv $f "docs\ops\$f" } }

# OPERATIONS.md and REPLICATION_AND_VALIDATION.md (new) stay in ROOT next to README.md
# NEXT_SESSION.md and STARTTEXT_NEXT_SESSION.txt stay in ROOT (working files)

# ============================================================
# SECTION 7 — rename TILL_RADERING (Swedish) → _TO_DELETE
# ============================================================
if (Test-Path "TILL_RADERING") { git mv "TILL_RADERING" "_TO_DELETE" }

# ============================================================
# SECTION 8 — review, then commit
# ============================================================
Write-Output ""
Write-Output "=== Review the moves ==="
git status
Write-Output ""
Write-Output "If correct, commit with:"
Write-Output '  git commit -m "Repo cleanup: group run/analysis/presentations/tools/docs; add OPERATIONS + REPLICATION_AND_VALIDATION"'
Write-Output ""
Write-Output "IMPORTANT after moving run scripts: update any shortcut/notes that called them"
Write-Output "at the old paths. New paths:"
Write-Output "  py -3.11 verify_tool\run\run_step6.py"
Write-Output "  py -3.11 verify_tool\run\build_r12_for_model.py --tx <csv>"
