# deploy_dashboard.ps1 -- BCG dashboard till Azure App Service (kod-deploy, ingen ACR)
# =====================================================================================
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Monster: MASTER_AZURE_DEPLOY (spok-katalogen D.1-D.11). Skriven som GRINDAT skript
# eftersom PowerShell INTE stoppar pa az-fel: utan grindar kaskadar ett rotfel till
# tio foljdfel (uppmatt tva ganger 2026-07-04). Varje az-steg mats och grindas.
# Idempotent: kan koras om fran borjan efter varje stopp -- befintligt hoppas over.
#
# KORNING (PowerShell, var som helst):
#   powershell -ExecutionPolicy Bypass -File C:\Projekt\BCG\tools\deploy_dashboard.ps1
#      -> fas 1: subscription/PIM-matning, plan, app, settings. Stannar vid AUTH-PAUS.
#   ... aktivera auth i Portalen (instruktion skrivs ut) ...
#   powershell -ExecutionPolicy Bypass -File C:\Projekt\BCG\tools\deploy_dashboard.ps1 -Deploy
#      -> fas 2: zip + deploy (Oryx bygger) + halsokoll med auth-larm.
param([switch]$Deploy)
$ErrorActionPreference = "Stop"

$RG      = "ev-openai-swce-rg-test"
$PLAN    = "bcg-dashboard-plan"
$APP     = "evbcg-dashboard"
$STORAGE = "evbcgpricinginput"
$REPO    = "C:\Projekt\BCG"

function Gate([string]$msg) {
    if ($LASTEXITCODE -ne 0) {
        throw "STOPP vid: $msg (se az-felet ovan). Atgarda och kor om -- skriptet ar idempotent."
    }
}
function Say([string]$m) { Write-Host "[deploy] $m" }

# --- Steg 0: subscription + PIM (D.2: RBAC-nekad lasning maskeras som NotFound) -------
$sub = az account show --query name -o tsv; Gate "az account show (ar du inloggad?)"
if ($sub -ne "ev-lz3-ai (SE)") {
    Say "Fel subscription ($sub) -- byter..."
    az account set --subscription "ev-lz3-ai (SE)"; Gate "account set"
}
# Rollkravande lasning = PIM-matning. Faller den: rollen ar dod, INTE resursen.
az group show -g $RG -o none
Gate "PIM-rollen nar inte $RG -- aktivera i Portalen (PIM > My roles > aktivera pa RG:n), vanta ~1 min, kor om"
Say "Subscription + PIM OK ($sub)"

if (-not $Deploy) {
    # --- Steg 1: plan (skapa BARA om den saknas) --------------------------------------
    $planId = az appservice plan show -g $RG -n $PLAN --query id -o tsv 2>$null
    if (-not $planId) {
        Say "Planen saknas -- skapar $PLAN (B1 Linux)..."
        az appservice plan create -g $RG -n $PLAN --sku B1 --is-linux --tags owner="Jens Palmo" -o none
        Gate "plan create"
    } else { Say "Planen finns redan: $PLAN" }

    # --- Steg 2: webapp som KOD-app (D.5: container-app kan inte flippas) -------------
    $appId = az webapp show -g $RG -n $APP --query id -o tsv 2>$null
    if (-not $appId) {
        Say "Appen saknas -- skapar $APP (PYTHON:3.11)..."
        az webapp create -g $RG -p $PLAN -n $APP --runtime "PYTHON:3.11" --tags owner="Jens Palmo" -o none
        Gate "webapp create (klagar CLI pa runtime-strangen: prova PYTHON^|3.11)"
    } else { Say "Appen finns redan: $APP" }

    # --- Steg 3: settings + startup + VERIFIERING (mat, anta inte) --------------------
    $key = az storage account keys list --account-name $STORAGE --resource-group $RG --query "[0].value" -o tsv
    Gate "storage keys list"
    if (-not $key) { throw "STOPP: keys list gav tom nyckel." }
    az webapp config appsettings set -g $RG -n $APP -o none --settings `
        SCM_DO_BUILD_DURING_DEPLOYMENT=true PRICINGMODEL_AUTH=key `
        PRICINGMODEL_KEY=$key PRICINGMODEL_STORAGE=$STORAGE PRICINGMODEL_RG=$RG
    Gate "appsettings set"
    az webapp config set -g $RG -n $APP --always-on true `
        --startup-file "gunicorn --bind=0.0.0.0:8000 --chdir orchestration/webapp --timeout 120 app:app" -o none
    Gate "config set (always-on + startup)"
    $n = az webapp config appsettings list -g $RG -n $APP --query "length([?name=='PRICINGMODEL_KEY'])" -o tsv
    Gate "settings verify"
    if ($n -ne "1") { throw "STOPP: PRICINGMODEL_KEY saknas efter set -- settings landade inte." }
    Say "Infra klar och verifierad."

    Write-Host ""
    Write-Host ">>> AUTH-PAUS (D.6 -- dorren fore nyckeln):" -ForegroundColor Yellow
    Write-Host ">>>   Portalen > App Service '$APP' > Authentication > Add identity provider"
    Write-Host ">>>   > Microsoft > Create new app registration > Require authentication"
    Write-Host ">>> Kor sedan fas 2:" -ForegroundColor Yellow
    Write-Host ">>>   powershell -ExecutionPolicy Bypass -File $REPO\tools\deploy_dashboard.ps1 -Deploy"
    exit 0
}

# --- Fas 2: zip + deploy + halsokoll --------------------------------------------------
Set-Location $REPO
if (-not (Test-Path .gitignore) -or -not (Select-String -Path .gitignore -Pattern "deploy\.zip" -Quiet)) {
    Add-Content .gitignore "deploy.zip"
}
Compress-Archive -Path orchestration, requirements.txt -DestinationPath deploy.zip -Force
$mb = [math]::Round((Get-Item deploy.zip).Length / 1MB, 1)
Say "deploy.zip byggd ($mb MB) -- deployar (Oryx pip-installerar, 2-4 min)..."
az webapp deploy -g $RG -n $APP --src-path deploy.zip --type zip
Gate "webapp deploy (kolla: az webapp log tail -g $RG -n $APP)"
Say "Deploy klar -- halsokoll om 30 s..."
Start-Sleep 30
$code = 0
try {
    $r = Invoke-WebRequest "https://$APP.azurewebsites.net" -UseBasicParsing -MaximumRedirection 0
    $code = [int]$r.StatusCode
} catch {
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
}
Say "HTTP-svar: $code"
if ($code -eq 302 -or $code -eq 401) {
    Say "RATT: login-redirect -- appen ar publicerad och last bakom Entra-inloggning."
} elseif ($code -eq 200) {
    Write-Host ">>> VARNING: 200 UTAN inloggning -- auth ar INTE aktiv. Aktivera i Portalen NU." -ForegroundColor Red
} elseif ($code -eq 503) {
    Say "503: appen startar an / bygget foll. Kor: az webapp log tail -g $RG -n $APP"
} else {
    Say "Ovantat svar -- kor: az webapp log tail -g $RG -n $APP"
}
