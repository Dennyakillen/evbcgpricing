# stadning.ps1  --  saker, granskningsbar stadning av BCG-repots rot
# ====================================================================
# Agare: Jens Palmo. Mal: en operativt anvandbar, logisk mappstruktur.
#
# SAKERHET FORST -- las innan korning:
#   * Skriptet anvander git mv sa historik bevaras och flyttarna sparas.
#   * Det flyttar bara SKRIPT och DOKUMENT. Det ror INTE Pipeline\, archives\,
#     output_*\, eller nagon datafil -- inget som en korning beror pa via relativ sokvag.
#   * Korskripten (run_step6, build_r12, fallback_blend, run_bundle_dataprep) anvander
#     ABSOLUTA BCG_ROOT-sokvagar, sa att flytta dem bryter inte deras atkomst till Pipeline\.
#     VERIFIERA detta med korsreferens-kollen forst (Sektion 0).
#   * Kor Sektion 0, las utskriften, kor SEDAN Sektion 1+ om rent.
#   * Allt ar git mv, sa "git reset --hard" angrar det fore commit.
#
# KOR FRAN:  C:\Projekt\BCG

# ============================================================
# SEKTION 0 -- VERIFIERA fore flytt (kor detta, las utskrift)
# ============================================================
Write-Output "=== Korsreferenser mellan rotskript (flaggas fore flytt) ==="
$pys = Get-ChildItem -File -Filter "*.py"
$flagged = $false
foreach ($f in $pys) {
    $c = Get-Content $f.FullName -Raw
    foreach ($o in $pys) {
        $pattern = "import\s+" + [regex]::Escape($o.BaseName)
        if (($f.Name -ne $o.Name) -and ($c -match $pattern)) {
            Write-Output ("  VARNING: " + $f.Name + " importerar " + $o.Name + " -- hall dessa i SAMMA mapp")
            $flagged = $true
        }
    }
}
if (-not $flagged) {
    Write-Output "  OK: inga import-beroenden mellan rotskript -- sakert att gruppera fritt."
}
Write-Output ""
Write-Output "Om nagot flaggats ovan, hall de skripten tillsammans. Annars fortsatt."
Write-Output "Ctrl+C for att stanna och granska, eller fortsatt for att kora flyttarna."
Pause

# ============================================================
# SEKTION 1 -- skapa malmapparna
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
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d | Out-Null
        Write-Output ("skapade " + $d)
    }
}

# ============================================================
# SEKTION 2 -- flytta KORSKRIPT -> verify_tool\run\
# ============================================================
$run = @("run_step6.py", "build_r12_for_model.py", "fallback_blend.py", "run_bundle_dataprep.py")
foreach ($f in $run) {
    if (Test-Path $f) { git mv $f ("verify_tool\run\" + $f) }
}

# ============================================================
# SEKTION 3 -- flytta ANALYS-skript -> analysis\
# ============================================================
$ana = @("analys_bcg_freshness.py", "xlsx_export_bcg_freshness.py", "compare_elasticity_runs.py", "assess_bundle_materiality.py")
foreach ($f in $ana) {
    if (Test-Path $f) { git mv $f ("analysis\" + $f) }
}

# ============================================================
# SEKTION 4 -- flytta PRESENTATIONER / pedagogik -> presentations\
# ============================================================
$pres = @("elasticity_since_bcg.html", "Model_Update_Guide.html", "Model_Update_Guide.pdf", "Elasticitet_Beslutssnurra_BCG.xlsx", "Elasticitet_Sandbox_BCG.xlsx")
foreach ($f in $pres) {
    if (Test-Path $f) { git mv $f ("presentations\" + $f) }
}

# ============================================================
# SEKTION 5 -- flytta ENGANGS-VERKTYG -> tools\
# ============================================================
$tools = @("convert_masterdata_to_parquet.py", "diagnose_masterdata_csv.py", "inspect_parquet.py", "check_yearflag_population.py", "patch_bundle_yearflag.py", "verify_bundle_growing.py", "verify_bundle_schema.py", "replicate_dataprep.py")
foreach ($f in $tools) {
    if (Test-Path $f) { git mv $f ("tools\" + $f) }
}

# ============================================================
# SEKTION 6 -- flytta DOKUMENT till docs\-undermappar
# ============================================================
$gov = @("BCG_PRICING_PLAYBOOK.md", "ROADMAP.md", "LOCKED_ASSUMPTIONS.md", "FUTURE_DEVELOPMENT.md")
foreach ($f in $gov) {
    if (Test-Path $f) { git mv $f ("docs\governance\" + $f) }
}

$know = @("LESSONS_BCG.md", "INSIGHTS_BCG.md", "F9_BUNDLE_INVENTORY.md")
foreach ($f in $know) {
    if (Test-Path $f) { git mv $f ("docs\knowledge\" + $f) }
}

$ops = @("TECHNICAL_PREREQUISITES.md", "KRAVSPEC_IT.md", "MASTER_AZURE.md", "UBUNTU_AZURE_VM.md")
foreach ($f in $ops) {
    if (Test-Path $f) { git mv $f ("docs\ops\" + $f) }
}

# README.md, DRIFT.md, REPLIKERING_OCH_VALIDERING.md stannar i ROTEN (navet)

# ============================================================
# SEKTION 7 -- arkivera gamla session-filer (inbakade i FUTURE_DEVELOPMENT)
# ============================================================
if (-not (Test-Path "archives\superseded")) {
    New-Item -ItemType Directory -Path "archives\superseded" | Out-Null
}
foreach ($f in @("NEXT_SESSION.md", "STARTTEXT_NEXT_SESSION.txt")) {
    if (Test-Path $f) { git mv $f ("archives\superseded\" + $f) }
}

# ============================================================
# SEKTION 8 -- dop om TILL_RADERING -> _ATT_RADERA
# ============================================================
if (Test-Path "TILL_RADERING") { git mv "TILL_RADERING" "_ATT_RADERA" }

# ============================================================
# SEKTION 9 -- granska, committa sedan
# ============================================================
Write-Output ""
Write-Output "=== Granska flyttarna ==="
git status
Write-Output ""
Write-Output "Om korrekt, committa med:"
Write-Output '  git commit -m "Repo-stadning: gruppera run/analysis/presentations/tools/docs"'
Write-Output ""
Write-Output "VIKTIGT efter flytt av korskript: nya sokvagar ar"
Write-Output "  py -3.11 verify_tool\run\run_step6.py"
Write-Output "  py -3.11 verify_tool\run\build_r12_for_model.py --tx <csv>"
