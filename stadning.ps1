# stadning.ps1  —  säker, granskningsbar städning av BCG-repots rot
# ====================================================================
# Ägare: Jens Palmö. Mål: en operativt användbar, logisk mappstruktur.
#
# SÄKERHET FÖRST — läs innan körning:
#   * Skriptet använder `git mv` så historik bevaras och flyttarna spåras.
#   * Det flyttar bara SKRIPT och DOKUMENT. Det rör INTE Pipeline\, archives\,
#     output_*\, eller någon datafil — inget som en körning beror på via relativ sökväg.
#   * Körskripten (run_step6, build_r12, fallback_blend, run_bundle_dataprep) använder
#     ABSOLUTA BCG_ROOT-sökvägar, så att flytta dem bryter inte deras åtkomst till Pipeline\.
#     VERIFIERA detta med korsreferens-kollen först (Sektion 0).
#   * Kör Sektion 0, läs utskriften, kör SEDAN Sektion 1+ om rent.
#   * Allt är `git mv`, så `git reset --hard` ångrar det före commit.
#
# KÖR FRÅN:  C:\Projekt\BCG

# ============================================================
# SEKTION 0 — VERIFIERA före flytt (kör detta, läs utskrift, hoppa inte över)
# ============================================================
Write-Output "=== Korsreferenser mellan rotskript (flaggas före flytt) ==="
$pys = Get-ChildItem -File -Filter "*.py"
$flagged = $false
foreach ($f in $pys) {
  $c = Get-Content $f.FullName -Raw
  foreach ($o in $pys) {
    if ($f.Name -ne $o.Name -and $c -match ("import\s+" + [regex]::Escape($o.BaseName) + "\b")) {
      Write-Output "  VARNING: $($f.Name) importerar $($o.Name) — håll dessa i SAMMA mapp"
      $flagged = $true
    }
  }
}
if (-not $flagged) { Write-Output "  OK: inga import-beroenden mellan rotskript — säkert att gruppera fritt." }
Write-Output ""
Write-Output "Om något flaggats ovan, håll de skripten tillsammans. Annars fortsätt."
Write-Output "Ctrl+C för att stanna och granska, eller fortsätt för att köra flyttarna."
Pause

# ============================================================
# SEKTION 1 — skapa målmapparna
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
  if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null; Write-Output "skapade $d" }
}

# ============================================================
# SEKTION 2 — flytta KÖRSKRIPT → verify_tool\run\
# (operativa ingångar som kör modellen)
# ============================================================
$run = @("run_step6.py","build_r12_for_model.py","fallback_blend.py","run_bundle_dataprep.py")
foreach ($f in $run) { if (Test-Path $f) { git mv $f "verify_tool\run\$f" } }

# ============================================================
# SEKTION 3 — flytta ANALYS-skript → analysis\
# ============================================================
$ana = @("analys_bcg_freshness.py","xlsx_export_bcg_freshness.py","compare_elasticity_runs.py",
         "assess_bundle_materiality.py")
foreach ($f in $ana) { if (Test-Path $f) { git mv $f "analysis\$f" } }

# ============================================================
# SEKTION 4 — flytta PRESENTATIONER / pedagogik → presentations\
# ============================================================
$pres = @("elasticity_since_bcg.html","Model_Update_Guide.html","Model_Update_Guide.pdf",
          "Elasticitet_Beslutssnurra_BCG.xlsx","Elasticitet_Sandbox_BCG.xlsx")
foreach ($f in $pres) { if (Test-Path $f) { git mv $f "presentations\$f" } }

# ============================================================
# SEKTION 5 — flytta ENGÅNGS-VERKTYG → tools\
# (diagnostik / konverterare / patchar, ej i körvägen)
# ============================================================
$tools = @("convert_masterdata_to_parquet.py","diagnose_masterdata_csv.py","inspect_parquet.py",
           "check_yearflag_population.py","patch_bundle_yearflag.py","verify_bundle_growing.py",
           "verify_bundle_schema.py","replicate_dataprep.py")
foreach ($f in $tools) { if (Test-Path $f) { git mv $f "tools\$f" } }

# ============================================================
# SEKTION 6 — flytta DOKUMENT till docs\-undermappar
# ============================================================
$gov = @("BCG_PRICING_PLAYBOOK.md","ROADMAP.md","LOCKED_ASSUMPTIONS.md","FUTURE_DEVELOPMENT.md")
foreach ($f in $gov) { if (Test-Path $f) { git mv $f "docs\governance\$f" } }

$know = @("LESSONS_BCG.md","INSIGHTS_BCG.md","F9_BUNDLE_INVENTORY.md")
foreach ($f in $know) { if (Test-Path $f) { git mv $f "docs\knowledge\$f" } }

$ops = @("TECHNICAL_PREREQUISITES.md","KRAVSPEC_IT.md","MASTER_AZURE.md","UBUNTU_AZURE_VM.md")
foreach ($f in $ops) { if (Test-Path $f) { git mv $f "docs\ops\$f" } }

# README.md, DRIFT.md, REPLIKERING_OCH_VALIDERING.md stannar i ROTEN (navet)

# ============================================================
# SEKTION 7 — NEXT_SESSION nu inbakad i FUTURE_DEVELOPMENT (Phase Z)
# Arkivera de gamla session-filerna (ersatta, ej raderade)
# ============================================================
if (-not (Test-Path "archives\superseded")) { New-Item -ItemType Directory -Path "archives\superseded" | Out-Null }
foreach ($f in @("NEXT_SESSION.md","STARTTEXT_NEXT_SESSION.txt")) {
  if (Test-Path $f) { git mv $f "archives\superseded\$f" }
}

# ============================================================
# SEKTION 8 — döp om TILL_RADERING (svenska, behåll) → _ATT_RADERA
# ============================================================
if (Test-Path "TILL_RADERING") { git mv "TILL_RADERING" "_ATT_RADERA" }

# ============================================================
# SEKTION 9 — granska, committa sedan
# ============================================================
Write-Output ""
Write-Output "=== Granska flyttarna ==="
git status
Write-Output ""
Write-Output "Om korrekt, committa med:"
Write-Output '  git commit -m "Repo-stadning: gruppera run/analysis/presentations/tools/docs; DRIFT + REPLIKERING_OCH_VALIDERING; NEXT_SESSION inbakad i FUTURE_DEVELOPMENT Phase Z"'
Write-Output ""
Write-Output "VIKTIGT efter flytt av körskript: uppdatera genvägar/anteckningar som anropade dem"
Write-Output "på gamla sökvägar. Nya sökvägar:"
Write-Output "  py -3.11 verify_tool\run\run_step6.py"
Write-Output "  py -3.11 verify_tool\run\build_r12_for_model.py --tx <csv>"
