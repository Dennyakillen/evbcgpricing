# deploy_dashboard_final.ps1 (v1.8) -- FINAL timeboxed Oryx round, then close
# =============================================================================
# Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# v1.8:      Inserts the DEPENDENCY PROBE as a gate before staging.
#            Chain: probe (measure closure + tooling + Azure state)
#                   -> stage (package per measured manifest)
#                   -> deploy (--clean zip) -> measure verdict.
#            The probe replaced v1.0's regex gate after it caught a REAL
#            transitive dependency (blob.py -> run_status) that all 13
#            earlier deploys silently lacked.
# Purpose:   ONE last, gated attempt at the App Service code-deploy path,
#            producing a DOCUMENTED verdict either way:
#              VERDICT A: startup.sh executes ("App command line is a shell
#                         script...") -> path works, still not preferred.
#              VERDICT B: Build Operation ID unchanged despite --clean +
#                         unique payload -> D.16 unbeatable via CLI,
#                         chapter formally closed. NO further attempts.
#            Permanent path is Azure DevOps pipeline (azure-pipelines.yml,
#            same probe + stage modules) when IT finishes the setup.
# Run:       powershell -ExecutionPolicy Bypass -File C:\Projekt\BCG\tools\deploy_dashboard_final.ps1
# TIMEBOX:   ~30 min total. If verdict is B, STOP. Do not iterate.
# =============================================================================

$ErrorActionPreference = "Continue"   # D.12: Stop kills expected probe errors
$RG  = "ev-openai-swce-rg-test"
$APP = "evbcg-dashboard"
$SUB = "ev-lz3-ai (SE)"
$OLD_BUILD_ID = "a885ccb64c1a662f"    # the stale ID served twice on 2026-07-06
$REPO = "C:\Projekt\BCG"

$logDir = Join-Path $REPO "workspace\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$ts = Get-Date -Format "yyyy-MM-dd_HHmm"
Start-Transcript -Path (Join-Path $logDir "deploy_final_$ts.log") | Out-Null

function Gate($ok, $msg) {
    if (-not $ok) {
        Write-Host "[GATE] STOP: $msg" -ForegroundColor Red
        Stop-Transcript | Out-Null
        exit 1
    }
}

Write-Host "=== FINAL ORYX ROUND (v1.8) -- probe, stage, deploy, verdict ===" -ForegroundColor Cyan

# --- Gate 1: right subscription (D.9 / LB.46) --------------------------------
$acct = az account show --query name -o tsv 2>$null
Gate ($LASTEXITCODE -eq 0 -and $acct -eq $SUB) `
    "active subscription is '$acct', expected '$SUB'. Run: az login --scope https://management.core.windows.net//.default ; az account set --subscription '$SUB'"
Write-Host "[gate 1] subscription OK: $acct"

# --- Gate 2: app exists (PIM may have expired mid-day, D.3) ------------------
$state = az webapp show -g $RG -n $APP --query state -o tsv 2>$null
Gate ($LASTEXITCODE -eq 0 -and $state) `
    "cannot read app '$APP' (PIM expired? app deleted?). Re-activate PIM, then rerun."
Write-Host "[gate 2] app exists, state: $state"

# --- Gate 3: DEPENDENCY PROBE (measured closure, tooling, Azure state) -------
Push-Location $REPO
py -3.11 tools\webapp_deploy_probe.py --azure
$probeExit = $LASTEXITCODE
Pop-Location
Gate ($probeExit -eq 0) "probe found CRITICAL issues -- read its receipt in workspace\validation_receipts\, fix, rerun."
Write-Host "[gate 3] probe CLEAN -- staging manifest written"

# --- Gate 4: stage the payload per the measured manifest ---------------------
Push-Location $REPO
py -3.11 tools\stage_webapp.py
Gate ($LASTEXITCODE -eq 0) "stage_webapp.py failed -- see its FAIL line above."
Pop-Location
Write-Host "[gate 4] staging OK, deploy.zip fresh with unique payload hash"

# --- Step 5: startup command must point at the script -------------------------
az webapp config set -g $RG -n $APP --startup-file "startup.sh" --output none 2>$null
Gate ($LASTEXITCODE -eq 0) "could not set startup-file"
Write-Host "[step 5] startup-file = startup.sh (set)"

