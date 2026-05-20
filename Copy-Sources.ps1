<#
.SYNOPSIS
    Phase 1b - copy the relevant files verbatim from BCG V2_New into the clean structure.

.DESCRIPTION
    Copies, WITHOUT modification, everything needed to run the elasticity pipeline:
    Python code (incl. utils.py / constants.py), SQL scripts, config.yml/.yaml,
    control_files, all README/markdown, requirements.txt, and the hardcoded input
    data files.

    Deliberately NOT copied:
      - Alteryx artefacts (*.yxmd, *.yxdb)        -> consultants said SQL replaces Alteryx
      - duckdb.exe                                -> AppLocker blocks .exe; replaced by the
                                                     duckdb Python package in Phase 4
      - generated outputs (model objects, automl) -> regenerated when we run
      - the two backup trees                      -> source of truth is V2_New only

    DOCUMENTED DECISION (interim input): V2_New is a code-centric snapshot and may not
    ship the generated weekly_model_data CSVs. The Product Cluster stage needs them to
    run before the SQL step is validated, so we copy BCG's last-good 0828 CSVs from the
    active '02. Elasticity' tree as interim input. They are replaced by SQL output once
    Phase 4 reproduces them. See playbook Phase 3/4.

    Pure ASCII; the a-ring in the OneDrive path is generated at runtime (PS 5.1 / CP1252).

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force
    . 'C:\Projekt\BCG\Copy-Sources.ps1'

.NOTES
    Jens Palmo (developer), 2026-05-20. Phase 1b of the BCG replication playbook.
#>

[CmdletBinding()]
param(
    [string]$TargetRoot = "C:\Projekt\BCG\Pipeline"
)

$ErrorActionPreference = 'Continue'

$aring   = [char]0x00E5
$bcgRoot = "C:\Users\jepa02\OneDrive - Evidensia Djursjukv${aring}rd AB\Datastrategi\BCG"
$v2e     = Join-Path $bcgRoot "BCG_orginal_V2_New\02. Elasticity"
$v2c     = Join-Path $bcgRoot "BCG_orginal_V2_New\01. Clustering"
$active  = Join-Path $bcgRoot "02. Elasticity"

$tgtE = Join-Path $TargetRoot "02. Elasticity"
$tgtC = Join-Path $TargetRoot "01. Clustering"

$modelStages = @("2. Product Cluster Level Models", "3. Product Site Level Models", "5. Bundle Clinic Models")

function Copy-Set {
    param([string]$Label, [string]$From, [string]$To, [string[]]$RoboArgs)
    Write-Host ("--- {0}" -f $Label) -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $From)) {
        Write-Host ("    SKIP: source missing -> {0}" -f $From) -ForegroundColor Yellow
        return
    }
    robocopy $From $To @RoboArgs /NFL /NDL /NJH /NP | Out-Null
    Write-Host ("    OK ({0})" -f $LASTEXITCODE) -ForegroundColor DarkGray
}

if (-not (Test-Path -LiteralPath $v2e)) {
    Write-Host "ERROR: V2_New source not found: $v2e" -ForegroundColor Red
    return
}

Write-Host "Populating: $TargetRoot" -ForegroundColor Cyan
Write-Host ""

$codePatterns = @('*.py', '*.sql', '*.yml', '*.yaml', '*.md', '*.txt')

# Pass 1 - code, sql, configs, READMEs, requirements (small, swept across both subtrees)
Copy-Set "Code/SQL/config/docs - Elasticity" $v2e $tgtE ($codePatterns + @('/S', '/XD', '__pycache__', 'venv', '.venv', '/XF', '*.yxmd'))
Copy-Set "Code/SQL/config/docs - Clustering" $v2c $tgtC ($codePatterns + @('/S', '/XD', '__pycache__', 'venv', '.venv', '/XF', '*.yxmd'))

# Pass 2 - control files (xlsx/csv) per model stage
foreach ($s in $modelStages) {
    Copy-Set ("Control files - {0}" -f $s) (Join-Path $v2e "$s\code\control_files") (Join-Path $tgtE "$s\code\control_files") @('*.xlsx', '*.csv')
}

# Pass 3 - model input data per stage (excludes huge Alteryx db); brings input CSV/XLSX and data\input\
foreach ($s in $modelStages) {
    Copy-Set ("Model data - {0}" -f $s) (Join-Path $v2e "$s\data") (Join-Path $tgtE "$s\data") @('/E', '/XF', '*.yxdb')
}

# Pass 4 - competitor input (lives under output\regular price\)
foreach ($s in $modelStages) {
    Copy-Set ("Competitor input - {0}" -f $s) (Join-Path $v2e "$s\output\regular price") (Join-Path $tgtE "$s\output\regular price") @('0619_regular_price_TT_competitors.xlsx')
}

# Pass 5 - INTERIM generated weekly_model_data CSVs for Product Cluster, from the active tree
Copy-Set "Interim weekly_model_data (Product Cluster, from active tree)" `
    (Join-Path $active "2. Product Cluster Level Models\data") `
    (Join-Path $tgtE "2. Product Cluster Level Models\data") `
    @('0828_Sweden_weekly_model_data_P_C.csv', '0828_Sweden_weekly_model_data_P_CH.csv')

# Pass 6 - SQL data prep inputs + parquet (transaction data)
Copy-Set "SQL prep inputs" (Join-Path $v2e "Sweden_Elasticity_Data_Prep_SQL\input")   (Join-Path $tgtE "Sweden_Elasticity_Data_Prep_SQL\input")   @('/E')
Copy-Set "SQL prep parquet" (Join-Path $v2e "Sweden_Elasticity_Data_Prep_SQL\parquet") (Join-Path $tgtE "Sweden_Elasticity_Data_Prep_SQL\parquet") @('/E')

# Pass 7 - Fall Back Logic inputs (xlsx only; exclude 4 GB yxdb)
Copy-Set "Fall Back inputs" (Join-Path $v2e "6. Fall Back Logic\input_data") (Join-Path $tgtE "6. Fall Back Logic\input_data") @('*.xlsx')

# Pass 8 - Clustering inputs
Copy-Set "Clustering inputs"     (Join-Path $v2c "Input")                       (Join-Path $tgtC "Input")                       @('/E', '/XF', '*.yxdb')
Copy-Set "Clustering SQL inputs" (Join-Path $v2c "Sweden_clustering_SQL\input") (Join-Path $tgtC "Sweden_clustering_SQL\input") @('/E')
Copy-Set "Clustering SQL parquet" (Join-Path $v2c "Sweden_clustering_SQL\parquet") (Join-Path $tgtC "Sweden_clustering_SQL\parquet") @('/E')

Write-Host ""
Write-Host "Copy complete. Verify with the sanity checks in the playbook (Phase 1)." -ForegroundColor Green
Write-Host "Robocopy exit codes 0-7 are success; 8+ means a real error." -ForegroundColor DarkGray
