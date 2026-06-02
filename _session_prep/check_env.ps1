# =============================================================================
# check_env.ps1 v3 - Environment check wrapper for BCG Pricing project
# =============================================================================
# Author: Jens Palmö
# Lives in: C:\Projekt\BCG\_session_prep\
#
# Usage:
#   .\check_env.ps1                # Default: LOCAL+CODE+CONFIG+AZURE+DATA+PIPELINE+HISTORY+STORAGE
#   .\check_env.ps1 -VmInner       # + VM-inre (om VM redan running)
#   .\check_env.ps1 -StartVm       # Startar VM, kor allt, deallocatar (~5 kr, ~7 min)
#   .\check_env.ps1 -SkipData      # Skippa CSV-läsning (snabbare, ~3 sek)
#   .\check_env.ps1 -Json          # JSON-output
#   .\check_env.ps1 -NoAutoFix     # Skippa auto-fix
#
# Exit code: 0 om alla PASS, 1 om nagot FAIL.
# =============================================================================

param(
    [switch]$VmInner,
    [switch]$StartVm,
    [switch]$Json,
    [switch]$NoAutoFix,
    [switch]$SkipData,
    [switch]$NoPause
)

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyScript  = Join-Path $ScriptDir "check_env.py"

$PythonExe = "C:\Projekt\BCG\Pipeline\02. Elasticity\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Host "FEL: Ingen Python-interpreter hittad." -ForegroundColor Red
    exit 2
}

if (-not (Test-Path $PyScript)) {
    Write-Host "FEL: check_env.py saknas: $PyScript" -ForegroundColor Red
    exit 2
}

$pyArgs = @($PyScript)
if ($Json)       { $pyArgs += "--json" }
if ($NoAutoFix)  { $pyArgs += "--no-autofix" }
if ($SkipData)   { $pyArgs += "--skip-data" }

$vmInnerEffective = $VmInner -or $StartVm

if ($StartVm) {
    Write-Host ""
    Write-Host "=== StartVm-flaggan aktiverad ==="
    Write-Host "Kostnad: ~5 kr (VM uppe ~5-10 min). Ctrl+C nu for att avbryta."
    if (-not $NoPause) {
        Write-Host "Tryck Enter for att fortsatta..." -ForegroundColor Yellow
        $null = Read-Host
    }
    
    Write-Host ""
    Write-Host "Startar VM..." -ForegroundColor Cyan
    az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEL: VM-start misslyckades." -ForegroundColor Red
        exit 2
    }
    
    Write-Host "Vantar 60s pa SSH..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
}

if ($vmInnerEffective) {
    $pyArgs += "--vm-inner"
}

& $PythonExe @pyArgs
$ExitCode = $LASTEXITCODE

if ($StartVm) {
    Write-Host ""
    Write-Host "Deallocatar VM (oavsett kontroll-resultat)..." -ForegroundColor Cyan
    az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "VM deallocated. Ingen mer kostnad tickar." -ForegroundColor Green
    } else {
        Write-Host "VARNING: Deallocate failade. Manuell ingripande kravs:" -ForegroundColor Red
        Write-Host "  az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm" -ForegroundColor Yellow
    }
}

exit $ExitCode