# --- Step 6: deploy with --clean (server-side wwwroot wipe = D.16 bust #2) ---
Write-Host "[step 6] deploying (zip + --clean). Client timeout is NOT build death (D.17)..."
az webapp deploy -g $RG -n $APP --src-path (Join-Path $REPO "deploy.zip") --type zip --clean true 2>&1 |
    Select-String -Pattern "Deployment|Build|status|error|Error" | ForEach-Object { "  $_" }
Write-Host "[step 6] deploy returned (exit $LASTEXITCODE) -- verdict comes from the SERVER log."

# --- Step 7: timeboxed log capture (90 s), filtered ---------------------------
Write-Host "[step 7] tailing logs 90 s, filtered (D.17: measure server-side)..."
$job = Start-Job -ScriptBlock {
    param($rg, $app)
    az webapp log tail -g $rg -n $app 2>&1
} -ArgumentList $RG, $APP
Wait-Job $job -Timeout 90 | Out-Null
$lines = Receive-Job $job
Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -Force -ErrorAction SilentlyContinue

$hits = $lines | Select-String -Pattern "Build Operation ID|App command line|Starting gunicorn|startup.sh|Booting worker|Traceback|not found|Build Summary|oryx-manifest"
Write-Host "--- filtered log lines ---" -ForegroundColor Yellow
$hits | ForEach-Object { "  $_" }
Write-Host "--------------------------" -ForegroundColor Yellow

# --- Step 8: VERDICT -----------------------------------------------------------
$receipt   = $hits | Select-String -Pattern "App command line is a shell script" -Quiet
$staleId   = $hits | Select-String -Pattern $OLD_BUILD_ID -Quiet
$newBuild  = ($hits | Select-String -Pattern "Build Operation ID" | Select-String -NotMatch $OLD_BUILD_ID -Quiet)
$gunicorn  = $hits | Select-String -Pattern "Starting gunicorn 20.1.0" -Quiet

Write-Host ""
Write-Host "=== VERDICT ===" -ForegroundColor Cyan
if ($staleId -and -not $newBuild) {
    Write-Host "VERDICT B: Build Operation ID STILL $OLD_BUILD_ID despite --clean + unique payload." -ForegroundColor Red
    Write-Host "Mechanically: wwwroot's oryx-manifest.toml was never replaced -- the deploy content"
    Write-Host "never landed. D.16 not beatable from the CLI here. CHAPTER CLOSED."
    Write-Host "Record in MASTER_AZURE_DEPLOY; permanent path: Azure DevOps pipeline."
} elseif ($receipt) {
    Write-Host "VERDICT A: startup.sh EXECUTED (receipt line seen -- first time ever)." -ForegroundColor Green
    if ($gunicorn) { Write-Host "  Pinned gunicorn 20.1.0 confirmed (D.22 fix bit)." }
    Write-Host "[health] probing site, 3 attempts / 30 s apart..."
    1..3 | ForEach-Object {
        Start-Sleep 30
        try { $c = (Invoke-WebRequest "https://$APP.azurewebsites.net" -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 20).StatusCode }
        catch { $c = [int]$_.Exception.Response.StatusCode }
        Write-Host "  attempt $($_): HTTP $c   (200/302-to-login = SUCCESS)"
    }
    Write-Host "Record in MASTER_AZURE_DEPLOY: D.16 busted by --clean + payload hash; path WORKS"
    Write-Host "but remains dispreferred (4 fragile Win/Linux seams). Permanent path is DevOps."
} else {
    Write-Host "VERDICT: INCONCLUSIVE within the 90 s window." -ForegroundColor Yellow
    Write-Host "Run ONE manual check (60 s, then Ctrl+C), paste ONLY matched lines:"
    Write-Host "  az webapp log tail -g $RG -n $APP 2>&1 | Select-String -Pattern 'Build Operation ID|App command line|Starting gunicorn|Traceback|not found'"
    Write-Host "Then apply the same A/B verdict rules. TIMEBOX still applies: no iteration."
}
Write-Host ""
Write-Host "Transcript: $logDir\deploy_final_$ts.log"
Stop-Transcript | Out-Null
